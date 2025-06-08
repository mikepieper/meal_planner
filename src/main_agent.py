"""
Main Integrated Meal Planning Agent
==================================

This module integrates the ReAct conversational agent with nutrition optimization
to create a comprehensive meal planning assistant.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal, Annotated, Sequence
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
import json
import os

from .nutrition_optimizer import (
    NutritionOptimizer, ConstraintSet, NutrientConstraint,
    FoodItem, Meal, MealPlan
)
from .food_database import get_food_database



# ========== Tools ==========

@tool
def generate_meal_suggestions(
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"],
    dietary_preferences: Optional[List[str]] = None,
    calorie_target: Optional[int] = None,
    avoid_foods: Optional[List[str]] = None
) -> str:
    """Generate meal suggestions based on preferences and constraints."""
    food_db = get_food_database()
    
    # Filter foods by meal type and preferences
    suitable_foods = []
    for food_id, food in food_db.items():
        # Check if food matches meal type
        if meal_type in food.tags or "snack" not in food.tags:
            # Check dietary preferences
            if dietary_preferences:
                if any(pref in food.tags for pref in dietary_preferences):
                    suitable_foods.append(food)
            else:
                suitable_foods.append(food)
    
    # Filter out avoided foods
    if avoid_foods:
        suitable_foods = [f for f in suitable_foods if f.name.lower() not in [a.lower() for a in avoid_foods]]
    
    # Create sample meals
    if meal_type == "breakfast":
        suggestions = [
            {
                "name": "Protein Power Bowl",
                "foods": {"greek_yogurt": 1, "berries": 0.5, "almonds": 0.5},
                "description": "High-protein Greek yogurt topped with antioxidant-rich berries and crunchy almonds"
            },
            {
                "name": "Classic Eggs & Toast",
                "foods": {"eggs": 1, "whole_wheat_toast": 2, "berries": 0.5},
                "description": "Scrambled eggs with whole grain toast and a side of fresh berries"
            },
            {
                "name": "Hearty Oatmeal",
                "foods": {"oatmeal": 1, "berries": 0.5, "almonds": 0.25},
                "description": "Warm oatmeal topped with fresh berries and sliced almonds for crunch"
            }
        ]
    elif meal_type == "lunch":
        suggestions = [
            {
                "name": "Quinoa Power Bowl",
                "foods": {"quinoa": 1, "grilled_chicken": 1, "broccoli": 1},
                "description": "Nutritious quinoa bowl with grilled chicken and steamed broccoli"
            },
            {
                "name": "Sweet Potato & Protein",
                "foods": {"sweet_potato": 1, "grilled_chicken": 1, "broccoli": 0.5},
                "description": "Baked sweet potato with grilled chicken and a side of broccoli"
            }
        ]
    elif meal_type == "dinner":
        suggestions = [
            {
                "name": "Salmon & Quinoa",
                "foods": {"salmon": 1, "quinoa": 1, "broccoli": 1},
                "description": "Omega-3 rich salmon with fluffy quinoa and steamed broccoli"
            },
            {
                "name": "Chicken & Sweet Potato",
                "foods": {"grilled_chicken": 1, "sweet_potato": 1, "broccoli": 1},
                "description": "Lean grilled chicken with roasted sweet potato and broccoli"
            }
        ]
    else:  # snack
        suggestions = [
            {
                "name": "Apple & Almonds",
                "foods": {"apple": 1, "almonds": 0.5},
                "description": "Fresh apple slices with a handful of almonds"
            },
            {
                "name": "Protein Bar",
                "foods": {"protein_bar": 1},
                "description": "Quick and convenient high-protein snack"
            }
        ]
    
    return json.dumps(suggestions, indent=2)


@tool
def optimize_meal_nutrition(
    meal_json: str,
    nutrition_goals_json: str
) -> str:
    """Optimize a meal to better meet nutritional goals."""
    meal_data = json.loads(meal_json)
    goals = json.loads(nutrition_goals_json)
    
    # Create nutrition profile from goals
    profile = ConstraintSet(
        calories=NutrientConstraint(**goals.get("calories", {"minimum": 400, "target": 500, "maximum": 600})),
        fat=NutrientConstraint(**goals.get("fat", {"minimum": 10, "target": 15, "maximum": 20})),
        carbohydrates=NutrientConstraint(**goals.get("carbohydrates", {"minimum": 50, "target": 65, "maximum": 80})),
        protein=NutrientConstraint(**goals.get("protein", {"minimum": 20, "target": 30, "maximum": 40}))
    )
    
    # Create meal object
    meal = Meal(
        id=meal_data.get("id", "meal1"),
        name=meal_data["name"],
        meal_type=meal_data["meal_type"],
        foods=meal_data["foods"]
    )
    
    # Optimize
    food_db = get_food_database()
    optimizer = NutritionOptimizer(food_db, profile)
    
    suggestions = optimizer.suggest_meal_improvement(meal, meal.meal_type)
    
    return json.dumps(suggestions, indent=2)


@tool
def save_meal_to_plan(
    meal_json: str,
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
) -> str:
    """Save a meal to the current meal plan."""
    meal_data = json.loads(meal_json)
    
    # This would update the state in the actual implementation
    return f"Saved {meal_data['name']} as {meal_type}"


@tool
def analyze_daily_nutrition() -> str:
    """Analyze the nutritional content of the current daily meal plan."""
    # This would analyze the current state's meal plan
    # For now, return mock analysis
    analysis = {
        "total_nutrition": {
            "calories": 1850,
            "fat": 65,
            "carbohydrates": 230,
            "protein": 95
        },
        "vs_targets": {
            "calories": "On target",
            "fat": "On target", 
            "carbohydrates": "Slightly low",
            "protein": "On target"
        },
        "recommendations": [
            "Consider adding a carbohydrate-rich snack to meet your target",
            "Great protein distribution throughout the day",
            "Good balance of nutrients across meals"
        ]
    }
    
    return json.dumps(analysis, indent=2)


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
            "minimum": (daily_calories * protein_percent / 4) * 0.9,  # 4 cal/g
            "target": daily_calories * protein_percent / 4,
            "maximum": (daily_calories * protein_percent / 4) * 1.1
        },
        "carbohydrates": {
            "minimum": (daily_calories * carb_percent / 4) * 0.9,  # 4 cal/g
            "target": daily_calories * carb_percent / 4,
            "maximum": (daily_calories * carb_percent / 4) * 1.1
        },
        "fat": {
            "minimum": (daily_calories * fat_percent / 9) * 0.9,  # 9 cal/g
            "target": daily_calories * fat_percent / 9,
            "maximum": (daily_calories * fat_percent / 9) * 1.1
        }
    }
    
    return json.dumps(goals, indent=2)


# ========== Main Agent ==========

def create_meal_planning_agent():
    """Create the main meal planning agent with all capabilities."""
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    # System prompt
    SYSTEM_PROMPT = """
You are NutriGuide, an expert meal planning assistant that combines nutritional science with culinary creativity.

Your mission is to help users create personalized, nutritionally optimized meal plans that are both healthy and delicious.

Key capabilities:
1. **Meal Generation**: Create diverse meal suggestions based on preferences
2. **Nutrition Optimization**: Fine-tune meals to meet specific macro/calorie goals
3. **Conversational Planning**: Guide users through the planning process naturally
4. **Holistic Approach**: Consider taste, nutrition, practicality, and preferences

Available tools:
- generate_meal_suggestions: Get meal ideas based on type and preferences
- optimize_meal_nutrition: Adjust portions to meet nutritional targets
- save_meal_to_plan: Add meals to the daily plan
- analyze_daily_nutrition: Review nutritional completeness
- set_nutrition_goals: Establish personalized targets

Interaction style:
- Be warm, encouraging, and knowledgeable
- Ask clarifying questions when needed
- Explain nutritional benefits in simple terms
- Celebrate progress and good choices
- Offer alternatives and modifications

Remember: You're not just planning meals, you're helping people build sustainable, healthy eating habits.
""".strip()
    
    # Bind tools
    tools = [
        generate_meal_suggestions,
        optimize_meal_nutrition,
        save_meal_to_plan,
        analyze_daily_nutrition,
        set_nutrition_goals
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    def agent_node(state: MealPlannerState) -> Dict[str, Any]:
        """Main reasoning node."""
        messages = state["messages"]
        
        # Build clean message list for LLM
        llm_messages = []
        
        # Always start with system prompt
        llm_messages.append(SystemMessage(content=SYSTEM_PROMPT))
        
        # Add context about current meal plan if exists and no recent tool calls
        # Only add if we're not in the middle of a tool execution
        last_msg = messages[-1] if messages else None
        if (state.get("current_meal_plan") and 
            not (last_msg and isinstance(last_msg, AIMessage) and last_msg.tool_calls)):
            plan = state["current_meal_plan"]
            if any([plan.breakfast, plan.lunch, plan.dinner, plan.snacks]):
                context = f"Current meal plan status: {json.dumps(plan.dict(), default=str, indent=2)}"
                llm_messages.append(SystemMessage(content=context))
        
        # Add all non-system messages from state
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        # Get response
        response = llm_with_tools.invoke(llm_messages)
        
        # Return just the new response - LangGraph will handle appending
        return {"messages": [response]}
    
    # Build graph
    workflow = StateGraph(MealPlannerState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
    )
    
    workflow.add_edge("tools", "agent")
    
    # Add memory
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)


# ========== Testing Helper ==========

def test_agent_interaction():
    """Test the agent with a sample interaction."""
    agent = create_meal_planning_agent()
    
    # Initial state
    initial_state = {
        "messages": [
            HumanMessage(content="Hi! I want to create a healthy meal plan. I'm vegetarian and trying to get more protein. My daily calorie target is around 2000.")
        ],
        "current_meal_plan": MealPlan(),
        "user_profile": {
            "dietary_preferences": ["vegetarian"],
            "goals": ["high_protein"],
            "daily_calories": 2000
        },
        "food_database": get_food_database(),
        "conversation_phase": "gathering_info",
        "optimization_history": []
    }
    
    # Run agent
    config = {"configurable": {"thread_id": "test_thread"}}
    result = agent.invoke(initial_state, config)
    
    return result


if __name__ == "__main__":
    # Test the agent
    result = test_agent_interaction()
    print("Agent response:")
    print(result["messages"][-1].content) 