# VPS Deployment

Deploy using **only this folder** — no git clone required on the server.

Images are pulled from GitHub Container Registry (GHCR), built by CI on push to `main`.

## Prerequisites

- VPS with Docker and Docker Compose v2
- Domain pointing to the VPS public IP (DuckDNS, No-IP, etc.)
- GHCR packages published (push to `main` triggers `.github/workflows/publish.yml`)
- If packages are **private**, log in on the VPS:

```bash
echo YOUR_GITHUB_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

## Quick Deploy

```bash
# 1. Copy deploy/ folder to VPS
scp -r deploy/ user@your-vps:/opt/job-scheduler

# 2. On the VPS
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
