# Conversation Generation for Human Labeling

This guide explains how to generate Malaysian (ms-my) conversations for human labeling tasks.

## Quick Start

### Generate Scam Conversations (250)
```bash
python3 generate_for_labeling.py --type scam --count 250
```

### Generate Legitimate Conversations (250)
```bash
python3 generate_for_labeling.py --type legit --count 250
```

## What This Script Does

The `generate_for_labeling.py` script generates conversations and saves them in **two formats**:

### 1. Default Comprehensive JSON (for reference)
- Saved to: `output/ms-my/{timestamp}/conversations/`
- Contains: All metadata, token usage, cost estimates, and conversations array
- Files: `scam_conversations.json` or `legit_conversations.json`

### 2. Individual Conversation Files (for human labeling)
- Saved to: `scam_labeling/` or `legit_labeling/` at project root
- Files: `scam-1.json`, `scam-2.json`, ... or `legit-1.json`, `legit-2.json`, ...
- Each file contains the complete conversation object with all metadata

## Individual File Structure

Each `scam-X.json` or `legit-X.json` file contains:

**Scam conversations include:**
```json
{
  "conversation_id": 1,
  "seed_id": "MY001",
  "scam_tag": "macau_pdrm",
  "scam_category": "government_impersonation",
  "summary": "...",
  "seed": "...",
  "quality_score": 95,
  "num_turns": 21,
  "victim_awareness": "not",
  "placeholders": [],
  "character_profiles": {...},
  "scenario_id": "MY001_T0483",
  "dialogue": [...],
  "voice_mapping": {...}
}
```

**Legitimate conversations include:**
```json
{
  "conversation_id": 1,
  "region": "Malaysia",
  "category": "family_checkin",
  "num_turns": 22,
  "dialogue": [...],
  "character_profiles": {...},
  "voice_mapping": {...}
}
```

## Workflow for 500 Conversations (250 Scam + 250 Legit)

### Person A: Generate 250 Scam Conversations
```bash
python3 generate_for_labeling.py --type scam --count 250
```

**Maximum Seed Diversity:**
- Generates **exactly 250 conversations** (respects --count flag)
- Distributes across all 19 available seeds for maximum variety
- Each seed generates ~13 conversations (250 ÷ 19 ≈ 13)
- Covers all scam categories:
  - **Macau Scam** (4 seeds) → ~52 conversations
  - **E-commerce Fraud** (4 seeds) → ~52 conversations
  - **Voice Scam** (4 seeds) → ~52 conversations
  - **Investment Scam** (1 seed) → ~13 conversations
  - **Loan Fraud** (2 seeds) → ~26 conversations
  - **Delivery Scam, SMS, Giveaway** (4 seeds) → ~52 conversations

This creates:
- `scam_labeling/scam-1.json` through `scam_labeling/scam-250.json`
- `output/ms-my/{timestamp}/conversations/scam_conversations.json` (reference)

### Person B: Generate 250 Legitimate Conversations
```bash
python3 generate_for_labeling.py --type legit --count 250
```

This creates:
- `legit_labeling/legit-1.json` through `legit_labeling/legit-250.json`
- `output/ms-my/{timestamp}/conversations/legit_conversations.json` (reference)

## For Human Labelers

Send the Malaysian-speaking labelers the individual JSON files from:
- `scam_labeling/` directory (250 files)
- `legit_labeling/` directory (250 files)

Each file contains the complete conversation with dialogue that they can review and mark as "human-sounding" or not.

## Seed Diversity Examples

The script automatically distributes conversations across seeds based on count:

**Small Count (2 conversations):**
- Scenarios per seed: 1
- Seeds used: 2
- Diversity: 2 different scam types

**Medium Count (50 conversations):**
- Scenarios per seed: 3 (50 ÷ 19 ≈ 3)
- Seeds used: 17-19
- Diversity: Most scam types represented

**Large Count (250 conversations):**
- Scenarios per seed: 14 (250 ÷ 19 ≈ 14)  
- Seeds used: All 19 seeds
- Diversity: All scam categories fully represented

## Features Included

All conversations are generated with:
- ✅ Natural Malay speech patterns (colloquial particles, fillers, contractions)
- ✅ Character profiles (diverse personalities and speaking styles)
- ✅ Locale-specific placeholders (Malaysian context)
- ✅ Pre-configured scenarios (category-balanced)
- ✅ Voice assignments (for future TTS)
- ✅ **Smart seed distribution** (maximizes diversity across all 19 scam seeds)

## Additional Options

### Verbose Mode
```bash
python3 generate_for_labeling.py --type scam --count 250 --verbose
```
Shows detailed generation logs and debugging information.

### Help
```bash
python3 generate_for_labeling.py --help
```

## Output Directories

- `scam_labeling/` - Individual scam conversation files (gitignored)
- `legit_labeling/` - Individual legit conversation files (gitignored)
- `output/ms-my/{timestamp}/` - Default comprehensive JSONs with metadata

## Notes

- The script uses ms-my (Malaysian Malay) locale hardcoded
- Conversations include all the natural speech pattern improvements
- Default comprehensive JSONs include token usage and cost estimates
- Individual files are excluded from git (see `.gitignore`)

