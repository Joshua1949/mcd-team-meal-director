from decimal import Decimal

import pytest
from pydantic import ValidationError

from mcd_team_meal_director.models import (
    MealItem,
    MealPlan,
    MealPlanLine,
    PlanGoal,
    TeamMealRequest,
)


def test_team_meal_request_accepts_valid_input() -> None:
    request = TeamMealRequest(
        party_size=6,
        budget_yuan="180.00",
        dietary_goals=["丰富一点", "控制热量"],
        calorie_conscious_count=2,
    )

    assert request.party_size == 6
    assert request.budget_yuan == Decimal("180.00")
    assert request.dietary_goals == ["丰富一点", "控制热量"]
    assert request.calorie_conscious_count == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("party_size", 0),
        ("budget_yuan", "0"),
        ("calorie_conscious_count", -1),
    ],
)
def test_team_meal_request_rejects_non_positive_values(
    field: str,
    value: object,
) -> None:
    data: dict[str, object] = {
        "party_size": 6,
        "budget_yuan": "180.00",
        "calorie_conscious_count": 2,
    }
    data[field] = value

    with pytest.raises(ValidationError):
        TeamMealRequest.model_validate(data)


def test_team_meal_request_rejects_calorie_count_above_party_size() -> None:
    with pytest.raises(
        ValidationError,
        match="calorie_conscious_count cannot exceed party_size",
    ):
        TeamMealRequest(
            party_size=2,
            budget_yuan="80.00",
            calorie_conscious_count=3,
        )


def test_meal_plan_calculates_estimated_totals() -> None:
    burger = MealItem(
        item_id="burger-1",
        name="示例汉堡",
        category="主食",
        unit_price_yuan="22.50",
        calories_kcal="450",
    )
    drink = MealItem(
        item_id="drink-1",
        name="示例饮料",
        category="饮料",
        unit_price_yuan="8.00",
    )

    plan = MealPlan(
        goal=PlanGoal.MOST_VARIETY,
        lines=[
            MealPlanLine(item=burger, quantity=2),
            MealPlanLine(item=drink, quantity=3),
        ],
        notes=["价格为菜单预估，确认后再精确计价"],
    )

    assert plan.lines[0].subtotal_yuan == Decimal("45.00")
    assert plan.estimated_total_yuan == Decimal("69.00")
    assert plan.goal == PlanGoal.MOST_VARIETY


@pytest.mark.parametrize("goal", list(PlanGoal))
def test_meal_plan_supports_each_required_goal(goal: PlanGoal) -> None:
    item = MealItem(
        item_id="item-1",
        name="示例餐品",
        category="主食",
        unit_price_yuan="10.00",
    )

    plan = MealPlan(
        goal=goal,
        lines=[MealPlanLine(item=item, quantity=1)],
    )

    assert plan.goal is goal


def test_output_models_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        MealItem(
            item_id="item-1",
            name="示例餐品",
            category="主食",
            unit_price_yuan="-1.00",
        )

    item = MealItem(
        item_id="item-1",
        name="示例餐品",
        category="主食",
        unit_price_yuan="10.00",
    )
    with pytest.raises(ValidationError):
        MealPlanLine(item=item, quantity=0)

    with pytest.raises(ValidationError):
        MealPlan(goal=PlanGoal.BALANCED, lines=[])
