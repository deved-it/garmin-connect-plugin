import json
import runpy
from pathlib import Path

import pytest

bump_version = runpy.run_path(Path(__file__).resolve().parents[1] / "scripts/bump_version.py")[
    "bump_version"
]


@pytest.fixture
def versioned_repo(tmp_path: Path) -> Path:
    files = {
        "pyproject.toml": '[project]\nversion = "0.1.1"\n',
        "plugin.json": '{\n  "version": "0.1.1",\n  "name": "garmin-personal"\n}\n',
        "src/garmin_connect_plugin/__init__.py": '__version__ = "0.1.1"\n',
        "uv.lock": '[[package]]\nname = "garmin-personal-plugin"\nversion = "0.1.1"\n',
        "README.md": "**Status: 0.1.1 development preview.**\n",
        "docs/IMPLEMENTATION_STATUS.md": "Version: **0.1.1 development preview**.\n",
    }
    for filename, content in files.items():
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_bump_version_updates_all_project_version_references(versioned_repo: Path):
    assert bump_version(versioned_repo) == "0.1.2"
    assert 'version = "0.1.2"' in (versioned_repo / "pyproject.toml").read_text()
    assert json.loads((versioned_repo / "plugin.json").read_text())["version"] == "0.1.2"
    assert '__version__ = "0.1.2"' in (
        versioned_repo / "src/garmin_connect_plugin/__init__.py"
    ).read_text()
    assert 'name = "garmin-personal-plugin"\nversion = "0.1.2"' in (
        versioned_repo / "uv.lock"
    ).read_text()
    assert "Status: 0.1.2 development preview." in (versioned_repo / "README.md").read_text()
    assert "Version: **0.1.2 development preview**." in (
        versioned_repo / "docs/IMPLEMENTATION_STATUS.md"
    ).read_text()


def test_bump_version_rejects_inconsistent_versions_without_partial_updates(versioned_repo: Path):
    plugin_path = versioned_repo / "plugin.json"
    plugin_path.write_text(plugin_path.read_text().replace("0.1.1", "0.1.0"), encoding="utf-8")

    with pytest.raises(ValueError, match="inconsistent version"):
        bump_version(versioned_repo)

    assert 'version = "0.1.1"' in (versioned_repo / "pyproject.toml").read_text()
