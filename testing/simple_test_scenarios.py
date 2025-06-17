"""Simple, focused test scenarios for initial chatbot evaluation.

These scenarios form a curriculum starting with atomic tasks that should
complete in 3-5 turns, gradually increasing in complexity.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.testing.test_scenarios import (
    TestScenario, 
    UserPersona, 
    ConversationGoal,
    get_scenario_by_id as get_full_scenario_by_id
)


# Level 1: Single-Step Tasks (Should complete in 2-3 turns)
LEVEL_1_SCENARIOS = [
    TestScenario(
        scenario_id="simple_add_item",
        persona=UserPersona(
            name="Quick User",
            age=30,
            communication_style="direct",
            decision_making="decisive"
        ),
        goal=ConversationGoal.FIND_SPECIFIC_MEAL,
        specific_requirements={
            "task": "add eggs to breakfast"
        },
        expected_outcomes=[
            "Eggs added to breakfast"
        ],
        success_criteria=[
            "User says 'add eggs to breakfast'",
            "Bot adds eggs without unnecessary questions",
            "Bot confirms addition"
        ],
        max_turns=7
    ),
    
    TestScenario(
        scenario_id="simple_nutrition_check",
        persona=UserPersona(
            name="Direct User",
            age=25,
            communication_style="direct"
        ),
        goal=ConversationGoal.MEET_NUTRITION_GOALS,
        specific_requirements={
            "task": "check calories in current meals"
        },
        expected_outcomes=[
            "Current nutrition displayed"
        ],
        success_criteria=[
            "User asks for nutrition info",
            "Bot shows current totals",
            "No unnecessary information gathering"
        ],
        max_turns=7
    ),
    
    TestScenario(
        scenario_id="simple_clear_meal",
        persona=UserPersona(
            name="Reset User",
            age=35,
            communication_style="direct"
        ),
        goal=ConversationGoal.FIND_SPECIFIC_MEAL,
        specific_requirements={
            "task": "clear breakfast and start over"
        },
        expected_outcomes=[
            "Breakfast cleared"
        ],
        success_criteria=[
            "User requests clear breakfast",
            "Bot clears without excessive confirmation",
            "Ready for new items"
        ],
        max_turns=7
    )
]

# Level 2: Multi-Step Tasks (Should complete in 4-5 turns)
LEVEL_2_SCENARIOS = [
    TestScenario(
        scenario_id="simple_breakfast_plan",
        persona=UserPersona(
            name="Morning Planner",
            age=28,
            dietary_restrictions=[],
            communication_style="direct",
            decision_making="decisive"
        ),
        goal=ConversationGoal.CREATE_DAILY_PLAN,
        specific_requirements={
            "task": "create a simple breakfast",
            "preferences": "quick and healthy"
        },
        expected_outcomes=[
            "Complete breakfast created",
            "Under 500 calories",
            "Quick to prepare"
        ],
        success_criteria=[
            "User states goal clearly",
            "Bot suggests appropriate options",
            "User makes selection",
            "Bot confirms and shows nutrition"
        ],
        max_turns=7
    ),
    
    TestScenario(
        scenario_id="simple_restriction_meal",
        persona=UserPersona(
            name="Gluten-Free User",
            age=32,
            dietary_restrictions=["gluten-free"],
            communication_style="direct"
        ),
        goal=ConversationGoal.ACCOMMODATE_RESTRICTIONS,
        specific_requirements={
            "task": "find gluten-free lunch option",
            "preference": "something filling"
        },
        expected_outcomes=[
            "Gluten-free lunch suggested",
            "User accepts suggestion"
        ],
        success_criteria=[
            "User mentions gluten-free need",
            "Bot acknowledges restriction",
            "Bot suggests appropriate meal",
            "No gluten-containing foods suggested"
        ],
        max_turns=7
    ),
    
    TestScenario(
        scenario_id="simple_calorie_goal",
        persona=UserPersona(
            name="Calorie Counter",
            age=27,
            health_goals=["weight loss"],
            communication_style="direct"
        ),
        goal=ConversationGoal.MEET_NUTRITION_GOALS,
        specific_requirements={
            "task": "set 1500 calorie daily goal",
            "preference": "balanced macros"
        },
        expected_outcomes=[
            "Nutrition goals set",
            "Confirmation of goals"
        ],
        success_criteria=[
            "User states calorie target",
            "Bot sets goals appropriately",
            "Bot confirms settings",
            "No excessive questions"
        ],
        max_turns=7
    )
]

# Level 3: Complex Tasks (May hit 7-turn limit, evaluate trajectory)
LEVEL_3_SCENARIOS = [
    TestScenario(
        scenario_id="trajectory_full_day_plan",
        persona=UserPersona(
            name="Busy Professional",
            age=35,
            dietary_restrictions=["vegetarian"],
            preferences=["quick meals"],
            communication_style="direct",
            decision_making="decisive"
        ),
        goal=ConversationGoal.CREATE_DAILY_PLAN,
        specific_requirements={
            "task": "create full day meal plan",
            "constraints": "vegetarian, 1800 calories",
            "preference": "minimal cooking"
        },
        expected_outcomes=[
            "Progress toward complete plan",
            "Vegetarian options only",
            "Efficient conversation flow"
        ],
        success_criteria=[
            "Clear goal communication",
            "Bot acknowledges all requirements",
            "Systematic meal building",
            "No redundant questions",
            "Progress visible each turn"
        ],
        max_turns=7,
        potential_challenges=[
            "May not complete in 7 turns",
            "Evaluate trajectory instead"
        ]
    ),
    
    TestScenario(
        scenario_id="trajectory_optimization",
        persona=UserPersona(
            name="Optimizer",
            age=29,
            health_goals=["high protein"],
            communication_style="direct"
        ),
        goal=ConversationGoal.OPTIMIZE_EXISTING_PLAN,
        specific_requirements={
            "existing_meals": {
                "breakfast": ["oatmeal", "banana"],
                "lunch": ["sandwich"],
                "dinner": ["pasta"]
            },
            "task": "increase protein to 120g"
        },
        expected_outcomes=[
            "Analysis of current meals",
            "Specific improvement suggestions",
            "Progress toward protein goal"
        ],
        success_criteria=[
            "Bot analyzes current nutrition",
            "Bot identifies protein gap",
            "Bot suggests specific changes",
            "Each turn makes progress",
            "No circular conversations"
        ],
        max_turns=7
    )
]


def get_simple_scenario_by_id(scenario_id: str) -> Optional[TestScenario]:
    """Get a simple test scenario by ID."""
    all_scenarios = LEVEL_1_SCENARIOS + LEVEL_2_SCENARIOS + LEVEL_3_SCENARIOS
    for scenario in all_scenarios:
        if scenario.scenario_id == scenario_id:
            return scenario
    return None


def get_scenarios_by_level(level: int) -> List[TestScenario]:
    """Get all scenarios for a specific curriculum level."""
    if level == 1:
        return LEVEL_1_SCENARIOS
    elif level == 2:
        return LEVEL_2_SCENARIOS
    elif level == 3:
        return LEVEL_3_SCENARIOS
    else:
        return []


def get_curriculum_progression() -> List[TestScenario]:
    """Get all scenarios in curriculum order."""
    return LEVEL_1_SCENARIOS + LEVEL_2_SCENARIOS + LEVEL_3_SCENARIOS


# Progress tracking for curriculum
class CurriculumProgress(BaseModel):
    """Track progress through the curriculum."""
    completed_scenarios: List[str] = Field(default_factory=list)
    level_1_complete: bool = False
    level_2_complete: bool = False
    level_3_complete: bool = False
    
    def get_next_scenario(self) -> Optional[str]:
        """Get the next scenario to test."""
        for scenario in get_curriculum_progression():
            if scenario.scenario_id not in self.completed_scenarios:
                return scenario.scenario_id
        return None
    
    def mark_complete(self, scenario_id: str, passed: bool):
        """Mark a scenario as complete if it passed."""
        if passed and scenario_id not in self.completed_scenarios:
            self.completed_scenarios.append(scenario_id)
            
        # Check level completion
        level_1_ids = [s.scenario_id for s in LEVEL_1_SCENARIOS]
        level_2_ids = [s.scenario_id for s in LEVEL_2_SCENARIOS]
        level_3_ids = [s.scenario_id for s in LEVEL_3_SCENARIOS]
        
        self.level_1_complete = all(sid in self.completed_scenarios for sid in level_1_ids)
        self.level_2_complete = all(sid in self.completed_scenarios for sid in level_2_ids)
        self.level_3_complete = all(sid in self.completed_scenarios for sid in level_3_ids) 