# Scam Conversation Generation Pipeline

This pipeline generates realistic scam phone conversations with audio synthesis using advanced character profiles, scenario-based generation, and multi-provider LLM support. The system creates diverse, culturally-appropriate conversations through seed-based generation, character-driven dialogue, and high-quality voice synthesis with ElevenLabs v3 features.

This pipeline generates realistic scam phone conversations with audio synthesis.

## Quick Start

### Prerequisites

#### Using uv (Recommended)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies from lock file (reproducible)
uv pip sync uv.lock

# Or install from requirements.txt (latest compatible versions)
uv pip install -r requirements.txt

# Update lock file after changing requirements.txt
uv pip compile requirements.txt -o uv.lock

# Activate virtual environment
source .venv/bin/activate
```

#### Using pip (Alternative)
```bash
pip install -r requirements.txt
```

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
├── src/                          # Source code modules
│   ├── config/                     # Configuration management
│   │   └── config_loader.py          # Unified configuration loader
│   ├── translation/                # Translation utilities (for future use)
│   │   ├── translator.py             # Base translator interface
│   │   └── language_codes.py         # Language code mappings
│   ├── conversation/               # LLM dialogue generation
│   │   ├── scam_generator.py         # Scam conversation generation
│   │   ├── legit_generator.py        # Legitimate conversation generation
│   │   ├── schemas.py                # Pydantic schemas for structured output
│   │   ├── seed_manager.py           # Seed data management
│   │   └── character_manager.py      # Character profile and voice mapping
│   ├── llm_core/                   # LLM abstraction layer with LangChain
│   │   ├── api_provider.py           # Multi-provider LLM factory
│   │   └── api_call.py               # Unified async API interface
│   ├── tts/                        # ElevenLabs voice synthesis
│   │   ├── voice_synthesizer.py
│   │   └── audio_combiner.py
│   ├── postprocessing/             # Output formatting and packaging
│   │   ├── json_formatter.py
│   │   └── audio_packager.py
│   ├── pipeline/                   # Pipeline orchestration
│   │   └── runner.py
│   └── cli/                        # Command-line interface
│       ├── commands.py               # CLI command implementations
│       ├── ui.py                     # Interactive menu interface
│       └── utils.py                  # CLI utility functions
├── configs/                      # Configuration files
│   ├── common.json                 # Shared settings across all locales
│   └── localizations/              # Locale-specific configurations
│       ├── ar-sa/                    # Arabic - Saudi Arabia
│       │   ├── config.json             # Locale configuration
│       │   └── placeholders.json       # Regional placeholder mappings
│       ├── ar-ae/                    # Arabic - United Arab Emirates
│       │   ├── config.json
│       │   └── placeholders.json
│       └── ms-my/                    # Malay - Malaysia
│           ├── config.json
│           └── placeholders.json
├── data/                         # Input data and resources
│   └── input/
│       ├── deduplicated_seeds_no_email.json  # Seed data for conversation generation
│       ├── seeds_and_placeholders.json       # Seed data with placeholder mappings
│       └── sound_effects/                    # Background noise for audio              
├── archive/                      # Legacy language-specific scripts
└── output/                       # Generated outputs (gitignored)
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

See the [Locale Roadmap](locale_road_map.md) for current implementation status.

#### Production-Ready (New Pipeline)
- **ms-my**: Malay (Malaysia) - MYR currency, Malaysian entities ✅ ✨
  - Updated placeholder schema format for optimized pipeline
  - Character-voice mappings in `voice_profiles.json`
  - ~45% reduction in API costs through prompt caching
  - Compact JSON format for placeholders

#### Legacy Format (Requires Migration)
- **ar-sa**: Arabic (Saudi Arabia) - SAR currency, Saudi entities ⚠️
- **ar-ae**: Arabic (United Arab Emirates) - AED currency, UAE entities ⚠️
- **id-id**: Indonesian (Indonesia) - IDR currency, Indonesian entities ⚠️
- **ko-kr**: Korean (South Korea) - KRW currency, Korean entities ⚠️
- **ja-jp**: Japanese (Japan) - JPY currency, Japanese entities ⚠️
- **vi-vn**: Vietnamese (Vietnam) - VND currency, Vietnamese entities ⚠️
- **en-ph**: English (Philippines) - PHP currency, Filipino entities ⚠️
- **th-th**: Thai (Thailand) - THB currency, Thai entities ⚠️
- **en-sg**: English (Singapore) - SGD currency, Singaporean entities ⚠️
- **zh-sg**: Chinese (Singapore) - SGD currency, Singaporean entities ⚠️
- **zh-tw**: Chinese (Taiwan) - TWD currency, Taiwanese entities ⚠️
- **zh-hk**: Chinese (Hong Kong) - HKD currency, Hong Kong entities ⚠️
- **en-hk**: English (Hong Kong) - HKD currency, Hong Kong entities ⚠️

**⚠️ IMPORTANT**: Currently only **ms-my** works with the new optimized pipeline. Other locales need:
1. Updated `placeholders.json` schema
2. Addition of `voice_profiles.json` with character mappings
3. Testing with the new pipeline

## LLM Module

The project includes a unified LLM abstraction layer (`src/llm_core/`) that supports multiple providers with advanced features:

### Supported LLM Providers
- **OpenAI**: GPT-4, GPT-4o, GPT-5-nano, GPT-5 (with reasoning), GPT-3.5-turbo
- **Anthropic**: Claude-3.5-Sonnet, Claude-3-Haiku, Claude-3-Opus
- **Google**: Gemini-1.5-Pro, Gemini-1.5-Flash, Gemini-1.0-Pro
- **LM-Studio**: Local model hosting with custom endpoints
- **OpenAI**: GPT-5 models
- **Anthropic**: Claude models
- **Google**: Gemini models
- **LM-Studio**: Local model hosting
- **vLLM**: High-performance inference server

### Advanced LLM Features

**Reasoning Models:**
- GPT-5 models with configurable reasoning effort levels
- Automatic reasoning token tracking
- Enhanced prompt engineering for complex tasks

**Token Tracking & Cost Management:**
- Comprehensive token usage tracking across all providers
- Real-time cost estimation with provider-specific pricing
- Session-based aggregation and reporting
- Budget monitoring and alerts

**Enhanced Configuration:**
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-5-nano",
    "reasoning_effort": "minimal",
    "max_concurrent_requests": 20,
    "model": "gpt-4o-mini",
    "max_concurrent_requests": 10,
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

## API Requirements

- **OpenAI API**: For LLM conversation generation (default provider)
- **ElevenLabs API**: For text-to-speech synthesis
- **Translation Services**: Google Translate (default), Argos Translate (offline), Qwen-MT (Alibaba Cloud)
- **Optional**: Anthropic/Gemini APIs for alternative LLM providers

## Voice ID Validation System

The pipeline includes comprehensive voice ID validation and management to ensure audio generation reliability across all locales.

### Features

- **Real-time validation**: Verify voice IDs against ElevenLabs API with detailed error reporting
- **Bulk validation**: Check all voice IDs across all locales simultaneously with progress tracking
- **Automatic cleanup**: Remove invalid voice IDs from configuration files with backup
- **Voice suggestions**: Get AI-powered voice recommendations based on locale compatibility
- **Minimum requirements**: Ensure each locale has ≥2 voices for redundancy with health scoring
- **Interactive management**: GUI-based voice management through interactive mode
- **Compatibility scoring**: Rate voice-locale compatibility with confidence scores
- **Voice discovery**: Automatic detection of available voices with metadata

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

## Interactive UI Enhancements

The interactive mode includes comprehensive management interfaces:

### Main Menu Options
1. **Select Locale/Language** - Choose target locale with detailed information
2. **Run Full Pipeline** - Execute complete generation pipeline
3. **Run Specific Steps** - Select individual pipeline steps
4. **Configuration Management** - Manage all configuration aspects
5. **Monitoring & Status** - Check output status and recent runs
6. **Help & Information** - Access documentation and troubleshooting

### Configuration Management
- **Voice ID Management**: Complete voice validation and suggestion system
- **Voice Quality & V3 Features**: TTS model and quality settings
- **Locale Validation**: Configuration validation and health checking
- **Settings Overview**: View all current configuration settings

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
10. **Translation Cache Not Working**: Cache will not work if source file is modified after cache is created. Use ```find data/translation_cache -type f -exec touch {} \;``` to refresh the cache timestamp to by pass
11. **Character Profiles Not Loading**: Ensure `configs/character_profiles.json` exists and is valid
12. **Seed File Not Found**: Check that `scam_samples.json` exists in the correct location
13. **Voice ID Validation Fails**: Use `--validate-voices` to check voice ID validity
14. **Reasoning Model Errors**: Ensure you have access to GPT-5 models and proper API keys
15. **Token Tracking Issues**: Enable `track_tokens: true` in configuration
16. **V3 Features Not Working**: Ensure you're using a v3 model (eleven_multilingual_v3)
17. **Generation Mode Errors**: Use `--generation-mode seeds` or `--generation-mode conversations`
18. **Voice Quality Issues**: Use interactive mode to configure voice settings
3. **Locale Config Not Found**: Check locale ID format (e.g., ar-sa, not arabic-sa)
4. **Audio Generation Fails**: Verify ElevenLabs quota and voice IDs
5. **Missing Placeholder Mappings**: Ensure all 98 placeholders are defined
6. **Voice Synthesis Quota**: ElevenLabs has monthly character limits
7. **LLM Parameter Warnings**: Parameters are now passed directly to model constructors
8. **Generation Count**: Use `--sample-limit` to control number of conversations generated

### Debug Mode

Run with verbose logging:
```bash
python main.py --locale ms-my --verbose
```

## License

This project is for research purposes only. Generated conversations are synthetic and should not be used for malicious purposes. 