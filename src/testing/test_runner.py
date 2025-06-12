"""Test runner for orchestrating automated chatbot testing."""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from langchain_core.messages import AIMessage, HumanMessage
import langsmith
from langsmith import traceable

from src.testing.test_scenarios import TestScenario, get_scenario_by_id, get_all_scenario_ids

# Import simple scenarios if available
try:
    from src.testing.simple_test_scenarios import get_simple_scenario_by_id
except ImportError:
    get_simple_scenario_by_id = None
from src.testing.user_agent import user_agent, initialize_user_state, UserAgentState
from src.testing.validation_agent import validation_agent, ValidationState, save_validation_report, ValidationReport
from src.agent import graph as meal_planning_graph
from src.models import create_initial_state


class TestRunner:
    """Orchestrates automated testing of the meal planning chatbot."""
    
    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = output_dir
        self.meal_planning_agent = meal_planning_graph
        self.user_simulation_agent = user_agent
        self.validation_agent = validation_agent
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    @traceable(name="run_single_test")
    async def run_single_test(self, scenario_id: str) -> ValidationReport:
        """Run a single test scenario."""
        
        # Get scenario - try simple scenarios first, then regular
        scenario = None
        if get_simple_scenario_by_id:
            scenario = get_simple_scenario_by_id(scenario_id)
        if not scenario:
            scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_id}' not found")
        
        print(f"\n{'='*60}")
        print(f"Running test: {scenario_id}")
        print(f"Persona: {scenario.persona.name}")
        print(f"Goal: {scenario.goal.value}")
        print(f"{'='*60}\n")
        
        # Run the conversation simulation
        conversation_messages = await self._simulate_conversation(scenario)
        
        # Get the final user state
        final_user_state = self.user_state  # Saved from simulation
        
        # Validate the conversation
        validation_report = await self._validate_conversation(
            scenario, conversation_messages, final_user_state
        )
        
        # Save results
        json_file, summary_file = save_validation_report(validation_report, self.output_dir)
        print(f"\nResults saved:")
        print(f"  - JSON: {json_file}")
        print(f"  - Summary: {summary_file}")
        
        # Print summary
        print(f"\nTest Summary:")
        print(f"  - Overall Score: {validation_report.overall_score:.2f}/1.0")
        print(f"  - Recommendation: {validation_report.recommendation.upper()}")
        print(f"  - Goal Achieved: {'✅ Yes' if validation_report.goal_achieved else '❌ No'}")
        
        return validation_report
    
    @traceable(name="simulate_conversation")
    async def _simulate_conversation(self, scenario: TestScenario) -> List[Any]:
        """Simulate a conversation between user agent and chatbot."""
        
        # Initialize user agent with scenario
        user_state = initialize_user_state(scenario)
        
        # Initialize chatbot state
        chatbot_config = {"configurable": {"thread_id": f"test_{scenario.scenario_id}"}}
        
        conversation_messages = []
        turn_count = 0
        
        print("Starting conversation simulation...\n")
        
        while not user_state.should_end and turn_count < scenario.max_turns:
            # User turn
            print(f"Turn {turn_count + 1}:")
            
            # Get the user's message (first turn should already have initial message)
            if turn_count == 0:
                # Use the initial message from state initialization
                last_user_msg = user_state.messages[-1].content
            else:
                # Let user agent process previous response and generate next message
                user_config = {"configurable": {"thread_id": f"user_{scenario.scenario_id}"}, "recursion_limit": 50}
                user_response = await self.user_simulation_agent.ainvoke(user_state, config=user_config)
                
                # Extract the updated state from the response
                if isinstance(user_response, dict):
                    # Update the user_state with the returned values
                    for key, value in user_response.items():
                        if hasattr(user_state, key):
                            setattr(user_state, key, value)
                else:
                    user_state = user_response
                
                # Check if conversation should end after user processing
                if user_state.should_end:
                    break
                
                # Get the newly generated user message
                last_user_msg = user_state.messages[-1].content
            
            print(f"User: {last_user_msg}")
            
            # Send to chatbot
            # Initialize proper state on first turn
            if turn_count == 0:
                initial_state = create_initial_state()
                initial_state["messages"] = [HumanMessage(content=last_user_msg)]
                chatbot_response = await self.meal_planning_agent.ainvoke(
                    initial_state,
                    config=chatbot_config
                )
            else:
                chatbot_response = await self.meal_planning_agent.ainvoke(
                    {"messages": [HumanMessage(content=last_user_msg)]},
                    config=chatbot_config
                )
            
            # Get assistant response
            assistant_msg = chatbot_response["messages"][-1]
            print(f"Assistant: {assistant_msg.content[:200]}..." if len(assistant_msg.content) > 200 else f"Assistant: {assistant_msg.content}")
            print()
            
            # Add to conversation
            conversation_messages.extend([
                HumanMessage(content=last_user_msg),
                assistant_msg
            ])
            
            # Update user state with assistant response
            user_state.messages.append(assistant_msg)
            
            turn_count += 1
        
        # Save final user state for validation
        self.user_state = user_state
        
        print(f"\nConversation ended after {turn_count} turns")
        print(f"End reason: {user_state.end_reason or 'Unknown'}")
        
        return conversation_messages
    
    @traceable(name="validate_conversation")
    async def _validate_conversation(
        self, 
        scenario: TestScenario, 
        conversation: List[Any], 
        user_state: UserAgentState
    ) -> ValidationReport:
        """Validate a completed conversation."""
        
        print("\nValidating conversation...")
        
        # Initialize validation state
        validation_state = ValidationState(
            scenario=scenario,
            conversation=conversation,
            user_state=user_state
        )
        
        # Run validation
        result = await self.validation_agent.ainvoke(validation_state)
        
        return result["report"]
    
    async def run_multiple_tests(self, scenario_ids: Optional[List[str]] = None) -> Dict[str, ValidationReport]:
        """Run multiple test scenarios."""
        
        if scenario_ids is None:
            scenario_ids = get_all_scenario_ids()
        
        print(f"Running {len(scenario_ids)} test scenarios...")
        
        results = {}
        for scenario_id in scenario_ids:
            try:
                report = await self.run_single_test(scenario_id)
                results[scenario_id] = report
            except Exception as e:
                print(f"Error running test {scenario_id}: {e}")
                continue
        
        # Generate aggregate report
        self._generate_aggregate_report(results)
        
        return results
    
    def _generate_aggregate_report(self, results: Dict[str, ValidationReport]):
        """Generate an aggregate report from multiple test results."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"{self.output_dir}/aggregate_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Aggregate Test Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Tests**: {len(results)}\n\n")
            
            # Summary statistics
            passed = sum(1 for r in results.values() if r.recommendation == "pass")
            needs_improvement = sum(1 for r in results.values() if r.recommendation == "needs_improvement")
            failed = sum(1 for r in results.values() if r.recommendation == "fail")
            
            f.write("## Summary Statistics\n")
            f.write(f"- **Passed**: {passed} ({passed/len(results)*100:.1f}%)\n")
            f.write(f"- **Needs Improvement**: {needs_improvement} ({needs_improvement/len(results)*100:.1f}%)\n")
            f.write(f"- **Failed**: {failed} ({failed/len(results)*100:.1f}%)\n\n")
            
            # Average scores
            avg_overall = sum(r.overall_score for r in results.values()) / len(results)
            avg_goal = sum(r.goal_achievement_score for r in results.values()) / len(results)
            avg_efficiency = sum(r.efficiency_score for r in results.values()) / len(results)
            avg_clarity = sum(r.clarity_score for r in results.values()) / len(results)
            avg_satisfaction = sum(r.user_satisfaction_score for r in results.values()) / len(results)
            
            f.write("## Average Scores\n")
            f.write(f"- **Overall**: {avg_overall:.2f}\n")
            f.write(f"- **Goal Achievement**: {avg_goal:.2f}\n")
            f.write(f"- **Efficiency**: {avg_efficiency:.2f}\n")
            f.write(f"- **Clarity**: {avg_clarity:.2f}\n")
            f.write(f"- **User Satisfaction**: {avg_satisfaction:.2f}\n\n")
            
            # Individual test results
            f.write("## Individual Test Results\n\n")
            for scenario_id, report in results.items():
                f.write(f"### {scenario_id}\n")
                f.write(f"- **Score**: {report.overall_score:.2f}\n")
                f.write(f"- **Recommendation**: {report.recommendation}\n")
                f.write(f"- **Goal Achieved**: {'✅' if report.goal_achieved else '❌'}\n")
                f.write(f"- **Key Issues**: {', '.join(report.pain_points[:3]) if report.pain_points else 'None'}\n\n")
            
            # Common issues
            all_pain_points = []
            all_immediate_fixes = []
            for report in results.values():
                all_pain_points.extend(report.pain_points)
                all_immediate_fixes.extend(report.immediate_fixes)
            
            if all_pain_points:
                f.write("## Common Pain Points\n")
                # Count frequency
                pain_point_counts = {}
                for point in all_pain_points:
                    pain_point_counts[point] = pain_point_counts.get(point, 0) + 1
                
                # Sort by frequency
                sorted_points = sorted(pain_point_counts.items(), key=lambda x: x[1], reverse=True)
                for point, count in sorted_points[:10]:
                    f.write(f"- {point} (occurred {count} times)\n")
                f.write("\n")
            
            if all_immediate_fixes:
                f.write("## Top Priority Fixes\n")
                fix_counts = {}
                for fix in all_immediate_fixes:
                    fix_counts[fix] = fix_counts.get(fix, 0) + 1
                
                sorted_fixes = sorted(fix_counts.items(), key=lambda x: x[1], reverse=True)
                for fix, count in sorted_fixes[:10]:
                    f.write(f"- {fix} (suggested {count} times)\n")
        
        print(f"\nAggregate report saved: {report_file}")


async def run_test_scenario(scenario_id: str):
    """Convenience function to run a single test scenario."""
    runner = TestRunner()
    return await runner.run_single_test(scenario_id)


async def run_all_tests():
    """Convenience function to run all test scenarios."""
    runner = TestRunner()
    return await runner.run_multiple_tests()


# Example usage in Jupyter or script
if __name__ == "__main__":
    # Run a single test
    # asyncio.run(run_test_scenario("busy_professional_weekly"))
    
    # Run all tests
    # asyncio.run(run_all_tests())
    
    # Run specific tests
    # runner = TestRunner()
    # asyncio.run(runner.run_multiple_tests(["busy_professional_weekly", "fitness_enthusiast_daily"]))
    
    print("Test runner ready. Use run_test_scenario() or run_all_tests()")


__all__ = ["TestRunner", "run_test_scenario", "run_all_tests"] 