# Automated Testing Framework for Meal Planning Chatbot

This framework provides automated testing capabilities for the meal planning chatbot by simulating user interactions and evaluating conversation quality.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Test Scenarios  │────▶│   User Agent    │────▶│ Meal Planning    │
│   Database      │     │  (Simulates     │     │    Chatbot       │
└─────────────────┘     │   User Input)   │◀────│                  │
                        └─────────────────┘     └──────────────────┘
                                │                         │
                                └─────────┬───────────────┘
                                          │
                                          ▼
                               ┌──────────────────┐
                               │ Validation Agent │
                               │   (Analyzes      │
                               │  Conversation)   │
                               └──────────────────┘
                                          │
                                          ▼
                               ┌──────────────────┐
                               │  Test Reports    │
                               │  & Analytics     │
                               └──────────────────┘
```

## Components

### 1. Test Scenarios (`test_scenarios.py`)
- **Purpose**: Defines test cases with user personas and goals
- **Features**:
  - 8 pre-defined test scenarios covering different user types
  - User personas with personality traits and communication styles
  - Specific goals and success criteria for each test

### 2. User Agent (`user_agent.py`)
- **Purpose**: Simulates realistic user behavior
- **Features**:
  - Adapts responses based on persona characteristics
  - Tracks emotional state (satisfaction, confusion, impatience)
  - Makes decisions based on conversation context
  - Knows when to end conversations

### 3. Validation Agent (`validation_agent.py`)
- **Purpose**: Evaluates conversation quality and goal achievement
- **Analyzes**:
  - Goal achievement against success criteria
  - Conversation efficiency
  - User satisfaction
  - Pain points and bot errors
- **Generates**:
  - Improvement suggestions
  - Test scores and recommendations

### 4. Test Runner (`test_runner.py`)
- **Purpose**: Orchestrates the testing process
- **Features**:
  - Runs single or multiple test scenarios
  - Integrates with LangSmith for tracing
  - Generates detailed reports
  - Creates aggregate analytics

## Usage

### Command Line Interface

```bash
# List all available test scenarios
python run_tests.py list

# Run a single test scenario
python run_tests.py run --scenario busy_professional_weekly

# Run multiple specific scenarios
python run_tests.py run --scenarios busy_professional_weekly fitness_enthusiast_daily

# Run all test scenarios
python run_tests.py run --all

# Specify custom output directory
python run_tests.py run --scenario test_name --output custom_results/
```

### Python API

```python
import asyncio
from src.testing import run_test_scenario, run_all_tests, TestRunner

# Run a single test
async def test_single():
    report = await run_test_scenario("busy_professional_weekly")
    print(f"Score: {report.overall_score}")
    print(f"Recommendation: {report.recommendation}")

# Run multiple tests
async def test_multiple():
    runner = TestRunner(output_dir="my_results")
    results = await runner.run_multiple_tests([
        "busy_professional_weekly",
        "fitness_enthusiast_daily"
    ])
    
    for scenario_id, report in results.items():
        print(f"{scenario_id}: {report.overall_score:.2f}")

# Run with asyncio
asyncio.run(test_single())
```

### Jupyter Notebook

See `notebooks/automated_testing.ipynb` for interactive testing and visualization.

## Test Scenarios

| Scenario ID | Persona | Goal | Key Challenges |
|------------|---------|------|----------------|
| busy_professional_weekly | Sarah Chen | Create weekly meal plan | Gluten-free, meal prep, time constraints |
| fitness_enthusiast_daily | Marcus Johnson | Meet nutrition goals | High protein (200g), 3200 calories |
| parent_allergies_quick | Jennifer Williams | Quick meal ideas | Nut/dairy allergies, family of 4 |
| vegetarian_transition | David Park | Accommodate restrictions | New vegetarian, protein concerns |
| student_budget_optimize | Alex Rivera | Optimize existing plan | Limited budget, lactose intolerant |
| diabetic_senior_daily | Robert Thompson | Create daily plan | Diabetic, low sodium, traditional foods |
| quick_shopping_list | Maria Gonzalez | Generate shopping list | Mediterranean diet preferences |
| keto_beginner_education | Patricia Brown | Create daily plan | Keto education, <20g carbs |

## Output Files

### Individual Test Results
- **JSON Report**: `test_results/{scenario_id}_{timestamp}.json`
  - Complete test data including all scores and issues
- **Markdown Summary**: `test_results/{scenario_id}_{timestamp}_summary.md`
  - Human-readable summary with key findings

### Aggregate Reports
- **Aggregate Report**: `test_results/aggregate_report_{timestamp}.md`
  - Summary statistics across all tests
  - Common pain points and fixes
  - Priority recommendations

## Evaluation Metrics

### Overall Score Calculation
```python
overall_score = (
    0.4 * goal_achievement_score +
    0.2 * efficiency_score +
    0.2 * clarity_score +
    0.2 * user_satisfaction_score
)
```

### Recommendations
- **Pass**: Overall score ≥ 0.8 AND goal achieved
- **Needs Improvement**: Overall score ≥ 0.6 OR (goal achieved AND score ≥ 0.5)
- **Fail**: Otherwise

## Integration with LangSmith

The framework integrates with LangSmith for detailed tracing:

1. Set up your LangSmith API key:
   ```bash
   export LANGSMITH_API_KEY="your-api-key"
   ```

2. All test runs are automatically traced with:
   - User agent decisions
   - Chatbot responses
   - Validation analysis

## Extending the Framework

### Adding New Test Scenarios

```python
from src.testing.test_scenarios import TestScenario, UserPersona, ConversationGoal

new_scenario = TestScenario(
    scenario_id="unique_id",
    persona=UserPersona(
        name="Test User",
        age=30,
        dietary_restrictions=["vegan"],
        preferences=["quick meals"],
        health_goals=["weight loss"],
        communication_style="direct"
    ),
    goal=ConversationGoal.CREATE_DAILY_PLAN,
    specific_requirements={
        "calorie_target": 1500,
        "meal_prep": True
    },
    expected_outcomes=["Daily plan created", "All meals vegan"],
    success_criteria=["Total calories 1400-1600", "All meals plant-based"]
)
```

### Custom Validation Logic

The validation agent can be extended with custom analysis:

```python
def custom_validation(conversation, user_state):
    # Add custom validation logic
    custom_score = analyze_custom_metric(conversation)
    return custom_score
```

## Best Practices

1. **Run tests regularly** after making changes to the chatbot
2. **Focus on failed tests** and "needs improvement" recommendations
3. **Look for patterns** in pain points across multiple tests
4. **Create new test scenarios** when users report issues
5. **Use aggregate reports** to identify systemic problems
6. **Monitor trends** over time to ensure improvements

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running from the project root
2. **Async errors**: Use `asyncio.run()` or run in Jupyter with `await`
3. **API rate limits**: Add delays between tests if needed
4. **Memory issues**: Run tests in smaller batches

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Add conversation replay functionality
- [ ] Create visual conversation flow diagrams
- [ ] Add A/B testing capabilities
- [ ] Implement regression testing
- [ ] Add performance benchmarking
- [ ] Create test scenario generator from real conversations 