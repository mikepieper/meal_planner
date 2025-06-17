from typing import Annotated, Optional, List, Literal, Union

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from src.context_functions import get_user_profile_context, get_dietary_restrictions_context
from src.models import MealPlannerState, MealPreferences, NutritionGoals, MEAL_TYPES, MealType
from src.context_functions import get_dietary_restrictions_context


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


    return Command(update={"user_profile": new_profile}) # No message since silent tool


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
    current_goals = state.get("nutrition_goals")
    
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
            update={"nutrition_goals": goals},
            messages=[
                ToolMessage(
                    content=message,
                    tool_call_id=tool_call_id
                )
            ]
        )
    except ValueError as e:
        return Command(
            messages=[
                ToolMessage(
                    content=f"Error setting nutrition goals: {str(e)}",
                    tool_call_id=tool_call_id
                )
            ]
        )

# === SMART SUGGESTION TOOLS ===

@tool
def suggest_foods_to_meet_goals(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    focus_area: Optional[str] = None
) -> str:
    """Suggest specific foods with portions based on dietary preferences and optional focus areas.
    
    Provides 5-7 specific food recommendations that respect dietary restrictions
    and align with user preferences. Can target specific nutritional focus areas
    if specified.
    
    Parameters:
    - focus_area: Optional nutritional focus (e.g., "high protein", "high fiber", "low calorie")
    
    This tool is most useful when:
    - User wants targeted food recommendations rather than full meals
    - Looking for specific types of foods (high protein, etc.)
    - Building meals incrementally with individual items
    
    PREREQUISITES:
    - Works best when dietary restrictions are set via update_user_profile()
    - More personalized if preferences (cuisines, cooking time) are also set
    
    Examples:
    - suggest_foods_to_meet_goals()  # General healthy suggestions
    - suggest_foods_to_meet_goals(focus_area="high protein")  # Protein-focused
    - suggest_foods_to_meet_goals(focus_area="quick breakfast options")
    """    
    # Build context based on what we know
    context = ""
    if focus_area:
        context += f"Focus on: {focus_area}\n\n"
    context += get_user_profile_context(state)    
    prompt = f"""{context}

Provide 5-7 specific food suggestions with realisticportions.
Focus on variety and practical options that align with any stated preferences."""

    response = llm.invoke(prompt)
    return f"**Food suggestions{f' for {focus_area}' if focus_area else ''}:**\n\n{response.content}"

@tool
def generate_meal_plan(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    meal_types: Optional[Union[List[MealType], Literal["all"]]] = None,
    preferences: Optional[MealPreferences] = None
) -> str:
    """Generate meal plan suggestions for specified meals or auto-detect empty slots.
    
    Flexible tool that can generate suggestions for:
    - Empty meals only (default behavior)
    - Specific meals you choose
    - Complete daily plan (all meals)
    
    Always shows existing meals for context and does NOT modify current meals.
    
    Parameters:
    - meal_types: Controls which meals to generate:
      * None (default): Auto-detects and fills only empty meal slots
      * "all": Generates suggestions for all meals (full daily plan)
      * List of meal types: Generate only specified meals (e.g., ["breakfast", "lunch"])
    - preferences: Optional MealPreferences object with structured preferences:
      * cuisine: Preferred cuisine type (e.g., 'italian', 'mediterranean', 'asian')
      * cooking_time: 'quick', 'moderate', or 'extensive'
      * meal_style: Style like 'light', 'hearty', 'comfort food', 'fresh'
      * ingredients_to_include: List of specific ingredients to include
      * ingredients_to_avoid: List of ingredients to avoid
    
    PREREQUISITES:
    - For best results, set dietary restrictions via update_user_profile() first
    - User preferences (cuisines, cooking time) improve personalization
    
    Examples:
    - generate_meal_plan()  # Auto-fill empty meals only
    - generate_meal_plan(meal_types="all")  # Complete daily plan
    - generate_meal_plan(meal_types=["breakfast", "lunch"])  # Specific meals
    - generate_meal_plan(preferences=MealPreferences(cuisine="mediterranean"))
    
    Returns formatted suggestions that the user can review. The agent will
    implement approved suggestions using add_multiple_items.
    """
    # Determine which meals to generate
    if meal_types is None:
        # Auto-detect empty meals
        meals_to_generate = []
        for meal in MEAL_TYPES:
            if not getattr(state, meal):
                meals_to_generate.append(meal)
        
        if not meals_to_generate:
            return "All meals are already planned! Your meal plan is complete."
    elif meal_types == "all":
        # Generate all meals
        meals_to_generate = MEAL_TYPES
    else:
        # Use specified meals
        meals_to_generate = meal_types

    # Show current meal plan status
    result = "**Current Meal Plan:**\n"
    has_existing_meals = False
    
    for meal_type in MEAL_TYPES:
        items = getattr(state, meal_type)
        if items:
            has_existing_meals = True
            result += f"\n{meal_type.capitalize()}:\n"
            for item in items:
                result += f"  - {item.amount} {item.unit} of {item.food}\n"
        else:
            if meal_type in meals_to_generate:
                result += f"\n{meal_type.capitalize()}: *Empty - will suggest*\n"
            else:
                result += f"\n{meal_type.capitalize()}: Empty\n"

    result += "\n---\n\n"
    
    # Format header based on what we're generating
    if meal_types is None:
        result += "**Suggested meals for empty slots:**\n\n"
    elif meal_types == "all":
        result += "**Complete Daily Meal Plan Suggestion:**\n\n"
    else:
        result += f"**Suggested meals for {', '.join(meals_to_generate)}:**\n\n"

    # Build context for generation
    context = f"Generate balanced, healthy meals for these slots: {', '.join(meals_to_generate)}\n\n"
    
    # Add dietary restrictions and preferences
    context += get_dietary_restrictions_context(state)

    # Add specific preferences if provided
    if preferences:
        context += "\nAdditional preferences:\n"
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

    # Set expectations for portion sizes based on meal types
    meal_portions = {
        "breakfast": "2-4 items",
        "lunch": "3-5 items",
        "dinner": "3-5 items",
        "snacks": "1-3 items"
    }
    
    portion_guide = "\n".join([f"- {meal.capitalize()}: {meal_portions[meal]}" 
                              for meal in meals_to_generate if meal in meal_portions])

    prompt = f"""{context}

Generate meals with specific portions for these meal types: {', '.join(meals_to_generate)}.

Target portions:
{portion_guide}

Provide realistic portion sizes for each food item.
Format each meal clearly with the meal name followed by items."""

    response = llm.invoke(prompt)
    result += response.content

    # Add implementation note
    if meal_types == "all" and has_existing_meals:
        result += "\n\n*Note: This is a complete meal plan suggestion. You can choose to:"
        result += "\n- Replace your entire current plan"
        result += "\n- Keep some existing meals and only add the new suggestions for empty slots"
        result += "\n- Mix and match items from the suggestions*"
    else:
        result += f"\n\n*To implement these suggestions, I can add the items to your meal plan using the meal planning tools.*"

    return result


@tool
def get_meal_suggestions(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    meal_type: Optional[MealType] = None,
    criteria: Optional[str] = None,
    num_suggestions: int = 3,
    preferences: Optional[MealPreferences] = None
) -> str:
    """Generate meal suggestions based on meal type and/or specific criteria.
    
    Flexible tool that can handle both specific meal slots and general meal ideas.
    Takes into account dietary restrictions and preferences.
    
    PREREQUISITES:
    - For best results, set dietary restrictions via update_user_profile() first
    - User preferences (cuisines, cooking time) improve personalization
    
    Parameters:
    - meal_type: Optional - 'breakfast', 'lunch', 'dinner', or 'snacks'
    - criteria: Optional - Any specific requirements (e.g., "high protein", "using chicken", "30 minute meals")
    - num_suggestions: Number of suggestions to generate (default 3, max 10)
    - preferences: Optional MealPreferences object with structured preferences:
      * cuisine: Preferred cuisine type (e.g., 'italian', 'mediterranean', 'asian')
      * cooking_time: 'quick', 'moderate', or 'extensive'
      * meal_style: Style like 'light', 'hearty', 'comfort food', 'fresh'
      * ingredients_to_include: List of specific ingredients to include
      * ingredients_to_avoid: List of ingredients to avoid
    
    Examples:
    - get_meal_suggestions(meal_type="breakfast")  # 3 breakfast ideas
    - get_meal_suggestions(criteria="high protein vegetarian")  # 3 high-protein veg ideas
    - get_meal_suggestions(meal_type="lunch", criteria="mediterranean style")  # Combined
    - get_meal_suggestions(criteria="using leftover rice", num_suggestions=5)  # 5 ideas
    - get_meal_suggestions(meal_type="dinner", preferences=MealPreferences(cooking_time="quick"))
    
    Returns formatted text with meal suggestions. The agent can parse these
    suggestions from conversation history when the user wants to add items.
    """
    if not meal_type and not criteria:
        return "Please specify either a meal type (breakfast/lunch/dinner/snacks) or criteria for suggestions."
    
    user_profile = state.user_profile
    num_suggestions = min(num_suggestions, 10)  # Cap at 10 suggestions
    
    # Build context
    context = ""
    
    if meal_type and criteria:
        context = f"Suggest {num_suggestions} different {meal_type} options that match: {criteria}\n\n"
    elif meal_type:
        context = f"Suggest {num_suggestions} different {meal_type} options.\n\n"
    else:
        context = f"Suggest {num_suggestions} meal ideas based on: {criteria}\n\n"
    
    # Add health goals if available for general guidance
    if user_profile.health_goals:
        context += f"User health goals: {', '.join(user_profile.health_goals)}\n"
        # Add specific guidance based on health goals
        if "muscle gain" in user_profile.health_goals or "high protein" in str(user_profile.health_goals).lower():
            context += "PRIORITIZE HIGH PROTEIN OPTIONS\n\n"
        elif "weight loss" in user_profile.health_goals:
            context += "Focus on nutrient-dense, lower-calorie options\n\n"
    
    # Add dietary restrictions
    context = add_dietary_restrictions_context(context, user_profile.dietary_restrictions, 
                                             "Only suggest foods that STRICTLY comply with")
    
    # Add preferences if provided
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
    
    # Add user profile preferences if no specific preferences provided
    elif user_profile.preferred_cuisines or user_profile.cooking_time_preference:
        context += "User preferences:\n"
        if user_profile.preferred_cuisines:
            context += f"- Preferred cuisines: {', '.join(user_profile.preferred_cuisines)}\n"
        if user_profile.cooking_time_preference:
            context += f"- Cooking time preference: {user_profile.cooking_time_preference}\n"
        context += "\n"
    
    prompt = f"""{context}

Provide {num_suggestions} detailed meal suggestions with:
- Complete list of ingredients with specific portions
- Brief description of preparation
- Estimated nutritional information if relevant

Format each suggestion clearly with a number or name."""
    
    response = llm.invoke(prompt)
    
    # Format the response
    header = ""
    if meal_type and criteria:
        header = f"**{num_suggestions} {meal_type.capitalize()} suggestions matching '{criteria}':**\n\n"
    elif meal_type:
        header = f"**{num_suggestions} {meal_type.capitalize()} suggestions:**\n\n"
    else:
        header = f"**{num_suggestions} meal ideas for '{criteria}':**\n\n"
    
    return header + response.content
