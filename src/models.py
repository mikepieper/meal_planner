from typing import TypedDict, List, Dict, Any, Optional, Literal, Annotated, Sequence
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState, add_messages
from langchain_core.messages import BaseMessage


# ========== Pydantic Models ==========

class NutrientConstraint(BaseModel):
    """Defines min, target, and max values for a nutrient."""
    minimum: float = Field(..., description="Minimum acceptable amount")
    target: float = Field(..., description="Target/ideal amount")
    maximum: float = Field(..., description="Maximum acceptable amount")


class ConstraintSet(BaseModel):
    """Complete nutrition constraints for meal planning."""
    calories: NutrientConstraint
    fat: NutrientConstraint
    carbohydrates: NutrientConstraint
    protein: NutrientConstraint


class FoodItem(BaseModel):
    """Represents a food item with nutritional information."""
    id: str
    name: str
    calories: float
    fat: float
    carbohydrates: float
    protein: float
    is_beverage: bool = False
    min_quantity: float = 0.0
    max_quantity: float = 1.0
    unit: str = "serving"
#     tags: List[str] = Field(default_factory=list)  # vegetarian, vegan, gluten-free, etc.


class MealItem(BaseModel):
    """Information about a single item in a meal."""
    amount: str = Field(..., description="The quantity of the food item (e.g., '1', '1/2', 'two').")
    measure: Optional[str] = Field("unit", description="The unit of measurement (e.g., 'cup', 'oz', 'grams', 'piece').")
    food: str = Field(..., description="The name of the food item (e.g., 'grapes', 'chicken breast', 'olive oil').")

class Meal(BaseModel):
    """Represents a meal with multiple food items."""
    name: str = Field(..., description="The name of the meal (e.g., 'breakfast', 'lunch', 'dinner', 'snack').")
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    meal_items: List[MealItem]
    
    def calculate_nutrition(self, food_db: Dict[str, FoodItem]) -> Dict[str, float]:
        """Calculate total nutrition for the meal."""
        totals = {"calories": 0, "fat": 0, "carbohydrates": 0, "protein": 0}
        for food_id, quantity in self.foods.items():
            if (food := food_db.get(food_id)) is not None:
                totals["calories"] += food.calories * quantity
                totals["fat"] += food.fat * quantity
                totals["carbohydrates"] += food.carbohydrates * quantity
                totals["protein"] += food.protein * quantity
        return totals


class MealPlan(BaseModel):
    """Complete meal plan for a day."""
    breakfast: Optional[Meal] = None
    lunch: Optional[Meal] = None
    dinner: Optional[Meal] = None
    snacks: List[Meal] = Field(default_factory=list)
    
    def calculate_daily_nutrition(self, food_db: Dict[str, FoodItem]) -> Dict[str, float]:
        """Calculate total nutrition for the day."""
        totals = {"calories": 0, "fat": 0, "carbohydrates": 0, "protein": 0}
        
        for meal in [self.breakfast, self.lunch, self.dinner] + self.snacks:
            if meal:
                meal_nutrition = meal.calculate_nutrition(food_db)
                for nutrient, value in meal_nutrition.items():
                    totals[nutrient] += value
        
        return totals

class UserProfile(BaseModel):
    """User profile containing preferences and nutrition information."""
    daily_calories: Optional[int] = Field(None, description="Daily caloric target if specified")
    diet_type: Optional[str] = Field("balanced", description="Diet type: balanced, high_protein, low_carb, etc.")
    dietary_restrictions: List[str] = Field(default_factory=list, description="Allergies, intolerances, preferences")
    nutrition_goals: Optional[ConstraintSet] = Field(None, description="Calculated nutrition constraints")
    automation_preference: Optional[Literal["manual", "assisted", "automated"]] = Field(
        None, 
        description="User's preference for meal planning assistance level"
    )

# ========== State Definitions ==========

class MealPlannerState(TypedDict):
    """Main state for the meal planning agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_meal_plan: MealPlan
    user_profile: UserProfile  # dietary restrictions, preferences, nutrition goals
    food_database: Dict[str, FoodItem]
    conversation_phase: str
    optimization_history: List[Dict[str, Any]]
