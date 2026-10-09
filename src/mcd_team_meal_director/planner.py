"""Deterministic meal-planning strategies."""

from decimal import Decimal

from mcd_team_meal_director.models import (
    MealItem,
    MealPlan,
    MealPlanLine,
    PlanGoal,
    TeamMealRequest,
)


class NoFeasiblePlanError(ValueError):
    """Raised when the available menu cannot satisfy a request."""


GENERAL_TARGET_KCAL = Decimal("650")
CALORIE_CONSCIOUS_TARGET_KCAL = Decimal("450")


def generate_meal_plans(
    request: TeamMealRequest,
    menu_items: list[MealItem],
) -> list[MealPlan]:
    """Generate the three required plans in a stable presentation order."""
    return [
        generate_lowest_cost_plan(request, menu_items),
        generate_balanced_plan(request, menu_items),
        generate_most_variety_plan(request, menu_items),
    ]


def generate_lowest_cost_plan(
    request: TeamMealRequest,
    menu_items: list[MealItem],
) -> MealPlan:
    """Select one lowest-priced item per person without exceeding the budget."""
    if not menu_items:
        raise NoFeasiblePlanError("cannot build a plan from an empty menu")

    cheapest_item = min(
        menu_items,
        key=lambda item: (item.unit_price_yuan, item.item_id),
    )
    line = MealPlanLine(item=cheapest_item, quantity=request.party_size)

    if line.subtotal_yuan > request.budget_yuan:
        raise NoFeasiblePlanError(
            "the lowest-cost plan exceeds the available budget"
        )

    return MealPlan(
        goal=PlanGoal.LOWEST_COST,
        lines=[line],
        notes=["按每人一份餐品计算，价格为菜单预估"],
    )


def generate_most_variety_plan(
    request: TeamMealRequest,
    menu_items: list[MealItem],
) -> MealPlan:
    """Maximize distinct categories while keeping one item per person in budget."""
    if not menu_items:
        raise NoFeasiblePlanError("cannot build a plan from an empty menu")

    cheapest_item = min(
        menu_items,
        key=lambda item: (item.unit_price_yuan, item.item_id),
    )
    baseline_total = cheapest_item.unit_price_yuan * request.party_size
    if baseline_total > request.budget_yuan:
        raise NoFeasiblePlanError(
            "the lowest-cost plan exceeds the available budget"
        )

    cheapest_by_category: dict[str, MealItem] = {}
    for item in menu_items:
        current = cheapest_by_category.get(item.category)
        if current is None or (item.unit_price_yuan, item.item_id) < (
            current.unit_price_yuan,
            current.item_id,
        ):
            cheapest_by_category[item.category] = item

    alternatives = sorted(
        (
            item
            for category, item in cheapest_by_category.items()
            if category != cheapest_item.category
        ),
        key=lambda item: (
            item.unit_price_yuan - cheapest_item.unit_price_yuan,
            item.category,
            item.item_id,
        ),
    )

    selected_alternatives: list[MealItem] = []
    estimated_total = baseline_total
    for item in alternatives:
        if len(selected_alternatives) >= request.party_size - 1:
            break

        incremental_cost = item.unit_price_yuan - cheapest_item.unit_price_yuan
        if estimated_total + incremental_cost <= request.budget_yuan:
            selected_alternatives.append(item)
            estimated_total += incremental_cost

    base_quantity = request.party_size - len(selected_alternatives)
    lines = [MealPlanLine(item=cheapest_item, quantity=base_quantity)]
    lines.extend(
        MealPlanLine(item=item, quantity=1) for item in selected_alternatives
    )

    return MealPlan(
        goal=PlanGoal.MOST_VARIETY,
        lines=lines,
        notes=["在预算内优先增加不同餐品品类，按每人一份计算"],
    )


def generate_balanced_plan(
    request: TeamMealRequest,
    menu_items: list[MealItem],
) -> MealPlan:
    """Minimize group calorie-target deviation without exceeding the budget."""
    candidates = [item for item in menu_items if item.calories_kcal is not None]
    if not candidates:
        raise NoFeasiblePlanError(
            "cannot build a balanced plan without calorie data"
        )

    general_count = request.party_size - request.calorie_conscious_count
    calorie_conscious_count = request.calorie_conscious_count

    general_choices: list[MealItem | None] = candidates if general_count else [None]
    conscious_choices: list[MealItem | None] = (
        candidates if calorie_conscious_count else [None]
    )

    feasible_options: list[
        tuple[Decimal, Decimal, str, str, MealItem | None, MealItem | None]
    ] = []
    for general_item in general_choices:
        for conscious_item in conscious_choices:
            total_price = Decimal("0")
            calorie_deviation = Decimal("0")

            if general_item is not None:
                total_price += general_item.unit_price_yuan * general_count
                calorie_deviation += (
                    abs(general_item.calories_kcal - GENERAL_TARGET_KCAL)
                    * general_count
                )
            if conscious_item is not None:
                total_price += (
                    conscious_item.unit_price_yuan * calorie_conscious_count
                )
                calorie_deviation += (
                    abs(
                        conscious_item.calories_kcal
                        - CALORIE_CONSCIOUS_TARGET_KCAL
                    )
                    * calorie_conscious_count
                )

            if total_price <= request.budget_yuan:
                feasible_options.append(
                    (
                        calorie_deviation,
                        total_price,
                        general_item.item_id if general_item else "",
                        conscious_item.item_id if conscious_item else "",
                        general_item,
                        conscious_item,
                    )
                )

    if not feasible_options:
        raise NoFeasiblePlanError(
            "no calorie-aware combination fits the available budget"
        )

    *_, selected_general, selected_conscious = min(
        feasible_options,
        key=lambda option: option[:4],
    )

    quantities: dict[str, tuple[MealItem, int]] = {}
    for item, quantity in (
        (selected_general, general_count),
        (selected_conscious, calorie_conscious_count),
    ):
        if item is None or quantity == 0:
            continue
        existing = quantities.get(item.item_id)
        quantities[item.item_id] = (
            item,
            quantity + (existing[1] if existing else 0),
        )

    lines = [
        MealPlanLine(item=item, quantity=quantity)
        for item, quantity in quantities.values()
    ]
    return MealPlan(
        goal=PlanGoal.BALANCED,
        lines=lines,
        notes=[
            "按普通成员 650 kcal、控热量成员 450 kcal 的启发式目标计算",
            "仅用于方案比较，不构成营养或医疗建议",
        ],
    )
