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
timeout="${GITLAB_TEST_READY_TIMEOUT:-1200}"
port="${GITLAB_TEST_HTTP_PORT:-8929}"

case "$timeout" in
  ''|*[!0-9]*) echo "GITLAB_TEST_READY_TIMEOUT must be an integer" >&2; exit 2 ;;
esac

compose_args=(-f compose.yaml -f compose.gitlab-integration.yaml -p "$project" --profile gitlab-integration)
"${compose[@]}" "${compose_args[@]}" up -d --wait --wait-timeout "$timeout" gitlab

version="$("${compose[@]}" "${compose_args[@]}" exec -T gitlab cat /opt/gitlab/embedded/service/gitlab-rails/VERSION)"
if [[ "$version" != "19.3.6-ee" ]]; then
  echo "Expected GitLab 19.3.6-ee, got $version" >&2
  exit 1
fi

curl --fail --silent --show-error "http://127.0.0.1:${port}/users/sign_in" >/dev/null
echo "GitLab test server is ready at http://127.0.0.1:${port}"
