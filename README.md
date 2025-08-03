# Scam Conversation Generation Pipeline

This pipeline generates realistic scam phone conversations with audio synthesis. The process involves translating Chinese scam texts to English, generating follow-up dialogue turns, translating to target languages, and finally creating audio files.


## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file with your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
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
python main.py --locale ms-my --steps preprocess translate

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

## Pipeline Overview

The pipeline consists of five main steps:

1. **Preprocessing**: Extract placeholder tags from Chinese source text
2. **Translation**: Translate Chinese to English (intermediate language)  
3. **Conversation Generation**: Generate multi-turn scam dialogues and legitimate conversations using LLM
4. **Text-to-Speech**: Convert conversations to audio using ElevenLabs
5. **Post-processing**: Format JSON files and package audio

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
│   │   ├── google_translator.py
│   │   ├── argos_translator.py
│   │   └── language_codes.py         # Language code mappings
│   ├── conversation/               # LLM dialogue generation
│   │   ├── scam_generator.py         # Scam conversation generation
│   │   └── legit_generator.py        # Legitimate conversation generation
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

Adding support for a new region is straightforward:

### 1. Create Locale Directory
```bash
mkdir -p configs/localizations/ar-eg  # Arabic - Egypt example
```

### 2. Create Configuration File (`config.json`)
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
    "ids": ["voice_id_1", "voice_id_2"],
    "names": ["Voice1", "Voice2"]
  },
  "conversation": {
    "legit_categories": ["family_checkin", "bank_verification_call", ...]
  },
  "output": {
    "scam_conversation": "scam_conversation.json",
    "legit_conversation": "legit_conversation.json",
    "scam_audio_dir": "scam",
    "legit_audio_dir": "legit",
    "scam_formatted": "scam_conversation_formatted.json",
    "legit_formatted": "legit_conversation_formatted.json"
  }
}
```

### 3. Create Placeholder Mappings (`placeholders.json`)
```json
{
  "{00001}": {
    "tag": "<person_name>",
    "substitutions": ["أحمد", "فاطمة", "محمد"],
    "translations": ["Ahmed", "Fatima", "Mohammed"]
  },
  "{00002}": {
    "tag": "<city_name>",
    "substitutions": ["القاهرة", "الإسكندرية", "الجيزة"],
    "translations": ["Cairo", "Alexandria", "Giza"]
  },
  "{00003}": {
    "tag": "<money_amount_medium>",
    "substitutions": ["١٠٠٠ جنيه", "٢٠٠٠ جنيه", "٣٠٠٠ جنيه"],
    "translations": ["1000 EGP", "2000 EGP", "3000 EGP"]
  }
}
```

### 4. Run the Pipeline
```bash
python main.py --locale ar-eg
```

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
- **ar-sa**: Arabic (Saudi Arabia) - SAR currency, Saudi entities
- **ar-ae**: Arabic (United Arab Emirates) - AED currency, UAE entities  
- **ms-my**: Malay (Malaysia) - MYR currency, Malaysian entities

## API Requirements

- **OpenAI API**: For LLM conversation generation
- **ElevenLabs API**: For text-to-speech synthesis
- **Google Translate**: Default translation service (Argos Translate also supported)

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
2. **Locale Config Not Found**: Check locale ID format (e.g., ar-sa, not arabic-sa)
3. **Audio Generation Fails**: Verify ElevenLabs quota and voice IDs
4. **Translation Errors**: Check internet connection and Google Translate API limits
5. **Missing Placeholder Mappings**: Check warnings in preprocessing step
6. **Voice Synthesis Quota**: ElevenLabs has monthly character limits

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

# Show pipeline steps
python main.py --show-steps
```

#### Interactive Mode
```bash
# Launch interactive interface for guided troubleshooting
python main.py

# Navigate to: Configuration Management → Validate current locale configuration
# Navigate to: Help & Information → Troubleshooting Tips
```

The interactive mode provides built-in troubleshooting with:
- Real-time configuration validation
- Output directory status checking
- Step-by-step guidance for common issues
- Integrated help system with examples

## License

This project is for research purposes only. Generated conversations are synthetic and should not be used for malicious purposes. 