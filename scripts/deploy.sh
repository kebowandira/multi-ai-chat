#!/usr/bin/env bash
# Compile config, validate it, and (re)create every enabled container.
# `docker compose restart` alone does not reliably apply changed environment
# variables or mounted files, which is why this always recreates.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  echo "error: .env not found; run: python3 scripts/init-env.py" >&2
  exit 1
fi

python3 scripts/configure.py

if grep -qE '^COMPOSE_PROFILES=.*\bstandalone\b' .env; then
  echo "validating Caddy configuration (standalone profile active)..."
  docker compose run --rm --no-deps --entrypoint caddy caddy validate --config /etc/caddy/Caddyfile
else
  echo "standalone profile not active; skipping bundled Caddy (deploying behind an existing reverse proxy — see .env.example)."
fi

echo "pulling images..."
docker compose pull --quiet || true  # tolerate images already pinned to a digest with no pull needed

echo "starting services..."
docker compose up -d --remove-orphans

echo "waiting for health checks..."
deadline=$((SECONDS + 300))
while true; do
  unhealthy=$(docker compose ps --format '{{.Name}} {{.Health}}' 2>/dev/null | awk '$2!="" && $2!="healthy" {print}') || true
  if [ -z "$unhealthy" ]; then
    break
  fi
  if [ $SECONDS -ge $deadline ]; then
    echo "error: services did not become healthy within 5 minutes:" >&2
    echo "$unhealthy" >&2
    docker compose logs --tail 50
    exit 1
  fi
  sleep 5
done

echo "all services healthy."
docker compose ps
