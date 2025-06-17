# Meal Planning Agent with Nutrition Optimization

An intelligent, conversational meal planning assistant that combines LangGraph's ReAct pattern with nutrition optimization algorithms to create personalized, nutritionally balanced meal plans.


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
