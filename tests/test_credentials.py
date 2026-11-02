import os

import pytest

from garmin_connect_plugin.config import Settings
from garmin_connect_plugin.credentials import CredentialResolver, configure_key
from garmin_connect_plugin.errors import PluginError
from garmin_connect_plugin.redaction import redact


def test_precedence_and_no_secret_repr(tmp_path):
    settings = Settings(config_dir=tmp_path)
    configure_key(settings.key_file, lambda _: "file-secret")
    resolver = CredentialResolver(
        settings,
        environ={
            "GARMIN_CONNECT_PERSONAL_API_KEY": "primary-secret",
            "GARMIN_PERSONAL_API_KEY": "alias-secret",
        },
    )
    assert resolver.resolve().value == "primary-secret"
    assert resolver.resolve("app-secret").value == "app-secret"
    assert "primary-secret" not in repr(resolver.resolve())
    assert CredentialResolver(settings, environ={}).resolve().value == "file-secret"
    if os.name != "nt":
        assert settings.key_file.stat().st_mode & 0o777 == 0o600


def test_empty_explicit_source_does_not_fall_back(tmp_path):
    settings = Settings(config_dir=tmp_path)
    configure_key(settings.key_file, lambda _: "file-secret")
    with pytest.raises(PluginError):
        CredentialResolver(settings, environ={"GARMIN_CONNECT_PERSONAL_API_KEY": ""}).resolve()


def test_symlink_destination_is_rejected(tmp_path):
    target = tmp_path / "target"
    target.write_text("keep")
    link = tmp_path / "key"
    link.symlink_to(target)
    with pytest.raises(PluginError):
        configure_key(link, lambda _: "new-secret")
    assert target.read_text() == "keep"


def test_nested_secret_redaction():
    result = redact(
        {"error": ["ApiKey example-secret", {"Authorization": "Bearer private-token"}], "value": 0},
        ["example-secret", "private-token"],
    )
    assert "example-secret" not in str(result)
    assert "private-token" not in str(result)
    assert result["value"] == 0


def test_process_alias_precedes_primary_dotenv(tmp_path):
    (tmp_path / ".env").write_text("GARMIN_CONNECT_PERSONAL_API_KEY=dotenv-synthetic\n")
    settings = Settings(config_dir=tmp_path / "config", plugin_root=tmp_path)
    result = CredentialResolver(
        settings, environ={"GARMIN_PERSONAL_API_KEY": "environment-synthetic"}
    ).resolve()
    assert result.value == "environment-synthetic"
