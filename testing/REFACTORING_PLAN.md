# Testing Framework Refactoring Plan

## Overview
Refactor the testing framework to be simpler, more maintainable, and better suited for the current development stage of the meal planning agent.

## Task 1: Simplify User Agent 🎯
**Goal**: Strip down user simulation to essential functionality, removing complexity that's not needed while the meal planning agent is still being optimized.

### Subtask 1.1: Analyze Current User Agent Complexity ✅ COMPLETE
- [x] Audit `UserAgentState` fields to identify essential vs. nice-to-have
- [x] Review emotional state tracking logic (satisfaction, confusion, impatience)
- [x] Identify complex persona behavior logic that can be simplified
- [x] Document which features to keep vs. remove vs. move to "future enhancements"

### Subtask 1.2: Create Simplified User State Model ✅ COMPLETE
- [x] Design new `SimpleUserState` class with only essential fields
- [x] Keep: scenario, messages, turn_count, goal_achieved, should_end
- [x] Remove: emotional tracking, complex metadata, advanced persona traits
- [x] Create migration path for any essential data

### Subtask 1.3: Simplify User Response Generation ✅ COMPLETE
- [x] Strip down the complex prompt with violation checking and regeneration logic
- [x] Create simple, direct user behavior focused on goal pursuit
- [x] Remove complex communication style variations (keep basic direct/chatty/uncertain)
- [x] Simplify end-of-conversation detection
- [x] Replace hardcoded string patterns with LLM-based evaluation (goal achievement & end detection)

### Subtask 1.4: Update User Agent Graph ✅ COMPLETE
- [x] Simplify the LangGraph nodes and edges (2 nodes → 1 node)
- [x] Remove unnecessary state update functions (combined into single function)
- [x] Streamline the conversation flow logic (single process_turn function)
- [x] Test that basic scenarios still work with simplified agent (test file created)

## Task 2: Separate Global vs Task-Specific Metrics 📊
**Goal**: Clearly distinguish between universal conversation quality metrics and scenario-specific success criteria.

### Subtask 2.1: Define Global Conversation Quality Metrics ✅ COMPLETE
- [x] Identify metrics that apply to ALL conversations regardless of scenario
- [x] Create `ConversationQuality` model with efficiency, clarity, satisfaction scores
- [x] Define standard thresholds and scoring logic for global metrics
- [x] Document what each global metric measures

### Subtask 2.2: Define Task-Specific Success Criteria ✅ COMPLETE & SIMPLIFIED
- [x] Create `TaskCompletion` model for scenario-specific outcomes
- [x] Separate domain knowledge (dietary restrictions, nutrition goals) from conversation flow
- [x] Update test scenarios to clearly separate global vs specific criteria
- [x] Ensure task-specific criteria are measurable and clear
- [x] Simplify scenarios to focus on conversation testing (remove cooking skill, family size, etc.)
- [x] Move scenarios to YAML for cleaner data/code separation
- [x] Create scenario loader for backward compatibility

### Subtask 2.3: Update Validation Logic
- [ ] Modify validation to score global and task-specific metrics separately
- [ ] Create combined scoring logic that weights both appropriately
- [ ] Update reporting to show both types of metrics clearly
- [ ] Test with existing scenarios to ensure accuracy

## Task 3: Focus on Core Scenarios (80/20 Rule) 🎯
**Goal**: Identify and prioritize the 20% of scenarios that catch 80% of issues.

### Subtask 3.1: Analyze Scenario Coverage and Value
- [ ] Review current scenarios for overlap and redundancy
- [ ] Identify which scenarios test unique functionality vs. variations
- [ ] Categorize scenarios by: basic functionality, edge cases, stress tests
- [ ] Determine which scenarios provide the most debugging value

### Subtask 3.2: Create Core Scenario Set
- [ ] Select 5-8 core scenarios that cover essential functionality
- [ ] Ensure coverage of: basic tasks, dietary restrictions, multi-step flows
- [ ] Create a "core test suite" that can run quickly for development
- [ ] Keep complex scenarios but mark them as "extended test suite"

### Subtask 3.3: Optimize Scenario Complexity
- [ ] Simplify overly complex scenarios that are hard to debug
- [ ] Ensure each core scenario has one clear primary objective
- [ ] Reduce max_turns for scenarios that don't need long conversations
- [ ] Create clear success/failure criteria for each core scenario

## Task 4: Migrate to LangSmith Evaluation Framework 🔄
**Goal**: Move evaluation logic from custom validation agent to LangSmith's built-in tools.

### Subtask 4.1: Set Up LangSmith Datasets
- [ ] Create LangSmith datasets for different scenario types
- [ ] Upload core scenarios as LangSmith examples
- [ ] Set up proper tagging and metadata for scenarios
- [ ] Test dataset creation and retrieval workflows

### Subtask 4.2: Create LangSmith Evaluators
- [ ] Convert global conversation quality metrics to LangSmith evaluators
- [ ] Create task-specific evaluators for domain knowledge
- [ ] Set up batch evaluation workflows
- [ ] Test evaluators against known good/bad conversations

### Subtask 4.3: Update Test Runner for LangSmith
- [ ] Modify test runner to use LangSmith datasets instead of local scenarios
- [ ] Update conversation logging to push results to LangSmith
- [ ] Replace local validation agent with LangSmith evaluation calls
- [ ] Maintain backward compatibility during transition

### Subtask 4.4: Remove Deprecated Components
- [ ] Remove validation_agent.py and related validation logic
- [ ] Clean up test scenarios that are now handled by LangSmith
- [ ] Update documentation and README files
- [ ] Archive old validation reports and migrate useful data

## Success Criteria
- [ ] Test execution time reduced by 50%+ (fewer scenarios, simpler logic)
- [ ] Debugging clarity improved (clearer failure modes, better reporting)
- [ ] Maintenance burden reduced (less custom evaluation code)
- [ ] Flexibility increased (easy to add new scenarios and metrics)
- [ ] Integration improved (LangSmith provides better tooling and visualization)

## Notes
- Each subtask should be completed and approved before moving to the next
- We'll test functionality after each major change to ensure nothing breaks
- We can always add complexity back later once the meal planning agent is working well
- Focus on making the testing framework a useful development tool, not a comprehensive evaluation suite 