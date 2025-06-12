from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from src.models import MealPlannerState
from src.intent_router_subgraph import create_intent_router_subgraph
from src.task_coordinator_subgraph import create_task_coordinator_subgraph
from src.manual_editor_subgraph import create_manual_editor_subgraph
from src.automated_planner_subgraph import create_automated_planner_subgraph
from src.info_gatherer_subgraph import create_info_gatherer_subgraph

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