# Deployment Setup

Full deployment documentation: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**

Quick start:

1. Push to `main` → CI publishes images to GHCR
2. Copy `deploy/` to VPS → configure `.env` → run `./init-letsencrypt.sh`
3. App live at `https://YOUR_DOMAIN/`
