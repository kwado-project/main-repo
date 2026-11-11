"""python manage.py research <command>

  matrix                     create the JAMB subject × year research matrix
  seed URL [--name N]        add a seed website to crawl
  sources [--status S]       list sources and their permission state
  check DOMAIN               re-run robots.txt and terms checks for a source
  discover [--targets N]     search for the N biggest gaps
  crawl DOMAIN               crawl a source for more documents (metadata only)
  extract [--limit N]        extract questions from permitted sources
  verify [--limit N]         run quality checks on unverified questions
  run                        one full autonomous cycle (all of the above)
  report [--json]            coverage report
  gaps                       list missing subject/year combinations
  export --out FILE [--verified-only] [--subject SLUG] [--year Y]
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.research import matrix, pipeline, reports
from apps.research.extraction.structure import to_record
from apps.research.models import PastQuestion, Source, SourceDocument


class Command(BaseCommand):
    help = "Past-question research pipeline"

    def add_arguments(self, p):
        p.add_argument("command", choices=["matrix", "seed", "sources", "check", "discover", "crawl", "extract", "verify",
                                           "run", "report", "gaps", "export"])
        p.add_argument("arg", nargs="?")
        p.add_argument("--exam", default="jamb")
        p.add_argument("--name", default="")
        p.add_argument("--status", default="")
        p.add_argument("--targets", type=int, default=None)
        p.add_argument("--limit", type=int, default=50)
        p.add_argument("--json", action="store_true")
        p.add_argument("--out", default="")
        p.add_argument("--verified-only", action="store_true")
        p.add_argument("--subject", default="")
        p.add_argument("--year", type=int, default=None)

    def out(self, data):
        self.stdout.write(json.dumps(data, indent=2, default=str) if not isinstance(data, str) else data)

    def handle(self, *a, **o):
        cmd = o["command"]
        if cmd == "matrix":
            return self.out(matrix.ensure_matrix(o["exam"]))
        if cmd == "seed":
            if not o["arg"]:
                raise CommandError("Give a URL")
            s = pipeline.add_seed(o["arg"], o["name"])
            return self.out(f"Seed added: {s.domain} (permission: {s.permission_status})")
        if cmd == "sources":
            qs = Source.objects.all().order_by("permission_status", "domain")
            if o["status"]:
                qs = qs.filter(permission_status=o["status"])
            for s in qs:
                n = s.documents.count()
                self.stdout.write(f"{s.permission_status:16} {s.domain:40} docs={n:<5} seed={s.is_seed} via={s.discovered_via}")
            return
        if cmd in ("check", "crawl"):
            s = Source.objects.filter(domain=(o["arg"] or "").removeprefix("www.")).first()
            if not s:
                raise CommandError("Unknown domain. Add it with: research seed https://DOMAIN/")
            return self.out(pipeline.check_source(s, force=True) if cmd == "check" else pipeline.crawl_source(s))
        if cmd == "discover":
            res = [pipeline.discover_target(t) for t in matrix.targets_needing_search(o["exam"], o["targets"] or 10)]
            return self.out({"targets_searched": len(res), "documents_recorded": sum(r.get("recorded", 0) for r in res),
                             "notes": sorted({r.get("note") for r in res if r.get("note")})})
        if cmd == "extract":
            docs = SourceDocument.objects.filter(status="discovered", source__permission_status__in=["permitted", "open_license"])[:o["limit"]]
            return self.out([{d.url: pipeline.extract_document(d)} for d in docs] or "No documents from permitted sources are waiting.")
        if cmd == "verify":
            return self.out(pipeline.verify_pending(o["limit"]))
        if cmd == "run":
            return self.out(pipeline.run_cycle(o["exam"], targets=o["targets"]))
        if cmd == "report":
            r = reports.coverage(o["exam"])
            if o["json"]:
                return self.out(r)
            t = r["totals"]
            self.stdout.write(self.style.MIGRATE_HEADING(f"Coverage — {o['exam'].upper()} {r['years'][0] if r['years'] else ''}–{r['years'][-1] if r['years'] else ''}"))
            for k, v in t.items():
                self.stdout.write(f"  {k.replace('_', ' '):38} {v}")
            self.stdout.write(self.style.MIGRATE_HEADING("Questions per subject"))
            for row in r["per_subject"]:
                self.stdout.write(f"  {row['subject']:36} {row['questions']:>6}  verified {row['verified']}")
            return
        if cmd == "gaps":
            for g in reports.coverage(o["exam"])["missing"]:
                self.stdout.write(f"{g['subject']:36} {g['year']}  {g['status']}")
            return
        if cmd == "export":
            if not o["out"]:
                raise CommandError("--out FILE is required")
            qs = PastQuestion.objects.filter(examination__code=o["exam"], duplicate_of__isnull=True).exclude(verification_status="rejected")
            if o["verified_only"]:
                qs = qs.filter(verification_status="verified")
            if o["subject"]:
                qs = qs.filter(subject__slug=o["subject"])
            if o["year"]:
                qs = qs.filter(year=o["year"])
            qs = qs.select_related("examination", "subject", "topic").prefetch_related("options", "answers", "explanations")
            records = [to_record(q) for q in qs]
            with open(o["out"], "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=1)
            return self.out(f"Wrote {len(records)} questions to {o['out']}")
