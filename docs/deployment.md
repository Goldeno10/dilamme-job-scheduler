# Deployment Guide

## Overview

| Environment | Compose file | Images |
|-------------|--------------|--------|
| Local dev | `docker-compose.yml` (repo root) | Built locally |
| VPS production | `deploy/docker-compose.yml` | Pulled from GHCR |

CI publishes images to GHCR on every push to `main` (`.github/workflows/publish.yml`):

- `ghcr.io/<owner>/<repo>/api:latest`
- `ghcr.io/<owner>/<repo>/worker:latest`
- `ghcr.io/<owner>/<repo>/frontend:latest`

## 1. Enable GHCR

After pushing to GitHub, images appear under **Packages** on your repo/profile.

If packages are private, create a GitHub PAT with `read:packages` and log in on the VPS:

```bash
echo YOUR_PAT | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

Make packages public (optional): Package → Package settings → Change visibility.

## 2. VPS Setup

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
# re-login
```

Point your domain (DuckDNS, No-IP, etc.) to the VPS public IP.

## 3. Deploy (compose only)

Copy **only** the `deploy/` folder to the server:

```bash
scp -r deploy/ user@your-vps:/opt/job-scheduler
ssh user@your-vps
cd /opt/job-scheduler
cp .env.example .env
nano .env   # set GHCR_IMAGE_PREFIX, DOMAIN, CERTBOT_EMAIL
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh
docker compose up -d --scale worker=2
```

## 4. HTTPS (Nginx + Certbot in Docker)

The init script:

1. Renders HTTP-only nginx config (ACME webroot)
2. Starts app stack + nginx
3. Runs certbot `certonly` via webroot challenge
4. Switches nginx to HTTPS config and reloads
5. Starts certbot renewal container (auto-renew every 12h)

Set `CERTBOT_STAGING=1` in `.env` while testing to avoid rate limits.

## 5. Updates

```bash
cd /opt/job-scheduler
docker compose pull
docker compose up -d
```

## 6. Verify

- `https://YOUR_DOMAIN/` — UI
- `https://YOUR_DOMAIN/api/v1/stats` — API
- `https://YOUR_DOMAIN/docs` — Swagger

See also `deploy/README.md`.
