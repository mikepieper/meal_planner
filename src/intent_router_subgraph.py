from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.tools import tool

from src.models import MealPlannerState, UserProfile, MealPlan
from src.tools import (
    # Analysis only - no execution planning here
    analyze_message_complexity,
    analyze_user_intent,
)


def create_intent_router_subgraph():
    """Router that analyzes messages and determines execution strategy."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [
        analyze_message_complexity,
        analyze_user_intent,
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    ROUTER_PROMPT = """
You are the Intent Router for a meal planning system. Your job is to:

1. Analyze incoming messages for complexity and user intent
2. Route to the appropriate specialized subgraph

Process:
1. First, use analyze_message_complexity to understand request complexity
2. Then, use analyze_user_intent to understand assistance preferences
3. Route based on the analysis results

You are ONLY responsible for analysis and routing - not execution planning.
"""
    
    def router_node(state: MealPlannerState) -> Dict[str, Any]:
        messages = state["messages"]
        
        # Initialize state if needed
        if not state.get("user_profile"):
            state["user_profile"] = UserProfile()
        if not state.get("current_meal_plan"):
            state["current_meal_plan"] = MealPlan()
        
        # Build context for LLM
        llm_messages = [SystemMessage(content=ROUTER_PROMPT)]
        
        # Add all user messages
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        result = llm_with_tools.invoke(llm_messages)
        return {"messages": [result]}
    
    def route_by_analysis(state: MealPlannerState) -> str:
        """Route based on complexity and intent analysis results."""
        last_msg = state["messages"][-1]
        
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            complexity_result = None
            intent_result = None
            
            # Extract analysis results
            for tool_call in last_msg.tool_calls:
                if tool_call["name"] == "analyze_message_complexity":
                    complexity_result = tool_call.get("result", {})
                elif tool_call["name"] == "analyze_user_intent":
                    intent_result = tool_call.get("result", {})
            
            # Route based on complexity first
            if complexity_result and complexity_result.get("complexity") == "complex":
                return "task_coordinator"
            
            # Then route based on intent for simple requests
            if intent_result:
                assistance_level = intent_result.get("assistance_level", "assisted")
                if assistance_level == "manual":
                    return "manual_editor"
                elif assistance_level == "automated":
                    if intent_result.get("calories_mentioned"):
                        return "automated_planner"
                    else:
                        return "info_gatherer"
                else:  # assisted
                    return "automated_planner"
        
        # Default to automated planner for safety
        return "automated_planner"
    
    # Build router subgraph
    router_graph = StateGraph(MealPlannerState)
    router_graph.add_node("router", router_node)
    router_graph.add_node("tools", ToolNode(tools))
    
    router_graph.add_edge(START, "router")
    router_graph.add_conditional_edges("router", tools_condition)
    router_graph.add_edge("tools", "router")
    router_graph.add_conditional_edges("router", route_by_analysis)
    
    return router_graph.compile()