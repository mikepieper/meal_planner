import json
from typing import Annotated, Optional, List, Dict, Any, Literal

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from src.models import (
    MealPlannerState, MealItem, NutritionInfo, NutritionGoals,
    MealSuggestion
)

# Initialize LLM for generation tools
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

# === CONSTANTS ===
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snacks"]
MealType = Literal["breakfast", "lunch", "dinner", "snacks"]


# === HELPER FUNCTIONS ===
def update_planning_phase(state: MealPlannerState, context) -> Any:
    """Update planning phase based on current state."""
    new_context = context.model_copy()
    
    if new_context.planning_phase == "gathering_info" and state.nutrition_goals:
        new_context.planning_phase = "building_meals"
    elif new_context.planning_phase == "setting_goals":
        new_context.planning_phase = "building_meals"
    elif new_context.planning_phase == "building_meals" and state.has_sufficient_nutrition:
        new_context.planning_phase = "optimizing"
    elif new_context.planning_phase == "optimizing" and state.has_sufficient_nutrition:
        new_context.planning_phase = "complete"
    
    # Special case for when meals already exist
    meals_with_items = sum(1 for meal in MEAL_TYPES if getattr(state, meal))
    if meals_with_items > 0 and new_context.planning_phase == "setting_goals":
        new_context.planning_phase = "building_meals"
        if meals_with_items >= 2:
            new_context.planning_phase = "optimizing"
    
    return new_context


def add_dietary_restrictions_context(context: str, restrictions: List[str], severity: str = "MUST NOT") -> str:
    """Add dietary restrictions warning to context."""
    if restrictions:
        context += f"Dietary restrictions: {', '.join(restrictions)}\n"
        context += f"⚠️ CRITICAL: You {severity} include ANY foods that violate these restrictions!\n"
        context += "This is extremely important - double-check every single item.\n\n"
    return context


def parse_json_from_llm_response(response_content: str) -> Optional[dict]:
    """Extract and parse JSON from LLM response."""
    try:
        import re
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def create_meal_items(items_data: List[Dict[str, Any]]) -> List[MealItem]:
    """Convert JSON item data to MealItem objects."""
    items = []
    for item_data in items_data:
        items.append(MealItem(
            food=item_data["food"],
            amount=item_data["amount"],
            unit=item_data.get("unit", "serving")
        ))
    return items

# === NUTRITION HELPERS ===

# === MEAL MANAGEMENT TOOLS ===

@tool
def add_meal_item(
    meal_type: MealType,
    food: str,
    amount: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    unit: str = "serving"
) -> Command:
    """Add a food item to a specific meal."""
    new_item = MealItem(food=food, amount=amount, unit=unit)
    updated_meal = state[meal_type] + [new_item]

    # Update phase if needed - use a temporary state to check phase transitions
    temp_state = state.model_copy()
    setattr(temp_state, meal_type, updated_meal)
    
    new_context = update_planning_phase(temp_state, state["conversation_context"])

    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type,
            "conversation_context": new_context
        }
    )


@tool
def add_multiple_items(
    meal_type: MealType,
    items: List[Dict[str, str]],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Add multiple items to a meal in one operation. Each item should have 'food', 'amount', and optionally 'unit'."""
    # Use helper to create items
    new_items = create_meal_items(items)

    # Add all items to the meal
    updated_meal = state[meal_type] + new_items

    # Update planning phase if appropriate - use temporary state to check transitions
    temp_state = state.model_copy()
    setattr(temp_state, meal_type, updated_meal)
    
    new_context = update_planning_phase(temp_state, state["conversation_context"])

    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type,
            "conversation_context": new_context
        }
    )


@tool
def add_meal_from_suggestion(
    meal_type: MealType,
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

    # Add all items from the suggestion
    updated_meal = state[meal_type] + suggestion.items

    # Update planning phase if we're starting to build meals - use temporary state to check transitions
    temp_state = state.model_copy()
    setattr(temp_state, meal_type, updated_meal)
    
    new_context = update_planning_phase(temp_state, context)

    return Command(
        update={
            meal_type: updated_meal,
            "current_meal": meal_type,
            "conversation_context": new_context
        }
    )


@tool
def remove_meal_item(
    meal_type: MealType,
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

    for meal_type in MEAL_TYPES:
        items = state[meal_type]
        if items:
            result += f"**{meal_type.capitalize()}:**\n"
            for item in items:
                result += f"  - {item.amount} {item.unit} of {item.food}\n"
            result += "\n"
        else:
            result += f"**{meal_type.capitalize()}:** Empty\n\n"

    # Add current nutrition totals
    result += f"\n**Current Daily Totals:**\n- {state.nutrition_summary}\n"

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


@tool
def clear_meal(
    meal_type: MealType,
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
    updates = {"current_meal": "breakfast"}
    for meal_type in MEAL_TYPES:
        updates[meal_type] = []
    
    return Command(update=updates)


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

    # Update conversation phase - always progress from gathering_info to setting_goals
    context = state["conversation_context"]
    new_context = context.model_copy()

    if new_context.planning_phase == "gathering_info":
        new_context.planning_phase = "setting_goals"

    # If we already have meals, might need to jump to building_meals or optimizing
    meals_with_items = sum(1 for meal in ["breakfast", "lunch", "dinner"] if state.get(meal))
    if meals_with_items > 0:
        new_context.planning_phase = "building_meals"
        if meals_with_items >= 2:
            new_context.planning_phase = "optimizing"

    return Command(
        update={
            "nutrition_goals": goals,
            "conversation_context": new_context
        }
    )


@tool
def analyze_meal_nutrition(
    meal_type: MealType,
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


# === SMART SUGGESTION TOOLS ===

@tool
def suggest_foods_to_meet_goals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """Suggest foods that would help meet remaining nutrition goals."""
    if not state.nutrition_goals:
        return "Please set nutrition goals first to get targeted suggestions."

    restrictions = state.user_profile.dietary_restrictions
    
    # Use the standardized nutrition context
    nutrition_context = state.nutrition_context_for_prompts
    
    prompt = f"""{nutrition_context}

{add_dietary_restrictions_context("", restrictions, "ONLY suggest foods that are FULLY compliant with")}Provide 5-7 specific food suggestions with portions that would help fill the remaining nutrition gaps.
Focus on foods that are high in the most needed nutrients."""

    response = llm.invoke(prompt)
    return f"**Foods to help meet your remaining goals:**\n\n{response.content}"


# === PLANNING TOOLS ===

@tool
def generate_remaining_meals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    meal_types: Optional[List[MealType]] = None
) -> Command:
    """Generate meals only for empty meal slots, preserving existing meals."""
    user_profile = state.user_profile
    nutrition_goals = state.nutrition_goals

    # Determine which meals to generate
    if meal_types is None:
        # Auto-detect empty meals
        meal_types = []
        for meal in MEAL_TYPES:
            if not getattr(state, meal):
                meal_types.append(meal)

    if not meal_types:
        return Command(update={})  # All meals already have items

    context = f"Generate meals ONLY for these empty slots: {', '.join(meal_types)}\n\n"
    
    # Add nutrition context if goals are set
    if state.nutrition_context_for_prompts:
        context += state.nutrition_context_for_prompts + "\n\n"

    context = add_dietary_restrictions_context(context, user_profile.dietary_restrictions)
    if user_profile.preferred_cuisines:
        context += f"Preferred cuisines: {', '.join(user_profile.preferred_cuisines)}\n"

    prompt = f"""{context}

Generate meals with specific portions. Format as JSON:
{{"""

    for meal in meal_types:
        prompt += f"""
    "{meal}": [
        {{"food": "item1", "amount": "1", "unit": "cup"}},
        {{"food": "item2", "amount": "2", "unit": "oz"}}
    ],"""

    prompt = prompt.rstrip(",") + "\n}"

    response = llm.invoke(prompt)

    # Update conversation phase
    conv_context = state["conversation_context"]
    new_context = conv_context.model_copy()
    new_context.planning_phase = "optimizing"

    meal_data = parse_json_from_llm_response(response.content)
    if meal_data:
        # Start with current state
        temp_state = dict(state)

                # Only update the requested meals
        for meal_type in meal_types:
            if meal_type in meal_data:
                items = create_meal_items(meal_data[meal_type])
                temp_state[meal_type] = items

        # Create a full temp state for checking phase transitions
        full_temp_state = state.model_copy()
        for meal_type in meal_types:
            if meal_type in temp_state:
                setattr(full_temp_state, meal_type, temp_state[meal_type])

        # Check if we should be in complete phase
        if state.has_sufficient_nutrition:
            new_context.planning_phase = "complete"

        # Build updates - only for meals we generated
        updates = {
            "conversation_context": new_context
        }
        for meal_type in meal_types:
            if meal_type in temp_state:
                updates[meal_type] = temp_state[meal_type]

        return Command(update=updates)

    # Fallback
    return Command(update={"conversation_context": new_context})


@tool
def generate_meal_plan(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    preferences: Optional[Dict[str, Any]] = None,
    preserve_existing: bool = True
) -> Command:
    """Generate a complete daily meal plan. By default, preserves existing meals unless preserve_existing=False."""

    # If preserve_existing and we have some meals, use generate_remaining_meals
    if preserve_existing:
        has_meals = any(getattr(state, meal) for meal in MEAL_TYPES)
        if has_meals:
            # Delegate to generate_remaining_meals
            return generate_remaining_meals(state, tool_call_id)

    # Otherwise, generate full plan (original behavior)
    user_profile = state.user_profile
    nutrition_goals = state.nutrition_goals

    context = "Generate a complete daily meal plan with specific portions.\n\n"

    if not preserve_existing:
        context += "NOTE: This will replace any existing meals.\n\n"

    if nutrition_goals:
        context += f"Nutrition targets: {nutrition_goals.daily_calories} calories, "
        context += f"{nutrition_goals.protein_target:.0f}g protein, "
        context += f"{nutrition_goals.carb_target:.0f}g carbs, {nutrition_goals.fat_target:.0f}g fat\n"
        context += f"Diet type: {nutrition_goals.diet_type}\n"

    if user_profile:
        context = add_dietary_restrictions_context(context, user_profile.dietary_restrictions)
        if user_profile.preferred_cuisines:
            context += f"Preferred cuisines: {', '.join(user_profile.preferred_cuisines)}\n"
        if user_profile.cooking_time_preference:
            context += f"Cooking time preference: {user_profile.cooking_time_preference}\n"

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

    # Update conversation phase - generating a full plan means we're optimizing
    conv_context = state["conversation_context"]
    new_context = conv_context.model_copy()
    new_context.planning_phase = "optimizing"

    meal_data = parse_json_from_llm_response(response.content)
    if meal_data:
        # Convert to MealItem objects and validate against restrictions
        temp_state = {"user_profile": user_profile}
        all_items = []

        for meal_type in MEAL_TYPES:
            if meal_type in meal_data:
                items = create_meal_items(meal_data[meal_type])
                temp_state[meal_type] = items
                for item in items:
                    all_items.append(f"{item.amount} {item.unit} of {item.food}")
            else:
                temp_state[meal_type] = []

            # Create full temp state for checking phase transitions
            full_temp_state = state.model_copy()
            for meal_type in MEAL_TYPES:
                setattr(full_temp_state, meal_type, temp_state[meal_type])

            # Check if we should be in complete phase
            if state.has_sufficient_nutrition:
                new_context.planning_phase = "complete"

            updates = {
                "conversation_context": new_context
            }
            for meal_type in MEAL_TYPES:
                updates[meal_type] = temp_state[meal_type]

            return Command(update=updates)

    # Fallback: clear meals and return empty state
    updates = {"conversation_context": new_context}
    for meal_type in MEAL_TYPES:
        updates[meal_type] = []
    
    return Command(update=updates)


@tool
def suggest_meal(
    meal_type: MealType,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    preferences: Optional[Dict[str, Any]] = None
) -> Command:
    """Suggest options for a specific meal based on preferences and remaining nutrition needs."""
    user_profile = state.user_profile
    
    context = f"Suggest 3 different {meal_type} options.\n\n"

    # Add nutrition context if available
    if state.nutrition_context_for_prompts:
        context += state.nutrition_context_for_prompts + "\n\n"
        
        # Add meal-specific guidance based on remaining nutrition
        if state.nutrition_goals:
            totals = state.current_totals
            goals = state.nutrition_goals
            protein_remaining = max(0, goals.protein_target - totals.protein)
            
            if protein_remaining > 50:
                context += "PRIORITIZE HIGH PROTEIN OPTIONS\n\n"

    context = add_dietary_restrictions_context(context, user_profile.dietary_restrictions, "Only suggest foods that STRICTLY comply with")

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

    suggestions_data = parse_json_from_llm_response(response.content)
    if suggestions_data:
        # Convert to MealSuggestion objects and save in context
        new_context.last_suggestions[meal_type] = {}

        for key, data in suggestions_data.items():
            if key.startswith("option_"):
                # Convert each item in suggestion using helper
                items = create_meal_items(data.get("items", []))

                if items:  # Save suggestion if it has items
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
    else:
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
    for meal_type in MEAL_TYPES:
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
    user_profile = state.user_profile

    context = f"Provide meal ideas based on: {criteria}\n\n"
    context = add_dietary_restrictions_context(context, user_profile.dietary_restrictions, "Only suggest meals that COMPLETELY comply with")

    prompt = f"""{context}

Provide 5 meal ideas that match the criteria.
Include a brief description of each meal and why it fits the criteria."""

    response = llm.invoke(prompt)
    return f"Meal ideas for '{criteria}':\n\n{response.content}"
