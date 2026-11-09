# Deploying Kwado AI

- **Frontend** (`frontend/`) → Vercel
- **Backend** (`backend/`) → a VPS running Docker: Django API, Celery worker, Celery beat, PostgreSQL + pgvector, Redis, and Caddy for automatic HTTPS.

Example domains below: `yourdomain.com` (frontend) and `api.yourdomain.com` (backend). Replace them with yours.

---

## Part 1 — Backend on a VPS

### 1. Get a server
Ubuntu 24.04, **2 vCPU / 4 GB RAM** minimum (Hetzner, DigitalOcean, Contabo, AWS Lightsail…). Note its public IP.

### 2. Point DNS at it
At your domain registrar, add an **A record**: `api` → `<VPS IP>`. Wait until `ping api.yourdomain.com` shows the IP.

### 3. Secure the server and install Docker
SSH in as root, then:
```bash
apt update && apt -y upgrade
adduser kwado && usermod -aG sudo kwado          # day-to-day user
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
curl -fsSL https://get.docker.com | sh
usermod -aG docker kwado
```
Log out and SSH back in as `kwado`.

### 4. Get the code
```bash
sudo mkdir -p /opt/kwado && sudo chown kwado: /opt/kwado
git clone -b <your-branch> https://github.com/kwado-project/main-repo.git /opt/kwado
cd /opt/kwado
```
(For a private repo, add a read-only GitHub deploy key to the server first.)

### 5. Create the two config files
```bash
cp deploy/.env.example .env                                   # compose settings
cp deploy/backend.env.production.example backend/.env         # app settings
python3 -c "import secrets; print(secrets.token_urlsafe(50))"  # run twice: secret key + DB password
nano .env           # API_DOMAIN, POSTGRES_PASSWORD
nano backend/.env   # DJANGO_SECRET_KEY, your domains, and every service key
chmod 600 .env backend/.env
```
What `backend/.env` needs:

| Setting | Where to get it |
|---|---|
| `DJANGO_ALLOWED_HOSTS` | `api.yourdomain.com,localhost` (keep `localhost` — the health check uses it) |
| `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Your Vercel domain, e.g. `https://yourdomain.com` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | The Gmail address, and a Google **App Password** for it (see "Gmail App Password" below) |
| `R2_*` | Cloudflare → R2: create a **private** bucket and an API token with read/write on it |
| `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` | Paystack dashboard → Settings → API keys (use test keys first) |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `VOYAGE_API_KEY` | voyageai.com (embeddings for searching student notes) |

### 6. Start everything
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps        # api should become "healthy"
curl https://api.yourdomain.com/api/health/          # {"status": "ok"}
```
Caddy obtains the HTTPS certificate automatically on first start (needs DNS from step 2 and ports 80/443 open).

### 7. Load reference data and create your admin
```bash
docker compose -f docker-compose.prod.yml exec api python manage.py seed --admin you@yourdomain.com
```
This loads exams, subjects, credit packages, prices, badges and missions, plus **sample** questions and lessons (labelled as sample content). Then sign in on the website with that email; you'll see the Admin console in the menu.

### 8. Connect Paystack
Paystack dashboard → Settings → API Keys & Webhooks → Webhook URL:
`https://api.yourdomain.com/api/payments/webhooks/paystack/`

### 9. Turn on backups and housekeeping
```bash
crontab -e
```
Add:
```
17 2 * * * /opt/kwado/deploy/backup.sh >> /var/log/kwado-backup.log 2>&1
40 3 * * * cd /opt/kwado && docker compose -f docker-compose.prod.yml exec -T api python manage.py flushexpiredtokens
```
Backups are kept 14 days in `/var/backups/kwado`. Strongly recommended: also copy them off the server. Install `rclone`, run `rclone config` to add an R2 remote named `r2`, create a `kwado-backups` bucket, and `backup.sh` uploads automatically.

**Test a restore once** so you know it works:
```bash
gunzip -c /var/backups/kwado/<file>.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U kwado -d kwado
```

### Gmail App Password
1. Sign in to the Gmail account that will send the codes (a dedicated account such as `kwado.noreply@gmail.com` is best).
2. Google Account → **Security** → turn on **2-Step Verification** (App Passwords require it).
3. Visit https://myaccount.google.com/apppasswords, create one named "Kwado", and copy the 16-character password.
4. Put it in `backend/.env` as `EMAIL_HOST_PASSWORD` (spaces are fine), then `docker compose -f docker-compose.prod.yml up -d`.

Things to know:
- **Daily limit:** a personal Gmail account sends about **500 emails/day**; Google Workspace about **2,000/day**. Every sign-up and login sends one code, so plan to move to a dedicated email service (set `EMAIL_PROVIDER=ses`, or any SMTP provider such as Brevo, Mailgun or Postmark via `EMAIL_HOST`/`EMAIL_PORT`) before you outgrow it.
- **Blocked ports:** some VPS hosts block outbound SMTP on new accounts (DigitalOcean always; Hetzner until you ask support). If sends time out, ask your host to unblock port 587, or try `EMAIL_PORT=465`.
- **Sender address:** Gmail sends from the signed-in account. To show another address, add it in Gmail → Settings → Accounts → "Send mail as" first.

---

## Part 2 — Frontend on Vercel
1. Import the GitHub repo in Vercel. **Root Directory: `frontend`**.
2. Environment variable: `BACKEND_URL=https://api.yourdomain.com` (set it **before** deploying — it's baked in at build time).
3. Deploy, then add your domain (`yourdomain.com`) in Vercel → Domains.

The site calls `/api/...` on its own domain and Vercel forwards to the VPS, so the login cookie stays first-party. No CORS changes needed.

---

## Part 3 — Check it end to end
1. Register with a real email → the code arrives (from your Gmail account; check spam the first time).
2. Finish onboarding → you have 100 credits, then a roadmap.
3. Ask the AI tutor a question → the answer streams in.
4. Buy the Starter package with a Paystack **test card** → credits arrive, the receipt shows.
5. Upload a small PDF → it reaches "Ready".
When all pass, switch Paystack to live keys in `backend/.env` and restart (below).

---

## Day-to-day operations
```bash
cd /opt/kwado
C="docker compose -f docker-compose.prod.yml"

# Deploy an update (migrations run automatically on start)
git pull && $C up -d --build

# After editing backend/.env
$C up -d

# Logs
$C logs -f api        # or worker / beat / caddy

# Django shell / management commands
$C exec api python manage.py shell
```

## Scaling up
1. **First:** move Postgres to a managed service with backups (DigitalOcean, AWS RDS, Neon or Supabase, with pgvector enabled). Set `DATABASE_URL` in `backend/.env` and remove the `db` service.
2. Increase `API_WORKERS` / `WORKER_CONCURRENCY` in `.env`, or give the VPS more CPU.
3. Then run more API servers behind a load balancer. The API keeps no session state, so this needs no code changes. Add a read replica via `DATABASE_REPLICA_URL` and PgBouncer in front of Postgres.

## Troubleshooting
| Symptom | Check |
|---|---|
| No HTTPS / certificate error | DNS points at the VPS? Ports 80+443 open? `$C logs caddy` |
| `api` not healthy | `$C logs api` — usually a missing or invalid value in `backend/.env` |
| 400 Bad Request | Domain missing from `DJANGO_ALLOWED_HOSTS` |
| No OTP emails | `$C logs worker`. `535 Username and Password not accepted` → wrong or revoked App Password, or 2-Step Verification is off. Timeouts → your VPS host blocks outbound SMTP (see Gmail section) |
| Credits not added after payment | Webhook URL in Paystack; `$C logs api` for `/payments/` |
