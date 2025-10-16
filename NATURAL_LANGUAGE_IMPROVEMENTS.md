# Natural Language Improvements for Malaysian Conversations

## Date: 2025-10-16

## Problem Identified

Generated Malay conversations (both scam and legit) sounded too formal and AI-generated:
- Overuse of formal words: "sila", "terima kasih", "adakah", "selamat pagi"
- Too structured and polite
- Missing natural speech patterns and colloquialisms
- No use of Malay particles: lah, kan, je, etc.
- Overly complete sentences without natural breaks
- No code-switching (common in Malaysian speech)

## Solutions Implemented

### 1. Model Upgrade

**File:** `configs/common.json`

**Changes:**
- Model: `gpt-5-nano` → `gpt-5` (full model for better quality)
- Reasoning Effort: `minimal` → `medium` (better language understanding)
- Temperature: `1.0` → `1.1` (more natural variation)
- Frequency Penalty: `0.0` → `0.3` (reduce repetitive phrases)

**Why:**
- GPT-5 full model has much better multilingual capabilities, especially for Malay
- Medium reasoning effort allows model to think more about naturalness
- Higher temperature and frequency penalty reduce robotic patterns

### 2. Natural Speech Pattern Instructions

**Files Modified:**
- `src/conversation/scam_generator.py`
- `src/conversation/legit_generator.py`

**Added Section: "Natural Speech Patterns (Language-Specific)"**

For Malay (ms-my):
- Colloquial particles to use: "lah", "kan", "je", "pun", "ni", "tu"
- Pronouns: Mix "awak/anda" (you), "saya/aku" (I)
- Natural fillers: "eh", "ah", "hmm", "macam", "betul ke", "okay"
- Contractions: "nak" (hendak), "dah" (sudah), "tak" (tidak)
- Code-switching with English is natural
- Avoid overusing: "sila", "terima kasih", "adakah"
- Use incomplete sentences and natural breaks

### 3. Concrete Examples in User Prompts

**Added "CRITICAL FOR MALAY" Examples:**

**Scam Generator:**
```
BAD: "Selamat pagi. Sila sahkan nombor akaun anda."
GOOD: "Hai, boleh tolong sahkan nombor akaun awak sekejap?"

BAD: "Terima kasih kerana memberi maklumat tersebut."
GOOD: "Ok, terima kasih ye. Lepas ni..."

BAD: "Adakah anda bersedia untuk meneruskan?"
GOOD: "Awak okay nak proceed ke?"
```

**Legit Generator:**
```
BAD: "Selamat pagi. Saya dari syarikat. Adakah anda bersedia?"
GOOD: "Hai, saya dari syarikat. Awak ada masa sekejap tak?"

BAD: "Terima kasih kerana menunggu. Sila berikan maklumat."
GOOD: "Thanks sebab tunggu. Boleh bagi details sikit?"

BAD: "Baiklah, saya akan memproses permintaan anda."
GOOD: "Ok, nanti saya process ye."
```

### 4. Guidance for Other Languages

Also added placeholders for natural speech in:
- Arabic (ar-sa, ar-ae): Dialectal mixed with MSA
- Other languages: General guidance to use spoken forms

## Testing

### New Test Script
`test_natural_malay_conversations.sh`

Generates 5 scam + 5 legit conversations with improved settings.

### Quality Checklist

When reviewing outputs, check for:
- ✓ Turn counts (20-24)
- ✓ Natural Malay particles: lah, kan, je, tak, dah, nak
- ✓ Casual greetings: Hai, Eh (not always "Selamat pagi")
- ✓ Code-switching with English words
- ✓ Incomplete sentences and natural pauses
- ✓ Less formal pronouns: awak > anda, mix of saya/aku
- ✓ Reduced usage of: sila, terima kasih, adakah
- ✓ Natural fillers: hmm, eh, macam, betul ke
- ✓ Mix of short and long sentences
- ✓ Natural conversation flow

## Expected Improvements

**Before (Formal):**
```
Caller: "Selamat pagi. Saya dari pasukan keselamatan bank. Sila sahkan identiti anda."
Callee: "Selamat pagi. Baiklah, apakah maklumat yang diperlukan?"
Caller: "Terima kasih kerana bekerjasama. Sila berikan nombor akaun anda."
```

**After (Natural):**
```
Caller: "Hai, saya dari security team bank. Boleh verify identity awak sekejap?"
Callee: "Eh, ok je. Nak info apa ni?"
Caller: "Thanks ye. Boleh bagi nombor akaun awak?"
```

## Cost & Performance Impact

**Estimated Cost Increase:**
- GPT-5 vs GPT-5-nano: ~3-4x higher per token
- Low/Medium vs Minimal reasoning: ~1.5-2x higher
- **Total:** ~5-6x cost increase per conversation

**Generation Time:**
- Old (GPT-5-nano, minimal reasoning, 7-10 turns): ~5-10 seconds/conversation
- New (GPT-5, low reasoning, 20-24 turns): **~45-75 seconds/conversation**
- New (GPT-5, medium reasoning, 20-24 turns): **~90-120 seconds/conversation**

**Expected Times for Test Scripts:**
- `quick_test_malay.sh` (2+2 conversations, low reasoning): **~3-5 minutes**
- `test_natural_malay_conversations.sh` (5+5 conversations, low reasoning): **~7-12 minutes**
- Full batch (100 conversations, low reasoning): **~90-120 minutes**

**Why It's Slower:**
1. GPT-5 full model thinks more deeply than nano (~3-5x slower)
2. Reasoning effort adds "thinking time" before generating
3. 20-24 turns = 3x more content to generate
4. More complex prompts with colloquial instructions

**Justification:**
- Significantly better quality for Malay conversations
- More human-sounding, less detectable as AI
- Better training data for scam detection models
- Acceptable trade-off for quality improvement

**If Stuck/Slow:**
- Check terminal for progress bar updates
- Each conversation can take 1-2 minutes - this is normal
- If stuck on one conversation for >3 minutes, may indicate API rate limiting
- Use `quick_test_malay.sh` for faster validation (2+2 conversations)

## Usage

### Generate Natural Conversations
```bash
# Use the new test script
./test_natural_malay_conversations.sh

# Or use main.py directly (automatically uses new settings)
python main.py --locale ms-my --scam-limit 10 --legit-limit 10
```

### Revert to Old Settings (If Needed)
```bash
# Edit configs/common.json
# Change:
#   "model": "gpt-5" → "gpt-5-nano"
#   "reasoning_effort": "medium" → "minimal"
#   "temperature": 1.1 → 1.0
#   "frequency_penalty": 0.3 → 0.0
```

## Next Steps

1. **Test the improvements:**
   ```bash
   ./test_natural_malay_conversations.sh
   ```

2. **Review outputs manually:**
   - Check for natural Malay particles
   - Verify code-switching is appropriate
   - Ensure conversations flow naturally

3. **Compare with previous formal output:**
   - Side-by-side comparison of old vs new
   - Validate improvement in naturalness

4. **Expand to other locales:**
   - Once satisfied with Malay, test with Arabic
   - Add language-specific patterns for other locales

5. **Fine-tune if needed:**
   - Adjust temperature if too chaotic
   - Modify examples if patterns not followed
   - Consider adding more specific Malay examples

## Files Modified

1. `configs/common.json` - Model and parameter upgrades
2. `src/conversation/scam_generator.py` - Natural speech patterns + examples
3. `src/conversation/legit_generator.py` - Natural speech patterns + examples
4. `test_natural_malay_conversations.sh` (new) - Testing script

## Validation Criteria

A good natural Malay conversation should:
- Sound like real Malaysians talking on the phone
- Mix formal and informal appropriately based on context
- Include natural particles without overdoing it
- Have code-switching that feels organic
- Show personality through speech patterns
- Include thinking pauses and incomplete thoughts
- Avoid sounding like a textbook or formal letter

