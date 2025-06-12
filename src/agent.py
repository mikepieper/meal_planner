from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from src.models import MealPlannerState
from src.tools import (
    # Meal Management
    add_meal_item,
    add_multiple_items,
    add_meal_from_suggestion,
    remove_meal_item,
    view_current_meals,
    clear_meal,
    clear_all_meals,
    # User Profile
    update_user_profile,
    # Nutrition
    set_nutrition_goals,
    analyze_meal_nutrition,
    analyze_daily_nutrition,
    suggest_foods_to_meet_goals,
    # Planning
    generate_meal_plan,
    generate_remaining_meals,
    suggest_meal,
    get_meal_ideas,
    # Utility
    generate_shopping_list
)


# ====== SIMPLIFIED REACT AGENT ======

def create_meal_planning_agent():
    """Single ReAct agent that handles all meal planning tasks."""

    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

    # All available tools
    tools = [
        # Meal Management
        add_meal_item,
        add_multiple_items,
        add_meal_from_suggestion,
        remove_meal_item,
        view_current_meals,
        clear_meal,
        clear_all_meals,
        # User Profile
        update_user_profile,
        # Nutrition
        set_nutrition_goals,
        analyze_meal_nutrition,
        analyze_daily_nutrition,
        suggest_foods_to_meet_goals,
        # Planning
        generate_meal_plan,
        generate_remaining_meals,
        suggest_meal,
        get_meal_ideas,
        # Utility
        generate_shopping_list
    ]

    llm_with_tools = llm.bind_tools(tools)

    AGENT_PROMPT = """You are a friendly and knowledgeable meal planning assistant.
Your goal is to help users create personalized, nutritious meal plans that fit their preferences and dietary needs.

Key behaviors:
1. **Be conversational and helpful** - Act like a knowledgeable friend, not a robot
2. **Ask clarifying questions** when needed, but don't overwhelm with too many questions
3. **Use tools intelligently** - Select the right tool for each task
4. **Provide context** - Explain why you're making certain suggestions
5. **Be proactive** - After completing a task, offer relevant next steps

IMPORTANT: Track conversation context:
- When you use suggest_meal, the suggestions are saved in conversation_context
- When users say "add option 1" or "the first one", use add_meal_from_suggestion with "option_1"
- The planning phase progresses: gathering_info → setting_goals → building_meals → optimizing → complete
- Remember what suggestions you've shown to avoid repeating

NUTRITION TRACKING:
- Running nutrition totals are automatically calculated and stored in current_totals
- view_current_meals now shows current totals and progress toward goals
- suggest_meal automatically considers remaining nutrition needs
- Dietary restrictions are validated automatically - restricted foods will be rejected
- Use suggest_foods_to_meet_goals when users need help reaching nutrition targets

CONVERSATION FLOW MANAGEMENT:
Based on the current phase, guide the conversation appropriately:

**gathering_info phase**:
- Ask about dietary restrictions, preferences, and health goals
- Once you have basic info, suggest moving to goal setting
- "I have your preferences noted. How many calories are you targeting daily?"

**setting_goals phase**:
- Help set realistic calorie and macro targets
- After goals are set, offer to start building meals
- "Great! Your goals are set. Would you like me to generate a complete plan or build it meal by meal?"

**building_meals phase**:
- Focus on creating balanced meals that meet goals
- Show running totals after each addition
- If approaching calorie limit, mention it proactively
- "You're at 1400/1800 calories. Let's plan a lighter dinner to stay on target."

**optimizing phase**:
- Triggered when meals are mostly complete
- Analyze gaps and suggest improvements
- "You're a bit short on protein. Would you like suggestions to boost it?"

**complete phase**:
- Offer final tools like shopping list generation
- Suggest saving successful meal combinations as templates
- "Your meal plan looks great! Would you like me to generate a shopping list?"

ERROR HANDLING:
- If a food violates dietary restrictions, explain why and suggest alternatives
- If users try to add too many calories, warn them kindly
- If suggestions aren't appealing, ask what they'd prefer instead

Tool Usage Guidelines:
- Use update_user_profile to properly save dietary restrictions and preferences
- Use add_multiple_items when adding several custom items at once
- Use add_meal_from_suggestion for quick addition of suggested meals
- Always use set_nutrition_goals before generating meal plans

ENHANCED GENERATION:
- generate_meal_plan now preserves existing meals by default
- Use generate_remaining_meals to fill only empty meal slots
- Both tools consider remaining nutrition budget intelligently
- Perfect for users who've started planning but need help finishing

When users provide dietary information:
- Use update_user_profile to save restrictions like "vegetarian", "no gluten", etc.
- The system will automatically validate foods against restrictions
- If a food is rejected, explain why and suggest alternatives

When users ask for meal plans or suggestions:
- If they already have some meals, use generate_remaining_meals to fill gaps
- Use generate_meal_plan with preserve_existing=False only if they want to start over
- Use suggest_meal for individual meal ideas
- After adding meals, view_current_meals shows running totals

When users manually build plans:
- Use add_meal_item for single items
- Use add_multiple_items for batch additions
- Use add_meal_from_suggestion when they select from your suggestions
- Show the current plan with view_current_meals after changes (it includes nutrition)
- Offer suggest_foods_to_meet_goals if they're short on any nutrients

Remember: You're here to make meal planning easy, enjoyable, and personalized!"""

    def agent_node(state: MealPlannerState) -> dict:
        """Main ReAct agent node."""
        messages = state["messages"]

        # Build conversation for LLM
        llm_messages = [SystemMessage(content=AGENT_PROMPT)]

        # Add phase-specific guidance
        conv_context = state.get("conversation_context", {})
        if hasattr(conv_context, 'planning_phase'):
            phase = conv_context.planning_phase
        elif isinstance(conv_context, dict):
            phase = conv_context.get('planning_phase')
        else:
            phase = None
            
        if phase:
            phase_guidance = get_phase_guidance(phase, state)
            if phase_guidance:
                llm_messages.append(SystemMessage(content=phase_guidance))

        # Add nutrition context if relevant
        if state.get("current_totals") and state.get("nutrition_goals"):
            totals = state["current_totals"]
            goals = state["nutrition_goals"]
            nutrition_context = (
                f"Current nutrition: {totals.calories:.0f} cal, "
                f"{totals.protein:.0f}g protein "
                f"({(totals.calories/goals.daily_calories*100):.0f}% of daily goal)"
            )
            llm_messages.append(SystemMessage(content=nutrition_context))

        # Add conversation history (limit to recent messages to avoid token issues)
        for msg in messages[-10:]:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)

        # Get agent response
        result = llm_with_tools.invoke(llm_messages)

        return {"messages": [result]}

    # Build the graph
    graph = StateGraph(MealPlannerState)

    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    # Add edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    graph.add_edge("agent", END)

    return graph.compile()


def get_phase_guidance(phase: str, state: MealPlannerState) -> str:
    """Get specific guidance based on current conversation phase."""

    if phase == "gathering_info":
        if not state.get("user_profile") or not state["user_profile"].dietary_restrictions:
            return "Current phase: Gathering Info. Ask about dietary restrictions and preferences."
        else:
            return (
                "Current phase: Gathering Info. You have their restrictions. "
                "Ask about calorie goals to move to next phase."
            )

    elif phase == "setting_goals":
        if not state.get("nutrition_goals"):
            return "Current phase: Setting Goals. Help them set daily calorie and macro targets."
        else:
            return (
                "Current phase: Setting Goals. Goals are set! "
                "Offer to start building their meal plan."
            )

    elif phase == "building_meals":
        # Count how many meals have items
        meals_with_items = sum(1 for meal in ["breakfast", "lunch", "dinner"] if state.get(meal))
        empty_meals = [meal for meal in ["breakfast", "lunch", "dinner"] if not state.get(meal)]

        if meals_with_items < 2:
            return (
                f"Current phase: Building Meals. {meals_with_items}/3 main meals planned. "
                "Focus on building out the meal plan."
            )
        elif empty_meals:
            return (
                f"Current phase: Building Meals. Empty slots: {', '.join(empty_meals)}. "
                "Offer to use generate_remaining_meals to fill them."
            )
        else:
            return (
                "Current phase: Building Meals. Most meals have items. "
                "Check if they're satisfied or want to optimize."
            )

    elif phase == "optimizing":
        if state.get("current_totals") and state.get("nutrition_goals"):
            totals = state["current_totals"]
            goals = state["nutrition_goals"]
            if totals.calories < goals.daily_calories * 0.9:
                return (
                    "Current phase: Optimizing. They're under calorie target. "
                    "Suggest foods to meet goals or generate_remaining_meals."
                )
            else:
                return (
                    "Current phase: Optimizing. Nutrition looks good! "
                    "Offer to generate shopping list or save as template."
                )

    elif phase == "complete":
        return (
            "Current phase: Complete. Offer shopping list, meal prep tips, "
            "or to save successful combinations."
        )

    return f"Current phase: {phase}"


# Create and export the graph
graph = create_meal_planning_agent()

# This is what LangGraph Studio will load
__all__ = ["graph"]
