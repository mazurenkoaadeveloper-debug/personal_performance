# План реализации аналитики активности разработчиков в GitLab

> **Для агентов-исполнителей:** ОБЯЗАТЕЛЬНЫЙ НАВЫК: используйте `superpowers:subagent-driven-development` (рекомендуется) или `superpowers:executing-plans`, чтобы выполнять план по одной задаче. Для отслеживания используются чекбоксы `- [ ]`.

**Цель:** создать внутреннее веб-приложение, которое синхронизирует последние 12 месяцев данных из GitLab `19.3.6-ee` и показывает сортируемую статистику активности пользователей с подробной карточкой вклада каждого человека.

**Архитектура:** модульный Python-монолит запускается двумя процессами — FastAPI API и специализированным worker синхронизации — поверх одной PostgreSQL. React SPA получает данные через отчётный API; фильтры работают по локальной БД, а GitLab-токен и содержимое diff остаются только на сервере и обрабатываются транзитно. Отдельный Docker Compose integration-профиль поднимает точный GitLab `19.3.6-ee`, детерминированно наполняет его и запускает live-интеграционные тесты вне быстрого тестового набора.

**Стек:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, httpx, pytest; TypeScript, React, Vite, React Router, TanStack Query, TanStack Table, Material UI, Apache ECharts, Vitest, Testing Library, Playwright; Docker Compose; `gitlab/gitlab-ee:19.3.6-ee.0`.

**Спецификация:** `docs/superpowers/specs/2026-10-31-gitlab-developer-activity-design.md`

## Общие ограничения

- Целевая версия — строго GitLab `19.3.6-ee`; отсутствие обязательных возможностей должно приводить к явной ошибке совместимости.
- Система полностью работает внутри корпоративного контура, без внешней телеметрии и облачных сервисов.
- Хранятся последние скользящие 12 месяцев; более старые метаданные допустимы только для интерпретации событий внутри окна и текущих открытых MR.
- Исходный код и необработанные diff никогда не сохраняются; в БД попадают только нормализованные метаданные и файловая статистика.
- GitLab-токен нельзя сохранять, логировать, возвращать в API или передавать frontend; он поступает только через переменную окружения или Docker secret.
- PostgreSQL используется и для заданий синхронизации, и для отчётных данных; Celery, Redis и webhooks не добавляются.
- В первую версию не входят рейтинги, баллы, поиск аномалий, Jira, Confluence, авторизация и SSO.
- Backend-схемы и UI должны различать нулевую активность, недоступные данные и ещё не синхронизированные данные.
- Границы отчёта трактуются в настроенной IANA timezone, по умолчанию `Europe/Moscow`; все timestamp хранятся в UTC.
- Каждая задача выполняется через TDD и коммитится только после прохождения указанных фокусных и релевантных общих тестов.
- Live-интеграционные тесты используют только сгенерированные тестовые credentials, запускаются отдельной командой и обязательны перед релизом, но не входят в быстрый `pytest` по умолчанию.

## Особое внимание при ревью

- GitLab возвращает `401`, `403`, не отдаёт pagination totals или часть endpoint-данных: UI показывает недоступность/неполное покрытие и не превращает их в ноль (тесты задачи 3).
- Squash, merge commit и direct commit относятся к одному принятому изменению: вклад учитывается один раз, ссылки на источник сохраняются (тесты задачи 6).
- Diff содержит generated, vendor, binary или исключённый для репозитория файл: строки не учитываются, причина сохраняется, исходный diff в БД не попадает (тесты задачи 7).
- Пользователь выбирает репозиторий и произвольный период с timezone-границами: один фильтр применяется к списку, карточке, таймлайну и исходным фактам, включая DST и локальную полночь (тесты задач 8–9).
- Worker падает после частичной записи: отчёты продолжают использовать предыдущий успешный watermark, lease истекает, повторный запуск идемпотентно завершает синхронизацию (тесты задачи 4).

---

## Планируемая структура файлов

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
  tests/{conftest.py,core/,gitlab/,sync/,activity/,reports/,integration/,gitlab_live/}
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
compose.gitlab-integration.yaml
.env.example
.env.gitlab-integration.example
scripts/gitlab-integration/{wait-ready.sh,seed.py,run.sh}
README.md
docs/operations.md
```

Файлы группируются по ответственности. Route-модули только преобразуют HTTP; GitLab DTO остаются в `gitlab`, нормализованные факты — в `activity`, SQL-агрегация — в `reports`.

## Подготовка GitHub Issues до начала реализации

До передачи задачи 1 в работу в репозитории `mazurenkoaadeveloper-debug/personal_performance` нужно создать:

- один родительский Issue «GitLab Developer Activity Analytics — первая версия» со ссылками на утверждённые спецификацию и план;
- 14 отдельных Issues — по одному на каждую задачу этого плана;
- ссылки на все 14 Issues в checklist родительского Issue;
- в каждом дочернем Issue: цель задачи, полный список файлов, интерфейсы, TDD-шаги, команды проверки, критерии завершения и ссылка на родительский Issue.

Пользователь вручную выбирает следующий Issue для передачи в работу. После выбора применяется `subagent-driven-development`: свежий implementer выполняет только этот Issue, отдельный reviewer проверяет diff, исправления проходят повторное ревью. Автоматически начинать следующий Issue запрещено.

Для каждого Issue используется отдельная feature-ветка. Pull request должен содержать `Closes #N`, если его merge действительно завершает Issue. Создание Issues, веток и pull requests не означает разрешения на merge, закрытие Issues или удаление веток.

### Задача 1: Запускаемый каркас приложения и типизированная конфигурация

**Файлы:**
- Создать: `backend/pyproject.toml`
- Создать: `backend/app/__init__.py`
- Создать: `backend/app/main.py`
- Создать: `backend/app/core/config.py`
- Создать: `backend/app/core/database.py`
- Создать: `backend/app/core/logging.py`
- Создать: `backend/tests/conftest.py`
- Создать: `backend/tests/core/test_config.py`
- Создать: `backend/tests/test_health.py`
- Создать: `frontend/package.json`
- Создать: `frontend/vite.config.ts`
- Создать: `frontend/index.html`
- Создать: `frontend/src/main.tsx`
- Создать: `frontend/src/app/App.tsx`
- Создать: `frontend/src/app/theme.ts`
- Создать: `frontend/src/test/setup.ts`
- Создать: `frontend/src/app/App.test.tsx`
- Создать: `compose.yaml`
- Создать: `.env.example`

**Интерфейсы:**
- Результат: `Settings` с полями `gitlab_base_url: AnyHttpUrl`, `gitlab_token: SecretStr`, `database_url: str`, `report_timezone: str = "Europe/Moscow"`, `retention_days: int = 365`, `gitlab_project_ids: tuple[int, ...]`.
- Результат: `get_settings() -> Settings`, `get_session() -> AsyncIterator[AsyncSession]`, `create_app() -> FastAPI`, `GET /api/health -> {"status": "ok"}`.
- Результат: Compose-сервисы `frontend`, `api`, `sync-worker`, `postgres`; до задачи 4 worker может завершаться с явным сообщением «not implemented».

- [ ] **Шаг 1: Написать падающие тесты конфигурации и health endpoint**

Проверить, что `Settings` отклоняет отсутствующий токен и пустой список проектов, принимает `Europe/Moscow`, скрывает токен как secret, а `/api/health` возвращает строго `{"status": "ok"}` без секретов.

- [ ] **Шаг 2: Запустить backend-тесты и подтвердить падение**

Команда: `cd backend && pytest tests/core/test_config.py tests/test_health.py -v`

Ожидание: FAIL, потому что `app.core.config` и `create_app` не существуют.

- [ ] **Шаг 3: Реализовать backend-каркас**

Реализовать указанные интерфейсы, structured logs в stdout с редактированием token/authorization и async SQLAlchemy session factory. Feature routes пока не добавлять.

- [ ] **Шаг 4: Написать и запустить падающий тест frontend-каркаса**

Проверить, что `<App />` отображает название продукта и пункты «Разработчики» и «Синхронизация».

Команда: `cd frontend && npm test -- --run src/app/App.test.tsx`

Ожидание: FAIL до создания React-каркаса.

- [ ] **Шаг 5: Реализовать React-каркас и Compose**

Добавить Material UI theme, оболочку приложения и Vite proxy для `/api`. В Compose настроить health checks; PostgreSQL наружу не публиковать.

- [ ] **Шаг 6: Проверить задачу**

Команды:

```bash
cd backend && pytest tests/core/test_config.py tests/test_health.py -v
cd frontend && npm test -- --run src/app/App.test.tsx
docker compose config --quiet
```

Ожидание: все команды завершаются с кодом 0.

- [ ] **Шаг 7: Сделать коммит**

```bash
git add backend frontend compose.yaml .env.example
git commit -m "feat: scaffold activity analytics application"
```

### Задача 2: PostgreSQL-схема и миграции

**Файлы:**
- Создать: `backend/alembic.ini`
- Создать: `backend/migrations/env.py`
- Создать: `backend/migrations/versions/0001_initial_schema.py`
- Создать: `backend/app/sync/models.py`
- Создать: `backend/app/activity/models.py`
- Создать: `backend/tests/core/test_migrations.py`
- Создать: `backend/tests/activity/test_model_constraints.py`

**Интерфейсы:**
- Результат: SQLAlchemy-модели `Repository`, `User`, `UserAlias`, `MergeRequest`, `Commit`, `Review`, `Approval`, `FileChange`, `SyncJob`, `SyncProjectStatus`, `AppConfig`.
- Стабильные ключи: GitLab ID репозитория; `(repository_id, iid)` для MR; `(repository_id, sha)` для commit; детерминированные ключи событий для review, approvals и file changes.
- Состояния `SyncJob`: `pending`, `running`, `succeeded`, `failed`; сохраняются lease, progress, warnings, error summary, timestamps и кандидат report watermark.

- [ ] **Шаг 1: Написать падающие тесты миграций и ограничений**

Проверить upgrade пустой PostgreSQL, уникальность source keys, timezone-aware timestamp, JSON-поля прогресса/предупреждений и запрет второго активного sync job через partial unique index.

- [ ] **Шаг 2: Запустить тесты и подтвердить падение**

Команда: `cd backend && pytest tests/core/test_migrations.py tests/activity/test_model_constraints.py -v`

Ожидание: FAIL, потому что модели и миграции отсутствуют.

- [ ] **Шаг 3: Реализовать схему и первую миграцию**

Использовать PostgreSQL enum/check constraints там, где они исключают некорректные состояния. Не создавать колонок для кода или diff body. Добавить индексы `(user_id, event_time)`, `(repository_id, event_time)`, MR timestamps/state и sync-job state/lease.

- [ ] **Шаг 4: Проверить миграции и ограничения**

Команда: `cd backend && pytest tests/core/test_migrations.py tests/activity/test_model_constraints.py -v`

Ожидание: PASS, включая upgrade, downgrade и повторный upgrade.

- [ ] **Шаг 5: Сделать коммит**

```bash
git add backend/alembic.ini backend/migrations backend/app/sync/models.py backend/app/activity/models.py backend/tests
git commit -m "feat: add activity data schema"
```

### Задача 3: GitLab-клиент и проверка совместимости с 19.3.6-ee

**Файлы:**
- Создать: `backend/app/gitlab/__init__.py`
- Создать: `backend/app/gitlab/schemas.py`
- Создать: `backend/app/gitlab/client.py`
- Создать: `backend/tests/gitlab/test_client.py`
- Создать: `backend/tests/gitlab/fixtures/`

**Интерфейсы:**
- Результат: `GitLabClient(base_url: str, token: SecretStr, transport: httpx.AsyncBaseTransport | None = None, page_size: int = 100)`; `page_size` ограничен диапазоном GitLab `1..100` и позволяет live-тесту доказать переход между страницами на маленьком fixture.
- Результат: `get_version() -> GitLabVersion`, `validate_capabilities() -> CapabilityReport`, async-итераторы `iter_active_users()`, `iter_projects(project_ids)`, `iter_merge_requests(project_id, updated_after)`, `iter_commits(project_id, ref, since)`, `iter_discussions(project_id, mr_iid)`, `get_approvals(project_id, mr_iid)`, `iter_mr_changes(project_id, mr_iid)`.
- `CapabilityReport` различает отсутствие обязательной возможности и недоступность необязательной метрики.

- [ ] **Шаг 1: Написать падающие контрактные HTTP-тесты**

Покрыть token header без утечки в логи, границы `page_size`, pagination с/без totals, `Retry-After`, ограниченные повторы `429` и временных `5xx`, немедленные типизированные ошибки `401/403`, принятие `19.3.6-ee`, отклонение несовместимой версии и необязательную недоступность истории approvals.

- [ ] **Шаг 2: Запустить тесты и подтвердить падение**

Команда: `cd backend && pytest tests/gitlab/test_client.py -v`

Ожидание: FAIL, потому что `GitLabClient` отсутствует.

- [ ] **Шаг 3: Реализовать DTO и тонкий REST-клиент**

Централизовать URL, timeout, pagination и retry policy. Возвращать типизированные данные и coverage errors; не логировать authorization, токен и содержимое diff.

- [ ] **Шаг 4: Проверить контракты клиента**

Команда: `cd backend && pytest tests/gitlab/test_client.py -v`

Ожидание: PASS для успешных, частично доступных и ошибочных fixtures.

- [ ] **Шаг 5: Сделать коммит**

```bash
git add backend/app/gitlab backend/tests/gitlab
git commit -m "feat: add compatible GitLab API client"
```

### Задача 4: Надёжный жизненный цикл синхронизации

**Файлы:**
- Создать: `backend/app/sync/repository.py`
- Создать: `backend/app/sync/service.py`
- Создать: `backend/app/sync/routes.py`
- Создать: `backend/app/sync/worker.py`
- Изменить: `backend/app/main.py`
- Изменить: `compose.yaml`
- Создать: `backend/tests/sync/test_job_repository.py`
- Создать: `backend/tests/sync/test_job_routes.py`
- Создать: `backend/tests/sync/test_worker_recovery.py`

**Интерфейсы:**
- Результат: `SyncJobRepository.create() -> SyncJob`, `claim_next(worker_id: str, lease_seconds: int) -> SyncJob | None`, `update_progress(job_id, progress: SyncProgress)`, `succeed(job_id, watermark: datetime)`, `fail(job_id, summary: str)`, `expire_stale_leases(now: datetime)`.
- Результат: `SyncOrchestrator.run(job_id: UUID) -> None`; следующие задачи регистрируют последовательные этапы.
- Результат: `POST /api/sync-jobs`, `GET /api/sync-jobs/current`, `GET /api/sync-jobs/{job_id}`.

- [ ] **Шаг 1: Написать падающие тесты жизненного цикла**

Проверить atomic claim через `FOR UPDATE SKIP LOCKED`, единственный pending/running job, сохранение прогресса, неизменность предыдущего watermark при ошибке, истечение lease, идемпотентный retry и отсутствие секретов в error summary.

- [ ] **Шаг 2: Запустить тесты repository/worker и подтвердить падение**

Команда: `cd backend && pytest tests/sync/test_job_repository.py tests/sync/test_worker_recovery.py -v`

Ожидание: FAIL, потому что repository и worker ещё не существуют.

- [ ] **Шаг 3: Реализовать repository, оболочку orchestrator и worker loop**

Worker опрашивает PostgreSQL, забирает одно задание, продлевает lease между этапами и сохраняет ошибку. Report watermark меняется только после успеха всех этапов.

- [ ] **Шаг 4: Написать падающие route-тесты и реализовать routes**

Проверить `202` при создании, `409` при активном job и отдельные схемы `pending/running/succeeded/failed` с progress и warnings.

Команда: `cd backend && pytest tests/sync/test_job_routes.py -v`

Ожидание: до реализации routes — FAIL, после — PASS.

- [ ] **Шаг 5: Проверить восстановление после падения**

Команда: `cd backend && pytest tests/sync -v`

Ожидание: PASS, включая имитацию падения между этапами и retry.

- [ ] **Шаг 6: Сделать коммит**

```bash
git add backend/app/sync backend/app/main.py backend/tests/sync compose.yaml
git commit -m "feat: add durable synchronization jobs"
```

### Задача 5: Синхронизация пользователей, репозиториев и идентичностей

**Файлы:**
- Создать: `backend/app/activity/identity.py`
- Создать: `backend/app/activity/ingestion.py`
- Создать: `backend/tests/activity/test_identity.py`
- Создать: `backend/tests/activity/test_user_sync.py`
- Изменить: `backend/app/sync/service.py`

**Интерфейсы:**
- Результат: `IdentityResolver.resolve(email: str) -> AttributionResult` с исходами `matched`, `unmatched`, `ambiguous`.
- Результат: `UserRepositorySync.run(job_id: UUID, client: GitLabClient, cutoff: datetime) -> StageResult`.
- Сохраняются активные users, разрешённые repositories, точные case-normalized aliases и предупреждения качества данных.

- [ ] **Шаг 1: Написать падающие тесты идентификации**

Покрыть уникальный точный email, нормализацию регистра, GitLab noreply identity, общий/неоднозначный email, отсутствие совпадения, bot/service masks и запрет fuzzy/name-only matching.

- [ ] **Шаг 2: Запустить тесты и подтвердить падение**

Команда: `cd backend && pytest tests/activity/test_identity.py -v`

Ожидание: FAIL, потому что `IdentityResolver` отсутствует.

- [ ] **Шаг 3: Реализовать определение идентичности**

Использовать только детерминированные версионируемые правила; для каждого несовпадения возвращать evidence и warning code.

- [ ] **Шаг 4: Написать падающие тесты user/repository sync и реализовать этап**

Проверить active state, исключение bot/service accounts, project allowlist, идемпотентный upsert, coverage warning для недоступного проекта и progress этапа.

Команда: `cd backend && pytest tests/activity/test_user_sync.py -v`

Ожидание: до реализации — FAIL, после — PASS.

- [ ] **Шаг 5: Зарегистрировать этап и проверить**

Команда: `cd backend && pytest tests/activity/test_identity.py tests/activity/test_user_sync.py tests/sync -v`

Ожидание: PASS.

- [ ] **Шаг 6: Сделать коммит**

```bash
git add backend/app/activity backend/app/sync/service.py backend/tests/activity
git commit -m "feat: synchronize GitLab users and repositories"
```

### Задача 6: Загрузка MR, commit и совместной работы

**Файлы:**
- Изменить: `backend/app/activity/ingestion.py`
- Создать: `backend/tests/activity/test_activity_ingestion.py`
- Создать: `backend/tests/activity/test_review_sessions.py`
- Создать: `backend/tests/activity/test_commit_deduplication.py`
- Изменить: `backend/app/sync/service.py`

**Интерфейсы:**
- Результат: `ActivitySync.run(job_id: UUID, client: GitLabClient, cutoff: datetime, now: datetime) -> StageResult`.
- Результат: `group_review_sessions(events: Sequence[ReviewEvent], window: timedelta) -> list[ReviewSession]`.
- Сохраняются MR, commit, review, approval и явный availability status необязательных метрик.

- [ ] **Шаг 1: Написать падающие тесты MR и временных границ**

Покрыть полуинтервал `[start, end)`, UTC storage, timezone conversion, MR созданный раньше, но merged внутри окна, все текущие open MR независимо от возраста и watermark для open/stale.

- [ ] **Шаг 2: Написать падающие тесты дедупликации commit**

Покрыть MR commits против merge/squash commits, direct target-branch commit, cherry-pick с отдельным SHA, несколько target branches и стабильные GitLab keys. Одно принятое изменение не должно одновременно считаться MR и direct contribution.

- [ ] **Шаг 3: Написать падающие тесты collaboration**

Покрыть исключение system notes/bots, объединение нескольких комментариев в review session, self-review, approvals отдельно от reviews, approve/revoke и явный `unavailable` для истории approvals.

- [ ] **Шаг 4: Запустить тесты и подтвердить падение**

Команда: `cd backend && pytest tests/activity/test_activity_ingestion.py tests/activity/test_review_sessions.py tests/activity/test_commit_deduplication.py -v`

Ожидание: FAIL, потому что activity sync ещё не реализован.

- [ ] **Шаг 5: Реализовать синхронизацию активности**

Использовать `merged_at`, `committed_date`, review creation time и `closed_at` строго по спецификации. Текущие open/stale facts сохранять с watermark; все записи должны быть идемпотентны.

- [ ] **Шаг 6: Зарегистрировать этап и проверить**

Команда: `cd backend && pytest tests/activity -v`

Ожидание: PASS.

- [ ] **Шаг 7: Сделать коммит**

```bash
git add backend/app/activity/ingestion.py backend/app/sync/service.py backend/tests/activity
git commit -m "feat: synchronize developer activity facts"
```

### Задача 7: Транзитная обработка diff и правила исключения

**Файлы:**
- Создать: `backend/app/activity/diff_stats.py`
- Создать: `backend/tests/activity/test_diff_stats.py`
- Создать: `backend/tests/activity/test_diff_persistence.py`
- Изменить: `backend/app/activity/ingestion.py`
- Изменить: `backend/app/sync/service.py`

**Интерфейсы:**
- Результат: `ExclusionRules.from_config(global_rules, repository_rules) -> ExclusionRules`.
- Результат: `analyze_change(change: GitLabFileChange, rules: ExclusionRules) -> FileChangeStat`.
- `FileChangeStat` содержит path, additions, deletions, binary flag, classification (`production`, `test`, `docs_config`, `other`), exclusion flag и reason; diff body отсутствует.

- [ ] **Шаг 1: Написать падающие тесты классификации и исключений**

Покрыть vendor/generated/build directories, lock files, minified assets, source maps, binary files, приоритет repository overrides, а также test/docs/config и обычные production files.

- [ ] **Шаг 2: Запустить тесты и подтвердить падение**

Команда: `cd backend && pytest tests/activity/test_diff_stats.py -v`

Ожидание: FAIL, потому что diff analysis отсутствует.

- [ ] **Шаг 3: Реализовать транзитный анализ**

Разбирать содержимое diff в памяти только настолько, насколько нужно для подсчёта. Для excluded/binary files возвращать нулевые аналитические строки и причину исключения.

- [ ] **Шаг 4: Написать падающие тесты persistence и multi-author attribution**

Проверить, что MR-level stats относятся к автору MR, accepted changes сохраняются один раз, unmerged stats остаются контекстом, excluded counts доступны для проверки, а БД не содержит patch text.

Команда: `cd backend && pytest tests/activity/test_diff_persistence.py -v`

Ожидание: до интеграции — FAIL, после — PASS.

- [ ] **Шаг 5: Интегрировать обработку diff и проверить**

Команда: `cd backend && pytest tests/activity/test_diff_stats.py tests/activity/test_diff_persistence.py tests/activity/test_commit_deduplication.py -v`

Ожидание: PASS.

- [ ] **Шаг 6: Сделать коммит**

```bash
git add backend/app/activity/diff_stats.py backend/app/activity/ingestion.py backend/app/sync/service.py backend/tests/activity
git commit -m "feat: calculate repository contribution statistics"
```

### Задача 8: Временная семантика отчётов и SQL query services

**Файлы:**
- Создать: `backend/app/reports/__init__.py`
- Создать: `backend/app/reports/time.py`
- Создать: `backend/app/reports/schemas.py`
- Создать: `backend/app/reports/queries.py`
- Создать: `backend/tests/reports/test_time_ranges.py`
- Создать: `backend/tests/reports/test_user_list_query.py`
- Создать: `backend/tests/reports/test_user_detail_queries.py`

**Интерфейсы:**
- Результат: `ReportFilter(repository_id: int | None, start_date: date, end_date: date, timezone: str)` с проверкой доступного 12-месячного окна.
- Результат: `to_utc_interval(filter: ReportFilter) -> tuple[datetime, datetime]` с полуоткрытыми границами.
- Результат: типы `UserSort`, `PageRequest`, `UserPage`, `CoverageStatus` в `reports/schemas.py`.
- Результат: `ReportQueries.list_users(filter, sort: UserSort, page: PageRequest) -> UserPage`.
- Результат: `get_user_summary(user_id, filter)`, `get_user_timeline(user_id, filter, granularity)`, `get_repository_contribution(user_id, filter)`, `list_source_facts(user_id, filter, kind, page)`.

- [ ] **Шаг 1: Написать падающие тесты периодов**

Покрыть включение выбранной пользователем конечной даты, UTC conversion, `Europe/Moscow`, timezone с DST, выход за доступное окно и автоматический выбор daily/weekly/monthly granularity.

- [ ] **Шаг 2: Написать падающие тесты списка пользователей**

Проверить: «все репозитории» включает активных пользователей с нулевыми метриками; один репозиторий — только пользователей с активностью; каждая метрика сортируется; unavailable отличается от zero; pagination стабильна; coverage/watermark возвращаются.

- [ ] **Шаг 3: Написать падающие тесты карточки пользователя**

Проверить одинаковые repository/date filters в summary, timeline, repository contribution и source facts; active days/months; median cycle time; исключения строк/файлов; current open/stale labels и корректные GitLab links.

- [ ] **Шаг 4: Запустить тесты и подтвердить падение**

Команда: `cd backend && pytest tests/reports/test_time_ranges.py tests/reports/test_user_list_query.py tests/reports/test_user_detail_queries.py -v`

Ожидание: FAIL, потому что report services отсутствуют.

- [ ] **Шаг 5: Реализовать схемы и SQL query services**

Сначала использовать нормализованные индексированные facts. Сортировку ограничить enum/allowlist; нельзя подставлять клиентские имена полей в SQL. Materialized aggregates добавлять только по результатам измерения query plan.

- [ ] **Шаг 6: Проверить report services**

Команда: `cd backend && pytest tests/reports -v`

Ожидание: PASS.

- [ ] **Шаг 7: Сделать коммит**

```bash
git add backend/app/reports backend/tests/reports
git commit -m "feat: add developer activity report queries"
```

### Задача 9: HTTP API отчётов и контракты покрытия данных

**Файлы:**
- Создать: `backend/app/reports/routes.py`
- Изменить: `backend/app/main.py`
- Создать: `backend/tests/reports/test_report_routes.py`
- Создать: `backend/tests/test_secret_redaction.py`

**Интерфейсы:**
- Результат: `GET /api/repositories`.
- Результат: `GET /api/report-rules` с несекретными target-branch, stale-MR, classification и exclusion rules и их версией.
- Результат: `GET /api/users` с repository/date/search/sort/page.
- Результат: `GET /api/users/{user_id}/summary`, `/timeline`, `/repositories`, `/sources`.
- Каждый отчёт возвращает `watermark`, `coverage` и версию применённых правил.

- [ ] **Шаг 1: Написать падающие контрактные route-тесты**

Проверить validation, различия `400/404/422`, стабильные JSON fields, pagination, propagation фильтров, явный status вместо числового zero для unavailable, доступные несекретные rules и корректные GitLab URLs.

- [ ] **Шаг 2: Написать падающие security-тесты**

Вызвать validation, GitLab и sync errors; убедиться, что токены и authorization headers отсутствуют в логах и HTTP responses.

- [ ] **Шаг 3: Запустить тесты и подтвердить падение**

Команда: `cd backend && pytest tests/reports/test_report_routes.py tests/test_secret_redaction.py -v`

Ожидание: FAIL, потому что report routes отсутствуют.

- [ ] **Шаг 4: Реализовать routes и зарегистрировать router**

Routes зависят только от query services задачи 8. Фильтрация и расчёт метрик в route handlers запрещены.

- [ ] **Шаг 5: Проверить весь backend**

Команда: `cd backend && pytest -v`

Ожидание: PASS без unawaited work и утечек соединений.

- [ ] **Шаг 6: Сделать коммит**

```bash
git add backend/app/reports/routes.py backend/app/main.py backend/tests
git commit -m "feat: expose activity report API"
```

### Задача 10: Frontend API, маршрутизация и UI синхронизации

**Файлы:**
- Создать: `frontend/src/api/client.ts`
- Создать: `frontend/src/api/types.ts`
- Создать: `frontend/src/app/router.tsx`
- Изменить: `frontend/src/app/App.tsx`
- Создать: `frontend/src/features/sync/useSyncJob.ts`
- Создать: `frontend/src/features/sync/SyncPage.tsx`
- Создать: `frontend/src/features/sync/SyncPage.test.tsx`
- Создать: `frontend/src/test/fixtures.ts`

**Интерфейсы:**
- Результат: типизированные API-функции, соответствующие контрактам задач 4 и 9.
- Результат: маршруты `/developers`, `/developers/:userId`, `/synchronization`.
- `useSyncJob()` опрашивает API в статусах pending/running и останавливается при succeeded/failed.

- [ ] **Шаг 1: Написать падающие тесты страницы синхронизации**

Покрыть отсутствие предыдущей sync, запуск, reuse активного job после `409`, stage/project/item progress, elapsed/last-success timestamps, access warning, failure/retry и блокировку двойного запуска.

- [ ] **Шаг 2: Запустить тесты и подтвердить падение**

Команда: `cd frontend && npm test -- --run src/features/sync/SyncPage.test.tsx`

Ожидание: FAIL, потому что API client, router и страница отсутствуют.

- [ ] **Шаг 3: Реализовать API client, router и страницу**

Использовать TanStack Query для mutation/polling. Warnings отображать отдельно от числовых значений; формы ввода токена быть не должно.

- [ ] **Шаг 4: Проверить frontend sync**

Команда: `cd frontend && npm test -- --run src/features/sync/SyncPage.test.tsx src/app/App.test.tsx`

Ожидание: PASS.

- [ ] **Шаг 5: Сделать коммит**

```bash
git add frontend/src
git commit -m "feat: add visible synchronization workflow"
```

### Задача 11: Список разработчиков, глобальные фильтры и сортировка

**Файлы:**
- Создать: `frontend/src/features/reports/useReportFilters.ts`
- Создать: `frontend/src/features/reports/ReportFilters.tsx`
- Создать: `frontend/src/features/reports/UsersTable.tsx`
- Создать: `frontend/src/features/reports/UsersPage.tsx`
- Создать: `frontend/src/features/reports/UsersPage.test.tsx`
- Изменить: `frontend/src/app/router.tsx`

**Интерфейсы:**
- Результат: `ReportFilterState`, синхронизированный с URL params `repository`, `start`, `end`, `search`, `sort`, `direction`, `page`.
- Результат: `UsersPage` с серверной сортировкой и pagination по всем колонкам спецификации.

- [ ] **Шаг 1: Написать падающие тесты фильтров и таблицы**

Покрыть произвольные даты, quick presets, выбор репозитория, URL round-trip, поиск, сортировку всех колонок, сброс page при фильтре, users с нулём в all-repositories и только active users в single-repository.

- [ ] **Шаг 2: Написать падающие тесты состояний данных**

Проверить разное отображение `0`, «Недоступно», «Не синхронизировано»; видимость coverage warnings и watermark; отсутствие терминов «рейтинг» и composite score.

- [ ] **Шаг 3: Запустить тесты и подтвердить падение**

Команда: `cd frontend && npm test -- --run src/features/reports/UsersPage.test.tsx`

Ожидание: FAIL, потому что controls и table отсутствуют.

- [ ] **Шаг 4: Реализовать filters, controls и table**

Использовать TanStack Table в manual sorting/pagination mode. Все запросы получают один repository/date filter из `useReportFilters`.

- [ ] **Шаг 5: Проверить feature**

Команда: `cd frontend && npm test -- --run src/features/reports/UsersPage.test.tsx`

Ожидание: PASS.

- [ ] **Шаг 6: Сделать коммит**

```bash
git add frontend/src/features/reports frontend/src/app/router.tsx
git commit -m "feat: add sortable developer activity list"
```

### Задача 12: Подробная карточка человека и вклад в репозитории

**Файлы:**
- Создать: `frontend/src/features/user/UserPage.tsx`
- Создать: `frontend/src/features/user/SummaryCards.tsx`
- Создать: `frontend/src/features/user/ActivityTimeline.tsx`
- Создать: `frontend/src/features/user/RepositoryContribution.tsx`
- Создать: `frontend/src/features/user/SourceFacts.tsx`
- Создать: `frontend/src/features/user/UserPage.test.tsx`
- Изменить: `frontend/src/app/router.tsx`

**Интерфейсы:**
- `UserPage` использует общий `ReportFilterState` и endpoints задачи 9.
- `ActivityTimeline` принимает типизированные buckets и выбираемые series.
- `RepositoryContribution` показывает totals, change composition, code areas, exclusions и версию правил.
- `SourceFacts` показывает pageable MR/commit/review и ссылки в GitLab.

- [ ] **Шаг 1: Написать падающие тесты summary и timeline**

Проверить totals, labels периода/репозитория, automatic granularity, series toggles, watermark для current open/stale MR и unavailable approvals.

- [ ] **Шаг 2: Написать падающие тесты repository contribution**

Проверить добавленные/удалённые строки по месяцам и репозиториям, changed files, merged MR, reviews, active months, production/test/docs/other, code-area paths, excluded-file counts и просмотр несекретных rules.

- [ ] **Шаг 3: Написать падающие тесты source facts**

Проверить pageable kinds, source links, маркировку unmerged work как context-only и propagation repository/date filters во все запросы.

- [ ] **Шаг 4: Запустить тесты и подтвердить падение**

Команда: `cd frontend && npm test -- --run src/features/user/UserPage.test.tsx`

Ожидание: FAIL, потому что компоненты карточки отсутствуют.

- [ ] **Шаг 5: Реализовать карточку**

Использовать ECharts для timeline и доступные HTML tables для repository/source details. Сохранять filter params при переходах из списка и обратно.

- [ ] **Шаг 6: Проверить feature и весь frontend**

Команда: `cd frontend && npm test -- --run`

Ожидание: PASS.

- [ ] **Шаг 7: Сделать коммит**

```bash
git add frontend/src/features/user frontend/src/app/router.tsx
git commit -m "feat: add detailed developer contribution view"
```

### Задача 13: Локальный GitLab 19.3.6-ee в Docker и live-интеграционные тесты

**Файлы:**
- Создать: `compose.gitlab-integration.yaml`
- Создать: `.env.gitlab-integration.example`
- Создать: `scripts/gitlab-integration/wait-ready.sh`
- Создать: `scripts/gitlab-integration/seed.py`
- Создать: `scripts/gitlab-integration/run.sh`
- Создать: `backend/tests/gitlab_live/conftest.py`
- Создать: `backend/tests/gitlab_live/test_client_against_gitlab.py`
- Создать: `backend/tests/gitlab_live/test_full_sync_against_gitlab.py`
- Изменить: `backend/pyproject.toml`
- Изменить: `.gitignore`
- Изменить: `README.md`

**Интерфейсы:**
- Compose profile `gitlab-integration` добавляет test-only сервисы `gitlab`, `gitlab-seed` и `gitlab-integration-runner`; `gitlab` использует строго `gitlab/gitlab-ee:19.3.6-ee.0`, отдельные volumes и healthcheck, а обычный `docker compose up` эти сервисы не запускает.
- `seed.py --base-url URL --root-token TOKEN --output PATH` идемпотентно создаёт namespace `activity-integration`, три активных пользователя, bot/service user, три проекта, target-branch commits, merge/squash commits, direct commit, MR, discussion, approval и исключаемые generated/vendor/binary changes; затем атомарно пишет JSON manifest со стабильными GitLab ID/IID/SHA и ожидаемыми totals без токена.
- `GitLabClient(..., page_size=2)` в live-тесте обязан пройти более одной реальной страницы пользователей и проектов.
- `run.sh` поднимает профиль, ждёт readiness с настраиваемым timeout, получает только test-only root token внутри integration-среды, запускает seed и `pytest -m gitlab_integration`, повторяет seed и full sync для проверки идемпотентности. При timeout/failure он печатает диагностический status и ограниченный tail логов без credentials; при успехе останавливает test-only сервисы.
- Pytest marker `gitlab_integration` исключён из default test command и является отдельным обязательным release-gate.

- [ ] **Шаг 1: Написать падающие live-тесты GitLab-клиента**

В `test_client_against_gitlab.py` проверить точные version/edition `19.3.6-ee`, capability report и реальные DTO для users/projects/MR/commits/discussions/approvals/changes. Создать клиент с `page_size=2` и доказать, что результаты включают объекты со второй страницы без дублей.

- [ ] **Шаг 2: Написать падающий live-тест полного sync и отчёта**

В `test_full_sync_against_gitlab.py` прочитать manifest, выполнить sync в чистую PostgreSQL, проверить attribution, merged/direct deduplication, review/approval, excluded lines, source URLs, coverage и report totals из manifest. Повторить sync и проверить неизменность числа фактов и totals.

- [ ] **Шаг 3: Зарегистрировать отдельный test marker и подтвердить изоляцию набора**

Добавить marker `gitlab_integration` в `backend/pyproject.toml`, пометить весь `backend/tests/gitlab_live/` и настроить default pytest так, чтобы `cd backend && pytest -v` не требовал GitLab.

Команда: `cd backend && pytest --collect-only -q`

Ожидание: live-тесты распознаются, но исключаются из default selection; прямой `pytest -m gitlab_integration` завершается FAIL без integration environment.

- [ ] **Шаг 4: Реализовать изолированный Compose-профиль и readiness**

Добавить pinned GitLab EE service, test-only volumes/network, seed и integration-runner. `wait-ready.sh` должен проверять container health и `/-/readiness`, завершаться по timeout и не выводить credentials. Не добавлять GitLab в production/default services.

Команда: `docker compose -f compose.yaml -f compose.gitlab-integration.yaml --profile gitlab-integration config --quiet`

Ожидание: PASS; resolved image GitLab равен `gitlab/gitlab-ee:19.3.6-ee.0`.

- [ ] **Шаг 5: Реализовать идемпотентный seed**

Через GitLab API и Git over HTTP создать fixture из интерфейса задачи. Для тестового admin token использовать GitLab Rails runner только внутри контейнера; не писать token в manifest, stdout, git remote или файлы репозитория. Повторный seed должен находить/обновлять fixture по стабильным path/username и не дублировать активность.

- [ ] **Шаг 6: Реализовать единый runner и добиться прохождения live-suite**

Команда: `scripts/gitlab-integration/run.sh`

Ожидание: GitLab достигает ready, seed и reseed завершаются успешно, оба live-тестовых модуля PASS, повторный sync не создаёт дубликатов, после успешного запуска test-only containers остановлены.

- [ ] **Шаг 7: Проверить повторяемость с уже существующими volumes**

Команда: `scripts/gitlab-integration/run.sh`

Ожидание: второй полный запуск PASS на сохранённом GitLab volume; fixture IDs из manifest стабильны, activity facts и report totals не удваиваются. Скрипт документирует отдельный явный reset volumes для диагностики, но сам не удаляет их.

- [ ] **Шаг 8: Документировать требования и диагностику**

В README описать Docker resources, первый медленный startup, команду запуска, timeout override, расположение диагностических логов, безопасный reset только integration volumes и различие между mock, live-GitLab и Playwright suites. `.env.gitlab-integration.example` содержит только безопасные placeholder/generated значения.

- [ ] **Шаг 9: Сделать коммит**

```bash
git add compose.gitlab-integration.yaml .env.gitlab-integration.example scripts/gitlab-integration backend/tests/gitlab_live backend/pyproject.toml .gitignore README.md
git commit -m "test: add Dockerized GitLab integration suite"
```

### Задача 14: Сквозная проверка, эксплуатационная документация и подготовка релиза

**Файлы:**
- Создать: `frontend/tests/report-flow.spec.ts`
- Создать: `backend/tests/integration/test_full_sync_report.py`
- Изменить: `compose.yaml`
- Изменить: `.env.example`
- Изменить: `README.md`
- Создать: `docs/operations.md`

**Интерфейсы:**
- Результат: один документированный сценарий от локального GitLab до отчёта и инструкция production-конфигурации.
- Результат: health checks и порядок запуска, достаточные для `docker compose up`.

- [ ] **Шаг 1: Написать падающий backend integration test**

На детерминированных GitLab HTTP fixtures и PostgreSQL выполнить full sync; проверить list/card totals, exclusions, watermark, coverage warnings, idempotent retry и отсутствие raw diff/secrets в persistence/logs.

- [ ] **Шаг 2: Запустить integration test и подтвердить падение**

Команда: `cd backend && pytest tests/integration/test_full_sync_report.py -v`

Ожидание: FAIL, пока cross-feature fixture и wiring не завершены.

- [ ] **Шаг 3: Завершить интеграцию и провести тест**

Внести только минимальные изменения между модулями, необходимые для failing assertions.

Команда: `cd backend && pytest tests/integration/test_full_sync_report.py -v`

Ожидание: PASS.

- [ ] **Шаг 4: Написать падающий Playwright-сценарий**

Покрыть запуск sync, progress, список пользователей, произвольный период, выбор репозитория, сортировку по added lines, карточку человека, помесячный вклад и source link.

- [ ] **Шаг 5: Запустить Playwright и завершить wiring**

Команда: `cd frontend && npm run test:e2e`

Ожидание: до финального wiring — FAIL на первом незавершённом шаге; после исправлений — PASS.

- [ ] **Шаг 6: Документировать безопасную эксплуатацию**

Описать local GitLab, scopes токена, Docker secret/environment, project IDs, timezone, exclusion overrides, обязательную network isolation, первую/инкрементальную sync, backup/restore и token rotation. Явно указать, что метрики описывают GitLab-активность, а не являются вердиктом о производительности.

- [ ] **Шаг 7: Выполнить полную проверку**

```bash
cd backend && pytest -v
cd frontend && npm test -- --run
cd frontend && npm run build
cd frontend && npm run test:e2e
scripts/gitlab-integration/run.sh
docker compose config --quiet
docker compose -f compose.yaml -f compose.gitlab-integration.yaml --profile gitlab-integration config --quiet
git diff --check
```

Ожидание: все команды завершаются с кодом 0; нет failed tests, build errors, некорректного Compose или whitespace errors.

- [ ] **Шаг 8: Сделать коммит**

```bash
git add backend/tests/integration frontend/tests compose.yaml .env.example README.md docs/operations.md
git commit -m "test: validate GitLab activity analytics workflow"
```

## Критерии завершения плана

- До реализации созданы родительский GitHub Issue и 14 дочерних Issues, соответствующих задачам плана.
- Созданы все 14 task-коммитов; перед каждым прошли его фокусные проверки.
- Полная проверка задачи 14, включая live-интеграцию с Dockerized GitLab `19.3.6-ee`, проходит на финальном дереве.
- UI поддерживает синхронизацию, сортируемый список всех пользователей, выбор репозитория, произвольные даты в доступном окне и полную карточку из утверждённой спецификации.
- Не добавлены рейтинг, баллы, anomaly labels, внешние сервисы, авторизация, Celery или Redis.
- Финальная ветка проверена способом, выбранным при передаче плана в реализацию.
