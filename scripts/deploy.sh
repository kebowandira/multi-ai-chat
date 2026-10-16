#!/usr/bin/env bash
# Compile config, validate it, and (re)create every enabled container.
# `docker compose restart` alone does not reliably apply changed environment
# variables or mounted files, which is why `--force-recreate` is used.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  echo "error: .env not found; run: python3 scripts/init-env.py" >&2
  exit 1
fi

python3 scripts/preflight.py
python3 scripts/configure.py

echo "validating Compose configuration..."
docker compose config -q

expected_init_services=$(docker compose config --services 2>/dev/null || true)
if echo "$expected_init_services" | grep -qw "caddy"; then
  echo "validating Caddy configuration (standalone profile active)..."
  docker compose run --rm --no-deps --entrypoint caddy caddy validate --config /etc/caddy/Caddyfile
else
  echo "standalone profile not active; skipping bundled Caddy."
fi

echo "pulling images..."
docker compose pull --quiet

echo "starting services..."
docker compose up -d --force-recreate --remove-orphans

echo "waiting for health checks..."
timeout_sec="${DEPLOY_TIMEOUT_SEC:-300}"
deadline=$((SECONDS + timeout_sec))
sleep_sec="${DEPLOY_SLEEP_SEC:-5}"

while true; do
  expected_services=$(docker compose config --services 2>/dev/null) || {
    echo "error: failed to query docker compose services" >&2
    exit 1
  }

  if [ -z "${expected_services//[[:space:]]/}" ]; then
    echo "error: no expected services found in active Compose profile configuration" >&2
    exit 1
  fi

  status_output=$(docker compose ps --all --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null) || {
    echo "error: failed to query docker compose container states" >&2
    exit 1
  }

  not_ready=""
  for service in $expected_services; do
    srv_line=$(echo "$status_output" | awk -v s="$service" '$1==s {print $0; exit}')
    if [ -z "$srv_line" ]; then
      not_ready="${not_ready}service '$service': missing/not created\n"
      continue
    fi
    state=$(echo "$srv_line" | awk '{print $2}')
    health=$(echo "$srv_line" | awk '{print $3}')

    if [ "$state" != "running" ]; then
      not_ready="${not_ready}service '$service': state=$state\n"
    elif [ -n "$health" ] && [ "$health" != "healthy" ]; then
      not_ready="${not_ready}service '$service': health=$health\n"
    fi
  done

  if [ -z "$not_ready" ]; then
    break
  fi

  if [ $SECONDS -ge $deadline ]; then
    echo "error: services did not become ready within deadline:" >&2
    printf "%b" "$not_ready" >&2
    exit 1
  fi
  sleep "$sleep_sec"
done

echo "all services healthy."
docker compose ps
