#!/usr/bin/env python3
"""Command-line interface for running automated chatbot tests."""

import asyncio
import argparse
import sys
from typing import List

from src.testing import (
    run_test_scenario,
    run_all_tests,
    get_all_scenario_ids,
    get_scenario_by_id,
    TestRunner
)


def list_scenarios():
    """List all available test scenarios."""
    print("\nAvailable Test Scenarios:")
    print("=" * 60)
    
    for scenario_id in get_all_scenario_ids():
        scenario = get_scenario_by_id(scenario_id)
        print(f"\n{scenario_id}:")
        print(f"  Persona: {scenario.persona.name}")
        print(f"  Goal: {scenario.goal.value}")
        print(f"  Restrictions: {', '.join(scenario.persona.dietary_restrictions) or 'None'}")
        print(f"  Max turns: {scenario.max_turns}")


async def main():
    parser = argparse.ArgumentParser(
        description="Run automated tests for the meal planning chatbot"
    )
    
    parser.add_argument(
        "command",
        choices=["run", "list"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--scenario",
        "-s",
        type=str,
        help="Specific scenario ID to run (for 'run' command)"
    )
    
    parser.add_argument(
        "--scenarios",
        "-m",
        type=str,
        nargs="+",
        help="Multiple scenario IDs to run (for 'run' command)"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="test_results",
        help="Output directory for test results (default: test_results)"
    )
    
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Run all test scenarios (for 'run' command)"
    )
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_scenarios()
        return
    
    elif args.command == "run":
        runner = TestRunner(output_dir=args.output)
        
        if args.all:
            print("Running all test scenarios...")
            results = await runner.run_multiple_tests()
            
            # Print summary
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            
            passed = sum(1 for r in results.values() if r.recommendation == "pass")
            total = len(results)
            
            print(f"Total tests: {total}")
            print(f"Passed: {passed} ({passed/total*100:.1f}%)")
            print(f"Failed/Needs improvement: {total - passed}")
            
        elif args.scenarios:
            print(f"Running {len(args.scenarios)} test scenarios...")
            results = await runner.run_multiple_tests(args.scenarios)
            
        elif args.scenario:
            print(f"Running test scenario: {args.scenario}")
            report = await run_test_scenario(args.scenario)
            
            # Print detailed results
            print("\n" + "=" * 60)
            print("DETAILED RESULTS")
            print("=" * 60)
            print(f"Overall Score: {report.overall_score:.2f}/1.0")
            print(f"Recommendation: {report.recommendation.upper()}")
            
            if report.immediate_fixes:
                print("\nImmediate Fixes Needed:")
                for fix in report.immediate_fixes[:5]:
                    print(f"  - {fix}")
                    
        else:
            print("Error: Please specify --scenario, --scenarios, or --all")
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1) 