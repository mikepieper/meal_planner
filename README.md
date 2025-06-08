# Interactive Meal Planning Chatbot

A chatbot built with LangGraph and Gradio that helps you plan meals and manage your meal plan interactively.

## Features

- Add, remove, and modify meal items for breakfast, lunch, and dinner
- Track changes to your meal plan
- Interactive chat interface with real-time meal plan updates


## Poetry
```bash
eval $(poetry env activate)
```

## Usage

1. Run the application:
   ```bash
   python app.py
   ```
2. Open the provided URL in your browser (typically http://127.0.0.1:7860)
3. Start chatting with the meal planning assistant!

## Example Commands

- "Add 2 eggs to breakfast"
- "Add 1 cup of rice and 200 grams of chicken to lunch"
- "Remove the eggs from breakfast"
- "Clear my dinner plan"
- "Change the amount of rice to 2 cups"

## Project Structure

- `app.py`: Main application with LangGraph and Gradio setup
- `src/models.py`: Data models for meal planning
- `src/meal_planning.py`: Functions for manipulating meal plans 