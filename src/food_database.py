"""
Food Database Module
===================

Provides food items with nutritional information.
Loads food data from CSV file for easy maintenance.
"""

import csv
import os
from typing import Dict
from .nutrition_optimizer import FoodItem


def get_food_database() -> Dict[str, FoodItem]:
    """Load the food database from CSV file."""
    # Get the directory of this module
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Look for foods.csv in parent directory (project root)
    csv_path = os.path.join(os.path.dirname(current_dir), 'foods.csv')
    
    # Fallback to current directory
    if not os.path.exists(csv_path):
        csv_path = os.path.join(current_dir, 'foods.csv')
    
    # Final fallback - create empty dict if no CSV found
    if not os.path.exists(csv_path):
        print(f"Warning: foods.csv not found at {csv_path}")
        return {}
    
    foods = {}
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Parse tags from comma-separated string
                tags = [tag.strip() for tag in row['tags'].split(',') if tag.strip()]
                
                # Create FoodItem
                food_item = FoodItem(
                    id=row['id'],
                    name=row['name'],
                    calories=float(row['calories']),
                    fat=float(row['fat']),
                    carbohydrates=float(row['carbohydrates']),
                    protein=float(row['protein']),
                    unit=row['unit'],
                    max_quantity=int(row['max_quantity']),
                    tags=tags
                )
                
                foods[row['id']] = food_item
                
    except FileNotFoundError:
        print(f"Error: Could not find foods.csv at {csv_path}")
        return {}
    except Exception as e:
        print(f"Error loading food database: {e}")
        return {}
    
    return foods
