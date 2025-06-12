from typing import Dict, Any, Optional, List
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

from src.models import MealPlannerState, UserProfile, MealPlan
from src.tools import (
    # Analysis & Planning
    analyze_message_complexity,
    create_execution_plan,
    analyze_user_intent,
    extract_nutrition_info,
)

llm = ChatOpenAI(model="gpt-4o", temperature=0)

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
    
    response = llm.invoke(prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "intent_count": 1,
            "complexity": "simple", 
            "needs_planning": False,
            "intents": [{"type": "meal_modification", "description": "Single request", "dependencies": [], "can_parallelize": False}]
        }


def create_intent_router_subgraph():
    """Router that analyzes messages and determines execution strategy."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [analyze_message_complexity, create_execution_plan, analyze_user_intent, extract_nutrition_info]
    llm_with_tools = llm.bind_tools(tools)
    
    ROUTER_PROMPT = """
You are the Intent Router for a meal planning system. Your job is to:

1. Analyze incoming messages for complexity and multiple intents
2. Determine the appropriate execution strategy 
3. Route to specialized subgraphs

For simple single-intent messages, route directly.
For complex multi-intent messages, create an execution plan first.

Always use analyze_message_complexity as your first step.
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
    
    def route_by_complexity(state: MealPlannerState) -> str:
        """Route based on complexity analysis results."""
        last_msg = state["messages"][-1]
        
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            # Look for complexity analysis results
            for tool_call in last_msg.tool_calls:
                if tool_call["name"] == "analyze_message_complexity":
                    # We have complexity analysis, next step depends on complexity
                    return "task_coordinator"
                elif tool_call["name"] == "analyze_user_intent":
                    # Simple intent analysis, route directly
                    return "direct_router"
        
        # Default to task coordinator for safety
        return "task_coordinator"
    
    # Build router subgraph
    router_graph = StateGraph(MealPlannerState)
    router_graph.add_node("router", router_node)
    router_graph.add_node("tools", ToolNode(tools))
    
    router_graph.add_edge(START, "router")
    router_graph.add_conditional_edges("router", tools_condition)
    router_graph.add_edge("tools", "router")
    router_graph.add_conditional_edges("router", route_by_complexity)
    
    return router_graph.compile()