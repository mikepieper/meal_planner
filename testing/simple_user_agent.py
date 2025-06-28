"""Improved simplified user simulation agent with better abstraction."""

from typing import List, Optional, Any, Dict, Callable
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
import os

from src.testing.test_scenarios import TestScenario, UserPersona, ConversationGoal


class SimpleUserState(BaseModel):
    """Simplified state for user simulation agent - only essential fields."""
    
    # Core test data
    scenario: TestScenario
    
    # Conversation tracking
    messages: List[BaseMessage] = Field(default_factory=list)
    turn_count: int = 0
    
    # Success tracking
    goal_achieved: bool = False
    
    # Control flags
    should_end: bool = False
    end_reason: Optional[str] = None


class UserAgentConfig(BaseModel):
    """Configuration for user agent behavior."""
    
    # LLM settings
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_context_messages: int = 6
    
    # Evaluation settings
    use_llm_goal_evaluation: bool = True
    use_llm_end_detection: bool = True


def generate_opening_message(scenario: TestScenario, persona: UserPersona) -> str:
    """Generate opening message using LLM instead of hardcoded strings."""
    
    # Use a simple LLM call to generate contextual opening
    anthropic_key = os.getenv("ANTHROPIC_KEY") or os.getenv("ANTHROPIC_API_KEY")
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0.7, api_key=anthropic_key)
    
    prompt = f"""Generate a realistic opening message for a user interacting with a meal planning chatbot.

USER PROFILE:
- Name: {persona.name}
- Communication style: {persona.communication_style}
- Dietary restrictions: {', '.join(persona.dietary_restrictions) if persona.dietary_restrictions else 'None'}

GOAL: {scenario.goal.value}
SPECIFIC TASK: {scenario.specific_requirements.get('task', 'General goal pursuit')}
REQUIREMENTS: {scenario.specific_requirements}

Generate a single, direct opening message as {persona.name} would say it. Be {persona.communication_style}.
- Don't ask questions, make statements/demands
- Focus on what you need, not being polite
- Keep it natural and realistic
- One sentence preferred

Examples:
- Direct: "I need a meal plan for today"
- Chatty: "Hi there, I'm Sarah and I need help planning my weekly meals"
- Uncertain: "Um, I think I need help with my breakfast options"

Opening message:"""

    response = llm.invoke([SystemMessage(content=prompt)])
    content = response.content if isinstance(response.content, str) else response.content[0].text
    return content.strip().strip('"').strip("'")


def check_goal_achievement(state: SimpleUserState, config: UserAgentConfig) -> bool:
    """Check if goal has been achieved using LLM evaluation."""
    
    if state.goal_achieved:
        return True
    
    if not state.messages or not config.use_llm_goal_evaluation:
        return False
    
    # Use LLM to evaluate goal achievement
    anthropic_key = os.getenv("ANTHROPIC_KEY") or os.getenv("ANTHROPIC_API_KEY")
    llm = ChatAnthropic(model=config.model, temperature=0.3, api_key=anthropic_key)  # Lower temp for evaluation
    
    # Get recent conversation for context
    recent_messages = state.messages[-4:] if len(state.messages) > 4 else state.messages
    conversation_text = "\n".join([
        f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
        for msg in recent_messages
    ])
    
    prompt = f"""Evaluate if the user's goal has been achieved based on this conversation.

USER'S GOAL: {state.scenario.goal.value}
SPECIFIC TASK: {state.scenario.specific_requirements.get('task', 'General goal completion')}
SUCCESS CRITERIA: {state.scenario.success_criteria if hasattr(state.scenario, 'success_criteria') else 'Task completion'}

RECENT CONVERSATION:
{conversation_text}

Has the user's goal been achieved? Consider:
- Did the assistant provide what the user requested?
- Are the user's requirements met?
- Would a reasonable user consider this task complete?

Respond with only "YES" or "NO":"""

    response = llm.invoke([SystemMessage(content=prompt)])
    result = response.content.strip().upper()
    return result == "YES"


def check_conversation_end(state: SimpleUserState, config: UserAgentConfig) -> tuple[bool, Optional[str]]:
    """Check if conversation should end using LLM intent detection."""
    
    # Check basic end conditions
    if state.goal_achieved:
        return True, "goal_achieved"
    
    if state.turn_count >= state.scenario.max_turns:
        return True, "max_turns_reached"
    
    if not state.messages:
        return False, None
    
    # Use LLM to detect user intent to end conversation
    if config.use_llm_end_detection:
        last_user_msg = ""
        for msg in reversed(state.messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break
        
        if last_user_msg:
            anthropic_key = os.getenv("ANTHROPIC_KEY") or os.getenv("ANTHROPIC_API_KEY")
            llm = ChatAnthropic(model=config.model, temperature=0.3, api_key=anthropic_key)
            
            prompt = f"""Analyze this user message to determine if they want to end the conversation.

USER MESSAGE: "{last_user_msg}"

Does the user want to end/exit/stop the conversation? Consider:
- Explicit ending phrases (goodbye, bye, done, etc.)
- Expressions of frustration leading to giving up
- Statements indicating they're finished
- Dismissive language suggesting they want to quit

Respond with only "YES" or "NO":"""

            response = llm.invoke([SystemMessage(content=prompt)])
            result = response.content.strip().upper()
            if result == "YES":
                return True, "user_ended"
    
    return False, None


def create_simple_user_agent(config: UserAgentConfig = None) -> Any:
    """Create a simplified user simulation agent with configurable behavior."""
    
    if config is None:
        config = UserAgentConfig()
    
    # Initialize LLM
    anthropic_key = os.getenv("ANTHROPIC_KEY") or os.getenv("ANTHROPIC_API_KEY")
    llm = ChatAnthropic(model=config.model, temperature=config.temperature, api_key=anthropic_key)
    
    def generate_user_response(state: SimpleUserState) -> Dict[str, Any]:
        """Generate the next user message - cleaner version."""
        
        scenario = state.scenario
        persona = scenario.persona
        
        # Build context about the user's situation
        context_parts = []
        
        if persona.dietary_restrictions:
            context_parts.append(f"Dietary restrictions: {', '.join(persona.dietary_restrictions)}")
        
        if scenario.specific_requirements:
            req_text = ", ".join([f"{k}: {v}" for k, v in scenario.specific_requirements.items() 
                                if k not in ['task', 'success_indicators']])
            if req_text:
                context_parts.append(f"Requirements: {req_text}")
        
        context = "\n".join(context_parts) if context_parts else "No special requirements"
        
        # Clean, focused prompt
        system_prompt = f"""You are {persona.name}, a real user seeking help from a meal planning chatbot.

BACKGROUND:
{context}

GOAL: {scenario.goal.value}
TASK: {scenario.specific_requirements.get('task', 'Achieve your goal')}

TURN: {state.turn_count + 1}/{scenario.max_turns}

COMMUNICATION STYLE: {persona.communication_style}
- Direct: Brief, to-the-point statements
- Chatty: Conversational, adds context and personality  
- Uncertain: Hesitant, seeks reassurance

BEHAVIOR:
- Focus on YOUR needs, not helping the bot
- Make statements/demands rather than questions
- Be realistic - show mild frustration if progress is slow
- Respond to what the bot actually said

Generate your next response as {persona.name}:"""

        # Add conversation context
        messages = [SystemMessage(content=system_prompt)]
        recent_messages = state.messages[-config.max_context_messages:] if len(state.messages) > config.max_context_messages else state.messages
        messages.extend(recent_messages)
        
        # Generate response
        response = llm.invoke(messages)
        response_content = response.content if isinstance(response.content, str) else response.content[0].text
        
        # Check goal achievement
        goal_achieved = check_goal_achievement(state, config)
        
        return {
            "messages": state.messages + [HumanMessage(content=response_content)],
            "turn_count": state.turn_count + 1,
            "goal_achieved": goal_achieved
        }
    
    def check_should_end(state: SimpleUserState) -> Dict[str, Any]:
        """Check if conversation should end."""
        should_end, end_reason = check_conversation_end(state, config)
        
        return {
            "should_end": should_end,
            "end_reason": end_reason
        }
    
    # Build graph
    graph = StateGraph(SimpleUserState)
    
    graph.add_node("generate_response", generate_user_response)
    graph.add_node("check_end", check_should_end)
    
    graph.add_edge(START, "generate_response")
    graph.add_edge("generate_response", "check_end")
    graph.add_edge("check_end", END)
    
    return graph.compile()


def initialize_simple_user_state(scenario: TestScenario) -> SimpleUserState:
    """Initialize user state with dynamically generated opening message."""
    
    # Generate opening message using LLM instead of hardcoded strings
    opening_message = (
        scenario.specific_requirements.get('opening_message') 
        or generate_opening_message(scenario, scenario.persona)
    )
    
    return SimpleUserState(
        scenario=scenario,
        messages=[HumanMessage(content=opening_message)]
    )


def create_custom_config(**kwargs) -> UserAgentConfig:
    """Helper to create custom user agent configuration."""
    return UserAgentConfig(**kwargs)


# Create default agent instance
simple_user_agent = create_simple_user_agent()

__all__ = [
    "simple_user_agent", 
    "SimpleUserState", 
    "UserAgentConfig",
    "initialize_simple_user_state", 
    "create_simple_user_agent",
    "create_custom_config"
] 