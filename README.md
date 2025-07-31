# Scam Conversation Generation Pipeline

This pipeline generates realistic scam phone conversations with audio synthesis. The process involves translating Chinese scam texts to English, generating follow-up dialogue turns, translating to target languages, and finally creating audio files.

## Pipeline Sequence

The scripts should be run in the following order:

### 1. Translate (Chinese to English)
**Script**: `translate.py`
- Translates Chinese scam texts to English using Argos Translate
- Input: `scamGen_combined_first_20k.txt` (Chinese texts)
- Output: `translation.txt` (English translations)

### 2. Generate Follow-up Turns
**Script**: `followup_turns.py`
- Uses OpenAI GPT to generate realistic conversation dialogues
- Creates multi-turn conversations with different victim awareness levels
- Input: `translation.txt` (English texts)
- Output: `generated_conversations.json` (Structured conversation data)

### 3. Translate (English to Target Language)
**Script**: `translate_target.py` (to be created)
- Translates English conversations to target languages
- Supports multiple target languages (Spanish, French, German, etc.)
- Input: `generated_conversations.json` (English conversations)
- Output: `translated_conversations.json` (Multi-language conversations)

### 4. Text to Voice
**Script**: `text_to_voice.py`
- Generates audio files using ElevenLabs Text-to-Speech API
- Uses different voices for caller and callee
- Input: `translated_conversations.json` (Multi-language conversations)
- Output: `audio_conversations/` (Audio files and metadata)

## Setup Requirements

### Prerequisites
```bash
pip install argostranslate python-dotenv openai elevenlabs tqdm numpy
```

### Environment Variables
Create a `.env` file in the project directory:
```env
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

## Usage Instructions

### Step 1: Translate Chinese to English
```bash
python translate.py
```
- Reads from `scamGen_combined_first_20k.txt`
- Translates first 1000 lines (configurable)
- Saves English translations to `translation.txt`

### Step 2: Generate Follow-up Conversations
```bash
python followup_turns.py
```
- Reads from `translation.txt`
- Generates 10 conversations (configurable)
- Creates realistic multi-turn dialogues
- Saves to `generated_conversations.json`

### Step 3: Translate to Target Languages
```bash
python translate_target.py
```
- Reads from `generated_conversations.json`
- Translates to multiple target languages
- Saves to `translated_conversations.json`

### Step 4: Generate Audio Files
```bash
python text_to_voice.py
```
- Reads from `translated_conversations.json`
- Generates audio files for each conversation turn
- Uses different voices for caller and callee
- Saves to `audio_conversations/` directory

## Output Structure

### Conversation JSON Format
```json
{
  "conversation_id": 1,
  "first_turn": "Hello Ms. Zhang...",
  "num_turns": 5,
  "victim_awareness": "not",
  "dialogue": [
    {
      "sent_id": 1,
      "text": "Hello Ms. Zhang...",
      "role": "caller"
    },
    {
      "sent_id": 2,
      "text": "Who is this?",
      "role": "callee"
    }
  ]
}
```

## Configuration Options

### Translation Settings
- **Source Language**: Chinese (zh)
- **Target Languages**: English, Spanish, French, German, etc.
- **Translation Engine**: Argos Translate (offline)

### Conversation Generation
- **Model**: OpenAI GPT-3.5-turbo
- **Temperature**: 0.9 (creative responses)
- **Victim Awareness**: Random selection (not, tiny, very)
- **Turn Count**: Random (2-10 turns)

### Audio Generation
- **Voice Selection**: 15 different ElevenLabs voices
- **Model**: eleven_multilingual_v2
- **Format**: MP3 44.1kHz 128kbps
- **Rate Limiting**: 0.5s delay between requests

## Error Handling

- **Translation Errors**: Marked as `[Translation Error]` or `[Translation Timeout]`
- **API Failures**: Graceful handling with retry logic
- **File I/O**: Proper error handling for missing files
- **Rate Limiting**: Automatic delays to respect API limits

## Troubleshooting

### Common Issues
1. **Missing API Keys**: Ensure `.env` file is properly configured
2. **Translation Failures**: Check internet connection for Argos package download
3. **Audio Generation Errors**: Verify ElevenLabs API key and quota
4. **File Not Found**: Ensure input files exist in correct locations

### Performance Tips
- Use smaller batch sizes for testing
- Monitor API usage and quotas
- Consider running overnight for large datasets
- Use SSD storage for faster file I/O

## Data Privacy

- All translations happen locally using Argos Translate
- OpenAI API calls are made for conversation generation
- ElevenLabs API calls are made for audio synthesis
- No personal data is stored or transmitted beyond API calls

## License

This project is for research purposes only. Generated conversations are synthetic and should not be used for malicious purposes. 