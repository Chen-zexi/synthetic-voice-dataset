# Scam Conversation Generation Pipeline

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

The project includes a unified LLM abstraction layer (`src/llm_core/`) that supports multiple providers:

### Supported LLM Providers
- **OpenAI**: GPT-5 models
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
    "model": "gpt-4o-mini",
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

### Interactive Voice Management

Launch interactive mode for guided voice management:

```bash
python main.py
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