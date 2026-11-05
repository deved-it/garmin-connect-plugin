# Install Garmin Personal locally

The plugin runs on your computer. No public MCP endpoint, tunnel, hosted account database or OpenAI catalog submission is required for a local installation. You need a supported local ChatGPT Desktop/Codex client and your own Garmin Personal API Key.

## Install directly from GitHub — recommended

This is the shortest installation path. There is no manual repository clone, ZIP extraction, marketplace editing or `uv sync` step.

### Prerequisites

- A compatible ChatGPT Desktop/local Codex client with plugin marketplace support. **Codex CLI is not required for GUI installation.**
- Git and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed and available on PATH, including when launched by the desktop app.
- Python 3.12 or newer, either installed locally or managed by uv. Use the [official uv Python installation guide](https://docs.astral.sh/uv/guides/install-python/) if Python is missing.
- Internet access to fetch the Git repository, prepare the Python environment and contact Garmin.

The GUI handles marketplace registration and plugin installation. It does not install the source runtime prerequisites for you. If needed, check Git and uv from a terminal:

```sh
git --version
uv --version
```

The GitHub marketplace serves the source package and uses the `uv` command from `mcp.json`. Registering it does **not** automatically install a standalone release or remove the uv prerequisite. You can install from the GUI without a `codex` command; a fully runtime-bundled installation requires a published [standalone release](#standalone-release).

### 1. Register this GitHub repository

In ChatGPT Desktop, open **Plugins**, open the marketplace/source controls and choose **Add plugin marketplace**. Enter the following in the dialog:

| Field | What to enter |
| --- | --- |
| **Source** | `https://github.com/deved-it/garmin-connect-plugin.git` |
| **Git reference** | `main` |
| **Selective paths** | Leave empty — do not enter `plugin/codex` or `.agents/plugins` |

Click **Add marketplace** and wait for the repository to be fetched. The example text inside an empty field is a placeholder, not a value you need to copy. Menu labels and availability can vary by client version and workspace policy.

Point to the repository, **not** a `raw.githubusercontent.com` JSON URL, an individual file or a ZIP URL. The client discovers `.agents/plugins/marketplace.json`; no manual catalog generation is needed. Selective paths must stay empty because this plugin's runtime, lockfile and skills also live elsewhere in the repository.

The Git reference `main` follows our current development branch. A future release tag can be used instead to pin an installation to a tested version.

#### Optional CLI alternative

Only if you already use a current Codex CLI, you can replace the GUI registration step with these commands, run from any directory:

```sh
codex plugin marketplace add deved-it/garmin-connect-plugin --ref main
codex plugin marketplace list
```

Equivalent full Git URL:

```sh
codex plugin marketplace add https://github.com/deved-it/garmin-connect-plugin.git --ref main
```

Choose one form, not both. Do not add `--sparse .agents/plugins`. Continue with the same installation step below; CLI registration is not required in addition to GUI registration.

### 2. Install the plugin

Open **Plugins**, select **Garmin Personal (local)** from the marketplace/source picker, then install **garmin-personal**. Adding a marketplace and installing a plugin are separate steps. Restart ChatGPT Desktop if the new source is not visible, and open a new locally executed thread after installation.

If the source does not appear, check the marketplace list in the GUI and verify the origin and Git reference above. If you chose the CLI route, `codex plugin marketplace list` is an additional diagnostic. Installation and native settings depend on the host's supported plugin UI and workspace policies; see the [official marketplace documentation](https://developers.openai.com/plugins/build/plugins).

### 3. Configure a Personal API Key

Create your own key in [Garmin Connect → Settings → Personal API Key](https://connect.garmin.com/app/settings/personalApiToken). Then open plugin details/settings → **Garmin Connection → Configure API Key**. Enter it in the masked form and save locally. Never paste it into a conversation or pass it as a command-line argument.

If the host lacks the form, follow [Native masked configuration](#native-masked-configuration) for the hidden-input fallback. No API key belongs in the GitHub repository or marketplace catalog.

### 4. Validate and use

In the new thread, ask Garmin Personal to validate the connection (`garmin_status(validate_connection=true)`), then request a report. A local `configured` status alone does not prove that Garmin has accepted the key.

The first server startup uses `uv run --locked --no-dev` to prepare the environment. Dependency downloads can make the first call slower; subsequent starts reuse the cached environment. If startup reports that `uv` cannot be found, fix the desktop app's PATH and restart it.

### Update a GitHub installation

In the plugin/marketplace management UI, use its refresh/update action if your client provides one, then update the installed **garmin-personal** plugin if offered. Check the version in the plugin details. If the GUI has no update action, remove the plugin and marketplace through their management controls, add the same GitHub origin again with `main` and empty selective paths, then reinstall the plugin. Keep the separate private configuration directory: you do not need to re-enter or expose your key.

If you have Codex CLI installed, the optional terminal alternative is:

```sh
codex plugin marketplace upgrade garmin-personal-local
```

Restart the app and open a new thread. No manual `git pull` is needed for this managed installation, and the separately stored private key is not replaced by a repository update.

## Standalone release

When a maintainer has published a GitHub release, download the archive matching your machine:

- `garmin-personal-plugin-macos-arm64.zip`: macOS Apple Silicon.
- `garmin-personal-plugin-windows-x64.zip`: Windows x64.

Also download its `.sha256` file and verify the checksum before extraction. On macOS use `shasum -a 256 <archive.zip>`; on Windows use `Get-FileHash <archive.zip> -Algorithm SHA256`. Keep the extracted folder in a persistent user-owned location. Do not move its `bin` executable away from its bundled runtime files.

Configure locally:

```sh
# macOS, from the extracted folder
./bin/garmin-personal-plugin configure
./bin/garmin-personal-plugin status
```

```powershell
# Windows PowerShell, from the extracted folder
.\bin\garmin-personal-plugin.exe configure
.\bin\garmin-personal-plugin.exe status
```

The input is hidden. A configured status is offline and does not establish that Garmin has accepted the key. Validate in the installed plugin with `garmin_status(validate_connection=true)`.

Packages are not currently code-signed/notarized. Do not disable system security globally or remove quarantine indiscriminately. Review and build the source yourself if your OS blocks an untrusted artifact; signing requires maintainer certificates not supplied by this project.

## Source installation

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/) using their official instructions. Clone this repository, then run from its root:

```sh
uv sync --locked
uv run --locked garmin-personal-plugin configure
uv run --locked garmin-personal-plugin status
```

The repository and standalone archives include a repo-scoped `.agents/plugins/marketplace.json`. If that generated file is absent from a source export, run `uv run python scripts/prepare_marketplace.py` to regenerate it from the root template. The command refuses to overwrite an existing catalog.

On other platforms (macOS Intel, Windows ARM64, Linux), source installation is the supported fallback, but those platforms need their own host compatibility testing. Python minimum is 3.12; the initial local development verification used Python 3.14 on macOS arm64.

## Register the marketplace

This alternative is only for an extracted standalone archive or a manual source checkout. For direct GitHub installation, use the GUI repository instructions above instead.

In **Add plugin marketplace**, set **Source** to the absolute path of the persistent extracted folder or checkout. Leave **Git reference** and **Selective paths** empty for a local folder, then click **Add marketplace**.

Alternatively, from a current Codex CLI:

```sh
codex plugin marketplace add /absolute/path/to/extracted-folder-or-checkout
codex plugin marketplace list
```

Restart ChatGPT Desktop. In the Plugins directory choose the **Garmin Personal (local)** marketplace/source, install **garmin-personal**, then test in a new locally executed thread. Client versions and workspace policies can change the labels or availability. If the source does not appear, consult the [official local installation documentation](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually). Do not create a remote custom MCP URL for this stdio server.

The repository includes its generated catalog; standalone archives generate the same catalog automatically.

## Native masked configuration

In a host supporting structured plugin settings and MCP Apps, open plugin details/settings → **Garmin Connection → Configure API Key**. Enter the key into the masked field and click **Save locally**. The save tool has app-only visibility; do not attempt to call it from the model.

If the host does not show these settings or rejects the app bridge, use the terminal `configure` command. For a managed GitHub installation, the host runs a cached copy rather than your current directory. If you know its installed plugin folder, use:

```sh
uv run --project "/absolute/path/to/installed/plugin" --locked --no-dev garmin-personal-plugin configure
```

Alternatively, use the manual source checkout procedure above and run `configure` there. Both copies use the same platform-private configuration directory, so the key is available to the installed plugin too. Do not edit the managed cache's `.env` as your primary setup: reinstalling may replace that cache.

MCP Apps support and actual native UI behavior must be tested in the target host; command-line smoke tests cannot certify the settings screen.

## Advanced key sources and precedence

1. Environment `GARMIN_CONNECT_PERSONAL_API_KEY`.
2. Environment alias `GARMIN_PERSONAL_API_KEY`.
3. Same variables from the `.env` in the explicit `GARMIN_PLUGIN_ROOT`, if not provided by the process environment.
4. Private local key file written by `configure` or the masked form.

An explicitly empty variable is an error, not permission to silently use another key. Remove stale overrides if a newly saved settings key appears to have no effect. Never pass the key as a CLI argument. Never commit `.env` or a token cache.

Keys are stored in the platform user configuration directory under `garmin-personal/api-key`; tokens use `garmin-personal/bearer-token.json` in the same directory. `platformdirs` chooses the platform convention. `GARMIN_PLUGIN_CONFIG_DIR` can explicitly override this for testing. POSIX files are `0600`; the directory is created `0700`. On Windows files inherit the user's directory ACL: use a private profile directory, not a shared/synced folder.

## Update and uninstall

For a direct GitHub installation, follow [Update a GitHub installation](#update-a-github-installation), using the GUI or optional CLI. For a standalone/manual installation, replace the plugin folder with the verified newer version, keep the separate private configuration directory, refresh the marketplace and restart the app. Keep the folder path stable or register the new path.

To uninstall, remove/disable the plugin and remove its marketplace through the host's management UI. If you use Codex CLI, `codex plugin marketplace remove garmin-personal-local` is an alternative for removing the marketplace. Remove only the extracted plugin folder and, if desired, its dedicated `garmin-personal` configuration directory after confirming the exact path. Revoke the key in Garmin Connect to invalidate access. Uninstalling alone does not revoke a Garmin key.

## Troubleshooting

- **“Unable to load or save settings” / “Impossibile caricare o salvare le impostazioni” on version 0.1.0:** the settings tools returned text-only JSON instead of the required structured result and output schema. [Update to **0.1.1 or newer**](#update-a-github-installation) through the GUI or optional CLI, fully quit and reopen ChatGPT Desktop, then check the version in the plugin details. If it still shows 0.1.0, update/reinstall the plugin from the refreshed marketplace and restart again. Removing the installed plugin does not remove its separately stored key. Do not regenerate or paste your API key to fix this protocol error.
- `NOT_CONFIGURED`: configure a key locally; check empty or stale environment overrides.
- `AUTH_EXPIRED_OR_REVOKED`: generate a new key in Garmin settings and replace the local one.
- `FORBIDDEN`: the endpoint is not available to this account/key.
- `RATE_LIMITED`: wait and request a smaller interval. Automatic retries are bounded.
- `NETWORK_ERROR` / `GARMIN_UNAVAILABLE`: check connectivity and Garmin availability.
- `UNEXPECTED_RESPONSE`: Garmin returned an unsupported shape. Report only endpoint, dates and error code; do not attach health payloads or secrets to public issues.
- Partial report: inspect each source. Missing data is not a zero or proof of rest.
- Activity-file resource missing: it lasts only for the running server session; fetch again.

## Release verification

### Automatic publication for maintainers

The **Build and release standalone packages** GitHub Actions workflow builds and
tests macOS Apple Silicon and Windows x64 packages. Pushing a version tag such as
`v0.1.2` publishes a GitHub Release only after **both** native builds and their
archive smoke tests succeed. Before creating a tag, ensure its version matches
`plugin.json`, `pyproject.toml`, the source version and `uv.lock`, and that the
tag points to the intended reviewed commit on `main`.

The release includes both platform ZIPs and their `.zip.sha256` files, with
automatically generated release notes. Tags beginning with `v0.` and tags with a
prerelease suffix (for example `v1.0.0-rc.1`) are marked **prerelease** and are not
marked Latest. Ordinary stable version tags produce stable releases.

Running the workflow manually produces downloadable Actions artifacts only;
it never publishes, even when the selected reference is a tag. Publication uses
the repository's automatic `GITHUB_TOKEN` with write access restricted to the
publication job; no personal access token or Garmin key is needed. Repository
or organization policies may still prevent release creation.

New releases are prepared as drafts, and published after all four assets have
been verified and uploaded. Rerunning a successful tag workflow reuses the same
release and replaces same-name assets; it does not create another release or
delete its tag. Asset replacement is not atomic: an interrupted replacement can
require a rerun. If immutable releases are enabled, published assets cannot be
replaced; publish a new version tag instead. Do not move a published version tag.

Automatic publication does not sign/notarize the packages or certify their native
ChatGPT UI behavior. The local opt-in checks below remain separate from CI.

### Native and real-account checks

Public CI uses synthetic data only; it must never receive a personal Garmin key. Build release candidates natively and smoke-test extracted archives with Python/uv absent from the server process PATH. Windows execution must be verified on Windows; a Mac build is not evidence for Windows.

Before publishing, the maintainer opts in locally to a real-account check: configure through hidden input, validate connection, request recent activities, sleep, HRV, heart rate, stress, Body Battery, a partial-safe report and one activity ZIP. Record only version, endpoint, timestamp and pass/fail; never commit personal results, token files or screenshots containing keys.
