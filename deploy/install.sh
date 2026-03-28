#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_TEMPLATE="${SCRIPT_DIR}/.env.example"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

command="${1:-install}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

random_hex() {
  local bytes="${1:-16}"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "${bytes}"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import secrets; print(secrets.token_hex(${bytes}))"
    return
  fi

  echo "Neither openssl nor python3 is available for secret generation." >&2
  exit 1
}

upsert_env() {
  local key="$1"
  local value="$2"

  if grep -qE "^${key}=" "${ENV_FILE}"; then
    sed -i.bak "s|^${key}=.*$|${key}=${value}|" "${ENV_FILE}"
    rm -f "${ENV_FILE}.bak"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

read_env() {
  local key="$1"
  grep -E "^${key}=" "${ENV_FILE}" | head -n 1 | cut -d'=' -f2-
}

docker_compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

wait_for_api() {
  local attempts=0
  local max_attempts=60

  until docker_compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9999/health', timeout=3)" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "${attempts}" -ge "${max_attempts}" ]; then
      echo "API service did not become ready in time." >&2
      return 1
    fi
    sleep 2
  done
}

prepare_env() {
  if [ ! -f "${ENV_FILE}" ]; then
    cp "${ENV_TEMPLATE}" "${ENV_FILE}"
    echo "Created ${ENV_FILE}"
  fi

  if [ "$(read_env SECRET_KEY)" = "replace_with_a_secure_random_64_char_secret_key" ]; then
    upsert_env SECRET_KEY "$(random_hex 32)"
  fi

  if [ "$(read_env POSTGRES_PASSWORD)" = "change_me" ]; then
    local db_password
    db_password="$(random_hex 16)"
    upsert_env POSTGRES_PASSWORD "${db_password}"
  fi

  if [ -z "$(read_env INITIAL_ADMIN_PASSWORD)" ]; then
    local admin_password
    admin_password="Admin@$(random_hex 6)"
    upsert_env INITIAL_ADMIN_PASSWORD "${admin_password}"
  fi
}

print_summary() {
  local bind_host app_port admin_user admin_password
  bind_host="$(read_env BIND_HOST)"
  app_port="$(read_env APP_PORT)"
  admin_user="$(read_env INITIAL_ADMIN_USERNAME)"
  admin_password="$(read_env INITIAL_ADMIN_PASSWORD)"

  echo
  echo "React FastAPI Admin is ready."
  echo "URL: http://${bind_host}:${app_port}"
  echo "Admin username: ${admin_user}"
  echo "Admin password: ${admin_password}"
  echo
}

install() {
  require_command docker
  prepare_env

  docker_compose up -d --build
  wait_for_api
  docker_compose exec -T api python -m app bootstrap
  print_summary
}

upgrade() {
  require_command docker

  if [ ! -f "${ENV_FILE}" ]; then
    echo "Missing ${ENV_FILE}. Run ./install.sh first." >&2
    exit 1
  fi

  docker_compose up -d --build
  wait_for_api
  docker_compose exec -T api python -m app db upgrade
}

logs() {
  require_command docker
  docker_compose logs -f api
}

down() {
  require_command docker
  docker_compose down
}

case "${command}" in
  install)
    install
    ;;
  upgrade)
    upgrade
    ;;
  logs)
    logs
    ;;
  down)
    down
    ;;
  *)
    echo "Usage: $0 [install|upgrade|logs|down]" >&2
    exit 1
    ;;
esac
