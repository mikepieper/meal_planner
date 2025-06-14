from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
from langgraph.graph import END
from src.models import MealPlannerState

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", temperature=0) 


def should_summarize(state: MealPlannerState) -> str:
    """Determine whether to summarize the conversation or run tools."""
    messages = state.messages
    
    # First check if we need to call tools (this takes priority)
    last_message = messages[-1] if messages else None
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # More nuanced message counting with higher threshold
    non_system_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    
    # Summarize after 10 messages to allow for longer conversations
    if len(non_system_messages) > 10:
        return "summarize"
    
    # Otherwise, we're done with this turn
    return END

def summarize_conversation(state: MealPlannerState) -> dict:
    """Summarize the conversation while preserving meal planning context."""
    summary = state.summary
    messages = state.messages
    
    # More specific prompt that captures what ISN'T in structured state
    if summary:
        summary_prompt = (
            f"Previous conversation summary: {summary}\n\n"
            "Please extend this summary by incorporating the new messages above. "
            "Focus ONLY on information not captured in the meal plan state:\n"
            "- WHY the user made certain choices (reasoning/context)\n"
            "- Options they explicitly rejected and why\n"
            "- Specific brand preferences or cooking methods mentioned\n"
            "- Timing constraints (e.g., 'need lunch to be portable')\n"
            "- Any satisfaction/dissatisfaction with suggestions\n"
            "Do NOT repeat information already in the system like current meals, calories, or dietary restrictions."
        )
    else:
        summary_prompt = (
            "Create a concise summary focusing on context and reasoning. "
            "Capture ONLY:\n"
            "- WHY the user wants certain things (not just what)\n" 
            "- Rejected options and reasoning\n"
            "- Specific preferences about brands, cooking methods, timing\n"
            "- User's reactions to suggestions\n"
            "Skip facts already stored (meals planned, calories, restrictions)."
        )
    
    # Add the summarization prompt to messages
    summarization_messages = messages + [HumanMessage(content=summary_prompt)]
    
    # Get summary from LLM (using base model without tools)
    response = llm.invoke(summarization_messages)
    
    # Keep only the 4 most recent messages (leaving room before next summarization)
    delete_messages = [RemoveMessage(id=m.id) for m in messages[:-4]]
    
    return {
        "summary": response.content,
        "messages": delete_messages
    }
