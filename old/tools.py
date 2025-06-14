import json
from typing import Annotated, Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command, ToolMessage

from src.models import (
    MealPlannerState, MealItem, NutritionInfo, NutritionGoals,
    MealSuggestion, MealPreferences, MealPlanResponse, MealSuggestionOptions
)
from src.tool_utils import (
    add_dietary_restrictions_context,
    update_planning_phase,
    update_meal_with_items
)
from src.constants import MEAL_TYPES, MealType

# Initialize LLM for generation tools
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)


# === MEAL MANAGEMENT TOOLS ===


@tool
def add_meal_from_suggestion(
    meal_type: MealType,
    suggestion_key: str,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Add a complete suggested meal from previously generated suggestions.
    
    Use this tool after calling suggest_meal to add one of the suggested options
    to the meal plan. The suggestion must exist from a recent suggest_meal call.
    
    Parameters:
    - meal_type: Must be one of 'breakfast', 'lunch', 'dinner', or 'snacks'
    - suggestion_key: Key for the suggestion, always one of 'option_1', 'option_2', or 'option_3'
    
    Example workflow:
    1. suggest_meal(meal_type="breakfast")  # Generates 3 options
    2. add_meal_from_suggestion(meal_type="breakfast", suggestion_key="option_2")  # Adds option 2
    
    This adds all items from the chosen suggestion to the specified meal.
    """
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
    """Set personalized daily nutrition goals with macro targets.
    
    This tool establishes daily calorie and macronutrient targets based on the specified diet type.
    It automatically calculates protein, carbohydrate, and fat targets based on the diet approach.
    
    Parameters:
    - daily_calories: Target daily calories (e.g., 2000, 1800, 2500)
    - diet_type: Diet approach that determines macro ratios:
      * "balanced" - 20% protein, 50% carbs, 30% fat (standard balanced diet)
      * "high-protein" - 30% protein, 40% carbs, 30% fat (muscle building/weight loss)
      * "low-carb" - 25% protein, 20% carbs, 55% fat (reduced carbohydrate)
      * "keto" - 20% protein, 5% carbs, 75% fat (ketogenic diet)
      * "vegetarian" - 20% protein, 50% carbs, 30% fat (plant-based with dairy/eggs)
      * "vegan" - 20% protein, 50% carbs, 30% fat (fully plant-based)
    
    Example:
    - set_nutrition_goals(daily_calories=2000, diet_type="high-protein")
    - set_nutrition_goals(daily_calories=1800, diet_type="balanced")
    """
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
    """Get detailed nutritional breakdown for a specific meal.
    
    Provides estimated nutritional content (calories, protein, carbs, fat) for
    all items in the specified meal using common food nutrition data.
    
    Parameters:
    - meal_type: Must be one of 'breakfast', 'lunch', 'dinner', or 'snacks'
    
    Examples:
    - analyze_meal_nutrition(meal_type="breakfast")
    - analyze_meal_nutrition(meal_type="lunch")
    
    Use this tool to:
    - Check if a meal meets nutritional requirements
    - Understand calorie/macro distribution within a meal
    - Identify meals that need nutritional adjustment
    
    Returns 'Empty' if the meal has no items.
    """
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
    """Suggest specific foods with portions to fill remaining nutrition gaps.
    
    Analyzes current nutrition totals vs. goals and recommends 5-7 specific foods
    that would help reach daily targets. Respects all dietary restrictions.
    
    This tool is most useful when:
    - Daily nutrition is partially complete but gaps remain
    - User wants targeted food recommendations rather than full meals
    - Fine-tuning nutrition to meet specific macro targets
    
    Requires nutrition goals to be set first. Returns suggestions prioritized
    by the largest remaining nutrition gaps (e.g., high-protein foods if protein is low).
    
    Use this instead of suggest_meal when you want individual food suggestions
    rather than complete meal options.
    """
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
    """Fill empty meal slots while preserving existing planned meals.
    
    Automatically detects which meals are empty and generates complete meals for them.
    This is the preferred way to complete a partial meal plan without overwriting progress.
    
    Parameters:
    - meal_types: Optional list to specify which meals to generate. If None, auto-detects empty meals.
                 Valid values: ['breakfast', 'lunch', 'dinner', 'snacks']
    
    Examples:
    - generate_remaining_meals()  # Fill all empty meals automatically
    - generate_remaining_meals(meal_types=['lunch', 'dinner'])  # Only generate lunch and dinner
    
    Use this tool when:
    - User has some meals planned but others are empty
    - You want to complete a meal plan without losing existing progress
    - Preserving user's manual meal choices is important
    
    Takes into account nutrition goals, dietary restrictions, and remaining daily needs.
    """
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

Generate meals with specific portions for the requested meal types: {', '.join(meal_types)}.
Provide realistic portion sizes for each food item."""

    # Create structured LLM for meal generation
    structured_llm = llm.with_structured_output(MealPlanResponse)
    meal_plan = structured_llm.invoke(prompt)

    # Update conversation phase
    conv_context = state["conversation_context"]
    new_context = conv_context.model_copy()
    new_context.planning_phase = "optimizing"

    # Build updates - only for meals we generated
    updates = {
        "conversation_context": new_context
    }
    
    # Only update the requested meals
    for meal_type in meal_types:
        if hasattr(meal_plan, meal_type):
            meal_items = getattr(meal_plan, meal_type)
            if meal_items:
                updates[meal_type] = meal_items

    # Check if we should be in complete phase
    if state.has_sufficient_nutrition:
        new_context.planning_phase = "complete"

    return Command(update=updates)


@tool
def generate_meal_plan(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    preferences: Optional[MealPreferences] = None,
    preserve_existing: bool = True
) -> Command:
    """Generate a complete daily meal plan with structured preferences.
    
    Creates a comprehensive meal plan for all meals (breakfast, lunch, dinner, snacks).
    By default, preserves existing meals and only fills empty slots.
    
    Parameters:
    - preferences: Optional MealPreferences object with structured preferences:
      * cuisine: Preferred cuisine type (e.g., 'italian', 'mediterranean', 'asian')
      * cooking_time: 'quick', 'moderate', or 'extensive'
      * meal_style: Style like 'light', 'hearty', 'comfort food', 'fresh'
      * ingredients_to_include: List of specific ingredients to include
      * ingredients_to_avoid: List of ingredients to avoid
    - preserve_existing: If True (default), keeps existing meals and only fills empty slots.
                        If False, replaces entire meal plan.
    
    Example usage:
    - generate_meal_plan()  # Fill empty meals with defaults
    - generate_meal_plan(preferences=MealPreferences(cuisine="mediterranean"), preserve_existing=False)
    """

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
        context += "Additional preferences:\n"
        if preferences.cuisine:
            context += f"- Cuisine: {preferences.cuisine}\n"
        if preferences.cooking_time:
            context += f"- Cooking time: {preferences.cooking_time}\n"
        if preferences.meal_style:
            context += f"- Meal style: {preferences.meal_style}\n"
        if preferences.ingredients_to_include:
            context += f"- Must include: {', '.join(preferences.ingredients_to_include)}\n"
        if preferences.ingredients_to_avoid:
            context += f"- Avoid: {', '.join(preferences.ingredients_to_avoid)}\n"
        context += "\n"

    prompt = f"""{context}

Create a complete meal plan with:
- Breakfast (2-4 items)
- Lunch (3-5 items)  
- Dinner (3-5 items)
- Snacks (1-3 items, optional)

Provide realistic portion sizes for each food item."""

    # Create structured LLM for meal generation
    structured_llm = llm.with_structured_output(MealPlanResponse)
    meal_plan = structured_llm.invoke(prompt)

    # Update conversation phase - generating a full plan means we're optimizing
    conv_context = state["conversation_context"]
    new_context = conv_context.model_copy()
    new_context.planning_phase = "optimizing"

    # Check if we should be in complete phase
    if state.has_sufficient_nutrition:
        new_context.planning_phase = "complete"

    # Build updates for all meal types
    updates = {
        "conversation_context": new_context,
        "breakfast": meal_plan.breakfast,
        "lunch": meal_plan.lunch,
        "dinner": meal_plan.dinner,
        "snacks": meal_plan.snacks
    }
    
    return Command(update=updates)


@tool
def suggest_meal(
    meal_type: MealType,
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    preferences: Optional[MealPreferences] = None
) -> Command:
    """Generate 3 meal suggestions for a specific meal type.
    
    This tool provides 3 different options for a meal, taking into account:
    - Current nutrition needs and remaining daily targets
    - User's dietary restrictions and preferences  
    - High protein prioritization if protein goals are not being met
    
    Parameters:
    - meal_type: Must be one of 'breakfast', 'lunch', 'dinner', or 'snacks'
    - preferences: Optional MealPreferences object with structured preferences:
      * cuisine: Preferred cuisine type (e.g., 'italian', 'mediterranean', 'asian')
      * cooking_time: 'quick', 'moderate', or 'extensive'  
      * meal_style: Style like 'light', 'hearty', 'comfort food', 'fresh'
      * ingredients_to_include: List of specific ingredients to include
      * ingredients_to_avoid: List of ingredients to avoid
    
    The suggestions will be saved and can be added using add_meal_from_suggestion tool
    with keys like 'option_1', 'option_2', 'option_3'.
    
    Example usage:
    - suggest_meal(meal_type="breakfast") 
    - suggest_meal(meal_type="lunch", preferences=MealPreferences(cuisine="mediterranean", cooking_time="quick"))
    """
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
        context += "Additional preferences:\n"
        if preferences.cuisine:
            context += f"- Cuisine: {preferences.cuisine}\n"
        if preferences.cooking_time:
            context += f"- Cooking time: {preferences.cooking_time}\n"
        if preferences.meal_style:
            context += f"- Meal style: {preferences.meal_style}\n"
        if preferences.ingredients_to_include:
            context += f"- Must include: {', '.join(preferences.ingredients_to_include)}\n"
        if preferences.ingredients_to_avoid:
            context += f"- Avoid: {', '.join(preferences.ingredients_to_avoid)}\n"
        context += "\n"

    prompt = f"""{context}

Provide 3 different {meal_type} suggestions with specific portions and nutritional information."""

    # Create structured LLM for meal suggestions
    structured_llm = llm.with_structured_output(MealSuggestionOptions)
    suggestions = structured_llm.invoke(prompt)

    # Parse response and save suggestions in conversation context
    conv_context = state["conversation_context"]
    new_context = conv_context.model_copy()

    # Save the structured suggestions directly
    new_context.last_suggestions[meal_type] = {
        "option_1": suggestions.option_1,
        "option_2": suggestions.option_2,
        "option_3": suggestions.option_3
    }

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
    """Generate meal ideas based on specific criteria or constraints.
    
    Provides 5 meal ideas that match the given criteria while respecting
    all dietary restrictions. This is for inspiration and brainstorming.
    
    Parameters:
    - criteria: Specific requirements or preferences as a string
    
    Example criteria:
    - "using chicken and vegetables"
    - "quick 15-minute meals"
    - "high protein breakfast options"  
    - "Mediterranean cuisine"
    - "meals with leftover rice"
    - "low-carb dinner ideas"
    - "vegetarian lunch options"
    
    Use this tool when:
    - User needs inspiration for meal types
    - Looking for meals with specific ingredients
    - Exploring cuisine types or cooking methods
    - User asks "what can I make with..."
    
    Unlike suggest_meal, this provides general ideas rather than complete meal plans.
    """
    user_profile = state.user_profile

    context = f"Provide meal ideas based on: {criteria}\n\n"
    context = add_dietary_restrictions_context(context, user_profile.dietary_restrictions, "Only suggest meals that COMPLETELY comply with")

    prompt = f"""{context}

Provide 5 meal ideas that match the criteria.
Include a brief description of each meal and why it fits the criteria."""

    response = llm.invoke(prompt)
    return f"Meal ideas for '{criteria}':\n\n{response.content}"


