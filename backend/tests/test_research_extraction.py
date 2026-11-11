"""Stage 2: parsing, HTML/PDF/OCR extraction, provenance and export. Fixtures are invented sample questions."""
import pytest

from apps.research import pipeline
from apps.research.extraction import pdf as pdf_ex
from apps.research.extraction.html import html_to_text
from apps.research.extraction.parser import parse_text
from apps.research.extraction.structure import question_hash, to_record
from apps.research.models import PastAnswer, PastQuestion, Source, SourceDocument

from test_research_discovery import ROBOTS_OK, web  # noqa: F401  (shared fixture)

pytestmark = pytest.mark.django_db

PAPER = """SAMPLE PAPER - MATHEMATICS 2010
1. Simplify 2^3 x 2^2.
A. 2^5
B. 2^6
C. 4^5
D. 2^1
Answer: A
Explanation: add the indices, 3 + 2 = 5.
2. Find x if 3x = 12. A. 2 B. 3 C. 4 D. 5
3. Which of these is a prime number?
(a) 9 (b) 15 (c) 21 (d) 23
Read the passage below and answer questions 4 to 5.
The river was quiet. Ada counted the boats.
4. What did Ada count?
A. Fish
B. Boats
C. Stars
D. Birds
5. The river was
A. loud B. quiet C. dry D. wide
ANSWER KEY
1. A 2. C 3. D 4. B 5. B
"""


def test_parser_layouts_answers_passages_and_explanations():
    p = parse_text(PAPER)
    assert [q.number for q in p.questions] == [1, 2, 3, 4, 5]
    q1, q2, q3, q4, _ = p.questions
    assert q1.options == {"A": "2^5", "B": "2^6", "C": "4^5", "D": "2^1"} and q1.answer == "A"
    assert q1.explanation == "add the indices, 3 + 2 = 5." and q1.has_math
    assert q2.options["C"] == "4" and q2.answer == "C"          # inline options, answer from the key
    assert q3.options["D"] == "23" and "passage" not in q3.options["D"].lower()
    assert q4.passage.startswith("Read the passage") and "boats" in q4.passage
    assert not any(q.warnings for q in p.questions)


def test_parser_never_invents_answers_and_flags_problems():
    p = parse_text("1. What is the capital of Nigeria?\nA. Lagos\nB. Abuja\n2. Pick one.\nA. x B. y C. z D. w\nAnswer: E\n")
    q1, q2 = p.questions
    assert q1.answer is None and "only 2 options found" in q1.warnings
    assert q2.answer == "E" and "answer E is not among the options" in q2.warnings


def test_html_to_text_keeps_structure_images_and_superscripts():
    html = """<html><head><title>JAMB Mathematics 2010 Past Questions</title><script>x()</script></head><body>
      <nav>Home | About</nav><article>
      <div class="q"><p>1. Evaluate 5<sup>2</sup>.</p><ul><li>A. 10</li><li>B. 25</li><li>C. 7</li><li>D. 52</li></ul></div>
      <div class="q"><p>2. Use the figure below. <img src="/img/fig2.png"></p><ol><li>A. 1</li><li>B. 2</li><li>C. 3</li><li>D. 4</li></ol></div>
      <p>Some more filler text so the article is long enough to be picked as the main content of this page, as real pages are.</p>
      <p>Even more filler text describing the past questions and how to use them in your preparation for the examination.</p>
      </article><footer>© Example</footer></body></html>"""
    text, title = html_to_text(html, "https://pq.ng/jamb/maths/2010")
    assert title.startswith("JAMB Mathematics") and "Home | About" not in text and "x()" not in text
    p = parse_text(text)
    assert p.questions[0].text == "Evaluate 5^2." and p.questions[0].options["B"] == "25"
    assert p.questions[1].image_refs == ["https://pq.ng/img/fig2.png"] and p.questions[1].has_diagram


def _pdf(lines: list[str], scanned: bool = False) -> bytes:
    import pymupdf as fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 60
    for line in lines:
        page.insert_text((50, y), line, fontsize=12)
        y += 22
    if scanned:
        pix = page.get_pixmap(dpi=200)
        out = fitz.open()
        p2 = out.new_page(width=595, height=842)
        p2.insert_image(p2.rect, pixmap=pix)
        doc.close()
        doc = out
    data = doc.tobytes()
    doc.close()
    return data


PDF_LINES = ["SAMPLE PAPER - BIOLOGY 2004", "1. Which organelle releases energy?", "A. Nucleus", "B. Mitochondrion",
             "C. Ribosome", "D. Vacuole", "2. Green plants make food by", "A. respiration", "B. digestion",
             "C. photosynthesis", "D. excretion", "ANSWER KEY", "1. B 2. C"]


def test_pdf_text_layer_extraction():
    out = pdf_ex.pdf_to_text(_pdf(PDF_LINES))
    assert out.method == "pdf_text" and not out.ocr_pages
    p = parse_text(out.text)
    assert len(p.questions) == 2 and p.questions[0].options["B"] == "Mitochondrion"
    assert p.questions[1].answer == "C" and p.questions[0].page == 1


@pytest.mark.skipif(not pdf_ex.ocr_available(), reason="tesseract not installed")
def test_scanned_pdf_uses_ocr():
    out = pdf_ex.pdf_to_text(_pdf(PDF_LINES, scanned=True))
    assert out.method == "ocr" and out.ocr_pages == [1]
    p = parse_text(out.text)
    assert len(p.questions) == 2
    assert "mitochondrion" in p.questions[0].options.get("B", "").lower()


def _site(web, permission, pages):
    web({"https://lic.ng/robots.txt": (200, "text/plain", ROBOTS_OK), **pages})
    src = Source.objects.create(domain="lic.ng", homepage="https://lic.ng/", permission_status=permission,
                                robots_checked_at=None)
    return src


def test_extract_document_end_to_end_with_provenance(seeded, web):  # noqa: F811
    pdf_bytes = _pdf(PDF_LINES)
    src = _site(web, Source.Permission.PERMITTED, {"https://lic.ng/jamb-biology-2004.pdf": (200, "application/pdf", pdf_bytes)})
    doc = SourceDocument.objects.create(source=src, url="https://lic.ng/jamb-biology-2004.pdf")
    from apps.research.discovery.crawler import record_document
    record_document(src, doc.url)
    doc.refresh_from_db()
    out = pipeline.extract_document(doc)
    assert out["created"] == 2 and out["method"] == "pdf_text" and out["year"] == 2004 and out["subject"] == "Biology"
    q = PastQuestion.objects.get(document=doc, question_number=1)
    assert (q.source, q.source_url, q.page_number, q.extraction_method) == (src, doc.url, 1, "pdf_text")
    assert q.rights_status == "cleared" and q.verification_status == "unverified"
    assert q.answers.get().origin == PastAnswer.Origin.SOURCE and q.answers.get().label == "B"
    doc.refresh_from_db()
    assert doc.status == "extracted" and doc.storage_key.startswith("research/raw/lic.ng/")
    assert pipeline.extract_document(doc) == {"skipped": "already extracted"}
    # Same file at another URL is detected as duplicate content, not extracted twice.
    web({"https://lic.ng/robots.txt": (200, "text/plain", ROBOTS_OK), "https://lic.ng/copy.pdf": (200, "application/pdf", pdf_bytes)})
    twin = SourceDocument.objects.create(source=src, url="https://lic.ng/copy.pdf")
    assert "duplicate_of_document" in pipeline.extract_document(twin)
    assert PastQuestion.objects.count() == 2


def test_extract_refuses_sources_without_permission(seeded, web):  # noqa: F811
    w = web({"https://lic.ng/robots.txt": (200, "text/plain", ROBOTS_OK)})
    src = Source.objects.create(domain="lic.ng", homepage="https://lic.ng/", permission_status=Source.Permission.NEEDS_REVIEW)
    doc = SourceDocument.objects.create(source=src, url="https://lic.ng/jamb-biology-2004.pdf")
    out = pipeline.extract_document(doc)
    assert "blocked" in out and not PastQuestion.objects.exists()
    doc.refresh_from_db()
    assert doc.status == "blocked" and not any("biology" in u for u in w.requested)


def test_export_record_matches_agreed_schema(seeded, web):  # noqa: F811
    src = _site(web, Source.Permission.OPEN_LICENSE,
                {"https://lic.ng/jamb/mathematics/2010": (200, "text/html", "<title>JAMB Mathematics 2010</title><body>" + PAPER.replace("\n", "<br>") + "</body>")})
    from apps.research.discovery.crawler import record_document
    doc = record_document(src, "https://lic.ng/jamb/mathematics/2010", title="JAMB Mathematics 2010 past questions")
    pipeline.extract_document(doc)
    rec = to_record(PastQuestion.objects.get(document=doc, question_number=1))
    assert {k: rec[k] for k in ("exam", "year", "subject", "question_number", "correct_answer", "verification_status", "rights_status")} == {
        "exam": "JAMB", "year": 2010, "subject": "Mathematics", "question_number": 1, "correct_answer": "A",
        "verification_status": "unverified", "rights_status": "cleared"}
    assert rec["options"] == {"A": "2^5", "B": "2^6", "C": "4^5", "D": "2^1"} and rec["source_url"] == doc.url
    assert rec["explanation"] == "add the indices, 3 + 2 = 5." and rec["topic"] is None


def test_hash_ignores_option_order_and_spacing():
    assert question_hash("What is 2+2?", {"A": "3", "B": "4"}) == question_hash("what  is 2+2 ?", {"A": "4", "B": "3"})
