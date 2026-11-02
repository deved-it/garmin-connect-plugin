---
name: setup
description: Configure or troubleshoot the local Garmin Personal connection without exposing credentials.
---

Use `garmin_status` to check local configuration. It does not contact Garmin unless `validate_connection=true` is explicitly requested. Missing tools mean the plugin is not enabled; do not pretend to access Garmin.

Never ask the user to paste a key into chat. Never read `.env`, key files or token caches. Never call `garmin_save_key` from the model: it is app-only.

Guide users to plugin details/settings → **Collegamento Garmin → Configura chiave API**. This masked MCP App saves the value directly without chat messages or model context. The host must support OpenAI structured settings and MCP Apps.

Fallback: run the bundled executable with `configure`; source: `uv run --project <plugin-folder> --locked garmin-personal-plugin configure`. Input is hidden. Advanced users may set `GARMIN_CONNECT_PERSONAL_API_KEY` in their private `.env`, loaded only from explicit `GARMIN_PLUGIN_ROOT`, never arbitrary working directories.

Generate a personal key at https://connect.garmin.com/app/settings/personalApiToken. Every user must create their own. Environment variables and `.env` take precedence over the settings key; explain this if a newly saved key is not used.

After setup use `garmin_status(validate_connection=true)` and continue any already requested analysis with `garmin_report`. Offline configured status is not proof of a working connection. Report source failures.

Code and credentials live on the computer. Requests go directly to Garmin. Requested results in the conversation are processed by OpenAI. No project backend or telemetry. Local key/token files are plaintext with filesystem permissions, not encrypted vault storage.

Do not create scheduled tasks automatically. No tool modifies Garmin Connect. Saving workouts, scheduling sessions, courses and routes are unsupported.
