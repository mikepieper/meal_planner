"""Simplified test runner for LangSmith evaluation."""

import asyncio
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from langsmith import traceable

from src.testing.evaluation_models import TestScenario
from src.testing.scenario_loader import ScenarioLoader
from src.testing.langsmith_integration import setup_langsmith_evaluation
from src.testing.user_agent import user_agent, initialize_user_state
from src.agent import graph as meal_planning_graph


async def simulate_conversation(scenario: TestScenario) -> List[Any]:
    """Simulate a conversation between user agent and chatbot."""
    
    # Initialize user agent with scenario
    user_state = initialize_user_state(scenario)
    
    # Initialize chatbot state
    chatbot_config = {"configurable": {"thread_id": f"test_{scenario.scenario_id}"}}
    
    conversation_messages = []
    turn_count = 0
    
    print(f"Starting conversation: {scenario.persona.name} - {scenario.goal.value}")
    
    while not user_state.should_end and turn_count < scenario.max_turns:
        # Get user message
        if turn_count == 0:
            last_user_msg = user_state.messages[-1].content
        else:
            # Let user agent process and generate next message
            user_config = {"configurable": {"thread_id": f"user_{scenario.scenario_id}"}, "recursion_limit": 50}
            user_response = await user_agent.ainvoke(user_state, config=user_config)
            
            # Update user state
            if isinstance(user_response, dict):
                for key, value in user_response.items():
                    if hasattr(user_state, key):
                        setattr(user_state, key, value)
            else:
                user_state = user_response
            
            if user_state.should_end:
                break
            
            last_user_msg = user_state.messages[-1].content
        
        print(f"Turn {turn_count + 1} - User: {last_user_msg[:100]}...")
        
        # Send to chatbot
        chatbot_response = await meal_planning_graph.ainvoke(
            {"messages": [HumanMessage(content=last_user_msg)]},
            config=chatbot_config
        )
        
        # Get assistant response
        assistant_msg = chatbot_response["messages"][-1]
        print(f"Turn {turn_count + 1} - Assistant: {assistant_msg.content[:100]}...")
        
        # Add to conversation
        conversation_messages.extend([
            HumanMessage(content=last_user_msg),
            assistant_msg
        ])
        
        # Update user state with assistant response
        user_state.messages.append(assistant_msg)
        turn_count += 1
    
    print(f"Conversation ended after {turn_count} turns: {user_state.end_reason or 'Max turns reached'}")
    return conversation_messages


class LangSmithTestRunner:
    """Simple test runner that submits conversations to LangSmith for evaluation."""
    
    def __init__(self):
        self.scenario_loader = ScenarioLoader()
        
        # Set up LangSmith
        try:
            self.langsmith_runner = setup_langsmith_evaluation()
            print("✅ LangSmith integration ready")
        except Exception as e:
            print(f"❌ LangSmith setup failed: {e}")
            raise ValueError(f"LangSmith not available: {e}")
    
    @traceable(name="run_test")
    async def run_test(self, scenario_id: str) -> Dict[str, Any]:
        """Run a single test and evaluate with LangSmith."""
        
        # Get scenario
        all_scenarios = self.scenario_loader.load_all_scenarios()
        scenario = next((s for s in all_scenarios if s.scenario_id == scenario_id), None)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_id}' not found")
        
        print(f"\n🧪 Testing scenario: {scenario_id}")
        
        # Run conversation
        conversation_messages = await simulate_conversation(scenario)
        
        # Format for LangSmith
        conversation_text = self._format_conversation(conversation_messages)
        
        # Run LangSmith evaluation
        scores = await self._evaluate_with_langsmith(scenario, conversation_text)
        
        # Return simple summary (LangSmith has all the details)
        overall_score = (
            0.4 * scores.get("task_completion", 0) + 
            0.3 * scores.get("conversation_quality", 0) + 
            0.3 * scores.get("safety_compliance", 1)
        )
        
        result = {
            "scenario_id": scenario_id,
            "overall_score": overall_score,
            "component_scores": scores,
            "turns": len(conversation_messages) // 2,
            "status": "completed"
        }
        
        print(f"✅ Test completed - Overall: {overall_score:.2f}")
        return result
    
    async def run_batch_tests(self, scenario_ids: List[str] = None) -> str:
        """Run multiple tests using LangSmith's batch evaluation."""
        
        if scenario_ids is None:
            all_scenarios = self.scenario_loader.load_all_scenarios()
            scenario_ids = [s.scenario_id for s in all_scenarios]
        
        print(f"🚀 Running batch evaluation on {len(scenario_ids)} scenarios")
        
        # Create system function for LangSmith batch evaluation
        async def meal_planning_system(inputs: Dict[str, Any]) -> str:
            """System function that LangSmith will evaluate."""
            
            # Reconstruct scenario from LangSmith inputs
            scenario = self._reconstruct_scenario_from_inputs(inputs)
            
            # Run conversation
            conversation_messages = await simulate_conversation(scenario)
            
            # Return formatted conversation for evaluation
            return self._format_conversation(conversation_messages)
        
        # Run batch evaluation through LangSmith
        experiment_name = self.langsmith_runner.run_evaluation(
            meal_planning_system,
            experiment_prefix="meal-planning"
        )
        
        print(f"🎯 Batch evaluation started: {experiment_name}")
        print("📊 View results at: https://smith.langchain.com")
        
        return experiment_name
    
    async def _evaluate_with_langsmith(self, scenario: TestScenario, conversation_text: str) -> Dict[str, float]:
        """Run LangSmith evaluators and return scores."""
        
        # Convert scenario to LangSmith format
        example_data = self.langsmith_runner.converter.convert_scenario_to_example(scenario)
        inputs = example_data["inputs"]
        reference = example_data["outputs"]
        
        # Run evaluators
        scores = {}
        for evaluator in self.langsmith_runner.evaluators:
            try:
                result = evaluator._evaluate_strings(
                    prediction=conversation_text,
                    reference=str(reference),
                    input=str(inputs)
                )
                scores[evaluator.evaluation_name] = result.get("score", 0.0)
            except Exception as e:
                print(f"⚠️  {evaluator.evaluation_name} failed: {e}")
                scores[evaluator.evaluation_name] = 0.0
        
        return scores
    
    def _format_conversation(self, messages: List[Any]) -> str:
        """Format conversation for evaluation."""
        formatted = []
        for msg in messages:
            if hasattr(msg, 'content'):
                role = "User" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
                formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)
    
    def _reconstruct_scenario_from_inputs(self, inputs: Dict[str, Any]) -> TestScenario:
        """Reconstruct scenario from LangSmith inputs for batch evaluation."""
        
        from src.testing.evaluation_models import UserPersona, ConversationGoal
        
        persona_data = inputs.get("persona", {})
        persona = UserPersona(
            name=persona_data.get("name", "Test User"),
            communication_style=persona_data.get("communication_style", "direct"),
            dietary_restrictions=persona_data.get("dietary_restrictions", []),
            health_goals=persona_data.get("health_goals", [])
        )
        
        # Map goal string to enum
        goal_str = inputs.get("goal", "create_daily_plan")
        goal_enum = ConversationGoal.CREATE_DAILY_PLAN  # Default
        for goal_type in ConversationGoal:
            if goal_type.value == goal_str:
                goal_enum = goal_type
                break
        
        return TestScenario(
            scenario_id=f"batch_{persona.name.lower().replace(' ', '_')}",
            persona=persona,
            goal=goal_enum,
            specific_requirements=inputs.get("specific_requirements", {}),
            expected_outcomes=[],
            success_criteria=[],
            max_turns=inputs.get("max_turns", 15)
        )


# Simple convenience functions
async def run_test(scenario_id: str) -> Dict[str, Any]:
    """Run a single test scenario."""
    runner = LangSmithTestRunner()
    return await runner.run_test(scenario_id)


async def run_batch_tests(scenario_ids: List[str] = None) -> str:
    """Run batch evaluation - returns LangSmith experiment name."""
    runner = LangSmithTestRunner()
    return await runner.run_batch_tests(scenario_ids)


if __name__ == "__main__":
    print("LangSmith Test Runner")
    print("Usage:")
    print("  await run_test('scenario_id')")
    print("  await run_batch_tests()")


__all__ = [
    "LangSmithTestRunner",
    "run_test", 
    "run_batch_tests",
    "simulate_conversation"
] 