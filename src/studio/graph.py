"""
LangGraph Studio Graph Definition
=================================

This module exports the meal planning agent graph for use in LangGraph Studio.
"""

import os
import sys
from pathlib import Path

# Add parent directory to Python path so we can import our modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Set up environment
from dotenv import load_dotenv
load_dotenv()

# Import our agent
from main_agent import create_meal_planning_agent

# Create and export the graph
graph = create_meal_planning_agent()

# This is what LangGraph Studio will load
__all__ = ["graph"] 