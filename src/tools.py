import json

from langgraph.prebuilt import InjectedState
from typing import Annotated, Optional, List, Dict, Any, Literal
from langchain_core.tools import tool
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI

from src.models import MealPlannerState, MealItem

# Initialize LLM for analysis tools
analysis_llm = ChatOpenAI(model="gpt-4o", temperature=0)

def _validate_meal(meal: Optional[str], state: MealPlannerState) -> str:
    """Helper function to validate and return the correct meal."""
    if meal is None:
        meal = state.get("current_meal", "breakfast")
    if meal not in ["breakfast", "lunch", "dinner", "snack"]:
        raise ValueError("Invalid meal specified. Choose 'breakfast', 'lunch', 'dinner', or 'snack'.")
    return meal

def _create_command(updates: Dict[str, Any], message: str, tool_call_id: str, update_current_meal: Optional[str] = None) -> Command:
    """Helper function to create a Command with updates and message.
    
    Args:
        updates: Dictionary of state updates
        message: Message to add to state
        tool_call_id: Tool call ID for the message
        update_current_meal: If provided, updates the current_meal state
    """
    if update_current_meal:
        updates["current_meal"] = update_current_meal
    
    if "messages" not in updates:
        updates["messages"] = [ToolMessage(message, tool_call_id=tool_call_id)]
    
    return Command(update=updates)

# === MEAL MANAGEMENT TOOLS ===

@tool
def add_meal_item(
    food: str,
    amount: str,
    measure: Optional[str],
    meal: Optional[str],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Add a meal item to the specified meal or the current meal."""
    measure = measure or "unit"
    meal = _validate_meal(meal, state)

    new_item = MealItem(amount=amount, measure=measure, food=food)
    state[meal].append(new_item)

    return _create_command(
        {meal: state[meal]}, 
        f"Added {amount} {measure} of {food} to {meal}.", 
        tool_call_id,
        update_current_meal=meal
    )

@tool
def remove_meal_item(
    food: str,
    meal: Optional[str],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Remove a meal item from the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    meal_list = state[meal]
    for item in meal_list:
        if item.food == food:
            meal_list.remove(item)
            break
    else:
        raise ValueError(f"{food} not found in {meal}.")

    return _create_command(
        {meal: meal_list, "current_meal": meal},
        f"Removed {food} from {meal}.",
        tool_call_id
    )

@tool
def update_meal_item(
    food: str,
    new_amount: Optional[str],
    new_measure: Optional[str],
    new_food: Optional[str],
    meal: Optional[str],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Update a meal item in the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    meal_list = state[meal]
    for item in meal_list:
        if item.food == food:
            if new_amount:
                item.amount = new_amount
            if new_measure:
                item.measure = new_measure
            if new_food:
                item.food = new_food
            break
    else:
        raise ValueError(f"{food} not found in {meal}.")

    return _create_command(
        {meal: meal_list, "current_meal": meal},
        f"Updated {food} in {meal}.",
        tool_call_id
    )

@tool
def clear_meal(
    meal: Optional[str],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Clear all items from the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    state[meal] = []

    return _create_command(
        {meal: [], "current_meal": meal},
        f"Cleared {meal}.",
        tool_call_id
    )

@tool
def clear_meal_plan(
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Clear the entire meal plan."""
    return _create_command(
        {"breakfast": [], "lunch": [], "dinner": [], "current_meal": "breakfast"},
        "Cleared the entire meal plan.",
        tool_call_id
    )

@tool
def add_multiple_meal_items(
    items: List[MealItem],
    meal: Optional[str],
    state: Annotated[MealPlannerState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> dict:
    """Add multiple meal items to the specified meal or the current meal."""
    meal = _validate_meal(meal, state)

    added_items = []
    for item_input in items:
        measure = item_input.measure or "unit"
        new_item = MealItem(amount=item_input.amount, measure=measure, food=item_input.food)
        state[meal].append(new_item)
        added_items.append(f"{item_input.amount} {measure} of {item_input.food}")

    return _create_command(
        {meal: state[meal]},
        "Added " + ", ".join(added_items) + f" to {meal}.",
        tool_call_id
    )

# === NUTRITION TOOLS ===

@tool
def set_nutrition_goals(
    daily_calories: int,
    diet_type: Optional[str] = "balanced"
) -> str:
    """Set personalized nutrition goals based on calorie target and diet type."""
    # Calculate macro targets based on diet type
    if "high_protein" in str(diet_type).lower() or diet_type == "high_protein":
        protein_percent = 0.30
        carb_percent = 0.40
        fat_percent = 0.30
    elif "low_carb" in str(diet_type).lower() or diet_type == "low_carb":
        protein_percent = 0.25
        carb_percent = 0.20
        fat_percent = 0.55
    else:  # balanced
        protein_percent = 0.20
        carb_percent = 0.50
        fat_percent = 0.30
    
    goals = {
        "calories": {
            "minimum": daily_calories * 0.9,
            "target": daily_calories,
            "maximum": daily_calories * 1.1
        },
        "protein": {
            "minimum": (daily_calories * protein_percent / 4) * 0.9,
            "target": daily_calories * protein_percent / 4,
            "maximum": (daily_calories * protein_percent / 4) * 1.1
        },
        "carbohydrates": {
            "minimum": (daily_calories * carb_percent / 4) * 0.9,
            "target": daily_calories * carb_percent / 4,
            "maximum": (daily_calories * carb_percent / 4) * 1.1
        },
        "fat": {
            "minimum": (daily_calories * fat_percent / 9) * 0.9,
            "target": daily_calories * fat_percent / 9,
            "maximum": (daily_calories * fat_percent / 9) * 1.1
        }
    }
    
    return json.dumps(goals, indent=2)

# === ANALYSIS & PLANNING TOOLS ===

@tool
def analyze_message_complexity(
    user_message: str
) -> Dict[str, Any]:
    """Analyze if a message contains multiple intents and determine complexity."""
    
    prompt = f"""Analyze this user message for meal planning complexity:

User message: "{user_message}"

Determine:
1. Number of distinct intents/requests
2. Whether planning/decomposition is needed
3. Which tasks can be parallelized vs must be sequential
4. Overall complexity level

Respond in JSON:
{{
    "intent_count": <number>,
    "complexity": "simple" | "moderate" | "complex",
    "needs_planning": true | false,
    "intents": [
        {{
            "type": "meal_modification" | "meal_generation" | "nutrition_setup" | "information_request",
            "description": "<brief description>",
            "dependencies": [], // list of other intent indices this depends on
            "can_parallelize": true | false
        }}
    ]
}}"""
    
    response = analysis_llm.invoke(prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "intent_count": 1,
            "complexity": "simple", 
            "needs_planning": False,
            "intents": [{"type": "meal_modification", "description": "Single request", "dependencies": [], "can_parallelize": False}]
        }

@tool
def create_execution_plan(
    complexity_analysis: Dict[str, Any],
    user_message: str
) -> Dict[str, Any]:
    """Create a structured execution plan for complex multi-intent messages."""
    
    prompt = f"""Based on this complexity analysis, create a detailed execution plan:

Analysis: {json.dumps(complexity_analysis, indent=2)}
Original message: "{user_message}"

Create an execution plan with:
1. Sequential steps (tasks that must happen in order)
2. Parallel groups (tasks that can happen simultaneously) 
3. Specific tool calls for each task
4. Expected coordination points

Respond in JSON:
{{
    "execution_strategy": "sequential" | "parallel" | "hybrid",
    "steps": [
        {{
            "step_number": 1,
            "type": "sequential" | "parallel_group",
            "tasks": [
                {{
                    "task_id": "task_1",
                    "subgraph": "intent_router" | "manual_editor" | "automated_planner" | "info_gatherer",
                    "tool_calls": ["tool_name"],
                    "description": "What this task accomplishes"
                }}
            ]
        }}
    ]
}}"""
    
    response = analysis_llm.invoke(prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "execution_strategy": "sequential",
            "steps": [{"step_number": 1, "type": "sequential", "tasks": []}]
        }

@tool
def analyze_user_intent(
    user_message: str
) -> Dict[str, Any]:
    """Analyze user's message to determine their meal planning intent and preferences."""
    
    prompt = f"""Analyze the following user message about meal planning and determine:
1. Their assistance preference level:
   - "manual": User wants to build their own meal plan (e.g., "I want to add eggs", "Let me build")
   - "assisted": User wants some help but maintains control (e.g., "Help me plan lunch") 
   - "automated": User wants recommendations/suggestions (e.g., "Make me a meal plan", "Create a healthy plan")

2. Whether they mentioned specific calorie targets (extract the number if present)

3. Whether they mentioned a diet type (e.g., high-protein, low-carb, balanced)

User message: "{user_message}"

Respond in JSON format:
{{
    "assistance_level": "manual" | "assisted" | "automated",
    "calories_mentioned": null | <number>,
    "diet_type": null | "<diet_type>",
    "wants_general_suggestions": true | false
}}
"""
    
    response = analysis_llm.invoke(prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "assistance_level": "assisted",
            "calories_mentioned": None,
            "diet_type": None,
            "wants_general_suggestions": True
        }

@tool
def extract_nutrition_info(
    user_message: str
) -> Dict[str, Any]:
    """Extract nutrition-related information from user's message."""
    
    prompt = f"""Extract any nutrition-related information from this message:

User message: "{user_message}"

Look for:
1. Daily calorie targets (e.g., "2000 calories", "2,000 cal")
2. Diet preferences (e.g., "high protein", "low carb", "balanced", "keto")
3. Dietary restrictions (e.g., "vegetarian", "gluten-free", "no dairy")
4. Health goals (e.g., "lose weight", "build muscle", "maintain")

Respond in JSON format:
{{
    "daily_calories": null | <number>,
    "diet_type": null | "<type>",
    "dietary_restrictions": [],
    "health_goals": []
}}
"""
    
    response = analysis_llm.invoke(prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "daily_calories": None,
            "diet_type": None,
            "dietary_restrictions": [],
            "health_goals": []
        }

@tool
def generate_meal_suggestions(
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"],
    preferences: Optional[Dict[str, Any]] = None
) -> str:
    """Generate meal suggestions based on meal type and optional preferences."""
    
    pref_context = ""
    if preferences:
        if preferences.get("dietary_restrictions"):
            pref_context += f"Dietary restrictions: {', '.join(preferences['dietary_restrictions'])}. "
        if preferences.get("diet_type"):
            pref_context += f"Diet type: {preferences['diet_type']}. "
    
    prompt = f"""Suggest 3 {meal_type} options that are healthy and balanced.
{pref_context}

Provide suggestions in this format:
Option 1: [Name] - [Brief description]
Option 2: [Name] - [Brief description] 
Option 3: [Name] - [Brief description]
"""
    
    response = analysis_llm.invoke(prompt)
    return response.content