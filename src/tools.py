import json

from langgraph.prebuilt import InjectedState
from typing import Annotated, Optional, List, Dict, Any, Literal
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from src.models import MealPlannerState, MealItem, NutritionInfo, NutritionGoals, MealSuggestion, ConversationContext, UserProfile

# Initialize LLM for generation tools
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

# === NUTRITION HELPERS ===

def calculate_meal_totals(state: MealPlannerState) -> NutritionInfo:
    """Calculate total nutrition from all meals in state."""
    all_items = []
    for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
        for item in state[meal_type]:
            all_items.append(f"{item.amount} {item.unit} of {item.food}")
    
    if not all_items:
        return NutritionInfo(calories=0, protein=0, carbohydrates=0, fat=0)
    
    # Use LLM to estimate totals
    prompt = f"""Estimate the total nutritional content for all these items:
{chr(10).join(all_items)}

Respond ONLY with a JSON object in this exact format:
{{"calories": 1500, "protein": 75, "carbohydrates": 180, "fat": 50}}"""
    
    try:
        response = llm.invoke(prompt)
        data = json.loads(response.content)
        return NutritionInfo(
            calories=data["calories"],
            protein=data["protein"],
            carbohydrates=data["carbohydrates"],
            fat=data["fat"]
        )
    except:
        return NutritionInfo(calories=0, protein=0, carbohydrates=0, fat=0)


def is_food_allowed(food: str, dietary_restrictions: List[str]) -> bool:
    """Check if a food item is allowed based on dietary restrictions."""
    if not dietary_restrictions:
        return True
    
    # Use LLM for intelligent restriction checking
    prompt = f"""Given these dietary restrictions: {', '.join(dietary_restrictions)}
Is this food allowed: {food}?

Consider:
- Vegetarian/vegan restrictions
- Allergies (gluten, nuts, dairy, etc.)
- Religious dietary laws
- Health conditions

Respond with only "YES" or "NO"."""
    
    response = llm.invoke(prompt)
    return response.content.strip().upper() == "YES"


def get_restriction_violation(food: str, dietary_restrictions: List[str]) -> Optional[str]:
    """Get specific restriction violated by a food item."""
    if not dietary_restrictions:
        return None
    
    prompt = f"""Given these dietary restrictions: {', '.join(dietary_restrictions)}
Which restriction (if any) does this food violate: {food}?

If no violation, respond with "NONE".
If violation, respond with just the restriction name (e.g., "vegetarian", "gluten-free")."""
    
    response = llm.invoke(prompt)
    violation = response.content.strip()
    return None if violation.upper() == "NONE" else violation


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
    # Check dietary restrictions
    restrictions = state["user_profile"].dietary_restrictions
    if not is_food_allowed(food, restrictions):
        violation = get_restriction_violation(food, restrictions)
        return Command(update={})  # Agent will handle the message
    
    new_item = MealItem(food=food, amount=amount, unit=unit)
    updated_meal = state[meal_type] + [new_item]
    
    # Calculate new totals
    temp_state = dict(state)
    temp_state[meal_type] = updated_meal
    new_totals = calculate_meal_totals(temp_state)
    
    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type,
            "current_totals": new_totals
        }
    )


@tool
def add_multiple_items(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    items: List[Dict[str, str]],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Add multiple items to a meal in one operation. Each item should have 'food', 'amount', and optionally 'unit'."""
    restrictions = state["user_profile"].dietary_restrictions
    new_items = []
    
    # Validate all items first
    for item_data in items:
        food = item_data["food"]
        if not is_food_allowed(food, restrictions):
            violation = get_restriction_violation(food, restrictions)
            # Skip restricted items
            continue
        
        new_items.append(MealItem(
            food=food,
            amount=item_data["amount"],
            unit=item_data.get("unit", "serving")
        ))
    
    if not new_items:
        return Command(update={})  # All items were restricted
    
    # Add all allowed items to the meal
    updated_meal = state[meal_type] + new_items
    
    # Calculate new totals
    temp_state = dict(state)
    temp_state[meal_type] = updated_meal
    new_totals = calculate_meal_totals(temp_state)
    
    # Update planning phase if appropriate
    context = state["conversation_context"]
    new_context = context.model_copy()
    if new_context.planning_phase == "setting_goals":
        new_context.planning_phase = "building_meals"
    
    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type,
            "conversation_context": new_context,
            "current_totals": new_totals
        }
    )


@tool
def add_meal_from_suggestion(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    suggestion_key: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Add a complete suggested meal using its key (e.g., 'option_1')."""
    context = state["conversation_context"]
    
    # Get the suggestion from conversation context
    if meal_type not in context.last_suggestions:
        return Command(update={})  # No suggestions for this meal type
    
    if suggestion_key not in context.last_suggestions[meal_type]:
        return Command(update={})  # Invalid suggestion key
    
    suggestion = context.last_suggestions[meal_type][suggestion_key]
    
    # Validate all items (suggestions should already be validated, but double-check)
    restrictions = state["user_profile"].dietary_restrictions
    allowed_items = []
    for item in suggestion.items:
        if is_food_allowed(item.food, restrictions):
            allowed_items.append(item)
    
    if not allowed_items:
        return Command(update={})
    
    # Add all items from the suggestion
    updated_meal = state[meal_type] + allowed_items
    
    # Calculate new totals
    temp_state = dict(state)
    temp_state[meal_type] = updated_meal
    new_totals = calculate_meal_totals(temp_state)
    
    # Update planning phase if we're starting to build meals
    new_context = context.model_copy()
    if new_context.planning_phase == "setting_goals":
        new_context.planning_phase = "building_meals"
    
    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type,
            "conversation_context": new_context,
            "current_totals": new_totals
        }
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
    
    # Calculate new totals
    temp_state = dict(state)
    temp_state[meal_type] = updated_meal
    new_totals = calculate_meal_totals(temp_state)
    
    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type,
            "current_totals": new_totals
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
    
    # Add current nutrition totals if available
    if state.get("current_totals"):
        totals = state["current_totals"]
        result += "\n**Current Daily Totals:**\n"
        result += f"- Calories: {totals.calories:.0f}\n"
        result += f"- Protein: {totals.protein:.0f}g\n"
        result += f"- Carbohydrates: {totals.carbohydrates:.0f}g\n"
        result += f"- Fat: {totals.fat:.0f}g\n"
        
        # Compare to goals if set
        if state.get("nutrition_goals"):
            goals = state["nutrition_goals"]
            result += f"\n**Progress to Goals:**\n"
            result += f"- Calories: {totals.calories:.0f} / {goals.daily_calories} ({(totals.calories/goals.daily_calories*100):.0f}%)\n"
            result += f"- Protein: {totals.protein:.0f}g / {goals.protein_target:.0f}g ({(totals.protein/goals.protein_target*100):.0f}%)\n"
    
    return result.strip()


@tool
def clear_meal(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Clear all items from a specific meal."""
    # Calculate new totals
    temp_state = dict(state)
    temp_state[meal_type] = []
    new_totals = calculate_meal_totals(temp_state)
    
    return Command(
        update={
            meal_type: [],
            "current_meal": meal_type,
            "current_totals": new_totals
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
            "current_meal": "breakfast",
            "current_totals": NutritionInfo(calories=0, protein=0, carbohydrates=0, fat=0)
        }
    )


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
    """Update user profile information. Only provided fields will be updated."""
    profile = state["user_profile"]
    new_profile = profile.model_copy()
    
    # Update only provided fields
    if dietary_restrictions is not None:
        new_profile.dietary_restrictions = dietary_restrictions
    if preferred_cuisines is not None:
        new_profile.preferred_cuisines = preferred_cuisines
    if cooking_time_preference is not None:
        new_profile.cooking_time_preference = cooking_time_preference
    if health_goals is not None:
        new_profile.health_goals = health_goals
    
    # Track preferences in conversation context
    context = state["conversation_context"]
    new_context = context.model_copy()
    
    if dietary_restrictions:
        new_context.mentioned_preferences["dietary_restrictions"] = dietary_restrictions
    if preferred_cuisines:
        new_context.mentioned_preferences["cuisines"] = preferred_cuisines
    if cooking_time_preference:
        new_context.mentioned_preferences["cooking_time"] = cooking_time_preference
    if health_goals:
        new_context.mentioned_preferences["health_goals"] = health_goals
    
    return Command(
        update={
            "user_profile": new_profile,
            "conversation_context": new_context
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
    
    # Update conversation phase
    context = state["conversation_context"]
    new_context = context.model_copy()
    new_context.planning_phase = "setting_goals"
    
    return Command(
        update={
            "nutrition_goals": goals,
            "conversation_context": new_context
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
    if state.get("current_totals"):
        totals = state["current_totals"]
        result = "**Daily Nutrition Analysis:**\n\n"
        result += f"**Current Totals:**\n"
        result += f"- Calories: {totals.calories:.0f}\n"
        result += f"- Protein: {totals.protein:.0f}g\n"
        result += f"- Carbohydrates: {totals.carbohydrates:.0f}g\n"
        result += f"- Fat: {totals.fat:.0f}g\n"
        
        if state.get("nutrition_goals"):
            goals = state["nutrition_goals"]
            result += f"\n**Goals:**\n"
            result += f"- Calories: {goals.daily_calories}\n"
            result += f"- Protein: {goals.protein_target:.0f}g\n"
            result += f"- Carbohydrates: {goals.carb_target:.0f}g\n"
            result += f"- Fat: {goals.fat_target:.0f}g\n"
            
            result += f"\n**Progress:**\n"
            result += f"- Calories: {(totals.calories/goals.daily_calories*100):.0f}% of goal\n"
            result += f"- Protein: {(totals.protein/goals.protein_target*100):.0f}% of goal\n"
            result += f"- Carbohydrates: {(totals.carbohydrates/goals.carb_target*100):.0f}% of goal\n"
            result += f"- Fat: {(totals.fat/goals.fat_target*100):.0f}% of goal\n"
            
            # Calculate remaining needs
            result += f"\n**Remaining for the day:**\n"
            result += f"- Calories: {max(0, goals.daily_calories - totals.calories):.0f}\n"
            result += f"- Protein: {max(0, goals.protein_target - totals.protein):.0f}g\n"
            result += f"- Carbohydrates: {max(0, goals.carb_target - totals.carbohydrates):.0f}g\n"
            result += f"- Fat: {max(0, goals.fat_target - totals.fat):.0f}g\n"
        
        return result
    else:
        return "No meals in the current plan to analyze."


# === SMART SUGGESTION TOOLS ===

@tool
def suggest_foods_to_meet_goals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """Suggest foods that would help meet remaining nutrition goals."""
    if not state.get("nutrition_goals") or not state.get("current_totals"):
        return "Please set nutrition goals first to get targeted suggestions."
    
    goals = state["nutrition_goals"]
    totals = state["current_totals"]
    restrictions = state["user_profile"].dietary_restrictions
    
    # Calculate what's needed
    calories_needed = max(0, goals.daily_calories - totals.calories)
    protein_needed = max(0, goals.protein_target - totals.protein)
    carbs_needed = max(0, goals.carb_target - totals.carbohydrates)
    fat_needed = max(0, goals.fat_target - totals.fat)
    
    prompt = f"""Suggest foods to help meet these remaining nutrition needs:
- Calories: {calories_needed:.0f}
- Protein: {protein_needed:.0f}g
- Carbohydrates: {carbs_needed:.0f}g
- Fat: {fat_needed:.0f}g

Dietary restrictions: {', '.join(restrictions) if restrictions else 'None'}
Diet type: {goals.diet_type}

Provide 5-7 specific food suggestions with portions that would help fill these gaps.
Focus on foods that are high in the most needed nutrients."""
    
    response = llm.invoke(prompt)
    return f"**Foods to help meet your remaining goals:**\n\n{response.content}"


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
            context += "IMPORTANT: Do not include any foods that violate these restrictions!\n"
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
    
    # Update conversation phase
    conv_context = state["conversation_context"]
    new_context = conv_context.model_copy()
    new_context.planning_phase = "building_meals"
    
    try:
        # Parse the LLM response to extract meal items
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            meal_data = json.loads(json_match.group())
            
            # Convert to MealItem objects and validate against restrictions
            temp_state = {"user_profile": user_profile}
            all_items = []
            
            for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
                if meal_type in meal_data:
                    items = []
                    for item_data in meal_data[meal_type]:
                        # Validate each item
                        if is_food_allowed(item_data["food"], user_profile.dietary_restrictions):
                            item = MealItem(
                                food=item_data["food"],
                                amount=item_data["amount"],
                                unit=item_data.get("unit", "serving")
                            )
                            items.append(item)
                            all_items.append(f"{item.amount} {item.unit} of {item.food}")
                    temp_state[meal_type] = items
                else:
                    temp_state[meal_type] = []
            
            # Calculate totals for the new meal plan
            new_totals = calculate_meal_totals(temp_state)
            
            updates = {
                "conversation_context": new_context,
                "current_totals": new_totals
            }
            for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
                updates[meal_type] = temp_state[meal_type]
            
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
            "snacks": [],
            "conversation_context": new_context,
            "current_totals": NutritionInfo(calories=0, protein=0, carbohydrates=0, fat=0)
        }
    )


@tool
def suggest_meal(
    meal_type: Literal["breakfast", "lunch", "dinner", "snacks"],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    preferences: Optional[Dict[str, Any]] = None
) -> Command:
    """Suggest options for a specific meal based on preferences and remaining nutrition needs."""
    user_profile = state.get("user_profile", {})
    nutrition_goals = state.get("nutrition_goals")
    current_totals = state.get("current_totals")
    
    context = f"Suggest 3 different {meal_type} options.\n\n"
    
    # Smart suggestions based on what's needed
    if nutrition_goals and current_totals:
        calories_remaining = nutrition_goals.daily_calories - current_totals.calories
        protein_remaining = nutrition_goals.protein_target - current_totals.protein
        
        # Estimate portion of daily calories for this meal
        if meal_type in ["breakfast", "lunch", "dinner"]:
            meal_calories = calories_remaining / 3
        else:  # snacks
            meal_calories = calories_remaining / 10
        
        context += f"Remaining nutrition needs:\n"
        context += f"- Calories: {calories_remaining:.0f} (target ~{meal_calories:.0f} for this meal)\n"
        context += f"- Protein: {protein_remaining:.0f}g\n"
        context += f"Diet type: {nutrition_goals.diet_type}\n\n"
        
        if protein_remaining > 50:
            context += "PRIORITIZE HIGH PROTEIN OPTIONS\n"
    elif nutrition_goals:
        # No current meals, use standard portions
        meal_calories = nutrition_goals.daily_calories / 3 if meal_type in ["breakfast", "lunch", "dinner"] else nutrition_goals.daily_calories / 10
        context += f"Target approximately {meal_calories:.0f} calories\n"
        context += f"Diet type: {nutrition_goals.diet_type}\n"
    
    if user_profile and user_profile.dietary_restrictions:
        context += f"Dietary restrictions: {', '.join(user_profile.dietary_restrictions)}\n"
        context += "IMPORTANT: Only suggest foods that comply with these restrictions!\n"
    
    if preferences:
        context += f"Additional preferences: {json.dumps(preferences)}\n"
    
    prompt = f"""{context}

Provide 3 {meal_type} suggestions in JSON format with specific portions:
{{
    "option_1": {{
        "name": "Meal Name",
        "description": "Brief description",
        "items": [
            {{"food": "item1", "amount": "1", "unit": "cup"}},
            {{"food": "item2", "amount": "2", "unit": "oz"}}
        ],
        "nutrition": {{
            "calories": 450,
            "protein": 25,
            "carbohydrates": 50,
            "fat": 15
        }}
    }},
    "option_2": {{...}},
    "option_3": {{...}}
}}"""
    
    response = llm.invoke(prompt)
    
    # Parse response and save suggestions in conversation context
    conv_context = state["conversation_context"]
    new_context = conv_context.model_copy()
    
    try:
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            suggestions_data = json.loads(json_match.group())
            
            # Convert to MealSuggestion objects and save in context
            new_context.last_suggestions[meal_type] = {}
            
            for key, data in suggestions_data.items():
                if key.startswith("option_"):
                    items = []
                    # Validate each item in suggestion
                    for item_data in data.get("items", []):
                        if is_food_allowed(item_data["food"], user_profile.dietary_restrictions):
                            items.append(MealItem(
                                food=item_data["food"],
                                amount=item_data["amount"],
                                unit=item_data.get("unit", "serving")
                            ))
                    
                    if items:  # Only save suggestion if it has valid items
                        nutrition = NutritionInfo(
                            calories=data["nutrition"]["calories"],
                            protein=data["nutrition"]["protein"],
                            carbohydrates=data["nutrition"]["carbohydrates"],
                            fat=data["nutrition"]["fat"]
                        )
                        
                        suggestion = MealSuggestion(
                            name=data["name"],
                            items=items,
                            nutrition=nutrition,
                            description=data.get("description", "")
                        )
                        
                        new_context.last_suggestions[meal_type][key] = suggestion
    except:
        # If parsing fails, still update context to clear old suggestions
        new_context.last_suggestions[meal_type] = {}
    
    # Return the conversation context update and the formatted response
    return Command(
        update={
            "conversation_context": new_context
        }
    )


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
        context += "Only suggest meals that comply with these restrictions!\n"
    
    prompt = f"""{context}

Provide 5 meal ideas that match the criteria.
Include a brief description of each meal and why it fits the criteria."""
    
    response = llm.invoke(prompt)
    return f"Meal ideas for '{criteria}':\n\n{response.content}"


