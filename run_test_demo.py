#!/usr/bin/env python3
"""Demo script to run the automated testing framework."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Now import testing framework
from src.testing import run_test_scenario, get_all_scenario_ids

async def main():
    """Run a demonstration of the testing framework."""
    
    print("=" * 60)
    print("Meal Planning Chatbot - Automated Testing Demo")
    print("=" * 60)
    
    # Verify environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("Please ensure your .env file contains OPENAI_API_KEY")
        return
    
    print("✅ Environment loaded successfully")
    
    # Show available scenarios
    print("\nAvailable test scenarios:")
    scenarios = get_all_scenario_ids()
    for i, scenario_id in enumerate(scenarios[:5], 1):  # Show first 5
        print(f"  {i}. {scenario_id}")
    print(f"  ... and {len(scenarios) - 5} more")
    
    # Run a single test
    test_to_run = "busy_professional_weekly"
    print(f"\nRunning test: {test_to_run}")
    print("-" * 60)
    
    try:
        # Run the test
        report = await run_test_scenario(test_to_run)
        
        # Display results
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Scenario: {report.scenario_id}")
        print(f"Overall Score: {report.overall_score:.2f}/1.0")
        print(f"Recommendation: {report.recommendation.upper()}")
        print(f"Goal Achieved: {'✅ Yes' if report.goal_achieved else '❌ No'}")
        
        print(f"\nDetailed Scores:")
        print(f"  - Goal Achievement: {report.goal_achievement_score:.2f}")
        print(f"  - Efficiency: {report.efficiency_score:.2f} ({report.total_turns} turns)")
        print(f"  - Clarity: {report.clarity_score:.2f}")
        print(f"  - User Satisfaction: {report.user_satisfaction_score:.2f}")
        
        if report.pain_points:
            print(f"\nIdentified Issues:")
            for i, point in enumerate(report.pain_points[:3], 1):
                print(f"  {i}. {point}")
        
        if report.immediate_fixes:
            print(f"\nSuggested Improvements:")
            for i, fix in enumerate(report.immediate_fixes[:3], 1):
                print(f"  {i}. {fix}")
        
        print(f"\nFull report saved to: test_results/")
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting automated test demo...")
    asyncio.run(main()) 