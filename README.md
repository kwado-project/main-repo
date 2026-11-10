# Kwado AI — Learn. Play. Practise. Pass.

An AI-powered, gamified exam-preparation platform for Nigerian students (JAMB, WAEC, NECO, GCE, NABTEB, Post-UTME).

```
frontend/   Next.js 15 · TypeScript · Tailwind · Framer Motion · Lucide · RHF + Zod · Recharts · KaTeX
backend/    Django 5.2 · DRF · PostgreSQL + pgvector · Redis · Celery · Claude · Paystack · Resend · Cloudflare R2
```

## Run it locally

```bash
# Postgres 16 (with pgvector) + Redis running locally, or: docker compose up
cd backend
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env            # DJANGO_DEBUG=1, CELERY_TASK_ALWAYS_EAGER=1 for dev
python manage.py migrate
python manage.py seed --admin you@example.com
python manage.py runserver

cd ../frontend && npm install && npm run dev   # http://localhost:3000 (proxies /api to :8000)
pytest                                          # in backend/: 22 tests
```

### Development boundaries (never active in production)
| Service | Without credentials (dev) | Production |
|---|---|---|
| Email OTP | Code logged and shown on the OTP screen in a labelled "Development mode" box | Resend (`EMAIL_PROVIDER=resend`); AWS SES or any SMTP server optional |
| Payments | Labelled sandbox page that approves/declines (requires `DEBUG` **and** no Paystack key) | Paystack checkout + server verification + signed webhooks |
| AI tutor | Placeholder answer prefixed "Development mode", badge in UI | Anthropic Claude (`ANTHROPIC_API_KEY`, default `claude-opus-5-5`) or OpenAI (`OPENAI_API_KEY`, default `gpt-5.5`). Anthropic wins if both are set; `AI_PROVIDER` forces one |
| Embeddings | Hashed bag-of-words vectors | Voyage AI (`VOYAGE_API_KEY`), else OpenAI embeddings |
| File storage | Local disk under `backend/var/` | Cloudflare R2, private bucket, presigned URLs |

## Architecture

Modular monolith (`backend/apps/*`): `accounts` (users, profiles, email OTP), `examinations` (exams, subjects, topics, rules, student exam profiles), `questions` (bank + review workflow), `assessments` (quiz engine, mastery), `learning` (lessons, learning paths), `gamification` (XP, levels, streaks, badges, missions, leaderboards), `wallet` (ledger, packages, activity pricing), `payments` (Paystack), `referrals`, `ai_tutor`, `roadmaps`, `materials` (uploads + RAG), `notifications`, `analytics` (admin API), `core` (audit log, settings, provider boundaries).

### Money and integrity guarantees
- **Wallet**: append-only `CreditTransaction` ledger; every change runs in `transaction.atomic()` with `SELECT … FOR UPDATE` on the wallet; unique idempotency keys; a DB `CHECK (balance >= 0)`. Tested under 8 concurrent threads.
- **Paid activities** hold credits first and refund automatically on any failure (`paid_activity`). AI streams are refunded if they fail, are refused, or the client disconnects.
- **Payments**: credits are awarded only after the backend calls Paystack's verify API and matches reference, amount and currency. Webhooks are HMAC-SHA512 verified, de-duplicated and re-verified; refunds/chargebacks reverse credits and referral rewards.
- **Referrals**: 20% of purchased credits, bound at signup, self-referral blocked (code + DB constraint), one reward per payment, promotional credits excluded.
- **Signup bonus**: exactly 100 credits, once per account and once per canonical email (Gmail dots/`+tags` collapsed).
- **Marking** uses only human-verified `AnswerKey`s; publishing needs a verified key and a second reviewer. AI never marks questions.
- **OTP**: 6 digits, HMAC-hashed at rest, 5-minute expiry, single use, 5 attempts, 60s resend cooldown, IP throttles, identical responses for known and unknown emails.
- **Sessions**: 15-minute JWT access token in memory; rotating, blacklistable refresh token in an httpOnly cookie on a same-origin `/api` proxy.

### Built for 1M+ students
- Stateless API → scale gunicorn (gthread) horizontally behind a load balancer; Celery workers on separate `email` and `ai` queues.
- PostgreSQL behind PgBouncer; optional read replica (`DATABASE_REPLICA_URL`) for catalogue, leaderboards and analytics. Indexes on every hot path; cursor pagination on the ledger.
- Redis: cache, throttles, Celery broker, and leaderboards as sorted sets (DB fallback).
- Question pools cached per subject/topic and sampled in Python (no `ORDER BY random()`).
- Roadmaps generated in rolling 28-day windows to keep the task table small.
- AI cost control: per-purpose model/effort/max-token routing (admin-editable), prompt caching of the tutor system prompt, per-student daily caps, rate limits, usage tracking.
- Frontend: tree-shaken icons, code-split routes, KaTeX loaded only where maths is shown; reduced-motion respected.

## Production checklist
Set `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `EMAIL_PROVIDER=resend` + `RESEND_API_KEY` and `DEFAULT_FROM_EMAIL` on a domain verified in Resend, `STORAGE_PROVIDER=r2` + R2 keys, `PAYSTACK_SECRET_KEY` (webhook URL `https://<api>/api/payments/webhooks/paystack/`), `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY`, optionally `VOYAGE_API_KEY`. Run `celery worker` and `celery beat`. Enable daily Postgres backups/PITR, run `python manage.py flushexpiredtokens` daily, and complete an NDPA data-protection review.

The bundled questions and lessons are **original sample content**, labelled as such. Load authorised examination material through the admin question-bank workflow.
