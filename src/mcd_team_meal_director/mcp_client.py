"""Safe, read-only access to the McDonald's China MCP tool catalog."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, Tool


MCD_MCP_URL = "https://mcp.mcd.cn"


@asynccontextmanager
async def open_mcd_client(token: str) -> AsyncIterator[Client]:
    """Open an authenticated MCP client without exposing the token."""
    if not token.strip():
        raise ValueError("MCD_MCP_TOKEN cannot be empty")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx2.AsyncClient(headers=headers) as http_client:
        transport = streamable_http_client(MCD_MCP_URL, http_client=http_client)
        async with Client(
            transport,
            mode="legacy",
            read_timeout_seconds=30,
        ) as client:
            yield client


async def fetch_tool_catalog(token: str) -> list[Tool]:
    """Return every advertised tool without invoking any business operation."""
    async with open_mcd_client(token) as client:
        tools: list[Tool] = []
        cursor: str | None = None
        while True:
            result = await client.list_tools(
                cursor=cursor,
                cache_mode="reload",
            )
            tools.extend(result.tools)
            cursor = result.next_cursor
            if cursor is None:
                return tools


async def fetch_nutrition_foods(token: str) -> CallToolResult:
    """Call the argument-free, read-only nutrition catalog tool."""
    async with open_mcd_client(token) as client:
        return await client.call_tool("list-nutrition-foods", {})


async def fetch_nearby_pickup_stores(
    token: str,
    city: str,
    keyword: str,
) -> CallToolResult:
    """Search pickup stores near a public location without using a saved address."""
    if not city.strip() or not keyword.strip():
        raise ValueError("city and keyword cannot be empty")

    async with open_mcd_client(token) as client:
        return await client.call_tool(
            "query-nearby-stores",
            {
                "beType": 1,
                "searchType": 2,
                "city": city,
                "keyword": keyword,
            },
        )


async def fetch_pickup_menu(token: str, store_code: str) -> CallToolResult:
    """Fetch the read-only menu for an in-store pickup location."""
    if not store_code.strip():
        raise ValueError("store_code cannot be empty")

    async with open_mcd_client(token) as client:
        return await client.call_tool(
            "query-meals",
            {
                "storeCode": store_code,
                "orderType": 1,
                "beType": 1,
            },
        )


async def fetch_pickup_planning_data(
    token: str,
    store_code: str,
) -> tuple[CallToolResult, CallToolResult]:
    """Fetch only the real menu and nutrition catalogs needed for planning."""
    if not store_code.strip():
        raise ValueError("store_code cannot be empty")

    async with open_mcd_client(token) as client:
        menu_result = await client.call_tool(
            "query-meals",
            {
                "storeCode": store_code,
                "orderType": 1,
                "beType": 1,
            },
        )
        nutrition_result = await client.call_tool("list-nutrition-foods", {})
    return menu_result, nutrition_result
