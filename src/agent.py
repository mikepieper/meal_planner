from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage

from src.agent_prompt import AGENT_PROMPT
from src.models import MealPlannerState
from src.summarize_node import summarize_conversation, should_summarize
# Tool Imports
from src.tools.manual_planning_tools import (
    add_meal_item,
    add_multiple_items,
    remove_meal_item,
    view_current_meal_plan,
    clear_meal,
    clear_all_meals,
)
from src.tools.tools import (
    update_user_profile,
    set_nutrition_goals,
    suggest_foods_to_meet_goals,
    generate_meal_plan,
    get_meal_suggestions,
)
from src.tools.tool_utils import generate_shopping_list


# ====== LLM ======
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

tools = [
    # Manual Planning Tools
    add_meal_item,
    add_multiple_items,
    remove_meal_item,
    view_current_meal_plan,
    clear_meal,
    clear_all_meals,
    # Utility
    generate_shopping_list,
    # Tools - User Profile
    update_user_profile,
    # Tools - Nutrition
    set_nutrition_goals,
    # Tools - Planning
    suggest_foods_to_meet_goals,
    generate_meal_plan,
    get_meal_suggestions,
]

llm_with_tools = llm.bind_tools(tools)


# ====== AGENT ======
def agent_node(state: MealPlannerState) -> dict:
    """Main ReAct agent node."""
    messages = state.messages
    summary = state.summary

    # Build conversation for LLM
    llm_messages = [SystemMessage(content=AGENT_PROMPT)]

    # Add conversation summary if it exists
    if summary:
        llm_messages.append(SystemMessage(content=f"Summary of conversation history: {summary}"))

    # # Add nutrition context if relevant
    # if state.current_totals and state.nutrition_goals:
    #     totals = state.current_totals
    #     goals = state.nutrition_goals
    #     nutrition_context = (
    #         f"Current nutrition: {totals.calories:.0f} cal, "
    #         f"{totals.protein:.0f}g protein "
    #         f"({(totals.calories/goals.daily_calories*100):.0f}% of daily goal)"
    #     )
    #     llm_messages.append(SystemMessage(content=nutrition_context))

    # Add conversation history (limit to recent 10 messages to avoid token issues)
    llm_messages.extend([msg for msg in messages[-10:] if not isinstance(msg, SystemMessage)])

    # Get agent response
    result = llm_with_tools.invoke(llm_messages)

    return {"messages": [result]}


def build_graph():
    """Single ReAct agent that handles all meal planning tasks."""

    # Build the graph
    workflow = StateGraph(MealPlannerState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("summarize", summarize_conversation)

    # Add edges

    # Set the entrypoint as agent
    workflow.add_edge(START, "agent")
    
    # Conditional routing from agent
    workflow.add_conditional_edges(
        "agent",
        should_summarize,
        {
            "tools": "tools",
            "summarize": "summarize", 
            END: END
        }
    )
    
    # Tools always go back to agent
    workflow.add_edge("tools", "agent")
    # After summarization, continue the conversation
    workflow.add_edge("summarize", "agent")

    return workflow.compile()