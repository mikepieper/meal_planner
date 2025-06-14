# Meal Planning Agent with Nutrition Optimization

An intelligent, conversational meal planning assistant that combines LangGraph's ReAct pattern with nutrition optimization algorithms to create personalized, nutritionally balanced meal plans.

## 🌟 Features

- **Conversational Interface**: Natural language interaction using ReAct pattern
- **Nutrition Optimization**: Hill climbing algorithm to meet macro/calorie targets
- **Dietary Flexibility**: Supports vegetarian, vegan, low-carb, high-protein, etc.
- **Multi-turn Conversations**: Remembers context and preferences throughout the session
- **LangSmith Integration**: Full observability and evaluation capabilities
- **LangGraph Studio Support**: Visual debugging and testing

## 📁 Project Structure

```
src/
├── agent.py               # Main meal planning agent
├── tools.py               # All available tools
├── models.py              # Data models and state definitions
├── food_database.py       # Food nutrition database
├── nutrition_optimizer.py # Hill climbing optimization
├── testing/               # Automated testing framework
│   ├── test_scenarios.py  # Test case definitions
│   ├── user_agent.py      # User simulation agent
│   ├── validation_agent.py # Conversation analyzer
│   └── test_runner.py     # Test orchestration
├── notebooks/             # Jupyter notebooks
│   └── automated_testing.ipynb
└── DESIGN_OVERVIEW.md     # Detailed design documentation
```

## 🚀 Quick Start

### 3. Run the agent

```python
from meal_planner.main_agent import create_meal_planning_agent, MealPlannerState
from meal_planner.nutrition_optimizer import MealPlan, get_food_database
from langchain_core.messages import HumanMessage

# Create agent
agent = create_meal_planning_agent()

# Initialize state
state = {
    "messages": [
        HumanMessage(content="I'm vegetarian and need 2200 calories with high protein")
    ],
    "current_meal_plan": MealPlan(),
    "user_profile": {},
    "food_database": get_food_database(),
    "conversation_phase": "gathering_info",
    "optimization_history": []
}

# Run conversation
config = {"configurable": {"thread_id": "session1"}}
result = agent.invoke(state, config)
print(result["messages"][-1].content)
```

## 🛠️ Available Tools

The agent has access to several tools:

1. **`generate_meal_suggestions`**: Creates meal ideas based on preferences
2. **`optimize_meal_nutrition`**: Adjusts portions to meet nutritional targets
3. **`set_nutrition_goals`**: Establishes personalized macro/calorie goals
4. **`analyze_daily_nutrition`**: Reviews nutritional completeness
5. **`save_meal_to_plan`**: Adds meals to the daily plan

## 🧪 Testing

### Automated Testing Framework

The project includes a comprehensive automated testing framework that simulates user interactions and evaluates chatbot performance:

```bash
# List available test scenarios
python run_tests.py list

# Run a single test
python run_tests.py run --scenario busy_professional_weekly

# Run all tests
python run_tests.py run --all
```

The framework includes:
- **User Simulation**: AI agents that act like real users with different personalities
- **Goal Achievement Analysis**: Validates if user goals were met
- **Conversation Quality Metrics**: Measures efficiency, clarity, and satisfaction
- **Automated Reporting**: Generates detailed reports with improvement suggestions

See `src/testing/README.md` for detailed documentation.

### Run the test suite

```bash
python src/meal_planner/test_agent.py
```

This runs:
- Conversation tests for different scenarios (vegetarian, low-carb, athlete, etc.)
- LangSmith evaluations for nutrition accuracy, dietary compliance, and conversation quality
- Results saved to `test_results.json`

### Use LangGraph Studio

1. Open LangGraph Studio
2. Load the project from `src/meal_planner/studio`
3. Interactive debugging with visual graph representation

## 📊 Nutrition Optimization

The system uses a hill climbing algorithm to optimize meals:

```python
from meal_planner.nutrition_optimizer import NutritionOptimizer, ConstraintSet, NutrientConstraint

# Define goals
profile = ConstraintSet(
    calories=NutrientConstraint(minimum=1800, target=2000, maximum=2200),
    protein=NutrientConstraint(minimum=100, target=120, maximum=140),
    # ... other nutrients
)

# Optimize a meal
optimizer = NutritionOptimizer(food_database, profile)
optimized_meal, fitness = optimizer.optimize_meal_plan(meal_plan)
```

### Fitness Function

The optimizer minimizes a fitness score based on:
- Heavy penalty for being outside min/max bounds
- Light penalty for deviation from target
- Considers all macronutrients (protein, carbs, fat) and calories

## 🎯 Example Scenarios

### High-Protein Vegetarian
```
User: "I'm vegetarian trying to build muscle. Need 2200 calories with high protein."
Agent: Sets up high-protein goals, suggests Greek yogurt bowls, quinoa dishes, and optimizes portions
```

### Low-Carb Weight Loss
```
User: "I want to lose weight on low-carb. Target 1600 calories, <100g carbs."
Agent: Focuses on protein and healthy fats, avoids high-carb foods, suggests cauliflower alternatives
```

### Quick Meals for Busy Professional
```
User: "I need meals that take less than 15 minutes. Around 1800 calories."
Agent: Prioritizes simple preparations, meal prep options, and convenient protein sources
```

## 🔄 Architecture Overview

The system follows a ReAct (Reasoning and Acting) pattern:

1. **Think**: Agent reasons about user needs
2. **Act**: Calls appropriate tools or responds directly
3. **Observe**: Processes results and updates state
4. **Loop**: Continues until user needs are met

## 📈 Future Enhancements

- [ ] Connect to comprehensive food database API
- [ ] Add recipe generation with step-by-step instructions
- [ ] Implement weekly meal planning and prep schedules
- [ ] Create shopping list with store organization
- [ ] Add micronutrient tracking (vitamins, minerals)
- [ ] Integrate with fitness trackers for dynamic calorie adjustment
- [ ] Support for food allergies and intolerances
- [ ] Meal photo analysis for portion estimation

## 🤝 Contributing

Contributions are welcome! Key areas for improvement:
- Expanding the food database
- Adding more sophisticated optimization algorithms
- Improving conversation flows
- Adding more dietary patterns (keto, paleo, etc.)

## 📝 License

MIT License - feel free to use and modify for your needs.

## 🙏 Acknowledgments

Built with:
- [LangChain](https://langchain.com/) and [LangGraph](https://github.com/langchain-ai/langgraph)
- [OpenAI GPT-4](https://openai.com/)
- [LangSmith](https://smith.langchain.com/) for observability 