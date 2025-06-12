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
You are the Task Coordinator. You receive complex multi-intent requests and:

1. Create detailed execution plans using create_execution_plan
2. Analyze the plan to determine the best execution strategy
3. Provide a comprehensive response that addresses all aspects of the request

Since this is a complex request, provide a thorough response that covers:
- Acknowledgment of the multiple intents
- Step-by-step breakdown of what will be addressed
- Specific actions or recommendations for each intent
- Clear next steps for the user

You should handle the complexity here rather than routing to other subgraphs.
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
    
    # Build coordinator subgraph - simplified to handle complexity internally
    coord_graph = StateGraph(MealPlannerState)
    coord_graph.add_node("coordinator", coordinator_node)
    coord_graph.add_node("tools", ToolNode(tools))
    
    coord_graph.add_edge(START, "coordinator")
    coord_graph.add_conditional_edges("coordinator", tools_condition)
    coord_graph.add_edge("tools", "coordinator")
    coord_graph.add_edge("coordinator", END)
    
    return coord_graph.compile()