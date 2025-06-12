#!/usr/bin/env python3
"""Helper script to create new test scenarios."""

import argparse
from typing import List
import json

from src.testing.test_scenarios import (
    TestScenario, 
    UserPersona, 
    ConversationGoal,
    TEST_SCENARIOS
)


def create_test_scenario_interactive():
    """Interactively create a new test scenario."""
    
    print("\n=== Create New Test Scenario ===\n")
    
    # Scenario ID
    scenario_id = input("Scenario ID (e.g., 'elderly_simple_meals'): ").strip()
    
    # User Persona
    print("\n--- User Persona ---")
    name = input("User name: ").strip()
    age = int(input("Age: ").strip())
    
    # Dietary restrictions
    print("\nDietary restrictions (comma-separated, or press Enter for none):")
    restrictions_input = input().strip()
    dietary_restrictions = [r.strip() for r in restrictions_input.split(',')] if restrictions_input else []
    
    # Preferences
    print("\nFood preferences (comma-separated):")
    preferences_input = input().strip()
    preferences = [p.strip() for p in preferences_input.split(',')] if preferences_input else []
    
    # Health goals
    print("\nHealth goals (comma-separated):")
    health_goals_input = input().strip()
    health_goals = [g.strip() for g in health_goals_input.split(',')] if health_goals_input else []
    
    # Other persona attributes
    print("\nCooking skill (beginner/intermediate/advanced): ", end="")
    cooking_skill = input().strip() or "intermediate"
    
    print("Time constraints (or press Enter for none): ", end="")
    time_constraints = input().strip() or None
    
    print("Budget conscious (y/n): ", end="")
    budget_conscious = input().strip().lower() == 'y'
    
    print("Family size: ", end="")
    family_size = int(input().strip() or "1")
    
    print("\nCommunication style (direct/chatty/uncertain): ", end="")
    communication_style = input().strip() or "direct"
    
    print("Decision making (decisive/indecisive/exploratory): ", end="")
    decision_making = input().strip() or "decisive"
    
    print("Tech savviness (low/average/high): ", end="")
    tech_savviness = input().strip() or "average"
    
    # Goal
    print("\n--- Conversation Goal ---")
    print("Available goals:")
    for i, goal in enumerate(ConversationGoal):
        print(f"  {i+1}. {goal.value}")
    goal_idx = int(input("Select goal (number): ").strip()) - 1
    goal = list(ConversationGoal)[goal_idx]
    
    # Specific requirements
    print("\n--- Specific Requirements ---")
    print("Enter requirements as key:value pairs (one per line, empty line to finish):")
    specific_requirements = {}
    while True:
        req = input().strip()
        if not req:
            break
        if ':' in req:
            key, value = req.split(':', 1)
            # Try to parse numbers
            try:
                value = int(value.strip())
            except ValueError:
                try:
                    value = float(value.strip())
                except ValueError:
                    value = value.strip()
            specific_requirements[key.strip()] = value
    
    # Expected outcomes
    print("\n--- Expected Outcomes ---")
    print("Enter expected outcomes (one per line, empty line to finish):")
    expected_outcomes = []
    while True:
        outcome = input().strip()
        if not outcome:
            break
        expected_outcomes.append(outcome)
    
    # Success criteria
    print("\n--- Success Criteria ---")
    print("Enter success criteria (one per line, empty line to finish):")
    success_criteria = []
    while True:
        criterion = input().strip()
        if not criterion:
            break
        success_criteria.append(criterion)
    
    # Potential challenges
    print("\n--- Potential Challenges (optional) ---")
    print("Enter potential challenges (one per line, empty line to finish):")
    potential_challenges = []
    while True:
        challenge = input().strip()
        if not challenge:
            break
        potential_challenges.append(challenge)
    
    # Max turns
    print("\nMaximum conversation turns (default 20): ", end="")
    max_turns = int(input().strip() or "20")
    
    # Create the scenario
    persona = UserPersona(
        name=name,
        age=age,
        dietary_restrictions=dietary_restrictions,
        preferences=preferences,
        health_goals=health_goals,
        cooking_skill=cooking_skill,
        time_constraints=time_constraints,
        budget_conscious=budget_conscious,
        family_size=family_size,
        communication_style=communication_style,
        decision_making=decision_making,
        tech_savviness=tech_savviness
    )
    
    scenario = TestScenario(
        scenario_id=scenario_id,
        persona=persona,
        goal=goal,
        specific_requirements=specific_requirements,
        expected_outcomes=expected_outcomes,
        success_criteria=success_criteria,
        potential_challenges=potential_challenges,
        max_turns=max_turns
    )
    
    return scenario


def generate_scenario_code(scenario: TestScenario) -> str:
    """Generate Python code for a test scenario."""
    
    code = f'''    # Scenario: {scenario.scenario_id}
    TestScenario(
        scenario_id="{scenario.scenario_id}",
        persona=UserPersona(
            name="{scenario.persona.name}",
            age={scenario.persona.age},
            dietary_restrictions={scenario.persona.dietary_restrictions},
            preferences={scenario.persona.preferences},
            health_goals={scenario.persona.health_goals},
            cooking_skill="{scenario.persona.cooking_skill}",
            time_constraints={"'" + scenario.persona.time_constraints + "'" if scenario.persona.time_constraints else "None"},
            budget_conscious={scenario.persona.budget_conscious},
            family_size={scenario.persona.family_size},
            communication_style="{scenario.persona.communication_style}",
            decision_making="{scenario.persona.decision_making}",
            tech_savviness="{scenario.persona.tech_savviness}"
        ),
        goal=ConversationGoal.{scenario.goal.name},
        specific_requirements={json.dumps(scenario.specific_requirements, indent=12).strip()},
        expected_outcomes={json.dumps(scenario.expected_outcomes, indent=12)},
        success_criteria={json.dumps(scenario.success_criteria, indent=12)},
        potential_challenges={json.dumps(scenario.potential_challenges, indent=12) if scenario.potential_challenges else "[]"},
        max_turns={scenario.max_turns}
    ),'''
    
    return code


def validate_scenario(scenario: TestScenario) -> List[str]:
    """Validate a test scenario and return any issues."""
    issues = []
    
    # Check for duplicate ID
    if any(s.scenario_id == scenario.scenario_id for s in TEST_SCENARIOS):
        issues.append(f"Scenario ID '{scenario.scenario_id}' already exists")
    
    # Check for empty required fields
    if not scenario.expected_outcomes:
        issues.append("At least one expected outcome is required")
    
    if not scenario.success_criteria:
        issues.append("At least one success criterion is required")
    
    # Check persona validity
    valid_cooking_skills = ["beginner", "intermediate", "advanced"]
    if scenario.persona.cooking_skill not in valid_cooking_skills:
        issues.append(f"Invalid cooking skill. Must be one of: {valid_cooking_skills}")
    
    valid_communication_styles = ["direct", "chatty", "uncertain"]
    if scenario.persona.communication_style not in valid_communication_styles:
        issues.append(f"Invalid communication style. Must be one of: {valid_communication_styles}")
    
    valid_decision_making = ["decisive", "indecisive", "exploratory"]
    if scenario.persona.decision_making not in valid_decision_making:
        issues.append(f"Invalid decision making style. Must be one of: {valid_decision_making}")
    
    valid_tech_savviness = ["low", "average", "high"]
    if scenario.persona.tech_savviness not in valid_tech_savviness:
        issues.append(f"Invalid tech savviness. Must be one of: {valid_tech_savviness}")
    
    return issues


def main():
    parser = argparse.ArgumentParser(description="Create new test scenarios")
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for the scenario code",
        default="new_scenario.py"
    )
    parser.add_argument(
        "--json",
        "-j",
        help="Also output scenario as JSON",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # Create scenario interactively
    scenario = create_test_scenario_interactive()
    
    # Validate
    issues = validate_scenario(scenario)
    if issues:
        print("\n❌ Validation issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nPlease fix these issues and try again.")
        return
    
    # Generate code
    code = generate_scenario_code(scenario)
    
    print("\n=== Generated Test Scenario Code ===\n")
    print(code)
    
    # Save to file
    with open(args.output, 'w') as f:
        f.write("# Add this to TEST_SCENARIOS in test_scenarios.py:\n\n")
        f.write(code)
    
    print(f"\n✅ Scenario code saved to: {args.output}")
    
    # Optionally save as JSON
    if args.json:
        json_file = args.output.replace('.py', '.json')
        with open(json_file, 'w') as f:
            json.dump(scenario.dict(), f, indent=2)
        print(f"✅ Scenario JSON saved to: {json_file}")
    
    print("\nNext steps:")
    print("1. Review the generated code")
    print("2. Add it to TEST_SCENARIOS in test_scenarios.py")
    print("3. Run the test with: python run_tests.py run --scenario " + scenario.scenario_id)


if __name__ == "__main__":
    main() 