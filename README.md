# Scam Conversation Generation Pipeline

This pipeline generates realistic scam phone conversations with audio synthesis. The process involves translating Chinese scam texts to English, generating follow-up dialogue turns, translating to target languages, and finally creating audio files.


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
# Available steps: preprocess, translate, conversation, legit, translate_final, tts, postprocess
python main.py --locale ms-my --steps preprocess translate

# Run all conversation-related steps with sample limit (using uv)
uv run main.py --locale ms-my --steps preprocess translate conversation legit translate_final --sample-limit 1 --force

# Run complete pipeline with all steps
python main.py --locale ms-my --steps preprocess translate conversation legit translate_final tts postprocess

# List available locales
python main.py --list-locales

# Backward compatibility with old language parameter
python main.py --language arabic  # Maps to ar-sa

# Validate configuration
python main.py --validate-config arabic

# Show available pipeline steps
python main.py --show-steps

# Test with limited samples
python main.py --locale ar-sa --sample-limit 10

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

The pipeline consists of seven main steps:

1. **preprocess**: Extract placeholder tags from Chinese source text
2. **translate**: Translate Chinese to English (intermediate language)  
3. **conversation**: Generate multi-turn scam dialogues using LLM
4. **legit**: Generate legitimate (non-scam) conversations using LLM
5. **translate_final**: Translate English conversations to target language
6. **tts**: Convert conversations to audio using ElevenLabs
7. **postprocess**: Format JSON files and package audio

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

## Adding a New Locale

Adding support for a new region is straightforward. For comprehensive instructions, see the [Locale Implementation Guide](LOCALE_IMPLEMENTATION_GUIDE.md) and check the [Locale Roadmap](locale_road_map.md) for current status.

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

The project includes a unified LLM abstraction layer (`src/llm_core/`) that supports multiple providers:

### Supported LLM Providers
- **OpenAI**: GPT-4, GPT-3.5-turbo (default: gpt-4.1-mini)
- **Anthropic**: Claude models
- **Google**: Gemini models
- **LM-Studio**: Local model hosting
- **vLLM**: High-performance inference server

### LLM Configuration

Configure LLM parameters in `configs/common.json`:
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "max_concurrent_requests": 10,
    "temperature": 1.0,
    "max_tokens": null,
    "top_p": 0.95,
    "n": 1
  }
}
```

### Features
- **Async-only architecture**: All LLM calls are asynchronous for better performance
- **Structured output**: Uses LangChain's `with_structured_output` with Pydantic schemas
- **JSON fallback**: Robust parsing with multiple fallback patterns
- **Rate limiting**: Semaphore-based concurrent request management
- **Provider abstraction**: Easy switching between different LLM providers

### Environment Variables
```env
# OpenAI (default)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: other providers
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
HOST_IP=192.168.1.100  # For LM-Studio/vLLM
```

## API Requirements

- **OpenAI API**: For LLM conversation generation (default provider)
- **ElevenLabs API**: For text-to-speech synthesis
- **Translation Services**: Google Translate (default), Argos Translate (offline), Qwen-MT (Alibaba Cloud)
- **Optional**: Anthropic/Gemini APIs for alternative LLM providers

## Voice ID Validation System

The pipeline includes comprehensive voice ID validation to ensure audio generation reliability across all locales.

### Features

- **Real-time validation**: Verify voice IDs against ElevenLabs API
- **Bulk validation**: Check all voice IDs across all locales simultaneously
- **Automatic cleanup**: Remove invalid voice IDs from configuration files
- **Voice suggestions**: Get compatible voice recommendations for specific locales
- **Minimum requirements**: Ensure each locale has ≥2 voices for redundancy
- **Interactive management**: GUI-based voice management through interactive mode

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

## Performance Considerations

- Use `--steps` to run specific pipeline stages for faster iteration
- Use `--sample-limit N` for testing with smaller datasets
- Audio generation is rate-limited to avoid API throttling
- Large datasets should be processed in batches
- Consider running overnight for full datasets
- Monitor API quotas for OpenAI and ElevenLabs

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