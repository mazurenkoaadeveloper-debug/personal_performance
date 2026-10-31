# GitLab developer activity analytics

## Local GitLab for development tests

The separate integration profile runs GitLab EE `19.3.6-ee.0` without adding it to the normal application startup. Start it before work on subsequent tasks:

```bash
scripts/gitlab-integration/start.sh
```

The server is available at `http://127.0.0.1:8929` by default. To change the host port or readiness timeout, export `GITLAB_TEST_HTTP_PORT` or `GITLAB_TEST_READY_TIMEOUT` before running the script; see `.env.gitlab-integration.example`. The first startup downloads a large image and may take several minutes. The server uses persistent, test-only Docker volumes so later tasks can reuse it. No real GitLab token or corporate data is needed.

Stop the test server with `scripts/gitlab-integration/stop.sh`. This preserves its volumes. The normal `docker compose up` does not start GitLab.

The full deterministic seed and live sync tests are tracked in [Issue #17](https://github.com/mazurenkoaadeveloper-debug/personal_performance/issues/17). Until the GitLab client and sync modules exist, subsequent tasks can run the local server as a readiness and API compatibility fixture; each task should add focused live checks for the behavior it implements.

Repository-local agent workflows are installed in `.agents/skills/` and configured by `AGENTS.md`. Source revisions are pinned in `.agents/skills.lock.json`.
