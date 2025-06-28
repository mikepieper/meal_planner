"""Evaluation models for separating global vs task-specific metrics."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
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
    """Simplified user persona for conversation testing."""
    name: str
    communication_style: str = "direct"  # direct, chatty, uncertain
    dietary_restrictions: List[str] = Field(default_factory=list)
    health_goals: List[str] = Field(default_factory=list)


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


class ConversationQuality(BaseModel):
    """Global conversation quality metrics that apply to ALL conversations."""
    
    # Core quality metrics (0-1 scale)
    efficiency_score: float = Field(
        description="How efficiently was the conversation conducted (turns vs. expected)"
    )
    clarity_score: float = Field(
        description="How clear and understandable were the bot's responses"
    )
    user_satisfaction_score: float = Field(
        description="Overall user experience quality during conversation"
    )
    
    # Conversation flow metrics
    total_turns: int = Field(description="Total number of conversation turns")
    user_clarification_requests: int = Field(
        description="Number of times user asked for clarification"
    )
    bot_clarification_requests: int = Field(
        description="Number of times bot asked for clarification"
    )
    
    # Issue identification
    pain_points: List[str] = Field(
        default_factory=list,
        description="General usability issues encountered"
    )
    confusion_moments: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Specific moments where user got confused (turn + description)"
    )
    bot_errors: List[str] = Field(
        default_factory=list,
        description="Technical or logical errors made by the bot"
    )
    decision_points: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Key decision moments in the conversation"
    )


class NutritionRequirements(BaseModel):
    """Nutrition-specific evaluation criteria."""
    
    calorie_target_met: Optional[bool] = Field(default=None, description="Whether calorie target was achieved")
    protein_target_met: Optional[bool] = Field(default=None, description="Whether protein target was achieved")
    carb_target_met: Optional[bool] = Field(default=None, description="Whether carb target was achieved")
    fat_target_met: Optional[bool] = Field(default=None, description="Whether fat target was achieved")
    
    # Detailed nutrition analysis
    calorie_accuracy: Optional[float] = Field(default=None, description="How close to calorie target (0-1)")
    macro_balance_score: Optional[float] = Field(default=None, description="How well macros are balanced (0-1)")
    nutrition_education_provided: Optional[bool] = Field(default=None, description="Whether educational content was included")


class DietaryCompliance(BaseModel):
    """Dietary restriction and preference compliance."""
    
    restrictions_respected: Dict[str, bool] = Field(
        default_factory=dict,
        description="Whether each dietary restriction was respected"
    )
    allergies_avoided: Dict[str, bool] = Field(
        default_factory=dict, 
        description="Whether each allergy was properly avoided"
    )
    preferences_accommodated: Dict[str, bool] = Field(
        default_factory=dict,
        description="Whether user preferences were accommodated"
    )
    
    # Safety and compliance scores
    safety_score: float = Field(description="Critical safety compliance (allergies, medical) (0-1)")
    preference_score: float = Field(description="How well preferences were met (0-1)")


class MealPlanningSpecifics(BaseModel):
    """Meal planning domain-specific evaluations."""
    
    # Plan structure
    correct_meal_count: Optional[bool] = Field(default=None, description="Right number of meals generated")
    appropriate_portions: Optional[bool] = Field(default=None, description="Portions appropriate for family size")
    timing_considerations: Optional[bool] = Field(default=None, description="Meal timing properly addressed")
    
    # Practical considerations  
    prep_time_realistic: Optional[bool] = Field(default=None, description="Prep times are realistic")
    cooking_skill_appropriate: Optional[bool] = Field(default=None, description="Recipes match cooking skill level")
    budget_considerations: Optional[bool] = Field(default=None, description="Budget constraints respected")
    
    # Organization and usability
    shopping_list_complete: Optional[bool] = Field(default=None, description="Shopping list has all ingredients")
    instructions_clear: Optional[bool] = Field(default=None, description="Instructions are clear and actionable")
    organization_logical: Optional[bool] = Field(default=None, description="Content is well-organized")


class TaskCompletion(BaseModel):
    """Task-specific success metrics that vary by scenario."""
    
    # Goal achievement
    goal_achieved: bool = Field(description="Whether the specific goal was achieved")
    goal_achievement_score: float = Field(
        description="How well the specific goal was achieved (0-1 scale)"
    )
    
    # Domain-specific evaluations
    nutrition: NutritionRequirements = Field(default_factory=NutritionRequirements)
    dietary_compliance: DietaryCompliance = Field(default_factory=DietaryCompliance)
    meal_planning: MealPlanningSpecifics = Field(default_factory=MealPlanningSpecifics)
    
    # Scenario-specific criteria (for non-standard requirements)
    custom_criteria_results: Dict[str, bool] = Field(
        default_factory=dict,
        description="Results for scenario-specific custom criteria"
    )
    missing_criteria: List[str] = Field(
        default_factory=list,
        description="List of unmet requirements"
    )
    
    # Overall domain score
    domain_specific_score: float = Field(
        description="Overall score for meal planning domain knowledge (0-1)"
    )


class EvaluationThresholds(BaseModel):
    """Standard thresholds and scoring logic for global metrics."""
    
    # Quality score thresholds
    excellent_threshold: float = 0.8
    good_threshold: float = 0.6
    acceptable_threshold: float = 0.4
    
    # Efficiency thresholds (based on turn ratio)
    efficient_turn_ratio: float = 0.7  # If completed in ≤70% of max turns
    acceptable_turn_ratio: float = 1.0  # If completed within max turns
    
    # Clarity thresholds (based on clarification requests)
    max_acceptable_clarifications: int = 2
    max_good_clarifications: int = 1
    
    # User satisfaction bands
    high_satisfaction: float = 0.8
    medium_satisfaction: float = 0.6
    low_satisfaction: float = 0.4


class CombinedEvaluation(BaseModel):
    """Combined evaluation with both global and task-specific metrics."""
    
    # Test metadata
    scenario_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Separated metrics
    conversation_quality: ConversationQuality
    task_completion: TaskCompletion
    
    # Overall assessment
    overall_score: float = Field(description="Weighted combination of quality + completion")
    recommendation: str = Field(description="pass, needs_improvement, or fail")
    summary: str = Field(description="Brief assessment summary")
    
    # Improvement suggestions (global vs specific)
    global_improvements: List[str] = Field(
        default_factory=list,
        description="Improvements for conversation quality (apply to all scenarios)"
    )
    task_specific_improvements: List[str] = Field(
        default_factory=list,
        description="Improvements specific to this scenario type"
    )


def calculate_efficiency_score(total_turns: int, max_turns: int, goal_achieved: bool) -> float:
    """Calculate efficiency score based on turns used vs available."""
    if goal_achieved:
        # Reward completing early
        turn_ratio = total_turns / max_turns
        if turn_ratio <= 0.5:
            return 1.0  # Excellent - finished in half the time
        elif turn_ratio <= 0.7:
            return 0.9  # Very good - efficient completion
        elif turn_ratio <= 1.0:
            return 0.7  # Acceptable - used all available turns
        else:
            return 0.5  # Overtime but still completed
    else:
        # Penalize for not completing
        return max(0.0, 0.5 - (total_turns / max_turns) * 0.3)


def calculate_clarity_score(
    clarification_requests: int, 
    confusion_moments: List[Dict[str, str]],
    thresholds: EvaluationThresholds
) -> float:
    """Calculate clarity score based on clarifications and confusion."""
    base_score = 1.0
    
    # Penalize clarification requests
    if clarification_requests > thresholds.max_good_clarifications:
        penalty = (clarification_requests - thresholds.max_good_clarifications) * 0.2
        base_score -= penalty
    
    # Penalize confusion moments
    confusion_penalty = len(confusion_moments) * 0.15
    base_score -= confusion_penalty
    
    return max(0.0, min(1.0, base_score))


def calculate_overall_score(
    conversation_quality: ConversationQuality,
    task_completion: TaskCompletion,
    weights: Dict[str, float] = None
) -> float:
    """Calculate weighted overall score from quality and completion metrics."""
    
    if weights is None:
        weights = {
            "goal_achievement": 0.4,
            "efficiency": 0.2, 
            "clarity": 0.2,
            "satisfaction": 0.2
        }
    
    return (
        weights["goal_achievement"] * task_completion.goal_achievement_score +
        weights["efficiency"] * conversation_quality.efficiency_score +
        weights["clarity"] * conversation_quality.clarity_score +
        weights["satisfaction"] * conversation_quality.user_satisfaction_score
    )


def determine_recommendation(
    overall_score: float,
    goal_achieved: bool,
    thresholds: EvaluationThresholds
) -> str:
    """Determine pass/needs_improvement/fail recommendation."""
    
    if overall_score >= thresholds.excellent_threshold and goal_achieved:
        return "pass"
    elif overall_score >= thresholds.good_threshold or (goal_achieved and overall_score >= thresholds.acceptable_threshold):
        return "needs_improvement"
    else:
        return "fail"


def evaluate_nutrition_requirements(
    conversation_content: str,
    requirements: Dict[str, Any]
) -> NutritionRequirements:
    """Evaluate nutrition-specific requirements from conversation."""
    
    nutrition = NutritionRequirements()
    
    # Check calorie targets
    if "calorie_target" in requirements:
        target = requirements["calorie_target"]
        # Simple heuristic - look for calorie mentions in bot responses
        nutrition.calorie_target_met = str(target) in conversation_content.lower()
        
    # Check protein targets  
    if "protein_target" in requirements:
        target = requirements["protein_target"]
        nutrition.protein_target_met = f"{target}g" in conversation_content or f"protein" in conversation_content.lower()
        
    # Check for nutrition education
    education_indicators = ["nutrition", "macros", "balanced", "healthy", "vitamins"]
    nutrition.nutrition_education_provided = any(indicator in conversation_content.lower() for indicator in education_indicators)
    
    return nutrition


def evaluate_dietary_compliance(
    conversation_content: str,
    persona_restrictions: List[str],
    persona_preferences: List[str]
) -> DietaryCompliance:
    """Evaluate dietary restriction and preference compliance."""
    
    compliance = DietaryCompliance()
    
    # Check restrictions (allergies, medical diets, etc.)
    for restriction in persona_restrictions:
        # Look for proper handling of restriction in conversation
        restriction_mentioned = restriction.lower() in conversation_content.lower()
        # Simple heuristic - assume compliance if restriction was acknowledged
        compliance.restrictions_respected[restriction] = restriction_mentioned
        
        # Safety-critical restrictions (allergies, medical)
        if any(term in restriction.lower() for term in ["allergy", "diabetic", "celiac"]):
            compliance.allergies_avoided[restriction] = restriction_mentioned
    
    # Calculate safety score (critical for allergies/medical)
    safety_items = list(compliance.allergies_avoided.values())
    compliance.safety_score = sum(safety_items) / len(safety_items) if safety_items else 1.0
    
    # Check preferences
    for preference in persona_preferences:
        pref_accommodated = preference.lower() in conversation_content.lower()
        compliance.preferences_accommodated[preference] = pref_accommodated
    
    # Calculate preference score
    pref_items = list(compliance.preferences_accommodated.values())
    compliance.preference_score = sum(pref_items) / len(pref_items) if pref_items else 1.0
    
    return compliance


def evaluate_meal_planning_specifics(
    conversation_content: str,
    requirements: Dict[str, Any]
) -> MealPlanningSpecifics:
    """Evaluate basic meal planning conversation quality (simplified)."""
    
    planning = MealPlanningSpecifics()
    
    # Focus on conversation quality, not detailed meal planning
    planning.instructions_clear = True  # Assume clear if conversation completed
    
    # Only check for basic acknowledgment of task
    if requirements.get('task'):
        task = requirements['task'].lower()
        # Check if bot acknowledged the basic task
        if any(word in conversation_content.lower() for word in task.split()):
            planning.correct_meal_count = True
    
    return planning


def calculate_domain_specific_score(task_completion: TaskCompletion) -> float:
    """Calculate overall domain-specific score from all components."""
    
    scores = []
    
    # Nutrition score (if applicable)
    nutrition_items = [
        task_completion.nutrition.calorie_target_met,
        task_completion.nutrition.protein_target_met,
        task_completion.nutrition.nutrition_education_provided
    ]
    nutrition_items = [item for item in nutrition_items if item is not None]
    if nutrition_items:
        nutrition_score = sum(nutrition_items) / len(nutrition_items)
        scores.append(nutrition_score)
    
    # Dietary compliance (critical - weighted more heavily)
    scores.append(task_completion.dietary_compliance.safety_score * 1.5)  # Safety is critical
    scores.append(task_completion.dietary_compliance.preference_score)
    
    # Meal planning specifics
    planning_items = [
        task_completion.meal_planning.correct_meal_count,
        task_completion.meal_planning.prep_time_realistic,
        task_completion.meal_planning.cooking_skill_appropriate,
        task_completion.meal_planning.appropriate_portions
    ]
    planning_items = [item for item in planning_items if item is not None]
    if planning_items:
        planning_score = sum(planning_items) / len(planning_items)
        scores.append(planning_score)
    
    # Custom criteria
    if task_completion.custom_criteria_results:
        custom_score = sum(task_completion.custom_criteria_results.values()) / len(task_completion.custom_criteria_results)
        scores.append(custom_score)
    
    return sum(scores) / len(scores) if scores else 0.0


# Default thresholds instance
DEFAULT_THRESHOLDS = EvaluationThresholds()
