from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from src.models import MealPlannerState
from src.tools import (
    # Meal Management
    add_meal_item,
    add_meal_from_suggestion,
    remove_meal_item,
    view_current_meals,
    clear_meal,
    clear_all_meals,
    # Nutrition
    set_nutrition_goals,
    analyze_meal_nutrition,
    analyze_daily_nutrition,
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
        add_meal_from_suggestion,
        remove_meal_item,
        view_current_meals,
        clear_meal,
        clear_all_meals,
        # Nutrition
        set_nutrition_goals,
        analyze_meal_nutrition,
        analyze_daily_nutrition,
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

When users ask for meal plans or suggestions:
- If they provide calorie/diet info, use set_nutrition_goals first
- Use generate_meal_plan for complete plans, suggest_meal for individual meals
- Always analyze nutrition after creating plans to ensure they meet goals

When users manually build plans:
- Use add_meal_item for specific items
- Use add_meal_from_suggestion when they select from your suggestions
- Show the current plan with view_current_meals after changes
- Offer to analyze nutrition or suggest complementary items

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