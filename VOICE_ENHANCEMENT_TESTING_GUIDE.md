# Voice Enhancement Testing Guide

## Overview

This guide provides step-by-step instructions for testing the enhanced TTS features that improve audio quality using ElevenLabs v3 and advanced configuration options.

## Features Implemented

### ✅ **ElevenLabs v3 Model Support**
- **eleven_multilingual_v3** model with enhanced expressiveness
- Audio tags for emotional context ([excited], [whispers], [urgent], etc.)
- Improved pronunciation and intonation

### ✅ **Configurable Voice Settings**
- Stability (0.0-1.0): Controls voice consistency
- Similarity Boost (0.0-1.0): Voice cloning fidelity
- Style (0.0-1.0): Emotional variation (v3 only)
- Speaker Boost: Enhanced speaker clarity

### ✅ **High-Quality Audio Options**
- PCM 44.1kHz uncompressed audio
- Configurable output formats
- Optimized streaming latency settings

### ✅ **Audio Tags System**
- Context-aware emotional tagging
- Conversation-type specific emotions (scam vs. legit)
- Position-aware tags (opening, middle, closing)

## Testing Steps

### 1. **Basic Setup and Package Update**

First, ensure you have the latest ElevenLabs package:

```bash
# Navigate to project directory
cd /home/kidus/projects/scam.ai/voice_scam_dataset_gen

# Activate virtual environment (using uv as preferred)
uv venv
source .venv/bin/activate

# Update packages
uv pip install elevenlabs>=1.0.0
```

### 2. **Test Voice Quality Management (Interactive Mode)**

Launch the interactive menu to explore the new features:

```bash
python main.py
```

Navigate through the menu:
1. Select **"Configuration Management"** (option 4)
2. Select **"Voice Quality & V3 Features"** (option 7)

#### Test Options:

**Option 1: Enable V3 with Audio Tags**
- This enables the most advanced features
- Audio will include emotional context and conversational flow
- Best for production-quality datasets

**Option 4: Enable High-Quality Audio**
- Enables PCM uncompressed audio
- Larger file sizes but maximum quality
- Recommended for final datasets

**Option 6: Configure Voice Settings**
- Test different stability values (0.2 for more variation, 0.8 for consistency)
- Test similarity boost (0.5-0.8 recommended)
- Test style values (v3 only, 0.2-0.6 for natural variation)

### 3. **Test with Small Sample (Recommended First Test)**

Run a small test to verify everything works:

```bash
# Test with Saudi Arabia locale and limited samples
python main.py --locale ar-sa --sample-limit 3 --steps tts
```

This will:
- Use only 3 conversations for testing
- Skip other pipeline steps
- Focus on audio generation with new features

### 4. **Compare Audio Quality**

#### **Baseline Test (V2 Model)**
```bash
# First, disable V3 features to create baseline
python main.py
# Navigate to: Configuration → Voice Quality → Option 3 (Disable V3)

# Generate baseline audio
python main.py --locale ar-sa --sample-limit 5 --steps tts --force
```

#### **Enhanced Test (V3 Model with Audio Tags)**
```bash
# Enable V3 features with audio tags
python main.py
# Navigate to: Configuration → Voice Quality → Option 1 (Enable V3 with tags)

# Generate enhanced audio
python main.py --locale ar-sa --sample-limit 5 --steps tts --force
```

#### **High-Quality Test**
```bash
# Enable high-quality audio
python main.py
# Navigate to: Configuration → Voice Quality → Option 4 (Enable High-Quality)

# Generate high-quality audio
python main.py --locale ar-sa --sample-limit 5 --steps tts --force
```

### 5. **Test Different Locales**

Test with different languages to ensure compatibility:

```bash
# Test with Malay
python main.py --locale ms-my --sample-limit 3 --steps tts

# Test with another Arabic region
python main.py --locale ar-ae --sample-limit 3 --steps tts
```

### 6. **Full Pipeline Test**

Once individual features are verified, test the full pipeline:

```bash
# Full pipeline with enhanced features
python main.py --locale ar-sa --sample-limit 10
```

## Expected Results

### **Audio Quality Improvements**

1. **V3 Model Benefits:**
   - More natural speech patterns
   - Better emotional expression
   - Improved pronunciation of names and technical terms
   - More conversational flow

2. **Audio Tags Benefits:**
   - Scam conversations sound more urgent/pressing
   - Legitimate conversations sound more friendly/helpful
   - Context-appropriate emotional responses
   - More realistic conversational dynamics

3. **High-Quality Audio:**
   - Larger file sizes (WAV vs MP3)
   - Uncompressed audio for maximum fidelity
   - Better suited for professional applications

### **File Structure Changes**

With enhanced features enabled, you'll see:

```
output/ar-sa/audio/scam/conversation_001/
├── turn_01_caller.wav          # High-quality format (if enabled)
├── turn_02_callee.wav
├── conversation_001_combined.wav
└── metadata.json               # Enhanced metadata with model info
```

Enhanced metadata includes:
- Model used (v3 vs v2)
- V3 features enabled status
- Audio tags used per turn
- Voice settings applied

## Configuration Options

### **Via Interactive CLI:**
1. `python main.py` → Configuration → Voice Quality
2. Enable/disable features as needed
3. Configure individual voice parameters

### **Via Direct Configuration Editing:**

Edit `configs/common.json`:

```json
{
  "voice_generation": {
    "model_v3_enabled": true,
    "voice_settings": {
      "stability": 0.6,
      "similarity_boost": 0.7,
      "style": 0.3,
      "speaker_boost": true
    },
    "quality_settings": {
      "use_high_quality": true,
      "high_quality_format": "pcm_44100"
    },
    "v3_features": {
      "use_audio_tags": true,
      "emotional_context": true,
      "conversation_context": true
    }
  }
}
```

## Troubleshooting

### **Common Issues:**

1. **Import Error for ElevenLabs:**
   ```bash
   uv pip install --upgrade elevenlabs>=1.0.0
   ```

2. **V3 Model Not Found:**
   - Ensure your ElevenLabs API key has v3 access
   - V3 is currently in alpha - contact ElevenLabs for access

3. **Large File Sizes:**
   - Expected with high-quality audio
   - Disable high-quality mode for testing: Option 5 in Voice Quality menu

4. **Voice ID Errors:**
   ```bash
   python main.py --validate-all-voices
   ```

### **Performance Considerations:**

- **V3 Model:** Slightly higher latency than v2
- **Audio Tags:** Minimal performance impact
- **High-Quality Audio:** ~5x larger file sizes
- **Processing Time:** V3 may be 10-20% slower than v2

## Recommended Testing Sequence

1. **Start Small:** Test with 2-3 samples first
2. **Compare Models:** Test v2 vs v3 side-by-side
3. **Test Audio Tags:** Enable/disable to hear difference
4. **Test Quality Settings:** Compare MP3 vs PCM
5. **Test Different Languages:** Ensure compatibility
6. **Full Production Run:** Use settings that work best

## Production Recommendations

**For Best Quality:**
- Enable V3 model with audio tags
- Use stability: 0.6, similarity_boost: 0.7, style: 0.3
- Enable high-quality audio for final output
- Use speaker boost for clarity

**For Balanced Performance:**
- Enable V3 model without audio tags
- Use default voice settings (stability: 0.5, similarity_boost: 0.5)
- Standard MP3 output
- Enable speaker boost

**For Maximum Compatibility:**
- Use V2 model (disable V3)
- Standard voice settings
- Standard MP3 output

The enhancements are backward compatible - existing configurations will continue to work with improved default settings.