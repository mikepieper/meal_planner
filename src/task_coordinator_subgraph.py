from typing import Dict, Any, Optional, List
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage, ToolMessage

from src.models import MealPlannerState, UserProfile, MealPlan
from src.tools import create_execution_plan


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