"""LangSmith evaluators that use our sophisticated evaluation logic."""

import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langsmith.evaluation import LangChainStringEvaluator

from src.testing.evaluation_models import (
    ConversationQuality, TaskCompletion, 
    calculate_efficiency_score, calculate_clarity_score, calculate_overall_score,
    determine_recommendation, evaluate_nutrition_requirements, 
    evaluate_dietary_compliance, evaluate_meal_planning_specifics,
    calculate_domain_specific_score, DEFAULT_THRESHOLDS
)


class ConversationQualityEvaluator(LangChainStringEvaluator):
    """LangSmith evaluator for global conversation quality using our sophisticated logic."""
    
    def __init__(self):
        super().__init__()
        self.evaluation_name = "conversation_quality"
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def _evaluate_strings(
        self,
        prediction: str,
        reference: str = None,
        input: str = None,
        **kwargs
    ) -> dict:
        """Evaluate conversation quality using our LLM-based analysis."""
        
        # Parse inputs (this is the conversation text)
        conversation_text = prediction
        
        try:
            input_data = json.loads(input) if input else {}
            reference_data = json.loads(reference) if reference else {}
        except:
            input_data = {}
            reference_data = {}
        
        # Extract scenario info
        max_turns = input_data.get("max_turns", 15)
        persona = input_data.get("persona", {})
        
        # Count actual turns in conversation
        conversation_lines = conversation_text.split('\n')
        actual_turns = len([line for line in conversation_lines if line.strip().startswith('User:')]) 
        
        # Use our sophisticated LLM-based evaluation (from validation_agent.py)
        prompt = f"""Analyze the GLOBAL conversation quality (independent of meal planning domain).

CONVERSATION:
{conversation_text}

CONTEXT:
- Max turns allowed: {max_turns}
- Actual turns used: {actual_turns}
- User communication style: {persona.get('communication_style', 'unknown')}

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

        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            result = json.loads(response.content)
            
            # Calculate scores using our evaluation functions
            total_clarifications = len(result.get("confusion_moments", []))
            goal_achieved = self._detect_goal_achievement(conversation_text)
            
            # Use our actual calculation functions
            efficiency_score = calculate_efficiency_score(actual_turns, max_turns, goal_achieved)
            clarity_score = calculate_clarity_score(
                total_clarifications, result.get("confusion_moments", []), DEFAULT_THRESHOLDS
            )
            user_satisfaction_score = result.get("user_satisfaction_score", 0.7)
            
            # Calculate overall score
            overall_score = (efficiency_score + clarity_score + user_satisfaction_score) / 3
            
            # Determine quality level
            if overall_score >= 0.8:
                value = "EXCELLENT"
            elif overall_score >= 0.6:
                value = "GOOD"
            elif overall_score >= 0.4:
                value = "ACCEPTABLE"
            else:
                value = "POOR"
            
            return {
                "key": "conversation_quality",
                "score": overall_score,
                "value": value,
                "comment": f"Efficiency: {efficiency_score:.2f}, Clarity: {clarity_score:.2f}, Satisfaction: {user_satisfaction_score:.2f}",
                "metadata": {
                    "efficiency_score": efficiency_score,
                    "clarity_score": clarity_score,
                    "user_satisfaction_score": user_satisfaction_score,
                    "total_turns": actual_turns,
                    "max_turns": max_turns,
                    "pain_points": result.get("pain_points", []),
                    "confusion_moments": result.get("confusion_moments", [])
                }
            }
            
        except Exception as e:
            # Fallback to simple analysis
            goal_achieved = self._detect_goal_achievement(conversation_text)
            efficiency_score = calculate_efficiency_score(actual_turns, max_turns, goal_achieved)
            
            return {
                "key": "conversation_quality", 
                "score": efficiency_score,
                "value": "FALLBACK",
                "comment": f"LLM analysis failed, using fallback. Error: {str(e)[:100]}",
                "metadata": {"error": str(e), "fallback_used": True}
            }
    
    def _detect_goal_achievement(self, conversation: str) -> bool:
        """Simple heuristic to detect if goal was achieved."""
        success_keywords = ["plan created", "meal plan", "completed", "finished", "success"]
        conversation_lower = conversation.lower()
        return any(keyword in conversation_lower for keyword in success_keywords)


class TaskCompletionEvaluator(LangChainStringEvaluator):
    """LangSmith evaluator for task-specific completion using our domain logic."""
    
    def __init__(self):
        super().__init__()
        self.evaluation_name = "task_completion"
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def _evaluate_strings(
        self,
        prediction: str,
        reference: str = None,
        input: str = None,
        **kwargs
    ) -> dict:
        """Evaluate task completion using our sophisticated domain analysis."""
        
        conversation_text = prediction
        
        try:
            input_data = json.loads(input) if input else {}
            reference_data = json.loads(reference) if reference else {}
        except:
            input_data = {}
            reference_data = {}
        
        # Extract scenario information
        goal = input_data.get("goal", "")
        specific_requirements = input_data.get("specific_requirements", {})
        persona = input_data.get("persona", {})
        success_criteria = reference_data.get("success_criteria", [])
        
        # Use our domain-specific evaluation functions
        nutrition = evaluate_nutrition_requirements(conversation_text, specific_requirements)
        dietary_compliance = evaluate_dietary_compliance(
            conversation_text,
            persona.get("dietary_restrictions", []),
            []  # preferences simplified
        )
        meal_planning = evaluate_meal_planning_specifics(conversation_text, specific_requirements)
        
        # Use LLM for goal achievement analysis (from validation_agent.py)
        prompt = f"""Analyze TASK COMPLETION for this meal planning conversation.

GOAL: {goal}
SPECIFIC REQUIREMENTS: {json.dumps(specific_requirements, indent=2)}

SUCCESS CRITERIA:
{chr(10).join(f"- {criterion}" for criterion in success_criteria)}

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

        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            result = json.loads(response.content)
            
            # Create TaskCompletion using our evaluation models
            task_completion = TaskCompletion(
                goal_achieved=result.get("goal_achieved", False),
                goal_achievement_score=result.get("goal_achievement_score", 0.0),
                nutrition=nutrition,
                dietary_compliance=dietary_compliance,
                meal_planning=meal_planning,
                custom_criteria_results=result.get("custom_criteria_results", {}),
                missing_criteria=result.get("missing_criteria", []),
                domain_specific_score=0.0  # Will be calculated below
            )
            
            # Calculate domain-specific score using our function
            task_completion.domain_specific_score = calculate_domain_specific_score(task_completion)
            
            # Determine value
            if task_completion.goal_achieved and task_completion.goal_achievement_score >= 0.8:
                value = "COMPLETED"
            elif task_completion.goal_achieved:
                value = "PARTIAL"
            else:
                value = "FAILED"
            
            return {
                "key": "task_completion",
                "score": task_completion.goal_achievement_score,
                "value": value,
                "comment": f"Goal: {'✓' if task_completion.goal_achieved else '✗'}, Domain: {task_completion.domain_specific_score:.2f}",
                "metadata": task_completion.dict()
            }
            
        except Exception as e:
            # Fallback
            goal_achieved = goal.lower() in conversation_text.lower()
            
            return {
                "key": "task_completion",
                "score": 0.5 if goal_achieved else 0.0,
                "value": "FALLBACK",
                "comment": f"LLM analysis failed. Error: {str(e)[:100]}",
                "metadata": {"error": str(e), "fallback_used": True}
            }


class SafetyComplianceEvaluator(LangChainStringEvaluator):
    """LangSmith evaluator for safety-critical compliance (dietary restrictions)."""
    
    def __init__(self):
        super().__init__()
        self.evaluation_name = "safety_compliance"
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)  # Lower temp for safety
    
    def _evaluate_strings(
        self,
        prediction: str,
        reference: str = None,
        input: str = None,
        **kwargs
    ) -> dict:
        """Evaluate safety compliance with focus on dietary restrictions."""
        
        conversation_text = prediction
        
        try:
            input_data = json.loads(input) if input else {}
            reference_data = json.loads(reference) if reference else {}
        except:
            input_data = {}
            reference_data = {}
        
        # Extract dietary restrictions
        persona = input_data.get("persona", {})
        dietary_restrictions = persona.get("dietary_restrictions", [])
        is_safety_critical = reference_data.get("scenario_metadata", {}).get("safety_critical", False)
        
        if not dietary_restrictions:
            return {
                "key": "safety_compliance",
                "score": 1.0,
                "value": "N/A",
                "comment": "No dietary restrictions to check",
                "metadata": {"restrictions": [], "safety_critical": False}
            }
        
        # Use LLM to analyze safety compliance
        prompt = f"""Analyze SAFETY COMPLIANCE for dietary restrictions in this meal planning conversation.

DIETARY RESTRICTIONS: {dietary_restrictions}
SAFETY CRITICAL: {is_safety_critical}

CONVERSATION:
{conversation_text}

For each dietary restriction, determine:
1. Was it properly acknowledged by the assistant?
2. Were any foods suggested that violate the restriction?
3. Did the assistant ask clarifying questions about restrictions?
4. Were safety warnings provided where appropriate?

This is SAFETY-CRITICAL evaluation. Be thorough and conservative.

Respond in JSON format:
{{
    "restrictions_respected": {{
        "restriction_name": true/false
    }},
    "violations_found": ["list any foods that violate restrictions"],
    "safety_warnings_provided": true/false,
    "acknowledgment_quality": 0.0-1.0,
    "overall_safety_score": 0.0-1.0,
    "safety_analysis": "detailed explanation"
}}"""

        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            result = json.loads(response.content)
            
            # Calculate safety score
            safety_score = result.get("overall_safety_score", 0.0)
            violations = result.get("violations_found", [])
            
            # Determine severity
            if violations:
                value = "VIOLATION"
                severity = "CRITICAL" if is_safety_critical else "WARNING"
            elif safety_score >= 0.9:
                value = "SAFE"
                severity = "GOOD"
            elif safety_score >= 0.7:
                value = "ACCEPTABLE"
                severity = "MINOR_ISSUES"
            else:
                value = "UNSAFE"
                severity = "MAJOR_ISSUES"
            
            comment = f"Safety: {safety_score:.2f}, Violations: {len(violations)}"
            if violations:
                comment += f", Found: {', '.join(violations[:2])}"
            
            return {
                "key": "safety_compliance",
                "score": safety_score,
                "value": value,
                "comment": comment,
                "metadata": {
                    **result,
                    "severity": severity,
                    "safety_critical": is_safety_critical,
                    "restriction_count": len(dietary_restrictions)
                }
            }
            
        except Exception as e:
            # Safety fallback - conservative approach
            return {
                "key": "safety_compliance",
                "score": 0.5,  # Conservative fallback
                "value": "NEEDS_REVIEW",
                "comment": f"Safety analysis failed - manual review needed. Error: {str(e)[:100]}",
                "metadata": {
                    "error": str(e),
                    "fallback_used": True,
                    "requires_manual_review": True,
                    "safety_critical": is_safety_critical
                }
            }


__all__ = [
    "ConversationQualityEvaluator",
    "TaskCompletionEvaluator", 
    "SafetyComplianceEvaluator"
] 