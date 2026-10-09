"""Conservative normalization from real MCP catalogs to planner inputs."""

from collections import defaultdict

from mcd_team_meal_director.models import MealItem, MenuProduct, NutritionFood


MAIN_MEAL_CATEGORIES = frozenset(
    {
        "精选单人餐",
        "鸡肉汉堡 /卷",
        "随心配 1+1",
        "大堡口福 单人餐",
        "巨无霸 牛鱼肉堡",
        "安格斯MAX 厚牛堡",
        "500 大卡套餐",
    }
)


def _nutrition_values(food: NutritionFood) -> tuple[object, ...]:
    return (
        food.energy_kj,
        food.energy_kcal,
        food.protein,
        food.fat,
        food.carbohydrate,
        food.sodium,
        food.calcium,
    )


def select_main_meal_products(products: list[MenuProduct]) -> list[MenuProduct]:
    """Keep products whose real menu categories indicate a one-person main meal."""
    return [
        product
        for product in products
        if MAIN_MEAL_CATEGORIES.intersection(product.category_names)
    ]


def _planner_category(product: MenuProduct) -> str:
    for category in product.category_names:
        if category in MAIN_MEAL_CATEGORIES:
            return category
    return product.category_names[0] if product.category_names else "未分类"


def merge_menu_with_nutrition(
    products: list[MenuProduct],
    nutrition_foods: list[NutritionFood],
) -> list[MealItem]:
    """Build planner items using exact names and never guess nutrition values."""
    foods_by_name: dict[str, list[NutritionFood]] = defaultdict(list)
    for food in nutrition_foods:
        foods_by_name[food.product_name.strip()].append(food)

    unambiguous_foods: dict[str, NutritionFood] = {}
    for name, foods in foods_by_name.items():
        first = foods[0]
        if all(_nutrition_values(food) == _nutrition_values(first) for food in foods):
            unambiguous_foods[name] = first

    items: list[MealItem] = []
    for product in products:
        nutrition = unambiguous_foods.get(product.name.strip())
        items.append(
            MealItem(
                item_id=product.product_code,
                name=product.name,
                category=_planner_category(product),
                unit_price_yuan=product.current_price_yuan,
                calories_kcal=(nutrition.energy_kcal if nutrition else None),
            )
        )
    return items


def build_main_meal_catalog(
    products: list[MenuProduct],
    nutrition_foods: list[NutritionFood],
) -> list[MealItem]:
    """Create planner inputs from products that qualify as one-person main meals."""
    return merge_menu_with_nutrition(
        select_main_meal_products(products),
        nutrition_foods,
    )
