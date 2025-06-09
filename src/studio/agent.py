from typing import Dict, Any, Optional, List
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage, ToolMessage

from src.models import MealPlannerState, UserProfile, MealPlan
from src.tools import (
    # Analysis & Planning
    analyze_message_complexity,
    create_execution_plan,
    analyze_user_intent,
    extract_nutrition_info,
    # Meal Management
    add_meal_item,
    remove_meal_item,
    update_meal_item,
    clear_meal,
    clear_meal_plan,
    add_multiple_meal_items,
    # Nutrition & Generation
    set_nutrition_goals,
    generate_meal_suggestions
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

# ====== SPECIALIZED SUBGRAPHS ======

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

def create_task_coordinator_subgraph():
    """Coordinates execution of complex multi-step plans."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [create_execution_plan]
    llm_with_tools = llm.bind_tools(tools)
    
    COORDINATOR_PROMPT = """
You are the Task Coordinator. You receive complexity analysis and create execution plans
for multi-intent meal planning requests.

Your job is to:
1. Create detailed execution plans
2. Coordinate sequential vs parallel execution
3. Manage dependencies between tasks
4. Route to appropriate specialized subgraphs

Use create_execution_plan to structure complex requests.
"""
    
    def coordinator_node(state: MealPlannerState) -> Dict[str, Any]:
        messages = state["messages"]
        
        llm_messages = [SystemMessage(content=COORDINATOR_PROMPT)]
        
        # Include recent context
        for msg in messages[-3:]:  # Last 3 messages for context
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        result = llm_with_tools.invoke(llm_messages)
        return {"messages": [result]}
    
    def route_to_executor(state: MealPlannerState) -> str:
        """Route to appropriate execution strategy."""
        last_msg = state["messages"][-1]
        
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            for tool_call in last_msg.tool_calls:
                if tool_call["name"] == "create_execution_plan":
                    # We have an execution plan, route to parallel coordinator
                    return "parallel_coordinator"
        
        return "sequential_executor"
    
    # Build coordinator subgraph
    coord_graph = StateGraph(MealPlannerState)
    coord_graph.add_node("coordinator", coordinator_node)
    coord_graph.add_node("tools", ToolNode(tools))
    
    coord_graph.add_edge(START, "coordinator")
    coord_graph.add_conditional_edges("coordinator", tools_condition)
    coord_graph.add_edge("tools", "coordinator")
    coord_graph.add_conditional_edges("coordinator", route_to_executor)
    
    return coord_graph.compile()

def create_manual_editor_subgraph():
    """Handles direct meal plan modifications."""
    
    llm = ChatOpenAI(model="gpt-4o")
    tools = [add_meal_item, remove_meal_item, update_meal_item, clear_meal, clear_meal_plan, add_multiple_meal_items]
    llm_with_tools = llm.bind_tools(tools)
    
    EDITOR_PROMPT = """
You are the Manual Meal Editor. Handle direct modifications to meal plans.

Available operations:
- Add/remove/update individual meal items
- Clear meals or entire meal plan
- Add multiple items at once

Be precise and confirmatory in your responses.
Focus on the exact operations requested.
"""
    
    def editor_node(state: MealPlannerState) -> Dict[str, Any]:
        messages = state["messages"]
        
        llm_messages = [SystemMessage(content=EDITOR_PROMPT)]
        
        # Add meal plan context
        context_msg = _build_meal_plan_context(state, messages)
        if context_msg:
            llm_messages.append(context_msg)
        
        # Add recent messages
        for msg in messages[-2:]:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        result = llm_with_tools.invoke(llm_messages)
        return {"messages": [result]}
    
    # Build editor subgraph
    editor_graph = StateGraph(MealPlannerState)
    editor_graph.add_node("editor", editor_node)
    editor_graph.add_node("tools", ToolNode(tools))
    
    editor_graph.add_edge(START, "editor")
    editor_graph.add_conditional_edges("editor", tools_condition)
    editor_graph.add_edge("tools", "editor")
    editor_graph.add_edge("editor", END)
    
    return editor_graph.compile()

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
            profile_context = f"User's nutrition goals: {json.dumps(state['user_profile'].nutrition_goals.dict(), default=str)}"
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

def create_info_gatherer_subgraph():
    """Handles progressive disclosure when information is missing."""
    
    llm = ChatOpenAI(model="gpt-4o")
    tools = [extract_nutrition_info, analyze_user_intent]
    llm_with_tools = llm.bind_tools(tools)
    
    GATHERER_PROMPT = """
You are the Information Gatherer. When users want automated suggestions but haven't
provided enough information, you guide them through progressive disclosure.

Your approach:
- Ask for the minimum information needed
- Explain why the information helps
- Provide options and examples
- Make it easy to proceed without full details

Don't be pushy - respect if users want to proceed with defaults.
"""
    
    def gatherer_node(state: MealPlannerState) -> Dict[str, Any]:
        messages = state["messages"]
        
        llm_messages = [SystemMessage(content=GATHERER_PROMPT)]
        
        # Add user profile context
        if state.get("user_profile"):
            profile = state["user_profile"]
            profile_info = f"Current user info: calories={profile.daily_calories}, diet_type={profile.diet_type}"
            llm_messages.append(SystemMessage(content=profile_info))
        
        # Add recent messages
        for msg in messages[-2:]:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        result = llm_with_tools.invoke(llm_messages)
        return {"messages": [result]}
    
    # Build gatherer subgraph
    gatherer_graph = StateGraph(MealPlannerState)
    gatherer_graph.add_node("gatherer", gatherer_node)
    gatherer_graph.add_node("tools", ToolNode(tools))
    
    gatherer_graph.add_edge(START, "gatherer")
    gatherer_graph.add_conditional_edges("gatherer", tools_condition)
    gatherer_graph.add_edge("tools", "gatherer")
    gatherer_graph.add_edge("gatherer", END)
    
    return gatherer_graph.compile()

# ====== MAIN COORDINATION GRAPH ======

def create_meal_planning_agent():
    """Main coordination graph that routes to specialized subgraphs."""
    
    # Create specialized subgraphs
    intent_router = create_intent_router_subgraph()
    task_coordinator = create_task_coordinator_subgraph()
    manual_editor = create_manual_editor_subgraph()
    automated_planner = create_automated_planner_subgraph()
    info_gatherer = create_info_gatherer_subgraph()
    
    def route_by_intent(state: MealPlannerState) -> str:
        """Route based on intent analysis and complexity."""
        messages = state["messages"]
        
        # Look for the most recent intent analysis
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call["name"] == "analyze_user_intent":
                        intent_result = tool_call.get("result", {})
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
                    
                    elif tool_call["name"] == "analyze_message_complexity":
                        complexity_result = tool_call.get("result", {})
                        if complexity_result.get("complexity") == "complex":
                            return "task_coordinator"
        
        # Default routing based on message patterns
        last_user_msg = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content.lower()
                break
        
        if last_user_msg:
            if any(word in last_user_msg for word in ["add", "remove", "delete", "clear"]):
                return "manual_editor"
            elif any(word in last_user_msg for word in ["create", "make", "generate", "suggest"]):
                return "automated_planner"
        
        return "automated_planner"  # Default
    
    # Build main coordination graph
    main_graph = StateGraph(MealPlannerState)
    
    # Add subgraph nodes
    main_graph.add_node("intent_router", intent_router)
    main_graph.add_node("task_coordinator", task_coordinator)
    main_graph.add_node("manual_editor", manual_editor)
    main_graph.add_node("automated_planner", automated_planner)
    main_graph.add_node("info_gatherer", info_gatherer)
    
    # Set up routing
    main_graph.add_edge(START, "intent_router")
    main_graph.add_conditional_edges("intent_router", route_by_intent)
    
    # All subgraphs end at END
    main_graph.add_edge("task_coordinator", END)
    main_graph.add_edge("manual_editor", END)
    main_graph.add_edge("automated_planner", END)
    main_graph.add_edge("info_gatherer", END)
    
    return main_graph.compile()

# Create and export the graph
graph = create_meal_planning_agent()

# This is what LangGraph Studio will load
__all__ = ["graph"] 