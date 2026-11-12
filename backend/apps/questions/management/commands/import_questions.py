"""Import a JSON file of questions into the bank as drafts.

    python manage.py import_questions content/jamb_starter_questions.json --exam jamb --by kwado@example.com

Questions enter as *draft*; the suggested answer goes into review notes. Verify and publish them in
Admin → Question bank (a second reviewer publishes). Re-running skips questions already imported.
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.examinations.models import Examination
from apps.questions.services import import_rows


class Command(BaseCommand):
    help = "Import questions from a JSON file (list of rows) as drafts."

    def add_arguments(self, p):
        p.add_argument("path")
        p.add_argument("--exam", help="Examination code to attach, e.g. jamb")
        p.add_argument("--by", help="Email of the admin recorded as creator")

    def handle(self, path, exam=None, by=None, **o):
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            raise CommandError("The file must contain a JSON list.")
        if exam:
            ex = Examination.objects.filter(code__iexact=exam).first()
            if not ex:
                raise CommandError(f"No examination with code {exam!r}.")
            for r in rows:
                r.setdefault("examination_id", ex.pk)
        actor = User.objects.filter(email__iexact=by).first() if by else None
        if by and not actor:
            raise CommandError(f"No user {by!r}.")
        res = import_rows(rows, actor, skip_existing=True)
        for e in res["errors"]:
            self.stderr.write(f"row {e['row']}: {e['error']}")
        self.stdout.write(self.style.SUCCESS(
            f"Created {res['created']} draft questions, skipped {res['skipped']} already imported, {len(res['errors'])} errors."))
