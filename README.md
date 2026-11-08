# Garmin Personal

A local, read-only Garmin Connect plugin for ChatGPT Desktop and Codex. Explore activity, sleep, heart rate, HRV, stress and Body Battery through conversation, without handing your API key to a project-operated server.

**Status: 0.1.3 development preview.** Every push to `main` automatically creates a patch-version commit. The code is not an official Garmin or OpenAI product. GitHub release automation is provided; a build is not a published or certified release. Native-host installation/UI and real-account checks are separate from automated tests.

## What it does

- Read and filter activities; retrieve activity details and associated workouts.
- Download original activity ZIPs as private session-scoped MCP resources.
- Read selected wellness metrics, with explicit opt-in for menstrual-cycle records.
- Build partial-safe reports and measured 7/28-day baselines with sample counts.
- Configure a key in a masked settings form on compatible hosts, or with hidden terminal input.

It **cannot write to Garmin Connect**: no workout upload, scheduling, course import or watch synchronization. FIT files can be downloaded; comprehensive FIT lap/sensor parsing is not implemented. Unsupported Garmin JSON shapes are reported as unavailable rather than guessed.

## Install

### From GitHub — recommended

You do not need to clone this repository, download a ZIP manually or install **Codex CLI**. Use a compatible ChatGPT Desktop client with the **Add plugin marketplace** dialog. This source-based installation still needs **Git**, **uv** and **Python 3.12+** (installed locally or managed by uv). Git and uv must be available on the desktop app's PATH. See [prerequisites and troubleshooting](docs/INSTALL.md#prerequisites).

**1. Add the marketplace from the GUI:** open **Plugins**, open the marketplace/source controls and choose **Add plugin marketplace**. Fill in the dialog as follows:

| Field | Value |
| --- | --- |
| **Source** | `https://github.com/deved-it/garmin-connect-plugin.git` |
| **Git reference** | `main` |
| **Selective paths** | Leave empty |

Click **Add marketplace**. Leave selective paths empty because the plugin needs the whole repository, not just its catalog. This adds the marketplace; it does not install the plugin yet.

**2. Install in ChatGPT Desktop:** select the **Garmin Personal (local)** marketplace/source and install **garmin-personal**. Restart the app if needed and start a new locally executed thread. Menu labels and availability depend on client version and workspace policy.

**3. Configure your key:** generate a personal key in [Garmin Connect settings](https://connect.garmin.com/app/settings/personalApiToken), then open the plugin settings → **Garmin Connection → Configure API Key**. Save it in the masked form. Never paste it into the conversation. If the host does not support this form, use the [hidden-input terminal fallback](docs/INSTALL.md#native-masked-configuration).

**4. Verify:** ask the plugin to check the connection, using `garmin_status(validate_connection=true)`, then request your first report. On first use, uv prepares the locked Python environment and may need Internet access to download dependencies. This path runs the **source package**, not the standalone executable.

No public OpenAI catalog listing or remote MCP URL is required. The included marketplace catalog is discovered automatically from GitHub. See [updating a GitHub installation](docs/INSTALL.md#update-a-github-installation). We currently develop directly on `main`.

### Optional: register using Codex CLI

If you already use Codex CLI, these commands are an alternative to step 1 above, not an additional requirement:

```sh
codex plugin marketplace add deved-it/garmin-connect-plugin --ref main
codex plugin marketplace list
```

The full Git URL works too: `codex plugin marketplace add https://github.com/deved-it/garmin-connect-plugin.git --ref main`. Use either form, not both, then continue with step 2 above.

### Alternative installation paths

- [Standalone ZIP](docs/INSTALL.md#standalone-release), when published: **macOS Apple Silicon** and **Windows x64**, with runtime and dependencies included; no Python or uv required.
- [Manual source checkout](docs/INSTALL.md#source-installation): for development, terminal-only configuration or other platforms.

See the [complete installation guide](docs/INSTALL.md) for key precedence, private `.env` usage, updating, uninstalling and troubleshooting.

## Example questions

- “How has my sleep changed over the last four weeks?”
- “Compare my runs this week with last week.”
- “Show my HRV and resting heart rate, including the number of available samples.”
- “Prepare a recovery summary without making up a score.”

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
