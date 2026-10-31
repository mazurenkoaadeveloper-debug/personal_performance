#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "Docker Compose is required" >&2
  exit 1
fi

project="${GITLAB_TEST_PROJECT:-personal-performance-gitlab-test}"
"${compose[@]}" -f compose.yaml -f compose.gitlab-integration.yaml \
  -p "$project" --profile gitlab-integration down
