from typing import List, Dict, Any
from src.models import MealItem, MealPlannerState
from src.constants import MEAL_TYPES



def add_dietary_restrictions_context(context: str, restrictions: List[str]) -> str:
    """Add dietary restrictions warning to context."""
    if restrictions:
        context += f"Dietary restrictions: {', '.join(restrictions)}\n"
        context += f"⚠️ CRITICAL: You MUST NOT include ANY foods that violate these restrictions!\n"
        context += "This is extremely important - double-check every single item.\n\n"
    return context

# def update_planning_phase(state: MealPlannerState, context) -> Any:
#     """Update planning phase based on current state."""
#     new_context = context.model_copy()
    
#     if new_context.planning_phase == "gathering_info" and state.nutrition_goals:
#         new_context.planning_phase = "building_meals"
#     elif new_context.planning_phase == "setting_goals":
#         new_context.planning_phase = "building_meals"
#     elif new_context.planning_phase == "building_meals" and state.has_sufficient_nutrition:
#         new_context.planning_phase = "optimizing"
#     elif new_context.planning_phase == "optimizing" and state.has_sufficient_nutrition:
#         new_context.planning_phase = "complete"
    
#     # Special case for when meals already exist
#     meals_with_items = sum(1 for meal in MEAL_TYPES if getattr(state, meal))
#     if meals_with_items > 0 and new_context.planning_phase == "setting_goals":
#         new_context.planning_phase = "building_meals"
#         if meals_with_items >= 2:
#             new_context.planning_phase = "optimizing"
    
#     return new_context

# def update_meal_with_items(
#     meal_type: str,
#     new_items: List[MealItem], 
#     state: MealPlannerState
# ) -> Dict[str, Any]:
#     """
#     Helper function to update a meal with new items and handle phase transitions.
#     Returns the update dictionary for a Command.
#     """
#     # Add all items to the meal
#     updated_meal = state[meal_type] + new_items

#     # Update planning phase if appropriate - use temporary state to check transitions
#     temp_state = state.model_copy()
#     setattr(temp_state, meal_type, updated_meal)
    
#     new_context = update_planning_phase(temp_state, state["conversation_context"])

#     return {
#         meal_type: updated_meal,
#         "current_meal": meal_type,
#         "conversation_context": new_context
#     }