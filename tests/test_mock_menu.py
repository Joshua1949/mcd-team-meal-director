import json
from pathlib import Path

from mcd_team_meal_director.models import MealItem, TeamMealRequest
from mcd_team_meal_director.planner import generate_meal_plans


MOCK_MENU_PATH = Path(__file__).parents[1] / "examples" / "mock_menu.json"


def test_mock_menu_is_valid_and_supports_demo_request() -> None:
    payload = json.loads(MOCK_MENU_PATH.read_text(encoding="utf-8"))
    items = [MealItem.model_validate(item) for item in payload["items"]]
    request = TeamMealRequest(
        party_size=6,
        budget_yuan="180.00",
        dietary_goals=["丰富一点", "控制热量"],
        calorie_conscious_count=2,
    )

    plans = generate_meal_plans(request, items)

    assert "模拟菜单" in payload["notice"]
    assert len(items) == 8
    assert len(plans) == 3
