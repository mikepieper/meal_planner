from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
from langgraph.graph import END
from src.models import MealPlannerState

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0) 

# Configuration: Set to False if frontend doesn't support RemoveMessage
USE_REMOVE_MESSAGE = False  # Set to True when LangGraph Studio supports RemoveMessage


def should_summarize_conversation(state: MealPlannerState) -> bool:
    """Determine whether the conversation should be summarized.
    
    This is now separate from tool routing and focuses purely on conversation management.
    Uses smarter heuristics than just message count.
    
    Args:
        state: The current state of the conversation
        
    Returns:
        True if conversation should be summarized, False otherwise
    """
    messages = state.messages
    
    # Don't summarize if there are too few messages
    non_system_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    if len(non_system_messages) < 8:  # Lowered from 10, but still reasonable minimum
        return False
    
    # Always summarize if we have a lot of messages
    if len(non_system_messages) > 15:  # Hard limit to prevent token overflow
        return True
    
    # Smart heuristics: summarize if we've had substantial back-and-forth
    # Count user messages (HumanMessage) to gauge conversation depth
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    
    # If we've had 4+ user interactions, consider summarizing
    if len(user_messages) >= 4 and len(non_system_messages) >= 10:
        return True
    
    # Look for conversation phase changes (e.g., moved from setup to planning to adjustments)
    # This is a simple heuristic - could be made more sophisticated
    recent_messages = non_system_messages[-6:]  # Look at last 6 messages
    has_profile_updates = any("profile" in str(m).lower() or "dietary" in str(m).lower() 
                             for m in recent_messages)
    has_meal_planning = any("meal" in str(m).lower() or "add" in str(m).lower() 
                           for m in recent_messages)
    
    # If we've covered multiple conversation phases, summarize
    if has_profile_updates and has_meal_planning and len(non_system_messages) >= 8:
        return True
    
    return False


def summarize_conversation(state: MealPlannerState) -> dict:
    """Summarize the conversation while preserving meal planning context.
    
    This is now focused purely on passive fact gathering and context preservation,
    not blocking the main conversation flow.
    """
    summary = state.summary
    messages = state.messages
    
    # More specific prompt that captures what ISN'T in structured state
    if summary:
        summary_prompt = (
            f"Previous conversation summary: {summary}\n\n"
            "Please extend this summary by incorporating the new messages above. "
            "Focus ONLY on information not captured in the meal plan state:\n"
            "- User's reasoning and preferences (why they want certain things)\n"
            "- Options they explicitly rejected and their reasons\n"
            "- Specific brand preferences, cooking methods, or timing constraints\n"
            "- Satisfaction/dissatisfaction with suggestions and feedback\n"
            "- Context about their lifestyle, schedule, or cooking situation\n"
            "- Personal anecdotes or background that influences their choices\n\n"
            "Do NOT repeat information already stored in the system like current meals, "
            "calorie goals, or dietary restrictions. Keep it concise but capture the 'why' behind decisions."
        )
    else:
        summary_prompt = (
            "Create a concise summary focusing on context, reasoning, and user preferences. "
            "Capture ONLY information that provides context for future interactions:\n\n"
            "- WHY the user wants certain things (not just what they want)\n" 
            "- Rejected options and their reasoning\n"
            "- Specific preferences about preparation, brands, timing, etc.\n"
            "- User's reactions to suggestions and feedback\n"
            "- Lifestyle context that influences their choices\n"
            "- Personal background relevant to meal planning\n\n"
            "Skip facts already stored in the system (current meals, calories, restrictions). "
            "Focus on the reasoning and context that helps personalize future interactions."
        )
    
    # Add the summarization prompt to messages
    summarization_messages = messages + [HumanMessage(content=summary_prompt)]
    
    # Get summary from LLM (using base model without tools)
    response = llm.invoke(summarization_messages)
    
    # Handle message history management based on frontend support
    if USE_REMOVE_MESSAGE:
        # Use RemoveMessage when frontend supports it (more efficient)
        messages_to_keep = 6
        if len(messages) > messages_to_keep:
            delete_messages = [RemoveMessage(id=m.id) for m in messages[:-messages_to_keep]]
        else:
            delete_messages = []
        
        return {
            "summary": response.content,
            "messages": delete_messages
        }
    else:
        # Fallback: Keep only recent messages (when RemoveMessage not supported)
        messages_to_keep = 6
        if len(messages) > messages_to_keep:
            recent_messages = messages[-messages_to_keep:]
        else:
            recent_messages = messages
        
        return {
            "summary": response.content,
            "messages": recent_messages  # Replace entire message list with recent ones
        }
