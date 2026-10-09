"""Read-only command that prints the remote MCP tool catalog."""

import argparse
import asyncio
import json
import os
import sys
from typing import Sequence

from mcd_team_meal_director.mcp_client import fetch_tool_catalog


TOKEN_ENV_VAR = "MCD_MCP_TOKEN"


def build_parser() -> argparse.ArgumentParser:
    """Build arguments for the tool catalog diagnostic."""
    return argparse.ArgumentParser(
        description="只读列出麦当劳中国 MCP 当前提供的工具及输入结构"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """List remote tools while keeping the authentication token private."""
    build_parser().parse_args(argv)
    token = os.environ.get(TOKEN_ENV_VAR, "")
    if not token.strip():
        print(
            f"缺少环境变量 {TOKEN_ENV_VAR}；请在本机设置，勿将 Token 写入仓库。",
            file=sys.stderr,
        )
        return 2

    try:
        tools = asyncio.run(fetch_tool_catalog(token))
    except Exception as error:
        print(
            f"连接失败（{type(error).__name__}）。请检查网络、Token 和服务状态。",
            file=sys.stderr,
        )
        return 1

    print(f"发现 {len(tools)} 个 MCP Tools：")
    for tool in tools:
        print(f"\n{tool.name}")
        if tool.description:
            print(tool.description)
        print(
            json.dumps(
                tool.input_schema,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
