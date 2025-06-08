from typing import Dict, Any, Optional, List
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage


from src.models import MealPlannerState
from src.tools import (
    add_meal_item,
    remove_meal_item,
    update_meal_item,
    clear_meal,
    clear_meal_plan,
    add_multiple_meal_items
)

def _build_meal_plan_context(state: MealPlannerState, messages: List[BaseMessage]) -> Optional[SystemMessage]:
    """
    Build context message from current meal plan if conditions are met.
    
    Args:
        state: Current agent state containing meal plan
        messages: List of conversation messages
        
    Returns:
        SystemMessage with meal plan context, or None if conditions not met
    """
    # Only add context if we're not in the middle of a tool execution
    last_msg = messages[-1] if messages else None
    if (state.get("current_meal_plan") and 
        not (last_msg and isinstance(last_msg, AIMessage) and last_msg.tool_calls)):
        plan = state["current_meal_plan"]
        if any([plan.breakfast, plan.lunch, plan.dinner, plan.snacks]):
            context = f"Current meal plan status: {json.dumps(plan.dict(), default=str, indent=2)}"
            return SystemMessage(content=context)
    return None

def create_meal_planning_agent():
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o")

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

    # Define tools
    tools = [
        # add_meal_item,
        # remove_meal_item,
        # update_meal_item,
        # clear_meal,
        # clear_meal_plan,
        # add_multiple_meal_items
    ]
    llm_with_tools = llm.bind_tools(tools)

    # System message
    sys_msg = SystemMessage(content="You are a helpful nutrition assistant tasked with creating a meal plan for a user.")

    # Define LLM node
    def agent_node(state: MealPlannerState) -> Dict[str, Any]:
        messages = state["messages"]
        
        # Build clean message list for LLM
        llm_messages = []
        
        # Always start with system prompt
        llm_messages.append(SystemMessage(content=SYSTEM_PROMPT))

        # Add context about current meal plan if appropriate
        context_msg = _build_meal_plan_context(state, messages)
        if context_msg:
            llm_messages.append(context_msg)
        
        # Add all non-system messages from state
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)

        return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

    # Build graph
    workflow = StateGraph(MealPlannerState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")

    workflow.add_conditional_edges(
        "agent",
        # If the latest message (result) from agent is a tool call -> tools_condition routes to tools
        # If the latest message (result) from agent is a not a tool call -> tools_condition routes to END
        tools_condition,
    )
    workflow.add_edge("tools", "agent")

    # # Add memory
    # memory = MemorySaver()

    # Compile the graph
    graph = workflow.compile(
        # checkpointer=memory
    )
    return graph


# Create and export the graph
graph = create_meal_planning_agent()

# This is what LangGraph Studio will load
__all__ = ["graph"] 