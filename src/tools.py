import json

from langgraph.prebuilt import InjectedState
from typing import Annotated, Optional, List, Dict, Any, Literal
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from src.models import MealPlannerState, MealItem, NutritionInfo, NutritionGoals

# Initialize LLM for generation tools
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

# === MEAL MANAGEMENT TOOLS ===

@tool
def add_meal_item(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    food: str,
    amount: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    unit: str = "serving"
) -> Command:
    """Add a food item to a specific meal."""
    new_item = MealItem(food=food, amount=amount, unit=unit)
    
    # Create a new list with the item added (immutable update)
    updated_meal = state[meal_type] + [new_item]
    
    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type
        },
        # The message will be automatically added to the messages list
    )


@tool
def remove_meal_item(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    food: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Remove a food item from a specific meal."""
    meal_list = state[meal_type]
    
    # Find and remove the item (immutable update)
    updated_meal = []
    found = False
    for item in meal_list:
        if item.food.lower() == food.lower() and not found:
            found = True  # Skip this item (remove it)
        else:
            updated_meal.append(item)
    
    if not found:
        # Return command with no updates but a message
        return Command(update={})
    
    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type
        }
    )


@tool
def view_current_meals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """View all meals currently in the meal plan."""
    result = "Current Meal Plan:\n\n"
    
    for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
        items = state[meal_type]
        if items:
            result += f"**{meal_type.capitalize()}:**\n"
            for item in items:
                result += f"  - {item.amount} {item.unit} of {item.food}\n"
            result += "\n"
        else:
            result += f"**{meal_type.capitalize()}:** Empty\n\n"
    
    return result.strip()


@tool
def clear_meal(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Clear all items from a specific meal."""
    return Command(
        update={
            meal_type: [],
            "current_meal": meal_type
        }
    )


@tool
def clear_all_meals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Clear the entire meal plan."""
    return Command(
        update={
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "snacks": [],
            "current_meal": "breakfast"
        }
    )


# === NUTRITION TOOLS ===

@tool
def set_nutrition_goals(
    daily_calories: int,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    diet_type: Literal["balanced", "high-protein", "low-carb", "keto", "vegetarian", "vegan"] = "balanced"
) -> Command:
    """Set personalized daily nutrition goals."""
    # Calculate macro targets based on diet type
    if diet_type == "high-protein":
        protein_percent = 0.30
        carb_percent = 0.40
        fat_percent = 0.30
    elif diet_type == "low-carb":
        protein_percent = 0.25
        carb_percent = 0.20
        fat_percent = 0.55
    elif diet_type == "keto":
        protein_percent = 0.20
        carb_percent = 0.05
        fat_percent = 0.75
    else:  # balanced, vegetarian, vegan
        protein_percent = 0.20
        carb_percent = 0.50
        fat_percent = 0.30
    
    goals = NutritionGoals(
        daily_calories=daily_calories,
        diet_type=diet_type,
        protein_target=daily_calories * protein_percent / 4,  # 4 cal/g protein
        carb_target=daily_calories * carb_percent / 4,       # 4 cal/g carbs
        fat_target=daily_calories * fat_percent / 9          # 9 cal/g fat
    )
    
    return Command(
        update={
            "nutrition_goals": goals
        }
    )


@tool
def analyze_meal_nutrition(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """Analyze nutritional content of a specific meal. Uses estimates for common foods."""
    items = state[meal_type]
    if not items:
        return f"{meal_type.capitalize()} is empty."
    
    # This would normally use a food database - using estimates for now
    prompt = f"""Estimate the nutritional content for this {meal_type}:
{chr(10).join([f"- {item.amount} {item.unit} of {item.food}" for item in items])}

Provide totals in this format:
Calories: X
Protein: Xg
Carbohydrates: Xg
Fat: Xg"""
    
    response = llm.invoke(prompt)
    return f"**{meal_type.capitalize()} Nutrition:**\n{response.content}"


@tool
def analyze_daily_nutrition(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """Analyze total daily nutritional content and compare to goals."""
    all_items = []
    for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
        for item in state[meal_type]:
            all_items.append(f"{item.amount} {item.unit} of {item.food}")
    
    if not all_items:
        return "No meals in the current plan to analyze."
    
    prompt = f"""Estimate the total daily nutritional content for these meals:
{chr(10).join(all_items)}

Provide totals and analysis in this format:
Daily Totals:
- Calories: X
- Protein: Xg  
- Carbohydrates: Xg
- Fat: Xg

{f"Compare to goals - Calories: {state['nutrition_goals'].daily_calories}, Protein: {state['nutrition_goals'].protein_target:.0f}g, Carbs: {state['nutrition_goals'].carb_target:.0f}g, Fat: {state['nutrition_goals'].fat_target:.0f}g" if state.get('nutrition_goals') else "No nutrition goals set."}
"""
    
    response = llm.invoke(prompt)
    return response.content


# === PLANNING TOOLS ===

@tool
def generate_meal_plan(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    preferences: Optional[Dict[str, Any]] = None
) -> Command:
    """Generate a complete daily meal plan based on preferences and goals."""
    user_profile = state.get("user_profile", {})
    nutrition_goals = state.get("nutrition_goals")
    
    context = "Generate a complete daily meal plan with specific portions.\n\n"
    
    if nutrition_goals:
        context += f"Nutrition targets: {nutrition_goals.daily_calories} calories, "
        context += f"{nutrition_goals.protein_target:.0f}g protein, "
        context += f"{nutrition_goals.carb_target:.0f}g carbs, {nutrition_goals.fat_target:.0f}g fat\n"
        context += f"Diet type: {nutrition_goals.diet_type}\n"
    
    if user_profile:
        if user_profile.dietary_restrictions:
            context += f"Dietary restrictions: {', '.join(user_profile.dietary_restrictions)}\n"
        if user_profile.preferred_cuisines:
            context += f"Preferred cuisines: {', '.join(user_profile.preferred_cuisines)}\n"
    
    if preferences:
        context += f"Additional preferences: {json.dumps(preferences)}\n"
    
    prompt = f"""{context}
    
Create a meal plan with:
- Breakfast (2-4 items)
- Lunch (3-5 items)
- Dinner (3-5 items)
- Snacks (1-3 items, optional)

For each meal, format as a JSON list of items:
{{
    "breakfast": [
        {{"food": "oatmeal", "amount": "1", "unit": "cup"}},
        {{"food": "blueberries", "amount": "1/2", "unit": "cup"}}
    ],
    "lunch": [...],
    "dinner": [...],
    "snacks": [...]
}}
"""
    
    response = llm.invoke(prompt)
    
    try:
        # Parse the LLM response to extract meal items
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            meal_data = json.loads(json_match.group())
            
            # Convert to MealItem objects
            updates = {}
            for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
                if meal_type in meal_data:
                    items = []
                    for item_data in meal_data[meal_type]:
                        items.append(MealItem(
                            food=item_data["food"],
                            amount=item_data["amount"],
                            unit=item_data.get("unit", "serving")
                        ))
                    updates[meal_type] = items
                else:
                    updates[meal_type] = []
            
            return Command(update=updates)
    except:
        # If parsing fails, clear meals and let the agent handle it conversationally
        pass
    
    # Fallback: clear meals and return empty state
    return Command(
        update={
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "snacks": []
        }
    )


@tool
def suggest_meal(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    preferences: Optional[Dict[str, Any]] = None
) -> str:
    """Suggest options for a specific meal based on preferences."""
    user_profile = state.get("user_profile", {})
    nutrition_goals = state.get("nutrition_goals")
    
    context = f"Suggest 3 different {meal_type} options.\n\n"
    
    if nutrition_goals:
        # Approximate per-meal targets
        meal_calories = nutrition_goals.daily_calories / 3 if meal_type in ["breakfast", "lunch", "dinner"] else nutrition_goals.daily_calories / 10
        context += f"Target approximately {meal_calories:.0f} calories\n"
        context += f"Diet type: {nutrition_goals.diet_type}\n"
    
    if user_profile and user_profile.dietary_restrictions:
        context += f"Dietary restrictions: {', '.join(user_profile.dietary_restrictions)}\n"
    
    if preferences:
        context += f"Additional preferences: {json.dumps(preferences)}\n"
    
    prompt = f"""{context}

Provide 3 {meal_type} suggestions with specific portions that would work well.
Format each option clearly with a name and list of ingredients with amounts."""
    
    response = llm.invoke(prompt)
    return f"{meal_type.capitalize()} suggestions:\n\n{response.content}"


# === UTILITY TOOLS ===

@tool  
def generate_shopping_list(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """Generate a shopping list from the current meal plan."""
    all_items = {}
    
    # Collect all items from all meals
    for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
        for item in state[meal_type]:
            key = item.food.lower()
            if key not in all_items:
                all_items[key] = []
            all_items[key].append(f"{item.amount} {item.unit}")
    
    if not all_items:
        return "No items in meal plan to create shopping list."
    
    # Build shopping list
    shopping_list = "Shopping List:\n\n"
    for food, amounts in sorted(all_items.items()):
        if len(amounts) == 1:
            shopping_list += f"- {food.capitalize()}: {amounts[0]}\n"
        else:
            shopping_list += f"- {food.capitalize()}: {', '.join(amounts)} (total from multiple meals)\n"
    
    return shopping_list


@tool
def get_meal_ideas(
    criteria: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """Get meal ideas based on specific criteria like ingredients, cuisine, or cooking time."""
    user_profile = state.get("user_profile", {})
    
    context = f"Provide meal ideas based on: {criteria}\n\n"
    
    if user_profile and user_profile.dietary_restrictions:
        context += f"Keep in mind dietary restrictions: {', '.join(user_profile.dietary_restrictions)}\n"
    
    prompt = f"""{context}

Provide 5 meal ideas that match the criteria.
Include a brief description of each meal and why it fits the criteria."""
    
    response = llm.invoke(prompt)
    return f"Meal ideas for '{criteria}':\n\n{response.content}"


