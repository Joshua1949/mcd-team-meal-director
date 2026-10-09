from decimal import Decimal

from mcd_team_meal_director.catalog import (
    build_main_meal_catalog,
    merge_menu_with_nutrition,
    select_main_meal_products,
)
from mcd_team_meal_director.models import MenuProduct, NutritionFood


def make_product(
    code: str,
    name: str,
    categories: list[str] | None = None,
) -> MenuProduct:
    return MenuProduct(
        product_code=code,
        name=name,
        current_price_yuan="20.00",
        original_price_yuan="25.00",
        category_names=categories or [],
    )


def make_nutrition(name: str, calories: str) -> NutritionFood:
    return NutritionFood(
        product_name=name,
        energy_kj="1000",
        energy_kcal=calories,
        protein="10",
        fat="10",
        carbohydrate="20",
        sodium="500",
        calcium="50",
    )


def test_merge_uses_exact_name_and_primary_category() -> None:
    products = [make_product("meal-1", "示例汉堡", ["人气热卖", "主食"])]
    foods = [make_nutrition("示例汉堡", "450")]

    items = merge_menu_with_nutrition(products, foods)

    assert items[0].item_id == "meal-1"
    assert items[0].category == "人气热卖"
    assert items[0].unit_price_yuan == Decimal("20.00")
    assert items[0].calories_kcal == Decimal("450")


def test_merge_only_strips_outer_whitespace() -> None:
    products = [
        make_product("matched", " 示例汉堡 ", ["主食"]),
        make_product("unmatched", "示例 汉堡", ["主食"]),
    ]
    foods = [make_nutrition("示例汉堡", "450")]

    items = merge_menu_with_nutrition(products, foods)

    assert items[0].calories_kcal == Decimal("450")
    assert items[1].calories_kcal is None


def test_merge_keeps_missing_nutrition_empty_and_marks_uncategorized() -> None:
    products = [make_product("meal-1", "套餐名称")]

    items = merge_menu_with_nutrition(products, [])

    assert items[0].category == "未分类"
    assert items[0].calories_kcal is None


def test_merge_accepts_identical_duplicate_nutrition_rows() -> None:
    products = [make_product("meal-1", "示例饮料", ["饮品"])]
    foods = [
        make_nutrition("示例饮料", "100"),
        make_nutrition("示例饮料", "100"),
    ]

    items = merge_menu_with_nutrition(products, foods)

    assert items[0].calories_kcal == Decimal("100")


def test_merge_rejects_conflicting_duplicate_nutrition_without_guessing() -> None:
    products = [make_product("meal-1", "示例饮料", ["饮品"])]
    foods = [
        make_nutrition("示例饮料", "100"),
        make_nutrition("示例饮料", "120"),
    ]

    items = merge_menu_with_nutrition(products, foods)

    assert items[0].calories_kcal is None


def test_main_meal_filter_excludes_sauces_drinks_and_uncertain_share_platters() -> None:
    products = [
        make_product("burger", "示例汉堡", ["人气热卖", "鸡肉汉堡 /卷"]),
        make_product("combo", "示例单人餐", ["精选单人餐"]),
        make_product("sauce", "示例酱料", ["蘸酱炸鸡"]),
        make_product("drink", "示例饮料", ["饮品"]),
        make_product("share", "示例多人餐", ["小食拼盘 /多人餐"]),
        make_product("happy", "示例儿童附属商品", ["开心乐园"]),
    ]

    selected = select_main_meal_products(products)

    assert [product.product_code for product in selected] == ["burger", "combo"]


def test_main_meal_catalog_uses_eligible_category_instead_of_promotion() -> None:
    products = [
        make_product("burger", "示例汉堡", ["人气热卖", "鸡肉汉堡 /卷"])
    ]

    items = build_main_meal_catalog(products, [make_nutrition("示例汉堡", "450")])

    assert items[0].category == "鸡肉汉堡 /卷"
    assert items[0].calories_kcal == Decimal("450")
