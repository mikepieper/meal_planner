from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage

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
    generate_remaining_meals,
    suggest_meal,
    get_meal_ideas,
    # Utility
    generate_shopping_list
)
from src.agent_prompt import AGENT_PROMPT
from src.summarize_node import should_summarize, summarize_conversation

# ====== LLM ======
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
    generate_remaining_meals,
    suggest_meal,
    get_meal_ideas,
    # Utility
    generate_shopping_list
]

llm_with_tools = llm.bind_tools(tools)


# ====== SIMPLIFIED REACT AGENT ======
def agent_node(state: MealPlannerState) -> dict:
    """Main ReAct agent node."""
    messages = state.messages
    summary = state.summary

    # Build conversation for LLM
    llm_messages = [SystemMessage(content=AGENT_PROMPT)]

    # Add conversation summary if it exists
    if summary:
        llm_messages.append(SystemMessage(content=f"Summary of conversation history: {summary}"))

    # Add phase-specific guidance
    phase = state.conversation_context.planning_phase
    phase_guidance = get_phase_guidance(phase, state)
    if phase_guidance:
        llm_messages.append(SystemMessage(content=phase_guidance))

    # Add nutrition context if relevant
    if state.current_totals and state.nutrition_goals:
        totals = state.current_totals
        goals = state.nutrition_goals
        nutrition_context = (
            f"Current nutrition: {totals.calories:.0f} cal, "
            f"{totals.protein:.0f}g protein "
            f"({(totals.calories/goals.daily_calories*100):.0f}% of daily goal)"
        )
        llm_messages.append(SystemMessage(content=nutrition_context))

    # Add conversation history (limit to recent 6 messages to avoid token issues)
    for msg in messages[-10:]:
        if not isinstance(msg, SystemMessage):
            llm_messages.append(msg)

    # Get agent response
    result = llm_with_tools.invoke(llm_messages)

    return {"messages": [result]}


def create_meal_planning_agent():
    """Single ReAct agent that handles all meal planning tasks."""

    # Build the graph
    graph = StateGraph(MealPlannerState)

    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("summarize", summarize_conversation)

    # Add edges
    graph.add_edge(START, "agent")
    
    # Conditional routing from agent
    graph.add_conditional_edges(
        "agent",
        should_summarize,
        {
            "tools": "tools",
            "summarize": "summarize", 
            END: END
        }
    )
    
    # Tools always go back to agent
    graph.add_edge("tools", "agent")
    
    # After summarization, continue the conversation
    graph.add_edge("summarize", "agent")

    return graph.compile()


def get_phase_guidance(phase: str, state: MealPlannerState) -> str:
    """Get specific guidance based on current conversation phase."""

    if phase == "gathering_info":
        if not state.user_profile.dietary_restrictions:
            return "Current phase: Gathering Info. Ask about dietary restrictions and preferences."
        else:
            return (
                "Current phase: Gathering Info. You have their restrictions. "
                "Ask about calorie goals to move to next phase."
            )

    elif phase == "setting_goals":
        if not state.nutrition_goals:
            return "Current phase: Setting Goals. Help them set daily calorie and macro targets."
        else:
            return (
                "Current phase: Setting Goals. Goals are set! "
                "Offer to start building their meal plan."
            )

    elif phase == "building_meals":
        # Count how many meals have items
        meals_with_items = sum(1 for meal in [state.breakfast, state.lunch, state.dinner] if meal)
        empty_meals = [name for name, meal in [("breakfast", state.breakfast), ("lunch", state.lunch), ("dinner", state.dinner)] if not meal]

        if meals_with_items < 2:
            return (
                f"Current phase: Building Meals. {meals_with_items}/3 main meals planned. "
                "Focus on building out the meal plan."
            )
        elif empty_meals:
            return (
                f"Current phase: Building Meals. Empty slots: {', '.join(empty_meals)}. "
                "Offer to use generate_remaining_meals to fill them."
            )
        else:
            return (
                "Current phase: Building Meals. Most meals have items. "
                "Check if they're satisfied or want to optimize."
            )

    elif phase == "optimizing":
        if state.current_totals and state.nutrition_goals:
            totals = state.current_totals
            goals = state.nutrition_goals
            if totals.calories < goals.daily_calories * 0.9:
                return (
                    "Current phase: Optimizing. They're under calorie target. "
                    "Suggest foods to meet goals or generate_remaining_meals."
                )
            else:
                return (
                    "Current phase: Optimizing. Nutrition looks good! "
                    "Offer to generate shopping list or save as template."
                )

    elif phase == "complete":
        return (
            "Current phase: Complete. Offer shopping list, meal prep tips, "
            "or to save successful combinations."
        )

    return f"Current phase: {phase}"


# Create and export the graph
graph = create_meal_planning_agent()

# This is what LangGraph Studio will load
__all__ = ["graph"]
