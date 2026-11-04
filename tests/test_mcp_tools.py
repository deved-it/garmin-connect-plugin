import asyncio

from garmin_connect_plugin.config import Settings
from garmin_connect_plugin.container import ServiceContainer
from garmin_connect_plugin.server import create_server


def test_server_status_no_network_and_settings_no_secret(tmp_path):
    async def check():
        services = ServiceContainer.build(Settings(config_dir=tmp_path))
        server = create_server(services)
        tools = {tool.name: tool for tool in await server.list_tools()}
        assert {
            "garmin_status",
            "garmin_profile",
            "garmin_activities",
            "garmin_activity",
            "garmin_activity_file",
            "garmin_health",
            "garmin_report",
        } <= tools.keys()
        result = await server.call_tool("garmin_status", {})
        assert "not_configured" in str(result)
        assert str(tmp_path) not in str(result)
        assert tools["garmin_save_key"].meta["ui"]["visibility"] == ["app"]
        assert not tools["garmin_save_key"].annotations.readOnlyHint
        assert tools["garmin_configure"].title == "Configura chiave API"
        assert tools["garmin_save_key"].title == "Salva chiave API"
        assert server._mcp_server.version == "0.1.1"
        result = await server.call_tool("garmin_save_key", {"value": "synthetic-private-key"})
        assert "synthetic-private-key" not in str(result)
        settings = await server.call_tool("garmin_settings_read", {})
        assert "synthetic-private-key" not in str(settings)
        assert "garmin_configure" in str(settings)
        services.resources.cleanup()

    asyncio.run(check())


def test_invalid_tool_input_is_safe(tmp_path):
    async def check():
        services = ServiceContainer.build(Settings(config_dir=tmp_path))
        server = create_server(services)
        result = await server.call_tool("garmin_activity", {"activity_id": "../../private"})
        assert "INVALID_INPUT" in str(result)
        assert "../../private" not in str(result)
        services.resources.cleanup()

    asyncio.run(check())


def test_oversized_tool_results_are_not_silently_truncated():
    from garmin_connect_plugin.server import public_result

    result = public_result(lambda: {"status": "ok", "data": "x" * 600000})
    assert result.isError
    assert result.structuredContent["error"]["code"] == "INVALID_INPUT"
    assert "smaller" in result.content[0].text.lower()
