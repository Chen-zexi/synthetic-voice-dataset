#!/usr/bin/env python3
"""
Generate scenario assignments matching seeds to templates by category.
"""

import json
from datetime import datetime
from typing import Dict, List
import random

def load_seeds(seeds_path: str) -> List[Dict]:
    """Load seed data."""
    with open(seeds_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_templates(templates_path: str) -> Dict[str, List[Dict]]:
    """Load templates grouped by category."""
    with open(templates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Group templates by category
    templates_by_category = {}
    for template in data['templates']:
        category = template['category']
        if category not in templates_by_category:
            templates_by_category[category] = []
        templates_by_category[category].append(template)

    return templates_by_category

def select_templates_for_seed(seed: Dict, templates_by_category: Dict[str, List[Dict]],
                              templates_per_seed: int = 5) -> List[str]:
    """Select templates for a seed based on its meta_tag."""
    meta_tag = seed.get('meta_tag', 'E-commerce Fraud')  # Default if missing

    # Get templates for this category
    category_templates = templates_by_category.get(meta_tag, [])

    if not category_templates:
        print(f"Warning: No templates found for category '{meta_tag}', using E-commerce Fraud")
        category_templates = templates_by_category.get('E-commerce Fraud', [])

    # Weighted random selection based on template weights
    selected = []
    template_pool = category_templates.copy()

    for _ in range(min(templates_per_seed, len(template_pool))):
        if not template_pool:
            break

        # Weight-based selection (prefer higher weight templates)
        weights = [t['weight'] for t in template_pool]
        chosen = random.choices(template_pool, weights=weights, k=1)[0]

        selected.append(chosen['template_id'])
        template_pool.remove(chosen)  # Avoid duplicates

    return selected

def generate_assignments(seeds_path: str, templates_path: str,
                         templates_per_seed: int = 5) -> Dict:
    """Generate scenario assignments."""
    # Set random seed for reproducibility
    random.seed(42)

    # Load data
    seeds = load_seeds(seeds_path)
    templates_by_category = load_templates(templates_path)

    # Generate assignments
    assignments = {}
    for seed in seeds:
        seed_id = seed['seed_id']
        template_ids = select_templates_for_seed(seed, templates_by_category, templates_per_seed)
        assignments[seed_id] = template_ids

        print(f"  {seed_id} ({seed['meta_tag']}): {len(template_ids)} templates")

    return assignments

def main():
    """Generate and save scenario assignments."""
    print("Generating scenario assignments for Malaysian seeds...\n")

    seeds_path = "data/input/malaysian_voice_phishing_seeds_2025.json"
    templates_path = "configs/scenario_templates.json"

    assignments = generate_assignments(seeds_path, templates_path, templates_per_seed=5)

    # Create output structure
    output = {
        "version": "2.0",
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "assignment_method": "category_weighted",
        "total_seeds": len(assignments),
        "templates_per_seed": 5,
        "description": "Scenario assignments for Malaysian scam seeds aligned with meta_tag categories",
        "seed_scenarios": assignments
    }

    # Save to file
    output_path = "configs/scenario_assignments_malaysia.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Generated assignments for {len(assignments)} seeds")
    print(f"✓ Saved to {output_path}")

    # Calculate total scenarios
    total_scenarios = sum(len(templates) for templates in assignments.values())
    print(f"✓ Total scenarios: {total_scenarios}")

if __name__ == "__main__":
    main()
