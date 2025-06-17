from typing import List, Dict, Any
from src.models import MealItem
from src.models import MealPlannerState


def update_meal_with_items(
    meal_type: str,
    new_items: List[MealItem], 
    state: MealPlannerState
) -> Dict[str, Any]:
    """
    Helper function to update a meal with new items and handle phase transitions.
    Returns the update dictionary for a Command.
    """
    # Add all items to the meal
    updated_meal = getattr(state,meal_type) + new_items

    # Update planning phase if appropriate - use temporary state to check transitions
    temp_state = state.model_copy()
    setattr(temp_state, meal_type, updated_meal)
    
    return {
        meal_type: updated_meal,
        "current_meal": meal_type,
    }


