"""Evaluation models for separating global vs task-specific metrics."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


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


class TaskCompletion(BaseModel):
    """Task-specific success metrics that vary by scenario."""
    
    # Goal achievement
    goal_achieved: bool = Field(description="Whether the specific goal was achieved")
    goal_achievement_score: float = Field(
        description="How well the specific goal was achieved (0-1 scale)"
    )
    
    # Scenario-specific criteria
    criteria_results: Dict[str, bool] = Field(
        default_factory=dict,
        description="Results for each scenario-specific success criterion"
    )
    missing_criteria: List[str] = Field(
        default_factory=list,
        description="List of unmet scenario-specific requirements"
    )
    
    # Domain-specific analysis
    domain_specific_score: float = Field(
        description="Score for domain knowledge (nutrition, dietary restrictions, etc.)"
    )
    requirements_met: Dict[str, bool] = Field(
        default_factory=dict,
        description="Whether specific requirements were satisfied"
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


# Default thresholds instance
DEFAULT_THRESHOLDS = EvaluationThresholds()

__all__ = [
    "ConversationQuality",
    "TaskCompletion", 
    "EvaluationThresholds",
    "CombinedEvaluation",
    "calculate_efficiency_score",
    "calculate_clarity_score", 
    "calculate_overall_score",
    "determine_recommendation",
    "DEFAULT_THRESHOLDS"
] 