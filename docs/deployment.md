# Deployment Guide

Manual VPS deployment with Nginx, HTTPS, and dynamic DNS.

## 1. Server Setup

```bash
# On Ubuntu VPS
sudo apt update && sudo apt install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx
sudo usermod -aG docker $USER
```

## 2. Clone & Configure

```bash
git clone <your-repo> /opt/job-scheduler
cd /opt/job-scheduler
```

Set environment in `docker-compose.yml` or `.env`:
- `NEXT_PUBLIC_API_URL=https://your-domain.duckdns.org/api/v1`

## 3. Start Services

```bash
docker compose up -d --build
```

## 4. Dynamic DNS

Register with [DuckDNS](https://www.duckdns.org/) or No-IP. Point your subdomain to the VPS public IP.

## 5. Nginx + HTTPS

```bash
sudo cp nginx/nginx.conf /etc/nginx/sites-available/scheduler
# Edit server_name and SSL paths
sudo ln -s /etc/nginx/sites-available/scheduler /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.duckdns.org
sudo nginx -t && sudo systemctl reload nginx
```

Update `nginx.conf`:
- Replace `scheduler.example.com` with your domain
- API routes proxy to `127.0.0.1:8000`
- Frontend proxies to `127.0.0.1:3000`

## 6. Verify

- `https://your-domain.duckdns.org` — UI
- `https://your-domain.duckdns.org/api/v1/stats` — API
- `https://your-domain.duckdns.org/docs` — Swagger
