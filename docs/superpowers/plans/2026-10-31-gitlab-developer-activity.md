# GitLab Developer Activity Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal web application that synchronizes the latest 12 months from GitLab `19.3.6-ee` and provides sortable user activity reports and detailed per-user contribution views.

**Architecture:** A modular Python monolith runs as separate FastAPI and dedicated synchronization-worker processes over one PostgreSQL database. A React SPA queries report-ready APIs; all filters run against PostgreSQL, while the GitLab token and raw diffs remain server-side and transient.

**Tech Stack:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, httpx, pytest; TypeScript, React, Vite, React Router, TanStack Query, TanStack Table, Material UI, Apache ECharts, Vitest, Testing Library, Playwright; Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-31-gitlab-developer-activity-design.md`

## Global Constraints

- Target exactly GitLab `19.3.6-ee`; fail visibly when required capabilities are unavailable.
- Run entirely inside the corporate network with no external telemetry or cloud services.
- Retain only the latest rolling 12 months, while retaining older object metadata only when needed to interpret in-window activity or current open MRs.
- Never persist source code or raw diff bodies; persist only normalized metadata and file-level statistics.
- Never store, log, return or expose the GitLab token; accept it only through environment configuration or a Docker secret.
- Use PostgreSQL for durable sync jobs and report data; do not add Celery, Redis or webhooks.
- Keep rankings, scores, anomaly detection, Jira, Confluence, authentication and SSO out of this iteration.
- Distinguish zero activity, unavailable data and not-yet-synchronized data in backend schemas and UI copy.
- Interpret report boundaries in the configured IANA timezone, default `Europe/Moscow`, and persist timestamps in UTC.
- Use TDD for every task and commit only after the named focused tests and the relevant broader suite pass.

## Review Focus

- GitLab returns `401`, `403`, missing pagination totals or partial endpoint data: show unavailable/coverage warnings and never convert these cases into zero activity (Task 3 tests).
- A squash/merge/direct-commit combination refers to the same accepted change: count it once and retain correct source drill-down (Task 6 tests).
- A generated, vendored, binary or repository-specific excluded file appears in a diff: exclude its line counts, record the reason and never persist raw diff text (Task 7 tests).
- A user selects a repository and arbitrary timezone-aware interval boundary: apply identical filters to list, card, timeline and source facts, including DST/local-midnight boundaries (Tasks 8 and 9 tests).
- A synchronization process crashes after partial writes: keep the previous successful report watermark visible, expire the lease and complete a retry idempotently (Task 4 tests).

---

## Planned file structure

```text
backend/
  pyproject.toml
  alembic.ini
  app/
    main.py
    core/{config.py,database.py,logging.py}
    gitlab/{client.py,schemas.py}
    sync/{models.py,repository.py,service.py,routes.py,worker.py}
    activity/{models.py,identity.py,ingestion.py,diff_stats.py}
    reports/{schemas.py,queries.py,routes.py,time.py}
  migrations/{env.py,versions/0001_initial_schema.py}
  tests/{conftest.py,core/,gitlab/,sync/,activity/,reports/}
frontend/
  package.json
  vite.config.ts
  src/
    main.tsx
    app/{App.tsx,router.tsx,theme.ts}
    api/{client.ts,types.ts}
    features/sync/{SyncPage.tsx,useSyncJob.ts}
    features/reports/{ReportFilters.tsx,UsersPage.tsx,UsersTable.tsx,useReportFilters.ts}
    features/user/{UserPage.tsx,SummaryCards.tsx,ActivityTimeline.tsx,RepositoryContribution.tsx,SourceFacts.tsx}
    test/{setup.ts,fixtures.ts}
  tests/report-flow.spec.ts
compose.yaml
.env.example
README.md
```

Files are grouped by responsibility. Route modules translate HTTP only; GitLab DTOs remain in `gitlab`; normalized facts remain in `activity`; SQL aggregation remains in `reports`.

### Task 1: Runnable application skeleton and typed configuration

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/core/test_config.py`
- Create: `backend/tests/test_health.py`
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/app/theme.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/app/App.test.tsx`
- Create: `compose.yaml`
- Create: `.env.example`

**Interfaces:**
- Produces: `Settings` with `gitlab_base_url: AnyHttpUrl`, `gitlab_token: SecretStr`, `database_url: str`, `report_timezone: str = "Europe/Moscow"`, `retention_days: int = 365`, `gitlab_project_ids: tuple[int, ...]`.
- Produces: `get_settings() -> Settings`, `get_session() -> AsyncIterator[AsyncSession]`, `create_app() -> FastAPI` and `GET /api/health -> {"status": "ok"}`.
- Produces: Compose services named `frontend`, `api`, `sync-worker`, and `postgres`; the worker command may initially exit with a clear “not implemented” status until Task 4.

- [ ] **Step 1: Write failing backend configuration and health tests**

Assert that `Settings` rejects a missing token/project list, accepts `Europe/Moscow`, represents the token as a secret, and that `/api/health` returns exactly `{"status": "ok"}` without configuration secrets.

- [ ] **Step 2: Run backend tests and verify failure**

Run: `cd backend && pytest tests/core/test_config.py tests/test_health.py -v`

Expected: FAIL because `app.core.config` and `create_app` do not exist.

- [ ] **Step 3: Implement the backend skeleton**

Implement the interfaces above. Configure structured stdout logs with an authorization/token redaction filter and an async SQLAlchemy session factory; do not create feature routes yet.

- [ ] **Step 4: Write and run the failing frontend shell test**

Assert that `<App />` renders the product title and navigation placeholders for “Developers” and “Synchronization”.

Run: `cd frontend && npm test -- --run src/app/App.test.tsx`

Expected: FAIL before the React shell exists.

- [ ] **Step 5: Implement the React shell and Compose wiring**

Create the Material UI theme and application shell. Configure Vite’s development proxy for `/api`; configure Compose health checks and expose only frontend/API ports, not PostgreSQL.

- [ ] **Step 6: Verify the task**

Run: `cd backend && pytest tests/core/test_config.py tests/test_health.py -v`

Run: `cd frontend && npm test -- --run src/app/App.test.tsx`

Run: `docker compose config --quiet`

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add backend frontend compose.yaml .env.example
git commit -m "feat: scaffold activity analytics application"
```

### Task 2: PostgreSQL domain schema and migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_initial_schema.py`
- Create: `backend/app/sync/models.py`
- Create: `backend/app/activity/models.py`
- Create: `backend/tests/core/test_migrations.py`
- Create: `backend/tests/activity/test_model_constraints.py`

**Interfaces:**
- Produces SQLAlchemy models: `Repository`, `User`, `UserAlias`, `MergeRequest`, `Commit`, `Review`, `Approval`, `FileChange`, `SyncJob`, `SyncProjectStatus`, `AppConfig`.
- Stable source keys: repository GitLab ID; `(repository_id, iid)` for MRs; `(repository_id, sha)` for commits; deterministic source-event keys for reviews/approvals/file changes.
- `SyncJob` states: `pending`, `running`, `succeeded`, `failed`; stores lease expiry, progress, warnings, error summary, timestamps, and report watermark candidate.

- [ ] **Step 1: Write failing migration and constraint tests**

Test migration upgrade from an empty PostgreSQL database, uniqueness of GitLab source keys, UTC-aware timestamps, JSON warning/progress fields, and rejection of a second active sync job by a partial unique index.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/core/test_migrations.py tests/activity/test_model_constraints.py -v`

Expected: FAIL because migrations and models do not exist.

- [ ] **Step 3: Implement the schema and initial migration**

Use PostgreSQL enums/check constraints where they make invalid states impossible. Store no diff body or code-content column. Add indexes for `(user_id, event_time)`, `(repository_id, event_time)`, MR timestamps/state, and sync-job state/lease.

- [ ] **Step 4: Verify migration round-trip and constraints**

Run: `cd backend && pytest tests/core/test_migrations.py tests/activity/test_model_constraints.py -v`

Expected: PASS, including upgrade, downgrade, and upgrade again.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/migrations backend/app/sync/models.py backend/app/activity/models.py backend/tests
git commit -m "feat: add activity data schema"
```

### Task 3: GitLab 19.3.6-ee client and capability validation

**Files:**
- Create: `backend/app/gitlab/__init__.py`
- Create: `backend/app/gitlab/schemas.py`
- Create: `backend/app/gitlab/client.py`
- Create: `backend/tests/gitlab/test_client.py`
- Create: `backend/tests/gitlab/fixtures/`

**Interfaces:**
- Produces: `GitLabClient(base_url: str, token: SecretStr, transport: httpx.AsyncBaseTransport | None = None)`.
- Produces: `get_version() -> GitLabVersion`, `validate_capabilities() -> CapabilityReport`, `iter_active_users()`, `iter_projects(project_ids)`, `iter_merge_requests(project_id, updated_after)`, `iter_commits(project_id, ref, since)`, `iter_discussions(project_id, mr_iid)`, `get_approvals(project_id, mr_iid)`, `iter_mr_changes(project_id, mr_iid)` as async iterators/typed DTOs.
- `CapabilityReport` distinguishes required capability failure from optional metric unavailability.

- [ ] **Step 1: Write failing HTTP-contract tests**

Cover token header use without log exposure, keyset/page pagination, `Retry-After`, bounded retries for `429` and transient `5xx`, immediate typed errors for `401/403`, missing total headers, GitLab `19.3.6-ee` acceptance, incompatible version rejection, and optional approval-history unavailability.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/gitlab/test_client.py -v`

Expected: FAIL because `GitLabClient` does not exist.

- [ ] **Step 3: Implement DTOs and the thin REST client**

Centralize URL construction, timeout, pagination and retry policy. Return typed results and coverage errors; never emit authorization headers, response diff bodies or token values into logs.

- [ ] **Step 4: Verify client contracts**

Run: `cd backend && pytest tests/gitlab/test_client.py -v`

Expected: PASS for success, partial-capability and failure fixtures.

- [ ] **Step 5: Commit**

```bash
git add backend/app/gitlab backend/tests/gitlab
git commit -m "feat: add compatible GitLab API client"
```

### Task 4: Durable synchronization job lifecycle

**Files:**
- Create: `backend/app/sync/repository.py`
- Create: `backend/app/sync/service.py`
- Create: `backend/app/sync/routes.py`
- Create: `backend/app/sync/worker.py`
- Modify: `backend/app/main.py`
- Modify: `compose.yaml`
- Create: `backend/tests/sync/test_job_repository.py`
- Create: `backend/tests/sync/test_job_routes.py`
- Create: `backend/tests/sync/test_worker_recovery.py`

**Interfaces:**
- Produces: `SyncJobRepository.create() -> SyncJob`, `claim_next(worker_id: str, lease_seconds: int) -> SyncJob | None`, `update_progress(job_id, progress: SyncProgress)`, `succeed(job_id, watermark: datetime)`, `fail(job_id, summary: str)`, `expire_stale_leases(now: datetime)`.
- Produces: `SyncOrchestrator.run(job_id: UUID) -> None`; later tasks register ordered synchronization stages.
- Produces: `POST /api/sync-jobs`, `GET /api/sync-jobs/current`, `GET /api/sync-jobs/{job_id}`.

- [ ] **Step 1: Write failing lifecycle tests**

Test atomic claim with `FOR UPDATE SKIP LOCKED`, one pending/running job maximum, progress persistence, previous successful watermark preservation on failure, stale-lease expiration, retry idempotency and secret-free error summaries.

- [ ] **Step 2: Run repository/worker tests and verify failure**

Run: `cd backend && pytest tests/sync/test_job_repository.py tests/sync/test_worker_recovery.py -v`

Expected: FAIL because repository and worker services do not exist.

- [ ] **Step 3: Implement repository, orchestrator shell and worker loop**

The worker polls PostgreSQL, claims one job, renews its lease between stages and records failures. It never advances the report watermark unless all registered stages succeed.

- [ ] **Step 4: Write failing route tests, then implement routes**

Assert `202` on job creation, `409` when a job is active, and distinct `pending/running/succeeded/failed` response schemas with progress and warnings.

Run: `cd backend && pytest tests/sync/test_job_routes.py -v`

Expected before route implementation: FAIL; expected after implementation: PASS.

- [ ] **Step 5: Verify crash recovery and task integration**

Run: `cd backend && pytest tests/sync -v`

Expected: PASS, including simulated mid-stage crash and retry.

- [ ] **Step 6: Commit**

```bash
git add backend/app/sync backend/app/main.py backend/tests/sync compose.yaml
git commit -m "feat: add durable synchronization jobs"
```

### Task 5: User, repository and identity synchronization

**Files:**
- Create: `backend/app/activity/identity.py`
- Create: `backend/app/activity/ingestion.py`
- Create: `backend/tests/activity/test_identity.py`
- Create: `backend/tests/activity/test_user_sync.py`
- Modify: `backend/app/sync/service.py`

**Interfaces:**
- Produces: `IdentityResolver.resolve(email: str) -> AttributionResult`, with `matched`, `unmatched`, and `ambiguous` results.
- Produces: `UserRepositorySync.run(job_id: UUID, client: GitLabClient, cutoff: datetime) -> StageResult`.
- Stores active users, configured repositories, exact case-normalized aliases and data-quality warnings.

- [ ] **Step 1: Write failing identity tests**

Cover exact unique email, case normalization, GitLab noreply identity, shared/ambiguous email, unmatched email, bot/service masks, and explicit prohibition of fuzzy/name-only matching.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/activity/test_identity.py -v`

Expected: FAIL because `IdentityResolver` does not exist.

- [ ] **Step 3: Implement identity resolution**

Implement deterministic versioned rules only; return evidence and warning codes with every non-match.

- [ ] **Step 4: Write failing user/repository synchronization tests, then implement the stage**

Assert active-state persistence, bot/service exclusion, project allowlist enforcement, idempotent upsert, missing-project coverage warning and stage progress.

Run: `cd backend && pytest tests/activity/test_user_sync.py -v`

Expected before implementation: FAIL; expected after implementation: PASS.

- [ ] **Step 5: Register the stage and verify**

Run: `cd backend && pytest tests/activity/test_identity.py tests/activity/test_user_sync.py tests/sync -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/activity backend/app/sync/service.py backend/tests/activity
git commit -m "feat: synchronize GitLab users and repositories"
```

### Task 6: Merge-request, commit and collaboration ingestion

**Files:**
- Modify: `backend/app/activity/ingestion.py`
- Create: `backend/tests/activity/test_activity_ingestion.py`
- Create: `backend/tests/activity/test_review_sessions.py`
- Create: `backend/tests/activity/test_commit_deduplication.py`
- Modify: `backend/app/sync/service.py`

**Interfaces:**
- Produces: `ActivitySync.run(job_id: UUID, client: GitLabClient, cutoff: datetime, now: datetime) -> StageResult`.
- Produces: `group_review_sessions(events: Sequence[ReviewEvent], window: timedelta) -> list[ReviewSession]`.
- Stores MR, commit, review and approval facts plus explicit availability status for optional metrics.

- [ ] **Step 1: Write failing MR and interval-semantics tests**

Cover half-open `[start, end)` membership, UTC persistence, configured timezone conversion, MRs created before but merged inside the window, all currently open MRs regardless of age, and current-state labeling for open/stale metrics.

- [ ] **Step 2: Write failing commit de-duplication tests**

Cover MR commits versus merge/squash commits, direct target-branch commits, distinct-SHA cherry-picks, multiple target branches and stable GitLab source keys. Assert that one accepted change does not become both MR and direct contribution.

- [ ] **Step 3: Write failing collaboration tests**

Cover system-note/bot exclusion, multiple comments grouped into one review session, self-review exclusion, approvals separate from reviews, approve/revoke handling, and explicit `unavailable` approval history.

- [ ] **Step 4: Run tests and verify failure**

Run: `cd backend && pytest tests/activity/test_activity_ingestion.py tests/activity/test_review_sessions.py tests/activity/test_commit_deduplication.py -v`

Expected: FAIL because activity synchronization is incomplete.

- [ ] **Step 5: Implement activity synchronization**

Use `merged_at`, `committed_date`, review creation time and `closed_at` exactly as the spec defines. Persist current open/stale facts with the synchronization watermark and keep all writes idempotent.

- [ ] **Step 6: Register the stage and verify**

Run: `cd backend && pytest tests/activity -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/activity/ingestion.py backend/app/sync/service.py backend/tests/activity
git commit -m "feat: synchronize developer activity facts"
```

### Task 7: Transient diff processing and exclusion rules

**Files:**
- Create: `backend/app/activity/diff_stats.py`
- Create: `backend/tests/activity/test_diff_stats.py`
- Create: `backend/tests/activity/test_diff_persistence.py`
- Modify: `backend/app/activity/ingestion.py`
- Modify: `backend/app/sync/service.py`

**Interfaces:**
- Produces: `ExclusionRules.from_config(global_rules, repository_rules) -> ExclusionRules`.
- Produces: `analyze_change(change: GitLabFileChange, rules: ExclusionRules) -> FileChangeStat`.
- `FileChangeStat` contains path, additions, deletions, binary flag, classification (`production`, `test`, `docs_config`, `other`), exclusion flag and reason; it contains no diff body.

- [ ] **Step 1: Write failing classification/exclusion tests**

Cover vendor/generated/build directories, lock files, minified assets, source maps, binary files, repository override precedence, test/docs/config classification and ordinary production files.

- [ ] **Step 2: Run classification tests and verify failure**

Run: `cd backend && pytest tests/activity/test_diff_stats.py -v`

Expected: FAIL because diff analysis does not exist.

- [ ] **Step 3: Implement transient analysis**

Parse only enough diff content in memory to obtain counts when GitLab does not provide them. Return zero analytical lines plus an exclusion reason for excluded/binary files.

- [ ] **Step 4: Write failing persistence and multi-author attribution tests**

Assert MR-level stats are attributed to the MR author, accepted MR changes are stored once, unmerged stats are contextual, excluded-file counts remain inspectable, and no database column/value retains raw patch text.

Run: `cd backend && pytest tests/activity/test_diff_persistence.py -v`

Expected before ingestion integration: FAIL; expected after integration: PASS.

- [ ] **Step 5: Integrate diff processing into synchronization and verify**

Run: `cd backend && pytest tests/activity/test_diff_stats.py tests/activity/test_diff_persistence.py tests/activity/test_commit_deduplication.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/activity/diff_stats.py backend/app/activity/ingestion.py backend/app/sync/service.py backend/tests/activity
git commit -m "feat: calculate repository contribution statistics"
```

### Task 8: Report time semantics and SQL query services

**Files:**
- Create: `backend/app/reports/__init__.py`
- Create: `backend/app/reports/time.py`
- Create: `backend/app/reports/schemas.py`
- Create: `backend/app/reports/queries.py`
- Create: `backend/tests/reports/test_time_ranges.py`
- Create: `backend/tests/reports/test_user_list_query.py`
- Create: `backend/tests/reports/test_user_detail_queries.py`

**Interfaces:**
- Produces: `ReportFilter(repository_id: int | None, start_date: date, end_date: date, timezone: str)` with validated 12-month availability.
- Produces: `to_utc_interval(filter: ReportFilter) -> tuple[datetime, datetime]` using half-open boundaries.
- Produces: `UserSort`, `PageRequest`, `UserPage`, and `CoverageStatus` response types in `reports/schemas.py`.
- Produces: `ReportQueries.list_users(filter, sort: UserSort, page: PageRequest) -> UserPage`.
- Produces: `get_user_summary(user_id, filter)`, `get_user_timeline(user_id, filter, granularity)`, `get_repository_contribution(user_id, filter)`, `list_source_facts(user_id, filter, kind, page)`.

- [ ] **Step 1: Write failing time-range tests**

Cover included human end date, UTC conversion, `Europe/Moscow`, a DST-observing IANA timezone, out-of-window rejection and automatic daily/weekly/monthly granularity cutovers.

- [ ] **Step 2: Write failing list-query tests**

Assert all-repositories includes active users with zeros; one repository includes only users with qualifying activity; every metric is sortable; unavailable differs from zero; server pagination is stable; coverage/watermark metadata is returned.

- [ ] **Step 3: Write failing person-query tests**

Assert identical repository/date filters across summary, timeline, repository contribution and source facts; correct active-day/month semantics; median cycle time; line/file exclusions; current open/stale labeling; and source links built from stable GitLab identities.

- [ ] **Step 4: Run tests and verify failure**

Run: `cd backend && pytest tests/reports/test_time_ranges.py tests/reports/test_user_list_query.py tests/reports/test_user_detail_queries.py -v`

Expected: FAIL because report services do not exist.

- [ ] **Step 5: Implement report schemas and SQL query services**

Use normalized indexed facts first. Keep sorting as an enum/allowlist and never interpolate client field names into SQL. Add materialized aggregates only if the representative query-plan test proves they are needed.

- [ ] **Step 6: Verify report services**

Run: `cd backend && pytest tests/reports -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/reports backend/tests/reports
git commit -m "feat: add developer activity report queries"
```

### Task 9: Report HTTP API and coverage contracts

**Files:**
- Create: `backend/app/reports/routes.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/reports/test_report_routes.py`
- Create: `backend/tests/test_secret_redaction.py`

**Interfaces:**
- Produces: `GET /api/repositories`.
- Produces: `GET /api/report-rules` with non-secret target-branch, stale-MR, classification and exclusion rules plus their version.
- Produces: `GET /api/users` with repository/date/search/sort/page parameters.
- Produces: `GET /api/users/{user_id}/summary`, `/timeline`, `/repositories`, and `/sources`.
- Every report response includes `watermark`, `coverage`, and applied report/exclusion-rule version.

- [ ] **Step 1: Write failing route-contract tests**

Assert validated query parameters, `400/404/422` distinctions, stable JSON field names, pagination metadata, repository/date propagation, unavailable values serialized as explicit status rather than numeric zero, inspectable non-secret report rules, and correct GitLab source URLs.

- [ ] **Step 2: Write failing security tests**

Exercise validation errors, GitLab client failures and sync failures; assert token values and authorization headers are absent from logs and every HTTP response.

- [ ] **Step 3: Run tests and verify failure**

Run: `cd backend && pytest tests/reports/test_report_routes.py tests/test_secret_redaction.py -v`

Expected: FAIL because report routes do not exist.

- [ ] **Step 4: Implement route translation and register routers**

Routes depend only on query-service interfaces from Task 8. Keep filtering and metric computation out of route handlers.

- [ ] **Step 5: Verify all backend tests**

Run: `cd backend && pytest -v`

Expected: PASS with no warnings about unawaited work or leaked connections.

- [ ] **Step 6: Commit**

```bash
git add backend/app/reports/routes.py backend/app/main.py backend/tests
git commit -m "feat: expose activity report API"
```

### Task 10: Frontend API contracts, routing and synchronization UI

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/app/router.tsx`
- Modify: `frontend/src/app/App.tsx`
- Create: `frontend/src/features/sync/useSyncJob.ts`
- Create: `frontend/src/features/sync/SyncPage.tsx`
- Create: `frontend/src/features/sync/SyncPage.test.tsx`
- Create: `frontend/src/test/fixtures.ts`

**Interfaces:**
- Produces typed API functions matching Task 4 and Task 9 response schemas.
- Produces routes `/developers`, `/developers/:userId`, `/synchronization`.
- `useSyncJob()` polls while status is pending/running and stops on succeeded/failed.

- [ ] **Step 1: Write failing synchronization-page tests**

Cover no previous sync, start action, `409` active-job reuse, stage/project/item progress, elapsed/last-success timestamps, access warning, failure/retry and disabled duplicate start.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd frontend && npm test -- --run src/features/sync/SyncPage.test.tsx`

Expected: FAIL because API client, router and page do not exist.

- [ ] **Step 3: Implement typed client, router and synchronization page**

Use TanStack Query for mutation/polling. Render warnings separately from zero-like counts and never render a token field.

- [ ] **Step 4: Verify frontend sync behavior**

Run: `cd frontend && npm test -- --run src/features/sync/SyncPage.test.tsx src/app/App.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add visible synchronization workflow"
```

### Task 11: Developer list, global filters and sortable metrics

**Files:**
- Create: `frontend/src/features/reports/useReportFilters.ts`
- Create: `frontend/src/features/reports/ReportFilters.tsx`
- Create: `frontend/src/features/reports/UsersTable.tsx`
- Create: `frontend/src/features/reports/UsersPage.tsx`
- Create: `frontend/src/features/reports/UsersPage.test.tsx`
- Modify: `frontend/src/app/router.tsx`

**Interfaces:**
- Produces: `ReportFilterState` synchronized with URL search params: `repository`, `start`, `end`, `search`, `sort`, `direction`, `page`.
- Produces `UsersPage` using server-side sorting and pagination for every metric column from the spec.

- [ ] **Step 1: Write failing filter and table tests**

Cover arbitrary dates, quick presets, repository selection, URL round-trip, user search, all column sorts, pagination reset on filter change, active users with zero values in all-repository mode, and repository-only active users in single-repository mode.

- [ ] **Step 2: Write failing state-presentation tests**

Assert `0`, “Unavailable”, and “Not synchronized” render differently; coverage warnings and last-success watermark remain visible; the page never labels the table “ranking” or displays a composite score.

- [ ] **Step 3: Run tests and verify failure**

Run: `cd frontend && npm test -- --run src/features/reports/UsersPage.test.tsx`

Expected: FAIL because report controls and table do not exist.

- [ ] **Step 4: Implement filter state, controls and table**

Use TanStack Table in manual sorting/pagination mode. The repository/date filter object passed to every query must come from `useReportFilters`.

- [ ] **Step 5: Verify the feature**

Run: `cd frontend && npm test -- --run src/features/reports/UsersPage.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/reports frontend/src/app/router.tsx
git commit -m "feat: add sortable developer activity list"
```

### Task 12: Detailed person card and repository contribution views

**Files:**
- Create: `frontend/src/features/user/UserPage.tsx`
- Create: `frontend/src/features/user/SummaryCards.tsx`
- Create: `frontend/src/features/user/ActivityTimeline.tsx`
- Create: `frontend/src/features/user/RepositoryContribution.tsx`
- Create: `frontend/src/features/user/SourceFacts.tsx`
- Create: `frontend/src/features/user/UserPage.test.tsx`
- Modify: `frontend/src/app/router.tsx`

**Interfaces:**
- `UserPage` consumes the shared `ReportFilterState` and Task 9 endpoints.
- `ActivityTimeline` accepts typed time buckets and selectable metric series.
- `RepositoryContribution` renders repository totals, change composition, code areas and exclusions.
- `SourceFacts` provides pageable MR/commit/review lists with GitLab links.

- [ ] **Step 1: Write failing summary and timeline tests**

Assert totals, selected period/repository labels, automatic granularity data, series toggles, current-as-of watermark for open/stale MR, and unavailable approvals.

- [ ] **Step 2: Write failing repository-contribution tests**

Assert added/deleted lines by month and repository, changed files, merged MRs, reviews, active months, production/test/docs/other composition, code-area paths and excluded-file counts.
Assert the active classification/exclusion-rule version is visible and the non-secret rules can be inspected from the contribution view.

- [ ] **Step 3: Write failing source-fact tests**

Assert pageable fact kinds, source links, unmerged work labeled context-only, and repository/date filter propagation to every request.

- [ ] **Step 4: Run tests and verify failure**

Run: `cd frontend && npm test -- --run src/features/user/UserPage.test.tsx`

Expected: FAIL because person-card components do not exist.

- [ ] **Step 5: Implement the person card**

Use ECharts for the timeline and accessible HTML tables for detailed repository/source data. Preserve filter search params when navigating from the user list and back.

- [ ] **Step 6: Verify the feature and frontend suite**

Run: `cd frontend && npm test -- --run`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/user frontend/src/app/router.tsx
git commit -m "feat: add detailed developer contribution view"
```

### Task 13: End-to-end validation, operational documentation and release hardening

**Files:**
- Create: `frontend/tests/report-flow.spec.ts`
- Create: `backend/tests/integration/test_full_sync_report.py`
- Modify: `compose.yaml`
- Modify: `.env.example`
- Modify: `README.md`
- Create: `docs/operations.md`

**Interfaces:**
- Produces one documented local-GitLab-to-report workflow and production configuration procedure.
- Produces health checks and startup ordering sufficient for `docker compose up`.

- [ ] **Step 1: Write the failing backend integration test**

Using deterministic GitLab HTTP fixtures and PostgreSQL, run a full sync and assert the list/card totals, excluded files, watermark, coverage warnings, retry idempotency and absence of raw diffs/secrets in persistence/logs.

- [ ] **Step 2: Run integration test and verify failure**

Run: `cd backend && pytest tests/integration/test_full_sync_report.py -v`

Expected: FAIL until cross-feature fixture and any missing integration wiring are complete.

- [ ] **Step 3: Complete integration wiring and pass the test**

Make only the minimal cross-module changes required by the failing integration assertions.

Run: `cd backend && pytest tests/integration/test_full_sync_report.py -v`

Expected: PASS.

- [ ] **Step 4: Write the failing Playwright journey**

Cover start synchronization, observe progress, open the developer list, set an arbitrary date range, select one repository, sort by added lines, open a person, inspect monthly contribution and follow a source-link target.

- [ ] **Step 5: Run Playwright and complete missing wiring**

Run: `cd frontend && npm run test:e2e`

Expected before final wiring: FAIL at the first incomplete journey step; expected after fixes: PASS.

- [ ] **Step 6: Document secure operation**

Document local GitLab setup, required token scopes, Docker secret/environment use, project IDs, timezone, exclusion overrides, network-isolation requirement, first/incremental synchronization, backup/restore and token rotation. State explicitly that the metrics are GitLab activity observations, not performance verdicts.

- [ ] **Step 7: Run full verification**

Run: `cd backend && pytest -v`

Run: `cd frontend && npm test -- --run`

Run: `cd frontend && npm run build`

Run: `cd frontend && npm run test:e2e`

Run: `docker compose config --quiet`

Run: `git diff --check`

Expected: every command exits 0; no failed tests, build errors, invalid Compose configuration or whitespace errors.

- [ ] **Step 8: Commit**

```bash
git add backend/tests/integration frontend/tests compose.yaml .env.example README.md docs/operations.md
git commit -m "test: validate GitLab activity analytics workflow"
```

## Plan completion criteria

- All 13 task commits exist and each task’s focused verification passed before its commit.
- The full verification commands in Task 13 pass on the final tree.
- The UI supports synchronization, all-user sorting, repository filtering, arbitrary in-window dates and the complete person card from the approved spec.
- No ranking, score, anomaly label, external service, authentication feature, Celery or Redis was introduced.
- The final branch is reviewed using the execution method selected at handoff.
