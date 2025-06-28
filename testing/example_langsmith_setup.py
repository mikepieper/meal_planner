#!/usr/bin/env python3
"""
Example script showing how to use LangSmith integration for meal planning chatbot evaluation.

This demonstrates:
1. Creating LangSmith datasets from our scenarios.yaml
2. Setting up evaluators
3. Running evaluations (placeholder)

Prerequisites:
- LANGSMITH_API_KEY environment variable set
- langsmith package installed: pip install langsmith
"""

import os
import asyncio
from typing import Dict, Any

# Import our LangSmith integration
from src.testing.langsmith_integration import (
    setup_langsmith_evaluation,
    create_dataset_from_scenarios,
    list_evaluation_datasets,
    LangSmithConverter,
    LangSmithEvaluationRunner
)

# Import our sophisticated evaluators
from src.testing.langsmith_evaluators import (
    ConversationQualityEvaluator,
    TaskCompletionEvaluator,
    SafetyComplianceEvaluator
)

# Import our existing components that we'll evaluate
from src.testing.user_agent import user_agent, initialize_user_state
from src.agent import graph as meal_planning_graph


async def example_system_to_evaluate(inputs: Dict[str, Any]) -> str:
    """
    Example system function that LangSmith will evaluate.
    
    This simulates running our meal planning conversation system.
    In practice, this would:
    1. Initialize user agent with scenario
    2. Run conversation with meal planning bot
    3. Return conversation transcript
    """
    
    # Extract scenario inputs
    persona = inputs.get("persona", {})
    goal = inputs.get("goal", "")
    requirements = inputs.get("specific_requirements", {})
    max_turns = inputs.get("max_turns", 10)
    
    print(f"Running scenario for {persona.get('name', 'User')} with goal: {goal}")
    
    # Simulate a conversation (placeholder)
    # In practice, this would run our full user_agent + meal_planning_graph
    conversation_result = f"""
Conversation with {persona.get('name', 'User')}:
Goal: {goal}
Requirements: {requirements}

User: Hello, I need help with meal planning.
Assistant: I'd be happy to help you with meal planning! What are your goals?
User: {goal}
Assistant: Great! Let me help you create a plan that meets your needs.

[Conversation continues for {max_turns} turns...]

Final result: Meal plan created successfully.
"""
    
    return conversation_result.strip()


def main():
    """Main demonstration function."""
    
    print("=" * 60)
    print("LangSmith Integration Example")
    print("=" * 60)
    
    # Check if LangSmith API key is set
    if not os.getenv("LANGSMITH_API_KEY"):
        print("⚠️  LANGSMITH_API_KEY environment variable not set")
        print("   Set it to run actual LangSmith operations")
        print("   For now, showing what would happen...\n")
        demo_mode = True
    else:
        print("✅ LANGSMITH_API_KEY found\n")
        demo_mode = False
    
    # Step 1: Create dataset from scenarios
    print("Step 1: Creating LangSmith dataset from scenarios.yaml")
    print("-" * 50)
    
    if demo_mode:
        print("📁 Would create dataset 'meal-planning-scenarios'")
        print("📊 Would include all scenarios from scenarios.yaml")
        print("🏷️  Would tag scenarios by category and complexity")
    else:
        try:
            dataset = create_dataset_from_scenarios()
            print(f"✅ Created dataset: {dataset.name}")
            print(f"📊 Examples: {dataset.example_count}")
        except Exception as e:
            print(f"❌ Error creating dataset: {e}")
            demo_mode = True
    
    print()
    
    # Step 2: List available datasets
    print("Step 2: Listing available datasets")
    print("-" * 40)
    
    if demo_mode:
        print("📋 Would list all LangSmith datasets")
    else:
        try:
            datasets = list_evaluation_datasets()
            for dataset in datasets:
                print(f"  📁 {dataset.name}: {dataset.description}")
        except Exception as e:
            print(f"❌ Error listing datasets: {e}")
    
    print()
    
    # Step 3: Setup evaluation runner
    print("Step 3: Setting up evaluation runner")
    print("-" * 42)
    
    if demo_mode:
        print("🔧 Would setup LangSmith evaluation runner")
        print("📝 Would configure evaluators:")
        print("   - ConversationQualityEvaluator")
        print("   - TaskCompletionEvaluator") 
        print("   - SafetyComplianceEvaluator")
    else:
        try:
            runner = setup_langsmith_evaluation()
            print(f"✅ Setup complete")
            print(f"📊 Project: {runner.config.project_name}")
            print(f"🔍 Evaluators: {len(runner.evaluators)}")
        except Exception as e:
            print(f"❌ Error setting up runner: {e}")
            demo_mode = True
    
    print()
    
    # Step 4: Example evaluation run (placeholder)
    print("Step 4: Running evaluation (example)")
    print("-" * 41)
    
    if demo_mode:
        print("🚀 Would run evaluation with:")
        print("   - System: example_system_to_evaluate")
        print("   - Dataset: meal-planning-scenarios")
        print("   - Evaluators: All 3 configured evaluators")
        print("   - Output: Experiment results in LangSmith UI")
    else:
        try:
            print("🚀 Running evaluation...")
            # Note: This would take time as it runs through all scenarios
            # experiment_name = runner.run_evaluation(example_system_to_evaluate)
            # print(f"✅ Evaluation complete: {experiment_name}")
            print("📝 (Commented out to avoid long-running demo)")
        except Exception as e:
            print(f"❌ Error running evaluation: {e}")
    
    print()
    
    # Step 5: Next steps
    print("Step 5: Next steps")
    print("-" * 20)
    print("🔗 View results in LangSmith UI: https://smith.langchain.com")
    print("📊 Compare experiments and track improvements")
    print("🔔 Set up alerts for safety violations")
    print("🔄 Integrate with CI/CD for automated testing")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    
    if demo_mode:
        print("\nTo run with actual LangSmith:")
        print("1. Set LANGSMITH_API_KEY environment variable")
        print("2. Install: pip install langsmith")
        print("3. Run this script again")


def demo_scenario_conversion():
    """Demonstrate how scenarios are converted to LangSmith format."""
    
    print("\n" + "=" * 60)
    print("Scenario Conversion Demo")
    print("=" * 60)
    
    # Load a sample scenario
    from src.testing.scenario_loader import ScenarioLoader
    
    loader = ScenarioLoader()
    scenarios = loader.load_all_scenarios()
    
    if scenarios:
        sample_scenario = scenarios[0]
        print(f"Original scenario: {sample_scenario.scenario_id}")
        print(f"Persona: {sample_scenario.persona.name}")
        print(f"Goal: {sample_scenario.goal}")
        print()
        
        # Convert to LangSmith format
        converter = LangSmithConverter()
        example_data = converter.convert_scenario_to_example(sample_scenario)
        
        print("Converted to LangSmith format:")
        print(f"Inputs: {len(example_data['inputs'])} fields")
        print(f"Outputs: {len(example_data['outputs'])} fields")
        print(f"Metadata: {example_data['metadata']}")
        print()
        
        print("Sample input structure:")
        for key, value in example_data['inputs'].items():
            print(f"  {key}: {type(value).__name__}")
    else:
        print("No scenarios found - check scenarios.yaml")


if __name__ == "__main__":
    # Run main demo
    main()
    
    # Show scenario conversion
    demo_scenario_conversion() 