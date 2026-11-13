#!/usr/bin/env bash
# Build and (re)start the NeoMortalSurv stack on the server.
#
# RUN BY THE OWNER, ON THE SERVER, from a checkout of this repository:
#
#     deploy/deploy.sh            # deploy the checked-out commit
#
# It never touches DNS, certbot or the Streamlit service; those steps are manual and
# described in docs/CUTOVER.md. Claude does not run this script.
set -euo pipefail

cd "$(dirname "$0")"
if [[ ! -f .env ]]; then
  echo "deploy/.env is missing. Copy .env.example to .env and edit it." >&2
  exit 1
fi
set -a; . ./.env; set +a

files=(-f docker-compose.yml)
if [[ "${LEGACY:-off}" == "on" ]]; then
  files+=(-f docker-compose.legacy.yml)
fi

accounts=off
if [[ "${ENABLE_ACCOUNTS:-false}" == "true" ]]; then
  accounts=on
  files+=(-f docker-compose.accounts.yml)
  if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    echo "ENABLE_ACCOUNTS=true needs POSTGRES_PASSWORD in deploy/.env." >&2
    exit 1
  fi
fi

echo "Commit:   $(git rev-parse --short HEAD) ($(git status --porcelain | wc -l | tr -d ' ') uncommitted changes)"
echo "New site: ${SITE_NEW}"
echo "Legacy:   ${LEGACY:-off} ${SITE_LEGACY:-}"
echo "Accounts: ${accounts}   (stored clinical data; needs the sign-off in docs/DECISIONS.md)"
read -r -p "Deploy this? [y/N] " answer
[[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "Cancelled."; exit 1; }

docker compose "${files[@]}" build
if [[ "$accounts" == "on" ]]; then
  docker compose "${files[@]}" up -d --wait db
  docker compose "${files[@]}" run --rm api python -m app.cli migrate
fi
docker compose "${files[@]}" up -d --wait --remove-orphans
docker compose "${files[@]}" ps

echo
echo "Health as seen inside the stack:"
docker compose "${files[@]}" exec -T api python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5).read().decode())"
echo
echo "Now check from outside: https://${SITE_NEW}/api/v1/health"
