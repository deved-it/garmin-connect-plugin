# Garmin Personal

A local, read-only Garmin Connect plugin for ChatGPT Desktop and Codex. Explore activity, sleep, heart rate, HRV, stress and Body Battery through conversation, without handing your API key to a project-operated server.

**Status: 0.1.0 development preview.** The code is not an official Garmin or OpenAI product. GitHub release automation is provided; a build is not a published or certified release. Native-host installation/UI and real-account checks are separate from automated tests.

## What it does

- Read and filter activities; retrieve activity details and associated workouts.
- Download original activity ZIPs as private session-scoped MCP resources.
- Read selected wellness metrics, with explicit opt-in for menstrual-cycle records.
- Build partial-safe reports and measured 7/28-day baselines with sample counts.
- Configure a key in a masked settings form on compatible hosts, or with hidden terminal input.

It **cannot write to Garmin Connect**: no workout upload, scheduling, course import or watch synchronization. FIT files can be downloaded; comprehensive FIT lap/sensor parsing is not implemented. Unsupported Garmin JSON shapes are reported as unavailable rather than guessed.

## Install

See [complete installation instructions](docs/INSTALL.md).

- Standalone packages target **macOS Apple Silicon** and **Windows x64**. They contain Python and dependencies; users do not need Python or uv.
- Source installation requires **Python 3.12+ and uv**, and is the fallback for macOS Intel, Windows ARM64 and Linux.
- Public OpenAI catalog approval is not needed for local marketplace installation in supported clients. Actual menu availability depends on client version and account policy.

Quick start from a source checkout:

```sh
uv sync --locked
uv run --locked garmin-personal-plugin configure
uv run --locked garmin-personal-plugin status
```

Never paste your key in a chat or command-line argument. Create your personal key in [Garmin Connect settings](https://connect.garmin.com/app/settings/personalApiToken).

To load a development `.env`, set `GARMIN_PLUGIN_ROOT` to the checkout's absolute path. The plugin manifest sets it automatically. `.env` is deliberately not searched from arbitrary working directories. Copy [.env.example](.env.example) manually and edit locally.

## Example questions

- “Com’è cambiato il mio sonno nelle ultime quattro settimane?”
- “Confronta le mie corse di questa settimana con la precedente.”
- “Mostrami HRV e frequenza cardiaca a riposo, indicando quanti dati sono disponibili.”
- “Prepara un riepilogo del recupero senza inventare un punteggio.”

## Privacy

The key and token stay in local plaintext files protected by filesystem permissions. The plugin contacts Garmin directly. Requested tool results sent into the conversation are processed by OpenAI; local execution does not mean your conversation is offline. No project backend or telemetry. Read [privacy and data handling](docs/PRIVACY.md).

## Develop and verify

```sh
uv sync --locked --all-groups
uv run pytest --cov=garmin_connect_plugin --cov-report=term-missing
uv run ruff check .
uv run pyright
uv run python scripts/smoke_package.py --source-tree .
uv run python scripts/build_release.py --dry-run
```

Build natively on macOS arm64 or Windows x64:

```sh
uv run python scripts/build_release.py
```

The build refuses to overwrite an assembled output directory. Move an existing build out of the output path before rebuilding. Release candidates must pass extracted-package smoke tests and the local opt-in real-account checklist in [installation and release verification](docs/INSTALL.md#release-verification).

## Official references

- [Garmin Personal API](https://developer.garmin.com/gc-developer-program/personal/personal-api/)
- [Official Garmin Python client](https://github.com/garmin/connect-personal-api-python)
- [OpenAI desktop-only plugins](https://developers.openai.com/plugins/deploy/desktop-only)
- [OpenAI packaging and local marketplaces](https://developers.openai.com/plugins/build/plugins)
- [OpenAI structured settings](https://github.com/openai/mcp-extensions/blob/main/docs/spec.md#structured-settings)

Garmin and Garmin Connect are trademarks of Garmin. Data is sourced from the user's Garmin account. Generated interpretations are not Garmin measurements. Licensed under Apache-2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
