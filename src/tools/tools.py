from typing import Annotated, Optional, List, Literal, Union

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from src.models import MealPlannerState, NutritionGoals

# Initialize LLM for generation tools
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)


# === USER PROFILE TOOLS ===

@tool
def update_user_profile(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    dietary_restrictions: Optional[List[str]] = None,
    preferred_cuisines: Optional[List[str]] = None,
    cooking_time_preference: Optional[str] = None,
    health_goals: Optional[List[str]] = None
) -> Command:
    """Update user's dietary preferences and restrictions.
    
    Updates only the provided fields, leaving others unchanged.
    This information affects all meal suggestions and planning.
    
    Parameters:
    - dietary_restrictions: List of restrictions like ['vegetarian', 'gluten-free', 'dairy-free']
    - preferred_cuisines: List of cuisine preferences like ['italian', 'mediterranean', 'asian']
    - cooking_time_preference: 'quick', 'moderate', or 'extensive'
    - health_goals: List of goals like ['weight loss', 'muscle gain', 'heart health']
    
    Examples:
    - update_user_profile(dietary_restrictions=['vegetarian', 'gluten-free'])
    - update_user_profile(preferred_cuisines=['mediterranean'], cooking_time_preference='quick')
    
    Use this early in conversations to establish preferences that guide all meal planning.
    """
    profile = state.user_profile
    new_profile = profile.model_copy()

    # Track what was updated
    updated_fields = []

    # Update only provided fields
    if dietary_restrictions is not None:
        new_profile.dietary_restrictions = dietary_restrictions
        updated_fields.append(f"dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'none'}")
    if preferred_cuisines is not None:
        new_profile.preferred_cuisines = preferred_cuisines
        updated_fields.append(f"preferred cuisines: {', '.join(preferred_cuisines) if preferred_cuisines else 'none'}")
    if cooking_time_preference is not None:
        new_profile.cooking_time_preference = cooking_time_preference
        updated_fields.append(f"cooking time preference: {cooking_time_preference}")
    if health_goals is not None:
        new_profile.health_goals = health_goals
        updated_fields.append(f"health goals: {', '.join(health_goals) if health_goals else 'none'}")


    # Create a descriptive message about what was updated
    if updated_fields:
        message = f"Successfully updated user profile - {'; '.join(updated_fields)}"
    else:
        message = "No changes made to user profile"

    return Command(
        update={
            "user_profile": new_profile,
            "messages": [
                ToolMessage(
                    content=message,
                    tool_call_id=tool_call_id
                )
            ]
        }
    )


# === NUTRITION TOOLS ===

@tool
def set_nutrition_goals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    daily_calories: Optional[int] = None,
    diet_type: Optional[Literal["balanced", "high-protein", "low-carb", "keto", "custom"]] = None,
    protein_percent: Optional[float] = None,
    carb_percent: Optional[float] = None,
    fat_percent: Optional[float] = None
) -> Command:
    """Set or update personalized daily nutrition goals with macro targets.
    
    This tool establishes or updates daily calorie and macronutrient targets. You can:
    - Set initial goals with calories and diet type
    - Update any field individually
    - Use custom macro percentages for personalized ratios
    
    Parameters:
    - daily_calories: Target daily calories (e.g., 2000, 1800, 2500)
    - diet_type: Diet approach that determines macro ratios:
      * "balanced" - 20% protein, 50% carbs, 30% fat (standard balanced diet)
      * "high-protein" - 30% protein, 40% carbs, 30% fat (muscle building/weight loss)
      * "low-carb" - 25% protein, 20% carbs, 55% fat (reduced carbohydrate)
      * "keto" - 20% protein, 5% carbs, 75% fat (ketogenic diet)
      * "custom" - Use with custom macro percentages
    - protein_percent: Custom protein percentage (0-1, e.g., 0.25 for 25%)
    - carb_percent: Custom carbohydrate percentage (0-1, e.g., 0.45 for 45%)
    - fat_percent: Custom fat percentage (0-1, e.g., 0.30 for 30%)
    
    Note: When providing custom percentages, all three must be specified and sum to 1.0
    
    Examples:
    - set_nutrition_goals(daily_calories=2000, diet_type="high-protein")
    - set_nutrition_goals(daily_calories=1800, diet_type="balanced")
    - set_nutrition_goals(daily_calories=2200, protein_percent=0.25, carb_percent=0.45, fat_percent=0.30)
    - set_nutrition_goals(diet_type="keto")  # Update diet type only
    - set_nutrition_goals(daily_calories=2500)  # Update calories only
    """
    # Get existing goals if any
    current_goals = state.nutrition_goals
    
    # Prepare data for creating/updating goals
    goal_data = {}
    
    # If we have existing goals, start with their values
    if current_goals:
        goal_data = {
            "daily_calories": current_goals.daily_calories,
            "diet_type": current_goals.diet_type,
            "protein_percent": current_goals.protein_percent,
            "carb_percent": current_goals.carb_percent,
            "fat_percent": current_goals.fat_percent
        }
    
    # Update with any provided values
    if daily_calories is not None:
        goal_data["daily_calories"] = daily_calories
    
    if diet_type is not None:
        goal_data["diet_type"] = diet_type
        # When diet_type changes, clear custom percentages unless it's "custom"
        if diet_type != "custom":
            goal_data.pop("protein_percent", None)
            goal_data.pop("carb_percent", None)
            goal_data.pop("fat_percent", None)
    
    # Handle custom percentages
    if protein_percent is not None or carb_percent is not None or fat_percent is not None:
        goal_data["protein_percent"] = protein_percent
        goal_data["carb_percent"] = carb_percent
        goal_data["fat_percent"] = fat_percent
    
    # Ensure we have daily_calories for new goals
    if "daily_calories" not in goal_data:
        return Command(
            messages=[
                ToolMessage(
                    content="Please provide daily_calories when setting nutrition goals for the first time",
                    tool_call_id=tool_call_id
                )
            ]
        )
    
    # Create or update the goals
    try:
        goals = NutritionGoals(**goal_data)
        
        # Build success message
        message = "Successfully updated nutrition goals:\n"
        message += f"- Daily calories: {goals.daily_calories}\n"
        message += f"- Diet type: {goals.diet_type}\n"
        message += f"- Macros: {goals.protein_percent*100:.0f}% protein, {goals.carb_percent*100:.0f}% carbs, {goals.fat_percent*100:.0f}% fat\n"
        message += f"- Targets: {goals.protein_target:.0f}g protein, {goals.carb_target:.0f}g carbs, {goals.fat_target:.0f}g fat"
        
        return Command(
            update={
                "nutrition_goals": goals,
                "messages": [
                    ToolMessage(
                        content=message,
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    except ValueError as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Error setting nutrition goals: {str(e)}",
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )

# === SMART SUGGESTION TOOLS ===
