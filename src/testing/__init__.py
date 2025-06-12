"""Automated testing framework for the meal planning chatbot."""

from src.testing.test_scenarios import (
    TestScenario,
    UserPersona,
    ConversationGoal,
    TEST_SCENARIOS,
    get_scenario_by_id,
    get_scenarios_by_goal,
    get_all_scenario_ids
)

from src.testing.user_agent import (
    user_agent,
    UserAgentState,
    initialize_user_state
)

from src.testing.validation_agent import (
    validation_agent,
    ValidationState,
    ValidationReport,
    save_validation_report
)

from src.testing.test_runner import (
    TestRunner,
    run_test_scenario,
    run_all_tests
)

__all__ = [
    # Test Scenarios
    "TestScenario",
    "UserPersona", 
    "ConversationGoal",
    "TEST_SCENARIOS",
    "get_scenario_by_id",
    "get_scenarios_by_goal",
    "get_all_scenario_ids",
    
    # User Agent
    "user_agent",
    "UserAgentState",
    "initialize_user_state",
    
    # Validation Agent
    "validation_agent",
    "ValidationState",
    "ValidationReport",
    "save_validation_report",
    
    # Test Runner
    "TestRunner",
    "run_test_scenario",
    "run_all_tests"
] 