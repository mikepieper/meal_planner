from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from src.models import MealPlannerState
from src.tools import (
    # Only nutrition info extraction - intent analysis handled by router
    extract_nutrition_info
)

def create_info_gatherer_subgraph():
    """Handles progressive disclosure when nutrition information is missing."""
    
    llm = ChatOpenAI(model="gpt-4o")
    tools = [extract_nutrition_info]
    llm_with_tools = llm.bind_tools(tools)
    
    GATHERER_PROMPT = """
You are the Information Gatherer. When users want automated meal planning but haven't
provided key nutrition information, you help gather what's needed.

Your approach:
- Extract any nutrition info from their message using extract_nutrition_info
- Ask for the minimum additional information needed for good recommendations
- Explain why the information helps improve suggestions
- Provide sensible defaults and examples
- Make it easy to proceed even with minimal info

Focus specifically on nutrition-related information: calories, diet type, restrictions.
Don't re-analyze intent - that's already been determined.
"""
    
    def gatherer_node(state: MealPlannerState) -> Dict[str, Any]:
        messages = state["messages"]
        
        llm_messages = [SystemMessage(content=GATHERER_PROMPT)]
        
        # Add user profile context
        if state.get("user_profile"):
            profile = state["user_profile"]
            profile_info = f"Current user info: calories={profile.daily_calories}, diet_type={profile.diet_type}, restrictions={profile.dietary_restrictions}"
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