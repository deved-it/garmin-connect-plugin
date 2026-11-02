import importlib.util
import json
from pathlib import Path

import pytest


def load_builder():
    path = Path(__file__).resolve().parents[1] / "scripts/build_release.py"
    assert path.exists(), "Release builder is missing"
    spec = importlib.util.spec_from_file_location("builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_assembly_excludes_local_credentials_and_builds_platform_manifest(tmp_path):
    builder = load_builder()
    root = Path(__file__).resolve().parents[1]
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    (frozen / "garmin-personal-plugin").write_text("fake executable for assembly-only test")
    destination = tmp_path / "package"
    builder.assemble(root, frozen, destination, "macos-arm64")
    assert not (destination / ".env").exists()
    config = json.loads((destination / "mcp.json").read_text())["mcpServers"]["garmin-personal"]
    assert config["command"] == "${PLUGIN_ROOT}/bin/garmin-personal-plugin"
    assert config["args"] == ["serve"]
    assert (destination / "apps/configure/index.html").exists()
    assert (destination / ".agents/plugins/marketplace.json").exists()
    assert not (destination / "src").exists()


def test_assembly_refuses_dirty_or_symlinked_payload(tmp_path):
    builder = load_builder()
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    (frozen / ".env").write_text("SYNTHETIC_KEY=never ship")
    with pytest.raises(ValueError):
        builder.assemble(Path(__file__).resolve().parents[1], frozen, tmp_path / "package", "macos-arm64")


def test_internal_runtime_links_are_dereferenced_but_external_links_rejected(tmp_path):
    builder = load_builder()
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    (frozen / "garmin-personal-plugin").write_text("fake executable")
    (frozen / "runtime.dylib").write_bytes(b"fake runtime")
    (frozen / "runtime-link.dylib").symlink_to("runtime.dylib")
    root = Path(__file__).resolve().parents[1]
    package = tmp_path / "package"
    builder.assemble(root, frozen, package, "macos-arm64")
    assert not (package / "bin/runtime-link.dylib").is_symlink()
    (frozen / "outside").symlink_to(tmp_path / "not-in-package")
    with pytest.raises(ValueError):
        builder.assemble(root, frozen, tmp_path / "other", "macos-arm64")


def test_archive_verification_rejects_bad_checksum_and_path_traversal(tmp_path):
    import hashlib
    import zipfile

    path = Path(__file__).resolve().parents[1] / "scripts/smoke_package.py"
    spec = importlib.util.spec_from_file_location("smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../outside", "never extract")
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text("0" * 64 + "  release.zip\n")
    with pytest.raises(ValueError):
        module.extract_verified(archive, tmp_path / "extracted")
    checksum.write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  release.zip\n")
    with pytest.raises(ValueError):
        module.extract_verified(archive, tmp_path / "extracted")
    assert not (tmp_path / "outside").exists()
