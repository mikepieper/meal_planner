"""
Nutrition Optimization Module
============================

This module provides optimization algorithms for meal planning,
ensuring meals meet nutritional constraints while respecting preferences.
"""

from typing import Dict, Tuple, Any
import random
import math
from copy import deepcopy
from .models import FoodItem, Meal, MealPlan, ConstraintSet, NutrientConstraint


class NutritionOptimizer:
    """Optimizes meal plans to meet nutritional constraints."""

    def __init__(self, food_db: Dict[str, FoodItem], nutrition_profile: ConstraintSet):
        self.food_db = food_db
        self.nutrition_profile = nutrition_profile

    def calculate_fitness(self, meal_plan: MealPlan) -> float:
        """
        Calculate fitness score for a meal plan.
        Lower is better (0 is perfect).
        """
        nutrition = meal_plan.calculate_daily_nutrition(self.food_db)
        fitness = 0.0

        # For each nutrient, calculate deviation from target
        for nutrient in ["calories", "fat", "carbohydrates", "protein"]:
            constraint = getattr(self.nutrition_profile, nutrient)
            value = nutrition[nutrient]

            # Penalty for being outside min/max bounds (heavy penalty)
            if value < constraint.minimum:
                fitness += ((constraint.minimum - value) / constraint.target) ** 2 * 100
            elif value > constraint.maximum:
                fitness += ((value - constraint.maximum) / constraint.target) ** 2 * 100
            else:
                # Penalty for deviation from target (lighter penalty)
                fitness += ((value - constraint.target) / constraint.target) ** 2 * 10

        return fitness

    def generate_neighbor(self, meal: Meal, num_modifications: int = 1) -> Meal:
        """Generate a neighboring meal by adjusting food quantities."""
        neighbor = deepcopy(meal)

        for _ in range(num_modifications):
            if not neighbor.foods:
                break

            # Choose random food to modify
            food_id = random.choice(list(neighbor.foods.keys()))
            food = self.food_db.get(food_id)

            if not food:
                continue

            current_qty = neighbor.foods[food_id]

            # Adjust quantity
            if current_qty <= food.min_quantity:
                neighbor.foods[food_id] = min(current_qty + 0.25, food.max_quantity)
            elif current_qty >= food.max_quantity:
                neighbor.foods[food_id] = max(current_qty - 0.25, food.min_quantity)
            else:
                if random.random() < 0.5:
                    neighbor.foods[food_id] = max(current_qty - 0.25, food.min_quantity)
                else:
                    neighbor.foods[food_id] = min(current_qty + 0.25, food.max_quantity)

            # Remove if quantity is 0
            if neighbor.foods[food_id] == 0:
                del neighbor.foods[food_id]

        return neighbor

    def hill_climb_meal(self, meal: Meal, max_iterations: int = 100) -> Tuple[Meal, float]:
        """Optimize a single meal using hill climbing."""
        current_meal = deepcopy(meal)

        # Create temporary meal plan with just this meal
        temp_plan = MealPlan()
        setattr(temp_plan, meal.meal_type, current_meal)

        current_fitness = self.calculate_fitness(temp_plan)
        best_meal = deepcopy(current_meal)
        best_fitness = current_fitness

        for _ in range(max_iterations):
            # Generate neighbor
            neighbor = self.generate_neighbor(current_meal)

            # Evaluate
            temp_plan = MealPlan()
            setattr(temp_plan, meal.meal_type, neighbor)
            neighbor_fitness = self.calculate_fitness(temp_plan)

            # Accept if better
            if neighbor_fitness < current_fitness:
                current_meal = neighbor
                current_fitness = neighbor_fitness

                if neighbor_fitness < best_fitness:
                    best_meal = deepcopy(neighbor)
                    best_fitness = neighbor_fitness

        return best_meal, best_fitness

    def optimize_meal_plan(self, meal_plan: MealPlan, max_iterations: int = 500) -> Tuple[MealPlan, float]:
        """Optimize entire meal plan using hill climbing."""
        current_plan = deepcopy(meal_plan)
        current_fitness = self.calculate_fitness(current_plan)
        best_plan = deepcopy(current_plan)
        best_fitness = current_fitness

        for iteration in range(max_iterations):
            # Choose which meal to modify
            meals = []
            if current_plan.breakfast:
                meals.append(("breakfast", current_plan.breakfast))
            if current_plan.lunch:
                meals.append(("lunch", current_plan.lunch))
            if current_plan.dinner:
                meals.append(("dinner", current_plan.dinner))

            if not meals:
                break

            meal_type, meal = random.choice(meals)

            # Generate neighbor for this meal
            neighbor_meal = self.generate_neighbor(meal, num_modifications=random.randint(1, 3))

            # Create new plan with modified meal
            neighbor_plan = deepcopy(current_plan)
            setattr(neighbor_plan, meal_type, neighbor_meal)

            # Evaluate
            neighbor_fitness = self.calculate_fitness(neighbor_plan)

            # Accept if better (or with small probability if worse - simulated annealing style)
            if neighbor_fitness < current_fitness or random.random() < 0.1 * math.exp(-iteration/max_iterations):
                current_plan = neighbor_plan
                current_fitness = neighbor_fitness

                if neighbor_fitness < best_fitness:
                    best_plan = deepcopy(neighbor_plan)
                    best_fitness = neighbor_fitness

        return best_plan, best_fitness

    def suggest_meal_improvement(self, meal: Meal, meal_type: str) -> Dict[str, Any]:
        """Suggest improvements for a meal to better meet nutritional targets."""
        # Create a meal plan with just this meal
        temp_plan = MealPlan()
        setattr(temp_plan, meal_type, meal)

        current_nutrition = meal.calculate_nutrition(self.food_db)
        current_fitness = self.calculate_fitness(temp_plan)

        # Optimize
        optimized_meal, optimized_fitness = self.hill_climb_meal(meal, max_iterations=50)
        optimized_nutrition = optimized_meal.calculate_nutrition(self.food_db)

        # Generate suggestions
        suggestions = {
            "current_fitness": current_fitness,
            "optimized_fitness": optimized_fitness,
            "improvement": current_fitness - optimized_fitness,
            "current_nutrition": current_nutrition,
            "optimized_nutrition": optimized_nutrition,
            "changes": []
        }

        # Compare food quantities
        for food_id in set(meal.foods.keys()) | set(optimized_meal.foods.keys()):
            old_qty = meal.foods.get(food_id, 0)
            new_qty = optimized_meal.foods.get(food_id, 0)

            if old_qty != new_qty:
                food = self.food_db.get(food_id)
                if food:
                    if new_qty == 0:
                        suggestions["changes"].append(f"Remove {food.name}")
                    elif old_qty == 0:
                        suggestions["changes"].append(f"Add {new_qty} {food.unit} of {food.name}")
                    else:
                        suggestions["changes"].append(
                            f"Change {food.name} from {old_qty} to {new_qty} {food.unit}"
                        )

        return suggestions


# Example usage and testing
if __name__ == "__main__":
    # Create sample food database
    sample_foods = {
        "oatmeal": FoodItem(
            id="oatmeal",
            name="Oatmeal",
            calories=150,
            fat=3,
            carbohydrates=27,
            protein=5,
            unit="cup",
            tags=["vegetarian", "vegan", "whole-grain"]
        ),
        "banana": FoodItem(
            id="banana",
            name="Banana",
            calories=105,
            fat=0.4,
            carbohydrates=27,
            protein=1.3,
            unit="medium",
            max_quantity=2,
            tags=["vegetarian", "vegan", "fruit"]
        ),
        "almond_butter": FoodItem(
            id="almond_butter",
            name="Almond Butter",
            calories=98,
            fat=9,
            carbohydrates=3,
            protein=3.4,
            unit="tbsp",
            max_quantity=3,
            tags=["vegetarian", "vegan", "nut"]
        )
    }

    # Create nutrition profile
    profile = ConstraintSet(
        calories=NutrientConstraint(minimum=1800, target=2000, maximum=2200),
        fat=NutrientConstraint(minimum=60, target=70, maximum=80),
        carbohydrates=NutrientConstraint(minimum=225, target=250, maximum=275),
        protein=NutrientConstraint(minimum=90, target=100, maximum=110)
    )

    # Create sample meal
    breakfast = Meal(
        id="breakfast1",
        name="Oatmeal Bowl",
        meal_type="breakfast",
        foods={"oatmeal": 1, "banana": 1, "almond_butter": 1}
    )

    # Test optimization
    optimizer = NutritionOptimizer(sample_foods, profile)
    meal_plan = MealPlan(breakfast=breakfast)

    print("Initial nutrition:", breakfast.calculate_nutrition(sample_foods))
    print("Initial fitness:", optimizer.calculate_fitness(meal_plan))

    # Optimize
    optimized_plan, fitness = optimizer.optimize_meal_plan(meal_plan, max_iterations=100)
    print("\nOptimized nutrition:", optimized_plan.breakfast.calculate_nutrition(sample_foods))
    print("Optimized fitness:", fitness)
