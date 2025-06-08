# LangGraph Studio - Meal Planning Agent

This folder contains the configuration for running the Meal Planning Agent in LangGraph Studio.

## Setup

## Running in LangGraph Studio

1. **Open LangGraph Studio**
   
2. **Load the Project**
   - Click "Open" and navigate to this `studio` folder
   - LangGraph Studio will automatically detect the `langgraph.json` configuration

3. **The Graph**
   - The meal planning agent will load with two main nodes:
     - `agent`: The main reasoning node that processes messages
     - `tools`: Executes the various meal planning tools

## Available Tools

The agent has access to these tools:

- **`generate_meal_suggestions`**: Creates meal ideas based on preferences
- **`set_nutrition_goals`**: Sets daily calorie and macro targets
- **`optimize_meal_nutrition`**: Adjusts portions to meet nutritional goals
- **`analyze_daily_nutrition`**: Reviews the complete daily nutrition
- **`save_meal_to_plan`**: Adds meals to the daily plan

## Example Conversations

Use the example states in `example_states.json` to quickly test different scenarios:

1. **Vegetarian High Protein**: Muscle-building focused vegetarian meals
2. **Low Carb Weight Loss**: Weight loss with carb restriction
3. **Quick Meals**: Fast preparation for busy professionals
4. **Athlete Performance**: High-calorie endurance training
5. **Meal Optimization**: Optimize existing meals for nutrition targets

## Testing in Studio

1. **Start a New Session**
   - Click "New Session" in LangGraph Studio
   - Optionally load an example state

2. **Interact with the Agent**
   - Type messages in the chat interface
   - Watch the graph visualization show the flow
   - See tool calls and responses in real-time

3. **Inspect State**
   - View the current meal plan
   - Check nutrition calculations
   - See conversation history

## Debugging Tips

- **Enable Tracing**: The configuration automatically enables LangSmith tracing
- **Check Tool Outputs**: Click on tool nodes to see their inputs/outputs
- **State Inspector**: Use the state inspector to see all state variables
- **Message History**: Review the full conversation in the messages panel

## Common Workflows

### Creating a Daily Meal Plan
```
User: I need a 2000 calorie vegetarian meal plan with high protein
Agent: [Sets nutrition goals, suggests meals for breakfast/lunch/dinner]
User: Can you optimize the breakfast for more protein?
Agent: [Runs optimization, adjusts portions]
```

### Quick Meal Suggestions
```
User: Give me a quick lunch idea under 15 minutes
Agent: [Generates quick meal options]
User: Add that to my meal plan
Agent: [Saves the meal]
```

### Nutrition Analysis
```
User: Analyze my current meal plan
Agent: [Reviews total nutrition vs. targets]
User: What should I add to meet my protein goal?
Agent: [Suggests high-protein additions]
``` 