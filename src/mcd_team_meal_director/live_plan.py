"""Read-only end-to-end planning with live McDonald's China MCP data."""

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from mcd_team_meal_director.catalog import build_main_meal_catalog
from mcd_team_meal_director.mcp_client import fetch_pickup_planning_data
from mcd_team_meal_director.menu import parse_store_menu
from mcd_team_meal_director.models import TeamMealRequest
from mcd_team_meal_director.nutrition import parse_nutrition_table
from mcd_team_meal_director.planner import generate_meal_plans


TOKEN_ENV_VAR = "MCD_MCP_TOKEN"


class LivePlanDataError(ValueError):
    """Raised when a live MCP result lacks required read-only planning data."""


def build_parser() -> argparse.ArgumentParser:
    """Build arguments for live, read-only planning."""
    parser = argparse.ArgumentParser(
        description="使用真实 MCP 菜单和营养数据生成三套只读配餐方案"
    )
    parser.add_argument("--store-code", required=True, help="真实门店编码")
    parser.add_argument("--people", type=int, required=True, help="用餐人数")
    parser.add_argument("--budget", type=Decimal, required=True, help="总预算（元）")
    parser.add_argument(
        "--calorie-conscious",
        type=int,
        default=0,
        help="希望控制热量的人数",
    )
    parser.add_argument(
        "--dietary-goal",
        action="append",
        default=[],
        help="饮食目标，可重复传入",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="UTF-8 JSON 输出文件",
    )
    return parser


def _structured_data(result: object, tool_name: str) -> Any:
    if getattr(result, "is_error", True):
        raise LivePlanDataError(f"{tool_name} returned an MCP error")
    structured = getattr(result, "structured_content", None)
    if not isinstance(structured, Mapping) or "data" not in structured:
        raise LivePlanDataError(f"{tool_name} returned no structured data")
    return structured["data"]


def main(argv: Sequence[str] | None = None) -> int:
    """Fetch live read-only data and write three deterministic plans."""
    args = build_parser().parse_args(argv)
    token = os.environ.get(TOKEN_ENV_VAR, "")
    if not token.strip():
        print(
            f"缺少环境变量 {TOKEN_ENV_VAR}；请在本机设置，勿将 Token 写入仓库。",
            file=sys.stderr,
        )
        return 2

    try:
        request = TeamMealRequest(
            party_size=args.people,
            budget_yuan=args.budget,
            dietary_goals=args.dietary_goal,
            calorie_conscious_count=args.calorie_conscious,
        )
        menu_result, nutrition_result = asyncio.run(
            fetch_pickup_planning_data(token, args.store_code)
        )
        menu_data = _structured_data(menu_result, "query-meals")
        nutrition_data = _structured_data(
            nutrition_result,
            "list-nutrition-foods",
        )
        if not isinstance(menu_data, Mapping) or not isinstance(nutrition_data, str):
            raise LivePlanDataError("live MCP data types have changed")

        products = parse_store_menu(menu_data)
        nutrition_foods = parse_nutrition_table(nutrition_data)
        items = build_main_meal_catalog(products, nutrition_foods)
        plans = generate_meal_plans(request, items)

        payload = {
            "mode": "live-read-only",
            "storeCode": args.store_code,
            "request": request.model_dump(mode="json"),
            "sources": ["query-meals", "list-nutrition-foods"],
            "coverage": {
                "menuProducts": len(products),
                "nutritionRows": len(nutrition_foods),
                "mainMealCandidates": len(items),
                "candidatesWithNutrition": sum(
                    item.calories_kcal is not None for item in items
                ),
            },
            "plans": [plan.model_dump(mode="json") for plan in plans],
        }
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception as error:
        print(
            f"生成失败（{type(error).__name__}）。请检查参数、网络、Token 和 MCP 状态。",
            file=sys.stderr,
        )
        return 1

    print(f"三套真实数据方案已安全保存到：{args.output}")
    print("本命令未调用精确计价或下单工具。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
