"""YAML-based scenario loader for cleaner test configuration management."""

import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from pydantic import BaseModel

from src.testing.evaluation_models import ConversationGoal, UserPersona, TestScenario
from src.testing.evaluation_models import (
    ConversationQuality, TaskCompletion, CombinedEvaluation,
    NutritionRequirements, DietaryCompliance, MealPlanningSpecifics
)


class ScenarioLoader:
    """Loads and converts YAML test scenarios to evaluation models."""
    
    def __init__(self, yaml_file: str = "scenarios.yaml"):
        self.yaml_file = Path(__file__).parent / yaml_file
        self._scenarios_cache = None
    
    def load_scenarios(self) -> Dict[str, Any]:
        """Load scenarios from YAML file."""
        if self._scenarios_cache is None:
            with open(self.yaml_file, 'r') as f:
                self._scenarios_cache = yaml.safe_load(f)
        return self._scenarios_cache
    
    def get_scenario_by_id(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific scenario by ID from any category."""
        data = self.load_scenarios()
        
        # Search through all categories
        for category_name, category_scenarios in data.items():
            if category_name == 'config':
                continue
            if isinstance(category_scenarios, dict) and scenario_id in category_scenarios:
                scenario = category_scenarios[scenario_id].copy()
                scenario['scenario_id'] = scenario_id
                return scenario
        return None
    
    def list_all_scenarios(self) -> List[str]:
        """List all available scenario IDs."""
        data = self.load_scenarios()
        scenario_ids = []
        
        for category_name, category_scenarios in data.items():
            if category_name == 'config':
                continue
            if isinstance(category_scenarios, dict):
                scenario_ids.extend(category_scenarios.keys())
        
        return scenario_ids
    
    def get_scenarios_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """Get all scenarios in a specific category."""
        data = self.load_scenarios()
        if category in data and isinstance(data[category], dict):
            # Add scenario_id to each scenario
            scenarios = {}
            for scenario_id, scenario_data in data[category].items():
                scenario_data = scenario_data.copy()
                scenario_data['scenario_id'] = scenario_id
                scenarios[scenario_id] = scenario_data
            return scenarios
        return {}
    
    def convert_yaml_to_user_persona(self, persona_data: Dict[str, Any]) -> UserPersona:
        """Convert simplified YAML persona data to UserPersona model."""
        return UserPersona(
            name=persona_data.get('name', 'Test User'),
            communication_style=persona_data.get('communication_style', 'direct'),
            dietary_restrictions=persona_data.get('dietary_restrictions', []),
            health_goals=persona_data.get('health_goals', [])
        )
    
    def convert_yaml_to_test_scenario(self, scenario_data: Dict[str, Any]) -> TestScenario:
        """Convert YAML scenario to legacy TestScenario format (for backward compatibility)."""
        
        # Convert persona
        persona = self.convert_yaml_to_user_persona(scenario_data['persona'])
        
        # Convert goal
        goal_str = scenario_data['goal']
        goal = ConversationGoal(goal_str)
        
        # Extract requirements from simplified structure
        task_criteria = scenario_data.get('task_criteria', {})
        legacy_reqs = task_criteria.get('custom_requirements', {})
        
        # Add nutrition targets if present
        if 'nutrition_targets' in task_criteria:
            for key, value in task_criteria['nutrition_targets'].items():
                legacy_reqs[f"{key}_target"] = value
        
        # Create basic success criteria from task criteria
        success_criteria = []
        if task_criteria.get('must_respect_restrictions'):
            for restriction in task_criteria['must_respect_restrictions']:
                success_criteria.append(f"Respects {restriction} restriction")
        
        if task_criteria.get('nutrition_targets'):
            for nutrient, target in task_criteria['nutrition_targets'].items():
                success_criteria.append(f"{nutrient.title()} target of {target} met")
        
        if task_criteria.get('should_provide_shopping_list'):
            success_criteria.append("Shopping list provided")
        
        if not success_criteria:
            success_criteria = ["Task completed successfully"]
        
        return TestScenario(
            scenario_id=scenario_data['scenario_id'],
            persona=persona,
            goal=goal,
            specific_requirements=legacy_reqs,
            expected_outcomes=[scenario_data.get('description', 'Task completed')],
            success_criteria=success_criteria,
            max_turns=scenario_data.get('global_criteria', {}).get('max_turns', 10)
        )
    
    def convert_yaml_to_evaluation_criteria(self, scenario_data: Dict[str, Any]) -> CombinedEvaluation:
        """Convert YAML scenario to new separated evaluation criteria."""
        
        # Create conversation quality from global criteria
        global_criteria = scenario_data.get('global_criteria', {})
        conversation_quality = ConversationQuality(
            efficiency_score=0.0,  # Will be calculated during evaluation
            clarity_score=0.0,     # Will be calculated during evaluation
            user_satisfaction_score=0.0,  # Will be calculated during evaluation
            total_turns=0,         # Will be filled during evaluation
            user_clarification_requests=0,  # Will be filled during evaluation
            bot_clarification_requests=0    # Will be filled during evaluation
        )
        
        # Create task completion from task criteria
        task_criteria = scenario_data.get('task_criteria', {})
        
        # Nutrition requirements
        nutrition = NutritionRequirements()
        if 'nutrition_targets' in task_criteria:
            targets = task_criteria['nutrition_targets']
            nutrition.calorie_target_met = 'calories' in targets
            nutrition.protein_target_met = 'protein' in targets
            nutrition.carb_target_met = 'carbs' in targets
        nutrition.nutrition_education_provided = task_criteria.get('nutrition_education_required', False)
        
        # Dietary compliance
        dietary_compliance = DietaryCompliance(
            safety_score=0.0,      # Will be calculated during evaluation
            preference_score=0.0   # Will be calculated during evaluation
        )
        
        # Meal planning specifics (simplified for conversation testing)
        meal_planning = MealPlanningSpecifics()
        # Focus only on basic conversation acknowledgment, not detailed meal planning
        meal_planning.instructions_clear = True  # Assume instructions should be clear
        
        # Create task completion
        task_completion = TaskCompletion(
            goal_achieved=False,  # Will be determined during evaluation
            goal_achievement_score=0.0,  # Will be calculated during evaluation
            nutrition=nutrition,
            dietary_compliance=dietary_compliance,
            meal_planning=meal_planning,
            domain_specific_score=0.0  # Will be calculated during evaluation
        )
        
        return CombinedEvaluation(
            scenario_id=scenario_data['scenario_id'],
            conversation_quality=conversation_quality,
            task_completion=task_completion,
            overall_score=0.0,  # Will be calculated during evaluation
            recommendation="pending",  # Will be determined during evaluation
            summary=scenario_data.get('description', 'Test scenario evaluation')
        )


# Global loader instance
scenario_loader = ScenarioLoader()


def load_scenario_for_testing(scenario_id: str) -> Optional[TestScenario]:
    """Load a scenario in legacy TestScenario format for backward compatibility."""
    scenario_data = scenario_loader.get_scenario_by_id(scenario_id)
    if scenario_data:
        return scenario_loader.convert_yaml_to_test_scenario(scenario_data)
    return None


def load_evaluation_criteria(scenario_id: str) -> Optional[CombinedEvaluation]:
    """Load evaluation criteria for a scenario using the new separated model."""
    scenario_data = scenario_loader.get_scenario_by_id(scenario_id)
    if scenario_data:
        return scenario_loader.convert_yaml_to_evaluation_criteria(scenario_data)
    return None


def list_available_scenarios() -> List[str]:
    """List all available scenario IDs."""
    return scenario_loader.list_all_scenarios()


def get_scenarios_by_category(category: str) -> Dict[str, TestScenario]:
    """Get all scenarios in a category as TestScenario objects."""
    yaml_scenarios = scenario_loader.get_scenarios_by_category(category)
    return {
        scenario_id: scenario_loader.convert_yaml_to_test_scenario(scenario_data)
        for scenario_id, scenario_data in yaml_scenarios.items()
    }


__all__ = [
    "ScenarioLoader",
    "scenario_loader",
    "load_scenario_for_testing",
    "load_evaluation_criteria", 
    "list_available_scenarios",
    "get_scenarios_by_category"
] 