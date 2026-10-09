from decimal import Decimal

import pytest

from mcd_team_meal_director.models import MealItem, PlanGoal, TeamMealRequest
from mcd_team_meal_director.planner import (
    NoFeasiblePlanError,
    generate_balanced_plan,
    generate_lowest_cost_plan,
    generate_meal_plans,
    generate_most_variety_plan,
)


def make_item(
    item_id: str,
    price: str,
    category: str = "主食",
    calories: str | None = None,
) -> MealItem:
    return MealItem(
        item_id=item_id,
        name=f"示例餐品 {item_id}",
        category=category,
        unit_price_yuan=price,
        calories_kcal=calories,
    )


def test_lowest_cost_plan_selects_cheapest_item_for_each_person() -> None:
    request = TeamMealRequest(party_size=6, budget_yuan="180.00")
    menu = [
        make_item("meal-b", "22.00"),
        make_item("meal-a", "18.50"),
        make_item("meal-c", "25.00"),
    ]

    plan = generate_lowest_cost_plan(request, menu)

    assert plan.goal == PlanGoal.LOWEST_COST
    assert len(plan.lines) == 1
    assert plan.lines[0].item.item_id == "meal-a"
    assert plan.lines[0].quantity == 6
    assert plan.estimated_total_yuan == Decimal("111.00")


def test_lowest_cost_plan_uses_item_id_to_break_price_ties() -> None:
    request = TeamMealRequest(party_size=2, budget_yuan="50.00")
    menu = [
        make_item("meal-b", "20.00"),
        make_item("meal-a", "20.00"),
    ]

    plan = generate_lowest_cost_plan(request, menu)

    assert plan.lines[0].item.item_id == "meal-a"


def test_lowest_cost_plan_rejects_empty_menu() -> None:
    request = TeamMealRequest(party_size=2, budget_yuan="50.00")

    with pytest.raises(NoFeasiblePlanError, match="empty menu"):
        generate_lowest_cost_plan(request, [])


def test_lowest_cost_plan_rejects_insufficient_budget() -> None:
    request = TeamMealRequest(party_size=3, budget_yuan="29.99")
    menu = [make_item("meal-a", "10.00")]

    with pytest.raises(NoFeasiblePlanError, match="exceeds"):
        generate_lowest_cost_plan(request, menu)


def test_most_variety_plan_maximizes_categories_within_budget() -> None:
    request = TeamMealRequest(party_size=4, budget_yuan="46.00")
    menu = [
        make_item("main", "10.00", "主食"),
        make_item("drink", "12.00", "饮料"),
        make_item("side", "14.00", "小食"),
        make_item("dessert", "20.00", "甜品"),
    ]

    plan = generate_most_variety_plan(request, menu)

    assert plan.goal == PlanGoal.MOST_VARIETY
    assert plan.estimated_total_yuan == Decimal("46.00")
    assert sum(line.quantity for line in plan.lines) == 4
    assert {line.item.category for line in plan.lines} == {"主食", "饮料", "小食"}


def test_most_variety_plan_uses_cheapest_item_in_each_category() -> None:
    request = TeamMealRequest(party_size=2, budget_yuan="25.00")
    menu = [
        make_item("main", "10.00", "主食"),
        make_item("drink-expensive", "14.00", "饮料"),
        make_item("drink-cheap", "12.00", "饮料"),
    ]

    plan = generate_most_variety_plan(request, menu)

    assert [line.item.item_id for line in plan.lines] == ["main", "drink-cheap"]
    assert plan.estimated_total_yuan == Decimal("22.00")


def test_most_variety_plan_caps_categories_at_party_size() -> None:
    request = TeamMealRequest(party_size=2, budget_yuan="100.00")
    menu = [
        make_item("main", "10.00", "主食"),
        make_item("drink", "11.00", "饮料"),
        make_item("side", "12.00", "小食"),
    ]

    plan = generate_most_variety_plan(request, menu)

    assert len({line.item.category for line in plan.lines}) == 2
    assert sum(line.quantity for line in plan.lines) == 2


@pytest.mark.parametrize("menu", [[], [make_item("main", "10.00")]])
def test_most_variety_plan_rejects_infeasible_requests(
    menu: list[MealItem],
) -> None:
    request = TeamMealRequest(party_size=3, budget_yuan="29.99")

    with pytest.raises(NoFeasiblePlanError):
        generate_most_variety_plan(request, menu)


def test_balanced_plan_matches_targets_for_each_group() -> None:
    request = TeamMealRequest(
        party_size=4,
        budget_yuan="100.00",
        calorie_conscious_count=2,
    )
    menu = [
        make_item("light", "20.00", calories="450"),
        make_item("regular", "25.00", calories="650"),
        make_item("heavy", "20.00", calories="900"),
    ]

    plan = generate_balanced_plan(request, menu)

    assert plan.goal == PlanGoal.BALANCED
    assert plan.estimated_total_yuan == Decimal("90.00")
    assert [(line.item.item_id, line.quantity) for line in plan.lines] == [
        ("regular", 2),
        ("light", 2),
    ]


def test_balanced_plan_chooses_best_combination_that_fits_budget() -> None:
    request = TeamMealRequest(
        party_size=2,
        budget_yuan="30.00",
        calorie_conscious_count=1,
    )
    menu = [
        make_item("light", "20.00", calories="450"),
        make_item("regular", "20.00", calories="650"),
        make_item("middle", "15.00", calories="550"),
    ]

    plan = generate_balanced_plan(request, menu)

    assert [(line.item.item_id, line.quantity) for line in plan.lines] == [
        ("middle", 2)
    ]
    assert plan.estimated_total_yuan == Decimal("30.00")


def test_balanced_plan_requires_calorie_data() -> None:
    request = TeamMealRequest(party_size=2, budget_yuan="50.00")
    menu = [make_item("unknown", "10.00")]

    with pytest.raises(NoFeasiblePlanError, match="calorie data"):
        generate_balanced_plan(request, menu)


def test_balanced_plan_rejects_combinations_over_budget() -> None:
    request = TeamMealRequest(party_size=2, budget_yuan="19.99")
    menu = [make_item("regular", "10.00", calories="650")]

    with pytest.raises(NoFeasiblePlanError, match="fits"):
        generate_balanced_plan(request, menu)


def test_generate_meal_plans_returns_all_strategies_in_display_order() -> None:
    request = TeamMealRequest(
        party_size=3,
        budget_yuan="90.00",
        calorie_conscious_count=1,
    )
    menu = [
        make_item("main", "18.00", "主食", "650"),
        make_item("drink", "10.00", "饮料", "200"),
        make_item("light", "20.00", "轻食", "450"),
    ]

    plans = generate_meal_plans(request, menu)

    assert [plan.goal for plan in plans] == [
        PlanGoal.LOWEST_COST,
        PlanGoal.BALANCED,
        PlanGoal.MOST_VARIETY,
    ]
    assert all(plan.estimated_total_yuan <= request.budget_yuan for plan in plans)
    assert all(
        sum(line.quantity for line in plan.lines) == request.party_size
        for plan in plans
    )
