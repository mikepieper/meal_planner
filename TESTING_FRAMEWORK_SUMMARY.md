# Automated Testing Framework - Quick Reference

## Overview

The automated testing framework simulates real user interactions with your meal planning chatbot, evaluates performance, and provides actionable insights for improvement.

```
User Scenarios → User Agent → Chatbot → Validation Agent → Reports & Analytics
```

## Quick Start

### 1. Run Your First Test

```bash
# Run a single test scenario
python run_tests.py run --scenario busy_professional_weekly

# View available scenarios
python run_tests.py list

# Run all tests
python run_tests.py run --all
```

### 2. Interpret Results

- **Overall Score**: 0.8+ = Excellent, 0.6-0.8 = Good, <0.6 = Needs Work
- **Key Metrics**: Goal Achievement (40%), Efficiency (20%), Clarity (20%), Satisfaction (20%)
- **Reports**: Check `test_results/` for detailed JSON and Markdown summaries

### 3. Quick Analysis

```python
# Get summary statistics
from src.testing.test_utilities import TestAnalyzer

analyzer = TestAnalyzer()
stats = analyzer.get_summary_stats()
print(f"Average score: {stats['average_scores']['overall']}")
print(f"Top issues: {stats['top_pain_points'][:3]}")
```

## Key Components

### Test Scenarios (`src/testing/test_scenarios.py`)
Pre-built personas with specific goals:
- `busy_professional_weekly`: Time-constrained, gluten-free meal prep
- `fitness_enthusiast_daily`: High protein, 3200 calories
- `parent_allergies_quick`: Family meals, nut/dairy allergies
- `vegetarian_transition`: New vegetarian seeking guidance
- `student_budget_optimize`: Budget-conscious, simple meals
- `diabetic_senior_daily`: Medical dietary needs
- `quick_shopping_list`: Shopping list generation
- `keto_beginner_education`: Keto diet education

### User Agent (`src/testing/user_agent.py`)
Simulates realistic user behavior:
- Adapts communication style (direct, chatty, uncertain)
- Tracks emotional state (satisfaction, confusion, impatience)
- Makes contextual decisions
- Knows when to end conversations

### Validation Agent (`src/testing/validation_agent.py`)
Analyzes conversations for:
- Goal achievement
- Conversation efficiency
- User satisfaction
- Pain points and errors
- Improvement suggestions

## Common Commands

### Testing
```bash
# Run specific scenarios
python run_tests.py run --scenarios scenario1 scenario2 scenario3

# Run with custom output directory
python run_tests.py run --scenario test_name --output my_results/

# Create new test scenario
python src/testing/create_test_scenario.py
```

### Analysis
```python
# Compare two test runs
from src.testing.test_utilities import TestAnalyzer

analyzer = TestAnalyzer()
comparison = analyzer.compare_test_runs("20240115_143022", "20240116_091533")
print(f"Score change: {comparison['score_change']:+.2f}")

# Clean up old results
from src.testing.test_utilities import cleanup_old_results
cleanup_old_results(days_to_keep=7)
```

## Understanding Test Results

### Score Interpretation

| Score Range | Meaning | Action |
|------------|---------|--------|
| 0.8 - 1.0 | Excellent | Monitor and maintain |
| 0.6 - 0.8 | Good | Address specific issues |
| 0.4 - 0.6 | Needs Work | Focus on pain points |
| 0.0 - 0.4 | Critical | Immediate fixes needed |

### Common Pain Points & Solutions

| Issue | Symptoms | Quick Fix |
|-------|----------|-----------|
| Dietary restrictions ignored | Low goal achievement | Check `update_user_profile` tool |
| Long conversations | Low efficiency score | Improve initial data gathering |
| User confusion | High clarification requests | Simplify responses |
| Goals forgotten | Inconsistent suggestions | Better state management |

## CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/chatbot-tests.yml
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: python run_tests.py run --scenarios critical_path_tests
```

### Quality Gates
```python
# Add to CI pipeline
MIN_SCORE = 0.7
if stats['average_scores']['overall'] < MIN_SCORE:
    sys.exit(1)  # Fail the build
```

## Creating New Test Scenarios

### Option 1: Interactive Creator
```bash
python src/testing/create_test_scenario.py
```

### Option 2: Manual Creation
```python
from src.testing.test_scenarios import TestScenario, UserPersona, ConversationGoal

new_scenario = TestScenario(
    scenario_id="unique_id",
    persona=UserPersona(
        name="Test User",
        age=30,
        dietary_restrictions=["vegan"],
        communication_style="direct"
    ),
    goal=ConversationGoal.CREATE_DAILY_PLAN,
    expected_outcomes=["Daily plan created"],
    success_criteria=["All meals are vegan"]
)
```

## Best Practices

### 1. Regular Testing
- Run critical tests on every commit
- Full test suite nightly
- Trend analysis weekly

### 2. Test Selection
- **Quick feedback**: 3-5 scenarios, <5 minutes
- **Comprehensive**: All scenarios, <30 minutes
- **Focus on**: High-risk areas and recent changes

### 3. Acting on Results
- **Immediate**: Fix any score <0.4
- **This sprint**: Address top 3 pain points
- **Next release**: Implement enhancement suggestions

### 4. Continuous Improvement
- Add tests for bug reports
- Update success criteria as product evolves
- Review and refine test scenarios quarterly

## Troubleshooting

### Issue: Tests failing randomly
- Check API rate limits
- Add retry logic
- Increase timeouts

### Issue: Tests take too long
- Run in parallel
- Use subset for quick feedback
- Optimize slow scenarios

### Issue: Can't reproduce failures
- Check test logs in `test_results/`
- Use LangSmith tracing
- Run with debug logging

## Advanced Usage

### Custom Validation
```python
def custom_metric(conversation, user_state):
    # Add your custom analysis
    return score

# Add to validation pipeline
```

### Batch Testing
```python
# Test multiple versions
for branch in ['main', 'feature-x']:
    checkout(branch)
    results[branch] = run_all_tests()
compare_results(results)
```

### Performance Testing
```python
import time
start = time.time()
report = run_test_scenario("test_id")
duration = time.time() - start
print(f"Test took {duration:.1f} seconds")
```

## Resources

- **Detailed Documentation**: `src/testing/README.md`
- **Interpreting Results**: `src/testing/INTERPRETING_RESULTS.md`
- **CI/CD Integration**: `src/testing/CI_CD_INTEGRATION.md`
- **Interactive Notebook**: `notebooks/automated_testing.ipynb`

## Need Help?

1. Check the pain points in test reports
2. Review the improvement suggestions
3. Look for patterns across multiple tests
4. Use the interactive notebook for deeper analysis

Remember: The goal is continuous improvement, not perfection! 