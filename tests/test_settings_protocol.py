"""Exercise the settings contract over stdio, as a desktop host does."""

import asyncio
import os
import sys

import anyio
from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_settings_are_structured_and_match_advertised_schemas(tmp_path):
    async def check():
        env = {key: value for key, value in os.environ.items() if not key.startswith("GARMIN_")}
        env.update({"GARMIN_PLUGIN_CONFIG_DIR": str(tmp_path), "GARMIN_PLUGIN_ROOT": str(tmp_path)})
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "garmin_connect_plugin", "serve"],
            cwd=str(tmp_path),
            env=env,
        )
        with anyio.fail_after(20):
            async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
                initialized = await session.initialize()
                settings = initialized.capabilities.experimental["openai/settings"]
                tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                read_tool = tools[settings["readTool"]]
                assert read_tool.outputSchema is not None, "ChatGPT requires the settings outputSchema"
                assert {"schema", "values"} <= set(read_tool.outputSchema["required"])
                for name in ("schema", "values", "layout"):
                    assert name in read_tool.outputSchema["properties"]
                result = await session.call_tool(read_tool.name, {})
                assert not result.isError
                assert result.structuredContent is not None, "Settings must not be returned as text only"
                Draft202012Validator(read_tool.outputSchema).validate(result.structuredContent)
                data = result.structuredContent
                assert data["schema"] == {"type": "object", "properties": {}}
                assert data["values"] == {}
                action_name = data["layout"][0]["items"][0]["tool"]
                action = tools[action_name]
                Draft202012Validator(action.inputSchema).validate({})
                assert action.meta["ui"]["visibility"] == ["app"]
                opened = await session.call_tool(action_name, {})
                assert not opened.isError
                assert opened.structuredContent and opened.structuredContent["status"] == "ok"
                uri = action.meta["ui"]["resourceUri"]
                resource = await session.read_resource(uri)
                assert resource.contents[0].mimeType == "text/html;profile=mcp-app"
                configure_ui = resource.contents[0].text
                assert '<html lang="en">' in configure_ui
                assert "<h1>Garmin Connection</h1>" in configure_ui
                assert ">Save locally</button>" in configure_ui
                update_tool = tools[settings["updateTool"]]
                assert update_tool.outputSchema is not None
                assert "values" in update_tool.outputSchema["required"]
                updated = await session.call_tool(update_tool.name, {"set": {}})
                assert not updated.isError
                assert updated.structuredContent is not None
                Draft202012Validator(update_tool.outputSchema).validate(updated.structuredContent)
                assert updated.structuredContent["values"] == {}

    asyncio.run(check())
