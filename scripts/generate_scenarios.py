#!/usr/bin/env python3
"""
Generate pre-configured scenario templates and assignments for deterministic conversation generation.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Any
import argparse
from collections import defaultdict


def load_character_profiles(profiles_path: Path) -> Dict[str, List[Dict]]:
    """
    Load character profiles and categorize by role.
    
    Args:
        profiles_path: Path to character profiles JSON
        
    Returns:
        Dictionary with 'scammer' and 'victim' profile lists
    """
    with open(profiles_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    scammer_profiles = []
    victim_profiles = []
    
    for profile in data['profiles']:
        if profile['role_preference'] == 'scammer':
            scammer_profiles.append(profile)
        elif profile['role_preference'] == 'victim':
            victim_profiles.append(profile)
    
    return {
        'scammer': scammer_profiles,
        'victim': victim_profiles
    }


def calculate_weight(awareness: str, num_turns: int, awareness_weights: Dict, turn_weights: Dict) -> float:
    """
    Calculate weight for a scenario template based on awareness and turn count.
    
    Args:
        awareness: Victim awareness level
        num_turns: Number of conversation turns
        awareness_weights: Weight distribution for awareness levels
        turn_weights: Weight distribution for turn counts
        
    Returns:
        Combined weight value
    """
    awareness_weight = awareness_weights.get(awareness, 1.0)
    turn_weight = turn_weights.get(str(num_turns), 1.0)
    return awareness_weight * turn_weight


def generate_all_templates(profiles: Dict[str, List[Dict]], 
                          awareness_levels: List[str],
                          turn_range: tuple,
                          awareness_weights: Dict,
                          turn_weights: Dict) -> List[Dict]:
    """
    Generate all possible scenario templates.
    
    Args:
        profiles: Dictionary with scammer and victim profiles
        awareness_levels: List of awareness levels
        turn_range: Tuple of (min_turns, max_turns)
        awareness_weights: Weight distribution for awareness
        turn_weights: Weight distribution for turns
        
    Returns:
        List of scenario templates
    """
    templates = []
    template_id = 1
    
    scammer_profiles = profiles['scammer']
    victim_profiles = profiles['victim']
    
    for scammer in scammer_profiles:
        for victim in victim_profiles:
            for awareness in awareness_levels:
                for num_turns in range(turn_range[0], turn_range[1] + 1):
                    template = {
                        'template_id': f'T{template_id:04d}',
                        'scammer_profile_id': scammer['profile_id'],
                        'victim_profile_id': victim['profile_id'],
                        'victim_awareness': awareness,
                        'num_turns': num_turns,
                        'weight': calculate_weight(awareness, num_turns, awareness_weights, turn_weights),
                        'tags': []
                    }
                    
                    # Add descriptive tags
                    if awareness == 'not' and 'trusting' in victim.get('personality_traits', []):
                        template['tags'].append('high-success')
                    if awareness == 'very' and 'skeptical' in victim.get('personality_traits', []):
                        template['tags'].append('challenging')
                    if 'senior' in victim.get('age_range', ''):
                        template['tags'].append('elderly-target')
                    if 'urgent' in scammer.get('personality_traits', []):
                        template['tags'].append('high-pressure')
                    
                    templates.append(template)
                    template_id += 1
    
    return templates


def create_weighted_list(templates: List[Dict]) -> List[str]:
    """
    Create a weighted list of template IDs for distribution.
    
    Args:
        templates: List of scenario templates with weights
        
    Returns:
        List of template IDs repeated according to weights
    """
    weighted_list = []
    
    # Normalize weights to integers (multiply by 100 for precision)
    for template in templates:
        weight = int(template['weight'] * 100)
        weighted_list.extend([template['template_id']] * weight)
    
    # Shuffle for better distribution
    random.shuffle(weighted_list)
    
    return weighted_list


def assign_templates_to_seeds(seeds: List[Dict], 
                             templates: List[Dict],
                             strategy: str = 'balanced',
                             templates_per_seed: int = 3) -> Dict[str, List[str]]:
    """
    Assign scenario templates to seeds.
    
    Args:
        seeds: List of seed dictionaries
        templates: List of scenario templates
        strategy: Assignment strategy ('balanced', 'weighted', 'category_based')
        templates_per_seed: Number of templates to assign per seed
        
    Returns:
        Dictionary mapping seed IDs to template ID lists
    """
    assignments = {}
    
    if strategy == 'balanced':
        # Simple round-robin assignment
        num_templates = len(templates)
        for i, seed in enumerate(seeds):
            seed_id = seed['seed_id']
            # Assign templates with offset to ensure variety
            offset = (i * templates_per_seed) % num_templates
            assignments[seed_id] = [
                templates[(offset + j) % num_templates]['template_id']
                for j in range(templates_per_seed)
            ]
    
    elif strategy == 'weighted':
        # Use weighted distribution
        weighted_list = create_weighted_list(templates)
        list_len = len(weighted_list)
        
        for i, seed in enumerate(seeds):
            seed_id = seed['seed_id']
            # Pick from weighted list with offset
            offset = (i * templates_per_seed) % list_len
            assignments[seed_id] = [
                weighted_list[(offset + j) % list_len]
                for j in range(templates_per_seed)
            ]
    
    elif strategy == 'category_based':
        # Group templates by characteristics
        category_templates = defaultdict(list)
        
        for template in templates:
            # Group by awareness level primarily
            category = template['victim_awareness']
            category_templates[category].append(template['template_id'])
        
        # Distribute based on seed characteristics
        for seed in seeds:
            seed_id = seed['seed_id']
            # Use seed category to influence template selection
            seed_category = seed.get('scam_category', 'other')
            
            # Mix templates from different awareness levels
            selected = []
            if templates_per_seed >= 3:
                # 2 "not aware", 1 "tiny aware" for most seeds
                selected.extend(random.sample(category_templates['not'], min(2, len(category_templates['not']))))
                selected.extend(random.sample(category_templates['tiny'], min(1, len(category_templates['tiny']))))
            else:
                # Random selection from weighted categories
                for _ in range(templates_per_seed):
                    category = random.choices(['not', 'tiny', 'very'], weights=[0.6, 0.3, 0.1])[0]
                    if category_templates[category]:
                        selected.append(random.choice(category_templates[category]))
            
            assignments[seed_id] = selected[:templates_per_seed]
    
    return assignments


def load_seeds(seeds_path: Path) -> List[Dict]:
    """
    Load seed data from JSON file.
    
    Args:
        seeds_path: Path to seeds JSON file
        
    Returns:
        List of seed dictionaries
    """
    with open(seeds_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_templates(templates: List[Dict], output_path: Path):
    """
    Save scenario templates to JSON file.
    
    Args:
        templates: List of scenario templates
        output_path: Path to save templates
    """
    output = {
        'version': '1.0',
        'generated': '2025-09-10',
        'total_templates': len(templates),
        'templates': templates,
        'distribution_strategy': {
            'method': 'weighted_round_robin',
            'awareness_weights': {
                'not': 0.6,
                'tiny': 0.3,
                'very': 0.1
            },
            'turn_weights': {
                '7': 0.25,
                '8': 0.35,
                '9': 0.25,
                '10': 0.15
            }
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(templates)} scenario templates to {output_path}")


def save_assignments(assignments: Dict[str, List[str]], 
                    output_path: Path,
                    strategy: str):
    """
    Save seed-to-template assignments to JSON file.
    
    Args:
        assignments: Dictionary mapping seed IDs to template IDs
        output_path: Path to save assignments
        strategy: Assignment strategy used
    """
    output = {
        'version': '1.0',
        'generated': '2025-09-10',
        'assignment_method': strategy,
        'total_seeds': len(assignments),
        'templates_per_seed': len(next(iter(assignments.values()))) if assignments else 0,
        'seed_scenarios': assignments
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved assignments for {len(assignments)} seeds to {output_path}")


def analyze_distribution(templates: List[Dict], assignments: Dict[str, List[str]]):
    """
    Analyze and print distribution statistics.
    
    Args:
        templates: List of scenario templates
        assignments: Seed-to-template assignments
    """
    # Create template lookup
    template_dict = {t['template_id']: t for t in templates}
    
    # Count usage statistics
    awareness_counts = defaultdict(int)
    turns_counts = defaultdict(int)
    profile_pair_counts = defaultdict(int)
    
    for seed_id, template_ids in assignments.items():
        for template_id in template_ids:
            if template_id in template_dict:
                template = template_dict[template_id]
                awareness_counts[template['victim_awareness']] += 1
                turns_counts[template['num_turns']] += 1
                pair = f"{template['scammer_profile_id']} + {template['victim_profile_id']}"
                profile_pair_counts[pair] += 1
    
    total_assignments = sum(awareness_counts.values())
    
    print("\n=== Distribution Analysis ===")
    print(f"Total assignments: {total_assignments}")
    
    print("\nVictim Awareness Distribution:")
    for awareness, count in sorted(awareness_counts.items()):
        percentage = (count / total_assignments) * 100
        print(f"  {awareness}: {count} ({percentage:.1f}%)")
    
    print("\nTurn Count Distribution:")
    for turns, count in sorted(turns_counts.items()):
        percentage = (count / total_assignments) * 100
        print(f"  {turns} turns: {count} ({percentage:.1f}%)")
    
    print("\nTop 5 Profile Combinations:")
    sorted_pairs = sorted(profile_pair_counts.items(), key=lambda x: x[1], reverse=True)
    for pair, count in sorted_pairs[:5]:
        percentage = (count / total_assignments) * 100
        print(f"  {pair}: {count} ({percentage:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Generate scenario templates and assignments')
    parser.add_argument('--profiles-path', type=Path, 
                       default=Path('configs/character_profiles.json'),
                       help='Path to character profiles JSON')
    parser.add_argument('--seeds-path', type=Path,
                       default=Path('data/input/deduplicated_seeds_no_email.json'),
                       help='Path to seeds JSON')
    parser.add_argument('--templates-output', type=Path,
                       default=Path('configs/scenario_templates.json'),
                       help='Output path for scenario templates')
    parser.add_argument('--assignments-output', type=Path,
                       default=Path('configs/scenario_assignments.json'),
                       help='Output path for seed assignments')
    parser.add_argument('--strategy', choices=['balanced', 'weighted', 'category_based'],
                       default='weighted',
                       help='Assignment strategy')
    parser.add_argument('--templates-per-seed', type=int, default=3,
                       help='Number of templates to assign per seed')
    parser.add_argument('--seed-limit', type=int, default=None,
                       help='Limit number of seeds to process (for testing)')
    parser.add_argument('--analyze', action='store_true',
                       help='Analyze distribution after generation')
    
    args = parser.parse_args()
    
    # Configuration
    awareness_levels = ['not', 'tiny', 'very']
    turn_range = (7, 10)
    awareness_weights = {'not': 0.6, 'tiny': 0.3, 'very': 0.1}
    turn_weights = {'7': 0.25, '8': 0.35, '9': 0.25, '10': 0.15}
    
    # Load data
    print(f"Loading character profiles from {args.profiles_path}")
    profiles = load_character_profiles(args.profiles_path)
    print(f"  Found {len(profiles['scammer'])} scammer profiles")
    print(f"  Found {len(profiles['victim'])} victim profiles")
    
    print(f"\nLoading seeds from {args.seeds_path}")
    seeds = load_seeds(args.seeds_path)
    if args.seed_limit:
        seeds = seeds[:args.seed_limit]
    print(f"  Processing {len(seeds)} seeds")
    
    # Generate templates
    print("\nGenerating scenario templates...")
    templates = generate_all_templates(
        profiles, 
        awareness_levels,
        turn_range,
        awareness_weights,
        turn_weights
    )
    print(f"  Generated {len(templates)} templates")
    
    # Save templates
    save_templates(templates, args.templates_output)
    
    # Generate assignments
    print(f"\nGenerating seed assignments using '{args.strategy}' strategy...")
    assignments = assign_templates_to_seeds(
        seeds,
        templates,
        strategy=args.strategy,
        templates_per_seed=args.templates_per_seed
    )
    
    # Save assignments
    save_assignments(assignments, args.assignments_output, args.strategy)
    
    # Analyze distribution
    if args.analyze:
        analyze_distribution(templates, assignments)
    
    print("\nDone!")


if __name__ == '__main__':
    main()