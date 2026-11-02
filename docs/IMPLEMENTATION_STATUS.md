# Implementation and verification status

Version: **0.1.1 development preview**. Development and GitHub marketplace installation currently follow `main`.

0.1.1 fixes the native-settings protocol defect in 0.1.0: `garmin_settings_read` and `garmin_settings_update` now declare typed output schemas and return `structuredContent`. The read schema uses the required wire name `schema` without shadowing Pydantic's deprecated method. The settings action also returns structured output. A real stdio-client regression covers settings discovery, read, action/resource access and update with JSON Schema validation; the standalone smoke check now validates settings content as well. Native ChatGPT UI confirmation still depends on refreshing the installed copy and restarting its server.

Publication safety: the original repository's first commit tracked `.env`. That file has been removed from `main` and is now ignored; the local working copy is preserved. The plugin has been merged into `main`, and the separate `publish/garmin-personal` branch is being retired. The original credential remains in earlier `main` history, so the old key must be revoked/rotated. No history rewrite is implied by removing a file from the current commit.

## Implemented

- Seven official-API read-only Garmin MCP workflows and session-private original activity ZIP resources.
- Local credential resolution, hidden terminal setup and masked MCP App exposed from structured plugin settings.
- Official Garmin authentication with cache, refresh, sanitized errors and bounded HTTPS transport.
- Activity pagination, health normalization and source-aware reports with 7/28-day measured baselines.
- Portable manifests, repo-local marketplace, setup/analysis skills and GitHub installation documentation.
- Locked dependencies, CI matrix and standalone build jobs for macOS arm64 and Windows x64.
- Third-party notices, archive checksums and extracted-package smoke checks.

## Verification performed locally

- 38 automated tests passed, including end-to-end service/MCP workflows using synthetic Garmin HTTP responses and security/partial-data regressions.
- Ruff lint and Pyright: no errors.
- Source stdio MCP initialization/discovery/status/settings/resource handshake passed.
- Standalone macOS arm64 ZIP built (approximately 28 MB), checksum verified, safely extracted and launched from an unrelated working directory with Python and uv absent from the child process PATH.
- Masked UI exercised in a browser iframe using a simulated MCP Apps host and synthetic key: submit, app-only call, clearing and success state passed.
- Independent implementation review findings corrected with regression tests.

## Not verified or performed

- No real Garmin account calls: the provided local key was not used. Endpoint payload support is based on official client interfaces and synthetic fixtures, not universal real-account coverage.
- Native ChatGPT Desktop/Codex installation and actual structured-settings host interaction were not exercised.
- Windows standalone generation/execution and the GitHub CI matrix have not run here. The workflow is provided, not certified as passing.
- macOS developer signing/notarization, OpenAI public catalog approval and release publication were not performed. The source code has been pushed to GitHub and merged into `main`.
- FIT lap/record parsing, workout writes, scheduling and route import are outside this preview.

See [installation and release checks](INSTALL.md), [privacy](PRIVACY.md) and [execution decisions](superpowers/plans/progress.md).
