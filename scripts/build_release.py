"""Build platform-native standalone releases from an explicit allowlist."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from packaging.requirements import Requirement

FILES = ("plugin.json", "README.md", "LICENSE", "NOTICE", "docs/INSTALL.md", "docs/PRIVACY.md")
DIRECTORIES = ("skills", "apps")


def collect_runtime_notices(destination: Path) -> None:
    output = destination / "third-party-licenses"
    output.mkdir()
    pending, seen = ["garmin-personal-plugin"], set()
    while pending:
        name = pending.pop()
        distribution = importlib.metadata.distribution(name)
        canonical = distribution.metadata["Name"].lower().replace("_", "-")
        if canonical in seen:
            continue
        seen.add(canonical)
        folder = output / canonical
        folder.mkdir()
        (folder / "METADATA.txt").write_text(
            f"Name: {distribution.metadata['Name']}\nVersion: {distribution.version}\n"
            f"License: {distribution.metadata.get('License-Expression', distribution.metadata.get('License', 'See license files'))}\n",
            encoding="utf-8",
        )
        for item in distribution.files or []:
            if any(
                part.lower() in ("licenses", "license", "license.txt", "license.md", "notice")
                for part in item.parts
            ):
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    filename = "_".join(item.parts[-3:])
                    shutil.copy2(source, folder / filename)
        for dependency in distribution.requires or []:
            requirement = Requirement(dependency)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.exists():
        import sysconfig

        python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, output / "PYTHON-LICENSE.txt")


def verify_payload(root: Path, internal_links: bool = False) -> None:
    for path in root.rglob("*"):
        if path.is_symlink() and (
            not internal_links or not path.resolve().is_relative_to(root.resolve()) or not path.exists()
        ):
            raise ValueError("External, broken or unexpected symlink in package.")
        if (
            path.name == ".env"
            or path.name.startswith(".env.")
            or path.name in ("api-key", "bearer-token.json", ".git", ".venv")
        ):
            raise ValueError("Private configuration, development dependency or symlink in package.")


def assemble(root: Path, frozen: Path, destination: Path, target: str) -> Path:
    verify_payload(frozen, internal_links=True)
    if destination.exists():
        raise ValueError("Destination already exists; choose a fresh output directory.")
    executable = "garmin-personal-plugin.exe" if target == "windows-x64" else "garmin-personal-plugin"
    if not (frozen / executable).is_file():
        raise ValueError("Missing frozen entry point.")
    destination.mkdir(parents=True)
    for filename in FILES:
        source = root / filename
        target_path = destination / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target_path)
    for dirname in DIRECTORIES:
        shutil.copytree(root / dirname, destination / dirname)
    shutil.copytree(frozen, destination / "bin", symlinks=False)
    config = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {
            "garmin-personal": {
                "type": "stdio",
                "command": "${PLUGIN_ROOT}/bin/" + executable,
                "args": ["serve"],
                "cwd": "${PLUGIN_ROOT}",
                "env": {"GARMIN_PLUGIN_ROOT": "${PLUGIN_ROOT}"},
            }
        },
    }
    (destination / "mcp.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    catalog = destination / ".agents/plugins"
    catalog.mkdir(parents=True)
    shutil.copy2(root / "marketplace.json", catalog / "marketplace.json")
    verify_payload(destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("dist/releases"))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "files": FILES,
                    "directories": DIRECTORIES,
                    "excluded": [".env", ".venv", ".git", "tests", "source credentials"],
                }
            )
        )
        return 0
    system, machine = platform.system(), platform.machine().lower()
    if system == "Darwin" and machine == "arm64":
        target = "macos-arm64"
    elif system == "Windows" and machine in ("amd64", "x86_64"):
        target = "windows-x64"
    else:
        parser.error("Autonomous v1 builds require native macOS arm64 or Windows x64.")
    work = root / "build" / target
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name",
        "garmin-personal-plugin",
        "--paths",
        str(root / "src"),
        "--distpath",
        str(work / "frozen"),
        "--workpath",
        str(work / "work"),
        "--specpath",
        str(work),
        "--add-data",
        f"{root / 'apps'}:apps",
        "--copy-metadata",
        "mcp",
        str(root / "scripts/entrypoint.py"),
    ]
    subprocess.run(command, cwd=root, check=True)
    output = args.output.resolve()
    package = assemble(
        root, work / "frozen/garmin-personal-plugin", output / f"garmin-personal-plugin-{target}", target
    )
    collect_runtime_notices(package)
    archive = Path(shutil.make_archive(str(package), "zip", root_dir=package))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
