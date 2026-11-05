"""Increment the project's patch version and update its version references."""

import re
import sys
from pathlib import Path


def bump_version(root: Path) -> str:
    paths = {
        "pyproject.toml": (r'(?m)^version = "(\d+\.\d+\.\d+)"$', r'version = "{version}"', 1),
        "plugin.json": (r'(?m)^  "version": "(\d+\.\d+\.\d+)",$', r'  "version": "{version}",', 1),
        "src/garmin_connect_plugin/__init__.py": (
            r'(?m)^__version__ = "(\d+\.\d+\.\d+)"$',
            r'__version__ = "{version}"',
            1,
        ),
        "uv.lock": (
            r'(?m)(\[\[package\]\]\nname = "garmin-personal-plugin"\nversion = )"(\d+\.\d+\.\d+)"',
            r'\g<1>"{version}"',
            2,
        ),
        "README.md": (
            r"(?m)^\*\*Status: (\d+\.\d+\.\d+) development preview\.\*\*",
            r"**Status: {version} development preview.**",
            1,
        ),
        "docs/IMPLEMENTATION_STATUS.md": (
            r"(?m)^Version: \*\*(\d+\.\d+\.\d+) development preview\*\*\.",
            r"Version: **{version} development preview**.",
            1,
        ),
    }
    updates = {}
    current_version = None
    for filename, (pattern, replacement, version_group) in paths.items():
        path = root / filename
        contents = path.read_text(encoding="utf-8")
        match = re.search(pattern, contents)
        if match is None or (
            current_version is not None and match.group(version_group) != current_version
        ):
            raise ValueError(f"Missing or inconsistent version in {filename}.")
        current_version = current_version or match.group(version_group)
        major, minor, patch = (int(part) for part in current_version.split("."))
        version = f"{major}.{minor}.{patch + 1}"
        updated, count = re.subn(pattern, replacement.format(version=version), contents, count=1)
        if count != 1:
            raise ValueError(f"Could not update version in {filename}.")
        updates[path] = updated

    for path, contents in updates.items():
        path.write_text(contents, encoding="utf-8")
    return version


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[1]
    print(bump_version(repository_root))
