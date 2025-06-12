from typing import Dict, Any, Optional, List
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage, ToolMessage

from src.models import MealPlannerState, UserProfile, MealPlan
from src.state_utils import build_meal_plan_context
from src.tools import (
    add_meal_item,
    remove_meal_item,
    update_meal_item,
    clear_meal,
    clear_meal_plan,
    add_multiple_meal_items
)


def create_manual_editor_subgraph():
    """Handles direct meal plan modifications."""
    
    llm = ChatOpenAI(model="gpt-4o")
    tools = [
        add_meal_item,
        remove_meal_item,
        update_meal_item,
        clear_meal,
        clear_meal_plan,
        add_multiple_meal_items
    ]
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
        context_msg = build_meal_plan_context(state)
        if context_msg:
            llm_messages.append(context_msg)
        
        # Add recent messages
        # Only use the last 2 messages to keep context focused and manageable:
        # - Usually includes the user's current request and the previous response
        # - Prevents token limit issues from long conversation history
        # - Manual editing tasks typically only need immediate context
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