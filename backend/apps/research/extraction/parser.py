"""Turn plain text (from HTML, a PDF text layer or OCR) into structured questions.

The parser never invents content: a missing answer or explanation stays None, and
anything it is unsure about is reported in `warnings` for the quality checks.
"""
import re
from dataclasses import dataclass, field

IMG_MARK = re.compile(r"\[\[IMG:([^\]]+)\]\]")
PAGE_MARK = re.compile(r"\[\[PAGE:(\d+)\]\]")
Q_START = re.compile(r"^\s*(?:Q(?:uestion)?\s*)?(\d{1,3})\s*[.):]\s*(?=\S)", re.I)
OPT_MARK = re.compile(r"(?:(?<=\s)|^)\(?([A-Ea-e])\s*[.):]\s+")
INLINE_ANSWER = re.compile(r"(?:^|\s)(?:correct\s+)?(?:answer|ans)\s*(?:is)?\s*[:\-=]?\s*\(?([A-E])\)?(?![A-Za-z])", re.I)
EXPLANATION = re.compile(r"(?:^|\n)\s*(?:explanation|solution|working)\s*[:\-]\s*", re.I)
KEY_HEADER = re.compile(r"^\s*(?:answer\s*key|answers?|key\s+to\s+questions|solutions?)\s*[:\-]?\s*$", re.I | re.M)
KEY_PAIR = re.compile(r"(?<!\d)(\d{1,3})\s*[.):\-]?\s*\(?([A-E])\)?(?![A-Za-z])")
PASSAGE_RANGE = re.compile(r"(?:questions?|nos?\.?)\s*(\d{1,3})\s*(?:to|-|–|and|through)\s*(\d{1,3})", re.I)
PASSAGE_INTRO = re.compile(r"read the (?:following )?passages?|passage below|comprehension", re.I)
MATH_RE = re.compile(r"[²³√π∫∑÷×≤≥≠∞θ]|\^\d|\b\d+/\d+\b|\b(?:log|sin|cos|tan)\b|[a-z]\s*=\s*-?\d|\d\s*[xy]\b")
DIAGRAM_RE = re.compile(r"\b(?:diagram|figure|fig\.|graph (?:below|above)|shown (?:below|above)|the table below|illustrat)", re.I)


@dataclass
class ParsedQuestion:
    number: int
    text: str
    options: dict = field(default_factory=dict)
    answer: str | None = None
    explanation: str | None = None
    passage: str = ""
    image_refs: list = field(default_factory=list)
    page: int | None = None
    has_math: bool = False
    has_diagram: bool = False
    warnings: list = field(default_factory=list)


@dataclass
class ParsedPaper:
    questions: list = field(default_factory=list)
    answer_key: dict = field(default_factory=dict)
    header: str = ""
    warnings: list = field(default_factory=list)


def _clean(s: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\s*\n\s*", " ", s)).strip()


def _split_answer_key(text: str) -> tuple[str, dict]:
    """Remove a trailing answer-key section and parse it into {number: letter}."""
    m = None
    for m in KEY_HEADER.finditer(text):
        pass
    if not m:
        return text, {}
    tail = PAGE_MARK.sub(" ", text[m.end():])
    pairs = KEY_PAIR.findall(tail)
    # Only treat it as a key if the section is mostly number→letter pairs.
    tokens = len(re.findall(r"\S+", tail))
    if not pairs or 2 * len(pairs) < 0.6 * tokens:
        return text, {}
    return text[:m.start()], {int(n): a.upper() for n, a in pairs}


def _find_options(block: str) -> tuple[str, dict]:
    """Find an ordered A, B, C, D(, E) run of option markers. Returns (stem, options)."""
    marks = [(m.group(1).upper(), m.start(), m.end()) for m in OPT_MARK.finditer(block)]
    best = []
    for i, (lab, _, _) in enumerate(marks):
        if lab != "A":
            continue
        run, want = [marks[i]], "B"
        for mk in marks[i + 1:]:
            if mk[0] == want:
                run.append(mk)
                want = chr(ord(want) + 1)
        if len(run) > len(best):
            best = run
    if len(best) < 2:
        return block, {}
    stem = block[:best[0][1]]
    opts = {}
    for j, (lab, _, end) in enumerate(best):
        stop = best[j + 1][1] if j + 1 < len(best) else len(block)
        opts[lab] = _clean(block[end:stop])
    return stem, opts


def _passages(text: str) -> list[tuple[int, int, str]]:
    """Find comprehension passages that state which questions they belong to."""
    out = []
    for m in PASSAGE_INTRO.finditer(text):
        window = text[max(0, m.start() - 200): m.end() + 300]
        r = PASSAGE_RANGE.search(window)
        if not r:
            continue
        start, end = int(r.group(1)), int(r.group(2))
        # passage text runs from the intro to the first line starting with question `start`
        q = re.search(rf"(?m)^\s*{start}\s*[.)]\s", text[m.start():])
        body = text[m.start(): m.start() + q.start()] if q else ""
        if body:
            out.append((start, end, _clean(body)))
    return out


def parse_text(text: str) -> ParsedPaper:
    paper = ParsedPaper()
    text = text.replace("\r", "")
    text, paper.answer_key = _split_answer_key(text)
    passages = _passages(text)

    lines = text.split("\n")
    blocks, current, expected, page = [], None, None, None
    header_lines = []
    for line in lines:
        pm = PAGE_MARK.search(line)
        if pm:
            page = int(pm.group(1))
            line = PAGE_MARK.sub("", line)
        if PASSAGE_INTRO.search(line) and not Q_START.match(line):
            # A passage (or other instructions) ends the previous question; its text is
            # attached to the questions it names by _passages().
            if current:
                blocks.append(current)
            current = None
            continue
        m = Q_START.match(line)
        n = int(m.group(1)) if m else None
        # A new question must continue the numbering (tolerating a few skipped numbers).
        if m and (expected is None and n <= 5 or expected is not None and expected <= n <= expected + 3):
            if current:
                blocks.append(current)
            current = {"n": n, "lines": [line[m.end():]], "page": page}
            expected = n + 1
        elif current:
            current["lines"].append(line)
        else:
            header_lines.append(line)
    if current:
        blocks.append(current)
    paper.header = _clean("\n".join(header_lines))[:1000]

    for b in blocks:
        raw = "\n".join(b["lines"])
        q = ParsedQuestion(number=b["n"], text="", page=b["page"])
        q.image_refs = IMG_MARK.findall(raw)
        raw = IMG_MARK.sub(" ", raw)
        ex = EXPLANATION.search(raw)
        if ex:
            q.explanation = _clean(raw[ex.end():]) or None
            raw = raw[:ex.start()]
        stem, opts = _find_options(raw)
        if opts:
            last = sorted(opts)[-1]
            am = INLINE_ANSWER.search(opts[last])
            if am:
                q.answer = am.group(1).upper()
                opts[last] = _clean(opts[last][:am.start()])
        am = INLINE_ANSWER.search(stem) if not q.answer else None
        if am and opts:
            q.answer = am.group(1).upper()
            stem = stem[:am.start()]
        q.text = _clean(stem)
        q.options = opts
        if not q.answer and b["n"] in paper.answer_key:
            q.answer = paper.answer_key[b["n"]]
        for start, end, body in passages:
            if start <= q.number <= end:
                q.passage = body
        joined = f"{q.text} {' '.join(opts.values())}"
        q.has_math = bool(MATH_RE.search(joined))
        q.has_diagram = bool(q.image_refs) or bool(DIAGRAM_RE.search(q.text))
        if len(opts) < 4:
            q.warnings.append(f"only {len(opts)} options found")
        if q.answer and q.answer not in opts:
            q.warnings.append(f"answer {q.answer} is not among the options")
        if q.has_diagram and not q.image_refs:
            q.warnings.append("mentions a diagram but none was captured")
        paper.questions.append(q)

    numbers = [q.number for q in paper.questions]
    if numbers and numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        missing = sorted(set(range(numbers[0], numbers[-1] + 1)) - set(numbers))
        if missing:
            paper.warnings.append(f"question numbers missing: {missing[:20]}")
    return paper
