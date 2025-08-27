#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scam table deduper/merger (LLM-powered; compares NEW vs OLD within same type)

What this script does:
- Read two well-formatted JSON files (lists of rows with keys: "type", "summary", "seed").
  * --old: canonical (existing) set
  * --new: incoming (to be checked against old)
- Assign integer "id" to each row if absent. Old rows get IDs 1..N_old. New rows continue from there.
- For each NEW row, compare ONLY against OLD rows with the same "type" using an OpenAI GPT model
  (LLM similarity judgment) instead of embeddings.
- For each (new_row, old_row) pair, the LLM returns a strict JSON verdict with fields:
    {
      "summary_similarity": float in [0,1],
      "seed_similarity": float in [0,1],
      "decision": "duplicate" | "merge" | "distinct",
      "merged_summary": string,
      "merged_seed": string,
      "rationale": string
    }
- We pick the BEST matching OLD row for each NEW row (highest seed_similarity primarily),
  and then apply the decision:
    * "duplicate": mark the NEW id as removed (we keep the OLD entry)
    * "merge": create a merged row (using the provided merged_summary/merged_seed),
               mark BOTH (OLD id and NEW id) in "removed", append the merged row
               (with a fresh id), and mark that OLD id as "consumed" so it won't be reused.
    * "distinct": keep the NEW row as-is
- Finally, we build a NEW TABLE by taking:
    * All OLD + NEW rows, dropping every id in "removed"
    * Plus all merged rows in "appended"
- Write outputs:
    * --output: the new table JSON (list of rows)
    * --audit:  an audit JSON with {"removed": [...], "appended": [...], "matches": [...per-new reports...]}

Usage example:
$ export OPENAI_API_KEY="sk-..."
$ python3 scam_deduper_llm.py \
    --old old_scams.json \
    --new new_scams.json \
    --output updated_scams.json \
    --audit audit_llm.json \
    --model gpt-5.1 \
    --decision-mode auto \
    --summary-threshold 0.80 \
    --seed-dup-threshold 0.92 \
    --seed-merge-threshold 0.85 \
    --max-candidates 50

Notes:
- Set --decision-mode to "llm" to trust the model's "decision" verbatim.
- Set --decision-mode to "auto" (default) to derive the decision from the LLM similarity scores
  using the thresholds (still logs the model's suggested decision/rationale).
- To limit cost, you can cap comparisons per NEW row with --max-candidates (top-K by a quick heuristic length/keyword match).
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Any, Tuple, Set, Optional
from dotenv import load_dotenv
load_dotenv()

try:
    # Official OpenAI Python SDK (v1+)
    # pip install --upgrade openai
    from openai import OpenAI
except Exception:
    OpenAI = None

SYSTEM_PROMPT = """You are a meticulous data deduplication assistant. 
You will be given two scam entries: an OLD canonical case and a NEW incoming case. 
Each entry has fields: type, summary, seed.

Your tasks:
1) Judge similarity of the two entries.
   - Provide a numeric score summary_similarity in [0,1] for the "summary" fields only.
   - Provide a numeric score seed_similarity in [0,1] for the "seed" fields only.
   - Base similarity on semantic equivalence, not exact wording; penalize contradictory facts.

2) Decide one of:
   - "duplicate": If they describe the same incident/details (essentially redundant).
   - "merge": If they are the same scenario with only small differing details that can be compactly combined.
   - "distinct": If they are meaningfully different scenarios that should both remain.

3) If "merge", produce:
   - merged_summary: a concise line that keeps shared parts and uses "/" to separate differing spans.
   - merged_seed: same idea: restate shared parts, and use "/" to separate the small differing details.

4) Return STRICT JSON with keys:
   {
     "summary_similarity": float,
     "seed_similarity": float,
     "decision": "duplicate" | "merge" | "distinct",
     "merged_summary": string,
     "merged_seed": string,
     "rationale": string
   }
Do not include any extra keys. Keep merged_* empty strings if decision is not "merge".
"""

USER_TEMPLATE = """OLD:
type: {old_type}
summary: {old_summary}
seed: {old_seed}

NEW:
type: {new_type}
summary: {new_summary}
seed: {new_seed}
"""

def llm_compare(client, model: str, old_row: Dict[str, Any], new_row: Dict[str, Any], temperature: float = 0.0, max_retries: int = 3) -> Dict[str, Any]:
    """Call the LLM once to compare one OLD vs one NEW entry and return a parsed JSON dict."""
    last_err = None
    for _ in range(max_retries):
        try:
            content = USER_TEMPLATE.format(
                old_type=str(old_row["type"]),
                old_summary=str(old_row["summary"]),
                old_seed=str(old_row["seed"]),
                new_type=str(new_row["type"]),
                new_summary=str(new_row["summary"]),
                new_seed=str(new_row["seed"]),
            )
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content
            data = json.loads(text)
            # Basic validation
            for k in ["summary_similarity", "seed_similarity", "decision", "merged_summary", "merged_seed", "rationale"]:
                if k not in data:
                    raise ValueError(f"LLM JSON missing key: {k}")
            # Coerce numeric
            data["summary_similarity"] = float(data["summary_similarity"])
            data["seed_similarity"] = float(data["seed_similarity"])
            # Normalize decision
            data["decision"] = str(data["decision"]).lower().strip()
            if data["decision"] not in {"duplicate", "merge", "distinct"}:
                data["decision"] = "distinct"
            return data
        except Exception as e:
            last_err = e
            time.sleep(1.2)
    raise RuntimeError(f"LLM compare failed after retries: {last_err}")

def load_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        rows = data["data"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError("JSON must be a list of rows or an object with a 'data' list.")
    for i, r in enumerate(rows):
        if not all(k in r for k in ("type", "summary", "seed")):
            raise ValueError(f"Row {i} missing required keys 'type', 'summary', 'seed'")
    return rows

def assign_ids(old_rows: List[Dict[str, Any]], new_rows: List[Dict[str, Any]]) -> None:
    next_id = 1
    for r in old_rows:
        if "id" not in r or not isinstance(r["id"], int):
            r["id"] = next_id
        next_id = max(next_id, r["id"] + 1)
    for r in new_rows:
        if "id" not in r or not isinstance(r["id"], int):
            r["id"] = next_id
        next_id = max(next_id, r["id"] + 1)

def choose_best_match(judgments: List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]]) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
    """
    judgments is a list of tuples: (old_row, new_row, verdict_dict)
    We pick the one with the highest seed_similarity, tie-break by summary_similarity.
    Returns the winning tuple or None if empty.
    """
    if not judgments:
        return None
    return sorted(judgments, key=lambda t: (t[2]["seed_similarity"], t[2]["summary_similarity"]), reverse=True)[0]

def main():
    parser = argparse.ArgumentParser(description="LLM-powered dedupe: compare NEW vs OLD within same type.")
    parser.add_argument("--old", default="seeds_llm.json", help="Path to OLD JSON.")
    parser.add_argument("--new", default="seeds_scamGen.json", help="Path to NEW JSON.")
    parser.add_argument("--output", default="seeds_filtered.json", help="Path to write the NEW TABLE JSON.")
    parser.add_argument("--audit", default=None, help="Optional path to write an audit JSON.")
    parser.add_argument("--model", default="gpt-5", help="OpenAI chat model to use (e.g., gpt-5.1, gpt-5.1-mini).")
    parser.add_argument("--decision-mode", choices=["llm", "auto"], default="llm",
                        help="Use LLM's decision verbatim ('llm') or derive via thresholds ('auto').")
    parser.add_argument("--summary-threshold", type=float, default=0.80, help="Auto mode: min summary similarity to consider.")
    parser.add_argument("--seed-dup-threshold", type=float, default=0.92, help="Auto mode: seed >= this => duplicate.")
    parser.add_argument("--seed-merge-threshold", type=float, default=0.85, help="Auto mode: seed >= this => merge (else distinct).")
    parser.add_argument("--max-candidates", type=int, default=0,
                        help="If >0, limit OLD comparisons per NEW to this number via a quick heuristic (same type only).")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    if os.getenv("OPENAI_API_KEY") in (None, "", "YOUR_API_KEY"):
        print("ERROR: Please set environment variable OPENAI_API_KEY.", file=sys.stderr)
        sys.exit(2)
    if OpenAI is None:
        print("ERROR: OpenAI SDK not installed. Run: pip install --upgrade openai", file=sys.stderr)
        sys.exit(2)

    client = OpenAI()

    old_rows = load_rows(args.old)
    new_rows = load_rows(args.new)

    # Assign IDs (old first, then new)
    assign_ids(old_rows, new_rows)

    # Index old by type
    by_type_old: Dict[str, List[Dict[str, Any]]] = {}
    for r in old_rows:
        by_type_old.setdefault(str(r["type"]), []).append(r)

    # We will mark removed ids and collect appended merged rows
    removed: Set[int] = set()
    appended: List[Dict[str, Any]] = []
    matches_report: List[Dict[str, Any]] = []  # for audit

    # Track "consumed" old rows that have been merged so they don't get reused
    consumed_old: Set[int] = set()

    # Process each NEW row
    for new_row in new_rows:
        t = str(new_row["type"])
        candidates = [r for r in by_type_old.get(t, []) if r["id"] not in removed and r["id"] not in consumed_old]

        # Optional quick cap to reduce cost: simple heuristic - prioritize closer length & keyword overlap
        if args.max_candidates and len(candidates) > args.max_candidates:
            # crude score: shared lowercase tokens between summary+seed fields; tie-break by length gap
            def quick_score(old_r):
                otext = (str(old_r["summary"]) + " " + str(old_r["seed"])).lower()
                ntext = (str(new_row["summary"]) + " " + str(new_row["seed"])).lower()
                otoks = set(otext.split())
                ntoks = set(ntext.split())
                overlap = len(otoks & ntoks)
                length_gap = abs(len(otext) - len(ntext))
                return (overlap, -length_gap)
            candidates = sorted(candidates, key=quick_score, reverse=True)[: args.max_candidates]

        judgments: List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]] = []

        # Compare against each OLD candidate of same type
        for old_row in candidates:
            verdict = llm_compare(client, args.model, old_row, new_row, temperature=args.temperature)
            judgments.append((old_row, new_row, verdict))

        # If no OLD of same type, keep NEW as distinct
        if not judgments:
            matches_report.append({
                "new_id": new_row["id"],
                "matched_old_id": None,
                "decision_used": "distinct",
                "llm_suggested": None
            })
            continue

        best = choose_best_match(judgments)
        old_row, _, verdict = best

        # Decide action
        if args.decision_mode == "llm":
            decision = verdict["decision"]
        else:  # auto
            if verdict["summary_similarity"] >= args.summary_threshold:
                if verdict["seed_similarity"] >= args.seed_dup_threshold:
                    decision = "duplicate"
                elif verdict["seed_similarity"] >= args.seed_merge_threshold:
                    decision = "merge"
                else:
                    decision = "distinct"
            else:
                decision = "distinct"

        # Apply action
        if decision == "duplicate":
            # Remove NEW only
            removed.add(new_row["id"])
            matches_report.append({
                "new_id": new_row["id"],
                "matched_old_id": old_row["id"],
                "decision_used": "duplicate",
                "llm_suggested": verdict
            })

        elif decision == "merge":
            merged = {
                "id": max([r["id"] for r in old_rows + new_rows + appended]) + 1,
                "type": t,
                "summary": verdict.get("merged_summary", "").strip() or f'{old_row["summary"]} / {new_row["summary"]}',
                "seed": verdict.get("merged_seed", "").strip() or f'{old_row["seed"]} / {new_row["seed"]}',
            }
            appended.append(merged)
            removed.add(old_row["id"])
            removed.add(new_row["id"])
            consumed_old.add(old_row["id"])

            matches_report.append({
                "new_id": new_row["id"],
                "matched_old_id": old_row["id"],
                "decision_used": "merge",
                "llm_suggested": verdict,
                "merged_id": merged["id"]
            })

        else:  # distinct
            matches_report.append({
                "new_id": new_row["id"],
                "matched_old_id": old_row["id"],
                "decision_used": "distinct",
                "llm_suggested": verdict
            })

    # Build the final table:
    # Start with all rows
    combined = old_rows + new_rows
    # Drop removed
    final_rows = [r for r in combined if r["id"] not in removed]
    # Append merges
    final_rows += appended
    # Sort by type then id for neatness
    final_rows.sort(key=lambda r: (str(r["type"]), int(r["id"]) if isinstance(r["id"], int) else 999999))

    # Write outputs
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(final_rows, f, ensure_ascii=False, indent=2)

    if args.audit:
        audit = {
            "removed": sorted(list(removed)),
            "appended": appended,
            "matches": matches_report
        }
        with open(args.audit, "w", encoding="utf-8") as f:
            json.dump(audit, f, ensure_ascii=False, indent=2)

    # Console summary
    print(f"OLD rows: {len(old_rows)} | NEW rows: {len(new_rows)}")
    print(f"Removed: {len(removed)} -> {sorted(list(removed))[:10]}{'...' if len(removed) > 10 else ''}")
    print(f"Merged appended: {len(appended)}")
    print(f"Final table size: {len(final_rows)}")
    print(f"Wrote: {args.output}")
    if args.audit:
        print(f"Wrote audit: {args.audit}")

if __name__ == "__main__":
    main()
