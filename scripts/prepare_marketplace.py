"""Prepare a repository-local marketplace explicitly, never overwrite existing catalogs."""

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / ".agents/plugins/marketplace.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = json.loads((root / "marketplace.json").read_text(encoding="utf-8"))
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(content, stream, indent=2)
        stream.write("\n")
    print("Local marketplace prepared. Register this repository with codex plugin marketplace add.")


if __name__ == "__main__":
    main()
