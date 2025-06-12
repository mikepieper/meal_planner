"""
State utility functions for the meal planning agent.

This module contains reusable helper functions that operate on MealPlannerState
and provide common functionality across different subgraphs.
"""

import json
from typing import Optional
from langchain_core.messages import SystemMessage, AIMessage

from src.models import MealPlannerState


def build_meal_plan_context(state: MealPlannerState) -> Optional[SystemMessage]:
    """
    Build context message from current meal plan if conditions are met.

    Args:
        state: Current agent state containing meal plan

    Returns:
        SystemMessage with meal plan context, or None if conditions not met
    """
    # Only add context if we're not in the middle of a tool execution
    last_msg = state["messages"][-1]
    if not (isinstance(last_msg, AIMessage) and last_msg.tool_calls):
        plan = state["current_meal_plan"]
        if any([plan.breakfast, plan.lunch, plan.dinner, plan.snacks]):
            context = f"Current meal plan status: {json.dumps(plan.model_dump(), default=str, indent=2)}"
            return SystemMessage(content=context)
    return None
