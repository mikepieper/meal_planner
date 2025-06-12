#!/usr/bin/env python3
"""Run simple curriculum-based tests for the meal planning chatbot."""

import asyncio
import argparse
import sys
from typing import Optional

from src.testing import TestRunner
from src.testing.simple_test_scenarios import (
    get_simple_scenario_by_id,
    get_scenarios_by_level,
    get_curriculum_progression,
    CurriculumProgress
)


def list_curriculum():
    """List all curriculum scenarios by level."""
    print("\n🎓 CURRICULUM-BASED TEST SCENARIOS")
    print("=" * 60)
    
    for level in [1, 2, 3]:
        scenarios = get_scenarios_by_level(level)
        if scenarios:
            print(f"\n📚 LEVEL {level}: ", end="")
            if level == 1:
                print("Single-Step Tasks (2-3 turns)")
            elif level == 2:
                print("Multi-Step Tasks (4-5 turns)")
            else:
                print("Complex Tasks (7 turns, trajectory eval)")
            
            print("-" * 40)
            
            for scenario in scenarios:
                print(f"\n  🎯 {scenario.scenario_id}")
                print(f"     Goal: {scenario.goal.value}")
                print(f"     Task: {scenario.specific_requirements.get('task', 'N/A')}")
                if scenario.persona.dietary_restrictions:
                    print(f"     Restrictions: {', '.join(scenario.persona.dietary_restrictions)}")


async def run_single_test(scenario_id: str, output_dir: str = "test_results/simple"):
    """Run a single simple test scenario."""
    scenario = get_simple_scenario_by_id(scenario_id)
    if not scenario:
        print(f"❌ Error: Scenario '{scenario_id}' not found")
        return False
    
    print(f"\n🧪 Running test: {scenario_id}")
    print(f"   Level: {'1' if scenario in get_scenarios_by_level(1) else '2' if scenario in get_scenarios_by_level(2) else '3'}")
    print(f"   Max turns: {scenario.max_turns}")
    
    runner = TestRunner(output_dir=output_dir)
    report = await runner.run_single_test(scenario_id)
    
    # Quick result display
    print("\n📊 QUICK RESULTS:")
    print(f"   Score: {report.overall_score:.2f}/1.0")
    print(f"   Status: ", end="")
    
    if report.recommendation == "pass":
        print("✅ PASSED")
    elif report.recommendation == "needs_improvement":
        print("⚠️  NEEDS IMPROVEMENT")
    else:
        print("❌ FAILED")
    
    print(f"   Turns used: {report.total_turns}/{scenario.max_turns}")
    
    if "trajectory" in scenario_id and not report.goal_achieved:
        print(f"   Trajectory: Making progress but incomplete")
    
    return report.recommendation == "pass"


async def run_level(level: int, output_dir: str = "test_results/simple"):
    """Run all scenarios in a specific level."""
    scenarios = get_scenarios_by_level(level)
    if not scenarios:
        print(f"❌ Error: No scenarios found for level {level}")
        return
    
    print(f"\n🎓 Running Level {level} Tests")
    print("=" * 60)
    
    passed = 0
    total = len(scenarios)
    
    for scenario in scenarios:
        success = await run_single_test(scenario.scenario_id, output_dir)
        if success:
            passed += 1
        print("-" * 60)
    
    print(f"\n📈 Level {level} Summary: {passed}/{total} passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Ready for next level.")
    else:
        print("💪 Keep improving! Some tests need work.")


async def run_curriculum(output_dir: str = "test_results/simple"):
    """Run the full curriculum progression."""
    print("\n🎓 STARTING FULL CURRICULUM")
    print("=" * 60)
    print("This will run all tests in order, from simple to complex.")
    print("The chatbot should pass each level before moving to the next.\n")
    
    progress = CurriculumProgress()
    
    for level in [1, 2, 3]:
        print(f"\n{'='*60}")
        print(f"📚 LEVEL {level}")
        print(f"{'='*60}")
        
        scenarios = get_scenarios_by_level(level)
        level_passed = 0
        
        for scenario in scenarios:
            success = await run_single_test(scenario.scenario_id, output_dir)
            if success:
                level_passed += 1
                progress.mark_complete(scenario.scenario_id, True)
        
        # Level summary
        print(f"\n📊 Level {level} Complete: {level_passed}/{len(scenarios)} passed")
        
        if level_passed < len(scenarios):
            print(f"⚠️  Level {level} not fully passed. Consider fixing issues before proceeding.")
        else:
            print(f"✅ Level {level} complete! Moving to next level...")
    
    # Final summary
    print("\n" + "="*60)
    print("🎓 CURRICULUM COMPLETE")
    print("="*60)
    print(f"Level 1: {'✅' if progress.level_1_complete else '❌'}")
    print(f"Level 2: {'✅' if progress.level_2_complete else '❌'}")
    print(f"Level 3: {'✅' if progress.level_3_complete else '❌'}")
    
    total_complete = len(progress.completed_scenarios)
    total_scenarios = len(get_curriculum_progression())
    print(f"\nOverall: {total_complete}/{total_scenarios} scenarios passed ({total_complete/total_scenarios*100:.0f}%)")


async def main():
    parser = argparse.ArgumentParser(
        description="Run simple curriculum-based tests for the meal planning chatbot"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all curriculum scenarios")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run tests")
    run_parser.add_argument(
        "target",
        help="What to run: scenario ID, 'level1', 'level2', 'level3', or 'curriculum'"
    )
    run_parser.add_argument(
        "--output",
        "-o",
        default="test_results/simple",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "list":
        list_curriculum()
    
    elif args.command == "run":
        if args.target == "curriculum":
            await run_curriculum(args.output)
        elif args.target == "level1":
            await run_level(1, args.output)
        elif args.target == "level2":
            await run_level(2, args.output)
        elif args.target == "level3":
            await run_level(3, args.output)
        else:
            # Try running as a single scenario
            success = await run_single_test(args.target, args.output)
            if not success:
                sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1) 