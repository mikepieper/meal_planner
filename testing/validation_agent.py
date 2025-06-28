"""Validation agent for analyzing conversation quality and goal achievement."""

from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from datetime import datetime
import json

from src.testing.evaluation_models import TestScenario
from src.testing.user_agent import UserAgentState


class ValidationReport(BaseModel):
    """Comprehensive validation report for a test conversation."""
    
    # Test metadata
    scenario_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Goal achievement
    goal_achieved: bool
    goal_achievement_score: float  # 0-1 scale
    criteria_results: Dict[str, bool] = Field(default_factory=dict)
    missing_criteria: List[str] = Field(default_factory=list)
    
    # Conversation quality
    efficiency_score: float  # 0-1 scale (based on turns needed)
    clarity_score: float  # 0-1 scale (based on confusion level)
    user_satisfaction_score: float  # 0-1 scale
    
    # User experience issues
    pain_points: List[str] = Field(default_factory=list)
    confusion_moments: List[Dict[str, str]] = Field(default_factory=list)
    bot_errors: List[str] = Field(default_factory=list)
    
    # Conversation analysis
    total_turns: int
    user_clarification_requests: int
    bot_clarification_requests: int
    decision_points: List[Dict[str, str]] = Field(default_factory=list)
    
    # Improvement suggestions
    immediate_fixes: List[str] = Field(default_factory=list)
    enhancement_suggestions: List[str] = Field(default_factory=list)
    new_test_suggestions: List[str] = Field(default_factory=list)
    
    # Overall assessment
    overall_score: float  # 0-1 scale
    summary: str
    recommendation: str  # "pass", "needs_improvement", "fail"


class ValidationState(BaseModel):
    """State for the validation agent."""
    scenario: TestScenario
    conversation: List[BaseMessage]
    user_state: UserAgentState
    report: Optional[ValidationReport] = None


def create_validation_agent():
    """Create a validation agent for analyzing test conversations."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def analyze_goal_achievement(state: ValidationState) -> Dict[str, Any]:
        """Analyze whether the user's goal was achieved."""
        
        scenario = state.scenario
        conversation = state.conversation
        user_state = state.user_state
        
        # Check if this is a trajectory evaluation (hit max turns without completion)
        is_trajectory_eval = (user_state.turn_count >= scenario.max_turns and 
                            not user_state.goal_achieved and
                            "trajectory" in scenario.scenario_id)
        
        prompt = f"""Analyze this conversation to determine goal achievement.

SCENARIO: {scenario.scenario_id}
USER GOAL: {scenario.goal.value}
SPECIFIC REQUIREMENTS: {json.dumps(scenario.specific_requirements, indent=2)}
TURN COUNT: {user_state.turn_count}/{scenario.max_turns}

SUCCESS CRITERIA:
{chr(10).join(f"- {criterion}" for criterion in scenario.success_criteria)}

{"TRAJECTORY EVALUATION MODE: Task incomplete due to turn limit. Evaluate PROGRESS and EFFICIENCY instead of completion." if is_trajectory_eval else ""}

CONVERSATION:
{format_conversation(conversation)}

Analyze each success criterion and determine:
1. Was it met? (true/false)
2. If not, what was missing?
3. Overall goal achievement score (0-1)
{f"4. For trajectory eval: Score based on (a) clear progress each turn, (b) no circular conversations, (c) efficient path toward goal" if is_trajectory_eval else ""}

Respond in JSON format:
{{
    "goal_achieved": true/false,
    "goal_achievement_score": 0.0-1.0,
    "criteria_results": {{
        "criterion_name": true/false
    }},
    "missing_criteria": ["list of unmet criteria"],
    "analysis": "Brief explanation",
    "trajectory_score": 0.0-1.0 (if trajectory evaluation),
    "progress_notes": "explanation of progress made"
}}"""

        response = llm.invoke([SystemMessage(content=prompt)])
        
        # Parse response (in production, use proper JSON parsing with error handling)
        try:
            result = json.loads(response.content)
            return {"report": ValidationReport(
                scenario_id=scenario.scenario_id,
                goal_achieved=result["goal_achieved"],
                goal_achievement_score=result["goal_achievement_score"],
                criteria_results=result["criteria_results"],
                missing_criteria=result["missing_criteria"]
            )}
        except:
            # Fallback parsing
            return {"report": ValidationReport(
                scenario_id=scenario.scenario_id,
                goal_achieved=state.user_state.goal_achieved,
                goal_achievement_score=0.5 if state.user_state.goal_achieved else 0.0,
                efficiency_score=0.5,
                clarity_score=0.5,
                user_satisfaction_score=state.user_state.satisfaction_level,
                total_turns=state.user_state.turn_count,
                user_clarification_requests=state.user_state.asked_for_clarification,
                bot_clarification_requests=0,
                overall_score=0.5,
                summary="Analysis failed, using fallback values",
                recommendation="needs_improvement"
            )}
    
    def analyze_conversation_quality(state: ValidationState) -> Dict[str, Any]:
        """Analyze the quality of the conversation."""
        
        scenario = state.scenario
        conversation = state.conversation
        user_state = state.user_state
        
        prompt = f"""Analyze the conversation quality and user experience.

CONVERSATION:
{format_conversation(conversation)}

USER EMOTIONAL STATE:
- Final satisfaction: {user_state.satisfaction_level}
- Final confusion: {user_state.confusion_level}
- Final impatience: {user_state.impatience_level}
- Clarifications requested: {user_state.asked_for_clarification}

Analyze:
1. Efficiency (was the goal achieved with minimal turns?)
2. Clarity (was the bot clear and easy to understand?)
3. User satisfaction (did the user seem happy with the interaction?)
4. Pain points (any moments of frustration or confusion?)
5. Bot errors (incorrect information, misunderstandings, etc.)

Respond in JSON format:
{{
    "efficiency_score": 0.0-1.0,
    "clarity_score": 0.0-1.0,
    "user_satisfaction_score": 0.0-1.0,
    "pain_points": ["list of issues"],
    "confusion_moments": [
        {{"turn": X, "issue": "description"}}
    ],
    "bot_errors": ["list of errors"],
    "decision_points": [
        {{"turn": X, "decision": "what was decided"}}
    ],
    "analysis": "Brief summary"
}}"""

        response = llm.invoke([SystemMessage(content=prompt)])
        
        # Parse and update report
        try:
            result = json.loads(response.content)
            report = state.report
            report.efficiency_score = result["efficiency_score"]
            report.clarity_score = result["clarity_score"]
            report.user_satisfaction_score = result["user_satisfaction_score"]
            report.pain_points = result["pain_points"]
            report.confusion_moments = result["confusion_moments"]
            report.bot_errors = result["bot_errors"]
            report.decision_points = result["decision_points"]
            report.total_turns = user_state.turn_count
            report.user_clarification_requests = user_state.asked_for_clarification
            return {"report": report}
        except:
            # Fallback
            report = state.report
            report.efficiency_score = min(1.0, 1.0 - (user_state.turn_count / scenario.max_turns))
            report.clarity_score = 1.0 - user_state.confusion_level
            report.user_satisfaction_score = user_state.satisfaction_level
            report.total_turns = user_state.turn_count
            return {"report": report}
    
    def generate_improvements(state: ValidationState) -> Dict[str, Any]:
        """Generate improvement suggestions based on the analysis."""
        
        report = state.report
        scenario = state.scenario
        conversation = state.conversation
        
        prompt = f"""Based on this conversation analysis, suggest improvements.

SCENARIO: {scenario.scenario_id}
GOAL ACHIEVEMENT: {report.goal_achieved} (score: {report.goal_achievement_score})
MISSING CRITERIA: {report.missing_criteria}
PAIN POINTS: {report.pain_points}
BOT ERRORS: {report.bot_errors}
USER SATISFACTION: {report.user_satisfaction_score}

CONVERSATION EXCERPT (problematic parts):
{format_conversation(conversation[-10:])}  # Last 10 messages

Generate:
1. Immediate fixes (critical issues to address)
2. Enhancement suggestions (ways to improve the experience)
3. New test suggestions (edge cases to test based on this conversation)

Consider:
- How to better handle {scenario.persona.communication_style} communication style
- How to address the specific requirements: {scenario.specific_requirements}
- How to avoid the confusion moments and pain points

Respond in JSON format:
{{
    "immediate_fixes": ["list of critical fixes"],
    "enhancement_suggestions": ["list of improvements"],
    "new_test_suggestions": ["list of new test scenarios to create"],
    "specific_recommendations": "Detailed explanation"
}}"""

        response = llm.invoke([SystemMessage(content=prompt)])
        
        # Parse and update report
        try:
            result = json.loads(response.content)
            report.immediate_fixes = result["immediate_fixes"]
            report.enhancement_suggestions = result["enhancement_suggestions"]
            report.new_test_suggestions = result["new_test_suggestions"]
            return {"report": report}
        except:
            # Fallback suggestions
            report.immediate_fixes = ["Review conversation for specific failure points"]
            report.enhancement_suggestions = ["Improve response clarity", "Add more guidance"]
            return {"report": report}
    
    def generate_final_assessment(state: ValidationState) -> Dict[str, Any]:
        """Generate final assessment and recommendations."""
        
        report = state.report
        
        # Calculate overall score
        weights = {
            "goal": 0.4,
            "efficiency": 0.2,
            "clarity": 0.2,
            "satisfaction": 0.2
        }
        
        overall_score = (
            weights["goal"] * report.goal_achievement_score +
            weights["efficiency"] * report.efficiency_score +
            weights["clarity"] * report.clarity_score +
            weights["satisfaction"] * report.user_satisfaction_score
        )
        
        report.overall_score = overall_score
        
        # Determine recommendation
        if overall_score >= 0.8 and report.goal_achieved:
            report.recommendation = "pass"
        elif overall_score >= 0.6 or (report.goal_achieved and overall_score >= 0.5):
            report.recommendation = "needs_improvement"
        else:
            report.recommendation = "fail"
        
        # Generate summary
        report.summary = f"""Test scenario '{state.scenario.scenario_id}' completed with overall score: {overall_score:.2f}.
Goal achievement: {'Yes' if report.goal_achieved else 'No'} ({report.goal_achievement_score:.2f})
User experience: Efficiency={report.efficiency_score:.2f}, Clarity={report.clarity_score:.2f}, Satisfaction={report.user_satisfaction_score:.2f}
Major issues: {len(report.pain_points)} pain points, {len(report.bot_errors)} bot errors
Recommendation: {report.recommendation.upper()}"""
        
        return {"report": report}
    
    # Build the graph
    graph = StateGraph(ValidationState)
    
    # Add nodes
    graph.add_node("analyze_goal", analyze_goal_achievement)
    graph.add_node("analyze_quality", analyze_conversation_quality)
    graph.add_node("generate_improvements", generate_improvements)
    graph.add_node("final_assessment", generate_final_assessment)
    
    # Add edges
    graph.add_edge(START, "analyze_goal")
    graph.add_edge("analyze_goal", "analyze_quality")
    graph.add_edge("analyze_quality", "generate_improvements")
    graph.add_edge("generate_improvements", "final_assessment")
    graph.add_edge("final_assessment", END)
    
    return graph.compile()


def format_conversation(messages: List[BaseMessage]) -> str:
    """Format conversation for analysis."""
    formatted = []
    for i, msg in enumerate(messages):
        role = "User" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
        formatted.append(f"Turn {i+1} - {role}: {msg.content}")
    return "\n".join(formatted)


def save_validation_report(report: ValidationReport, output_dir: str = "test_results"):
    """Save validation report to file."""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{output_dir}/{report.scenario_id}_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump(report.dict(), f, indent=2, default=str)
    
    # Also save a human-readable summary
    summary_filename = f"{output_dir}/{report.scenario_id}_{report.timestamp.strftime('%Y%m%d_%H%M%S')}_summary.md"
    
    with open(summary_filename, 'w') as f:
        f.write(f"# Validation Report: {report.scenario_id}\n\n")
        f.write(f"**Date**: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Overall Score**: {report.overall_score:.2f}/1.0\n")
        f.write(f"**Recommendation**: {report.recommendation.upper()}\n\n")
        
        f.write("## Summary\n")
        f.write(f"{report.summary}\n\n")
        
        f.write("## Goal Achievement\n")
        f.write(f"- **Goal Achieved**: {'✅ Yes' if report.goal_achieved else '❌ No'}\n")
        f.write(f"- **Achievement Score**: {report.goal_achievement_score:.2f}\n")
        if report.missing_criteria:
            f.write("- **Missing Criteria**:\n")
            for criterion in report.missing_criteria:
                f.write(f"  - {criterion}\n")
        f.write("\n")
        
        f.write("## User Experience\n")
        f.write(f"- **Efficiency**: {report.efficiency_score:.2f} ({report.total_turns} turns)\n")
        f.write(f"- **Clarity**: {report.clarity_score:.2f}\n")
        f.write(f"- **Satisfaction**: {report.user_satisfaction_score:.2f}\n\n")
        
        if report.pain_points:
            f.write("## Pain Points\n")
            for point in report.pain_points:
                f.write(f"- {point}\n")
            f.write("\n")
        
        if report.immediate_fixes:
            f.write("## Immediate Fixes Needed\n")
            for fix in report.immediate_fixes:
                f.write(f"- {fix}\n")
            f.write("\n")
        
        if report.enhancement_suggestions:
            f.write("## Enhancement Suggestions\n")
            for suggestion in report.enhancement_suggestions:
                f.write(f"- {suggestion}\n")
    
    return filename, summary_filename


# Create and export the validation agent
validation_agent = create_validation_agent()

__all__ = ["validation_agent", "ValidationState", "ValidationReport", "save_validation_report"] 