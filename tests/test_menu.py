from decimal import Decimal

import pytest

from mcd_team_meal_director.menu import MenuDataError, parse_store_menu


def test_parse_store_menu_normalizes_prices_categories_and_tags() -> None:
    data = {
        "categories": [
            {
                "name": "人气热卖",
                "meals": [
                    {"code": "meal-1", "tags": ["优惠"]},
                    {"code": "meal-2"},
                ],
            },
            {
                "name": "鸡肉汉堡\n/卷",
                "meals": [{"code": "meal-1", "tags": ["优惠", "可特调"]}],
            },
        ],
        "meals": {
            "meal-1": {
                "name": "示例汉堡",
                "image": "https://example.invalid/image.png",
                "currentPrice": "18.5",
                "originalPrice": "22",
                "canWithOrder": True,
            },
            "meal-2": {
                "name": "示例饮料",
                "currentPrice": "8",
                "originalPrice": "8",
                "canWithOrder": False,
            },
        },
    }

    products = parse_store_menu(data)

    assert len(products) == 2
    assert products[0].product_code == "meal-1"
    assert products[0].current_price_yuan == Decimal("18.5")
    assert products[0].original_price_yuan == Decimal("22")
    assert products[0].category_names == ["人气热卖", "鸡肉汉堡 /卷"]
    assert products[0].tags == ["优惠", "可特调"]
    assert products[0].can_with_order is True
    assert not hasattr(products[0], "image")


def test_parse_store_menu_keeps_uncategorized_products() -> None:
    products = parse_store_menu(
        {
            "categories": [],
            "meals": {
                "meal-1": {
                    "name": "示例餐品",
                    "currentPrice": "10",
                    "originalPrice": None,
                }
            },
        }
    )

    assert products[0].category_names == []
    assert products[0].original_price_yuan is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"categories": {}, "meals": {}}, "categories"),
        ({"categories": [], "meals": []}, "meals"),
        (
            {
                "categories": [
                    {"name": "主食", "meals": [{"code": "missing"}]}
                ],
                "meals": {},
            },
            "unknown product code",
        ),
        (
            {
                "categories": [],
                "meals": {
                    "meal-1": {
                        "name": "示例",
                        "currentPrice": "not-a-price",
                    }
                },
            },
            "invalid values",
        ),
    ],
)
def test_parse_store_menu_rejects_malformed_data(
    data: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(MenuDataError, match=message):
        parse_store_menu(data)
