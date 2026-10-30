# GitLab Developer Activity Analytics — Design

## Status

Proposed design for the first product iteration. No implementation may begin until this document is explicitly approved.

## Intent and why

Senior management needs a factual, inspectable view of developer activity recorded in a self-managed GitLab instance. The first iteration is deliberately an analytics product, not an employee-performance scoring system. It lets management inspect all active GitLab users, sort objective activity metrics, narrow the view to a repository and period, and drill from a person’s summary to the underlying GitLab objects.

The system is intended to help management decide where additional human investigation may be worthwhile. It must not declare that a person is effective or ineffective.

## Users and operating context

- The only intended users are senior managers.
- The application runs entirely inside the corporate network.
- The development and test environment uses a locally deployed GitLab.
- Production connects to the company’s self-managed GitLab `19.3.6-ee` (Enterprise Edition), which is the compatibility baseline for the first iteration.
- The first iteration has no application-level authentication. Network isolation is therefore mandatory.
- A senior manager’s GitLab personal access token supplies the application’s GitLab permissions.

## Goals

1. Synchronize the most recent rolling 12 months of data from five configured GitLab repositories.
2. Make synchronization visible and controllable from the web UI.
3. Show all active GitLab users and their activity metrics in a sortable table.
4. Filter reports by an arbitrary date interval within the available 12-month window.
5. View all configured repositories together or select one repository.
6. Provide a detailed person card with totals, timeline trends, repository contribution, collaboration activity and source-object drill-down.
7. Calculate added and deleted lines while excluding generated and otherwise non-analytical files.
8. Keep reports responsive by querying a local PostgreSQL analytical cache rather than GitLab on every filter change.
9. Make missing permissions, incomplete synchronization and exclusions visible so missing data is not mistaken for zero activity.

## Non-goals for the first iteration

- Ranking, scoring or labeling employees.
- Automatic anomaly detection or a list of suspected low performers.
- Thresholds, weights or a configurable performance formula.
- HR decisions or automated actions based on activity data.
- Jira or Confluence integrations.
- Organization roles, grades, teams or HR identity reconciliation.
- Application authentication, authorization or SSO.
- GitLab webhooks or real-time ingestion.
- More than the latest rolling 12 months of history.
- LLM-based code-quality assessment.
- Persisting source code or raw diffs in the analytics database.
- Comments, investigation workflows or management decisions attached to a user.

## Anti-goals

The product fails even if technically functional when it:

- presents activity volume as a definitive measurement of productivity;
- treats lines of code as inherently positive or negative;
- silently converts unavailable GitLab data into zeros;
- double-counts the same accepted change as both a merge request and its commits;
- makes it difficult to reach the source merge request, commit or review;
- sends code, metadata, telemetry or credentials outside the corporate network;
- requires distributed infrastructure disproportionate to five repositories and roughly 150 developers.

## Agreed product shape

### Global report controls

Every report view uses the same controls:

- repository: all configured repositories or one repository;
- date interval: arbitrary start and end dates inside the synchronized 12-month window;
- quick date presets: 30 days, 3 months, 6 months, 12 months and current calendar year;
- user search by visible name, username or known email.

The selected repository and date interval are encoded in the URL, so a report can be shared inside the corporate network.

Timeline granularity is automatic:

- daily for short intervals;
- weekly for medium intervals;
- monthly for long intervals.

Exact cutovers are a builder call and should be centralized in one frontend utility.

### User list

The default “all repositories” view lists active GitLab accounts, including users with zero qualifying activity in the configured repositories during the selected period. This makes an absence of observed activity visible.

When one repository is selected, the list contains only users with at least one qualifying activity event in that repository during the selected period.

The table supports server-side sorting by every displayed metric. The initial columns are:

- user name and GitLab username;
- merged merge requests;
- accepted commits;
- direct commits to a target branch;
- substantive reviews;
- approvals;
- active days;
- active months;
- added lines;
- deleted lines;
- changed files;
- open merge requests;
- stale merge requests;
- median merge-request cycle time.

The table is not called a ranking and has no composite score or ordinal “place.”

### Person card

The card uses the global repository and date filters and contains:

1. **Summary:** total values for the metrics listed above and the timestamp of the last successful synchronization.
2. **Timeline:** selectable activity series by automatic day/week/month buckets.
3. **Completed contribution:** merged merge requests, accepted commits and direct target-branch commits.
4. **Collaboration:** substantive reviews, discussion participation and approvals kept as separate facts.
5. **Work-flow context:** time to first review, cycle time, open merge requests, closed-unmerged merge requests and stale merge requests.
6. **Repository contribution:** repository-by-repository merge requests, commits, reviews, added/deleted lines, changed files and active months.
7. **Code-area contribution:** directories or configured path groups touched by accepted changes; this indicates where a user worked and does not assert code ownership.
8. **Change composition:** production code, tests, documentation/configuration and other, classified by configurable path and extension rules.
9. **Source facts:** pageable lists linking to the original GitLab merge requests, commits and review discussions.

Unmerged work is context only. It is never added to completed contribution totals.

### Synchronization screen

The UI provides:

- a “Synchronize” action;
- current stage and progress;
- current project and object type being processed;
- processed/estimated item counts when GitLab exposes a useful total;
- start time, elapsed time and last successful completion time;
- warnings for inaccessible projects or endpoints;
- a concise error and retry action after failure;
- prevention of overlapping synchronization runs.

The browser polls the API for progress. Server-Sent Events are not required in the first iteration.

Reports show data from the last successful synchronization. A failed or partial run must not advance the visible synchronization watermark.

## Metric semantics

All metrics are neutral observations and must be labeled accordingly in the UI.

### User population

- An active user is an account whose GitLab state is `active` and which is visible to the configured token.
- Bot and service accounts are excluded using GitLab account metadata where available and configurable username/email masks as a fallback.
- The stable identity is the GitLab user ID.
- Commit author emails are aliases used for attribution, not primary identities.
- Unmatched commit identities are reported as a data-quality warning and are not silently assigned.

### Completed contribution

- **Merged merge request:** an MR authored by the user whose `merged_at` lies within the selected interval.
- **Accepted commit:** a commit authored by the user and included in a qualifying merged MR. Accepted commits support drill-down but do not add a second unit to the merged-MR count.
- **Direct target-branch commit:** a qualifying authored commit present on a configured target branch and not already attributed through a counted merged MR.
- MR diff statistics are counted once at MR level to avoid merge/squash commit duplication.
- MR-level added/deleted lines and changed files are attributed to the MR author. Commit authorship is exposed separately; the first iteration does not attempt to divide a final MR diff among multiple commit authors because overlapping intermediate diffs cannot be allocated reliably.
- Closed-unmerged and open MRs are context only.

By default, each repository’s default branch is a target branch. Additional long-lived target branches are repository configuration.

A direct target-branch commit is evaluated from the target branch history observed at synchronization time, uses `committed_date` for interval membership, excludes merge commits, and excludes commits already associated with a counted MR. A cherry-pick with a distinct SHA is a separate direct commit. The system does not claim historical branch-membership reconstruction beyond what GitLab exposes.

### Reviews and approvals

- System notes and automated bot messages are ignored.
- A substantive review is human participation in an MR discussion or a human review comment containing non-whitespace content.
- Multiple comments by the same reviewer on the same MR in one review session count as one review for headline totals; comment and discussion counts remain available in details.
- An approval is shown separately and is not assumed to be a substantive review.
- Self-review and self-approval do not count as collaboration.
- When GitLab exposes timestamped approve/revoke events, each approval interval fact is the latest non-revoked approval event by that user for that MR. When the deployed GitLab version exposes only current approval state without event timestamps, interval approval metrics are marked unavailable rather than inferred.

The exact review-session grouping window is a builder call, centralized and covered by tests.

### Flow metrics

- **Cycle time:** `merged_at - created_at` for MRs merged in the selected interval; headline value is the median.
- **Time to first review:** first qualifying review time minus MR creation time.
- **Open MR:** authored MR still open at the last successful synchronization, independent of the selected historical report end date.
- **Stale MR:** currently open MR with no qualifying update for a configurable number of days before the last successful synchronization; default 30.
- **Closed-unmerged MR:** MR whose `closed_at` lies within the selected interval.
- Durations are contextual and not normalized into a score.

The first iteration does not reconstruct MR state as of an arbitrary past date. Current open/stale metrics are labeled “as of last synchronization” so they cannot be mistaken for historical-period values.

### Active periods

- An active day contains at least one qualifying authored merge, direct commit, substantive review or approval.
- An active month contains at least one active day.
- Several events on one day do not multiply the active-day count.

### Time and interval rules

- All source timestamps are persisted in UTC.
- Report date boundaries are interpreted in one configured IANA timezone; the initial default is `Europe/Moscow`.
- API intervals are half-open: `[start, end)`. The date-picker’s human-readable end date is converted to the following local midnight, so the selected end date is included from the user’s perspective.
- Merged MRs use `merged_at`; direct commits use `committed_date`; review comments/discussions use their creation timestamp; closed-unmerged MRs use `closed_at`; timestamped approvals use the approval-event timestamp.
- Timeline buckets are calculated in the configured report timezone.

### Line and file statistics

- Added/deleted lines and changed files are calculated only from accepted changes in the selected interval.
- Unmerged diffs are displayed separately as context and do not enter completed line totals.
- Binary files contribute neither added nor deleted lines.
- Raw diff content is processed transiently and is not stored.
- Stored facts include repository, source object ID, file path, added/deleted counts, classification and exclusion reason where applicable.

Default exclusions include:

- dependency/vendor directories;
- generated-code directories;
- build and distribution output;
- minified assets and source maps;
- lock files;
- generated documentation and snapshots when configured;
- binary files.

There is a global exclusion configuration plus per-repository overrides. The person card reports excluded file counts and makes the active rule set inspectable.

Lines of code are sortable facts but carry no special positive or negative interpretation.

## Architecture approaches considered

### 1. Modular monolith with a local relational cache — selected

One backend codebase contains clearly separated GitLab ingestion, domain calculation and HTTP API modules. API and synchronization run as separate processes. PostgreSQL stores normalized facts and report-ready aggregates. React provides the browser UI.

This has the lowest operational complexity that still supports durable synchronization, fast filters and a future path to more sources.

### 2. Batch analytics platform

An orchestrator plus Parquet/DuckDB or an analytical database would make repeated large historical transformations convenient. It adds technologies and operating burden that are not justified by five repositories, 150 developers and a 12-month window.

### 3. Event-driven services

Webhooks, a message broker and independently deployed services would support near-real-time updates and large scale. Monthly management use does not benefit from that complexity.

## Data-access approaches considered

### Direct GitLab queries on every filter

Rejected. Arbitrary report filtering would trigger many API calls and diff downloads, cause slow and variable response times, repeatedly load GitLab and turn permission or availability failures into ambiguous report gaps.

### Celery/Redis ingestion

Rejected for the first iteration. It is robust but introduces a general-purpose broker and task framework for one serialized synchronization workflow.

### PostgreSQL-backed dedicated sync process — selected

The API records a synchronization request in PostgreSQL. A single-purpose Python process claims the job using row locking, performs the work and writes progress. This provides durability and visible progress without Celery or Redis.

## Technical stack

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- `httpx` for a thin GitLab REST API client
- PostgreSQL driver compatible with SQLAlchemy async operation

The GitLab client owns pagination, timeouts, retry/backoff, rate-limit handling, endpoint capability checks and response logging with secret redaction.

The first supported server baseline is GitLab `19.3.6-ee`. Synchronization records the detected GitLab version and edition and fails with a clear compatibility error when the server does not provide a required endpoint. Supporting other GitLab versions is not a first-iteration requirement; optional capability fallbacks must not silently change metric semantics.

### Frontend

- TypeScript
- React
- Vite
- React Router
- TanStack Query
- TanStack Table
- Apache ECharts
- Material UI

### Testing

- pytest for domain, storage and API tests
- mocked GitLab HTTP fixtures for pagination, retries and permission gaps
- migration tests against PostgreSQL
- Vitest and Testing Library for frontend behavior
- Playwright for synchronization, report filtering and person-card drill-down journeys

### Deployment

Docker Compose services:

- `frontend`: static frontend plus reverse proxy;
- `api`: FastAPI HTTP service;
- `sync-worker`: the same Python image running the dedicated synchronization loop;
- `postgres`: persistent database.

No Redis, Celery, external telemetry or external cloud services.

## Backend module boundaries

The modular monolith has explicit packages:

- `gitlab_client`: transport and GitLab DTOs only;
- `sync`: job state machine, incremental cursors and orchestration;
- `identity`: GitLab users and commit-author alias matching;
- `activity`: normalized MR, commit, review and approval facts;
- `diff_stats`: transient diff parsing, exclusions and file classification;
- `metrics`: interval aggregation and timeline bucketing;
- `reports`: query services for the user list and person card;
- `api`: HTTP schemas and routes;
- `config`: repositories, target branches, masks and secrets.

GitLab response shapes must not leak into report-domain APIs.

## Conceptual data model

Core tables:

- `repositories`: GitLab project identity, path, default/target branches and enabled state;
- `users`: GitLab user ID, visible profile fields, state and bot/service exclusion state;
- `user_aliases`: commit email/name attribution with confidence and source;
- `merge_requests`: stable project/IID identity, author, state and timestamps;
- `commits`: stable project/SHA identity, attributed author and relationship to an MR;
- `reviews`: normalized reviewer/MR review session;
- `approvals`: reviewer/MR approval fact;
- `file_changes`: accepted source object, path, added/deleted counts, classification and exclusion state;
- `sync_jobs`: job state, progress, cursors, warnings, errors and timing;
- `sync_project_status`: per-project/per-object-type progress and completeness;
- `app_config`: non-secret repository rules and exclusion settings.

Report aggregates may be materialized after profiling real query plans. The initial design favors normalized indexed facts and SQL aggregation because the data window and scale are small.

Required uniqueness constraints make synchronization idempotent, using GitLab project IDs plus GitLab object IDs/IIDs/SHAs as appropriate.

## Synchronization behavior

1. The UI requests synchronization.
2. The API creates one pending job if no pending/running job exists.
3. `sync-worker` atomically claims the job.
4. The worker verifies token access and configured projects.
   It also verifies that the server reports the supported GitLab `19.3.6-ee` baseline or passes the explicitly implemented capability checks.
5. It synchronizes active users visible to the token.
6. It processes each project and object family with paginated requests.
7. It fetches changes only when required for accepted-change line/file statistics.
8. It records progress, warnings and incremental cursors.
9. It finalizes derived attribution and data-quality checks.
10. It marks the run successful and advances the report-visible watermark.
11. It prunes facts older than the rolling 12-month retention boundary only after success.

The first run loads the complete 12-month window. Later runs use stored GitLab update cursors where endpoint semantics are reliable and re-read a small overlap window to capture delayed edits. All writes are idempotent.

Objects needed to interpret in-window activity may originate before the retention boundary. In particular, the worker fetches full metadata for MRs merged inside the window even when they were created earlier, and fetches all currently open MRs regardless of creation date. Pre-window comments and commits are retained only when required to calculate cycle time, first-review time, attribution or current open-work context; they do not become in-window activity.

Automatic commit attribution accepts exact, case-normalized matches to email addresses GitLab associates with exactly one visible user, including GitLab noreply addresses that encode a stable user identity. Shared or ambiguous emails remain unmatched. Name-only and fuzzy matching are prohibited. Attribution rules are versioned so a rule correction can trigger deterministic reprocessing.

Cancellation is not required for the first iteration. A stale running job may be marked failed after a configurable lease timeout and retried.

## Report query behavior

- Filter changes query PostgreSQL, never GitLab.
- Tables use server-side pagination and sorting.
- Timeline bucketing is performed by SQL/report services using the requested interval.
- Responses include the report-visible synchronization timestamp, coverage warnings and applied exclusion configuration version.
- Empty activity and unavailable data are different states in API schemas and UI presentation.
- Source links use the configured GitLab base URL and stable project/object identities.

## API surface

Exact paths are a builder call, but the first version requires these capabilities:

- system health and GitLab-coverage summary;
- list configured repositories;
- list and sort active users with report filters;
- retrieve person summary and timeline;
- retrieve repository contribution and code-area breakdown;
- retrieve pageable source facts for a person;
- create a synchronization job;
- retrieve current and historical synchronization status;
- retrieve inspectable non-secret reporting rules.

No endpoint accepts or returns the GitLab token.

## Configuration and secrets

The manager’s GitLab token is supplied through an environment variable or Docker secret. It is never stored in PostgreSQL, logged, returned by an API or embedded in the frontend.

Required secret configuration:

- GitLab base URL;
- GitLab personal access token with the minimum practical read scopes;
- PostgreSQL credentials.

Non-secret application configuration includes:

- project allowlist;
- additional target branches;
- bot/service-account masks;
- global and repository-specific file exclusions;
- path classification rules;
- stale-MR threshold;
- report IANA timezone, default `Europe/Moscow`;
- retention period fixed to 12 months in the first iteration.

Configuration errors fail closed and appear on the synchronization screen.

## Security and privacy

- The application must be reachable only in the isolated corporate/development network until authentication is added.
- The reverse proxy does not expose PostgreSQL.
- Logs redact authorization headers, token-like values, query payloads that may contain code and raw diff content.
- Raw code and diff bodies exist only in process memory while statistics are calculated.
- Source links lead back to GitLab, whose permissions remain authoritative.
- The UI states that metrics describe GitLab activity and are not a performance verdict.
- Production deployment without network access controls is unsupported.

## Error and data-quality handling

- A 401/403 response is an access warning or synchronization failure, never zero activity.
- A missing project is shown as missing coverage.
- Rate limiting uses bounded retry/backoff and is visible in sync status.
- Unmatched commit authors, unavailable diffs and unsupported GitLab endpoint variants are counted and displayed.
- A partial run does not become the report-visible data version.
- The UI distinguishes `0`, `not available` and `not synchronized`.
- Source-object deletion after synchronization leaves a tombstone/detail warning rather than silently altering past totals until the next successful sync reconciles it.

## Performance expectations

The target scale is five repositories, about 150 developers and a rolling 12-month window. Normal report filters, sorting and person-card requests should feel interactive and should not depend on GitLab response time. Exact service-level targets should be set after the first representative local-GitLab fixture is available.

Indexes must cover interval, project, attributed user and source-object keys. Materialized aggregates are added only if measured query plans justify them.

## Validation strategy

Before release, verify:

- idempotent repeated synchronization;
- recovery from a failed mid-project run;
- progress visibility and overlap prevention;
- permission gaps represented as unavailable rather than zero;
- no double counting across MRs, squash/merge commits and direct commits;
- active-user semantics for all-repository and one-repository filters;
- arbitrary date boundaries and timeline bucketing;
- repository filter propagation through every card section;
- generated/vendor/lock/binary exclusions;
- line totals against known GitLab fixtures;
- review-session grouping and separation from approvals;
- secret redaction and absence of raw diffs in persistent storage;
- source links point to the correct GitLab objects;
- responsive user list and person card at target data volume.

## Deferred directions

Possible later iterations, requiring a new design decision, include:

- rankings, percentile comparison or anomaly detection;
- organization role/team data and fair comparison cohorts;
- Jira and Confluence signals;
- authentication, SSO and authorization;
- longer retention and historical snapshots;
- webhooks or a general-purpose task queue;
- saved reports and exports;
- management investigation workflows.

## Builder calls left intentionally open

A builder may decide without changing the product:

- exact Python/JavaScript package versions, pinned at implementation time;
- exact REST path naming and internal DTO names;
- exact day/week/month timeline cutovers;
- review-session grouping window;
- polling interval for synchronization progress;
- SQL aggregation versus materialized aggregate use after profiling;
- visual styling within the approved information architecture.

Any change to metric meaning, data retention, user-population rules, authentication, ranking/scoring, or persistent storage of code/diffs requires renewed product approval.
