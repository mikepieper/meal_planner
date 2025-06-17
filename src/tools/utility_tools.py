from typing import Annotated

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from src.models import MealPlannerState, MEAL_TYPES

# Initialize LLM for generation tools
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)


@tool
def generate_shopping_list(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Create a consolidated shopping list from all meals in the current meal plan.
    
    Combines all food items across breakfast, lunch, dinner, and snacks into
    an organized shopping list. Consolidates duplicate items and shows total quantities.
    
    This tool is most useful:
    - After completing a meal plan
    - When user is ready to shop for ingredients
    - To see total quantities needed for meal prep
    
    Returns formatted shopping list with:
    - All unique food items
    - Combined quantities for items used in multiple meals
    - Clear indication when items appear in multiple meals
    
    Example output format:
    - chicken breast: 12 oz (total from multiple meals)
    - brown rice: 2 cups
    - broccoli: 3 cups
    
    Returns message if meal plan is empty.
    """
    all_items = {}

    # Collect all items from all meals
    for meal_type in MEAL_TYPES:
        for item in getattr(state,meal_type):
            key = item.food.lower()
            if key not in all_items:
                all_items[key] = []
            all_items[key].append(f"{item.amount} {item.unit}")

    if not all_items:
        content = "No items in meal plan to create shopping list."
    else:
        # Build shopping list
        shopping_list = "Shopping List:\n\n"
        for food, amounts in sorted(all_items.items()):
            if len(amounts) == 1:
                shopping_list += f"- {food.capitalize()}: {amounts[0]}\n"
            else:
                shopping_list += f"- {food.capitalize()}: {', '.join(amounts)} (total from multiple meals)\n"
        content = shopping_list

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=content,
                    tool_call_id=tool_call_id
                )
            ]
        }
    )
