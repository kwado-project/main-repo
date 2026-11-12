from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils.text import slugify

from apps.examinations.models import Subject
from apps.questions.models import Passage, Question

pytestmark = pytest.mark.django_db
FILE = Path(__file__).resolve().parent.parent / "content" / "jamb_starter_questions.json"


def test_starter_file_imports_as_drafts_with_shared_passages(capsys):
    import json
    rows = json.loads(FILE.read_text(encoding="utf-8"))
    for name in {r["subject"] for r in rows}:
        Subject.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
    call_command("import_questions", str(FILE))
    assert "Created %d" % len(rows) in capsys.readouterr().out
    assert Question.objects.filter(status="draft").count() == len(rows)
    eng = Passage.objects.get(title="Comprehension passage")
    assert eng.questions.count() == 5 and Passage.objects.count() == 2
    q = Question.objects.filter(text__startswith="Evaluate $\\log_{10} 8").get()
    assert q.options.count() == 4 and "Suggested answer" in q.review_notes and not hasattr(q, "answer_key")
    call_command("import_questions", str(FILE))  # re-running is safe
    assert Question.objects.count() == len(rows) and Passage.objects.count() == 2
    assert f"skipped {len(rows)}" in capsys.readouterr().out


def test_publish_flag_publishes_with_topics_and_answer_keys(make_student, capsys):
    import json
    from apps.questions.models import Question
    rows = json.loads(FILE.read_text(encoding="utf-8"))
    for name in {r["subject"] for r in rows}:
        Subject.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
    admin = make_student("boss@example.com")
    admin.role = "admin"
    admin.save()
    call_command("import_questions", str(FILE))  # first as drafts, like an earlier run on the VPS
    call_command("import_questions", str(FILE), "--by", admin.email, "--publish")
    out = capsys.readouterr()
    assert f"Published {len(rows)} questions. 0 could not" in out.out, out.err
    assert Question.objects.filter(status="published").count() == len(rows)
    assert not Question.objects.filter(topic__isnull=True).exists()
    q = Question.objects.get(text__startswith="Evaluate $\\log_{10} 8")
    assert q.topic.name == "Logarithms" and q.answer_key.correct_option.text == "3" and q.answer_key.is_verified
    for r in rows:
        q = Question.objects.get(text=r["text"], subject__name=r["subject"])
        assert q.answer_key.correct_option.label == r["answer"]
