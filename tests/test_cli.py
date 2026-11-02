import subprocess
import sys


def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "garmin_connect_plugin", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert all(command in result.stdout for command in ("serve", "configure", "status"))


def test_status_without_key_is_safe(tmp_path):
    import os

    env = {k: v for k, v in os.environ.items() if not k.startswith("GARMIN_")}
    env["GARMIN_PLUGIN_CONFIG_DIR"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "garmin_connect_plugin", "status"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "not_configured" in result.stdout
    assert str(tmp_path) not in result.stdout
