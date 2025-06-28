"""Validation agent for analyzing conversation quality and goal achievement."""

from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from datetime import datetime
import json

from src.testing.evaluation_models import (
    TestScenario, CombinedEvaluation, ConversationQuality, TaskCompletion,
    calculate_efficiency_score, calculate_clarity_score, calculate_overall_score,
    determine_recommendation, evaluate_nutrition_requirements, 
    evaluate_dietary_compliance, evaluate_meal_planning_specifics,
    calculate_domain_specific_score, DEFAULT_THRESHOLDS
)
from src.testing.user_agent import UserAgentState

# Backward compatibility alias
ValidationReport = CombinedEvaluation


class ValidationState(BaseModel):
    """State for the validation agent."""
    scenario: TestScenario
    conversation: List[BaseMessage]
    user_state: UserAgentState
    conversation_quality: Optional[ConversationQuality] = None
    task_completion: Optional[TaskCompletion] = None
    report: Optional[CombinedEvaluation] = None


def create_validation_agent():
    """Create a validation agent for analyzing test conversations."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def analyze_conversation_quality(state: ValidationState) -> Dict[str, Any]:
        """Analyze global conversation quality metrics."""
        
        scenario = state.scenario
        conversation = state.conversation
        user_state = state.user_state
        
        conversation_text = format_conversation(conversation)
        
        prompt = f"""Analyze the GLOBAL conversation quality (independent of meal planning domain).

CONVERSATION:
{conversation_text}

USER STATE:
- Final satisfaction: {user_state.satisfaction_level}
- Final confusion: {user_state.confusion_level}
- Final impatience: {user_state.impatience_level}
- Clarifications requested: {user_state.asked_for_clarification}
- Turn count: {user_state.turn_count}/{scenario.max_turns}

Analyze UNIVERSAL conversation quality metrics:
1. Efficiency: How well did the conversation flow? Was it concise or did it drag?
2. Clarity: Were the bot's responses clear and understandable?
3. User satisfaction: Did the user seem happy with the interaction style?
4. Pain points: General usability issues (not domain-specific)
5. Bot errors: Technical/logical errors in conversation flow
6. Confusion moments: When did the user get confused about the process?

Focus on CONVERSATION QUALITY, not meal planning knowledge.

Respond in JSON format:
{{
    "efficiency_score": 0.0-1.0,
    "clarity_score": 0.0-1.0,
    "user_satisfaction_score": 0.0-1.0,
    "pain_points": ["general usability issues"],
    "confusion_moments": [
        {{"turn": X, "issue": "description of confusion"}}
    ],
    "bot_errors": ["conversation flow errors"],
    "decision_points": [
        {{"turn": X, "decision": "key decision in conversation"}}
    ]
}}"""

        response = llm.invoke([SystemMessage(content=prompt)])
        
        try:
            result = json.loads(response.content)
            
            # Calculate scores using our evaluation functions
            total_clarifications = user_state.asked_for_clarification + result.get("bot_clarification_requests", 0)
            
            conversation_quality = ConversationQuality(
                efficiency_score=calculate_efficiency_score(
                    user_state.turn_count, scenario.max_turns, user_state.goal_achieved
                ),
                clarity_score=calculate_clarity_score(
                    total_clarifications, result["confusion_moments"], DEFAULT_THRESHOLDS
                ),
                user_satisfaction_score=result["user_satisfaction_score"],
                total_turns=user_state.turn_count,
                user_clarification_requests=user_state.asked_for_clarification,
                bot_clarification_requests=result.get("bot_clarification_requests", 0),
                pain_points=result["pain_points"],
                confusion_moments=result["confusion_moments"],
                bot_errors=result["bot_errors"],
                decision_points=result["decision_points"]
            )
            
            return {"conversation_quality": conversation_quality}
            
        except Exception as e:
            # Fallback calculation
            conversation_quality = ConversationQuality(
                efficiency_score=calculate_efficiency_score(
                    user_state.turn_count, scenario.max_turns, user_state.goal_achieved
                ),
                clarity_score=1.0 - user_state.confusion_level,
                user_satisfaction_score=user_state.satisfaction_level,
                total_turns=user_state.turn_count,
                user_clarification_requests=user_state.asked_for_clarification,
                bot_clarification_requests=0,
                pain_points=["Analysis failed - using fallback"],
                confusion_moments=[],
                bot_errors=[],
                decision_points=[]
            )
            return {"conversation_quality": conversation_quality}
    
    def analyze_task_completion(state: ValidationState) -> Dict[str, Any]:
        """Analyze task-specific completion and domain knowledge."""
        
        scenario = state.scenario
        conversation = state.conversation
        user_state = state.user_state
        
        conversation_text = format_conversation(conversation)
        
        # Evaluate domain-specific components using helper functions
        nutrition = evaluate_nutrition_requirements(conversation_text, scenario.specific_requirements)
        dietary_compliance = evaluate_dietary_compliance(
            conversation_text, 
            scenario.persona.dietary_restrictions,
            []  # preferences simplified out
        )
        meal_planning = evaluate_meal_planning_specifics(conversation_text, scenario.specific_requirements)
        
        prompt = f"""Analyze TASK COMPLETION for this meal planning conversation.

SCENARIO: {scenario.scenario_id}
USER GOAL: {scenario.goal.value}
SPECIFIC REQUIREMENTS: {json.dumps(scenario.specific_requirements, indent=2)}

SUCCESS CRITERIA:
{chr(10).join(f"- {criterion}" for criterion in scenario.success_criteria)}

CONVERSATION:
{conversation_text}

Analyze TASK-SPECIFIC completion:
1. Was the main goal achieved? 
2. How well were the specific success criteria met?
3. What requirements were missed?
4. Score the goal achievement (0-1 based on criteria completion)

Focus on MEAL PLANNING TASK completion, not conversation quality.

Respond in JSON format:
{{
    "goal_achieved": true/false,
    "goal_achievement_score": 0.0-1.0,
    "custom_criteria_results": {{
        "criterion_name": true/false
    }},
    "missing_criteria": ["list of unmet requirements"],
    "analysis": "Brief explanation of task completion"
}}"""

        response = llm.invoke([SystemMessage(content=prompt)])
        
        try:
            result = json.loads(response.content)
            
            # Create TaskCompletion with calculated domain score
            task_completion = TaskCompletion(
                goal_achieved=result["goal_achieved"],
                goal_achievement_score=result["goal_achievement_score"],
                nutrition=nutrition,
                dietary_compliance=dietary_compliance,
                meal_planning=meal_planning,
                custom_criteria_results=result["custom_criteria_results"],
                missing_criteria=result["missing_criteria"],
                domain_specific_score=0.0  # Will be calculated below
            )
            
            # Calculate domain-specific score
            task_completion.domain_specific_score = calculate_domain_specific_score(task_completion)
            
            return {"task_completion": task_completion}
            
        except Exception as e:
            # Fallback
            task_completion = TaskCompletion(
                goal_achieved=user_state.goal_achieved,
                goal_achievement_score=0.5 if user_state.goal_achieved else 0.0,
                nutrition=nutrition,
                dietary_compliance=dietary_compliance,
                meal_planning=meal_planning,
                domain_specific_score=0.5
            )
            return {"task_completion": task_completion}
    
    def generate_combined_evaluation(state: ValidationState) -> Dict[str, Any]:
        """Generate final combined evaluation with improvement suggestions."""
        
        scenario = state.scenario
        conversation = state.conversation
        conversation_quality = state.conversation_quality
        task_completion = state.task_completion
        
        # Calculate overall score using weighted combination
        overall_score = calculate_overall_score(conversation_quality, task_completion)
        
        # Determine recommendation
        recommendation = determine_recommendation(overall_score, task_completion.goal_achieved, DEFAULT_THRESHOLDS)
        
        # Generate improvement suggestions with LLM
        prompt = f"""Based on this evaluation, suggest improvements.

SCENARIO: {scenario.scenario_id}
GOAL ACHIEVED: {task_completion.goal_achieved} (score: {task_completion.goal_achievement_score})
OVERALL SCORE: {overall_score:.2f}
RECOMMENDATION: {recommendation}

CONVERSATION QUALITY:
- Efficiency: {conversation_quality.efficiency_score:.2f}
- Clarity: {conversation_quality.clarity_score:.2f}
- Satisfaction: {conversation_quality.user_satisfaction_score:.2f}
- Pain points: {conversation_quality.pain_points}

TASK COMPLETION:
- Missing criteria: {task_completion.missing_criteria}
- Domain score: {task_completion.domain_specific_score:.2f}

Generate suggestions separating GLOBAL vs TASK-SPECIFIC improvements:

Respond in JSON format:
{{
    "global_improvements": ["conversation quality improvements that apply to ALL scenarios"],
    "task_specific_improvements": ["meal planning specific improvements for this scenario type"],
    "summary": "Brief assessment of what worked and what didn't"
}}"""

        response = llm.invoke([SystemMessage(content=prompt)])
        
        try:
            result = json.loads(response.content)
            global_improvements = result["global_improvements"]
            task_specific_improvements = result["task_specific_improvements"]
            summary = result["summary"]
        except:
            # Fallback
            global_improvements = ["Improve conversation flow and clarity"]
            task_specific_improvements = ["Better handle meal planning requirements"]
            summary = f"Test completed with score {overall_score:.2f}. {'Goal achieved' if task_completion.goal_achieved else 'Goal not achieved'}."
        
        # Create combined evaluation
        combined_evaluation = CombinedEvaluation(
            scenario_id=scenario.scenario_id,
            conversation_quality=conversation_quality,
            task_completion=task_completion,
            overall_score=overall_score,
            recommendation=recommendation,
            summary=summary,
            global_improvements=global_improvements,
            task_specific_improvements=task_specific_improvements
        )
        
        return {"report": combined_evaluation}
    
    # Build the graph
    graph = StateGraph(ValidationState)
    
    # Add nodes
    graph.add_node("analyze_quality", analyze_conversation_quality)
    graph.add_node("analyze_task", analyze_task_completion)
    graph.add_node("generate_final", generate_combined_evaluation)
    
    # Add edges
    graph.add_edge(START, "analyze_quality")
    graph.add_edge("analyze_quality", "analyze_task")
    graph.add_edge("analyze_task", "generate_final")
    graph.add_edge("generate_final", END)
    
    return graph.compile()


def format_conversation(messages: List[BaseMessage]) -> str:
    """Format conversation for analysis."""
    formatted = []
    for i, msg in enumerate(messages):
        role = "User" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
        formatted.append(f"Turn {i+1} - {role}: {msg.content}")
    return "\n".join(formatted)


def save_validation_report(report: CombinedEvaluation, output_dir: str = "test_results"):
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
        
        f.write("## Task Completion\n")
        f.write(f"- **Goal Achieved**: {'✅ Yes' if report.task_completion.goal_achieved else '❌ No'}\n")
        f.write(f"- **Achievement Score**: {report.task_completion.goal_achievement_score:.2f}\n")
        f.write(f"- **Domain Score**: {report.task_completion.domain_specific_score:.2f}\n")
        if report.task_completion.missing_criteria:
            f.write("- **Missing Criteria**:\n")
            for criterion in report.task_completion.missing_criteria:
                f.write(f"  - {criterion}\n")
        f.write("\n")
        
        f.write("## Conversation Quality\n")
        f.write(f"- **Efficiency**: {report.conversation_quality.efficiency_score:.2f} ({report.conversation_quality.total_turns} turns)\n")
        f.write(f"- **Clarity**: {report.conversation_quality.clarity_score:.2f}\n")
        f.write(f"- **Satisfaction**: {report.conversation_quality.user_satisfaction_score:.2f}\n\n")
        
        if report.conversation_quality.pain_points:
            f.write("## Pain Points (Global)\n")
            for point in report.conversation_quality.pain_points:
                f.write(f"- {point}\n")
            f.write("\n")
        
        if report.global_improvements:
            f.write("## Global Improvements (Apply to All Scenarios)\n")
            for improvement in report.global_improvements:
                f.write(f"- {improvement}\n")
            f.write("\n")
        
        if report.task_specific_improvements:
            f.write("## Task-Specific Improvements\n")
            for improvement in report.task_specific_improvements:
                f.write(f"- {improvement}\n")
            f.write("\n")
        
        # Add detailed breakdowns
        f.write("## Dietary Compliance\n")
        if report.task_completion.dietary_compliance.restrictions_respected:
            f.write("- **Restrictions Respected**:\n")
            for restriction, respected in report.task_completion.dietary_compliance.restrictions_respected.items():
                f.write(f"  - {restriction}: {'✅' if respected else '❌'}\n")
        f.write(f"- **Safety Score**: {report.task_completion.dietary_compliance.safety_score:.2f}\n")
        f.write(f"- **Preference Score**: {report.task_completion.dietary_compliance.preference_score:.2f}\n\n")
        
        if report.conversation_quality.confusion_moments:
            f.write("## Confusion Moments\n")
            for moment in report.conversation_quality.confusion_moments:
                f.write(f"- Turn {moment.get('turn', '?')}: {moment.get('issue', 'Unknown issue')}\n")
    
    return filename, summary_filename


# Create and export the validation agent
validation_agent = create_validation_agent()

__all__ = ["validation_agent", "ValidationState", "ValidationReport", "save_validation_report"] 