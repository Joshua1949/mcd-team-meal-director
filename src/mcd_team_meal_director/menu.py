"""Normalization for store menus returned by McDonald's China MCP."""

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from mcd_team_meal_director.models import MenuProduct


class MenuDataError(ValueError):
    """Raised when a real menu does not match the observed MCP structure."""


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def parse_store_menu(data: Mapping[str, Any]) -> list[MenuProduct]:
    """Normalize ``structuredContent.data`` from ``query-meals``."""
    categories = data.get("categories")
    meals = data.get("meals")
    if not isinstance(categories, list):
        raise MenuDataError("menu categories must be a list")
    if not isinstance(meals, Mapping):
        raise MenuDataError("menu meals must be an object")

    categories_by_code: dict[str, list[str]] = {}
    tags_by_code: dict[str, list[str]] = {}
    for category_index, category in enumerate(categories, start=1):
        if not isinstance(category, Mapping):
            raise MenuDataError(f"menu category {category_index} must be an object")
        category_name = category.get("name")
        references = category.get("meals")
        if not isinstance(category_name, str) or not category_name.strip():
            raise MenuDataError(f"menu category {category_index} has no name")
        if not isinstance(references, list):
            raise MenuDataError(
                f"menu category {category_name!r} references must be a list"
            )

        normalized_category = " ".join(category_name.split())
        for reference in references:
            if not isinstance(reference, Mapping):
                raise MenuDataError(
                    f"menu category {category_name!r} contains an invalid reference"
                )
            code = reference.get("code")
            if not isinstance(code, str) or not code.strip():
                raise MenuDataError(
                    f"menu category {category_name!r} contains an empty product code"
                )
            _append_unique(categories_by_code.setdefault(code, []), normalized_category)

            tags = reference.get("tags", [])
            if not isinstance(tags, list) or not all(
                isinstance(tag, str) for tag in tags
            ):
                raise MenuDataError(
                    f"menu product {code!r} contains invalid category tags"
                )
            for tag in tags:
                _append_unique(tags_by_code.setdefault(code, []), tag)

    missing_codes = sorted(set(categories_by_code) - set(meals))
    if missing_codes:
        raise MenuDataError(
            f"menu categories reference unknown product code {missing_codes[0]!r}"
        )

    products: list[MenuProduct] = []
    for product_code, raw_product in meals.items():
        if not isinstance(product_code, str) or not product_code.strip():
            raise MenuDataError("menu contains an empty product code")
        if not isinstance(raw_product, Mapping):
            raise MenuDataError(f"menu product {product_code!r} must be an object")

        try:
            product = MenuProduct(
                product_code=product_code,
                name=raw_product.get("name"),
                current_price_yuan=raw_product.get("currentPrice"),
                original_price_yuan=raw_product.get("originalPrice"),
                category_names=categories_by_code.get(product_code, []),
                tags=tags_by_code.get(product_code, []),
                can_with_order=raw_product.get("canWithOrder", False),
            )
        except ValidationError as error:
            raise MenuDataError(
                f"menu product {product_code!r} contains invalid values"
            ) from error
        products.append(product)

    return products
