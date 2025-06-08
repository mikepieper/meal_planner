import json

from langgraph.prebuilt import InjectedState
from typing import Annotated, Optional, List, Dict, Any
from langchain_core.tools import tool
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId

from src.models import State, MealItem

def _validate_meal(meal: Optional[str], state: State) -> str:
    """Helper function to validate and return the correct meal."""
    if meal is None:
        meal = state["current_meal"]
    if meal not in ["breakfast", "lunch", "dinner"]:
        raise ValueError("Invalid meal specified. Choose 'breakfast', 'lunch', or 'dinner'.")
    return meal

def _create_command(updates: Dict[str, Any], message: str, tool_call_id: str, update_current_meal: Optional[str] = None) -> Command:
    """Helper function to create a Command with updates and message.
    
    Args:
        updates: Dictionary of state updates
        message: Message to add to state
        tool_call_id: Tool call ID for the message
        update_current_meal: If provided, updates the current_meal state
    """
    if update_current_meal:
        updates["current_meal"] = update_current_meal
    
    if "messages" not in updates:
        updates["messages"] = [ToolMessage(message, tool_call_id=tool_call_id)]
    
    return Command(update=updates)

@tool
def add_meal_item(
    food: str,
    amount: str,
    measure: Optional[str],
    meal: Optional[str],
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Add a meal item to the specified meal or the current meal."""
    measure = measure or "unit"
    meal = _validate_meal(meal, state)

    new_item = MealItem(amount=amount, measure=measure, food=food)
    state[meal].append(new_item)

    return _create_command(
        {meal: state[meal]}, 
        f"Added {amount} {measure} of {food} to {meal}.", 
        tool_call_id,
        update_current_meal=meal
    )

@tool
def remove_meal_item(
    food: str,
    meal: Optional[str],
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Remove a meal item from the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    meal_list = state[meal]
    for item in meal_list:
        if item.food == food:
            meal_list.remove(item)
            break
    else:
        raise ValueError(f"{food} not found in {meal}.")

    return _create_command(
        {meal: meal_list, "current_meal": meal},
        f"Removed {food} from {meal}.",
        tool_call_id
    )

@tool
def update_meal_item(
    food: str,
    new_amount: Optional[str],
    new_measure: Optional[str],
    new_food: Optional[str],
    meal: Optional[str],
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Update a meal item in the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    meal_list = state[meal]
    for item in meal_list:
        if item.food == food:
            if new_amount:
                item.amount = new_amount
            if new_measure:
                item.measure = new_measure
            if new_food:
                item.food = new_food
            break
    else:
        raise ValueError(f"{food} not found in {meal}.")

    return _create_command(
        {meal: meal_list, "current_meal": meal},
        f"Updated {food} in {meal}.",
        tool_call_id
    )

@tool
def clear_meal(
    meal: Optional[str],
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Clear all items from the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    state[meal] = []

    return _create_command(
        {meal: [], "current_meal": meal},
        f"Cleared {meal}.",
        tool_call_id
    )

@tool
def clear_meal_plan(
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Clear the entire meal plan."""
    return _create_command(
        {"breakfast": [], "lunch": [], "dinner": [], "current_meal": "breakfast"},
        "Cleared the entire meal plan.",
        tool_call_id
    )

@tool
def add_multiple_meal_items(
    items: List[MealItem],
    meal: Optional[str],
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Add multiple meal items to the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    added_items = []
    for item_input in items:
        measure = item_input.measure or "unit"
        new_item = MealItem(amount=item_input.amount, measure=measure, food=item_input.food)
        state[meal].append(new_item)
        added_items.append(f"{item_input.amount} {measure} of {item_input.food}")

    return _create_command(
        {meal: state[meal]},
        "Added " + ", ".join(added_items) + f" to {meal}.",
        tool_call_id
    )


@tool
def set_nutrition_goals(
    daily_calories: int,
    diet_type: Optional[str] = "balanced"
) -> str:
    """Set personalized nutrition goals based on calorie target and diet type."""
    # Calculate macro targets based on diet type
    if "high_protein" in str(diet_type).lower() or diet_type == "high_protein":
        protein_percent = 0.30
        carb_percent = 0.40
        fat_percent = 0.30
    elif "low_carb" in str(diet_type).lower() or diet_type == "low_carb":
        protein_percent = 0.25
        carb_percent = 0.20
        fat_percent = 0.55
    else:  # balanced
        protein_percent = 0.20
        carb_percent = 0.50
        fat_percent = 0.30
    
    goals = {
        "calories": {
            "minimum": daily_calories * 0.9,
            "target": daily_calories,
            "maximum": daily_calories * 1.1
        },
        "protein": {
            "minimum": (daily_calories * protein_percent / 4) * 0.9,  # 4 cal/g
            "target": daily_calories * protein_percent / 4,
            "maximum": (daily_calories * protein_percent / 4) * 1.1
        },
        "carbohydrates": {
            "minimum": (daily_calories * carb_percent / 4) * 0.9,  # 4 cal/g
            "target": daily_calories * carb_percent / 4,
            "maximum": (daily_calories * carb_percent / 4) * 1.1
        },
        "fat": {
            "minimum": (daily_calories * fat_percent / 9) * 0.9,  # 9 cal/g
            "target": daily_calories * fat_percent / 9,
            "maximum": (daily_calories * fat_percent / 9) * 1.1
        }
    }
    
    return json.dumps(goals, indent=2)