# Conversation Generation Control Guide

**Version**: 2.0
**Last Updated**: October 16, 2025

## Table of Contents
- [Quick Start](#quick-start)
- [Pipeline Steps](#pipeline-steps)
- [Generation Control Methods](#generation-control-methods)
- [Quality & Filtering](#quality--filtering)
- [Reproducibility](#reproducibility)
- [Advanced Options](#advanced-options)
- [Common Use Cases](#common-use-cases)

---

## Quick Start

### Default Behavior
By default, the pipeline runs **conversation generation only** (no TTS):

```bash
# Generates conversations for all seeds (default behavior)
python main.py --locale ms-my --scam

# Equivalent to:
python main.py --locale ms-my --scam --steps conversation
```

**Output**: `output/ms-my/{timestamp}/conversations/scam_conversations.json`

### Generate Conversations + TTS + Post-processing
```bash
# Run full pipeline
python main.py --locale ms-my --scam --steps conversation tts postprocess

# Or shorthand
python main.py --locale ms-my --scam --steps all
```

---

## Pipeline Steps

Control which steps run with `--steps`:

| Step | Description | Output |
|------|-------------|--------|
| `conversation` | Generate scam dialogues | `conversations/scam_conversations.json` |
| `legit` | Generate legitimate dialogues | `conversations/legit_conversations.json` |
| `tts` | Convert text to speech | `audio/scam/*.mp3`, `audio/legit/*.mp3` |
| `postprocess` | Format JSON + ZIP audio | `final/scam_dataset.json`, `final/scam_audio.zip` |
| `all` | Run all steps | Complete dataset |

### Examples

```bash
# Only generate conversations (DEFAULT)
python main.py --locale ms-my --scam

# Generate conversations and audio
python main.py --locale ms-my --scam --steps conversation tts

# Only run TTS on existing conversations
python main.py --locale ms-my --steps tts --use-timestamp 1016_2123

# Full pipeline
python main.py --locale ms-my --scam --legit --steps all
```

---

## Generation Control Methods

### Method 1: Seed-Based Control (Default)

Control by number of **seeds** to use:

```bash
# Use 10 seeds (each generates 1 conversation by default)
python main.py --locale ms-my --scam --seed-limit 10

# Use 10 seeds with 5 variations each = 50 conversations
python main.py --locale ms-my --scam --seed-limit 10 --scenarios-per-seed 5
```

**Configuration**:
```json
{
  "generation_control_mode": "seeds",  // default
  "seed_limit": 10,
  "scenarios_per_seed": 1
}
```

**How it works**:
1. Filters seeds by quality (default: quality_score >= 70)
2. Selects first N seeds (or random if `deterministic_seed_order: false`)
3. Generates `scenarios_per_seed` conversations for each seed

### Method 2: Conversation-Based Control

Control by **target conversation count**:

```bash
# Target 100 total conversations
python main.py --locale ms-my --scam --conversation-count 100

# System automatically calculates: ceil(100 / scenarios_per_seed) seeds needed
```

**Configuration**:
```json
{
  "generation_control_mode": "conversations",
  "conversation_count": 100,
  "scenarios_per_seed": 3  // Will use 34 seeds (34 × 3 = 102 ≥ 100)
}
```

**How it works**:
1. Calculates seeds needed: `ceil(target_count / scenarios_per_seed)`
2. Generates conversations until target reached
3. May slightly exceed target to complete last seed

### Method 3: Absolute Cap

Hard limit regardless of mode:

```bash
# Will stop at 50 even if other settings allow more
python main.py --locale ms-my --scam --seed-limit 100 --total-limit 50
```

**Configuration**:
```json
{
  "total_limit": 50  // Absolute maximum
}
```

**Priority order**: `total_limit` > `conversation_count` > `seed_limit`

---

## Scam vs Legitimate Conversations

### Generate Scam Only (Default)
```bash
python main.py --locale ms-my --scam
python main.py --locale ms-my --scam --scam-limit 100
```

### Generate Legitimate Only
```bash
python main.py --locale ms-my --legit
python main.py --locale ms-my --legit --legit-limit 50
```

### Generate Both Types
```bash
# Same limit for both
python main.py --locale ms-my --scam --legit --sample-limit 75

# Different limits
python main.py --locale ms-my --scam --legit --scam-limit 100 --legit-limit 50

# Scam with seed control, legit with count control
python main.py --locale ms-my --scam --legit --seed-limit 20 --legit-limit 100
```

**Note**:
- `--sample-limit` applies to both scam and legit
- `--scam-limit` / `--legit-limit` override `--sample-limit` for each type
- Scam uses seed-based system, legit uses random category selection

---

## Quality & Filtering

### Seed Quality Filtering

```bash
# Only use seeds with quality_score >= 80
python main.py --locale ms-my --scam --min-quality 80

# Use all seeds regardless of quality
python main.py --locale ms-my --scam --min-quality 0

# Default is 70
python main.py --locale ms-my --scam  # min-quality defaults to 70
```

**Configuration**:
```json
{
  "min_seed_quality": 70
}
```

**Quality Score Ranges**:
- 90-100: Excellent (based on real cases, detailed scenarios)
- 80-89: Good (realistic patterns, clear manipulation tactics)
- 70-79: Fair (complete scenarios, some generic elements)
- <70: Filtered out by default

### Check Available Seeds

```bash
# View all seeds with quality scores
jq '.[] | {seed_id, quality_score, scam_tag, meta_tag}' \
  data/input/malaysian_voice_phishing_seeds_2025.json

# Count seeds by quality threshold
jq '[.[] | select(.quality_score >= "80")] | length' \
  data/input/malaysian_voice_phishing_seeds_2025.json
```

---

## Reproducibility

### Deterministic Generation

```bash
# Same output every time
python main.py --locale ms-my --scam \
  --seed-limit 10 \
  --random-seed 42

# Same seeds, same order, same templates
```

**Configuration**:
```json
{
  "random_seed": 42,
  "deterministic_seed_order": true
}
```

**What gets fixed**:
- ✅ Seed selection order
- ✅ Character profile pairings (in random mode)
- ✅ Victim awareness levels (in random mode)
- ✅ Turn counts (in random mode)
- ✅ Template selection weights

### Non-Deterministic Generation

```bash
# Different variations each run
python main.py --locale ms-my --scam --seed-limit 10
# (no --random-seed flag)
```

**Configuration**:
```json
{
  "random_seed": null,
  "deterministic_seed_order": false
}
```

**Use cases**:
- Exploring diverse conversation patterns
- Generating multiple dataset versions
- A/B testing different scenarios

---

## Scenario Assignment Modes

### Mode 1: Pre-configured (Recommended)

Uses pre-defined seed-to-template mappings:

```bash
# Uses scenario_assignments_malaysia.json
python main.py --locale ms-my --scam --seed-limit 10
```

**Configuration**:
```json
{
  "scenario_mode": "pre_configured",
  "scenario_templates_file": "configs/scenario_templates.json",
  "scenario_assignments_file": "configs/scenario_assignments_malaysia.json"
}
```

**Benefits**:
- ✅ Reproducible: Same seed → same template
- ✅ Category-balanced: Follows Malaysian scam statistics
- ✅ Optimized profiles: Scammer-victim pairings match scam psychology
- ✅ Controlled distribution: Each seed has 5 pre-assigned templates

**How it works**:
```
MY001 → [T0483, T0486, T0489, T0492, T0495]  // 5 Macau Scam templates
MY007 → [T0156, T0159, T0162, T0165, T0168]  // 5 Investment Scam templates
```

### Mode 2: Random Scenario Generation

Dynamically creates scenarios:

```bash
# Random profile selection for each conversation
python main.py --locale ms-my --scam --seed-limit 10
# (requires scenario_mode: "random" in config)
```

**Configuration**:
```json
{
  "scenario_mode": "random"
}
```

**What gets randomized**:
- Character profiles (scammer + victim)
- Victim awareness level (not/slightly/very)
- Number of turns (20-24 range)

**Use cases**:
- Exploring edge cases
- Generating diverse training data
- Testing model robustness

---

## Timestamp Management

### Automatic Timestamp (Default)

```bash
# Creates new timestamp directory
python main.py --locale ms-my --scam
# Output: output/ms-my/1016_2145/
```

### Use Existing Timestamp

```bash
# Use latest timestamp for TTS
python main.py --locale ms-my --steps tts

# Use specific timestamp
python main.py --locale ms-my --steps tts --use-timestamp 1016_2123

# Force new timestamp even for processing steps
python main.py --locale ms-my --steps tts --use-timestamp new
```

### Legacy Mode (No Timestamp)

```bash
# Old single-directory structure
python main.py --locale ms-my --scam --no-timestamp
# Output: output/ms-my/conversations/
```

**Timestamp behavior**:
- **Generation steps** (`conversation`, `legit`): Always create new timestamp
- **Processing steps** (`tts`, `postprocess`): Use latest timestamp
- **Manual override**: `--use-timestamp MMDD_HHMM`

---

## Advanced Options

### Verbose Logging

```bash
# Detailed debug output
python main.py --locale ms-my --scam --seed-limit 2 --verbose

# Shows:
# - Seed selection process
# - Template assignments
# - Character profile details
# - LLM API calls
# - Token usage
```

### LLM Configuration

Control model behavior via `configs/common.json`:

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 1.0,
    "max_tokens": null,
    "reasoning_effort": "low",  // for o1 models
    "use_response_api": true,
    "track_tokens": true
  }
}
```

### Turn Range Control

```json
{
  "followup_turns": {
    "num_turns_lower_limit": 20,
    "num_turns_upper_limit": 24
  }
}
```

**Effect**:
- Pre-configured templates use 20-24 turns
- Random scenarios generate 20-24 turns
- LLM prompts guide to this range (±2 tolerance allowed)

### Victim Awareness Distribution

```json
{
  "victim_awareness_levels": [
    "not",    // 60% of templates
    "not",
    "not",
    "tiny",   // 30% of templates
    "tiny",
    "very"    // 10% of templates
  ]
}
```

Affects conversation dynamics:
- **not**: Victim trusts scammer, high success rate
- **tiny**: Victim shows skepticism, scammer works harder
- **very**: Victim suspicious, may expose scam

---

## Common Use Cases

### 1. Quick Test (2 conversations)
```bash
python main.py --locale ms-my --scam --seed-limit 2 --verbose
```
**Output**: 2 conversations from first 2 seeds
**Time**: ~40 seconds
**Cost**: ~$0.06

### 2. Small Balanced Dataset (100 conversations)
```bash
python main.py --locale ms-my --scam \
  --conversation-count 100 \
  --random-seed 42
```
**Output**: 100 scam conversations, category-balanced
**Time**: ~30 minutes
**Cost**: ~$3.00

### 3. Full Seed Coverage (95 conversations)
```bash
python main.py --locale ms-my --scam \
  --seed-limit 19 \
  --scenarios-per-seed 5
```
**Output**: All 19 seeds × 5 templates = 95 conversations
**Time**: ~45 minutes
**Cost**: ~$3.00

### 4. Mixed Dataset (Scam + Legit)
```bash
python main.py --locale ms-my --scam --legit \
  --scam-limit 200 \
  --legit-limit 100 \
  --random-seed 42
```
**Output**: 200 scam + 100 legit = 300 total
**Time**: ~90 minutes
**Cost**: ~$9.00

### 5. High-Quality Only
```bash
python main.py --locale ms-my --scam \
  --min-quality 90 \
  --scenarios-per-seed 3
```
**Output**: Only seeds with quality >= 90
**Seeds used**: ~8 seeds (quality_score >= 90)
**Conversations**: 24 (8 × 3)

### 6. Production Dataset with Audio
```bash
python main.py --locale ms-my --scam --legit \
  --conversation-count 500 \
  --legit-limit 250 \
  --steps all \
  --random-seed 42
```
**Output**:
- 500 scam + 250 legit conversations
- Audio files for all conversations
- Formatted JSON + ZIP archives
**Time**: ~4 hours (including TTS)
**Cost**: ~$15 (LLM) + ElevenLabs API costs

### 7. Category-Specific Generation
```bash
# Generate only Macau Scam conversations (seeds MY001, MY002, MY005, MY008)
python main.py --locale ms-my --scam \
  --seed-limit 4 \
  --scenarios-per-seed 5

# First 4 seeds are all Macau Scam type
```

### 8. Reproducible A/B Testing
```bash
# Version A
python main.py --locale ms-my --scam \
  --conversation-count 100 \
  --random-seed 42

# Version B (same seeds, different templates/profiles)
python main.py --locale ms-my --scam \
  --conversation-count 100 \
  --random-seed 43
```

### 9. Iterative Development
```bash
# Step 1: Generate conversations only
python main.py --locale ms-my --scam --seed-limit 10

# Step 2: Review output, then generate audio
python main.py --locale ms-my --steps tts

# Step 3: Post-process for final dataset
python main.py --locale ms-my --steps postprocess
```

---

## Validation & Verification

### Check Generation Settings
```bash
# Validate configuration
python main.py --validate-config ms-my

# List available locales
python main.py --list-locales

# Show pipeline steps
python main.py --show-steps
```

### Verify Seed Distribution
```bash
# Check meta_tag distribution
jq -r '.[] | .meta_tag' data/input/malaysian_voice_phishing_seeds_2025.json | sort | uniq -c

# Expected output:
#   4 E-commerce Fraud
#   2 Delivery Scam
#   1 Giveaway Scam
#   1 Investment Scam
#   2 Loan Fraud
#   4 Macau Scam
#   1 SMS Scam
#   4 Voice Scam
```

### Check Template Assignments
```bash
# View assignments for specific seed
jq '.seed_scenarios.MY001' configs/scenario_assignments_malaysia.json

# Output: ["T0483", "T0486", "T0489", "T0492", "T0495"]
```

### Verify Generated Output
```bash
# Check conversation structure
jq '.conversations[0] | keys' output/ms-my/{timestamp}/conversations/scam_conversations.json

# Check turn count
jq '.conversations[] | {id: .conversation_id, num_turns, actual: (.dialogue | length)}' \
  output/ms-my/{timestamp}/conversations/scam_conversations.json

# Check category distribution
jq '.conversations | group_by(.scam_category) | map({cat: .[0].scam_category, count: length})' \
  output/ms-my/{timestamp}/conversations/scam_conversations.json
```

---

## Cost Estimation

### Token Usage (with gpt-4o)
- **Average per conversation**: ~9,000 tokens
  - Input: ~6,900 tokens (6,000 cached after first call)
  - Output: ~2,500 tokens
  - Reasoning: ~1,300 tokens (for o1/o3 models)

### Cost Estimates
- **gpt-4o**: ~$0.031 per conversation
- **gpt-4o-mini**: ~$0.005 per conversation
- **o1-mini**: ~$0.045 per conversation (with reasoning)

### Calculate Total Cost
```bash
# 100 conversations with gpt-4o
# Cost: 100 × $0.031 = $3.10

# 1000 conversations with gpt-4o-mini
# Cost: 1000 × $0.005 = $5.00
```

### Monitor Token Usage
```bash
# Enable token tracking
python main.py --locale ms-my --scam --seed-limit 10 --verbose

# Check token summary in output
# Shows: total tokens, cached tokens, cost breakdown
```

---

## Troubleshooting

### Issue: No conversations generated
```bash
# Check if seeds exist
jq 'length' data/input/malaysian_voice_phishing_seeds_2025.json

# Check quality filter
jq '[.[] | select(.quality_score >= "70")] | length' \
  data/input/malaysian_voice_phishing_seeds_2025.json

# Lower quality threshold
python main.py --locale ms-my --scam --min-quality 0
```

### Issue: Wrong number of conversations
```bash
# Verify settings
python main.py --locale ms-my --scam --seed-limit 10 --verbose

# Check actual limit applied
jq '.generation_metadata.generation_control' \
  output/ms-my/{timestamp}/conversations/scam_conversations.json
```

### Issue: Conversations too short/long
```bash
# Check turn configuration
jq '.followup_turns' configs/common.json

# Should show:
# {
#   "num_turns_lower_limit": 20,
#   "num_turns_upper_limit": 24
# }

# Verify template turns
jq '.templates[] | select(.template_id == "T0483") | .num_turns' \
  configs/scenario_templates.json
```

### Issue: Same conversations every time
```bash
# Remove random seed for variety
python main.py --locale ms-my --scam --seed-limit 10
# (without --random-seed)

# Or change random seed
python main.py --locale ms-my --scam --seed-limit 10 --random-seed 999
```

---

## Best Practices

### ✅ Recommended
- Use `--random-seed 42` for reproducible datasets
- Start with `--seed-limit 2 --verbose` to test configuration
- Use `--conversation-count` for production datasets
- Enable `--verbose` during development
- Use pre-configured mode for balanced distribution
- Set `min-quality >= 70` for production data

### ❌ Avoid
- Running full TTS without testing conversations first
- Using `--no-timestamp` for production (limits versioning)
- Setting `min-quality < 60` (low-quality seeds)
- Mixing `--seed-limit` and `--conversation-count` (confusing)
- Running without `--random-seed` if reproducibility needed

---

## Quick Reference

### Essential Commands
```bash
# Test with 2 seeds
python main.py --locale ms-my --scam --seed-limit 2 --verbose

# Generate 100 balanced conversations
python main.py --locale ms-my --scam --conversation-count 100 --random-seed 42

# All seeds, 5 variations each
python main.py --locale ms-my --scam --seed-limit 19 --scenarios-per-seed 5

# Scam + legit dataset
python main.py --locale ms-my --scam --legit --scam-limit 200 --legit-limit 100

# Full pipeline with audio
python main.py --locale ms-my --scam --steps all --conversation-count 100
```

### Key Flags
| Flag | Purpose | Example |
|------|---------|---------|
| `--seed-limit` | Number of seeds | `--seed-limit 10` |
| `--conversation-count` | Target conversation count | `--conversation-count 100` |
| `--total-limit` | Absolute maximum | `--total-limit 50` |
| `--scenarios-per-seed` | Variations per seed | `--scenarios-per-seed 5` |
| `--min-quality` | Quality threshold | `--min-quality 80` |
| `--random-seed` | Reproducibility | `--random-seed 42` |
| `--steps` | Pipeline steps | `--steps conversation tts` |
| `--verbose` | Debug logging | `--verbose` |
| `--use-timestamp` | Timestamp control | `--use-timestamp 1016_2123` |

---

For more details, see:
- [SCENARIO_REDESIGN_SUMMARY.md](SCENARIO_REDESIGN_SUMMARY.md) - Template and assignment system
- [PIPELINE_OPTIMIZATIONS.md](PIPELINE_OPTIMIZATIONS.md) - Performance optimizations
- [CLAUDE.md](CLAUDE.md) - Full project documentation
