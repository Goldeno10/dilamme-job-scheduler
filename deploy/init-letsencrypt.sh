#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example to .env and configure it."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${DOMAIN:?DOMAIN is required in .env}"
: "${CERTBOT_EMAIL:?CERTBOT_EMAIL is required in .env}"

STAGING_ARG=""
if [[ "${CERTBOT_STAGING:-0}" == "1" ]]; then
  STAGING_ARG="--staging"
  echo "Using Let's Encrypt staging environment."
fi

render() {
  sed "s/\${DOMAIN}/${DOMAIN}/g" "$1" > "$2"
}

echo "==> Rendering nginx config (HTTP-only for certificate issuance)"
render nginx/conf.d/app-http-only.conf.template nginx/conf.d/app.conf

echo "==> Starting core services"
docker compose up -d redis api worker frontend nginx

echo "==> Requesting certificate for ${DOMAIN}"
docker compose run --rm --entrypoint certbot certbot certonly --webroot \
  -w /var/www/certbot \
  -d "${DOMAIN}" \
  --email "${CERTBOT_EMAIL}" \
  --agree-tos \
  --no-eff-email \
  ${STAGING_ARG}

echo "==> Rendering nginx config (HTTPS)"
render nginx/conf.d/app.conf.template nginx/conf.d/app.conf

echo "==> Reloading nginx"
docker compose exec nginx nginx -s reload

echo "==> Starting certbot renewal loop"
docker compose up -d certbot

echo ""
echo "Done. Your app should be available at https://${DOMAIN}"
echo "To scale workers: docker compose up -d --scale worker=2"
