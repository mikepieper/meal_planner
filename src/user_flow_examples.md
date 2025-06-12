# User Flow Examples - Simplified ReAct Architecture

## Example 1: Simple Meal Addition
**User Input**: "Add eggs and toast to my breakfast"

**Flow**:
1. **Agent** → Reasoning: User wants to add specific items to breakfast
2. **Agent** → Calls `add_meal_item("breakfast", "eggs", "2", "large")`
3. **Tool Result** → "Added 2 large of eggs to breakfast."
4. **Agent** → Calls `add_meal_item("breakfast", "toast", "2", "slices")`
5. **Tool Result** → "Added 2 slices of toast to breakfast."
6. **Agent** → Response: "Great! I've added 2 large eggs and 2 slices of toast to your breakfast. Would you like me to show you the nutritional breakdown or add anything else?"
7. **END**

## Example 2: Complex Multi-Intent Request
**User Input**: "I need a 2000 calorie high-protein meal plan, I'm vegetarian, and want to add Greek yogurt to breakfast"

**Flow**:
1. **Agent** → Reasoning: Multiple requests - set goals, create plan, add specific item
2. **Agent** → Calls `set_nutrition_goals(2000, "high-protein")`
3. **Tool Result** → "Set nutrition goals: 2000 calories/day with high-protein diet. Targets: 150g protein, 200g carbs, 67g fat."
4. **Agent** → Updates user_profile.dietary_restrictions = ["vegetarian"]
5. **Agent** → Calls `generate_meal_plan({"vegetarian": True})`
6. **Tool Result** → Complete meal plan generated
7. **Agent** → Calls `add_meal_item("breakfast", "Greek yogurt", "1", "cup")`
8. **Tool Result** → "Added 1 cup of Greek yogurt to breakfast."
9. **Agent** → Response: "Perfect! I've created a 2000 calorie high-protein vegetarian meal plan and added Greek yogurt to your breakfast. Let me analyze the nutrition to ensure it meets your goals..."
10. **Agent** → Calls `analyze_daily_nutrition()`
11. **Tool Result** → Nutrition analysis showing plan meets targets
12. **Agent** → Response: "Excellent news! Your meal plan provides 2050 calories with 155g of protein, perfectly meeting your high-protein goals while being completely vegetarian."
13. **END**

## Example 3: Automated Plan Request with Calories
**User Input**: "Create a 1800 calorie meal plan for me"

**Flow**:
1. **Agent** → Reasoning: User wants automated plan with specific calories
2. **Agent** → Calls `set_nutrition_goals(1800, "balanced")`
3. **Tool Result** → "Set nutrition goals: 1800 calories/day with balanced diet..."
4. **Agent** → Calls `generate_meal_plan()`
5. **Tool Result** → Complete meal plan generated
6. **Agent** → Response: "I've created a balanced 1800 calorie meal plan for you! Here's what I've put together: [meal details]. Would you like me to analyze the nutritional breakdown or make any adjustments?"
7. **END**

## Example 4: Progressive Disclosure
**User Input**: "Make me a healthy meal plan"

**Flow**:
1. **Agent** → Reasoning: User wants help but hasn't provided specifics
2. **Agent** → Response: "I'd be happy to create a healthy meal plan for you! To make it perfect for your needs, could you tell me:
   - Your target daily calories (or I can use 2000 as a healthy default)
   - Any dietary restrictions or foods you avoid?
   - Any specific health goals (weight loss, muscle gain, etc.)?"
3. **User**: "Let's do 1800 calories, and I don't eat red meat"
4. **Agent** → Updates user_profile.dietary_restrictions = ["no red meat"]
5. **Agent** → Calls `set_nutrition_goals(1800, "balanced")`
6. **Tool Result** → "Set nutrition goals: 1800 calories/day..."
7. **Agent** → Calls `generate_meal_plan({"avoid": ["beef", "pork", "lamb"]})`
8. **Tool Result** → Meal plan generated without red meat
9. **Agent** → Response: "Perfect! I've created an 1800 calorie meal plan without any red meat. Your meals focus on chicken, fish, and plant-based proteins..."
10. **END**

## Example 5: Information Request
**User Input**: "What should I eat for lunch?"

**Flow**:
1. **Agent** → Reasoning: User wants lunch suggestions
2. **Agent** → Calls `suggest_meal("lunch")`
3. **Tool Result** → Three lunch suggestions with portions
4. **Agent** → Response: "Here are three delicious lunch options for you: [suggestions]. Would you like me to add any of these to your meal plan, or would you like to see more options based on specific preferences?"
5. **END**

## Example 6: View and Analyze Current Plan
**User Input**: "Show me what I have so far and analyze the nutrition"

**Flow**:
1. **Agent** → Reasoning: User wants to see current plan and nutrition analysis
2. **Agent** → Calls `view_current_meals()`
3. **Tool Result** → Current meal plan displayed
4. **Agent** → Calls `analyze_daily_nutrition()`
5. **Tool Result** → Nutrition analysis with totals
6. **Agent** → Response: "Here's your current meal plan: [plan details]. The nutritional analysis shows: [nutrition details]. Based on this, you might want to add more protein to meet your goals. Would you like some suggestions?"
7. **END**

## Key Improvements in New Architecture

### ✅ **No Dead Ends**
- Single agent can handle any follow-up naturally
- Tools can be called in any combination

### ✅ **Natural Conversation Flow**
- Agent maintains context throughout
- Can handle complex requests by breaking them down
- Provides helpful follow-up suggestions

### ✅ **Flexible Tool Usage**
- Agent intelligently selects and combines tools
- Can handle multi-step operations seamlessly
- No rigid routing constraints

### ✅ **Better User Experience**
- Conversational and friendly
- Proactive suggestions
- Progressive disclosure when needed
- Always offers next steps 