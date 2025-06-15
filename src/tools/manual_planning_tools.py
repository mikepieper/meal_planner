import json
from typing import Annotated, Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command, ToolMessage

from src.models import MealPlannerState, MealItem
from src.constants import MEAL_TYPES, MealType
from src.tools.tool_utils import update_meal_with_items

# Initialize LLM for generation tools
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)


@tool
def add_meal_item(
    meal_type: MealType,
    food: str,
    amount: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    unit: str = "serving"
) -> Command:
    """Add a single food item to a specific meal.
    
    Use this tool to add one food item at a time to a meal.
    
    Parameters:
    - meal_type: Must be one of 'breakfast', 'lunch', 'dinner', or 'snacks'
    - food: Name of the food item (e.g., 'chicken breast', 'apple', 'greek yogurt')
    - amount: Quantity as string - supports fractions (e.g., '1', '2.5', '1/2', '1 1/4')
    - unit: Unit of measurement (e.g., 'cup', 'oz', 'slice', 'large', 'medium') - defaults to 'serving'
    
    Examples:
    - add_meal_item(meal_type="breakfast", food="oatmeal", amount="1", unit="cup")
    - add_meal_item(meal_type="lunch", food="chicken breast", amount="6", unit="oz")
    - add_meal_item(meal_type="dinner", food="salmon fillet", amount="1", unit="large")
    """
    new_item = MealItem(food=food, amount=amount, unit=unit)
    
    # Use helper to handle common meal update logic
    updates = update_meal_with_items(meal_type, [new_item], state)
    
    return Command(
        update=updates,
        messages=[
            ToolMessage(
                content=f"Successfully added {new_item.food} to {meal_type}",
                tool_call_id=tool_call_id
            )
        ]
    )


@tool
def add_multiple_items(
    meal_type: MealType,
    items: List[MealItem],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Add multiple food items to a meal in one operation.
    
    Use this tool when you want to add several items to a meal at once.
    Each item must have 'food' and 'amount', with 'unit' being optional (defaults to 'serving').
    
    Parameters:
    - meal_type: Must be one of 'breakfast', 'lunch', 'dinner', or 'snacks'
    - items: List of MealItemInput objects, each containing:
      * food: str - Name of the food item
      * amount: str - Quantity (supports fractions like '1/2', '1 1/4')
      * unit: str - Unit of measurement (optional, defaults to 'serving')
    
    Example:
    add_multiple_items(
        meal_type="lunch",
        items=[
            MealItemInput(food="chicken breast", amount="6", unit="oz"),
            MealItemInput(food="brown rice", amount="1", unit="cup"),
            MealItemInput(food="broccoli", amount="2", unit="cups"),
            MealItemInput(food="olive oil", amount="1", unit="tbsp")
        ]
    )
    """
    # Convert MealItemInput objects to MealItem objects
    new_items = [MealItem(food=item.food, amount=item.amount, unit=item.unit) for item in items]

    # Use helper to handle common meal update logic
    updates = update_meal_with_items(meal_type, new_items, state)
    meal_names = ", ".join([item.food for item in new_items])
    return Command(
        update=updates,
        messages=[
            ToolMessage(
                content=f"Successfully added {meal_names} items to {meal_type}",
                tool_call_id=tool_call_id
            )
        ]
    )


@tool
def remove_meal_item(
    food: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    meal_type: Optional[MealType] = None
) -> Command:
    """Remove a specific food item from a meal or all meals.
    
    If meal_type is specified, removes the first occurrence from that meal only.
    If meal_type is not specified, removes the first occurrence from each meal that contains it.
    Food name matching is case-insensitive.
    
    Parameters:
    - food: Name of the food item to remove (case-insensitive match)
    - meal_type: Optional - one of 'breakfast', 'lunch', 'dinner', or 'snacks'. 
                If not specified, removes from all meals containing the item.
    
    Examples:
    - remove_meal_item(food="oatmeal", meal_type="breakfast")  # Remove from breakfast only
    - remove_meal_item(food="broccoli")  # Remove from all meals containing broccoli
    """
    updates = {}
    removed_from = []
    
    if meal_type:
        # Remove from specific meal only
        meal_list = state[meal_type]
        updated_meal = []
        found = False
        
        for item in meal_list:
            if item.food.lower() == food.lower() and not found:
                found = True  # Skip this item (remove it)
                removed_from.append(meal_type)
            else:
                updated_meal.append(item)
        
        if found:
            updates[meal_type] = updated_meal
            updates["current_meal"] = meal_type
    else:
        # Remove from all meals that contain the item
        for meal in MEAL_TYPES:
            meal_list = state[meal]
            updated_meal = []
            found = False
            
            for item in meal_list:
                if item.food.lower() == food.lower() and not found:
                    found = True  # Skip this item (remove it)
                    removed_from.append(meal)
                else:
                    updated_meal.append(item)
            
            if found:
                updates[meal] = updated_meal

    if not removed_from:
        meal_context = f"in {meal_type}" if meal_type else "in any meal"
        return Command(update={}, messages=[
            ToolMessage(
                content=f"Food item '{food}' not found {meal_context}",
                tool_call_id=tool_call_id
            )
        ])

    # Create success message
    if len(removed_from) == 1:
        message = f"Successfully removed '{food}' from {removed_from[0]}"
    else:
        meals_list = ", ".join(removed_from)
        message = f"Successfully removed '{food}' from {meals_list}"

    return Command(
        update=updates,
        messages=[
            ToolMessage(
                content=message,
                tool_call_id=tool_call_id
            )
        ]
    )


@tool
def clear_meal(
    meal_type: MealType,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Remove all items from a specific meal, making it empty.
    
    Use this tool when you want to completely restart a meal or remove
    all items from a meal that doesn't meet requirements.
    
    Parameters:
    - meal_type: Must be one of 'breakfast', 'lunch', 'dinner', or 'snacks'
    
    Examples:
    - clear_meal(meal_type="breakfast")  # Empty breakfast completely
    - clear_meal(meal_type="snacks")     # Remove all snack items
    
    This is useful when meal suggestions don't work or when starting fresh.
    """
    return Command(
        update={
            meal_type: [],
            "current_meal": meal_type
        },
        messages=[
            ToolMessage(
                content=f"Successfully cleared {meal_type}",
                tool_call_id=tool_call_id
            )
        ]
    )


@tool
def clear_all_meals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Reset the entire meal plan to empty state.
    
    Removes all items from all meals (breakfast, lunch, dinner, snacks).
    This is a complete reset of the meal planning process.
    
    Use this tool when:
    - User wants to start completely over
    - Current meal plan doesn't meet requirements
    - Major dietary restrictions or goals have changed
    
    WARNING: This removes ALL meal planning progress.
    Consider using clear_meal() for individual meals instead.
    
    After using this tool, you'll need to rebuild the entire meal plan.
    """
    updates = {"current_meal": "breakfast"}
    for meal_type in MEAL_TYPES:
        updates[meal_type] = []
    
    return Command(
        update=updates,
        messages=[
            ToolMessage(
                content=f"Successfully cleared all meals",
                tool_call_id=tool_call_id
            )
        ]
    )

