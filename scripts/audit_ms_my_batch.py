#!/usr/bin/env python3
"""
Batch audit for ms-my conversations (scam/legit).

Usage:
  python scripts/audit_ms_my_batch.py /path/to/folder

Outputs a concise summary to stdout.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List

# Ensure project root (which contains the 'src' package) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.conversation.length_utils import estimate_dialogue_syllables, estimate_minutes_from_syllables


NAME_KEYS = {
    "caller_name",
    "callee_name",
}

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
}


def iter_conversations(path: Path):
    for f in sorted(path.glob("*.json")):
        try:
            data = json.load(open(f, "r", encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and "dialogue" in data:
            yield data


def main(folder: str):
    p = Path(folder)
    if not p.exists():
        print(f"Folder not found: {folder}")
        sys.exit(1)

    name_counter = Counter()
    org_counter = Counter()
    turns = []
    syllables_list = []

    n = 0
    for conv in iter_conversations(p):
        n += 1
        # Names/orgs from placeholders_used if present
        used = conv.get("placeholders_used", {})
        for k, v in used.items():
            if k in NAME_KEYS:
                name_counter[v] += 1
            if k in ORG_KEYS:
                org_counter[v] += 1
        # Length
        dialogue = conv.get("dialogue", [])
        turns.append(len(dialogue))
        s = estimate_dialogue_syllables(dialogue)
        syllables_list.append(s)

    def top(counter: Counter, k=10):
        return counter.most_common(k)

    print("=== AUDIT SUMMARY ===")
    print(f"Folder: {folder}")
    print(f"Conversations: {n}")
    if n == 0:
        return
    print("")
    # Names
    total_names = sum(name_counter.values()) or 1
    print("Top names (count, %):")
    for item, c in top(name_counter):
        print(f"  {item:25s} {c:5d}  {c/total_names:5.1%}")
    # Orgs
    print("")
    total_orgs = sum(org_counter.values()) or 1
    print("Top organizations (count, %):")
    for item, c in top(org_counter):
        print(f"  {item:25s} {c:5d}  {c/total_orgs:5.1%}")
    # Length
    if syllables_list:
        syllables_list.sort()
        avg_syll = sum(syllables_list) / len(syllables_list)
        avg_min = estimate_minutes_from_syllables(avg_syll)
        pct_1500 = sum(1 for x in syllables_list if x >= 1500) / len(syllables_list)
        print("")
        print("Length (syllables):")
        print(f"  avg={avg_syll:.0f} (~{avg_min:.2f} min)  >=1500: {pct_1500:5.1%}")
    if turns:
        avg_turns = sum(turns) / len(turns)
        pct_20 = sum(1 for x in turns if x >= 20) / len(turns)
        print("Turns:")
        print(f"  avg={avg_turns:.1f}  >=20: {pct_20:5.1%}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/audit_ms_my_batch.py /path/to/folder")
        sys.exit(1)
    main(sys.argv[1])


