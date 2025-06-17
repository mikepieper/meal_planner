"""User simulation agent for automated testing."""

from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
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
    
    # Use Claude for user agent - better at following adversarial instructions without being helpful
    import os
    anthropic_key = os.getenv("ANTHROPIC_KEY") or os.getenv("ANTHROPIC_API_KEY")
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0.7, api_key=anthropic_key)
    
    def get_response_content(response):
        """Extract content from LLM response, handling different formats."""
        if isinstance(response.content, list):
            return response.content[0].text if response.content else ""
        else:
            return response.content
    
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

STRICT FORBIDDEN BEHAVIORS - NEVER DO THESE:

1. **NEVER repeat a previous message** - each response must be unique and move the conversation forward
2. **NEVER ask the chatbot questions** - you make statements and demands, not questions to the bot
3. **NEVER thank the chatbot** - real users don't constantly thank bots, especially when frustrated
4. **NEVER offer help to the chatbot** - you are the customer who needs help
5. **NEVER say "let me know if you need anything"** - the BOT should ask if YOU need anything
6. **NEVER be accommodating or polite when you're not getting what you want**

REQUIRED BEHAVIORS - YOU MUST:

1. **Make demands and statements** - "I need X", "Do Y", "Give me Z"
2. **Express frustration when things aren't working** - "This isn't what I asked for"
3. **Push for your specific goal** - "But I said I wanted..."
4. **Respond to what the bot actually said** - don't ignore their response
5. **Show impatience if the bot is slow or unclear** - "Just get to the point"
6. **Make decisions when presented with options** - pick something or reject it

COMMUNICATION PATTERNS:

1. **Direct**: "I need X. Do it." / "That's not right." / "Fine, do Y instead."
2. **Chatty**: "So I'm trying to do X and it's really important because Y..." / "The thing is..."
3. **Uncertain**: "I think I want X... but is that right?" / "I'm not sure if..."

EMOTIONAL RESPONSES:

- **If confused**: "What does that mean?" / "I don't get it" / "That makes no sense"
- **If impatient**: "This is taking forever" / "Just do it already" / "Can we move on?"
- **If satisfied**: "Good" / "That works" / "Finally" / "Yes, that's it"
- **If frustrated**: "This isn't working" / "That's not what I said" / "Forget it"

Remember: You are {persona.name}, a real person with real problems to solve. You're not here to be nice to the chatbot - you're here to get help with YOUR goal. Be demanding, realistic, and focused on what YOU need.

NEVER repeat previous messages. NEVER ask questions. NEVER thank the bot. NEVER offer help.

Generate ONLY your next message as {persona.name} would realistically say it."""

        # Combine system prompt with final reminder to avoid multiple system messages
        combined_system_prompt = system_prompt + "\n\n" + """FINAL REMINDER - STRICT RULES:
- NO QUESTIONS to the chatbot (no "Can you...", "Could you...", "Would you...")
- NO THANKING the chatbot (no "thank you", "thanks")  
- NO OFFERING HELP (no "let me know if you need anything")
- MAKE DEMANDS, not requests ("Add eggs to breakfast", "Do this now")
- BE IMPATIENT if the bot is slow or unclear
- NEVER repeat previous messages"""
        
        # Add conversation history
        messages = [SystemMessage(content=combined_system_prompt)]
        
        # Include recent conversation (limit to prevent token issues)
        for msg in state.messages[-10:]:
            messages.append(msg)
        
        # Get response
        response = llm.invoke(messages)
        
        # Check for message repetition - if the new message is too similar to a previous user message, regenerate
        previous_user_messages = [msg.content for msg in state.messages if isinstance(msg, HumanMessage)]
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            response_content = get_response_content(response).strip()
            
            # Check for forbidden behaviors
            is_invalid = False
            violation_reason = ""
            
            # Check for repetition
            for prev_msg in previous_user_messages:
                if (len(response_content) > 10 and len(prev_msg) > 10 and 
                    response_content.lower() in prev_msg.lower() or 
                    prev_msg.lower() in response_content.lower()):
                    is_invalid = True
                    violation_reason = "repetitive message"
                    break
            
            # Check for questions (ending with ? or starting with question words)
            if not is_invalid:
                question_indicators = ["?", "can you", "could you", "would you", "will you", "do you", "are you", "how do", "what do", "when do", "where do", "why do"]
                response_lower = response_content.lower()
                if any(indicator in response_lower for indicator in question_indicators):
                    is_invalid = True
                    violation_reason = "asking questions"
            
            # Check for thanking
            if not is_invalid:
                thank_phrases = ["thank", "thanks", "appreciate"]
                if any(phrase in response_content.lower() for phrase in thank_phrases):
                    is_invalid = True
                    violation_reason = "thanking the bot"
            
            # Check for offering help
            if not is_invalid:
                help_offers = ["let me know if you need", "if you need anything", "happy to help", "here to help"]
                if any(offer in response_content.lower() for offer in help_offers):
                    is_invalid = True
                    violation_reason = "offering help"
            
            if not is_invalid:
                break
            
            # Debug logging for violations
            print(f"  ⚠️  Attempt {attempts}: Regenerating due to {violation_reason}")
            print(f"  📝 Invalid response: {response_content[:100]}...")
            
            # Regenerate with stronger violation-specific prompt
            attempts += 1
            violation_prompt = f"""CRITICAL VIOLATION: Your response was rejected for: {violation_reason}

FORBIDDEN BEHAVIORS YOU MUST AVOID:
- NO questions (no ?, no "Can you", "Could you", etc.)
- NO thanking (no "thank you", "thanks")
- NO offering help (no "let me know if you need anything")
- NO repeating previous messages

YOU ARE {persona.name} - A DEMANDING USER WHO NEEDS HELP.

Your task: {scenario.specific_requirements.get('task', 'achieve your goal')}
The assistant just said: "{state.messages[-1].content if state.messages else 'nothing yet'}"

Generate a COMPLETELY DIFFERENT response that:
1. Makes a DEMAND or STATEMENT (not a question)
2. Shows impatience if the bot isn't helping
3. Pushes for your specific goal
4. NEVER asks questions or offers help

Examples of good responses:
- "Add eggs to my breakfast now."
- "That's not what I asked for."
- "Just do what I said."
- "I need X. Do it."

Be {persona.communication_style} and demanding."""
            
            response = llm.invoke([SystemMessage(content=violation_prompt)])
        
        # Update emotional state based on conversation
        final_content = get_response_content(response)
        new_state = update_emotional_state(state, final_content)
        
        return {
            "messages": state.messages + [HumanMessage(content=final_content)],
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

        eval_messages = [
            SystemMessage(content="You are a conversation evaluator. Analyze conversations and determine if goals were achieved."),
            HumanMessage(content=progress_prompt)
        ]
        
        response = llm.invoke(eval_messages)
        
        # Parse response (in real implementation, use proper JSON parsing)
        # For now, simple heuristic
        goal_achieved = "goal_achieved\": true" in get_response_content(response)
        
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
    task = scenario.specific_requirements.get('task', '')
    
    # Generate appropriate opening based on the specific task, not generic goals
    if task:
        # Use the specific task for a more demanding opening
        if "add eggs to breakfast" in task.lower():
            opening = "Add eggs to my breakfast"
        elif "check calories" in task.lower():
            opening = "Show me the calories in my current meals"
        elif "clear breakfast" in task.lower():
            opening = "Clear my breakfast. I want to start over"
        elif "create a simple breakfast" in task.lower():
            opening = "I need a quick healthy breakfast plan"
        elif "gluten-free lunch" in task.lower():
            opening = "I need a gluten-free lunch option"
        elif "1500 calorie" in task.lower():
            opening = "Set my daily goal to 1500 calories"
        elif "full day meal plan" in task.lower():
            opening = "Create a full day vegetarian meal plan for 1800 calories"
        elif "increase protein" in task.lower():
            opening = "I need to increase my protein to 120g daily"
        else:
            opening = f"I need you to {task}"
    else:
        # Fallback to demanding versions without questions
        opening_messages = {
            ConversationGoal.CREATE_DAILY_PLAN: [
                "I need a meal plan for today",
                "Plan my meals for today", 
                "Create my daily meal plan"
            ],
            ConversationGoal.CREATE_WEEKLY_PLAN: [
                "I need a weekly meal plan",
                "Plan my meals for the week",
                "Create a 7-day meal plan"
            ],
            ConversationGoal.FIND_SPECIFIC_MEAL: [
                "I need meal ideas",
                "Give me dinner suggestions",
                "I need lunch ideas"
            ],
            ConversationGoal.MEET_NUTRITION_GOALS: [
                "I need to hit my nutrition goals",
                "Set up my macros",
                "I need my protein targets met"
            ],
            ConversationGoal.ACCOMMODATE_RESTRICTIONS: [
                f"I'm {persona.dietary_restrictions[0]} and need meal ideas" if persona.dietary_restrictions else "I have dietary restrictions and need meal ideas",
                f"I have dietary restrictions - {', '.join(persona.dietary_restrictions)}" if persona.dietary_restrictions else "I have some dietary restrictions",
                "Find meals that fit my dietary needs"
            ],
            ConversationGoal.QUICK_MEAL_IDEAS: [
                "I need something quick to make",
                "Give me meals under 20 minutes",
                "I'm short on time. Give me quick meal ideas"
            ],
            ConversationGoal.SHOPPING_LIST: [
                "I need a shopping list for my meal plan",
                "Create a grocery list for me",
                "Give me what to buy for these meals"
            ],
            ConversationGoal.OPTIMIZE_EXISTING_PLAN: [
                "I have meals planned but want to improve them",
                "Optimize my current meal plan",
                "I'm eating these foods but need better nutrition"
            ]
        }
        
        # Select opening based on communication style
        openings = opening_messages.get(scenario.goal, ["I need help with meal planning"])
        
        if persona.communication_style == "chatty":
            opening = random.choice(openings) + f" I'm {persona.name} by the way"
        elif persona.communication_style == "uncertain":
            opening = "Um, " + random.choice(openings).lower() 
        else:
            opening = random.choice(openings)
    
    return UserAgentState(
        scenario=scenario,
        messages=[HumanMessage(content=opening)]
    )


# Create and export the user agent
user_agent = create_user_agent()

__all__ = ["user_agent", "UserAgentState", "initialize_user_state"] 