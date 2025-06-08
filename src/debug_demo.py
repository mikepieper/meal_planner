"""
Debug Demo Script for Meal Planning Agent
=========================================

Run this to debug the agent message flow.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Set up LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "meal-planner-debug"

from meal_planner.main_agent import create_meal_planning_agent, MealPlannerState
from meal_planner.nutrition_optimizer import MealPlan
from meal_planner.food_database import get_food_database
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage


def print_messages(messages, title="Messages"):
    """Debug print all messages."""
    print(f"\n=== {title} ===")
    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__
        print(f"{i}: {msg_type}")
        if hasattr(msg, 'content'):
            print(f"   Content: {msg.content[:100]}...")
        if hasattr(msg, 'tool_calls'):
            print(f"   Tool calls: {msg.tool_calls}")
        if isinstance(msg, ToolMessage):
            print(f"   Tool call ID: {msg.tool_call_id}")
    print("=" * 50)


def main():
    """Run a debug conversation with the meal planning agent."""
    print("🍽️  Meal Planning Agent Debug Demo")
    print("=" * 50)
    
    # Create the agent
    agent = create_meal_planning_agent()
    
    # Initialize state
    state = {
        "messages": [],
        "current_meal_plan": MealPlan(),
        "user_profile": {},
        "food_database": get_food_database(),
        "conversation_phase": "gathering_info",
        "optimization_history": []
    }
    
    # Configuration for conversation thread
    config = {"configurable": {"thread_id": "debug_session"}}
    
    # First message
    message = "Hi! I'm vegetarian and trying to build muscle. I need about 2200 calories per day with high protein."
    print(f"\n👤 User: {message}")
    
    # Add user message to state
    state["messages"].append(HumanMessage(content=message))
    
    # Debug: Print state messages before invoke
    print_messages(state["messages"], "State messages BEFORE invoke")
    
    # Get agent response
    try:
        # Get the graph structure
        graph = agent.get_graph()
        print("\nGraph nodes:", list(graph.nodes))
        print("Graph edges:", list(graph.edges))
        
        # Invoke the agent
        response = agent.invoke(state, config)
        
        # Debug: Print response messages
        print_messages(response["messages"], "Response messages AFTER invoke")
        
        agent_message = response["messages"][-1].content
        print(f"\n🤖 Agent: {agent_message[:200]}...")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
    
    print("\n✅ First turn completed!")
    
    # Try a second turn that might trigger tool use
    if 'response' in locals():
        print("\n" + "="*50)
        print("Testing second turn with tool-triggering message...")
        
        # Update state with response
        state = response
        
        # Add another message that should trigger tool use
        message2 = "Yes, please set my nutrition goals for 2200 calories with high protein."
        print(f"\n👤 User: {message2}")
        state["messages"].append(HumanMessage(content=message2))
        
        print_messages(state["messages"], "State messages BEFORE second invoke")
        
        try:
            response2 = agent.invoke(state, config)
            print_messages(response2["messages"], "Response messages AFTER second invoke")
            
            agent_message2 = response2["messages"][-1].content
            print(f"\n🤖 Agent: {agent_message2[:200]}...")
            
        except Exception as e:
            print(f"\n❌ Error on second turn: {str(e)}")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
    
    print("\n✅ Debug completed!")
    

if __name__ == "__main__":
    main() 