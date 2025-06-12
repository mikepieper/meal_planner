# Curriculum-Based Testing Approach

## Overview

We've implemented a curriculum-based testing framework that progressively evaluates the chatbot's capabilities, starting with simple tasks and advancing to more complex scenarios. All tests are limited to 7 turns to ensure focused, efficient conversations.

## Key Principles

1. **7-Turn Limit**: Forces efficient, focused interactions
2. **Progressive Complexity**: Start simple, gradually increase difficulty
3. **Trajectory Evaluation**: For complex tasks, evaluate progress rather than completion
4. **Realistic User Behavior**: User agent acts demanding and goal-focused, not helpful

## Curriculum Structure

### 📚 Level 1: Single-Step Tasks (2-3 turns)
Focus: Basic operations without unnecessary questions

- **simple_add_item**: Add eggs to breakfast
- **simple_nutrition_check**: Check current calories  
- **simple_clear_meal**: Clear breakfast

Expected behavior:
- Direct action without gathering unnecessary info
- Immediate confirmation
- No circular conversations

### 📚 Level 2: Multi-Step Tasks (4-5 turns)
Focus: Coordinated actions with clear flow

- **simple_breakfast_plan**: Create a quick, healthy breakfast
- **simple_restriction_meal**: Find gluten-free lunch
- **simple_calorie_goal**: Set 1500 calorie daily goal

Expected behavior:
- Acknowledge requirements upfront
- Provide relevant suggestions
- Complete task efficiently

### 📚 Level 3: Complex Tasks (7 turns, trajectory evaluation)
Focus: Progress and efficiency, not necessarily completion

- **trajectory_full_day_plan**: Create vegetarian 1800-cal day plan
- **trajectory_optimization**: Improve existing meals to hit 120g protein

Expected behavior:
- Make clear progress each turn
- No redundant questions
- Systematic approach

## Running the Tests

### List all scenarios:
```bash
python run_simple_tests.py list
```

### Run a single test:
```bash
python run_simple_tests.py run simple_add_item
```

### Run a complete level:
```bash
python run_simple_tests.py run level1
```

### Run full curriculum:
```bash
python run_simple_tests.py run curriculum
```

## Success Criteria

### For Levels 1-2:
- **Pass**: Goal achieved within turn limit with good user experience
- **Needs Improvement**: Goal achieved but inefficient or confusing
- **Fail**: Goal not achieved or poor user experience

### For Level 3 (Trajectory):
- **Pass**: Clear progress toward goal, efficient conversation flow
- **Needs Improvement**: Some progress but circular or inefficient
- **Fail**: No clear progress or stuck in loops

## Interpreting Results

### Good Signs 🟢
- Completes simple tasks in 2-3 turns
- Acknowledges requirements without re-asking
- Makes progress each turn
- User satisfaction remains high

### Warning Signs 🟡
- Takes maximum turns for simple tasks
- Asks for information already provided
- User becomes impatient or confused
- Progress is slow but present

### Red Flags 🔴
- Circular conversations
- Ignores user's stated goal
- Asks unnecessary questions
- No progress toward goal

## Benefits of This Approach

1. **Quick Feedback**: Know within 7 turns if the chatbot is on track
2. **Focused Testing**: Each scenario tests specific capabilities
3. **Clear Progression**: Must master basics before complex tasks
4. **Realistic Scenarios**: Based on actual user needs and behaviors
5. **Measurable Progress**: Clear metrics for improvement

## Next Steps

1. Run Level 1 tests first
2. Fix any issues before proceeding to Level 2
3. Use trajectory evaluation to guide improvements for complex tasks
4. Iterate based on specific failure patterns

The goal is not to pass all tests immediately, but to use them as a guide for systematic improvement. 