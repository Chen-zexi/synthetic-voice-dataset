# Scam Conversation Generation Pipeline

This pipeline generates realistic scam phone conversations with audio synthesis using advanced character profiles, scenario-based generation, and multi-provider LLM support. The system creates diverse, culturally-appropriate conversations through seed-based generation, character-driven dialogue, and high-quality voice synthesis with ElevenLabs v3 features.


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
# Run full pipeline for Saudi Arabia (Arabic)
python main.py --locale ar-sa

# Run full pipeline for UAE (Arabic)
python main.py --locale ar-ae

# Run specific steps for Malaysia (Malay)
# Available steps: conversation, legit, tts, postprocess
python main.py --locale ms-my --steps conversation

# Run with character profiles and scenario-based generation
python main.py --locale ms-my --steps conversation --scam-limit 10

# Run with generation control modes
python main.py --locale ar-sa --generation-mode seeds --seed-limit 5
python main.py --locale ar-sa --generation-mode conversations --conversation-count 20

# Run with specific LLM model
python main.py --locale ar-sa --model gpt-5-nano --reasoning-effort minimal

# Run with custom voice settings
python main.py --locale ar-sa --steps tts --force

# List available locales
python main.py --list-locales

# Backward compatibility with old language parameter
python main.py --language arabic  # Maps to ar-sa

# Validate configuration
python main.py --validate-config ar-sa

# Show available pipeline steps
python main.py --show-steps

# Test with limited samples
python main.py --locale ar-sa --total-limit 10

# Force overwrite existing files
python main.py --locale ar-sa --force
```

#### Translation Cache

The pipeline supports caching Chinese-to-English translations to avoid redundant API calls when running multiple locales:

```bash
# Generate cached translation using Google Translate
python main.py --cache-translation --cache-service google

# Generate cached translation using Qwen with specific model
python main.py --cache-translation --cache-service qwen --cache-model qwen-mt-turbo

# Force refresh existing cache
python main.py --cache-translation --cache-service google --cache-force-refresh

# List all cached translations
python main.py --list-cached-translations
```

**Cache Configuration** (in `configs/common.json`):
```json
"translation_cache": {
  "enabled": true,           # Enable cache system
  "use_cache": true,         # Use cache in pipeline if available
  "cache_dir": "data/translation_cache",
  "cache_service": "qwen",   # Which service's cache to use
  "force_refresh": false
}
```

**Cache Features**:
- Stores translations by service (google, argos, qwen)
- For Qwen, stores separate caches per model (turbo, plus)
- Validates cache against source file modification time
- Automatically uses cache when available (if `use_cache: true`)
- Links cached files directly without copying

## Pipeline Overview

The pipeline consists of four main steps with advanced character-driven generation:

1. **conversation**: Generate multi-turn scam dialogues using LLM with character profiles
2. **legit**: Generate legitimate (non-scam) conversations using LLM with character profiles
3. **tts**: Convert conversations to audio using ElevenLabs with v3 features
4. **postprocess**: Format JSON files and package audio

### Character Profiles & Scenario-Based Generation

The system uses advanced character profiles and scenario-based generation for authentic, diverse conversations:

- **141 High-Quality Scam Scenarios**: Pre-curated scam patterns across 14 categories
- **15 Character Profiles**: Diverse scammer and victim personalities with cultural adaptation
- **Dynamic Placeholder System**: 53 culturally-appropriate placeholders with smart selection
- **Quality Filtering**: Only uses high-quality seeds (configurable threshold)
- **Multiple Scenarios per Seed**: Generate varied conversations from the same scam type

## Project Structure

```
voice_scam_dataset_gen/
├── main.py                       # Main entry point
├── src/                          # Source code modules
│   ├── config/                     # Configuration management
│   │   └── config_loader.py          # Unified configuration loader
│   ├── preprocessing/              # Tag extraction from Chinese source
│   │   └── tag_extractor.py          # Placeholder tag extraction
│   ├── translation/                # Multi-service translation
│   │   ├── translator.py             # Base translator interface
│   │   ├── google_translator.py      # Google Translate API
│   │   ├── argos_translator.py       # Offline Argos Translate
│   │   ├── qwen_translator.py        # Alibaba Cloud Qwen-MT
│   │   ├── cache_translator.py       # Translation caching system
│   │   └── language_codes.py         # Language code mappings
│   ├── conversation/               # LLM dialogue generation
│   │   ├── scam_generator.py         # Scam conversation generation
│   │   ├── legit_generator.py        # Legitimate conversation generation
│   │   └── schemas.py                # Pydantic schemas for structured output
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
│       ├── scam_first_line_chinese.txt  
│       └── sound_effects/              
├── archive/                      # Legacy language-specific scripts
└── output/                       # Generated outputs (gitignored)
    ├── ar-sa/                      # Saudi Arabia Arabic outputs
    ├── ar-ae/                      # UAE Arabic outputs
    └── ms-my/                      # Malaysia Malay outputs
```

## Advanced Features

### Character Profiles System

The pipeline includes a sophisticated character profile system for creating diverse, authentic conversations:

**Character Types:**
- **Scammers**: Authoritative figures, friendly helpers, tech support impersonators, government officials, investment advisors
- **Victims**: Trusting individuals, skeptical persons, busy professionals, confused seniors, tech-savvy users, anxious people, students

**Profile Attributes:**
- Gender, age range, personality traits, speaking style, education level
- Locale affinity for cultural adaptation
- Role preferences (scammer/victim/any)

**Configuration:**
```json
{
  "generation": {
    "enable_character_profiles": true,
    "profiles_file": "configs/character_profiles.json",
    "scenarios_per_seed": 2,
    "min_seed_quality": 70
  }
}
```

### Scenario-Based Generation

Instead of line-by-line text processing, the system uses rich scenario-based generation:

**Seed Management:**
- 141 high-quality scam scenarios from `scam_samples.json`
- Quality scoring and filtering (0-100 scale)
- Category-based organization (14 scam categories)
- Dynamic placeholder integration

**Generation Modes:**
```bash
# Seed-based generation (default)
python main.py --locale ar-sa --generation-mode seeds --seed-limit 10

# Conversation-based generation
python main.py --locale ar-sa --generation-mode conversations --conversation-count 50

# Mixed mode with specific limits
python main.py --locale ar-sa --scam-limit 20 --legit-limit 10
```

### Enhanced LLM Core

Multi-provider LLM support with advanced features:

**Supported Providers:**
- **OpenAI**: GPT-4, GPT-4o, GPT-5-nano, GPT-5 (with reasoning)
- **Anthropic**: Claude-3.5-Sonnet, Claude-3-Haiku
- **Google**: Gemini-1.5-Pro, Gemini-1.5-Flash
- **Local**: LM-Studio, vLLM servers

**Advanced Features:**
- Reasoning model support with effort levels
- Token tracking and cost estimation
- Concurrent API calls with rate limiting
- Structured output with JSON fallback
- Response API integration (OpenAI)

**Configuration:**
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-5-nano",
    "reasoning_effort": "minimal",
    "max_concurrent_requests": 20,
    "track_tokens": true
  }
}
```

### ElevenLabs v3 Features

Advanced voice synthesis with emotional context and expressiveness:

**v3 Capabilities:**
- Audio tags for emotional context (urgent, friendly, concerned, etc.)
- Enhanced voice settings (stability, similarity, style, speaker boost)
- Conversation context awareness
- Multiple TTS models (turbo, flash, multilingual v2/v3)

**Voice Quality Management:**
```bash
# Interactive voice quality configuration
python main.py
# Navigate to: Configuration Management → Voice Quality & V3 Features

# Change TTS model
python main.py --locale ar-sa --steps tts --model eleven_multilingual_v3

# Configure voice settings
python main.py --locale ar-sa --steps tts --voice-stability 0.7
```

**Audio Processing:**
- Background noise and call effects
- Bandpass filtering for phone quality
- Multiple audio formats (MP3, various bitrates)
- Silence insertion and volume normalization

### Dynamic Placeholder System

Intelligent placeholder replacement with cultural adaptation:

**53 Placeholder Types:**
- Personal names, locations, companies, amounts
- Government agencies, services, products
- Dates, times, account numbers, reference codes

**Smart Selection:**
- Random selection from culturally-appropriate arrays
- Conversation-level consistency (same placeholder = same value)
- Cross-conversation diversity for dataset variety

**Configuration:**
```json
{
  "generation": {
    "enable_dynamic_placeholders": true,
    "batch_size": 10,
    "random_seed": null
  }
}
```

### Voice Management System

Comprehensive voice ID validation and management:

**Voice Health Checking:**
```bash
# Validate voices for specific locale
python main.py --validate-voices ar-sa

# Validate all voices across all locales
python main.py --validate-all-voices

# Get voice suggestions for locale
python main.py --suggest-voices ar-sa

# Clean up invalid voice IDs
python main.py --update-voice-configs

# Ensure minimum voice requirements
python main.py --ensure-minimum-voices
```

**Features:**
- Real-time voice ID validation
- Compatibility scoring and suggestions
- Automatic cleanup of invalid IDs
- Minimum requirements enforcement (≥2 voices per locale)
- Interactive voice management through CLI

### Token Tracking & Cost Management

Comprehensive cost tracking across all providers:

**Token Tracking:**
- Input/output token counting
- Reasoning token tracking (GPT-5 models)
- Cached token tracking
- Audio token tracking (multimodal models)
- Session-based aggregation

**Cost Estimation:**
- Real-time cost calculation
- Provider-specific pricing
- Session summaries
- Budget monitoring

**Configuration:**
```json
{
  "llm": {
    "track_tokens": true,
    "use_response_api": true
  }
}
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

### 3. Configure Locale Settings
Edit `configs/localizations/ar-eg/config.json` with the **new standardized structure**:

```json
{
  "locale": {
    "id": "ar-eg",
    "language_code": "ar",
    "country_code": "EG",
    "language_name": "Arabic",
    "region_name": "Egypt",
    "currency": "EGP",
    "currency_symbol": "جنيه"
  },
  "translation": {
    "from_code": "zh-CN",
    "to_code": "ar",
    "intermediate_code": "en"
  },
  "voices": {
    "ids": ["voice_id_1", "voice_id_2", "voice_id_3"],
    "names": ["Voice1 (Gender/Age)", "Voice2 (Gender/Age)", "Voice3 (Gender/Age)"]
  },
  "conversation": {
    "legit_categories": [
      "family_checkin", "friend_chat", "relationship_talk",
      "holiday_greeting", "emergency_help_request",
      "doctor_appointment_confirmation", "clinic_test_results",
      "delivery_confirmation", "utility_service_followup",
      "repair_scheduling", "bank_verification_call",
      "visa_status_update", "tax_inquiry"
    ]
  },
  "output": {
    "scam_conversation": "scam_conversation.json",
    "legit_conversation": "legit_conversation.json",
    "scam_audio_dir": "scam",
    "legit_audio_dir": "legit",
    "scam_formatted": "scam_conversation_formatted.json",
    "legit_formatted": "legit_conversation_formatted.json"
  },
  "cultural_notes": {
    "phone_greeting": "السلام عليكم / أهلاً",
    "formality_level": "Formal - Arabic uses respectful forms",
    "common_scam_themes": [
      "Government agency impersonation",
      "Bank security calls",
      "Investment scams"
    ]
  }
}
```

### 4. Populate All 53 Placeholders
Edit `configs/localizations/ar-eg/placeholders.json` with culturally appropriate substitutions for all placeholders ({00001} through {00053}).

### 5. Test and Validate
```bash
# Validate configuration
python main.py --validate-config ar-eg

# Test with sample data
python main.py --locale ar-eg --sample-limit 5

# Run full pipeline
python main.py --locale ar-eg
```

### 6. Update Documentation
- Mark locale as "✅ Completed" in [locale_road_map.md](locale_road_map.md)
- Test all 53 placeholders are populated
- Verify cultural appropriateness

For detailed implementation instructions, troubleshooting, and placeholder reference, see the [Locale Implementation Guide](LOCALE_IMPLEMENTATION_GUIDE.md).

## Output Structure

```
output/
└── {locale-id}/              # e.g., ar-sa, ar-ae, ms-my
    ├── intermediate/         # Processing artifacts
    │   ├── preprocessed/     # Placeholder-mapped Chinese text
    │   ├── translated/       # English translations
    │   └── conversations/    # Generated conversations
    ├── audio/               # Generated audio files
    │   ├── scam/           # Scam conversation audio
    │   └── legit/          # Legitimate conversation audio
    └── final/              # Final formatted outputs
        ├── json/           # Labeled conversation data
        └── archives/       # ZIP files with audio
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
- Tags like `<person_name>`, `<city_name>` in source text become `{00001}`, `{00002}`
- Each locale provides culturally appropriate substitutions
- Consistent replacement across all conversations in a dataset
- Validation warns about missing mappings

### Supported Locales

See the [Locale Roadmap](locale_road_map.md) for current implementation status. Currently supported:

- **ar-sa**: Arabic (Saudi Arabia) - SAR currency, Saudi entities
- **ar-ae**: Arabic (United Arab Emirates) - AED currency, UAE entities  
- **ms-my**: Malay (Malaysia) - MYR currency, Malaysian entities
- **ko-kr**: Korean (South Korea) - KRW currency, Korean entities
- **ja-jp**: Japanese (Japan) - JPY currency, Japanese entities
- **vi-vn**: Vietnamese (Vietnam) - VND currency, Vietnamese entities
- **en-ph**: English (Philippines) - PHP currency, Filipino entities
- **th-th**: Thai (Thailand) - THB currency, Thai entities
- **en-sg**: English (Singapore) - SGD currency, Singaporean entities
- **zh-sg**: Chinese (Singapore) - SGD currency, Singaporean entities
- **zh-tw**: Chinese (Taiwan) - TWD currency, Taiwanese entities
- **zh-hk**: Chinese (Hong Kong) - HKD currency, Hong Kong entities
- **en-hk**: English (Hong Kong) - HKD currency, Hong Kong entities

## LLM Module

The project includes a unified LLM abstraction layer (`src/llm_core/`) that supports multiple providers with advanced features:

### Supported LLM Providers
- **OpenAI**: GPT-4, GPT-4o, GPT-5-nano, GPT-5 (with reasoning), GPT-3.5-turbo
- **Anthropic**: Claude-3.5-Sonnet, Claude-3-Haiku, Claude-3-Opus
- **Google**: Gemini-1.5-Pro, Gemini-1.5-Flash, Gemini-1.0-Pro
- **LM-Studio**: Local model hosting with custom endpoints
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

### Voice Validation API Integration

The system integrates with ElevenLabs API for:

- **Voice Discovery**: Automatic detection of available voices
- **Compatibility Checking**: Language and accent matching
- **Real-time Validation**: Instant verification of voice ID accessibility
- **Metadata Extraction**: Voice names, languages, and accent information

### Troubleshooting Voice Issues

#### Common Problems

1. **Voice ID Not Found**: Voice may have been removed from ElevenLabs
   - **Solution**: Use `--update-voice-configs` to clean invalid IDs
   - **Prevention**: Regular validation with `--validate-all-voices`

2. **Insufficient Voices**: Locale has <2 voices
   - **Solution**: Use `--suggest-voices LOCALE` to find compatible voices
   - **Interactive**: Use Voice Management menu for guided addition

3. **API Rate Limiting**: Too many validation requests
   - **Solution**: Built-in rate limiting prevents API throttling
   - **Batch Processing**: Validation uses concurrent requests with semaphores

4. **Language Mismatch**: Voice language doesn't match locale
   - **Detection**: Voice suggestions include compatibility scoring
   - **Manual Check**: Review voice metadata in interactive mode

#### Debug Voice Validation

```bash
# Verbose validation output
python main.py --validate-all-voices --verbose

# Interactive troubleshooting
python main.py
# Navigate to: Help & Information → Troubleshooting Tips
```

## Migration from Legacy System

The system maintains backward compatibility with the old language-based structure:

### Backward Compatibility
```bash
# Old format (still works)
python main.py --language arabic  # Maps to ar-sa
python main.py --language malay   # Maps to ms-my

# New format (recommended)
python main.py --locale ar-sa
python main.py --locale ms-my
```

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

### Debug Mode

Run with verbose logging:
```bash
python main.py --locale ar-sa --verbose
```

### Validation Commands

#### Command Line
```bash
# List all available locales
python main.py --list-locales

# Validate a specific configuration
python main.py --validate-config ar-sa

# Validate voice IDs for specific locale
python main.py --validate-voices ar-sa

# Validate all voice IDs across all locales
python main.py --validate-all-voices

# Show pipeline steps
python main.py --show-steps
```

#### Interactive Mode
```bash
# Launch interactive interface for guided troubleshooting
python main.py

# Navigate to: Configuration Management → Validate current locale configuration
# Navigate to: Configuration Management → Voice ID Management
# Navigate to: Help & Information → Troubleshooting Tips
```

The interactive mode provides built-in troubleshooting with:
- Real-time configuration validation
- Voice ID health checking and management
- Automatic voice suggestions and addition
- Output directory status checking
- Step-by-step guidance for common issues
- Integrated help system with examples

## License

This project is for research purposes only. Generated conversations are synthetic and should not be used for malicious purposes. 