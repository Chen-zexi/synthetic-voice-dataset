# Scam/Legit Conversation Generation Pipeline

This pipeline generates realistic scam phone conversations with audio synthesis using advanced character profiles, scenario-based generation, and multi-provider LLM support. The system creates diverse, culturally-appropriate conversations through seed-based generation, character-driven dialogue, and high-quality voice synthesis with ElevenLabs v3 features.

## Key Features

- **Multi-Language Support**: 15+ locales with culturally-appropriate conversations
- **Advanced Voice Synthesis**: ElevenLabs v3 with audio tags, emotional context, and high-quality settings
- **Character Profiles**: Diverse personality traits and speaking styles for authentic dialogue
- **Scenario Management**: Pre-configured templates with balanced scam type distribution
- **Interactive UI**: Comprehensive menu-driven interface for all operations
- **Voice Management**: Real-time validation, suggestions, and health monitoring
- **Quality Improvements**: Natural speech patterns with balanced formality and grammatical correctness
- **Human Labeling Support**: Specialized scripts for generating conversations for human reviewers
- **Multi-Provider LLM**: Support for OpenAI, Anthropic, Google, LM-Studio, and vLLM
- **Token Tracking**: Comprehensive cost monitoring and usage analytics

## Quick Start

### Prerequisites

#### Using uv (Recommended)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# Create virtual environment
uv venv
```

```bash
# Activate virtual environment
source .venv/bin/activate
```

```bash
# Install dependencies from lock file (reproducible)
uv pip sync uv.lock
```

```bash
# Or install from requirements.txt (latest compatible versions)
uv pip install -r requirements.txt
```

```bash
# Update lock file after changing requirements.txt
uv pip compile requirements.txt -o uv.lock
```

#### Using pip (Alternative)
```bash
# Create virtual environment
python -m venv .venv
```

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

```bash
# Install dependencies
pip install -r requirements.txt
```

```bash
# Optional: Install development dependencies
pip install -r requirements-dev.txt
```

#### Package Management Notes
- **uv**: Faster dependency resolution and installation, better lock file management
- **pip**: Standard Python package manager, works with all Python environments
- **Lock files**: `uv.lock` provides reproducible builds across environments
- **Requirements**: `requirements.txt` contains latest compatible versions

### Environment Setup

Create a `.env` file with your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional: For Qwen translation service
DASHSCOPE_API_KEY=your_qwen_api_key_here
```

### Usage

#### Interactive Mode

```bash
# Launch interactive menu interface
python main.py
```

#### Command Line Mode

```bash
# Run complete pipeline (creates new timestamp directory)
python main.py --locale ms-my --total-limit 1

# Run specific steps for Malaysia (Malay)
# Available steps: conversation, tts, postprocess
python main.py --locale ms-my --steps conversation --legit --scam 

# Run TTS processing on existing conversations (auto-uses latest timestamp)
python main.py --locale ms-my --steps tts postprocess
```

##### Generation Control

**Pipeline Steps Control:**
```bash
# Available steps: conversation, legit, tts, postprocess, all
python main.py --locale ms-my --steps conversation  # Generate conversations only (default)
python main.py --locale ms-my --steps conversation tts  # Generate conversations + audio
python main.py --locale ms-my --steps all  # Full pipeline
python main.py --locale ms-my --steps tts postprocess  # Process existing conversations
```

**Scam vs Legitimate Conversations:**
```bash
# Generate only scam conversations
python main.py --locale ms-my --scam --steps conversation 

# Generate only legitimate conversations  
python main.py --locale ms-my --legit --steps conversation

# Generate both types (default if neither flag specified)
python main.py --locale ms-my

# Control generation count
python main.py --locale ms-my --total-limit 50  # Absolute cap: stops at 50 conversations max
python main.py --locale ms-my --scam-limit 100 --legit-limit 20  # Different limits
```

**Generation Control Methods:**

**Method 1: Seed-Based Control (Default)**
```bash
# Use 10 seeds (each generates 1 conversation by default)
python main.py --locale ms-my --scam --seed-limit 10

# Use 10 seeds with 5 variations each = 50 conversations
python main.py --locale ms-my --scam --seed-limit 10 --scenarios-per-seed 5
```

**Method 2: Conversation-Based Control**
```bash
# Target 100 total conversations
python main.py --locale ms-my --scam --conversation-count 100

# System automatically calculates: ceil(100 / scenarios_per_seed) seeds needed
```

**Method 3: Absolute Cap**
```bash
# Will stop at 50 even if other settings allow more
python main.py --locale ms-my --scam --seed-limit 100 --total-limit 50
```

**Quality Filtering:**
```bash
# Only use seeds with quality_score >= 80
python main.py --locale ms-my --scam --min-quality 80

# Use all seeds regardless of quality
python main.py --locale ms-my --scam --min-quality 0
```

##### Advanced Options

**Reproducible Generation:**
```bash
# Use random seed for deterministic seed/profile selection
python main.py --locale ms-my --random-seed 42

# Combine with limits for exact reproducibility
python main.py --locale ms-my --seed-limit 10 --random-seed 42
```

**Model Selection:**
```bash
# Use GPT-5 with reasoning effort control
python main.py --locale ms-my --model gpt-5-nano --reasoning-effort high
```

**Timestamp Control:**
```bash
# Use specific timestamp directory
python main.py --locale ms-my --use-timestamp 0910_1430

# Use latest timestamp for tts and postprocess
python main.py --locale ms-my --steps tts postprocess
```

## Project Structure

```
voice_scam_dataset_gen/
├── main.py                       # Main entry point
├── generate_for_labeling.py       # Human labeling generation script
├── src/                          # Source code modules
│   ├── config/                     # Configuration management
│   │   ├── config_loader.py          # Unified configuration loader
│   │   ├── locale_manager.py         # Locale configuration management
│   │   └── schemas.py                # Configuration validation schemas
│   ├── translation/                # Translation utilities
│   │   ├── translator.py             # Base translator interface
│   │   ├── google_translator.py      # Google Translate implementation
│   │   ├── argos_translator.py      # Offline Argos Translate
│   │   ├── qwen_translator.py       # Alibaba Cloud Qwen-MT
│   │   └── language_codes.py        # Language code mappings
│   ├── conversation/               # LLM dialogue generation
│   │   ├── scam_generator.py         # Scam conversation generation
│   │   ├── legit_generator.py        # Legitimate conversation generation
│   │   ├── schemas.py                # Pydantic schemas for structured output
│   │   ├── seed_manager.py           # Seed data management
│   │   └── character_manager.py      # Character profile and voice mapping
│   ├── llm_core/                   # LLM abstraction layer with LangChain
│   │   ├── api_provider.py           # Multi-provider LLM factory
│   │   ├── api_call.py               # Unified async API interface
│   │   ├── token_counter.py          # Token usage tracking and cost estimation
│   │   └── model_config.json         # Model configurations and pricing
│   ├── tts/                        # ElevenLabs voice synthesis
│   │   ├── voice_synthesizer.py      # Main voice synthesis engine
│   │   ├── voice_validator.py        # Voice ID validation and management
│   │   ├── audio_combiner.py         # Audio file combination
│   │   ├── audio_processor.py        # Audio effects and processing
│   │   ├── audio_tags.py             # V3 audio tags management
│   │   └── models.py                 # Voice data models
│   ├── postprocessing/             # Output formatting and packaging
│   │   ├── json_formatter.py         # JSON output formatting
│   │   └── audio_packager.py         # Audio ZIP packaging
│   ├── pipeline/                   # Pipeline orchestration
│   │   └── runner.py                 # Main pipeline runner
│   ├── cli/                        # Command-line interface
│   │   ├── commands.py               # CLI command implementations
│   │   ├── ui.py                     # Interactive menu interface
│   │   ├── utils.py                  # CLI utility functions
│   │   └── voice_quality_commands.py # Voice quality management
│   ├── seed/                       # Seed data processing
│   │   ├── placeholder_generator.py   # Placeholder generation
│   │   ├── placeholder_substitution_generator.py # Substitution generation
│   │   ├── scamGen_seed_generator.py # Seed generation from scenarios
│   │   ├── scam_deduper_llm.py      # LLM-based seed deduplication
│   │   └── utils_async.py           # Async utilities
│   └── utils/                       # Utility modules
│       └── logging_utils.py          # Logging utilities
├── configs/                      # Configuration files
│   ├── common.json                 # Shared settings across all locales
│   ├── character_profiles.json     # Character profile definitions
│   ├── scenario_templates.json     # Pre-configured scenario templates
│   ├── scenario_assignments_malaysia.json # Seed-to-template mappings
│   └── localizations/              # Locale-specific configurations
│       ├── template/                 # Template for new locales
│       ├── ar-sa/                    # Arabic - Saudi Arabia
│       ├── ar-ae/                    # Arabic - United Arab Emirates
│       ├── ms-my/                    # Malay - Malaysia (production-ready)
│       ├── ko-kr/                    # Korean - South Korea
│       ├── ja-jp/                    # Japanese - Japan
│       ├── vi-vn/                    # Vietnamese - Vietnam
│       ├── en-ph/                    # English - Philippines
│       ├── th-th/                    # Thai - Thailand
│       ├── en-sg/                    # English - Singapore
│       ├── zh-sg/                    # Chinese - Singapore
│       ├── zh-tw/                    # Chinese - Taiwan
│       ├── zh-hk/                    # Chinese - Hong Kong
│       └── en-hk/                    # English - Hong Kong
├── data/                         # Input data and resources
│   ├── input/
│   │   ├── malaysian_voice_phishing_seeds_2025.json # Malaysian scam seeds
│   │   ├── seeds_and_placeholders.json # General seed data
│   │   └── sound_effects/            # Background noise for audio
│   └── translation_cache/           # Translation cache directory
├── doc/                          # Documentation
│   ├── GENERATION_CONTROL_GUIDE.md  # Generation control documentation
│   ├── LOCALE_IMPLEMENTATION_GUIDE.md # Locale implementation guide
│   ├── QUALITY_IMPROVEMENTS_SUMMARY.md # Quality improvements documentation
│   ├── SCAM_COVERAGE_ANALYSIS.md     # Scam coverage analysis
│   ├── LABELING_GENERATION_README.md # Human labeling guide
│   ├── VOICE_ENHANCEMENT_TESTING_GUIDE.md # Voice testing guide
│   ├── API_COMPATIBILITY_FIX.md     # API compatibility fixes
│   ├── MALAYSIAN_CONVERSATION_IMPROVEMENTS.md # Latest improvements for ms-my locale
│   └── locale_road_map.md            # Locale implementation roadmap
├── scripts/                      # Utility scripts
│   ├── measure_diversity.py        # Diversity metrics analysis
│   ├── audit_ms_my_batch.py         # Batch audit for ms-my conversations
│   ├── process_gpt5_outputs.py     # GPT-5 output processing
│   ├── compare_gpt5_models.py      # GPT-5 model comparison
│   └── generate_scenarios.py       # Scenario generation utilities
├── archive/                      # Legacy language-specific scripts
├── output/                       # Generated outputs (gitignored)
├── scam_labeling/               # Individual scam files for labeling (gitignored)
├── legit_labeling/              # Individual legit files for labeling (gitignored)
├── requirements.txt             # Python dependencies
├── uv.lock                      # uv lock file for reproducible builds
├── .env                         # Environment variables (gitignored)
└── .gitignore                   # Git ignore rules
```

## Adding a New Locale

Adding support for a new region is straightforward. For comprehensive instructions, see the [Locale Implementation Guide](doc/LOCALE_IMPLEMENTATION_GUIDE.md) and check the [Locale Roadmap](locale_road_map.md) for current status.

### Quick Start

### 1. Check Roadmap and Mark Status
Before starting, check the [Locale Roadmap](locale_road_map.md) and mark your locale as "🚧 In Progress".

### 2. Use Template Files
```bash
# Copy template to new locale directory
cp -r configs/localizations/template/ configs/localizations/ar-eg/
```

## Localization System

### Configuration Hierarchy
1. **Common Settings** (`configs/common.json`): Shared across all locales
   - Pipeline parameters, API settings, processing limits
2. **Locale Configuration** (`configs/localizations/{locale-id}/config.json`): 
   - Region-specific metadata, voices, conversation categories
3. **Placeholder Mappings** (`configs/localizations/{locale-id}/placeholders.json`):
   - Cultural substitutions for entities (names, places, companies)

### Placeholder System

#### New Format (ms-my only)
- 98 placeholders with structured substitutions
- Compact JSON format for token efficiency
- Direct value usage in conversations
- Supports the optimized pipeline

#### Legacy Format (other locales)
- Different schema structure
- Not compatible with new pipeline optimizations
- Requires migration to new format

**Migration Required**: To use other locales with the new pipeline, their `placeholders.json` files must be updated to match the ms-my format.

### Supported Locales

See the [Locale Roadmap](doc/locale_road_map.md) for current implementation status.

#### Production-Ready (New Pipeline)
- **ms-my**: Malay (Malaysia) - MYR currency, Malaysian entities ✅ ✨
  - Updated placeholder schema format for optimized pipeline
  - Character-voice mappings in `voice_profiles.json`
  - ~45% reduction in API costs through prompt caching
  - Compact JSON format for placeholders
  - Natural speech pattern improvements implemented

#### Completed Locales (53/53 Placeholders)
- **ar-sa**: Arabic (Saudi Arabia) - SAR currency, Saudi entities ✅
- **ar-ae**: Arabic (United Arab Emirates) - AED currency, UAE entities ✅
- **ko-kr**: Korean (South Korea) - KRW currency, Korean entities ✅
- **ja-jp**: Japanese (Japan) - JPY currency, Japanese entities ✅
- **vi-vn**: Vietnamese (Vietnam) - VND currency, Vietnamese entities ✅
- **en-ph**: English (Philippines) - PHP currency, Filipino entities ✅
- **th-th**: Thai (Thailand) - THB currency, Thai entities ✅
- **en-sg**: English (Singapore) - SGD currency, Singaporean entities ✅
- **zh-sg**: Chinese (Singapore) - SGD currency, Singaporean entities ✅
- **zh-tw**: Chinese (Taiwan) - TWD currency, Taiwanese entities ✅
- **zh-hk**: Chinese (Hong Kong) - HKD currency, Hong Kong entities ✅
- **en-hk**: English (Hong Kong) - HKD currency, Hong Kong entities ✅

#### Planned Locales
- **id-id**: Indonesian (Indonesia) - IDR currency, Indonesian entities ⏳
- **ar-qa**: Arabic (Qatar) - QAR currency, Qatari entities ⏳
- **fr-fr**: French (France) - EUR currency, French entities ⏳
- **pt-pt**: Portuguese (Portugal) - EUR currency, Portuguese entities ⏳
- **pt-br**: Brazilian Portuguese (Brazil) - BRL currency, Brazilian entities ⏳
- **es-es**: Spanish (Spain) - EUR currency, Spanish entities ⏳
- **es-mx**: Spanish (Mexico) - MXN currency, Mexican entities ⏳
- **it-it**: Italian (Italy) - EUR currency, Italian entities ⏳

**Migration Status**: All completed locales have full 53/53 placeholder coverage. The new optimized pipeline features (character profiles, voice mappings, natural speech patterns) are currently implemented for ms-my and can be extended to other locales as needed.

## LLM Module

The project includes a unified LLM abstraction layer (`src/llm_core/`) that supports multiple providers with advanced features:

### Supported LLM Providers

#### OpenAI Models
- **GPT-5 Series**: GPT-5, GPT-5-mini, GPT-5-nano (reasoning models with effort levels)
- **GPT-4 Series**: GPT-4o, GPT-4o-mini (optimized variants)
- **O-Series**: O3, O4-mini (advanced reasoning models)
- **Legacy**: GPT-3.5-turbo

#### Anthropic Models
- **Claude-3.5-Sonnet**: Advanced reasoning and analysis
- **Claude-3-Haiku**: Fast, efficient responses
- **Claude-3-Opus**: Most capable model

#### Google Models
- **Gemini-1.5-Pro**: Advanced reasoning capabilities
- **Gemini-1.5-Flash**: Fast, efficient responses
- **Gemini-1.0-Pro**: Standard model

#### Local Hosting
- **LM-Studio**: Local model hosting with custom endpoints
- **vLLM**: High-performance inference server

### Advanced LLM Features

**Reasoning Models:**
- GPT-5 series with configurable reasoning effort levels (minimal/low/medium/high)
- O-series models with advanced multi-faceted analysis capabilities
- Automatic reasoning token tracking and cost estimation
- Enhanced prompt engineering for complex conversation generation

**Token Tracking & Cost Management:**
- Comprehensive token usage tracking across all providers
- Real-time cost estimation with provider-specific pricing
- Session-based aggregation and reporting
- Budget monitoring and alerts
- Cached token tracking for OpenAI models (significant cost savings)

**Model-Specific Parameters:**

**Reasoning Models (GPT-5/O-series):**
- `reasoning_effort`: Controls reasoning depth and processing time
- `max_completion_tokens`: Maximum tokens for completion
- `use_response_api`: Enable Response API for streaming

**Standard Models:**
- `temperature`: Randomness in generation (0.0-2.0)
- `max_tokens`: Maximum tokens to generate
- `top_p`: Nucleus sampling parameter
- `presence_penalty`: Penalty for repetition
- `frequency_penalty`: Penalty for frequent tokens

**Gemini-Specific:**
- `thinking_budget`: Budget for internal reasoning
- `max_output_tokens`: Maximum output tokens

**Enhanced Configuration:**
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-5-nano",
    "reasoning_effort": "minimal",
    "max_concurrent_requests": 20,
    "temperature": 1.0,
    "max_tokens": null,
    "top_p": 0.95,
    "n": 1,
    "track_tokens": true,
    "use_response_api": true
  }
}
```

### Features
- **Async-only architecture**: All LLM calls are asynchronous for better performance
- **Structured output**: Uses LangChain's `with_structured_output` with Pydantic schemas
- **JSON fallback**: Robust parsing with multiple fallback patterns
- **Rate limiting**: Semaphore-based concurrent request management
- **Provider abstraction**: Easy switching between different LLM providers
- **Reasoning support**: Native support for reasoning models with effort levels
- **Token tracking**: Comprehensive usage and cost tracking
- **Response API**: OpenAI Response API integration for streaming

### Environment Variables
```env
# OpenAI (default)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: other providers
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
HOST_IP=192.168.1.100  # For LM-Studio/vLLM
```

### Model-Specific Parameters

**Reasoning Models (GPT-5):**
- `reasoning_effort`: "minimal", "low", "medium", "high"
- `max_completion_tokens`: Maximum tokens for completion
- `use_response_api`: Enable Response API for streaming

**Standard Models:**
- `temperature`: Randomness in generation (0.0-2.0)
- `max_tokens`: Maximum tokens to generate
- `top_p`: Nucleus sampling parameter
- `presence_penalty`: Penalty for repetition
- `frequency_penalty`: Penalty for frequent tokens

**Gemini-Specific:**
- `thinking_budget`: Budget for internal reasoning
- `max_output_tokens`: Maximum output tokens

## Quality Improvements & Natural Speech Patterns

The pipeline includes significant improvements to generate more natural, authentic conversations based on native speaker feedback.

### Natural Speech Pattern Enhancements

**Balanced Naturalness Framework:**
- Natural speech has minor imperfections, NOT broken grammar
- Particles enhance meaning; they don't replace proper grammar
- Maintain grammatical foundation while adding conversational elements
- Test: Would a native Malaysian speaker actually say this phrase?

**Refined Particle Usage:**
- Strategic usage (1-2 per turn), NOT excessive
- End-of-phrase placement for natural flow
- Warnings against overuse that breaks meaning
- Professional scammers use clearer grammar for credibility

**Balanced Filler/Disfluency Usage:**
- Moderate usage (1-3 per turn, not every sentence)
- Professional speakers use fewer fillers
- Casual speakers use more natural hesitations
- Context-appropriate disfluencies

**Enhanced Formality Matching:**
- **Professional scammers**: Clearer grammar for credibility
- **Government/bank staff**: Formal-professional hybrid
- **Service industry**: Casual-friendly with strategic particles
- **Elderly victims**: More traditional, fuller sentences
- **Young urban speakers**: More casual with code-switching

**Common Pitfalls Avoided:**
- Overusing particles until sentences lose meaning
- Using formal words incorrectly (e.g., "mengaku" when meaning "pastikan")
- Breaking grammar to force casualness
- Awkward constructions (e.g., "membangun kepercayaan" → "menguatkan kepercayaan")
- Mixing formality inconsistently within same character

### Scam Coverage Analysis

**Current Coverage vs LG Specifications:**
- **Macau Scam**: 26.3% (target 33.2%) - Close to target
- **E-commerce Fraud**: 15.8% (target 30.0%) - Needs expansion
- **Investment Fraud**: 10.5% (target 15.6%) - Small gap
- **Loan Fraud**: 10.5% (target 12.3%) - Very close

**Quality Metrics:**
- Native speakers find conversations natural
- Grammatical foundation maintained (no broken speech)
- Particle/filler usage feels appropriate (not excessive)
- Formality matches speaker role and context
- Professional scammers sound credible and authoritative

## API Requirements

- **OpenAI API**: For LLM conversation generation (default provider)
- **ElevenLabs API**: For text-to-speech synthesis
- **Translation Services**: Google Translate (default), Argos Translate (offline), Qwen-MT (Alibaba Cloud)
- **Optional**: Anthropic/Gemini APIs for alternative LLM providers

## Quality Assessment & Analysis Tools

The pipeline includes utility scripts for analyzing generated conversation quality and diversity:

### Diversity Measurement Script

The `scripts/measure_diversity.py` script calculates comprehensive diversity metrics for generated conversations:

```bash
# Analyze diversity for scam conversations
python scripts/measure_diversity.py scam_labeling/

# Analyze diversity for legit conversations
python scripts/measure_diversity.py legit_labeling/

# Analyze both types together
python scripts/measure_diversity.py scam_labeling/ legit_labeling/
```

**Metrics Calculated:**
- **Name Diversity**: Unique names, Shannon entropy, diversity score
- **Institution Diversity**: Unique institutions, distribution analysis
- **Conversation Type Diversity**: Distribution across scam types or legit categories
- **Most Common Entities**: Top 10 most frequently used names/institutions

**Output Format:**
- Human-readable report to stdout
- Optional JSON report (`--json` flag) for programmatic analysis

### Batch Audit Script

The `scripts/audit_ms_my_batch.py` script provides quick summaries of generated conversation batches:

```bash
# Audit a batch of conversations
python scripts/audit_ms_my_batch.py /path/to/conversation/folder
```

**Metrics Provided:**
- Top names and organizations (with counts and percentages)
- Average syllable count and percentage meeting >=1,500 threshold
- Average turn count and percentage meeting >=20 turns

## Human Labeling Support

The pipeline includes specialized scripts for generating conversations specifically for human labeling tasks.

### Labeling Generation Script

The `generate_for_labeling.py` script creates conversations optimized for human reviewers:

```bash
# Generate 250 scam conversations for labeling
python3 generate_for_labeling.py --type scam --count 250

# Generate 250 legitimate conversations for labeling
python3 generate_for_labeling.py --type legit --count 250
```

### Dual Output Format

**1. Comprehensive JSON (Reference)**
- Location: `output/ms-my/{timestamp}/conversations/`
- Contains: All metadata, token usage, cost estimates, conversations array
- Files: `scam_conversations.json` or `legit_conversations.json`

**2. Individual Files (For Labelers)**
- Location: `scam_labeling/` or `legit_labeling/` directories
- Files: `scam-1.json`, `scam-2.json`, ... or `legit-1.json`, `legit-2.json`, ...
- Each file contains complete conversation object with all metadata

### Smart Seed Distribution

**Maximum Diversity Strategy:**
- Distributes conversations across all 19 available seeds
- Each seed generates ~13 conversations (250 ÷ 19 ≈ 13)
- Covers all scam categories with balanced representation:
  - **Macau Scam** (4 seeds) → ~52 conversations
  - **E-commerce Fraud** (4 seeds) → ~52 conversations
  - **Voice Scam** (4 seeds) → ~52 conversations
  - **Investment Scam** (1 seed) → ~13 conversations
  - **Loan Fraud** (2 seeds) → ~26 conversations
  - **Other Categories** (4 seeds) → ~52 conversations

### Individual File Structure

Each labeling file contains complete conversation metadata:

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

### Features for Labelers

All conversations include:
- ✅ Natural Malay speech patterns (colloquial particles, fillers, contractions)
- ✅ Character profiles (diverse personalities and speaking styles)
- ✅ Locale-specific placeholders (Malaysian context)
- ✅ Pre-configured scenarios (category-balanced)
- ✅ Voice assignments (for future TTS)
- ✅ Smart seed distribution (maximizes diversity across all 19 scam seeds)

## Voice Management & Validation System

The pipeline includes comprehensive voice ID validation and management to ensure audio generation reliability across all locales.

### Core Features

- **Real-time validation**: Verify voice IDs against ElevenLabs API with detailed error reporting
- **Bulk validation**: Check all voice IDs across all locales simultaneously with progress tracking
- **Automatic cleanup**: Remove invalid voice IDs from configuration files with backup
- **Voice suggestions**: Get AI-powered voice recommendations based on locale compatibility
- **Minimum requirements**: Ensure each locale has ≥2 voices for redundancy with health scoring
- **Interactive management**: GUI-based voice management through interactive mode
- **Compatibility scoring**: Rate voice-locale compatibility with confidence scores
- **Voice discovery**: Automatic detection of available voices with metadata

### ElevenLabs v3 Features

- **Enhanced Expressiveness**: `eleven_multilingual_v3` model with improved pronunciation and intonation
- **Audio Tags**: Context-aware emotional tagging ([excited], [whispers], [urgent], etc.)
- **Voice Settings**: Configurable stability, similarity boost, style, and speaker boost
- **High-Quality Audio**: PCM 44.1kHz uncompressed audio options
- **Emotional Context**: Conversation-type specific emotions (scam vs. legit)
- **Position-Aware Tags**: Different emotional contexts for opening, middle, and closing turns

### CLI Commands

#### Voice Validation
```bash
# Validate voices for specific locale
python main.py --validate-voices ar-sa

# Validate all voice IDs across all locales
python main.py --validate-all-voices

# Remove invalid voice IDs from all configurations
python main.py --update-voice-configs

# Check minimum voice requirements (≥2 per locale)
python main.py --ensure-minimum-voices

# Get voice suggestions for a specific locale
python main.py --suggest-voices ar-sa
```

#### Voice Management Workflow
```bash
# 1. Check current voice health
python main.py --validate-all-voices

# 2. Get suggestions for locales needing more voices
python main.py --suggest-voices ar-sa

# 3. Clean up invalid voice IDs
python main.py --update-voice-configs

# 4. Verify all requirements are met
python main.py --ensure-minimum-voices
```

### Interactive Voice Management

Launch interactive mode for guided voice management:

```bash
python main.py
```

Navigate to: **Configuration Management** → **Voice ID Management**

#### Interactive Features:

1. **Voice Health Check**
   - Check individual locale or all locales
   - Real-time API validation with detailed results
   - Automatic follow-up options when issues are found

2. **Voice Suggestions**
   - AI-powered voice recommendations based on locale language
   - Confidence scoring and compatibility analysis
   - One-click voice addition to configuration

3. **Manual Voice Addition**
   - Real-time voice ID validation during entry
   - Automatic voice name detection from API
   - Duplicate detection and prevention

4. **Automatic Cleanup**
   - Batch removal of invalid voice IDs
   - Configuration backup and safe updates
   - Progress tracking for bulk operations

## Interactive UI System

The interactive mode provides a comprehensive menu-driven interface for all pipeline operations.

### Main Menu Options
1. **Select Locale/Language** - Choose target locale with detailed information
2. **Run Full Pipeline** - Execute complete generation pipeline
3. **Run Specific Steps** - Select individual pipeline steps
4. **Configuration Management** - Manage all configuration aspects
5. **Monitoring & Status** - Check output status and recent runs
6. **Help & Information** - Access documentation and troubleshooting

### Configuration Management Submenu
- **Voice ID Management**: Complete voice validation and suggestion system
- **Voice Quality & V3 Features**: TTS model and quality settings
- **Locale Validation**: Configuration validation and health checking
- **Settings Overview**: View all current configuration settings

### Voice Management Features
- **Voice Health Check**: Real-time validation with detailed results
- **Voice Suggestions**: AI-powered recommendations based on locale compatibility
- **Manual Voice Addition**: Real-time validation during entry with automatic name detection
- **Automatic Cleanup**: Batch removal of invalid voice IDs with progress tracking
- **Minimum Requirements Check**: Ensure all locales meet voice count requirements

### Voice Quality Management
- **TTS Model Selection**: Choose between turbo, flash, and v3 models
- **V3 Features Configuration**: Audio tags, emotional context, conversation context
- **Voice Settings**: Stability, similarity boost, style, speaker boost
- **Audio Format**: Multiple MP3 formats with quality options
- **Settings Reset**: Restore default configurations

### Monitoring & Status
- **Output Directory Status**: Check generation history and file counts
- **Recent Pipeline Runs**: View execution history and results
- **Directory Cleanup**: Manage old generations and storage
- **Health Monitoring**: System status and configuration validation

### Character Profiles & Scenario Management

The pipeline includes advanced character profiling and scenario management for creating diverse, authentic conversations.

### Character Profiles

Character profiles define personality traits, speaking styles, and demographic information for conversation participants:

```json
{
  "profile_id": "scammer_professional_male",
  "name": "Ahmad Hassan",
  "gender": "male",
  "age_range": "middle-aged",
  "personality_traits": ["authoritative", "patient", "manipulative"],
  "speaking_style": ["formal", "persuasive", "calm"],
  "education_level": "college",
  "locale_affinity": ["ar-sa", "ar-ae"],
  "role_preference": "scammer"
}
```

### Scenario Templates

Pre-configured scenario templates ensure balanced scam type distribution and realistic conversation flows:

- **Template Assignment**: Each seed is mapped to 5 specific templates for maximum diversity
- **Category Balance**: Follows Malaysian scam statistics (Macau Scam 33.2%, E-commerce 30%, etc.)
- **Character Pairing**: Optimized scammer-victim combinations based on psychology
- **Turn Management**: 20-24 turns with natural conversation progression

### Voice Profile Integration

Voice profiles enable intelligent voice assignment based on character context:

```json
{
  "available_voices": {
    "ahmad": {
      "id": "elevenlabs_voice_id",
      "name": "Ahmad Hassan",
      "gender": "male",
      "age": "middle-aged",
      "description": "Professional male voice with local accent",
      "use_cases": ["authority", "professional", "government"]
    }
  },
  "role_assignments": {
    "scam_scenarios": {
      "police_officer": ["ahmad", "khalid"],
      "bank_officer": ["sarah"],
      "female_victim": ["fatima", "aisha"],
      "male_victim": ["omar", "yousef"]
    }
  }
}
```

### Voice Configuration Structure

Voice IDs are stored in locale configuration files:

```json
{
  "voices": {
    "ids": [
      "u0TsaWvt0v8migutHM3M",
      "A9ATTqUUQ6GHu0coCz8t",
      "R6nda3uM038xEEKi7GFl"
    ],
    "names": [
      "Ghizlane (Female/Adult)",
      "Hamid (Male/Adult)", 
      "Anas (Male/Young)"
    ]
  }
}
```

### Voice Quality Considerations

- **Minimum Requirements**: Each locale needs ≥2 valid voices for reliability
- **Language Compatibility**: Voices should match locale language for best results
- **Regional Accents**: Consider regional accent compatibility when adding voices
- **Voice Diversity**: Mix of genders and age ranges improves dataset quality

### Legacy Files
- `archive/` contains the original language-specific scripts
- `configs/languages/` old language configurations (deprecated)
- `data/input/placeholder_maps/` old placeholder maps (migrated to locale directories)

## Enhanced Command-Line Options

### Generation Control
```bash
# Generation modes
--generation-mode seeds          # Limit by number of seeds (default)
--generation-mode conversations  # Limit by total conversations

# Generation limits
--seed-limit N                   # Number of seeds to process
--conversation-count N           # Target number of conversations
--scam-limit N                   # Limit scam conversations only
--legit-limit N                  # Limit legitimate conversations only
--total-limit N                  # Absolute maximum conversations (overrides all)
--scenarios-per-seed N           # Override scenarios per seed

# Generation types
--scam                           # Generate only scam conversations
--legit                          # Generate only legitimate conversations
```

### LLM Configuration
```bash
# Model selection
--model MODEL_NAME               # Override LLM model (e.g., gpt-5-nano)
--reasoning-effort LEVEL         # Reasoning effort for GPT-5 (minimal/low/medium/high)
--random-seed N                  # Set random seed for reproducibility
```

### Output Control
```bash
# Timestamp control
--use-timestamp TIMESTAMP        # Use specific timestamp or "new"
--no-timestamp                   # Use old directory structure (no timestamps)

# Output management
--output-dir PATH                # Custom output directory
--force                          # Overwrite existing files
```

### Voice Management
```bash
# Voice validation
--validate-voices LOCALE         # Validate voices for specific locale
--validate-all-voices            # Validate all voice IDs
--update-voice-configs           # Remove invalid voice IDs
--ensure-minimum-voices          # Check minimum voice requirements
--suggest-voices LOCALE          # Get voice suggestions
```

## Performance Considerations

- Use `--steps` to run specific pipeline stages for faster iteration
- Use `--total-limit N` for testing with smaller datasets
- Audio generation is rate-limited to avoid API throttling
- Large datasets should be processed in batches
- Consider running overnight for full datasets
- Monitor API quotas for OpenAI and ElevenLabs
- Use `--generation-mode seeds` for more predictable generation counts
- Enable token tracking to monitor costs: `"track_tokens": true`

## Data Privacy & Ethics

- All conversations are synthetic - no real personal data is used
- Generated for research and defensive security purposes only
- Do not use generated content for malicious purposes
- Respect API usage terms and quotas
- Consider cultural sensitivity when creating regional substitutions

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure `.env` file contains valid keys
2. **"'locale' KeyError"**: Update config to new standardized structure with `"locale"` section
3. **Translation failures**: 
   - Hong Kong/Taiwan: use `"zh-TW"` (not `"zh-HK"`)
   - Singapore/Mainland China: use `"zh-CN"` (not `"zh"`)
4. **Locale Config Not Found**: Check locale ID format (e.g., ar-sa, not arabic-sa)
5. **Audio Generation Fails**: Verify ElevenLabs quota and voice IDs
6. **Translation Errors**: Check internet connection and Google Translate API limits
7. **Missing Placeholder Mappings**: Ensure all 53 placeholders are defined
8. **Voice Synthesis Quota**: ElevenLabs has monthly character limits
9. **LLM Parameter Warnings**: Parameters are now passed directly to model constructors
10. **Translation Cache Not Working**: Cache will not work if source file is modified after cache is created. Use ```find data/translation_cache -type f -exec touch {} \;``` to refresh the cache timestamp to bypass
11. **Character Profiles Not Loading**: Ensure `configs/character_profiles.json` exists and is valid
12. **Seed File Not Found**: Check that `scam_samples.json` exists in the correct location
13. **Voice ID Validation Fails**: Use `--validate-voices` to check voice ID validity
14. **Reasoning Model Errors**: Ensure you have access to GPT-5 models and proper API keys
15. **Token Tracking Issues**: Enable `track_tokens: true` in configuration
16. **V3 Features Not Working**: Ensure you're using a v3 model (eleven_multilingual_v3)
17. **Generation Mode Errors**: Use `--generation-mode seeds` or `--generation-mode conversations`
18. **Voice Quality Issues**: Use interactive mode to configure voice settings
19. **Natural Speech Issues**: Review quality improvements documentation for speech pattern guidelines
20. **Interactive UI Not Working**: Ensure all dependencies are installed and virtual environment is activated

### Debug Mode

Run with verbose logging:
```bash
python main.py --locale ms-my --verbose
```

## License

This project is for research purposes only. Generated conversations are synthetic and should not be used for malicious purposes. 