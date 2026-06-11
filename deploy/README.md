# VPS Deployment

Deploy using **only this folder** — no git clone required on the server.

Images are pulled from GitHub Container Registry (GHCR), built by CI on push to `main`.

## Prerequisites

- VPS with Docker and Docker Compose v2
- Domain pointing to the VPS public IP (DuckDNS, No-IP, etc.)
- GHCR packages published (push to `main` triggers `.github/workflows/publish.yml`)
- `GHCR_IMAGE_PREFIX` must match your GitHub repo: `ghcr.io/<owner>/<repo-name>`
- If packages are **private**, log in on the VPS before pulling:

```bash
echo YOUR_GITHUB_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

PAT needs the `read:packages` scope. Create one at GitHub → Settings → Developer settings → Personal access tokens.

**Or make packages public:** GitHub → Your profile → Packages → select package → Package settings → Change visibility → Public.

### GHCR pull denied?

1. Fix image prefix in `.env` (must match repo name, e.g. `dilamme-job-scheduler` not `hng14-stage9-job-scheduler`)
2. Run `docker login ghcr.io` on the VPS (see above)
3. Confirm images exist: GitHub repo → Packages (right sidebar)
4. Test pull: `docker pull ghcr.io/goldeno10/dilamme-job-scheduler/api:latest`

## Quick Deploy

```bash
# 1. Create target dir on VPS (/opt requires sudo)
ssh -i your-key.pem ubuntu@YOUR_VPS_IP \
  "sudo mkdir -p /opt/job-scheduler && sudo chown ubuntu:ubuntu /opt/job-scheduler"

# 2. Copy deploy/ folder to VPS
scp -i your-key.pem -r deploy/. ubuntu@YOUR_VPS_IP:/opt/job-scheduler/

# Alternative: copy to home directory (no sudo needed)
# scp -i your-key.pem -r deploy/ ubuntu@YOUR_VPS_IP:~/job-scheduler

# 3. On the VPS
cd /opt/job-scheduler
cp .env.example .env
# Edit .env — set GHCR_IMAGE_PREFIX, DOMAIN, CERTBOT_EMAIL

chmod +x init-letsencrypt.sh
./init-letsencrypt.sh

# 3. Scale workers (optional)
docker compose up -d --scale worker=2
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GHCR_IMAGE_PREFIX` | e.g. `ghcr.io/username/hng14-stage9-job-scheduler` |
| `IMAGE_TAG` | `latest` or commit SHA from CI |
| `DOMAIN` | Public domain for HTTPS |
| `CERTBOT_EMAIL` | Email for Let's Encrypt notifications |

## Updates

When CI publishes new images:

```bash
cd /opt/job-scheduler
docker compose pull
docker compose up -d
```

## Verify

- `https://YOUR_DOMAIN/` — UI
- `https://YOUR_DOMAIN/api/v1/stats` — API
- `https://YOUR_DOMAIN/docs` — Swagger

## Reset Redis (start fresh)

Clears all jobs, queues, DLQ entries, and locks. Use before a clean demo or after running the benchmark (which also flushes Redis).

```bash
cd /opt/job-scheduler
chmod +x reset-redis.sh

# Option 1 — flush keys only (quick, stack keeps running)
./reset-redis.sh flush

# Option 2 — delete Redis volume and restart entire stack
./reset-redis.sh full
```

One-liner without the script:

```bash
docker compose exec redis redis-cli FLUSHDB
```

**Warning:** Do not run `/api/v1/benchmark/run` on production unless you intend to wipe Redis — the benchmark calls `FLUSHDB` internally.
