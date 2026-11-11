"""Automatic checks. Each returns (check_name, result, details). Questions are never modified here."""
import ast
import operator
import re

from ..extraction.structure import BASE_CONFIDENCE, normalize

CHECKS_VERSION = 1
OTHER_EXAM_RE = re.compile(r"\b(waec|wassce|neco|nabteb|gce|post[\s-]?utme)\b", re.I)


def _options(q):
    return {o.label: o.text for o in q.options.all()}


def _source_answers(q):
    return [a.label for a in q.answers.all() if a.origin == "source"]


def check_completeness(q):
    words = len(q.text.split())
    if len(q.text.strip()) < 10 or words < 3:
        return ("completeness", "fail", {"reason": "question text too short", "words": words})
    if q.text.rstrip().endswith(("…", "...")) and words < 6:
        return ("completeness", "warn", {"reason": "question may be cut off"})
    return ("completeness", "pass", {})


def check_options(q):
    opts = _options(q)
    labels = sorted(opts)
    if len(opts) < 4:
        return ("options", "fail", {"reason": f"only {len(opts)} options", "labels": labels})
    if labels[:4] != ["A", "B", "C", "D"]:
        return ("options", "fail", {"reason": "option labels are not A–D", "labels": labels})
    empty = [k for k, v in opts.items() if not v.strip()]
    if empty:
        return ("options", "fail", {"reason": "empty options", "labels": empty})
    norm = [normalize(v) for v in opts.values()]
    if len(set(norm)) != len(norm):
        return ("options", "fail", {"reason": "duplicate option texts"})
    if any(len(v) > 300 for v in opts.values()):
        return ("options", "warn", {"reason": "an option is unusually long (possible extraction bleed)"})
    if len(opts) > 4:
        return ("options", "warn", {"reason": f"{len(opts)} options; JAMB UTME normally uses A–D"})
    return ("options", "pass", {"count": len(opts)})


def check_answer(q):
    answers = _source_answers(q)
    opts = _options(q)
    if not answers:
        return ("answer_present", "warn", {"reason": "source gives no answer"})
    if len(set(answers)) > 1:
        return ("answer_present", "fail", {"reason": "conflicting answers within the same source", "answers": answers})
    if answers[0] not in opts:
        return ("answer_present", "fail", {"reason": f"answer {answers[0]} is not an option"})
    return ("answer_present", "pass", {"answer": answers[0]})


def check_exam_attribution(q):
    flagged = [f for f in q.flags if "not JAMB" in f]
    if flagged:
        return ("exam_attribution", "fail", {"reason": flagged[0]})
    m = OTHER_EXAM_RE.search(f"{q.text} {q.passage}")
    if m:
        return ("exam_attribution", "warn", {"reason": f"question text mentions {m.group(0)}"})
    if q.year and not (1978 <= q.year <= 2026):
        return ("exam_attribution", "fail", {"reason": f"year {q.year} outside UTME history"})
    return ("exam_attribution", "pass", {})


def check_metadata(q):
    missing = [k for k, v in (("subject", q.subject_id), ("year", q.year), ("question_number", q.question_number)) if not v]
    return ("metadata", "fail" if missing else "pass", {"missing": missing} if missing else {})


def check_diagram(q):
    if q.has_diagram and not q.image_refs:
        return ("diagram", "warn", {"reason": "refers to a diagram that was not captured"})
    return ("diagram", "pass", {})


def check_parse_warnings(q):
    warnings = [f for f in q.flags if "not JAMB" not in f]
    return ("extraction_warnings", "warn" if warnings else "pass", {"warnings": warnings} if warnings else {})


# --- arithmetic re-check -----------------------------------------------------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg}
ARITH_Q = re.compile(r"^(?:evaluate|simplify|find the value of|calculate|what is)\s+([\d\s.+\-*/×÷^()]+?)\s*[.?]?\s*$", re.I)


def _safe_eval(expr: str):
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
    node = ast.parse(expr, mode="eval").body

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            if isinstance(n.op, ast.Pow) and abs(ev(n.right)) > 12:
                raise ValueError("exponent too large")
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("unsupported")
    return ev(node)


def _num(s: str):
    try:
        return float(s.strip().rstrip(".").replace(",", ""))
    except ValueError:
        return None


def check_arithmetic(q):
    """Only for plain numeric expressions like 'Evaluate 3 + 4 × 2'. Flags, never fixes."""
    m = ARITH_Q.match(q.text.strip())
    if not m:
        return None
    try:
        value = _safe_eval(m.group(1))
    except Exception:  # noqa: BLE001
        return None
    opts = {k: _num(v) for k, v in _options(q).items()}
    matching = [k for k, v in opts.items() if v is not None and abs(v - value) < 1e-9]
    answers = _source_answers(q)
    if not matching:
        return ("math_check", "warn", {"computed": value, "reason": "no option equals the computed value"})
    if answers and answers[0] not in matching:
        return ("math_check", "fail", {"computed": value, "source_answer": answers[0], "expected": matching,
                                       "reason": "source answer disagrees with arithmetic"})
    return ("math_check", "pass", {"computed": value, "option": matching[0]})


ALL_CHECKS = [check_completeness, check_options, check_answer, check_exam_attribution, check_metadata,
              check_diagram, check_parse_warnings, check_arithmetic]


def run_checks(q) -> list[tuple]:
    return [r for r in (c(q) for c in ALL_CHECKS) if r]


def confidence(method: str, results: list[tuple], cross_source_agree: int = 0) -> float:
    c = BASE_CONFIDENCE.get(method, 0.7)
    for _, res, _ in results:
        c -= {"warn": 0.08, "fail": 0.25}.get(res, 0)
    c += min(0.15, 0.08 * cross_source_agree)
    return round(max(0.0, min(1.0, c)), 2)
