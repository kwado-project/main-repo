# Past-question research pipeline

Finds, extracts, checks and organises JAMB UTME past questions (2000–2026 by default) with
provenance and copyright status for every question. Lives in `backend/apps/research`.

## Ground rules (enforced in code)

| Rule | Where |
|---|---|
| robots.txt is checked before **every** request; a 401/403 on robots.txt means "disallow" | `discovery/compliance.py`, `fetch.py` |
| Search-engine result pages are never scraped — only official search APIs | `discovery/search.py` |
| Paywalls, logins and CAPTCHAs are never bypassed (no credentials, no CAPTCHA solving, honest User-Agent) | `fetch.py` |
| Discovery stores **metadata only** (URL, title, subject/year guess) | `discovery/crawler.py` |
| Question text is fetched and stored **only** for sources a person marked *Permitted* or *Open licence*, with evidence | `fetch.py` (`purpose="extraction"`), `api.py` |
| Automated checks can only make a source more restricted; they never grant permission or override a human decision | `discovery/compliance.py` |
| Answers and explanations are never invented; AI opinions are stored separately and never become the answer | `extraction/parser.py`, `quality/ai_review.py`, `extraction/structure.py` |
| Extracted text is never edited; every check and decision is an appended `VerificationRecord` | `quality/`, `review.py` |
| Nothing reaches students until a question is human-verified, rights-cleared and promoted — and then it enters the question bank as a **draft** for the normal answer-verification workflow | `promote.py` |

JAMB past questions are, in general, JAMB's copyright regardless of which website hosts them, and most
hosting sites' terms forbid copying. Expect most discovered sources to stay *Needs review* or
*Terms prohibit* until you obtain permission (from JAMB or the site owner).

## Architecture

```
research matrix (exam × subject × year)
   → discovery: search APIs + seed sites → same-site crawler → classifier → Source / SourceDocument
   → compliance: robots.txt · terms scan · rate limit · human permission gate
   → extraction (permitted only): HTML / PDF text layer / Tesseract OCR → parser → PastQuestion (+ options, answers, explanations)
   → quality: checks · duplicates · cross-source answers · confidence · optional AI review → VerificationRecord
   → human review (verify / reject) → promote to question bank as draft
   → coverage report · admin dashboard · JSON export
```

```
backend/apps/research/
  models.py        ExaminationYear, ResearchTarget, Source, CopyrightPermission, SourceDocument, ExtractionJob,
                   PastQuestion, PastQuestionOption, PastAnswer, PastExplanation, VerificationRecord
  matrix.py        research matrix, gaps
  discovery/       classify.py · queries.py · search.py · crawler.py · compliance.py
  fetch.py         polite fetcher (requests · Playwright · Firecrawl)
  extraction/      parser.py · html.py · pdf.py (+OCR) · structure.py (save + JSON export)
  quality/         checks.py · dedupe.py · ai_review.py
  jobs.py          idempotent, resumable job records
  pipeline.py      discover · check · crawl · extract · verify · run_cycle
  tasks.py         Celery tasks (queue "research")
  reports.py       coverage report
  review.py        human verify / reject
  promote.py       research question → question bank draft
  api.py, urls.py  /api/admin-api/research/...
  management/commands/research.py
frontend/src/app/admin/research/page.tsx   dashboard
```

Spec model names map as: Examination/Subject → `apps.examinations`; Question → `PastQuestion`;
QuestionOption → `PastQuestionOption`; Answer → `PastAnswer`; Explanation → `PastExplanation`.
They are separate from the live question bank on purpose.

## Setup (VPS)

1. Pull and rebuild: `git pull && docker compose -f docker-compose.prod.yml up -d --build`
   (adds the `research-worker` service and Tesseract OCR; migrations run automatically).
2. In `backend/.env`, add at least one search provider key (all optional, all used if set):
   `BRAVE_SEARCH_API_KEY`, or `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_CX`, or `SERPAPI_API_KEY`, or `FIRECRAWL_API_KEY`.
   Without any, only seed sites you add are crawled.
3. Make sure JAMB's subjects are linked (Admin → Exam rules), then build the matrix:
   `docker compose -f docker-compose.prod.yml exec api python manage.py research matrix`
4. Optional: `RESEARCH_AUTORUN=1` runs one cycle every hour; `RESEARCH_AI_REVIEW=1` adds an AI
   second opinion on answer keys (uses your AI provider, advisory only).

## Running it

| Task | Command (`docker compose -f docker-compose.prod.yml exec api python manage.py research …`) |
|---|---|
| One full cycle | `run` |
| Add a site to crawl | `seed https://example.com/` |
| List sources and permission state | `sources` |
| Search the 10 biggest gaps | `discover --targets 10` |
| Re-check robots.txt/terms | `check example.com` |
| Extract from permitted sources | `extract` |
| Quality checks | `verify` |
| Coverage report | `report` (or `report --json`) |
| Missing subject/year cells | `gaps` |
| Export JSON | `export --out /app/var/jamb.json [--verified-only] [--subject mathematics] [--year 2010]` |

Or use **Admin console → Past-question research**: run cycles, add seeds, record copyright decisions
(evidence required), review and verify questions, promote them, export JSON.

## Permission workflow

1. A source is discovered → robots.txt and terms are checked → *Needs review* / *Terms prohibit* / *robots.txt blocks*.
2. You contact the rights holder. When you have written permission (or confirm an open licence that allows
   your use), record it in the dashboard with the evidence and scope.
3. The next cycle extracts that source's documents. Questions get `rights_status = cleared`.
4. If permission is later refused or withdrawn, record *Denied*: its questions become `rights_status = denied`
   and can't be promoted.

## Coverage numbers

Counts exclude duplicates and rejected questions. A subject/year cell is *Not found* only after
`RESEARCH_MAX_SEARCH_ATTEMPTS` searches (default 4, at least `RESEARCH_SEARCH_AGAIN_AFTER_DAYS` apart);
that is evidence nothing was found by the configured providers, not proof the paper doesn't exist.
