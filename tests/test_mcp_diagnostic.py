import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from mcd_team_meal_director import (
    live_plan,
    menu_diagnostic,
    mcp_client,
    mcp_diagnostic,
    nutrition_diagnostic,
    store_diagnostic,
)


def test_fetch_tool_catalog_sends_token_in_header_and_follows_pagination(
    monkeypatch: object,
) -> None:
    captured: dict[str, object] = {}

    class FakeHttpClient:
        def __init__(self, **kwargs: object) -> None:
            captured["headers"] = kwargs["headers"]

        async def __aenter__(self) -> "FakeHttpClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    class FakeClient:
        def __init__(self, transport: object, **kwargs: object) -> None:
            captured["transport"] = transport
            captured["client_options"] = kwargs

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def list_tools(self, *, cursor: str | None, **kwargs: object) -> ListToolsResult:
            captured.setdefault("cursors", []).append(cursor)  # type: ignore[union-attr]
            if cursor is None:
                return ListToolsResult(
                    tools=[Tool(name="first-tool", inputSchema={"type": "object"})],
                    nextCursor="page-2",
                )
            return ListToolsResult(
                tools=[Tool(name="second-tool", inputSchema={"type": "object"})]
            )

    sentinel_transport = object()

    def fake_transport(url: str, **kwargs: object) -> object:
        captured["url"] = url
        captured["http_client"] = kwargs["http_client"]
        return sentinel_transport

    monkeypatch.setattr(mcp_client.httpx2, "AsyncClient", FakeHttpClient)  # type: ignore[attr-defined]
    monkeypatch.setattr(mcp_client, "streamable_http_client", fake_transport)  # type: ignore[attr-defined]
    monkeypatch.setattr(mcp_client, "Client", FakeClient)  # type: ignore[attr-defined]

    tools = asyncio.run(mcp_client.fetch_tool_catalog("private-test-value"))

    assert captured["headers"] == {
        "Authorization": "Bearer private-test-value"
    }
    assert captured["url"] == mcp_client.MCD_MCP_URL
    assert captured["transport"] is sentinel_transport
    assert captured["client_options"] == {
        "mode": "legacy",
        "read_timeout_seconds": 30,
    }
    assert captured["cursors"] == [None, "page-2"]
    assert [tool.name for tool in tools] == ["first-tool", "second-tool"]


def test_diagnostic_requires_token_without_echoing_values(
    monkeypatch: object,
    capsys: object,
) -> None:
    monkeypatch.delenv(mcp_diagnostic.TOKEN_ENV_VAR, raising=False)  # type: ignore[attr-defined]

    exit_code = mcp_diagnostic.main([])

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert exit_code == 2
    assert mcp_diagnostic.TOKEN_ENV_VAR in captured.err


def test_diagnostic_prints_tool_names_and_schemas(
    monkeypatch: object,
    capsys: object,
) -> None:
    async def fake_fetch_tool_catalog(token: str) -> list[Tool]:
        assert token == "private-test-value"
        return [
            Tool(
                name="query-example",
                description="Example read-only tool",
                inputSchema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
            )
        ]

    monkeypatch.setenv(mcp_diagnostic.TOKEN_ENV_VAR, "private-test-value")  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        mcp_diagnostic,
        "fetch_tool_catalog",
        fake_fetch_tool_catalog,
    )

    exit_code = mcp_diagnostic.main([])

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert exit_code == 0
    assert "query-example" in output
    assert '"keyword"' in output
    assert "private-test-value" not in output


def test_diagnostic_help_does_not_require_token(
    monkeypatch: object,
    capsys: object,
) -> None:
    monkeypatch.delenv(mcp_diagnostic.TOKEN_ENV_VAR, raising=False)  # type: ignore[attr-defined]

    with pytest.raises(SystemExit) as raised:
        mcp_diagnostic.main(["--help"])

    output = capsys.readouterr()  # type: ignore[attr-defined]
    assert raised.value.code == 0
    assert "MCP" in output.out
    assert output.err == ""


def test_fetch_nutrition_foods_only_calls_allowlisted_read_only_tool(
    monkeypatch: object,
) -> None:
    captured: dict[str, object] = {}
    expected = CallToolResult(content=[TextContent(type="text", text="nutrition")])

    class FakeClient:
        async def call_tool(
            self,
            name: str,
            arguments: dict[str, object],
        ) -> CallToolResult:
            captured["name"] = name
            captured["arguments"] = arguments
            return expected

    @asynccontextmanager
    async def fake_open_mcd_client(token: str):  # type: ignore[no-untyped-def]
        captured["token"] = token
        yield FakeClient()

    monkeypatch.setattr(  # type: ignore[attr-defined]
        mcp_client,
        "open_mcd_client",
        fake_open_mcd_client,
    )

    result = asyncio.run(mcp_client.fetch_nutrition_foods("private-test-value"))

    assert result is expected
    assert captured == {
        "token": "private-test-value",
        "name": "list-nutrition-foods",
        "arguments": {},
    }


def test_nutrition_diagnostic_writes_utf8_json_without_token(
    monkeypatch: object,
    tmp_path: object,
) -> None:
    output_path = tmp_path / "nutrition.json"  # type: ignore[operator]

    async def fake_fetch_nutrition_foods(token: str) -> CallToolResult:
        assert token == "private-test-value"
        return CallToolResult(
            content=[TextContent(type="text", text="模拟营养数据")],
            structuredContent={"foods": [{"name": "示例"}]},
        )

    monkeypatch.setenv(nutrition_diagnostic.TOKEN_ENV_VAR, "private-test-value")  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        nutrition_diagnostic,
        "fetch_nutrition_foods",
        fake_fetch_nutrition_foods,
    )

    exit_code = nutrition_diagnostic.main(["--output", str(output_path)])
    output = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert "模拟营养数据" in output
    assert "private-test-value" not in output


def test_fetch_nearby_stores_uses_public_location_and_pickup_mode(
    monkeypatch: object,
) -> None:
    captured: dict[str, object] = {}
    expected = CallToolResult(content=[TextContent(type="text", text="stores")])

    class FakeClient:
        async def call_tool(
            self,
            name: str,
            arguments: dict[str, object],
        ) -> CallToolResult:
            captured["name"] = name
            captured["arguments"] = arguments
            return expected

    @asynccontextmanager
    async def fake_open_mcd_client(token: str):  # type: ignore[no-untyped-def]
        captured["token"] = token
        yield FakeClient()

    monkeypatch.setattr(  # type: ignore[attr-defined]
        mcp_client,
        "open_mcd_client",
        fake_open_mcd_client,
    )

    result = asyncio.run(
        mcp_client.fetch_nearby_pickup_stores(
            "private-test-value",
            "南京市",
            "鼓楼医院",
        )
    )

    assert result is expected
    assert captured["arguments"] == {
        "beType": 1,
        "searchType": 2,
        "city": "南京市",
        "keyword": "鼓楼医院",
    }


def test_store_diagnostic_writes_utf8_json(
    monkeypatch: object,
    tmp_path: object,
) -> None:
    output_path = tmp_path / "stores.json"  # type: ignore[operator]

    async def fake_fetch_stores(
        token: str,
        city: str,
        keyword: str,
    ) -> CallToolResult:
        assert (token, city, keyword) == (
            "private-test-value",
            "南京市",
            "鼓楼医院",
        )
        return CallToolResult(
            content=[TextContent(type="text", text="门店结果")],
            structuredContent={"stores": [{"storeCode": "test-store"}]},
        )

    monkeypatch.setenv(store_diagnostic.TOKEN_ENV_VAR, "private-test-value")  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        store_diagnostic,
        "fetch_nearby_pickup_stores",
        fake_fetch_stores,
    )

    exit_code = store_diagnostic.main(
        [
            "--city",
            "南京市",
            "--keyword",
            "鼓楼医院",
            "--output",
            str(output_path),
        ]
    )

    output = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "test-store" in output
    assert "private-test-value" not in output


def test_fetch_pickup_menu_uses_selected_store_without_be_code(
    monkeypatch: object,
) -> None:
    captured: dict[str, object] = {}
    expected = CallToolResult(content=[TextContent(type="text", text="menu")])

    class FakeClient:
        async def call_tool(
            self,
            name: str,
            arguments: dict[str, object],
        ) -> CallToolResult:
            captured["name"] = name
            captured["arguments"] = arguments
            return expected

    @asynccontextmanager
    async def fake_open_mcd_client(token: str):  # type: ignore[no-untyped-def]
        captured["token"] = token
        yield FakeClient()

    monkeypatch.setattr(  # type: ignore[attr-defined]
        mcp_client,
        "open_mcd_client",
        fake_open_mcd_client,
    )

    result = asyncio.run(
        mcp_client.fetch_pickup_menu("private-test-value", "1990696")
    )

    assert result is expected
    assert captured["arguments"] == {
        "storeCode": "1990696",
        "orderType": 1,
        "beType": 1,
    }
    assert "beCode" not in captured["arguments"]  # type: ignore[operator]


def test_menu_diagnostic_writes_utf8_json(
    monkeypatch: object,
    tmp_path: object,
) -> None:
    output_path = tmp_path / "menu.json"  # type: ignore[operator]

    async def fake_fetch_menu(token: str, store_code: str) -> CallToolResult:
        assert (token, store_code) == ("private-test-value", "1990696")
        return CallToolResult(
            content=[TextContent(type="text", text="菜单结果")],
            structuredContent={"products": [{"code": "test-product"}]},
        )

    monkeypatch.setenv(menu_diagnostic.TOKEN_ENV_VAR, "private-test-value")  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        menu_diagnostic,
        "fetch_pickup_menu",
        fake_fetch_menu,
    )

    exit_code = menu_diagnostic.main(
        [
            "--store-code",
            "1990696",
            "--output",
            str(output_path),
        ]
    )

    output = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "test-product" in output
    assert "private-test-value" not in output


def test_fetch_pickup_planning_data_only_calls_two_read_only_tools(
    monkeypatch: object,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeClient:
        async def call_tool(
            self,
            name: str,
            arguments: dict[str, object],
        ) -> CallToolResult:
            calls.append((name, arguments))
            return CallToolResult(content=[])

    @asynccontextmanager
    async def fake_open_mcd_client(token: str):  # type: ignore[no-untyped-def]
        assert token == "private-test-value"
        yield FakeClient()

    monkeypatch.setattr(  # type: ignore[attr-defined]
        mcp_client,
        "open_mcd_client",
        fake_open_mcd_client,
    )

    asyncio.run(
        mcp_client.fetch_pickup_planning_data(
            "private-test-value",
            "1990696",
        )
    )

    assert calls == [
        (
            "query-meals",
            {"storeCode": "1990696", "orderType": 1, "beType": 1},
        ),
        ("list-nutrition-foods", {}),
    ]


def test_live_plan_writes_three_plans_from_read_only_results(
    monkeypatch: object,
    tmp_path: object,
) -> None:
    output_path = tmp_path / "live-plan.json"  # type: ignore[operator]
    menu_data = {
        "categories": [
            {"name": "鸡肉汉堡\n/卷", "meals": [{"code": "light"}]},
            {"name": "随心配\n1+1", "meals": [{"code": "regular"}]},
            {"name": "500\n大卡套餐", "meals": [{"code": "combo"}]},
        ],
        "meals": {
            "light": {
                "name": "轻盈汉堡",
                "currentPrice": "10",
                "originalPrice": "10",
            },
            "regular": {
                "name": "经典汉堡",
                "currentPrice": "12",
                "originalPrice": "12",
            },
            "combo": {
                "name": "均衡套餐",
                "currentPrice": "15",
                "originalPrice": "15",
            },
        },
    }
    nutrition_data = """[3]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
轻盈汉堡,null,1800,450,20,15,40,500,100
经典汉堡,null,2600,650,25,20,50,600,120
均衡套餐,null,2400,600,24,18,48,550,110
"""

    async def fake_fetch(
        token: str,
        store_code: str,
    ) -> tuple[CallToolResult, CallToolResult]:
        assert (token, store_code) == ("private-test-value", "1990696")
        return (
            CallToolResult(content=[], structuredContent={"data": menu_data}),
            CallToolResult(content=[], structuredContent={"data": nutrition_data}),
        )

    monkeypatch.setenv(live_plan.TOKEN_ENV_VAR, "private-test-value")  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        live_plan,
        "fetch_pickup_planning_data",
        fake_fetch,
    )

    exit_code = live_plan.main(
        [
            "--store-code",
            "1990696",
            "--people",
            "2",
            "--budget",
            "50",
            "--calorie-conscious",
            "1",
            "--output",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["mode"] == "live-read-only"
    assert payload["sources"] == ["query-meals", "list-nutrition-foods"]
    assert len(payload["plans"]) == 3
    assert "private-test-value" not in output_path.read_text(encoding="utf-8")
