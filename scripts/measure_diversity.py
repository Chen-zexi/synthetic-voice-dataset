#!/usr/bin/env python3
"""
Measure diversity of names, institutions, and conversation types in generated conversations.

This script calculates diversity metrics including:
- Unique count and percentage
- Shannon entropy (diversity score)
- Distribution statistics
- Most common entities

Usage:
  python scripts/measure_diversity.py /path/to/scam_labeling
  python scripts/measure_diversity.py /path/to/legit_labeling
  python scripts/measure_diversity.py /path/to/scam_labeling /path/to/legit_labeling
"""

import json
import sys
import math
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional

# Ensure project root (which contains the 'src' package) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Name-related placeholder keys
NAME_KEYS = {
    "caller_name",
    "callee_name",
    "malay_male_name",
    "malay_female_name",
    "chinese_malay_name",
    "indian_malay_name",
}

# Institution/organization-related placeholder keys
ORG_KEYS = {
    "law_enforcement_agency_name",
    "financial_crimes_division_name_local",
    "case_or_warrant_reference_format",
    "courier_company_name_local",
    "parcel_tracking_number_format",
    "shipping_address_format_local",
    "investment_regulator_name",
    "trading_app_name_local",
    "crypto_token_symbol_local",
    "bank_name_local",
    "account_verification_fee_label_local",
    "ecommerce_platform_name_local",
    "payment_link_domain_pattern_local",
    "telecom_provider_name_local",
    "mobile_number_format_local",
    "national_tax_agency_name",
    "local_utility_provider_name",
    "direct_deposit_portal_name",
}


def iter_conversations(path: Path):
    """Iterate over all conversation JSON files in a directory."""
    for f in sorted(path.glob("*.json")):
        try:
            data = json.load(open(f, "r", encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Could not parse {f}: {e}", file=sys.stderr)
            continue
        if isinstance(data, dict) and "dialogue" in data:
            yield data, f


def calculate_shannon_entropy(counter: Counter) -> float:
    """
    Calculate Shannon entropy (diversity measure).
    
    Higher entropy = more diverse
    Maximum entropy = log2(n) where n is the number of unique items
    """
    if not counter:
        return 0.0
    
    total = sum(counter.values())
    if total == 0:
        return 0.0
    
    entropy = 0.0
    for count in counter.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    
    return entropy


def calculate_diversity_score(entropy: float, max_entropy: float) -> float:
    """Calculate normalized diversity score (0-1 scale)."""
    if max_entropy == 0:
        return 0.0
    return entropy / max_entropy


def analyze_entity_diversity(counter: Counter, entity_type: str, total_conversations: int) -> Dict:
    """Analyze diversity metrics for a given entity type."""
    if not counter:
        return {
            "entity_type": entity_type,
            "unique_count": 0,
            "total_occurrences": 0,
            "unique_percentage": 0.0,
            "shannon_entropy": 0.0,
            "max_entropy": 0.0,
            "diversity_score": 0.0,
            "most_common": []
        }
    
    unique_count = len(counter)
    total_occurrences = sum(counter.values())
    unique_percentage = (unique_count / total_conversations * 100) if total_conversations > 0 else 0.0
    
    entropy = calculate_shannon_entropy(counter)
    max_entropy = math.log2(unique_count) if unique_count > 0 else 0.0
    diversity_score = calculate_diversity_score(entropy, max_entropy)
    
    most_common = counter.most_common(10)
    
    return {
        "entity_type": entity_type,
        "unique_count": unique_count,
        "total_occurrences": total_occurrences,
        "unique_percentage": unique_percentage,
        "shannon_entropy": entropy,
        "max_entropy": max_entropy,
        "diversity_score": diversity_score,
        "most_common": [{"entity": item, "count": count, "percentage": (count/total_occurrences*100)} for item, count in most_common]
    }


def analyze_conversation_types(conversations: List[Dict]) -> Dict:
    """Analyze conversation type diversity (scam_tag for scam, category for legit)."""
    type_counter = Counter()
    
    for conv in conversations:
        # For scam conversations, use scam_tag
        if "scam_tag" in conv:
            tag = conv.get("scam_tag", "unknown")
            type_counter[tag] += 1
        # For legit conversations, use category
        elif "category" in conv:
            category = conv.get("category", "unknown")
            type_counter[category] += 1
        else:
            type_counter["unknown"] += 1
    
    return analyze_entity_diversity(type_counter, "conversation_types", len(conversations))


def analyze_directory(directory: Path, label: str = "") -> Dict:
    """Analyze diversity metrics for conversations in a directory."""
    conversations = []
    name_counter = Counter()
    org_counter = Counter()
    
    for conv, filepath in iter_conversations(directory):
        conversations.append(conv)
        
        # Extract names and organizations from placeholders_used
        used = conv.get("placeholders_used", {})
        for k, v in used.items():
            if k in NAME_KEYS:
                name_counter[v] += 1
            if k in ORG_KEYS:
                org_counter[v] += 1
    
    total_conversations = len(conversations)
    
    if total_conversations == 0:
        return {
            "directory": str(directory),
            "label": label,
            "total_conversations": 0,
            "names": {},
            "institutions": {},
            "conversation_types": {}
        }
    
    # Analyze each entity type
    names_analysis = analyze_entity_diversity(name_counter, "names", total_conversations)
    institutions_analysis = analyze_entity_diversity(org_counter, "institutions", total_conversations)
    types_analysis = analyze_conversation_types(conversations)
    
    return {
        "directory": str(directory),
        "label": label,
        "total_conversations": total_conversations,
        "names": names_analysis,
        "institutions": institutions_analysis,
        "conversation_types": types_analysis
    }


def print_human_readable_report(analysis: Dict):
    """Print a human-readable diversity report."""
    print("=" * 80)
    print(f"DIVERSITY REPORT: {analysis.get('label', analysis.get('directory', 'Unknown'))}")
    print("=" * 80)
    print(f"Total Conversations: {analysis['total_conversations']}")
    print()
    
    if analysis['total_conversations'] == 0:
        print("No conversations found in directory.")
        return
    
    # Names diversity
    names = analysis['names']
    print("📛 NAME DIVERSITY")
    print("-" * 80)
    print(f"  Unique Names: {names['unique_count']}")
    print(f"  Total Name Occurrences: {names['total_occurrences']}")
    print(f"  Unique Percentage: {names['unique_percentage']:.1f}%")
    print(f"  Shannon Entropy: {names['shannon_entropy']:.3f} (max: {names['max_entropy']:.3f})")
    print(f"  Diversity Score: {names['diversity_score']:.3f} (0-1 scale, higher = more diverse)")
    if names['most_common']:
        print(f"  Most Common Names:")
        for item in names['most_common'][:5]:
            print(f"    - {item['entity']:30s} {item['count']:4d} times ({item['percentage']:5.1f}%)")
    print()
    
    # Institutions diversity
    insts = analysis['institutions']
    print("🏢 INSTITUTION DIVERSITY")
    print("-" * 80)
    print(f"  Unique Institutions: {insts['unique_count']}")
    print(f"  Total Institution Occurrences: {insts['total_occurrences']}")
    print(f"  Unique Percentage: {insts['unique_percentage']:.1f}%")
    print(f"  Shannon Entropy: {insts['shannon_entropy']:.3f} (max: {insts['max_entropy']:.3f})")
    print(f"  Diversity Score: {insts['diversity_score']:.3f} (0-1 scale, higher = more diverse)")
    if insts['most_common']:
        print(f"  Most Common Institutions:")
        for item in insts['most_common'][:5]:
            print(f"    - {item['entity']:30s} {item['count']:4d} times ({item['percentage']:5.1f}%)")
    print()
    
    # Conversation types diversity
    types = analysis['conversation_types']
    print("📋 CONVERSATION TYPE DIVERSITY")
    print("-" * 80)
    print(f"  Unique Types: {types['unique_count']}")
    print(f"  Total Conversations: {types['total_occurrences']}")
    print(f"  Shannon Entropy: {types['shannon_entropy']:.3f} (max: {types['max_entropy']:.3f})")
    print(f"  Diversity Score: {types['diversity_score']:.3f} (0-1 scale, higher = more diverse)")
    if types['most_common']:
        print(f"  Distribution:")
        for item in types['most_common']:
            print(f"    - {item['entity']:30s} {item['count']:4d} conversations ({item['percentage']:5.1f}%)")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/measure_diversity.py <directory1> [directory2] ...")
        print("Example: python scripts/measure_diversity.py scam_labeling/ legit_labeling/")
        sys.exit(1)
    
    directories = [Path(arg) for arg in sys.argv[1:]]
    
    all_analyses = []
    for directory in directories:
        if not directory.exists():
            print(f"Warning: Directory not found: {directory}", file=sys.stderr)
            continue
        
        # Determine label from directory name
        label = directory.name.replace("_", " ").title()
        
        analysis = analyze_directory(directory, label)
        all_analyses.append(analysis)
        print_human_readable_report(analysis)
    
    # Output JSON report if multiple directories or explicitly requested
    if len(all_analyses) > 1 or "--json" in sys.argv:
        output_file = "diversity_report.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_analyses, f, indent=2, ensure_ascii=False)
        print(f"JSON report saved to: {output_file}")


if __name__ == "__main__":
    main()


