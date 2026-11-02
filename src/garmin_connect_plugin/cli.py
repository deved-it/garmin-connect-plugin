"""Terminal-only credential setup and MCP stdio entry point."""

import argparse
import json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Garmin Personal — local, read-only integration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="Run the MCP server over stdio")
    commands.add_parser("configure", help="Save a key locally using hidden input")
    commands.add_parser("status", help="Check local configuration without contacting Garmin")
    args = parser.parse_args(argv)
    if args.command == "serve":
        from .server import create_server

        create_server().run(transport="stdio")
    elif args.command == "configure":
        from .config import Settings
        from .credentials import configure_key

        configure_key(Settings.load().key_file)
        print("API key saved locally. Restart the plugin to reload configuration.")
    else:
        from .config import Settings
        from .credentials import CredentialResolver
        from .errors import PluginError

        try:
            credential = CredentialResolver(Settings.load()).resolve()
            result = {"status": "configured", "source": credential.source}
        except PluginError:
            result = {"status": "not_configured"}
        print(json.dumps(result))
    return 0
