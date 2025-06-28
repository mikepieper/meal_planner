"""LangSmith integration for meal planning chatbot evaluation."""

import os
from typing import Dict, List, Any, Optional
import yaml
from datetime import datetime
from langsmith import Client, TracerSession
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Example, Dataset
from pydantic import BaseModel

from src.testing.scenario_loader import ScenarioLoader
from src.testing.evaluation_models import (
    ConversationGoal, UserPersona, TestScenario
)


class LangSmithDatasetConfig(BaseModel):
    """Configuration for LangSmith dataset creation."""
    dataset_name: str = "meal-planning-scenarios"
    description: str = "Test scenarios for meal planning chatbot evaluation"
    project_name: str = "meal-planning-evaluation"


class LangSmithConverter:
    """Converts scenarios to LangSmith dataset format."""
    
    def __init__(self, config: LangSmithDatasetConfig = None):
        self.config = config or LangSmithDatasetConfig()
        self.client = Client()
        self.scenario_loader = ScenarioLoader()
    
    def convert_scenario_to_example(self, scenario: TestScenario) -> Dict[str, Any]:
        """Convert a single scenario to LangSmith example format."""
        
        # Input: What goes into our system
        inputs = {
            "persona": {
                "name": scenario.persona.name,
                "communication_style": scenario.persona.communication_style,
                "dietary_restrictions": scenario.persona.dietary_restrictions,
                "health_goals": scenario.persona.health_goals
            },
            "goal": scenario.goal.value,
            "specific_requirements": scenario.specific_requirements,
            "max_turns": scenario.max_turns
        }
        
        # Reference data: What we evaluate against
        reference = {
            "success_criteria": scenario.success_criteria,
            "expected_outcomes": scenario.expected_outcomes,
            "potential_challenges": scenario.potential_challenges,
            "scenario_metadata": {
                "scenario_id": scenario.scenario_id,
                "goal_type": scenario.goal.value,
                "has_dietary_restrictions": len(scenario.persona.dietary_restrictions) > 0,
                "has_nutrition_targets": any(
                    key in scenario.specific_requirements 
                    for key in ["calorie_target", "protein_target", "carb_target"]
                ),
                "communication_style": scenario.persona.communication_style
            }
        }
        
        return {
            "inputs": inputs,
            "outputs": reference,  # LangSmith uses "outputs" for reference data
            "metadata": {
                "scenario_id": scenario.scenario_id,
                "category": self._determine_category(scenario),
                "complexity": self._determine_complexity(scenario),
                "safety_critical": self._is_safety_critical(scenario)
            }
        }
    
    def _determine_category(self, scenario: TestScenario) -> str:
        """Determine scenario category based on content."""
        scenario_id = scenario.scenario_id.lower()
        
        if "basic" in scenario_id:
            return "basic"
        elif "nutrition" in scenario_id:
            return "nutrition"
        elif "safety" in scenario_id:
            return "safety"
        elif "conversation" in scenario_id:
            return "conversation"
        else:
            return "general"
    
    def _determine_complexity(self, scenario: TestScenario) -> str:
        """Determine scenario complexity."""
        complexity_score = 0
        
        # Add complexity for dietary restrictions
        complexity_score += len(scenario.persona.dietary_restrictions)
        
        # Add complexity for specific requirements
        complexity_score += len(scenario.specific_requirements)
        
        # Add complexity for success criteria
        complexity_score += len(scenario.success_criteria)
        
        if complexity_score <= 3:
            return "simple"
        elif complexity_score <= 6:
            return "moderate"
        else:
            return "complex"
    
    def _is_safety_critical(self, scenario: TestScenario) -> bool:
        """Determine if scenario involves safety-critical requirements."""
        # Check for allergy or medical dietary restrictions
        safety_keywords = ["allergy", "allergic", "diabetic", "celiac", "medical", "intolerance"]
        
        for restriction in scenario.persona.dietary_restrictions:
            if any(keyword in restriction.lower() for keyword in safety_keywords):
                return True
        
        return False
    
    def create_dataset_from_yaml(self, yaml_path: str = None) -> Dataset:
        """Create LangSmith dataset from scenarios YAML file."""
        
        if yaml_path is None:
            yaml_path = "scenarios.yaml"
        
        # Load scenarios using our scenario loader
        scenarios = self.scenario_loader.load_all_scenarios()
        
        # Convert scenarios to examples
        examples = []
        for scenario in scenarios:
            example_data = self.convert_scenario_to_example(scenario)
            examples.append(example_data)
        
        # Create or update dataset
        try:
            # Try to get existing dataset
            dataset = self.client.read_dataset(dataset_name=self.config.dataset_name)
            print(f"Found existing dataset: {self.config.dataset_name}")
            
            # Delete existing examples to replace with new ones
            self.client.delete_dataset(dataset_id=dataset.id)
            print("Deleted existing dataset for refresh")
            
        except Exception:
            print(f"Creating new dataset: {self.config.dataset_name}")
        
        # Create new dataset
        dataset = self.client.create_dataset(
            dataset_name=self.config.dataset_name,
            description=self.config.description,
            data_type="kv"  # key-value pairs
        )
        
        # Add examples to dataset
        for example_data in examples:
            self.client.create_example(
                inputs=example_data["inputs"],
                outputs=example_data["outputs"],
                dataset_id=dataset.id,
                metadata=example_data["metadata"]
            )
        
        print(f"Created dataset '{self.config.dataset_name}' with {len(examples)} examples")
        return dataset
    
    def list_datasets(self) -> List[Dataset]:
        """List all datasets in the project."""
        return list(self.client.list_datasets())
    
    def get_dataset_examples(self, dataset_name: str = None) -> List[Example]:
        """Get all examples from a dataset."""
        dataset_name = dataset_name or self.config.dataset_name
        dataset = self.client.read_dataset(dataset_name=dataset_name)
        return list(self.client.list_examples(dataset_id=dataset.id))


# Import real evaluators from separate module
from src.testing.langsmith_evaluators import (
    ConversationQualityEvaluator,
    TaskCompletionEvaluator,
    SafetyComplianceEvaluator
)


class LangSmithEvaluationRunner:
    """Runs evaluations using LangSmith framework."""
    
    def __init__(self, config: LangSmithDatasetConfig = None):
        self.config = config or LangSmithDatasetConfig()
        self.client = Client()
        self.converter = LangSmithConverter(config)
        
        # Initialize evaluators
        self.evaluators = [
            ConversationQualityEvaluator(),
            TaskCompletionEvaluator(),
            SafetyComplianceEvaluator()
        ]
    
    def run_evaluation(
        self,
        system_to_evaluate,
        dataset_name: str = None,
        experiment_prefix: str = "meal-planning"
    ) -> str:
        """Run evaluation on a system using LangSmith."""
        
        dataset_name = dataset_name or self.config.dataset_name
        experiment_name = f"{experiment_prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"Running evaluation: {experiment_name}")
        print(f"Dataset: {dataset_name}")
        print(f"Evaluators: {[e.evaluation_name for e in self.evaluators]}")
        
        # Run evaluation using LangSmith
        results = evaluate(
            target=system_to_evaluate,
            data=dataset_name,
            evaluators=self.evaluators,
            experiment_prefix=experiment_prefix,
            max_concurrency=2  # Limit concurrency for meal planning
        )
        
        print(f"Evaluation completed: {experiment_name}")
        return experiment_name
    
    def get_evaluation_results(self, experiment_name: str) -> Dict[str, Any]:
        """Get results from a completed evaluation."""
        
        # This would fetch and format results from LangSmith
        # For now, return placeholder
        return {
            "experiment_name": experiment_name,
            "total_examples": 0,
            "avg_conversation_quality": 0.0,
            "avg_task_completion": 0.0,
            "safety_violations": 0,
            "summary": "Evaluation results placeholder"
        }


def setup_langsmith_evaluation(
    yaml_path: str = None,
    project_name: str = "meal-planning-evaluation"
) -> LangSmithEvaluationRunner:
    """Set up LangSmith evaluation from scratch."""
    
    # Set environment variable for project
    os.environ["LANGCHAIN_PROJECT"] = project_name
    
    config = LangSmithDatasetConfig(project_name=project_name)
    
    # Create converter and dataset
    converter = LangSmithConverter(config)
    dataset = converter.create_dataset_from_yaml(yaml_path)
    
    # Create evaluation runner
    runner = LangSmithEvaluationRunner(config)
    
    print(f"LangSmith evaluation setup complete!")
    print(f"Dataset: {dataset.name} ({dataset.example_count} examples)")
    print(f"Project: {project_name}")
    
    return runner


# Convenience functions for easy usage
def create_dataset_from_scenarios(yaml_path: str = None) -> Dataset:
    """Quick function to create LangSmith dataset from scenarios."""
    converter = LangSmithConverter()
    return converter.create_dataset_from_yaml(yaml_path)


def list_evaluation_datasets() -> List[Dataset]:
    """List all evaluation datasets."""
    converter = LangSmithConverter()
    return converter.list_datasets()


if __name__ == "__main__":
    # Example usage
    print("Setting up LangSmith evaluation...")
    runner = setup_langsmith_evaluation()
    
    print("\nAvailable datasets:")
    for dataset in list_evaluation_datasets():
        print(f"  - {dataset.name}: {dataset.description}")


__all__ = [
    "LangSmithConverter",
    "LangSmithEvaluationRunner", 
    "ConversationQualityEvaluator",
    "TaskCompletionEvaluator",
    "SafetyComplianceEvaluator",
    "setup_langsmith_evaluation",
    "create_dataset_from_scenarios",
    "list_evaluation_datasets"
] 