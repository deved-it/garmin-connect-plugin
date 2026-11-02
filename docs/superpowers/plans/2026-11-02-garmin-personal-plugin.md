# Garmin Personal Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a privacy-preserving, read-only Garmin Connect Personal plugin that runs locally in ChatGPT Desktop and Codex, supports conversational activity and health analysis, and ships autonomous macOS Apple Silicon and Windows x64 artifacts.

**Architecture:** A Python 3.12 MCP server runs over stdio and wraps Garmin's official Personal API client behind focused credential, gateway, normalization, and report services. OpenAI manifests and two analysis/setup skills package the server as a desktop-only plugin; platform release jobs freeze the same application into self-contained executables.

**Tech Stack:** Python 3.12+, `mcp`, `garmin-connect-personal-api-python`, `pydantic`, `python-dotenv`, `platformdirs`, `uv`, `pytest`, `pytest-cov`, `respx`, `ruff`, `pyright`, PyInstaller, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-02-garmin-personal-plugin-design.md`

## Global Constraints

- Use only the official, pull-only Garmin Connect Personal API; every MCP tool is read-only.
- Run locally over MCP stdio; no project-operated server, database, or telemetry.
- Support Python 3.12 or newer for source installations.
- Prefer credential sources in this order: app-only secret, `GARMIN_CONNECT_PERSONAL_API_KEY`, `GARMIN_PERSONAL_API_KEY`, private key file.
- Never expose API keys, bearer tokens, health payloads, or credential paths in logs, errors, tool metadata, or results.
- Target current stable ChatGPT Desktop and Codex; declare `requires_local_executor: true`.
- Ship autonomous release artifacts for macOS Apple Silicon and Windows x64; source install is the fallback elsewhere.
- Default report history is 28 days, maximum 90 days; default timezone is the local system timezone.
- All dates are ISO `YYYY-MM-DD`; preserve Garmin timestamps, units, and provenance.
- Female-health data is fetched only when explicitly requested.
- Do not add workout/course write tools, medical diagnosis, recovery scores, cloud sync, or scheduled execution.
- Use small focused modules, typed public interfaces, TDD, and dependency injection at network/filesystem boundaries.

## Review Focus

- A key or token embedded inside a nested exception must be redacted from status, logs, and MCP results; Task 2 adds an adversarial secret-leak test.
- A report spanning a daylight-saving transition must keep Garmin calendar dates intact while computing `partial_day` in the requested timezone; Task 7 adds the boundary test.
- Garmin may return zero, `null`, an empty list, malformed JSON, or an unexpected shape; Task 4 and Task 6 pin distinct handling for each.
- A single failed metric must not erase successful metrics or make an empty activity list look like a rest day; Task 7 adds partial-source tests.
- A packaged executable may start outside the plugin directory and without Python on `PATH`; Task 10 smoke-tests both release layouts from an unrelated working directory.

---

## File Map

- `pyproject.toml`, `uv.lock`: package metadata, locked runtime/dev/build dependencies, CLI entry points, tool configuration.
- `src/garmin_connect_plugin/config.py`: immutable paths/settings and safe environment loading.
- `src/garmin_connect_plugin/credentials.py`: credential discovery and hidden-input configuration.
- `src/garmin_connect_plugin/redaction.py`: recursive secret-safe messages and logging filter.
- `src/garmin_connect_plugin/auth.py`: token acquisition, cache inspection, one forced refresh on `401`.
- `src/garmin_connect_plugin/errors.py`: stable public error codes and Garmin/HTTP exception mapping.
- `src/garmin_connect_plugin/gateway.py`: typed boundary around the official Garmin client.
- `src/garmin_connect_plugin/models.py`: request/result/status Pydantic models shared by services and MCP.
- `src/garmin_connect_plugin/normalize.py`: payload minimization and normalized activity/health records.
- `src/garmin_connect_plugin/activity_service.py`: activity listing/detail/workout/file workflows.
- `src/garmin_connect_plugin/health_service.py`: metric registry and bounded health queries.
- `src/garmin_connect_plugin/report_service.py`: orchestration, source coverage, baselines, partial-day semantics.
- `src/garmin_connect_plugin/resources.py`: private temporary activity resources and cleanup.
- `src/garmin_connect_plugin/server.py`: MCP server, tool schemas, annotations, structured results.
- `src/garmin_connect_plugin/cli.py`: `serve`, `configure`, and `status` commands.
- `plugin.json`, `mcp.json`: portable desktop-only plugin and local stdio server declarations.
- `skills/setup/SKILL.md`, `skills/garmin-analysis/SKILL.md`: safe configuration and analysis workflows.
- `scripts/build_release.py`: deterministic platform package assembly.
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`: validation and autonomous artifact builds.
- `README.md`, `docs/INSTALL.md`, `docs/PRIVACY.md`, `.env.example`, `.gitignore`, `LICENSE`: user distribution and policy documentation.
- `tests/`: mirrors the focused source modules plus manifest, skill, packaging, and end-to-end MCP tests.

### Task 1: Project skeleton and executable stdio server

**Files:**
- Create: `pyproject.toml`
- Create: `src/garmin_connect_plugin/__init__.py`
- Create: `src/garmin_connect_plugin/__main__.py`
- Create: `src/garmin_connect_plugin/cli.py`
- Create: `src/garmin_connect_plugin/server.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_server_smoke.py`

**Interfaces:**
- Consumes: none.
- Produces: `cli.main(argv: Sequence[str] | None = None) -> int`; `server.create_server(services: ServiceContainer | None = None) -> FastMCP`; console script `garmin-personal-plugin`.

- [ ] **Step 1: Write failing CLI and MCP initialization tests**

Add `test_cli_help_exits_zero`, `test_cli_serve_uses_stdio`, and `test_server_initializes_with_stable_name_and_version`. Assert command names `serve`, `configure`, `status`, server name `garmin-personal`, and import-safe startup without network access.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `uv run pytest tests/test_cli.py tests/test_server_smoke.py -v`

Expected: FAIL because the package and entry points do not exist.

- [ ] **Step 3: Add package metadata and the minimal server/CLI interfaces**

Declare Python `>=3.12`, runtime dependencies, dev/build groups, typed package data, and entry point. Implement only initialization and command dispatch; `serve` starts MCP stdio and the other commands return a clear not-yet-implemented exit code used only until their owning tasks land.

- [ ] **Step 4: Run quality checks for the skeleton**

Run: `uv lock && uv sync --all-groups && uv run pytest tests/test_cli.py tests/test_server_smoke.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/garmin_connect_plugin tests/test_cli.py tests/test_server_smoke.py
git commit -m "feat: scaffold Garmin Personal MCP server"
```

### Task 2: Local configuration, credential resolution, and redaction

**Files:**
- Create: `src/garmin_connect_plugin/config.py`
- Create: `src/garmin_connect_plugin/credentials.py`
- Create: `src/garmin_connect_plugin/redaction.py`
- Modify: `src/garmin_connect_plugin/cli.py`
- Create: `tests/test_config.py`
- Create: `tests/test_credentials.py`
- Create: `tests/test_redaction.py`
- Create: `.env.example`
- Create: `.gitignore`

**Interfaces:**
- Consumes: `cli.main(...)` from Task 1.
- Produces: `Settings.load(plugin_root: Path | None = None) -> Settings`; `CredentialResolver.resolve(app_secret: str | None = None) -> ResolvedCredential`; `configure_key(destination: Path, input_fn: Callable[[str], str] = getpass) -> Path`; `redact(value: object, secrets: Collection[str] = ()) -> object`; `RedactingFilter`.

- [ ] **Step 1: Write failing credential precedence and private-file tests**

Assert precedence app secret → `GARMIN_CONNECT_PERSONAL_API_KEY` → `GARMIN_PERSONAL_API_KEY` → configured key file; empty explicit sources raise `NOT_CONFIGURED`; `.env` is loaded only from the resolved plugin root; `configure` never accepts a key argument and creates a POSIX file with mode `0600`.

- [ ] **Step 2: Write the adversarial redaction tests from Review Focus**

Use a synthetic key and token nested in mappings, sequences, exception causes, URLs, and log records. Assert neither full secret nor recognizable prefix appears after redaction, while non-secret diagnostic fields remain.

- [ ] **Step 3: Run focused tests and verify failure**

Run: `uv run pytest tests/test_config.py tests/test_credentials.py tests/test_redaction.py -v`

Expected: FAIL on missing modules.

- [ ] **Step 4: Implement settings, resolver, secure configuration, and recursive redaction**

Use `platformdirs.user_config_path("garmin-personal")`; store only the key in the private file; never include the value in `ResolvedCredential.__repr__`. Add the working `configure` CLI command with hidden input and safe success text.

- [ ] **Step 5: Run focused and project checks**

Run: `uv run pytest tests/test_config.py tests/test_credentials.py tests/test_redaction.py tests/test_cli.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add .env.example .gitignore src/garmin_connect_plugin tests
git commit -m "feat: add secure local credential configuration"
```

### Task 3: Authentication lifecycle and stable error model

**Files:**
- Create: `src/garmin_connect_plugin/errors.py`
- Create: `src/garmin_connect_plugin/auth.py`
- Create: `tests/test_errors.py`
- Create: `tests/test_auth.py`

**Interfaces:**
- Consumes: `ResolvedCredential`, `Settings`, and `redact(...)` from Task 2; official `PersonalApiAuthenticator`.
- Produces: `ErrorCode` enum with the nine spec codes; `PluginError(code: ErrorCode, message: str, retryable: bool, details: Mapping[str, object] | None = None)`; `TokenManager.get_token(force_refresh: bool = False) -> TokenInfo`; `TokenManager.run_with_refresh(operation: Callable[[str], T]) -> T`; `TokenManager.cache_status() -> TokenCacheStatus`.

- [ ] **Step 1: Write failing error mapping tests**

Assert missing credentials, `400`, `401`, `403`, `429` with `Retry-After`, `5xx`, timeout/connection failures, malformed response, and unexpected exception map to exact public codes and retryability without leaking response bodies or credentials.

- [ ] **Step 2: Write failing token lifecycle tests**

Assert valid cached token reuse, forced refresh, one refresh plus one retry after `401`, no second retry, and no retry for `403`, invalid input, or non-auth errors.

- [ ] **Step 3: Run focused tests and verify failure**

Run: `uv run pytest tests/test_errors.py tests/test_auth.py -v`

Expected: FAIL on missing error/auth interfaces.

- [ ] **Step 4: Implement the stable error and token interfaces**

Adapt the official authenticator behind injected factories and clocks. Redact every public message and detail at construction time. Keep retry/backoff policy out of this task except the single auth refresh.

- [ ] **Step 5: Run focused and regression tests**

Run: `uv run pytest tests/test_errors.py tests/test_auth.py tests/test_redaction.py tests/test_credentials.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add src/garmin_connect_plugin/errors.py src/garmin_connect_plugin/auth.py tests/test_errors.py tests/test_auth.py
git commit -m "feat: manage Garmin authentication lifecycle"
```

### Task 4: Garmin gateway and bounded retry policy

**Files:**
- Create: `src/garmin_connect_plugin/gateway.py`
- Create: `tests/test_gateway.py`

**Interfaces:**
- Consumes: `TokenManager.run_with_refresh(...)`, `PluginError`, official `GarminPersonalApiClient`.
- Produces: `GarminGateway` methods `profile()`, `activities(query: ActivityQuery)`, `activity(activity_id: str)`, `activity_workouts(activity_id: str)`, `activity_file(activity_id: str)`, and `health(metric: HealthMetric, query: HealthQuery)`, each returning `JsonValue | bytes`; `RetryPolicy.run(operation: Callable[[], T]) -> T`.

- [ ] **Step 1: Write failing gateway delegation tests**

Parameterize every official client method used by the metric registry. Assert exact argument conversion, inclusive dates, pagination, maximum limits, and that all calls pass through token refresh and error mapping.

- [ ] **Step 2: Add malformed/zero/null/empty response tests from Review Focus**

Assert the gateway preserves legitimate `0`, `None`, and empty collections for the normalizer, but raises `UNEXPECTED_RESPONSE` for non-JSON where JSON is promised and for invalid download bytes.

- [ ] **Step 3: Add bounded retry tests**

With an injected sleeper, assert at most two retries for retryable `429`/`5xx`/network errors, `Retry-After` is capped, and no retry occurs for other codes.

- [ ] **Step 4: Run focused tests and verify failure**

Run: `uv run pytest tests/test_gateway.py -v`

Expected: FAIL on missing gateway.

- [ ] **Step 5: Implement the gateway and retry policy**

Keep endpoint knowledge in the official client and a single explicit `HealthMetric` registry. Do not log payloads. Cap per-call timeout and sleep values in settings.

- [ ] **Step 6: Run focused and regression checks**

Run: `uv run pytest tests/test_gateway.py tests/test_auth.py tests/test_errors.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/garmin_connect_plugin/gateway.py tests/test_gateway.py
git commit -m "feat: wrap official Garmin Personal API client"
```

### Task 5: Typed models, validation, and safe status/profile service

**Files:**
- Create: `src/garmin_connect_plugin/models.py`
- Create: `src/garmin_connect_plugin/status_service.py`
- Create: `tests/test_models.py`
- Create: `tests/test_status_service.py`

**Interfaces:**
- Consumes: `Settings`, `CredentialResolver`, `TokenManager`, `GarminGateway`.
- Produces: `ActivityQuery`, `HealthQuery`, `HealthMetric`, `SourceStatus`, `ToolEnvelope[T]`, `PluginStatus`; `StatusService.status(validate_connection: bool = False) -> PluginStatus`; `StatusService.profile() -> ToolEnvelope[dict[str, JsonValue]]`.

- [ ] **Step 1: Write failing model validation tests**

Assert ISO date parsing, inclusive ordering, activity limit `1..100`, report history `1..90`, non-empty metric sets, numeric/string activity IDs, timezone validation, and explicit opt-in for female-health metrics.

- [ ] **Step 2: Write failing status/profile tests**

Assert default status performs no network call, exposes only credential source kind/token expiry/version/prerequisites, validation uses one minimal profile call, and profile allowlists useful fields while dropping unknown/private fields.

- [ ] **Step 3: Run focused tests and verify failure**

Run: `uv run pytest tests/test_models.py tests/test_status_service.py -v`

Expected: FAIL on missing models/services.

- [ ] **Step 4: Implement models and status/profile service**

Use frozen Pydantic result models and stable string enums. Return public `PluginError` envelopes rather than raw exceptions.

- [ ] **Step 5: Run focused and regression checks**

Run: `uv run pytest tests/test_models.py tests/test_status_service.py tests/test_credentials.py tests/test_auth.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add src/garmin_connect_plugin/models.py src/garmin_connect_plugin/status_service.py tests/test_models.py tests/test_status_service.py
git commit -m "feat: validate requests and expose safe connection status"
```

### Task 6: Activity and health normalization services

**Files:**
- Create: `src/garmin_connect_plugin/normalize.py`
- Create: `src/garmin_connect_plugin/activity_service.py`
- Create: `src/garmin_connect_plugin/health_service.py`
- Create: `tests/fixtures/garmin/README.md`
- Create: `tests/test_normalize.py`
- Create: `tests/test_activity_service.py`
- Create: `tests/test_health_service.py`

**Interfaces:**
- Consumes: request/result models and `GarminGateway`.
- Produces: `normalize_activity(payload: JsonValue) -> NormalizedActivity`; `normalize_health(metric: HealthMetric, payload: JsonValue) -> NormalizedSource`; `ActivityService.list(query: ActivityQuery) -> ToolEnvelope[ActivityPage]`; `ActivityService.get(activity_id: str, include_workout: bool = False) -> ToolEnvelope[ActivityDetail]`; `HealthService.get(query: HealthQuery) -> ToolEnvelope[HealthResult]`.

- [ ] **Step 1: Write failing fixture-minimization and normalization tests**

Create synthetic, license-safe fixtures modeled on documented shapes. Assert IDs, dates, timestamps, units, provenance and unknown fields; prove no email, full name, location history unrelated to an activity, or raw unrequested field survives normalization.

- [ ] **Step 2: Add zero/null/empty/unexpected-shape tests from Review Focus**

For each representative metric, assert zero stays measured zero, `null` stays missing, a successful empty list stays empty, and malformed/unrecognized structures return source status `unavailable` with `UNEXPECTED_RESPONSE` rather than fabricated values.

- [ ] **Step 3: Write failing activity and health orchestration tests**

Assert activity pagination metadata, optional workout retrieval, metric-to-endpoint dispatch, explicit female-health opt-in, per-source statuses, and partial success when one metric fails.

- [ ] **Step 4: Run focused tests and verify failure**

Run: `uv run pytest tests/test_normalize.py tests/test_activity_service.py tests/test_health_service.py -v`

Expected: FAIL on missing normalization/services.

- [ ] **Step 5: Implement minimal normalization and services**

Keep raw payload access private to normalizers. Use allowlists plus an `extra` map only for documented, safe fields needed for future-compatible analysis.

- [ ] **Step 6: Run focused and regression checks**

Run: `uv run pytest tests/test_normalize.py tests/test_activity_service.py tests/test_health_service.py tests/test_gateway.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/garmin_connect_plugin tests/fixtures tests/test_normalize.py tests/test_activity_service.py tests/test_health_service.py
git commit -m "feat: normalize Garmin activity and health data"
```

### Task 7: Coherent multi-source report and baselines

**Files:**
- Create: `src/garmin_connect_plugin/report_service.py`
- Create: `tests/test_report_service.py`

**Interfaces:**
- Consumes: `ActivityService`, `HealthService`, normalized models.
- Produces: `ReportRequest(reference_date: date, history_days: int = 28, sections: frozenset[ReportSection], timezone: ZoneInfo)`; `ReportService.build(request: ReportRequest) -> ToolEnvelope[GarminReport]` with `status`, `fetched_at`, `range`, `partial_day`, `sources`, `days`, `baselines`, and `activities`.

- [ ] **Step 1: Write failing baseline tests**

Assert 7/28-day baselines exclude the reference date, preserve sample counts, ignore `null` but include zero, and report insufficient coverage instead of extrapolating.

- [ ] **Step 2: Add partial-source semantics from Review Focus**

Assert one failed source yields `PARTIAL_RESULT` while successful data remains; an activities error plus empty array is not labeled rest; an entirely failed fetch is unavailable and cannot overwrite a previously valid in-memory result.

- [ ] **Step 3: Add partial-day and DST boundary tests from Review Focus**

Inject clock/timezone. Assert today is partial before local midnight, past dates are complete, future dates are invalid, and a Europe/Rome DST transition never shifts Garmin calendar dates.

- [ ] **Step 4: Run focused tests and verify failure**

Run: `uv run pytest tests/test_report_service.py -v`

Expected: FAIL on missing report service.

- [ ] **Step 5: Implement report orchestration and pure baseline functions**

Fetch only requested sections, default to the core activity/sleep/HRV/heart-rate/stress/Body Battery set, and keep per-source coverage/errors. Do not calculate a proprietary recovery score.

- [ ] **Step 6: Run focused and regression checks**

Run: `uv run pytest tests/test_report_service.py tests/test_health_service.py tests/test_activity_service.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/garmin_connect_plugin/report_service.py tests/test_report_service.py
git commit -m "feat: build partial-safe Garmin analysis reports"
```

### Task 8: Private activity-file resources

**Files:**
- Create: `src/garmin_connect_plugin/resources.py`
- Modify: `src/garmin_connect_plugin/activity_service.py`
- Create: `tests/test_resources.py`
- Modify: `tests/test_activity_service.py`

**Interfaces:**
- Consumes: `GarminGateway.activity_file(...)`, `ActivityService`.
- Produces: `ActivityResourceStore.create(activity_id: str, content: bytes) -> ActivityResource`; `ActivityResourceStore.read(uri: str) -> bytes`; `ActivityResourceStore.cleanup() -> None`; `ActivityService.file(activity_id: str) -> ToolEnvelope[ActivityResource]`.

- [ ] **Step 1: Write failing private-resource tests**

Assert ZIP signature validation, private temporary directory permissions, opaque `garmin-activity://<id>/<nonce>` URI, no arbitrary path input, no overwrite, cleanup idempotence, and rejection of oversized or invalid downloads.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/test_resources.py tests/test_activity_service.py -v`

Expected: FAIL on missing resource store/file method.

- [ ] **Step 3: Implement the resource store and activity-file flow**

Keep the filesystem path in private server state; expose only URI, media type, byte size, activity ID, and expiry metadata. Register process-exit cleanup without deleting user-owned paths.

- [ ] **Step 4: Run focused and regression checks**

Run: `uv run pytest tests/test_resources.py tests/test_activity_service.py -v && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add src/garmin_connect_plugin/resources.py src/garmin_connect_plugin/activity_service.py tests/test_resources.py tests/test_activity_service.py
git commit -m "feat: expose downloaded activities as private resources"
```

### Task 9: MCP tools, manifests, configuration app, and skills

**Files:**
- Modify: `src/garmin_connect_plugin/server.py`
- Create: `src/garmin_connect_plugin/container.py`
- Create: `plugin.json`
- Create: `mcp.json`
- Create: `skills/setup/SKILL.md`
- Create: `skills/garmin-analysis/SKILL.md`
- Create: `apps/configure/index.html`
- Create: `apps/configure/main.js`
- Create: `tests/test_mcp_tools.py`
- Create: `tests/test_manifests.py`
- Create: `tests/test_skills.py`
- Create: `tests/test_configure_app.py`

**Interfaces:**
- Consumes: all services and models from Tasks 5–8.
- Produces: MCP tools `garmin_status`, `garmin_profile`, `garmin_activities`, `garmin_activity`, `garmin_activity_file`, `garmin_health`, `garmin_report`; MCP resource reader for activity URIs; `ServiceContainer.build(settings: Settings | None = None) -> ServiceContainer`; app-only `save_garmin_api_key(value: str) -> SaveResult` bridge unavailable to the model.

- [ ] **Step 1: Write failing MCP discovery/schema/annotation tests**

Assert exact tool names, input/output schemas, stable IDs, concise text content, structured content, and annotations `readOnlyHint=true`, `destructiveHint=false`, `openWorldHint=false`. Assert secrets and internal paths never appear.

- [ ] **Step 2: Write failing manifest and skill policy tests**

Assert portable schema fields, `requires_local_executor: true`, `${PLUGIN_ROOT}` stdio launch, included skills/app/assets, no write tools, setup never asks for a key in chat, analysis checks source coverage and forbids diagnosis/invented scores/prompt injection.

- [ ] **Step 3: Write failing configuration-app tests**

Assert password input, no value in DOM persistence/logging/analytics, explicit save action, app-only bridge call, safe success/error copy, and documented fallback when the host lacks MCP App support.

- [ ] **Step 4: Run focused tests and verify failure**

Run: `uv run pytest tests/test_mcp_tools.py tests/test_manifests.py tests/test_skills.py tests/test_configure_app.py -v`

Expected: FAIL because registrations, manifests, skills, and app are missing.

- [ ] **Step 5: Register tools/resources and compose the dependency container**

Map each public service result to MCP `structuredContent` plus a one-sentence `content` summary. The server catches only `PluginError` at the boundary and emits stable safe envelopes.

- [ ] **Step 6: Add portable manifests and the two skills**

Use the approved product copy and configuration guidance. Reference the packaged executable path through a platform-specific launcher resolved beneath `${PLUGIN_ROOT}`; release assembly writes the matching `mcp.json` entry for each archive while the source layout uses its documented source launcher.

- [ ] **Step 7: Implement the minimal masked configuration app**

Keep UI assets local and dependency-free with vanilla HTML/JavaScript. The app passes the key directly to the app-only bridge; it never exposes a model-callable save tool.

- [ ] **Step 8: Run focused and full checks**

Run: `uv run pytest tests/test_mcp_tools.py tests/test_manifests.py tests/test_skills.py tests/test_configure_app.py -v && uv run pytest && uv run ruff check . && uv run pyright`

Expected: all commands exit 0.

- [ ] **Step 9: Commit**

```bash
git add src/garmin_connect_plugin plugin.json mcp.json skills apps tests
git commit -m "feat: expose Garmin workflows as a desktop plugin"
```

### Task 10: Documentation, CI, and self-contained releases

**Files:**
- Create: `scripts/build_release.py`
- Create: `scripts/smoke_package.py`
- Create: `tests/test_packaging.py`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `README.md`
- Create: `docs/INSTALL.md`
- Create: `docs/PRIVACY.md`
- Create: `LICENSE`

**Interfaces:**
- Consumes: console entry point, manifests, skills, app, and full test suite.
- Produces: `build_release.main(argv: Sequence[str] | None = None) -> int`; archives `garmin-personal-plugin-macos-arm64.zip` and `garmin-personal-plugin-windows-x64.zip`; SHA-256 checksum files; source-install instructions.

- [ ] **Step 1: Write failing package-content and launch tests**

Assert archives contain manifests, skills, app assets, license, notices, platform executable/launcher, and no `.env`, caches, tests, source secrets, user paths, or unexpected binaries. Extract to a temporary directory and start MCP discovery from an unrelated working directory with `PATH` lacking Python/`uv`.

- [ ] **Step 2: Add documentation contract tests**

Assert README/install docs cover macOS Apple Silicon, Windows x64, source fallback, key creation, masked UI, `configure`, `.env`, `garmin_status`, update, uninstall, read-only limitations, troubleshooting, privacy, and official Garmin/OpenAI attribution.

- [ ] **Step 3: Run focused tests and verify failure**

Run: `uv run pytest tests/test_packaging.py -v`

Expected: FAIL because build scripts, workflows, and documentation are missing.

- [ ] **Step 4: Implement deterministic platform packaging**

Use PyInstaller one-folder mode built natively on `macos-14` and `windows-latest`; assemble the portable plugin around the frozen executable; generate checksums; fail closed if secret-pattern or denylist scans match. Do not claim code signing/notarization until certificates exist.

- [ ] **Step 5: Add CI and release workflows**

CI runs tests, coverage, Ruff, Pyright, manifest/skill checks, and secret scanning. Tagged release jobs build natively, run package smoke tests, upload both archives/checksums, and require no Garmin credential.

- [ ] **Step 6: Write installation, privacy, troubleshooting, and release documentation**

Describe that health data passes from Garmin to the local plugin and then only the requested result is provided to ChatGPT/Codex for the conversation. Document the opt-in manual real-account release check without storing results or credentials.

- [ ] **Step 7: Run complete local verification**

Run: `uv run pytest --cov=garmin_connect_plugin --cov-report=term-missing && uv run ruff check . && uv run pyright && uv run python scripts/build_release.py --dry-run && uv run python scripts/smoke_package.py --source-tree .`

Expected: tests pass, coverage meets the configured threshold, lint/type checks exit 0, dry-run enumerates only approved files, and source-tree smoke discovery succeeds.

- [ ] **Step 8: Run clean platform release verification in CI**

Run: trigger the GitHub Actions workflow on a release-candidate tag.

Expected: both platform jobs build, scan, extract, launch, discover all seven read-only tools, verify checksums, and upload artifacts without credentials.

- [ ] **Step 9: Perform the opt-in Garmin integration checklist locally**

Run: install the candidate artifact, configure a maintainer key through hidden input, validate profile, activities, sleep, HRV, heart rate, stress, Body Battery, partial report, and one activity file; record only pass/fail, endpoint, plugin version, and timestamp.

Expected: core sources succeed or a Garmin-unavailable source is accurately reported; no personal payload or credential is retained.

- [ ] **Step 10: Commit**

```bash
git add scripts tests/test_packaging.py .github README.md docs/INSTALL.md docs/PRIVACY.md LICENSE
git commit -m "build: ship autonomous Garmin plugin releases"
```

### Task 11: Final end-to-end acceptance and release readiness

**Files:**
- Create: `tests/test_acceptance.py`
- Modify: only files implicated by acceptance failures.

**Interfaces:**
- Consumes: complete plugin package.
- Produces: a passing acceptance suite and release checklist; no new product interface.

- [ ] **Step 1: Write acceptance scenarios against an in-process fake Garmin gateway**

Cover: first run without credentials; configured status; activities; activity detail/workout; private activity resource; core health metrics; 28-day report/baselines; partial result; expired key; rate limit; malformed payload; explicit female-health request; and proof that no write tool exists.

- [ ] **Step 2: Run acceptance tests and capture failures**

Run: `uv run pytest tests/test_acceptance.py -v`

Expected: any gap fails with an assertion tied to a user-visible requirement.

- [ ] **Step 3: Fix only acceptance gaps through focused TDD**

For each failure, add the smallest owning-module regression test before changing implementation; do not broaden v1 scope.

- [ ] **Step 4: Run the complete verification matrix**

Run: `uv run pytest --cov=garmin_connect_plugin --cov-report=term-missing && uv run ruff check . && uv run pyright && uv run python scripts/build_release.py --dry-run && uv run python scripts/smoke_package.py --source-tree .`

Expected: every command exits 0; no warnings about credentials, manifests, missing files, or unsupported write behavior.

- [ ] **Step 5: Review workspace for accidental secrets and untracked release inputs**

Run: `git status --short && git diff --check && git grep -nE '(GARMIN_(CONNECT_)?PERSONAL_API_KEY=.+|Authorization: (ApiKey|Bearer) .+)' -- ':!docs/superpowers/**' ':!.env.example'`

Expected: only intended changes; no whitespace errors; secret scan returns no matches.

- [ ] **Step 6: Commit**

```bash
git add tests/test_acceptance.py
git commit -m "test: verify Garmin plugin acceptance workflows"
```
