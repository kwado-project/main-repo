"""Import a JSON file of questions into the bank.

    python manage.py import_questions content/jamb_starter_questions.json --exam jamb --by admin@example.com
    python manage.py import_questions content/jamb_starter_questions.json --exam jamb --by admin@example.com --publish

Without --publish, questions enter as *draft* with the file's answer in the review notes; verify and publish
them in Admin → Question bank. With --publish, the file's "answer" letter becomes the verified answer key,
recorded as verified by the --by admin, and each question is validated → answer verified → reviewed → published
in one go. Re-running is safe: questions already imported are skipped (and get a topic if they had none);
with --publish, already-imported questions that aren't live yet are published too.
"""
import json

from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.examinations.models import Examination
from apps.questions.models import Question
from apps.questions.services import import_rows, transition

S = Question.Status


def publish_question(q: Question, answer: str, actor, source: str) -> str | None:
    """Walk one question through the workflow. Returns an error message, or None when published."""
    if q.status == S.PUBLISHED:
        return None
    if not answer:
        return "no answer letter in the file"
    opt = q.options.filter(label=answer).first()
    if not opt:
        return f"no option {answer!r}"
    try:
        if q.status in (S.DRAFT, S.REJECTED):
            q = transition(q, S.VALIDATED, actor)
        if q.status in (S.VALIDATED, S.ANSWER_VERIFIED):
            q = transition(q, S.ANSWER_VERIFIED, actor, correct_option_id=opt.pk, source=source)
        if q.status == S.ANSWER_VERIFIED:
            q = transition(q, S.IN_REVIEW, actor)
        transition(q, S.PUBLISHED, actor)
    except ValidationError as e:
        return str(e.detail)[:300]
    return None


class Command(BaseCommand):
    help = "Import questions from a JSON file (list of rows); optionally publish them."

    def add_arguments(self, p):
        p.add_argument("path")
        p.add_argument("--exam", help="Examination code to attach, e.g. jamb")
        p.add_argument("--by", help="Email of the admin recorded as creator (and verifier with --publish)")
        p.add_argument("--publish", action="store_true",
                       help="Use the file's answer letters as verified answer keys and publish the questions")

    def handle(self, path, exam=None, by=None, publish=False, **o):
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            raise CommandError("The file must contain a JSON list.")
        if exam:
            ex = Examination.objects.filter(code__iexact=exam).first()
            if not ex:
                raise CommandError(f"No examination with code {exam!r}. "
                                   f"Codes: {', '.join(Examination.objects.values_list('code', flat=True))}")
            for r in rows:
                r.setdefault("examination_id", ex.pk)
        actor = User.objects.filter(email__iexact=by).first() if by else None
        if by and not actor:
            raise CommandError(f"No user {by!r}.")
        if publish and (not actor or actor.role != "admin"):
            raise CommandError("--publish needs --by <email of an admin account>.")

        res = import_rows(rows, actor, skip_existing=True)
        for e in res["errors"]:
            self.stderr.write(f"row {e['row']}: {e['error']}")
        self.stdout.write(self.style.SUCCESS(
            f"Created {res['created']} questions, skipped {res['skipped']} already imported, {len(res['errors'])} errors."))
        if not publish:
            self.stdout.write("They are drafts. Verify and publish them in Admin → Question bank, or re-run with --publish.")
            return

        published, failed = 0, 0
        source = f"Import file {path.rsplit('/', 1)[-1]} (published with --publish by {actor.email})"[:200]
        for pk, answer in res["created_ids"] + res["matched_ids"]:
            q = Question.objects.get(pk=pk)
            if q.status == S.PUBLISHED:
                continue
            err = publish_question(q, answer, actor, source)
            if err:
                failed += 1
                self.stderr.write(f"question {pk} ({q.text[:50]!r}): {err}")
            else:
                published += 1
        self.stdout.write(self.style.SUCCESS(f"Published {published} questions. {failed} could not be published."))
