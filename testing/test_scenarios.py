"""Test scenarios for automated chatbot testing."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ConversationGoal(str, Enum):
    """Types of goals users might have."""
    CREATE_DAILY_PLAN = "create_daily_plan"
    FIND_SPECIFIC_MEAL = "find_specific_meal"
    MEET_NUTRITION_GOALS = "meet_nutrition_goals"
    ACCOMMODATE_RESTRICTIONS = "accommodate_restrictions"
    QUICK_MEAL_IDEAS = "quick_meal_ideas"
    SHOPPING_LIST = "shopping_list"
    OPTIMIZE_EXISTING_PLAN = "optimize_existing_plan"


class UserPersona(BaseModel):
    """Represents a test user with specific characteristics."""
    name: str
    age: int
    dietary_restrictions: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    health_goals: List[str] = Field(default_factory=list)
    cooking_skill: str = "intermediate"  # beginner, intermediate, advanced
    time_constraints: Optional[str] = None
    budget_conscious: bool = False
    family_size: int = 1
    
    # Personality traits that affect interaction style
    communication_style: str = "direct"  # direct, chatty, uncertain
    decision_making: str = "decisive"  # decisive, indecisive, exploratory
    tech_savviness: str = "average"  # low, average, high


class TestScenario(BaseModel):
    """A complete test scenario."""
    scenario_id: str
    persona: UserPersona
    goal: ConversationGoal
    specific_requirements: Dict[str, Any] = Field(default_factory=dict)
    expected_outcomes: List[str]
    success_criteria: List[str]
    potential_challenges: List[str] = Field(default_factory=list)
    max_turns: int = 15  # Maximum conversation turns before timeout
    

# ===== TEST SCENARIOS DATABASE =====

TEST_SCENARIOS = [
    # Scenario 1: Busy Professional
    TestScenario(
        scenario_id="busy_professional_weekly",
        persona=UserPersona(
            name="Sarah Chen",
            age=32,
            dietary_restrictions=["gluten-free"],
            preferences=["Asian cuisine", "meal prep friendly"],
            health_goals=["weight loss", "high protein"],
            cooking_skill="intermediate",
            time_constraints="30 minutes max per meal",
            budget_conscious=True,
            communication_style="direct",
            decision_making="decisive"
        ),
        goal=ConversationGoal.CREATE_DAILY_PLAN,
        specific_requirements={
            "calorie_target": 1800,
            "protein_target": 120,
            "prep_time": "Sunday meal prep",
            "must_include": ["variety", "reheatable meals"]
        },
        expected_outcomes=[
            "Daily meal plan created",
            "All meals are gluten-free",
            "Meals are prep-friendly",
            "Calorie and protein goals met",
            "Shopping list generated"
        ],
        success_criteria=[
            "Plan includes 21 meals (7 days x 3 meals)",
            "Each meal respects gluten-free restriction",
            "Daily calories between 1700-1900",
            "Daily protein >= 100g",
            "Includes meal prep instructions"
        ],
        potential_challenges=[
            "Balancing variety with meal prep efficiency",
            "Finding gluten-free high-protein options",
        ]
    ),
    
    # Scenario 2: Fitness Enthusiast
    TestScenario(
        scenario_id="fitness_enthusiast_daily",
        persona=UserPersona(
            name="Marcus Johnson",
            age=28,
            dietary_restrictions=[],
            preferences=["high protein", "pre/post workout meals"],
            health_goals=["muscle gain", "performance"],
            cooking_skill="beginner",
            budget_conscious=False,
            communication_style="chatty",
            decision_making="exploratory"
        ),
        goal=ConversationGoal.MEET_NUTRITION_GOALS,
        specific_requirements={
            "calorie_target": 3200,
            "protein_target": 200,
            "carb_target": 400,
            "meal_timing": "around workouts",
            "supplements_ok": True
        },
        expected_outcomes=[
            "Daily plan with 3 meals + 2 snacks",
            "Pre and post-workout meals identified",
            "Macro targets achieved",
            "Simple recipes for beginner"
        ],
        success_criteria=[
            "Total calories between 3000-3400",
            "Protein >= 180g",
            "Includes pre/post workout nutrition",
            "Recipes are beginner-friendly",
            "Clear timing recommendations"
        ]
    ),
    
    # Scenario 3: Parent with Allergies
    TestScenario(
        scenario_id="parent_allergies_quick",
        persona=UserPersona(
            name="Jennifer Williams",
            age=38,
            dietary_restrictions=["nut allergy", "dairy-free"],
            preferences=["kid-friendly", "quick meals"],
            health_goals=["balanced nutrition", "family health"],
            cooking_skill="intermediate",
            time_constraints="15-20 minutes",
            family_size=4,
            communication_style="uncertain",
            decision_making="indecisive"
        ),
        goal=ConversationGoal.QUICK_MEAL_IDEAS,
        specific_requirements={
            "meal_type": "dinner",
            "servings": 4,
            "kid_approved": True,
            "max_prep_time": 20
        },
        expected_outcomes=[
            "3-5 dinner suggestions provided",
            "All meals nut and dairy free",
            "Kid-friendly options",
            "Under 20 minutes prep"
        ],
        success_criteria=[
            "No nuts or dairy in suggestions",
            "Prep time clearly stated",
            "Family-friendly meals",
            "Clear allergy warnings"
        ],
        potential_challenges=[
            "Finding kid-friendly dairy-free options",
            "Ensuring strict allergy compliance",
            "Balancing quick prep with nutrition"
        ]
    ),
    
    # Scenario 4: Vegetarian Transition
    TestScenario(
        scenario_id="vegetarian_transition",
        persona=UserPersona(
            name="David Park",
            age=45,
            dietary_restrictions=["vegetarian"],
            preferences=["hearty meals", "familiar flavors"],
            health_goals=["lower cholesterol", "maintain energy"],
            cooking_skill="intermediate",
            communication_style="direct",
            decision_making="decisive"
        ),
        goal=ConversationGoal.ACCOMMODATE_RESTRICTIONS,
        specific_requirements={
            "transition_help": True,
            "protein_concerns": True,
            "satisfaction_factor": "high"
        },
        expected_outcomes=[
            "Daily plan created",
            "Adequate protein without meat",
            "Familiar, satisfying meals",
            "Nutrition education provided"
        ],
        success_criteria=[
            "All meals vegetarian",
            "Protein >= 60g daily",
            "Includes transition tips",
            "Addresses common concerns"
        ]
    ),
    
    # Scenario 5: Budget-Conscious Student  
    TestScenario(
        scenario_id="student_budget_optimize",
        persona=UserPersona(
            name="Alex Rivera",
            age=21,
            dietary_restrictions=["lactose intolerant"],
            preferences=["simple recipes", "batch cooking"],
            health_goals=["save money", "stay healthy"],
            cooking_skill="beginner",
            budget_conscious=True,
            communication_style="chatty",
            tech_savviness="high"
        ),
        goal=ConversationGoal.OPTIMIZE_EXISTING_PLAN,
        specific_requirements={
            "existing_meals": {
                "breakfast": ["oatmeal", "banana"],
                "lunch": ["ramen"],
                "dinner": ["pasta"]
            },
            "improve_nutrition": True,
            "keep_budget_low": True
        },
        expected_outcomes=[
            "Current plan analyzed",
            "Affordable improvements suggested",
            "Nutrition gaps identified",
            "Budget-friendly alternatives"
        ],
        success_criteria=[
            "Identifies nutrition issues",
            "Suggests affordable fixes",
            "Respects lactose intolerance",
            "Maintains simplicity"
        ]
    ),
    
    # Scenario 6: Diabetic Senior
    TestScenario(
        scenario_id="diabetic_senior_daily",
        persona=UserPersona(
            name="Robert Thompson",
            age=68,
            dietary_restrictions=["diabetic", "low sodium"],
            preferences=["traditional meals", "easy to chew"],
            health_goals=["blood sugar control", "heart health"],
            cooking_skill="advanced",
            communication_style="chatty",
            tech_savviness="low"
        ),
        goal=ConversationGoal.CREATE_DAILY_PLAN,
        specific_requirements={
            "carb_counting": True,
            "glycemic_index": "low",
            "portion_control": True
        },
        expected_outcomes=[
            "Diabetic-friendly daily plan",
            "Low sodium options",
            "Carb counts provided",
            "Traditional meal style"
        ],
        success_criteria=[
            "All meals diabetic-appropriate",
            "Carb counts included",
            "Sodium within limits",
            "Familiar foods used"
        ]
    ),
    
    # Scenario 7: Quick Shopping List
    TestScenario(
        scenario_id="quick_shopping_list",
        persona=UserPersona(
            name="Maria Gonzalez",
            age=29,
            dietary_restrictions=[],
            preferences=["Mediterranean diet"],
            health_goals=["general health"],
            cooking_skill="intermediate",
            communication_style="direct",
            decision_making="decisive"
        ),
        goal=ConversationGoal.SHOPPING_LIST,
        specific_requirements={
            "meals_planned": {
                "breakfast": ["Greek yogurt parfait"],
                "lunch": ["Mediterranean quinoa bowl"],
                "dinner": ["Grilled chicken with vegetables"]
            },
            "organize_by_section": True
        },
        expected_outcomes=[
            "Complete shopping list",
            "Organized by store section",
            "Quantities specified",
            "Nothing missing"
        ],
        success_criteria=[
            "All ingredients listed",
            "Organized logically",
            "Quantities clear",
            "Efficient format"
        ]
    ),
    
    # Scenario 8: Keto Beginner
    TestScenario(
        scenario_id="keto_beginner_education",
        persona=UserPersona(
            name="Patricia Brown",
            age=42,
            dietary_restrictions=["keto"],
            preferences=["simple meals", "familiar foods"],
            health_goals=["weight loss", "energy"],
            cooking_skill="beginner",
            communication_style="uncertain",
            decision_making="indecisive"
        ),
        goal=ConversationGoal.CREATE_DAILY_PLAN,
        specific_requirements={
            "carb_limit": 20,
            "education_needed": True,
            "transition_support": True
        },
        expected_outcomes=[
            "Keto-compliant daily plan",
            "Macro breakdown provided",
            "Keto basics explained",
            "Common mistakes addressed"
        ],
        success_criteria=[
            "Total carbs < 20g",
            "Adequate fat intake",
            "Educational elements included",
            "Beginner-friendly recipes"
        ],
        potential_challenges=[
            "Explaining keto without overwhelming",
            "Finding simple keto meals",
            "Addressing common concerns"
        ]
    )
]

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

ALL_SCENARIOS = LEVEL_1_SCENARIOS + LEVEL_2_SCENARIOS + LEVEL_3_SCENARIOS + TEST_SCENARIOS

def get_scenario_by_id(scenario_id: str) -> Optional[TestScenario]:
    """Get a specific test scenario by ID."""
    for scenario in TEST_SCENARIOS:
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

def get_scenarios_by_goal(goal: ConversationGoal) -> List[TestScenario]:
    """Get all scenarios with a specific goal."""
    return [s for s in TEST_SCENARIOS if s.goal == goal]


def get_all_scenario_ids() -> List[str]:
    """Get list of all scenario IDs."""
    return [s.scenario_id for s in TEST_SCENARIOS] 