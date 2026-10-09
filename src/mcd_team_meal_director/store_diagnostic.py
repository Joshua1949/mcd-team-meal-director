"""Read-only diagnostic for pickup stores near a public location."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from mcd_team_meal_director.mcp_client import fetch_nearby_pickup_stores


TOKEN_ENV_VAR = "MCD_MCP_TOKEN"


def build_parser() -> argparse.ArgumentParser:
    """Build arguments for the pickup-store diagnostic."""
    parser = argparse.ArgumentParser(
        description="只读调用 query-nearby-stores 并保存原始 JSON"
    )
    parser.add_argument("--city", required=True, help="城市，例如南京市")
    parser.add_argument("--keyword", required=True, help="公共地点关键词")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="UTF-8 JSON 输出文件",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Fetch pickup stores and save the raw result without printing private data."""
    args = build_parser().parse_args(argv)
    token = os.environ.get(TOKEN_ENV_VAR, "")
    if not token.strip():
        print(
            f"缺少环境变量 {TOKEN_ENV_VAR}；请在本机设置，勿将 Token 写入仓库。",
            file=sys.stderr,
        )
        return 2

    try:
        result = asyncio.run(
            fetch_nearby_pickup_stores(token, args.city, args.keyword)
        )
        payload = result.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception as error:
        print(
            f"联调失败（{type(error).__name__}）。请检查网络、Token、参数和输出路径。",
            file=sys.stderr,
        )
        return 1

    if result.is_error:
        print("MCP 工具返回错误；原始结果已保存，且未执行任何写操作。")
        return 1

    print(f"门店查询结果已安全保存到：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
