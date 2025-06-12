from typing import Dict, Any, Optional, List
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage

from src.models import MealPlannerState
from src.tools import (
    # Analysis & Planning
    extract_nutrition_info,
    # Nutrition & Generation
    set_nutrition_goals,
    generate_meal_suggestions
)


def create_automated_planner_subgraph():
    """Generates meal suggestions and handles nutrition optimization."""
    
    llm = ChatOpenAI(model="gpt-4o")
    tools = [set_nutrition_goals, generate_meal_suggestions, extract_nutrition_info]
    llm_with_tools = llm.bind_tools(tools)
    
    PLANNER_PROMPT = """
You are the Automated Meal Planner. You generate personalized meal suggestions.

Your approach:
1. If calories are mentioned, set nutrition goals immediately
2. Generate suggestions based on preferences and goals
3. Provide variety and balance in recommendations
4. Offer customization options

Use progressive disclosure - provide immediate value, then offer deeper personalization.
"""
    
    def planner_node(state: MealPlannerState) -> Dict[str, Any]:
        messages = state["messages"]
        
        llm_messages = [SystemMessage(content=PLANNER_PROMPT)]
        
        # Add user profile context if available
        if state.get("user_profile") and state["user_profile"].nutrition_goals:
            profile_context = f"User's nutrition goals: {json.dumps(state['user_profile'].nutrition_goals.model_dump(), default=str)}"
            llm_messages.append(SystemMessage(content=profile_context))
        
        # Add recent messages
        for msg in messages[-2:]:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        result = llm_with_tools.invoke(llm_messages)
        
        # Update user profile if nutrition goals were set
        if result.tool_calls:
            for tool_call in result.tool_calls:
                if tool_call["name"] == "set_nutrition_goals":
                    if "daily_calories" in tool_call["args"]:
                        state["user_profile"].daily_calories = tool_call["args"]["daily_calories"]
                        state["user_profile"].diet_type = tool_call["args"].get("diet_type", "balanced")
        
        return {"messages": [result]}
    
    # Build planner subgraph
    planner_graph = StateGraph(MealPlannerState)
    planner_graph.add_node("planner", planner_node)
    planner_graph.add_node("tools", ToolNode(tools))
    
    planner_graph.add_edge(START, "planner")
    planner_graph.add_conditional_edges("planner", tools_condition)
    planner_graph.add_edge("tools", "planner")
    planner_graph.add_edge("planner", END)
    
    return planner_graph.compile()