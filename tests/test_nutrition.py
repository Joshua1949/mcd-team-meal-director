from decimal import Decimal

import pytest

from mcd_team_meal_director.nutrition import NutritionDataError, parse_nutrition_table


SAMPLE_TABLE = """[3]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  猪柳麦满分,null,1288,308,16,16,24,781,213
  芝士安格斯厚牛堡,能量约鲈鱼1条,2914,696,32,44,43,897,150
  无糖可口可乐中杯,null,0,0,0,0,1,35,0
"""


def test_parse_nutrition_table_normalizes_real_response_shape() -> None:
    foods = parse_nutrition_table(SAMPLE_TABLE)

    assert len(foods) == 3
    assert foods[0].product_name == "猪柳麦满分"
    assert foods[0].nutrition_description is None
    assert foods[0].energy_kcal == Decimal("308")
    assert foods[0].protein == Decimal("16")
    assert foods[1].nutrition_description == "能量约鲈鱼1条"
    assert foods[2].energy_kcal == Decimal("0")


def test_parse_nutrition_table_supports_quoted_csv_values() -> None:
    table = """[1]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  示例餐品,"含逗号,仍可解析",100,24,1,2,3,4,5
"""

    foods = parse_nutrition_table(table)

    assert foods[0].nutrition_description == "含逗号,仍可解析"


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ("", "empty"),
        ("invalid", "header"),
        (
            "[1]{productName,energyKcal}:\n示例,100",
            "fields have changed",
        ),
        (
            "[2]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:\n"
            "示例,null,100,24,1,2,3,4,5",
            "declares 2 rows",
        ),
        (
            "[1]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:\n"
            "示例,null,not-a-number,24,1,2,3,4,5",
            "invalid values",
        ),
    ],
)
def test_parse_nutrition_table_rejects_malformed_data(
    table: str,
    message: str,
) -> None:
    with pytest.raises(NutritionDataError, match=message):
        parse_nutrition_table(table)
