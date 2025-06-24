from src.models import MealPlannerState, MEAL_TYPES
from typing import List, Annotated

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage

@tool
def view_current_meal_plan(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Display a comprehensive overview of the current meal plan.
    
    Shows all meals (breakfast, lunch, dinner, snacks) with their items and portions,
    current daily nutrition totals, and progress toward nutrition goals if set.
    
    This tool is essential for:
    - Reviewing what's currently planned
    - Checking progress toward nutrition goals
    - Identifying empty meals that need to be filled
    
    Use this tool when users ask to see their current meal plan or when they want
    to review what's currently planned before making changes.
    """
    result = "**Current Meal Plan:**\n\n"

    for meal_type in MEAL_TYPES:
        items = getattr(state, meal_type)
        if items:
            result += f"**{meal_type.capitalize()}:**\n"
            for item in items:
                result += f"  - {item.amount} {item.unit} of {item.food}\n"
            result += "\n"
        else:
            result += f"**{meal_type.capitalize()}:** Empty\n\n"

    # Add current nutrition totals
    result += f"**Current Daily Totals:**\n- {state.nutrition_summary}\n"

    # Compare to goals if set
    if state.nutrition_goals:
        goals = state.nutrition_goals
        totals = state.current_totals
        result += "\n**Progress to Goals:**\n"
        calories_percent = (totals.calories/goals.daily_calories*100)
        protein_percent = (totals.protein/goals.protein_target*100)
        result += f"- Calories: {totals.calories:.0f} / {goals.daily_calories} ({calories_percent:.0f}%)\n"
        result += f"- Protein: {totals.protein:.0f}g / {goals.protein_target:.0f}g ({protein_percent:.0f}%)\n"

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=result.strip(),
                    tool_call_id=tool_call_id
                )
            ]
        }
    )

def get_meal_plan_display(state: MealPlannerState) -> str:
    """Helper function to get meal plan display without tool call overhead.
    
    Use this when you need the meal plan content as a string for inclusion
    in other tool responses (like after modifications).
    """
    result = "**Updated Meal Plan:**\n\n"

    for meal_type in MEAL_TYPES:
        items = getattr(state, meal_type)
        if items:
            result += f"**{meal_type.capitalize()}:**\n"
            for item in items:
                result += f"  - {item.amount} {item.unit} of {item.food}\n"
            result += "\n"
        else:
            result += f"**{meal_type.capitalize()}:** Empty\n\n"

    # Add current nutrition totals
    result += f"**Current Daily Totals:**\n- {state.nutrition_summary}\n"

    # Compare to goals if set
    if state.nutrition_goals:
        goals = state.nutrition_goals
        totals = state.current_totals
        result += "\n**Progress to Goals:**\n"
        calories_percent = (totals.calories/goals.daily_calories*100)
        protein_percent = (totals.protein/goals.protein_target*100)
        result += f"- Calories: {totals.calories:.0f} / {goals.daily_calories} ({calories_percent:.0f}%)\n"
        result += f"- Protein: {totals.protein:.0f}g / {goals.protein_target:.0f}g ({protein_percent:.0f}%)\n"

    return result.strip()


def get_daily_nutrition_summary(state: MealPlannerState) -> str:
    """Return total daily nutritional content and compare to goals."""
    result = "**Daily Nutrition Analysis:**\n\n"
    result += f"**Current Totals:**\n- {state.nutrition_summary}\n"

    if state.nutrition_goals:
        goals = state.nutrition_goals
        totals = state.current_totals
        result += "\n**Goals:**\n"
        result += f"- Calories: {goals.daily_calories}\n"
        result += f"- Protein: {goals.protein_target:.0f}g\n"
        result += f"- Carbohydrates: {goals.carb_target:.0f}g\n"
        result += f"- Fat: {goals.fat_target:.0f}g\n"

        result += "\n**Progress:**\n"
        result += f"- Calories: {(totals.calories/goals.daily_calories*100):.0f}% of goal\n"
        result += f"- Protein: {(totals.protein/goals.protein_target*100):.0f}% of goal\n"
        result += f"- Carbohydrates: {(totals.carbohydrates/goals.carb_target*100):.0f}% of goal\n"
        result += f"- Fat: {(totals.fat/goals.fat_target*100):.0f}% of goal\n"

        # Calculate remaining needs
        result += "\n**Remaining for the day:**\n"
        result += f"- Calories: {max(0, goals.daily_calories - totals.calories):.0f}\n"
        result += f"- Protein: {max(0, goals.protein_target - totals.protein):.0f}g\n"
        result += f"- Carbohydrates: {max(0, goals.carb_target - totals.carbohydrates):.0f}g\n"
        result += f"- Fat: {max(0, goals.fat_target - totals.fat):.0f}g\n"

    return result
    

# === Tool Context ===
def get_user_profile_context(state: MealPlannerState) -> str:
    """Get user profile context."""
    user_profile = state.user_profile
    context = ""
    if user_profile.dietary_restrictions:
        context += get_dietary_restrictions_context(state)
    if user_profile.preferred_cuisines:
        context += f"Preferred cuisines: {', '.join(user_profile.preferred_cuisines)}\n"
    if user_profile.cooking_time_preference:
        context += f"Cooking time preference: {user_profile.cooking_time_preference}\n"
    if user_profile.health_goals:
        context += f"Health goals: {', '.join(user_profile.health_goals)}\n"
    return context


def get_dietary_restrictions_context(state: MealPlannerState) -> str:
    """Add dietary restrictions warning to context."""
    context = ""
    if dietary_restrictions := state.user_profile.dietary_restrictions:
        context += f"Dietary restrictions: {', '.join(dietary_restrictions)}\n"
        context += f"⚠️ CRITICAL: You MUST NOT include ANY foods that violate these restrictions!\n"
        context += "This is extremely important - double-check every single item.\n\n"
    return context