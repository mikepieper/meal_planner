from typing import TypedDict, List, Dict, Any, Optional, Literal, Annotated, Sequence
from pydantic import BaseModel, Field, computed_field
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
import re
from fractions import Fraction


# # ========== Pydantic Models ==========

# class NutrientConstraint(BaseModel):
#     """Defines min, target, and max values for a nutrient."""
#     minimum: float = Field(..., description="Minimum acceptable amount")
#     target: float = Field(..., description="Target/ideal amount")
#     maximum: float = Field(..., description="Maximum acceptable amount")


# class ConstraintSet(BaseModel):
#     """Complete nutrition constraints for meal planning."""
#     calories: NutrientConstraint
#     fat: NutrientConstraint
#     carbohydrates: NutrientConstraint
#     protein: NutrientConstraint


# class FoodItem(BaseModel):
#     """Represents a food item with nutritional information."""
#     id: str
#     name: str
#     calories: float
#     fat: float
#     carbohydrates: float
#     protein: float
#     is_beverage: bool = False
#     min_quantity: float = 0.0
#     max_quantity: float = 1.0
#     unit: str = "serving"
# #     tags: List[str] = Field(default_factory=list)  # vegetarian, vegan, gluten-free, etc.


class MealItem(BaseModel):
    """Information about a single item in a meal."""
    food: str = Field(..., description="Name of the food item (e.g., 'chicken breast', 'brown rice')")
    amount: str = Field(..., description="Quantity as string - supports whole numbers, decimals, and fractions (e.g., '1', '2.5', '1/2', '1 1/4')")
    unit: str = Field("serving", description="Unit of measurement (e.g., 'cup', 'oz', 'slice', 'large', 'medium', 'serving')")


# class NutritionInfo(BaseModel):
#     """Nutritional information."""
#     calories: float = Field(0, description="Calories")
#     protein: float = Field(0, description="Protein in grams")
#     carbohydrates: float = Field(0, description="Carbohydrates in grams")
#     fat: float = Field(0, description="Fat in grams")

# # TODO: Duplicate fields for constraints
# class NutritionGoals(BaseModel):
#     """Daily nutrition goals."""
#     daily_calories: int = Field(..., description="Target daily calories")
#     diet_type: str = Field("balanced", description="Diet type: balanced, high-protein, low-carb, etc.")
#     protein_target: Optional[float] = Field(None, description="Daily protein target in grams")
#     carb_target: Optional[float] = Field(None, description="Daily carb target in grams")
#     fat_target: Optional[float] = Field(None, description="Daily fat target in grams")


class UserProfile(BaseModel):
    """User profile containing preferences and nutrition information."""
    dietary_restrictions: List[str] = Field(default_factory=list, description="Allergies, intolerances, preferences")
    preferred_cuisines: List[str] = Field(default_factory=list, description="Favorite cuisine types")
    cooking_time_preference: Optional[str] = Field(None, description="Quick, moderate, or extensive")
    health_goals: List[str] = Field(default_factory=list, description="Weight loss, muscle gain, etc.")


# class MealSuggestion(BaseModel):
#     """A suggested meal with items and nutrition info."""
#     name: str = Field(..., description="Name of the meal suggestion")
#     items: List[MealItem] = Field(default_factory=list, description="Items in this meal")
#     nutrition: NutritionInfo = Field(default_factory=NutritionInfo, description="Nutritional content")
#     description: Optional[str] = Field(None, description="Brief description")


# class MealPreferences(BaseModel):
#     """Input model for meal preferences with validation for tool usage."""
#     cuisine: Optional[str] = Field(None, description="Preferred cuisine type (e.g., 'italian', 'mediterranean', 'asian', 'mexican')")
#     cooking_time: Optional[str] = Field(None, description="Cooking time preference: 'quick' (<15 min), 'moderate' (15-45 min), 'extensive' (45+ min)")
#     meal_style: Optional[str] = Field(None, description="Style preference (e.g., 'light', 'hearty', 'comfort food', 'fresh')")
#     ingredients_to_include: Optional[List[str]] = Field(None, description="Specific ingredients to include")
#     ingredients_to_avoid: Optional[List[str]] = Field(None, description="Specific ingredients to avoid (beyond dietary restrictions)")


# class MealPlanResponse(BaseModel):
#     """Structured response for meal plan generation."""
#     breakfast: List[MealItem] = Field(default_factory=list)
#     lunch: List[MealItem] = Field(default_factory=list)
#     dinner: List[MealItem] = Field(default_factory=list)
#     snacks: List[MealItem] = Field(default_factory=list)


# class MealSuggestionOptions(BaseModel):
#     """Structured response for meal suggestions with three options."""
#     option_1: MealSuggestion
#     option_2: MealSuggestion  
#     option_3: MealSuggestion


# class ConversationContext(BaseModel):
#     """Tracks conversation state and memory."""
#     # Suggestions presented to user
#     last_suggestions: Dict[str, Dict[str, MealSuggestion]] = Field(
#         default_factory=dict,
#         description="Last suggestions shown for each meal type"
#     )

#     # Planning phase tracking
#     planning_phase: Literal["gathering_info", "setting_goals", "building_meals", "optimizing", "complete"] = Field(
#         "gathering_info",
#         description="Current phase of meal planning"
#     )

#     # User preferences mentioned in conversation
#     mentioned_preferences: Dict[str, Any] = Field(
#         default_factory=dict,
#         description="Preferences mentioned during conversation"
#     )

#     # Meal templates from successful combinations
#     saved_templates: Dict[str, MealSuggestion] = Field(
#         default_factory=dict,
#         description="Saved meal templates for reuse"
#     )


# ========== State Definition ==========

class MealPlannerState(BaseModel):
    """Main state for the meal planning agent - using Pydantic for proper defaults."""
    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(default_factory=list)

    # Conversation summary for managing long conversations
    summary: str = Field("", description="Summary of earlier conversation history")

    # Simple meal storage - just lists of MealItems
    breakfast: List[MealItem] = Field(default_factory=list)
    lunch: List[MealItem] = Field(default_factory=list)
    dinner: List[MealItem] = Field(default_factory=list)
    snacks: List[MealItem] = Field(default_factory=list)

    # User information
    user_profile: UserProfile = Field(default_factory=UserProfile)
#     nutrition_goals: Optional[NutritionGoals] = None

#     # Enhanced conversation tracking
#     conversation_context: ConversationContext = Field(default_factory=ConversationContext)

#     # Current meal being edited (for context)
#     current_meal: Literal["breakfast", "lunch", "dinner", "snacks"] = "breakfast"

#     # Running nutrition totals - now computed automatically
#     # current_totals: Optional[NutritionInfo] = None

#     def _parse_amount(self, amount_str: str) -> float:
#         """Parse amount string to float, handling fractions like '1/2', '1 1/2'."""
#         amount_str = amount_str.strip()
        
#         # Handle mixed numbers like "1 1/2"
#         mixed_match = re.match(r'^(\d+)\s+(\d+)/(\d+)$', amount_str)
#         if mixed_match:
#             whole, num, den = mixed_match.groups()
#             return float(whole) + float(num) / float(den)
        
#         # Handle simple fractions like "1/2"
#         if '/' in amount_str:
#             try:
#                 return float(Fraction(amount_str))
#             except ValueError:
#                 pass
        
#         # Handle decimals and whole numbers
#         try:
#             return float(amount_str)
#         except ValueError:
#             # Default to 1 if we can't parse
#             return 1.0

#     def _get_food_database(self) -> Dict[str, 'FoodItem']:
#         """Get the food database. Import here to avoid circular imports."""
#         try:
#             from .food_database import get_food_database
#             return get_food_database()
#         except ImportError:
#             return {}

#     def _calculate_item_nutrition(self, item: MealItem, food_db: Dict[str, 'FoodItem']) -> NutritionInfo:
#         """Calculate nutrition for a single meal item using the food database."""
#         # Try to find exact match first
#         food_item = None
#         food_key = item.food.lower().replace(' ', '_')
        
#         # Look for exact match by ID
#         if food_key in food_db:
#             food_item = food_db[food_key]
#         else:
#             # Look for name match
#             for fid, fitem in food_db.items():
#                 if fitem.name.lower() == item.food.lower():
#                     food_item = fitem
#                     break
        
#         if not food_item:
#             # If not found in database, return zero nutrition
#             # In a real app, you might want to log this or use LLM as fallback
#             return NutritionInfo(calories=0, protein=0, carbohydrates=0, fat=0)
        
#         # Parse the amount
#         multiplier = self._parse_amount(item.amount)
        
#         # Calculate nutrition based on the multiplier
#         return NutritionInfo(
#             calories=food_item.calories * multiplier,
#             protein=food_item.protein * multiplier,
#             carbohydrates=food_item.carbohydrates * multiplier,
#             fat=food_item.fat * multiplier
#         )

#     def calculate_nutrition_totals(self) -> NutritionInfo:
#         """Calculate total nutrition from all meals using the food database."""
#         food_db = self._get_food_database()
        
#         total = NutritionInfo(calories=0, protein=0, carbohydrates=0, fat=0)
        
#         # Sum up all meals
#         for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
#             meal_items = getattr(self, meal_type, [])
#             for item in meal_items:
#                 item_nutrition = self._calculate_item_nutrition(item, food_db)
#                 total.calories += item_nutrition.calories
#                 total.protein += item_nutrition.protein
#                 total.carbohydrates += item_nutrition.carbohydrates
#                 total.fat += item_nutrition.fat
        
#         return total

#     @computed_field
#     @property
#     def current_totals(self) -> NutritionInfo:
#         """Automatically calculated nutrition totals (computed field)."""
#         return self.calculate_nutrition_totals()

#     @computed_field
#     @property
#     def nutrition_summary(self) -> str:
#         """Formatted nutrition summary for display."""
#         totals = self.current_totals
#         return f"Calories: {totals.calories:.0f}, Protein: {totals.protein:.0f}g, Carbs: {totals.carbohydrates:.0f}g, Fat: {totals.fat:.0f}g"

#     @computed_field
#     @property
#     def nutrition_context_for_prompts(self) -> str:
#         """Standard nutrition context for LLM prompts."""
#         if not self.nutrition_goals:
#             return ""
        
#         totals = self.current_totals
#         goals = self.nutrition_goals
        
#         # Calculate remaining needs
#         calories_remaining = max(0, goals.daily_calories - totals.calories)
#         protein_remaining = max(0, goals.protein_target - totals.protein)
#         carbs_remaining = max(0, goals.carb_target - totals.carbohydrates)
#         fat_remaining = max(0, goals.fat_target - totals.fat)
        
#         # Calculate progress percentages
#         calories_percent = (totals.calories / goals.daily_calories * 100)
#         protein_percent = (totals.protein / goals.protein_target * 100)
        
#         context = f"""Current nutrition status:
# - Consumed: {self.nutrition_summary}
# - Remaining: Calories: {calories_remaining:.0f}, Protein: {protein_remaining:.0f}g, Carbs: {carbs_remaining:.0f}g, Fat: {fat_remaining:.0f}g
# - Progress: {calories_percent:.0f}% of daily calories, {protein_percent:.0f}% of protein goal
# - Diet type: {goals.diet_type}"""
        
#         return context

#     @computed_field
#     @property
#     def has_sufficient_nutrition(self) -> bool:
#         """Check if current nutrition meets minimum goals (within 10% of calorie target)."""
#         if not self.nutrition_goals:
#             return False
        
#         totals = self.current_totals
#         goals = self.nutrition_goals
#         calorie_percent = totals.calories / goals.daily_calories
#         return 0.9 <= calorie_percent <= 1.1
