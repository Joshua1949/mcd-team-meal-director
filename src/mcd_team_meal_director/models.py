"""Domain models for team meal planning."""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field, model_validator


class PlanGoal(StrEnum):
    """Optimization goal used to distinguish the three required plans."""

    LOWEST_COST = "lowest_cost"
    BALANCED = "balanced"
    MOST_VARIETY = "most_variety"


class MealItem(BaseModel):
    """Normalized menu item used by the deterministic planning engine."""

    item_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    unit_price_yuan: Decimal = Field(ge=0)
    calories_kcal: Decimal | None = Field(default=None, ge=0)


class NutritionFood(BaseModel):
    """One normalized row returned by ``list-nutrition-foods``."""

    product_name: str = Field(min_length=1)
    nutrition_description: str | None = None
    energy_kj: Decimal = Field(ge=0)
    energy_kcal: Decimal = Field(ge=0)
    protein: Decimal = Field(ge=0)
    fat: Decimal = Field(ge=0)
    carbohydrate: Decimal = Field(ge=0)
    sodium: Decimal = Field(ge=0)
    calcium: Decimal = Field(ge=0)


class MenuProduct(BaseModel):
    """Normalized product from a store-specific ``query-meals`` response."""

    product_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    current_price_yuan: Decimal = Field(ge=0)
    original_price_yuan: Decimal | None = Field(default=None, ge=0)
    category_names: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    can_with_order: bool = False


class MealPlanLine(BaseModel):
    """A menu item and the quantity selected for a meal plan."""

    item: MealItem
    quantity: int = Field(gt=0)

    @computed_field
    @property
    def subtotal_yuan(self) -> Decimal:
        """Return the estimated subtotal for this line."""
        return self.item.unit_price_yuan * self.quantity


class MealPlan(BaseModel):
    """One candidate plan generated for a specific optimization goal."""

    goal: PlanGoal
    lines: list[MealPlanLine] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def estimated_total_yuan(self) -> Decimal:
        """Return the sum of all estimated line subtotals."""
        return sum((line.subtotal_yuan for line in self.lines), start=Decimal("0"))


class TeamMealRequest(BaseModel):
    """Validated input for generating team meal plans."""

    party_size: int = Field(gt=0, description="Number of people sharing the meal")
    budget_yuan: Decimal = Field(gt=0, description="Total budget in Chinese yuan")
    dietary_goals: list[str] = Field(
        default_factory=list,
        description="Free-form dietary goals shared by the group",
    )
    calorie_conscious_count: int = Field(
        default=0,
        ge=0,
        description="Number of people who want to control calorie intake",
    )

    @model_validator(mode="after")
    def validate_calorie_conscious_count(self) -> "TeamMealRequest":
        """Ensure subgroup counts cannot exceed the whole party."""
        if self.calorie_conscious_count > self.party_size:
            raise ValueError("calorie_conscious_count cannot exceed party_size")
        return self
