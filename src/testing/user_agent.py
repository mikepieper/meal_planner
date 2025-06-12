"""User simulation agent for automated testing."""

from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
import random

from src.testing.test_scenarios import TestScenario, UserPersona, ConversationGoal


class UserAgentState(BaseModel):
    """State for the user simulation agent."""
    # Test scenario being executed
    scenario: TestScenario
    
    # Conversation with the chatbot
    messages: List[BaseMessage] = Field(default_factory=list)
    
    # Current conversation turn
    turn_count: int = 0
    
    # Tracking goal progress
    goal_progress: Dict[str, bool] = Field(default_factory=dict)
    goal_achieved: bool = False
    
    # User's internal state
    satisfaction_level: float = 1.0  # 0-1 scale
    confusion_level: float = 0.0  # 0-1 scale
    impatience_level: float = 0.0  # 0-1 scale
    
    # Conversation metadata
    asked_for_clarification: int = 0
    received_suggestions: List[str] = Field(default_factory=list)
    made_decisions: List[str] = Field(default_factory=list)
    encountered_issues: List[str] = Field(default_factory=list)
    
    # Control flags
    should_end: bool = False
    end_reason: Optional[str] = None


def create_user_agent():
    """Create a user simulation agent."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    def generate_user_response(state: UserAgentState) -> Dict[str, Any]:
        """Generate the next user message based on persona and conversation state."""
        
        scenario = state.scenario
        persona = scenario.persona
        
        # Build the prompt for the user agent
        system_prompt = f"""You are simulating a REAL USER named {persona.name} who NEEDS HELP from a meal planning chatbot.

PERSONA DETAILS:
- Age: {persona.age}
- Dietary Restrictions: {', '.join(persona.dietary_restrictions) if persona.dietary_restrictions else 'None'}
- Preferences: {', '.join(persona.preferences)}
- Health Goals: {', '.join(persona.health_goals)}
- Cooking Skill: {persona.cooking_skill}
- Time Constraints: {persona.time_constraints or 'None'}
- Budget Conscious: {'Yes' if persona.budget_conscious else 'No'}
- Family Size: {persona.family_size}
- Communication Style: {persona.communication_style}
- Decision Making: {persona.decision_making}
- Tech Savviness: {persona.tech_savviness}

YOUR GOAL: {scenario.goal.value}
SPECIFIC REQUIREMENTS: {scenario.specific_requirements}

CURRENT STATE:
- Turn: {state.turn_count + 1}/{scenario.max_turns}
- Satisfaction: {state.satisfaction_level:.1f}
- Confusion: {state.confusion_level:.1f}
- Impatience: {state.impatience_level:.1f}

CRITICAL RULES - YOU ARE THE USER WHO NEEDS HELP:

1. **You are NOT helpful or accommodating** - you have your own needs and problems to solve
2. **You do NOT offer help to the chatbot** - the chatbot should help YOU
3. **You are focused on YOUR goal** - be demanding about getting what you need
4. **You are realistic and sometimes difficult** - real users aren't always pleasant
5. **You don't say "let me know if you need anything"** - YOU need things from the bot

BEHAVIORAL GUIDELINES:

1. **Communication Style**:
   - Direct: "I need X. Can you do that or not?"
   - Chatty: "So I'm trying to do X because Y, and I really need help with Z..."
   - Uncertain: "I think I need X? But I'm not sure if that's right..."

2. **Decision Making**:
   - Decisive: Make quick choices, move forward fast
   - Indecisive: "Actually, wait, maybe not that... what about...?"
   - Exploratory: "What are my other options? I want to see everything first"

3. **Emotional Responses**:
   - If confused: "I don't understand what you mean" or "That doesn't make sense"
   - If impatient: "This is taking too long" or "Can we just get to the point?"
   - If satisfied: "Perfect, that's exactly what I wanted" or "Great, what's next?"

4. **User Behavior**:
   - Push for what you want: "But I specifically said I need..."
   - Question unclear responses: "What do you mean by that?"
   - Redirect when off-topic: "That's not what I asked for"
   - Express frustration when appropriate: "This isn't working for me"

5. **Goal-Oriented**:
   - Keep pushing toward your specific goal
   - Don't get sidetracked by the bot's agenda
   - Express what you actually need, not what's polite

Remember: You're a REAL PERSON with problems to solve, not a customer service representative. Be authentic to {persona.name}'s personality and current emotional state. NEVER offer help to the chatbot - YOU are the one who needs help.

Generate ONLY your next message as {persona.name} would realistically say it."""

        # Add conversation history
        messages = [SystemMessage(content=system_prompt)]
        
        # Include recent conversation (limit to prevent token issues)
        for msg in state.messages[-10:]:
            messages.append(msg)
        
        # Get response
        response = llm.invoke(messages)
        
        # Update emotional state based on conversation
        new_state = update_emotional_state(state, response.content)
        
        return {
            "messages": state.messages + [HumanMessage(content=response.content)],
            **new_state
        }
    
    def update_emotional_state(state: UserAgentState, user_message: str) -> Dict[str, Any]:
        """Update user's emotional state based on conversation progress."""
        
        updates = {}
        
        # Check for confusion indicators
        confusion_phrases = ["don't understand", "confused", "not sure", "what do you mean", "can you explain"]
        if any(phrase in user_message.lower() for phrase in confusion_phrases):
            updates["confusion_level"] = min(1.0, state.confusion_level + 0.2)
            updates["asked_for_clarification"] = state.asked_for_clarification + 1
        
        # Check for impatience indicators
        if state.turn_count > state.scenario.max_turns * 0.7 and not state.goal_achieved:
            updates["impatience_level"] = min(1.0, state.impatience_level + 0.1)
        
        # Check for satisfaction indicators
        satisfaction_phrases = ["great", "perfect", "exactly", "thank you", "that's helpful"]
        if any(phrase in user_message.lower() for phrase in satisfaction_phrases):
            updates["satisfaction_level"] = min(1.0, state.satisfaction_level + 0.1)
            updates["confusion_level"] = max(0.0, state.confusion_level - 0.1)
        
        return updates
    
    def check_goal_progress(state: UserAgentState) -> Dict[str, Any]:
        """Analyze conversation to check goal progress."""
        
        scenario = state.scenario
        last_messages = state.messages[-4:] if len(state.messages) >= 4 else state.messages
        
        progress_prompt = f"""Analyze this conversation excerpt to determine goal progress.

GOAL: {scenario.goal.value}
SUCCESS CRITERIA: {scenario.success_criteria}

RECENT CONVERSATION:
{format_messages(last_messages)}

For each success criterion, determine if it has been met.
Also determine if the overall goal has been achieved.

Respond with a JSON object like:
{{
    "criteria_met": {{
        "criterion_1": true/false,
        "criterion_2": true/false
    }},
    "goal_achieved": true/false,
    "progress_notes": "Brief explanation"
}}"""

        response = llm.invoke([SystemMessage(content=progress_prompt)])
        
        # Parse response (in real implementation, use proper JSON parsing)
        # For now, simple heuristic
        goal_achieved = "goal_achieved\": true" in response.content
        
        return {
            "goal_achieved": goal_achieved,
            "turn_count": state.turn_count + 1
        }
    
    def should_end_conversation(state: UserAgentState) -> Dict[str, Any]:
        """Determine if the conversation should end."""
        
        should_end = False
        end_reason = None
        
        # Check various end conditions
        if state.goal_achieved:
            should_end = True
            end_reason = "goal_achieved"
        elif state.turn_count >= state.scenario.max_turns:
            should_end = True
            end_reason = "max_turns_reached"
        elif state.satisfaction_level < 0.2 and state.turn_count > 5:
            should_end = True
            end_reason = "user_frustrated"
        elif state.confusion_level > 0.8:
            should_end = True
            end_reason = "too_confused"
        
        # Check if user expressed intent to end
        if state.messages:
            last_user_msg = get_last_user_message(state.messages)
            if last_user_msg:
                end_phrases = ["goodbye", "thanks bye", "that's all", "i'm done", "nevermind"]
                if any(phrase in last_user_msg.lower() for phrase in end_phrases):
                    should_end = True
                    end_reason = "user_ended"
        
        return {
            "should_end": should_end,
            "end_reason": end_reason
        }
    
    # Build the graph
    graph = StateGraph(UserAgentState)
    
    # Add nodes
    graph.add_node("generate_response", generate_user_response)
    graph.add_node("check_progress", check_goal_progress)
    graph.add_node("check_end", should_end_conversation)
    
    # Add edges
    graph.add_edge(START, "generate_response")
    graph.add_edge("generate_response", "check_progress")
    graph.add_edge("check_progress", "check_end")
    
    # Always end after checking - the test runner will call us again if needed
    graph.add_edge("check_end", END)
    
    return graph.compile()


def format_messages(messages: List[BaseMessage]) -> str:
    """Format messages for display."""
    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            formatted.append(f"Assistant: {msg.content}")
    return "\n".join(formatted)


def get_last_user_message(messages: List[BaseMessage]) -> Optional[str]:
    """Get the last user message from the conversation."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return None


def initialize_user_state(scenario: TestScenario) -> UserAgentState:
    """Initialize user agent state with opening message."""
    
    persona = scenario.persona
    
    # Generate appropriate opening based on goal and persona
    opening_messages = {
        ConversationGoal.CREATE_DAILY_PLAN: [
            "Hi, I need help planning my meals for today",
            "Can you help me create a meal plan for today?",
            "I'd like to plan out what I'm eating today"
        ],
        ConversationGoal.CREATE_WEEKLY_PLAN: [
            "I want to meal prep for the week",
            "Can you help me plan meals for the next 7 days?",
            "I need a weekly meal plan"
        ],
        ConversationGoal.FIND_SPECIFIC_MEAL: [
            "I'm looking for meal ideas",
            "Can you suggest something for dinner?",
            "I need inspiration for lunch"
        ],
        ConversationGoal.MEET_NUTRITION_GOALS: [
            "I have specific nutrition goals I'm trying to meet",
            "I need help hitting my macros",
            "Can you help me plan meals to meet my protein goals?"
        ],
        ConversationGoal.ACCOMMODATE_RESTRICTIONS: [
            f"I'm {persona.dietary_restrictions[0]} and need meal ideas" if persona.dietary_restrictions else "I have dietary restrictions and need meal ideas",
            f"I have dietary restrictions - {', '.join(persona.dietary_restrictions)}" if persona.dietary_restrictions else "I have some dietary restrictions",
            "I need help finding meals that fit my dietary needs"
        ],
        ConversationGoal.QUICK_MEAL_IDEAS: [
            "I need something quick to make",
            "What can I cook in under 20 minutes?",
            "I'm short on time, any quick meal ideas?"
        ],
        ConversationGoal.SHOPPING_LIST: [
            "I need a shopping list for my meal plan",
            "Can you create a grocery list for me?",
            "What do I need to buy for these meals?"
        ],
        ConversationGoal.OPTIMIZE_EXISTING_PLAN: [
            "I have some meals planned but want to improve them",
            "Can you help me optimize my current meal plan?",
            "I'm eating these foods but think I could do better nutritionally"
        ]
    }
    
    # Select opening based on communication style
    openings = opening_messages.get(scenario.goal, ["Hi, I need help with meal planning"])
    
    if persona.communication_style == "chatty":
        opening = random.choice(openings) + f" I'm {persona.name} by the way!"
    elif persona.communication_style == "uncertain":
        opening = "Um, " + random.choice(openings).lower() + "... if that's something you can help with?"
    else:
        opening = random.choice(openings)
    
    return UserAgentState(
        scenario=scenario,
        messages=[HumanMessage(content=opening)]
    )


# Create and export the user agent
user_agent = create_user_agent()

__all__ = ["user_agent", "UserAgentState", "initialize_user_state"] 