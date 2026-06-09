Deployment Setup:


### GHCR publish (CI)
`.github/workflows/publish.yml` builds and pushes on every push to `main`:

| Image | Tag |
|-------|-----|
| `ghcr.io/<owner>/<repo>/api` | `latest`, branch, sha |
| `ghcr.io/<owner>/<repo>/worker` | same |
| `ghcr.io/<owner>/<repo>/frontend` | same (built with `NEXT_PUBLIC_API_URL=/api/v1`) |

### VPS deploy folder (`deploy/`)
Only this folder goes on the server — no repo clone:

```
deploy/
├── docker-compose.yml      # pulls from GHCR (no build)
├── .env.example
├── init-letsencrypt.sh     # nginx + certbot bootstrap
├── README.md
└── nginx/
    ├── nginx.conf
    └── conf.d/
        ├── app.conf.template          # HTTPS config
        └── app-http-only.conf.template # HTTP for ACME challenge
```

Stack: **redis → api → worker → frontend → nginx → certbot** (auto-renewal)

### Local dev
Root `docker-compose.yml` still **builds locally** for development.

---

## Your workflow

**1. Push to GitHub** → CI publishes images to GHCR

**2. On VPS** (copy only `deploy/`):

```bash
scp -r deploy/ user@your-vps:/opt/job-scheduler
ssh user@your-vps
cd /opt/job-scheduler
cp .env.example .env
```

**3. Edit `.env`:**

```env
GHCR_IMAGE_PREFIX=ghcr.io/your-username/hng14-stage9-job-scheduler
DOMAIN=yourname.duckdns.org
CERTBOT_EMAIL=you@example.com
```

**4. Bootstrap HTTPS + start:**

```bash
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh
docker compose up -d --scale worker=2
```

**5. Updates later:**

```bash
docker compose pull && docker compose up -d
```

---

## Notes

- **Private GHCR packages:** log in on the VPS with a PAT (`read:packages`).
- **Testing certs:** set `CERTBOT_STAGING=1` in `.env` to avoid Let's Encrypt rate limits.
- **Frontend API:** uses relative `/api/v1` in production (same domain via nginx).

Want me to commit these changes with conventional commits?