"""Real stdio MCP handshake and offline status from an unrelated directory."""

import argparse
import asyncio
import hashlib
import json
import os
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def extract_verified(archive: Path, destination: Path) -> None:
    expected = archive.with_suffix(".zip.sha256").read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError("Archive checksum mismatch.")
    with zipfile.ZipFile(archive) as zipped:
        if sum(item.file_size for item in zipped.infolist()) > 1024 * 1024 * 1024:
            raise ValueError("Archive too large.")
        for item in zipped.infolist():
            target = destination / item.filename
            if not target.resolve().is_relative_to(destination.resolve()) or stat.S_ISLNK(
                item.external_attr >> 16
            ):
                raise ValueError("Unsafe archive member.")
        zipped.extractall(destination)


async def smoke(root: Path, source: bool) -> None:
    config = json.loads((root / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]["garmin-personal"]
    if source:
        command, args = sys.executable, ["-m", "garmin_connect_plugin", "serve"]
    else:
        command = config["command"].replace("${PLUGIN_ROOT}", str(root))
        args = config["args"]
        if os.name != "nt":
            Path(command).chmod(0o755)
    with tempfile.TemporaryDirectory(prefix="garmin-smoke-") as directory:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GARMIN_")}
        env.update({"GARMIN_PLUGIN_CONFIG_DIR": directory, "GARMIN_PLUGIN_ROOT": directory})
        if not source:
            env["PATH"] = ""
        parameters = StdioServerParameters(command=command, args=args, cwd=directory, env=env)
        with anyio.fail_after(45):
            async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                expected = {
                    "garmin_status",
                    "garmin_profile",
                    "garmin_activities",
                    "garmin_activity",
                    "garmin_activity_file",
                    "garmin_health",
                    "garmin_report",
                }
                assert expected <= names, names
                for tool in tools.tools:
                    if tool.name in expected:
                        assert tool.annotations and tool.annotations.readOnlyHint is True
                result = await session.call_tool("garmin_status", {})
                assert result.structuredContent and result.structuredContent["status"] == "not_configured"
                assert (
                    initialized.capabilities.experimental["openai/settings"]["readTool"]
                    == "garmin_settings_read"
                )
                settings_tool = next(tool for tool in tools.tools if tool.name == "garmin_settings_read")
                assert settings_tool.outputSchema is not None
                assert {"schema", "values"} <= set(settings_tool.outputSchema["required"])
                settings_result = await session.call_tool(settings_tool.name, {})
                assert not settings_result.isError and settings_result.structuredContent is not None
                assert {"schema", "values", "layout"} <= settings_result.structuredContent.keys()
                resource = await session.read_resource("ui://garmin-personal/configure-v1.html")
                assert resource.contents
                print(
                    "PASS: MCP initialize, seven read-only tools, offline status, structured settings, UI resource."
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-tree", type=Path)
    group.add_argument("--package", type=Path)
    group.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.archive:
        with tempfile.TemporaryDirectory(prefix="garmin-extracted-") as directory:
            root = Path(directory)
            extract_verified(args.archive.resolve(), root)
            asyncio.run(smoke(root, False))
        return
    asyncio.run(smoke((args.source_tree or args.package).resolve(), args.source_tree is not None))


if __name__ == "__main__":
    main()
