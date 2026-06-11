#!/usr/bin/env bash
# Wipe Redis job data and start with an empty queue.
# Run from the deploy/ directory on your VPS.
set -euo pipefail

cd "$(dirname "$0")"

MODE="${1:-flush}"

case "$MODE" in
  flush)
    echo "==> Flushing Redis database (jobs, queues, locks, events)"
    echo "    API and workers can stay running."
    docker compose exec redis redis-cli FLUSHDB
    echo "==> Done. Dashboard should show zero jobs."
    ;;
  full)
    echo "==> Full reset: stop stack, delete Redis volume, restart"
    read -r -p "This removes ALL jobs and Redis persistence. Continue? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
      echo "Aborted."
      exit 0
    fi
    docker compose down
    docker volume rm job-scheduler_redis_data 2>/dev/null || docker volume rm deploy_redis_data 2>/dev/null || true
    docker compose up -d
    echo "==> Stack restarted with empty Redis."
    ;;
  *)
    echo "Usage: $0 [flush|full]"
    echo ""
    echo "  flush  Clear all keys in Redis (default). Fast, keeps containers running."
    echo "  full   Stop compose, delete redis_data volume, start fresh."
    exit 1
    ;;
esac
