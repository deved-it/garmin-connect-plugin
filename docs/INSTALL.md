# Install Garmin Personal locally

The plugin runs on your computer. No public MCP endpoint, tunnel, hosted account database or OpenAI catalog submission is required for a local installation. You need a supported local ChatGPT Desktop/Codex client and your own Garmin Personal API Key.

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

From a current Codex CLI:

```sh
codex plugin marketplace add /absolute/path/to/extracted-folder-or-checkout
codex plugin marketplace list
```

Restart ChatGPT Desktop. In the Plugins directory choose the **Garmin Personal (local)** marketplace/source, install **garmin-personal**, then test in a new locally executed thread. Client versions and workspace policies can change the labels or availability. If the source does not appear, consult the [official local installation documentation](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually). Do not create a remote custom MCP URL for this stdio server.

Once hosted on GitHub, users can register the repository using `codex plugin marketplace add OWNER/REPO --ref <release-tag>`. The repository includes its generated catalog; standalone archives generate the same catalog automatically.

## Native masked configuration

In a host supporting structured plugin settings and MCP Apps, open plugin details/settings → **Collegamento Garmin → Configura chiave API**. Enter the key into the masked field and click **Salva localmente**. The save tool has app-only visibility; do not attempt to call it from the model.

If the host does not show these settings or rejects the app bridge, use the terminal `configure` command. MCP Apps support and actual native UI behavior must be tested in the target host; command-line smoke tests cannot certify the settings screen.

## Advanced key sources and precedence

1. Environment `GARMIN_CONNECT_PERSONAL_API_KEY`.
2. Environment alias `GARMIN_PERSONAL_API_KEY`.
3. Same variables from the `.env` in the explicit `GARMIN_PLUGIN_ROOT`, if not provided by the process environment.
4. Private local key file written by `configure` or the masked form.

An explicitly empty variable is an error, not permission to silently use another key. Remove stale overrides if a newly saved settings key appears to have no effect. Never pass the key as a CLI argument. Never commit `.env` or a token cache.

Keys are stored in the platform user configuration directory under `garmin-personal/api-key`; tokens use `garmin-personal/bearer-token.json` in the same directory. `platformdirs` chooses the platform convention. `GARMIN_PLUGIN_CONFIG_DIR` can explicitly override this for testing. POSIX files are `0600`; the directory is created `0700`. On Windows files inherit the user's directory ACL: use a private profile directory, not a shared/synced folder.

## Update and uninstall

Replace the plugin folder with a verified newer release (keep the separate private configuration directory). Refresh its marketplace with `codex plugin marketplace upgrade garmin-personal-local`, restart the app, and open a new thread. Keep the folder path stable or register the new path.

To uninstall, remove/disable the plugin in your host and remove the marketplace with `codex plugin marketplace remove garmin-personal-local`. Remove only the extracted plugin folder and, if desired, its dedicated `garmin-personal` configuration directory after confirming the exact path. Revoke the key in Garmin Connect to invalidate access. Uninstalling alone does not revoke a Garmin key.

## Troubleshooting

- `NOT_CONFIGURED`: configure a key locally; check empty or stale environment overrides.
- `AUTH_EXPIRED_OR_REVOKED`: generate a new key in Garmin settings and replace the local one.
- `FORBIDDEN`: the endpoint is not available to this account/key.
- `RATE_LIMITED`: wait and request a smaller interval. Automatic retries are bounded.
- `NETWORK_ERROR` / `GARMIN_UNAVAILABLE`: check connectivity and Garmin availability.
- `UNEXPECTED_RESPONSE`: Garmin returned an unsupported shape. Report only endpoint, dates and error code; do not attach health payloads or secrets to public issues.
- Partial report: inspect each source. Missing data is not a zero or proof of rest.
- Activity-file resource missing: it lasts only for the running server session; fetch again.

## Release verification

Public CI uses synthetic data only; it must never receive a personal Garmin key. Build release candidates natively and smoke-test extracted archives with Python/uv absent from the server process PATH. Windows execution must be verified on Windows; a Mac build is not evidence for Windows.

Before publishing, the maintainer opts in locally to a real-account check: configure through hidden input, validate connection, request recent activities, sleep, HRV, heart rate, stress, Body Battery, a partial-safe report and one activity ZIP. Record only version, endpoint, timestamp and pass/fail; never commit personal results, token files or screenshots containing keys.
