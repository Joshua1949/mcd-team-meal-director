"""Command-line interface for the dry-run meal-planning demo."""

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from mcd_team_meal_director.models import MealItem, PlanGoal, TeamMealRequest
from mcd_team_meal_director.planner import NoFeasiblePlanError, generate_meal_plans


DEFAULT_MOCK_MENU = Path(__file__).resolve().parents[2] / "examples" / "mock_menu.json"
GOAL_TITLES = {
    PlanGoal.LOWEST_COST: "最省钱方案",
    PlanGoal.BALANCED: "营养相对均衡方案",
    PlanGoal.MOST_VARIETY: "品类最丰富方案",
}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="麦麦团建导演 dry-run 演示")
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
        "--menu",
        type=Path,
        default=DEFAULT_MOCK_MENU,
        help="dry-run 菜单 JSON 文件",
    )
    return parser


def load_mock_menu(path: Path) -> tuple[str, list[MealItem]]:
    """Load and validate a dry-run menu file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    notice = str(payload["notice"])
    items = [MealItem.model_validate(item) for item in payload["items"]]
    return notice, items


def main(argv: Sequence[str] | None = None) -> int:
    """Run the dry-run CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        request = TeamMealRequest(
            party_size=args.people,
            budget_yuan=args.budget,
            dietary_goals=args.dietary_goal,
            calorie_conscious_count=args.calorie_conscious,
        )
        notice, menu_items = load_mock_menu(args.menu)
        plans = generate_meal_plans(request, menu_items)
    except (OSError, KeyError, json.JSONDecodeError, ValidationError, NoFeasiblePlanError) as error:
        parser.error(str(error))

    print(f"DRY-RUN：{notice}")
    print(
        f"需求：{request.party_size} 人，预算 {request.budget_yuan:.2f} 元，"
        f"其中 {request.calorie_conscious_count} 人控制热量"
    )
    for plan in plans:
        print(f"\n[{GOAL_TITLES[plan.goal]}]")
        for line in plan.lines:
            print(
                f"- {line.item.name} × {line.quantity}："
                f"{line.subtotal_yuan:.2f} 元"
            )
        print(f"预估合计：{plan.estimated_total_yuan:.2f} 元")
        for note in plan.notes:
            print(f"说明：{note}")

    return 0
