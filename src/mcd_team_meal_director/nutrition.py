"""Parsing for the compact nutrition table returned by McDonald's China MCP."""

import csv
import re
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from mcd_team_meal_director.models import NutritionFood


EXPECTED_FIELDS = (
    "productName",
    "nutritionDescription",
    "energyKj",
    "energyKcal",
    "protein",
    "fat",
    "carbohydrate",
    "sodium",
    "calcium",
)
HEADER_PATTERN = re.compile(r"^\[(\d+)]\{([^}]+)}:$")


class NutritionDataError(ValueError):
    """Raised when MCP nutrition data does not match the observed format."""


def parse_nutrition_table(data: str) -> list[NutritionFood]:
    """Parse the compact table stored in ``structuredContent.data``."""
    lines = data.strip().splitlines()
    if not lines:
        raise NutritionDataError("nutrition data is empty")

    header_match = HEADER_PATTERN.fullmatch(lines[0].strip())
    if header_match is None:
        raise NutritionDataError("nutrition data header is invalid")

    declared_count = int(header_match.group(1))
    fields = tuple(field.strip() for field in header_match.group(2).split(","))
    if fields != EXPECTED_FIELDS:
        raise NutritionDataError("nutrition data fields have changed")

    foods: list[NutritionFood] = []
    for row_number, line in enumerate(lines[1:], start=1):
        if not line.strip():
            continue

        values = next(csv.reader([line.strip()]))
        if len(values) != len(EXPECTED_FIELDS):
            raise NutritionDataError(
                f"nutrition row {row_number} has {len(values)} fields; "
                f"expected {len(EXPECTED_FIELDS)}"
            )

        description = values[1].strip()
        try:
            food = NutritionFood(
                product_name=values[0].strip(),
                nutrition_description=(
                    None if description.lower() == "null" else description
                ),
                energy_kj=Decimal(values[2].strip()),
                energy_kcal=Decimal(values[3].strip()),
                protein=Decimal(values[4].strip()),
                fat=Decimal(values[5].strip()),
                carbohydrate=Decimal(values[6].strip()),
                sodium=Decimal(values[7].strip()),
                calcium=Decimal(values[8].strip()),
            )
        except (InvalidOperation, ValidationError) as error:
            raise NutritionDataError(
                f"nutrition row {row_number} contains invalid values"
            ) from error
        foods.append(food)

    if len(foods) != declared_count:
        raise NutritionDataError(
            f"nutrition data declares {declared_count} rows but contains {len(foods)}"
        )
    return foods
