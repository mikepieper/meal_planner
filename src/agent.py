from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from src.models import MealPlannerState
from src.tools import (
    # Meal Management
    add_meal_item,
    add_multiple_items,
    add_meal_from_suggestion,
    remove_meal_item,
    view_current_meals,
    clear_meal,
    clear_all_meals,
    # User Profile
    update_user_profile,
    # Nutrition
    set_nutrition_goals,
    analyze_meal_nutrition,
    analyze_daily_nutrition,
    suggest_foods_to_meet_goals,
    # Planning
    generate_meal_plan,
    suggest_meal,
    get_meal_ideas,
    # Utility
    generate_shopping_list
)

# ====== SIMPLIFIED REACT AGENT ======

def create_meal_planning_agent():
    """Single ReAct agent that handles all meal planning tasks."""
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    # All available tools
    tools = [
        # Meal Management
        add_meal_item,
        add_multiple_items,
        add_meal_from_suggestion,
        remove_meal_item,
        view_current_meals,
        clear_meal,
        clear_all_meals,
        # User Profile
        update_user_profile,
        # Nutrition
        set_nutrition_goals,
        analyze_meal_nutrition,
        analyze_daily_nutrition,
        suggest_foods_to_meet_goals,
        # Planning
        generate_meal_plan,
        suggest_meal,
        get_meal_ideas,
        # Utility
        generate_shopping_list
    ]
    
    llm_with_tools = llm.bind_tools(tools)
    
    AGENT_PROMPT = """You are a friendly and knowledgeable meal planning assistant. Your goal is to help users create personalized, nutritious meal plans that fit their preferences and dietary needs.

Key behaviors:
1. **Be conversational and helpful** - Act like a knowledgeable friend, not a robot
2. **Ask clarifying questions** when needed, but don't overwhelm with too many questions
3. **Use tools intelligently** - Select the right tool for each task
4. **Provide context** - Explain why you're making certain suggestions
5. **Be proactive** - After completing a task, offer relevant next steps

IMPORTANT: Track conversation context:
- When you use suggest_meal, the suggestions are saved in conversation_context
- When users say "add option 1" or "the first one", use add_meal_from_suggestion with "option_1"
- The planning phase progresses: gathering_info → setting_goals → building_meals → optimizing → complete
- Remember what suggestions you've shown to avoid repeating

NUTRITION TRACKING:
- Running nutrition totals are automatically calculated and stored in current_totals
- view_current_meals now shows current totals and progress toward goals
- suggest_meal automatically considers remaining nutrition needs
- Dietary restrictions are validated automatically - restricted foods will be rejected
- Use suggest_foods_to_meet_goals when users need help reaching nutrition targets

Tool Usage Guidelines:
- Use update_user_profile to properly save dietary restrictions and preferences
- Use add_multiple_items when adding several custom items at once
- Use add_meal_from_suggestion for quick addition of suggested meals
- Always use set_nutrition_goals before generating meal plans

When users provide dietary information:
- Use update_user_profile to save restrictions like "vegetarian", "no gluten", etc.
- The system will automatically validate foods against restrictions
- If a food is rejected, explain why and suggest alternatives

When users ask for meal plans or suggestions:
- If they provide calorie/diet info, use set_nutrition_goals first
- Use generate_meal_plan for complete plans, suggest_meal for individual meals
- The tools now automatically consider remaining nutrition needs
- After adding meals, view_current_meals shows running totals

When users manually build plans:
- Use add_meal_item for single items
- Use add_multiple_items for batch additions
- Use add_meal_from_suggestion when they select from your suggestions
- Show the current plan with view_current_meals after changes (it includes nutrition)
- Offer suggest_foods_to_meet_goals if they're short on any nutrients

Remember: You're here to make meal planning easy, enjoyable, and personalized!"""
    
    def agent_node(state: MealPlannerState) -> dict:
        """Main ReAct agent node."""
        messages = state["messages"]
        
        # Build conversation for LLM
        llm_messages = [SystemMessage(content=AGENT_PROMPT)]
        
        # Add phase context if relevant
        phase = state.get("conversation_context", {}).planning_phase
        if phase and phase != "gathering_info":
            phase_context = f"Current planning phase: {phase}"
            llm_messages.append(SystemMessage(content=phase_context))
        
        # Add nutrition context if relevant
        if state.get("current_totals") and state.get("nutrition_goals"):
            totals = state["current_totals"]
            goals = state["nutrition_goals"]
            nutrition_context = f"Current nutrition: {totals.calories:.0f} cal, {totals.protein:.0f}g protein ({(totals.calories/goals.daily_calories*100):.0f}% of daily goal)"
            llm_messages.append(SystemMessage(content=nutrition_context))
        
        # Add conversation history (limit to recent messages to avoid token issues)
        for msg in messages[-10:]:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        # Get agent response
        result = llm_with_tools.invoke(llm_messages)
        
        return {"messages": [result]}
    
    # Build the graph
    graph = StateGraph(MealPlannerState)
    
    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    
    # Add edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    graph.add_edge("agent", END)
    
    return graph.compile()

# Create and export the graph
graph = create_meal_planning_agent()

# This is what LangGraph Studio will load
__all__ = ["graph"] 