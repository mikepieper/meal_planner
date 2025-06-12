# LangGraph Command Pattern Guide

## Overview

The Command pattern is the recommended approach for state updates in LangGraph tools. Instead of directly mutating state, tools return `Command` objects that describe how the state should be updated.

## Why Use Commands?

### 1. **Immutability**
Commands ensure state updates are immutable and predictable:
```python
# ❌ Direct mutation (not recommended)
state[meal_type].append(new_item)

# ✅ Command pattern (recommended)
return Command(update={
    meal_type: state[meal_type] + [new_item]
})
```

### 2. **Testability**
Tools become pure functions without side effects:
```python
# Easy to test - just check the returned Command
command = add_meal_item("breakfast", "eggs", "2", state, "tool_id")
assert command.update["breakfast"][-1].food == "eggs"
```

### 3. **Consistency**
All state changes follow the same pattern, making the codebase more maintainable.

### 4. **Advanced Features**
Commands support advanced control flow:
- `goto`: Navigate to different nodes
- `interrupt`: Pause execution for human input
- Conditional updates based on state

## Command Pattern Examples

### Basic State Update
```python
@tool
def add_meal_item(...) -> Command:
    """Add a food item to a meal."""
    new_item = MealItem(food=food, amount=amount, unit=unit)
    
    return Command(
        update={
            meal_type: state[meal_type] + [new_item],
            "current_meal": meal_type
        }
    )
```

### Read-Only Tools
Tools that don't modify state can return strings:
```python
@tool
def view_current_meals(state: ...) -> str:
    """View current meal plan - no state changes."""
    return "Current meals: ..."
```

### Complex Updates
```python
@tool
def generate_meal_plan(...) -> Command:
    """Generate and set complete meal plan."""
    # Generate meals...
    
    return Command(
        update={
            "breakfast": breakfast_items,
            "lunch": lunch_items,
            "dinner": dinner_items,
            "snacks": snack_items,
            "last_generated": datetime.now()
        }
    )
```

### Conditional Updates
```python
@tool
def remove_meal_item(...) -> Command:
    """Remove item if it exists."""
    updated_meal = [item for item in state[meal_type] 
                    if item.food.lower() != food.lower()]
    
    if len(updated_meal) == len(state[meal_type]):
        # Item not found - no update needed
        return Command(update={})
    
    return Command(
        update={meal_type: updated_meal}
    )
```

## Best Practices

### 1. **Always Return New Objects**
```python
# ❌ Bad - modifies existing list
meal_list = state[meal_type]
meal_list.append(new_item)
return Command(update={meal_type: meal_list})

# ✅ Good - creates new list
return Command(update={
    meal_type: state[meal_type] + [new_item]
})
```

### 2. **Handle Tool Messages Automatically**
The Command pattern automatically adds tool messages to the conversation:
```python
# The tool's response is automatically added as a ToolMessage
# You don't need to manually add messages
return Command(update={...})
```

### 3. **Use Type Hints**
```python
from langgraph.types import Command

@tool
def my_tool(...) -> Command:  # Clear return type
    ...
```

### 4. **Keep Updates Minimal**
Only update what's necessary:
```python
# ❌ Updating everything
return Command(update={
    "breakfast": state["breakfast"],
    "lunch": state["lunch"],  # Unchanged
    "dinner": state["dinner"],  # Unchanged
    ...
})

# ✅ Update only what changed
return Command(update={
    "breakfast": new_breakfast
})
```

## Migration from Direct Mutation

If you have existing tools using direct mutation:

```python
# Old approach
@tool
def add_item(food: str, state: State) -> str:
    state["items"].append(food)
    return f"Added {food}"

# New approach
@tool 
def add_item(food: str, state: State) -> Command:
    return Command(
        update={"items": state["items"] + [food]}
    )
```

## Summary

The Command pattern provides a clean, testable, and maintainable approach to state management in LangGraph. By returning Commands instead of directly mutating state, your tools become:

- **Predictable**: Clear inputs and outputs
- **Testable**: No side effects
- **Composable**: Easy to chain operations
- **Debuggable**: State changes are explicit

This approach aligns with functional programming principles and makes your LangGraph applications more robust and easier to maintain. 