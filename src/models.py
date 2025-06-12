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
    food: str = Field(..., description="The name of the food item")
    amount: str = Field(..., description="The quantity (e.g., '1', '2', '1/2')")
    unit: str = Field("serving", description="The unit (e.g., 'cup', 'oz', 'large', 'slice')")


class NutritionInfo(BaseModel):
    """Nutritional information."""
    calories: float = Field(0, description="Calories")
    protein: float = Field(0, description="Protein in grams")
    carbohydrates: float = Field(0, description="Carbohydrates in grams")
    fat: float = Field(0, description="Fat in grams")


class NutritionGoals(BaseModel):
    """Daily nutrition goals."""
    daily_calories: int = Field(..., description="Target daily calories")
    diet_type: str = Field("balanced", description="Diet type: balanced, high-protein, low-carb, etc.")
    protein_target: Optional[float] = Field(None, description="Daily protein target in grams")
    carb_target: Optional[float] = Field(None, description="Daily carb target in grams")
    fat_target: Optional[float] = Field(None, description="Daily fat target in grams")


class UserProfile(BaseModel):
    """User profile containing preferences and nutrition information."""
    dietary_restrictions: List[str] = Field(default_factory=list, description="Allergies, intolerances, preferences")
    preferred_cuisines: List[str] = Field(default_factory=list, description="Favorite cuisine types")
    cooking_time_preference: Optional[str] = Field(None, description="Quick, moderate, or extensive")
    health_goals: List[str] = Field(default_factory=list, description="Weight loss, muscle gain, etc.")


# ========== State Definition ==========

class MealPlannerState(TypedDict):
    """Main state for the meal planning agent - simplified version."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Simple meal storage - just lists of MealItems
    breakfast: List[MealItem]
    lunch: List[MealItem] 
    dinner: List[MealItem]
    snacks: List[MealItem]
    
    # User information
    user_profile: UserProfile
    nutrition_goals: Optional[NutritionGoals]
    
    # Conversation tracking
    conversation_context: Dict[str, Any]
    
    # Current meal being edited (for context)
    current_meal: Literal["breakfast", "lunch", "dinner", "snacks"]


def create_initial_state() -> MealPlannerState:
    """Create initial state with proper defaults."""
    return {
        "messages": [],
        "breakfast": [],
        "lunch": [],
        "dinner": [],
        "snacks": [],
        "user_profile": UserProfile(),
        "nutrition_goals": None,
        "conversation_context": {},
        "current_meal": "breakfast"
    }
