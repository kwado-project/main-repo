"""Guess examination, subject and year from a URL, title or snippet.

Pure functions — no database access — so they are cheap to run on every link.
"""
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

# alias (lower-case, word-bounded) → canonical subject slug used by apps.examinations
SUBJECT_ALIASES = {
    "use of english": "english-language", "english language": "english-language", "english": "english-language",
    "mathematics": "mathematics", "maths": "mathematics", "math": "mathematics",
    "further mathematics": "further-mathematics", "further maths": "further-mathematics",
    "physics": "physics", "chemistry": "chemistry", "biology": "biology",
    "agricultural science": "agricultural-science", "agric science": "agricultural-science", "agriculture": "agricultural-science", "agric": "agricultural-science",
    "economics": "economics", "commerce": "commerce",
    "principles of accounts": "financial-accounting", "principles of account": "financial-accounting",
    "financial accounting": "financial-accounting", "accounting": "financial-accounting", "accounts": "financial-accounting",
    "government": "government", "govt": "government",
    "literature in english": "literature-in-english", "literature": "literature-in-english", "lit in english": "literature-in-english",
    "geography": "geography",
    "christian religious studies": "christian-religious-studies", "christian religious knowledge": "christian-religious-studies",
    "crs": "christian-religious-studies", "crk": "christian-religious-studies",
    "islamic religious studies": "islamic-studies", "islamic studies": "islamic-studies", "irs": "islamic-studies", "irk": "islamic-studies",
    "civic education": "civic-education", "history": "history", "computer studies": "computer-studies",
    "computer science": "computer-studies", "home economics": "home-economics",
    "physical and health education": "physical-and-health-education", "physical health education": "physical-and-health-education",
    "fine art": "fine-art", "fine arts": "fine-art", "music": "music", "french": "french", "arabic": "arabic",
    "hausa": "hausa", "igbo": "igbo", "yoruba": "yoruba",
}
_ALIASES_LONGEST_FIRST = sorted(SUBJECT_ALIASES, key=len, reverse=True)

OTHER_EXAMS = {
    "waec": "waec", "wassce": "waec", "neco": "neco", "ssce": "neco", "gce": "gce", "nabteb": "nabteb",
    "post utme": "post-utme", "post-utme": "post-utme", "putme": "post-utme", "aptitude test": "post-utme",
}
QUESTION_WORDS = ("past question", "past-question", "pastquestion", "questions and answers", "question paper",
                  "past paper", "objective", "utme", "jamb", "cbt")


@dataclass
class Classification:
    exam: str = ""          # "jamb", another exam code, or "" if unknown
    subject_slug: str = ""
    year: int | None = None
    looks_like_questions: bool = False
    confidence: float = 0.0


def _haystack(*parts: str) -> str:
    text = " ".join(unquote(p or "") for p in parts).lower()
    text = re.sub(r"[_\-/.+=?&%]+", " ", text)
    return re.sub(r"\s+", " ", text)


def url_text(url: str) -> str:
    p = urlparse(url)
    return f"{p.netloc} {p.path} {p.query}"


def detect_exam(text: str) -> str:
    for alias, code in sorted(OTHER_EXAMS.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return code
    if re.search(r"\b(jamb|utme|ume)\b", text):
        return "jamb"
    return ""


def detect_subject(text: str) -> str:
    for alias in _ALIASES_LONGEST_FIRST:
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return SUBJECT_ALIASES[alias]
    return ""


def detect_year(text: str, year_from: int = 1978, year_to: int = 2100) -> int | None:
    years = [int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", text)]
    years = [y for y in years if year_from <= y <= year_to]
    return years[0] if years else None


def classify(url: str = "", title: str = "", snippet: str = "", year_from: int = 1978, year_to: int = 2100) -> Classification:
    # Title and URL are the strongest signals; snippets often mention many years/subjects.
    primary = _haystack(title, url_text(url))
    secondary = _haystack(snippet)
    c = Classification()
    c.exam = detect_exam(primary) or detect_exam(secondary)
    c.subject_slug = detect_subject(primary) or detect_subject(secondary)
    c.year = detect_year(primary, year_from, year_to) or detect_year(secondary, year_from, year_to)
    c.looks_like_questions = any(w in primary or w in secondary for w in QUESTION_WORDS) or url.lower().endswith(".pdf")
    score = 0.0
    score += 0.35 if c.exam == "jamb" else (-0.3 if c.exam else 0)
    score += 0.25 if c.subject_slug else 0
    score += 0.25 if c.year else 0
    score += 0.15 if c.looks_like_questions else 0
    c.confidence = round(max(0.0, min(1.0, score)), 2)
    return c


def is_relevant(c: Classification) -> bool:
    """Worth recording as a candidate JAMB past-question document."""
    if c.exam and c.exam != "jamb":
        return False
    return c.looks_like_questions and (c.exam == "jamb" or (c.subject_slug and c.year))
