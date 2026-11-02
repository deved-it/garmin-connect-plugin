# Privacy and data handling

Garmin Personal is a local process, not a cloud service. It calls the official Garmin Personal API directly over HTTPS. There is no project-operated backend, analytics or telemetry.

## Credentials

The API key is exchanged with Garmin for a bearer token using Garmin's official Python client. The origin is fixed to `https://personal.connectapi.garmin.com`: an upstream environment override cannot redirect the key to another host. Token exchange and cached-token handling use that client.

Key and token files are **plaintext**, protected by local filesystem permissions. They are not encrypted keychain entries. Keep your OS account secure, avoid shared/synced configuration directories, and apply your backup policy accordingly. On POSIX the key is written atomically with `0600` permissions, its directory created `0700`; on Windows access depends on inherited directory ACLs.

No key or token is returned by MCP tools, profile responses, error bodies or settings reads. The UI clears its input after submit and never uses localStorage, chat messages or model-context updates to persist the value. Only app-visible save operations handle UI credentials. Host enforcement of app-only visibility is required; use hidden terminal input if the host does not implement it correctly.

## Health records

Tool results needed for a requested conversation are shared with ChatGPT/Codex and processed by OpenAI according to the user's service settings and policies. “Local plugin” does **not** mean those requested results remain exclusively on the computer. Avoid requesting data you do not want in the conversation.

The plugin minimizes account identifiers and unknown fields, preserves original measurement units and Garmin dates, and fetches menstrual-cycle data only with explicit opt-in. It does not log raw records. Normal reports are not written to disk. Activity ZIPs are stored in a private temporary directory and deleted on normal shutdown; abrupt termination can leave OS temporary files, which should be handled under your OS cleanup policy.

Garmin tool results and files are untrusted input. The included analysis skill instructs the assistant not to follow embedded instructions or disclose credentials. This is not a medical device and provides no diagnoses or invented recovery scores.

## Control

Users choose metrics and periods, can remove the local configuration, and can revoke keys in Garmin Connect. The plugin does not modify Garmin records or schedule background tasks. Report bugs without attaching `.env`, tokens, private files or personal health payloads.
