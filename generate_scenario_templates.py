#!/usr/bin/env python3
"""
Generate scenario templates for Malaysian scam data with proper proportions.
"""

import json
from datetime import datetime
from typing import List, Dict

#Category proportions based on Malaysian scam statistics
CATEGORY_PROPORTIONS = {
    "E-commerce Fraud": 0.232,  # 23.2% (adjusted from 33.2% to make room for Delivery)
    "Delivery Scam": 0.10,      # 10% (part of original E-commerce)
    "Voice Scam": 0.15,         # 15% Part of 30% Phone Message Scam
    "SMS Scam": 0.10,           # 10% Part of 30% Phone Message Scam
    "Giveaway Scam": 0.05,      # 5% Part of 30% Phone Message Scam
    "Investment Scam": 0.156,   # 15.6%
    "Loan Fraud": 0.123,        # 12.3%
    "Macau Scam": 0.089         # 8.9% (high priority despite no specified %)
}

# Profile mappings optimized per scam type
SCAM_PROFILES = {
    "Macau Scam": {
        "scammers": ["authoritative_scammer_01", "government_scammer_01"],
        "victims": ["trusting_victim_01", "elderly_victim_01", "anxious_victim_01", "confused_victim_01"]
    },
    "E-commerce Fraud": {
        "scammers": ["friendly_scammer_01", "urgent_scammer_01", "tech_support_scammer_01"],
        "victims": ["busy_victim_01", "working_parent_victim_01", "trusting_victim_01", "student_victim_01"]
    },
    "Voice Scam": {
        "scammers": ["urgent_scammer_01", "authoritative_scammer_01", "friendly_scammer_01"],
        "victims": ["anxious_victim_01", "trusting_victim_01", "elderly_victim_01", "busy_victim_01"]
    },
    "SMS Scam": {
        "scammers": ["authoritative_scammer_01", "government_scammer_01", "urgent_scammer_01"],
        "victims": ["tech_savvy_victim_01", "student_victim_01", "skeptical_victim_01", "busy_victim_01"]
    },
    "Giveaway Scam": {
        "scammers": ["friendly_scammer_01", "urgent_scammer_01"],
        "victims": ["trusting_victim_01", "elderly_victim_01", "student_victim_01"]
    },
    "Investment Scam": {
        "scammers": ["investment_scammer_01", "friendly_scammer_01"],
        "victims": ["trusting_victim_01", "student_victim_01", "busy_victim_01", "working_parent_victim_01"]
    },
    "Loan Fraud": {
        "scammers": ["friendly_scammer_01", "urgent_scammer_01"],
        "victims": ["anxious_victim_01", "working_parent_victim_01", "student_victim_01"]
    },
    "Delivery Scam": {
        "scammers": ["friendly_scammer_01", "urgent_scammer_01", "tech_support_scammer_01"],
        "victims": ["busy_victim_01", "working_parent_victim_01", "trusting_victim_01", "student_victim_01"]
    }
}

# Awareness level distribution (realistic for each category)
AWARENESS_DISTRIBUTION = {
    "not": 0.60,      # 60% not aware
    "tiny": 0.30,     # 30% slightly aware
    "very": 0.10      # 10% very aware
}

# Turn distribution (20-24 range)
TURN_DISTRIBUTION = {
    20: 0.15,  # 15%
    21: 0.25,  # 25%
    22: 0.30,  # 30%
    23: 0.20,  # 20%
    24: 0.10   # 10%
}

def generate_templates(total_templates: int = 500) -> List[Dict]:
    """Generate scenario templates with proper proportions."""
    templates = []
    template_id = 1

    # Calculate templates per category
    for category, proportion in CATEGORY_PROPORTIONS.items():
        num_templates = int(total_templates * proportion)

        # Get profiles for this category
        scammers = SCAM_PROFILES[category]["scammers"]
        victims = SCAM_PROFILES[category]["victims"]

        # Generate templates for this category
        templates_created = 0
        while templates_created < num_templates:
            # Cycle through all combinations
            for scammer in scammers:
                for victim in victims:
                    # Generate templates with different awareness/turn combinations
                    for awareness, awareness_weight in AWARENESS_DISTRIBUTION.items():
                        # How many templates for this combination based on awareness weight
                        num_for_awareness = max(1, int(num_templates * awareness_weight / (len(scammers) * len(victims))))

                        for _ in range(num_for_awareness):
                            if templates_created >= num_templates:
                                break

                            # Select turn count based on distribution
                            import random
                            turn_choices = list(TURN_DISTRIBUTION.keys())
                            turn_weights = list(TURN_DISTRIBUTION.values())
                            num_turns = random.choices(turn_choices, weights=turn_weights)[0]

                            # Calculate weight (higher for more common awareness levels)
                            weight = awareness_weight / (len(scammers) * len(victims))

                            template = {
                                "template_id": f"T{template_id:04d}",
                                "scammer_profile_id": scammer,
                                "victim_profile_id": victim,
                                "victim_awareness": awareness,
                                "num_turns": num_turns,
                                "weight": round(weight, 4),
                                "category": category,
                                "tags": _generate_tags(category, awareness, scammer, victim)
                            }

                            templates.append(template)
                            template_id += 1
                            templates_created += 1

                            if templates_created >= num_templates:
                                break

                    if templates_created >= num_templates:
                        break

                if templates_created >= num_templates:
                    break

    return templates

def _generate_tags(category: str, awareness: str, scammer: str, victim: str) -> List[str]:
    """Generate descriptive tags for template."""
    tags = []

    # Success likelihood tags
    if awareness == "not":
        tags.append("high-success")
    elif awareness == "tiny":
        tags.append("medium-success")
    else:
        tags.append("low-success")

    # Victim demographic tags
    if "elderly" in victim:
        tags.append("elderly-target")
    elif "student" in victim:
        tags.append("youth-target")
    elif "working_parent" in victim:
        tags.append("parent-target")

    # Scam tactic tags
    if "authoritative" in scammer or "government" in scammer:
        tags.append("high-pressure")
    elif "urgent" in scammer:
        tags.append("urgency-tactics")
    elif "friendly" in scammer:
        tags.append("trust-building")
    elif "investment" in scammer:
        tags.append("financial-lure")

    return tags

def main():
    """Generate and save scenario templates."""
    print("Generating 500 scenario templates with Malaysian scam proportions...")

    templates = generate_templates(500)

    # Create output structure
    output = {
        "version": "2.0",
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "total_templates": len(templates),
        "description": "Scenario templates aligned with Malaysian scam statistics and 20-24 turn range",
        "category_distribution": {
            cat: f"{prop*100}%"
            for cat, prop in CATEGORY_PROPORTIONS.items()
        },
        "turn_range": "20-24",
        "templates": templates
    }

    # Save to file
    output_path = "configs/scenario_templates.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ Generated {len(templates)} templates")
    print(f"✓ Saved to {output_path}")

    # Print distribution summary
    print("\nCategory Distribution:")
    category_counts = {}
    for template in templates:
        cat = template["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat in sorted(category_counts.keys()):
        count = category_counts[cat]
        percentage = (count / len(templates)) * 100
        print(f"  {cat}: {count} templates ({percentage:.1f}%)")

    # Print turn distribution
    print("\nTurn Distribution:")
    turn_counts = {}
    for template in templates:
        turns = template["num_turns"]
        turn_counts[turns] = turn_counts.get(turns, 0) + 1

    for turns in sorted(turn_counts.keys()):
        count = turn_counts[turns]
        percentage = (count / len(templates)) * 100
        print(f"  {turns} turns: {count} templates ({percentage:.1f}%)")

    # Print awareness distribution
    print("\nAwareness Distribution:")
    awareness_counts = {}
    for template in templates:
        awareness = template["victim_awareness"]
        awareness_counts[awareness] = awareness_counts.get(awareness, 0) + 1

    for awareness in sorted(awareness_counts.keys()):
        count = awareness_counts[awareness]
        percentage = (count / len(templates)) * 100
        print(f"  {awareness} aware: {count} templates ({percentage:.1f}%)")

if __name__ == "__main__":
    main()
