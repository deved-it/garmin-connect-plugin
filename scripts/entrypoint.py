"""PyInstaller entry point; all credential access remains in the application."""

from garmin_connect_plugin.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
