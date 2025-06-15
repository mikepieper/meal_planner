from typing import Annotated, Optional, List, Literal, Union

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command, ToolMessage

from src.models import MealPlannerState, MealPreferences, NutritionGoals
from src.tool_utils import add_dietary_restrictions_context
from src.constants import MEAL_TYPES, MealType

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


    return Command(
        update={"user_profile": new_profile},
        messages=[
            ToolMessage(
                content=f"Updated user profile",
                tool_call_id=tool_call_id
            )
        ]
    )


# === NUTRITION TOOLS ===

# NOTE: Nutrition tracking is currently disabled
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
        },
        messages=[
            ToolMessage(
                content=f"Successfully set nutrition goals",
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
    restrictions = state.user_profile.dietary_restrictions
    preferences = state.user_profile
    
    # Build context based on what we know
    context = "Suggest 5-7 specific foods with realistic portion sizes.\n\n"
    
    if focus_area:
        context += f"Focus on: {focus_area}\n\n"
    
    # Add dietary restrictions
    context = add_dietary_restrictions_context(context, restrictions, "ONLY suggest foods that are FULLY compliant with")
    
    # Add preferences if available
    if preferences.preferred_cuisines:
        context += f"Preferred cuisines: {', '.join(preferences.preferred_cuisines)}\n"
    if preferences.cooking_time_preference:
        context += f"Cooking time preference: {preferences.cooking_time_preference}\n"
    if preferences.health_goals:
        context += f"Health goals: {', '.join(preferences.health_goals)}\n"
    
    prompt = f"""{context}

Provide 5-7 specific food suggestions with portions.
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
    user_profile = state.user_profile

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
    context = add_dietary_restrictions_context(context, user_profile.dietary_restrictions)
    if user_profile.preferred_cuisines:
        context += f"Preferred cuisines: {', '.join(user_profile.preferred_cuisines)}\n"
    if user_profile.cooking_time_preference:
        context += f"Cooking time preference: {user_profile.cooking_time_preference}\n"

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
