# Execution ledger — Garmin Personal plugin

Plan: 2026-11-02-garmin-personal-plugin.md

Ruling: execute inline after user's “vai”; preserve the approved spec and plan.
Ruling: use the dedicated feat/garmin-personal branch in the current checkout. The repository has no product files or existing commits to isolate; preserve the user's ignored .env without reading its value.
Ruling: no invented host credential API. Verify MCP App visibility and settings support against official schemas before implementing the masked configuration UI. Never expose save credentials as a model-visible tool.
Ruling: tests cover observable behavior, not document wording or literal framework metadata.
Ruling: source uses the official Garmin package; inspect installed signatures before implementing adapters.
Pre-flight: gateway consumes models originally scheduled later; define request models with the gateway task to avoid forward imports. Token/cache and resource boundaries remain independently injectable.

Tasks 1–8: initial implementation present; 19 behavioral tests passed (2026-11-02). Further review and acceptance remain.
Task 9: seven read-only tools, structured settings, masked app-only key save and skills implemented; 21 tests passed. Native-host UI verification remains.
Ruling: pin MCP to >=1.26,<2: current 2.x removed the FastMCP import contract. The lock resolves 1.30.0.
Ruling: keep marketplace template at root; this environment prohibits writes under root .agents. Release assembly generates its own marketplace tree; source instructions tell users how to register it.
Ruling: do not test document wording. Use runtime MCP and resource tests instead.
Ruling: Garmin's official HttpError does not retain Retry-After headers; the adapter cannot honor them without a bounded HTTP session. Review this before release.

## Final implementation state (2026-11-02)

Tasks 1–9: implemented. Task 10: build scripts, native-platform CI matrix, documentation, licenses and local macOS artifact implemented. Task 11: automated acceptance scenarios implemented and passing. Native Windows build, actual ChatGPT Desktop installation/settings, real-account validation, signing and public publishing remain unverified/not performed; these are not represented as successful.

Final: fixed all independent review findings with RED→GREEN regressions: dated unknown JSON, nested statistical lists, all-null daily payloads, process-variable alias precedence, full 91-date activity range, pagination, per-record recognition, and activity-only capped-report status. Added atomic source ingestion regression so a failed source contributes no residual records.

Final: official Garmin client runs through BoundedSession. It pins the HTTPS origin, blocks redirects, bounds decompressed response bytes, preserves a capped Retry-After and omits upstream response text. HTTP auth retries once; transient failures have a bounded retry budget.

Final: MCP output explicitly declares object schemas. The server reports plugin version 0.1.0. Oversized structured results fail with an explicit smaller-range instruction instead of silent truncation.

Final: source MCP handshake passed. Frozen macOS MCP handshake passed with PATH empty and unrelated cwd. Final ZIP checksum, traversal-safe extraction, settings capability and UI resource smoke passed.

Final: masked configuration form was exercised in a browser iframe with a simulated MCP Apps host and synthetic key; password input, correct app-only tools/call, success state and input clearing passed. This does not establish actual ChatGPT host compatibility.

Final: 38 tests passed; Ruff and Pyright exited cleanly. Coverage before the final archive-extraction regression was 85%. Real-account tests were not run and the user's .env contents were never exposed.

Ruling: add a small explicit HTTP boundary rather than changing Garmin's official client — preserves the client while making byte limits, destination pinning and Retry-After enforceable; cost is maintaining Session-compatible transport tests.
Ruling: allow only resolved internal PyInstaller runtime symlinks during assembly, then dereference them in the shipped copy; reject external/broken links. Cost is a larger macOS archive, avoiding extraction-dependent symlink behavior.
Ruling: report activity pagination is capped at 10 pages and reports partial coverage at the cap. Cost is an explicit additional query for unusually large histories, not silently incomplete analysis.
Ruling: standalone artifacts are unsigned development candidates. Native signing certificates, OpenAI allowlisting and publication are external steps, not assumed authority.
Ruling: the approved generator successfully created the actual repo .agents marketplace catalog. The earlier template-only constraint is resolved; direct Git-backed distribution can include the catalog.

Security finding: `.env` was already tracked in the pre-existing `f6eb947` initial commit. Removed only from the index, not from disk. Publishing this ancestry would disclose the original credential file. Prepare an independent root publication commit/branch from the credential-free index; preserve existing refs and history locally. Never push old refs or use `--all`/`--mirror` for publication.
