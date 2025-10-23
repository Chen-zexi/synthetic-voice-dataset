"""
Legitimate conversation generator using LLM core with LangChain.
"""

import json
import random
import logging
import asyncio
from typing import List, Dict, Optional
from tqdm import tqdm

from src.config.config_loader import Config
from src.llm_core.api_provider import LLM
from src.llm_core.api_call import make_api_call
from src.llm_core.token_counter import TokenUsageTracker
from src.conversation.schemas import LegitConversationResponse
from src.utils.logging_utils import ConditionalLogger


logger = logging.getLogger(__name__)


class LegitGenerator:
    """
    Generates legitimate (non-scam) conversations using OpenAI GPT-4.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the legitimate conversation generator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.clogger = ConditionalLogger(__name__, config.verbose)
        # Initialize LLM with configurable provider (default to OpenAI)
        self.llm_provider = getattr(config, 'llm_provider', 'openai')
        self.llm_model = getattr(config, 'llm_model', 'gpt-4.1-mini')
        
        # Check for Response API and token tracking settings
        # Default to True for OpenAI models
        use_response_api = getattr(config, 'llm_use_response_api', self.llm_provider == 'openai')
        track_tokens = getattr(config, 'llm_track_tokens', False)
        
        # Initialize token tracker if enabled
        self.token_tracker = TokenUsageTracker(verbose=False) if track_tokens else None
        
        # Collect all LLM parameters from config
        llm_params = {}
        for attr_name in dir(config):
            if attr_name.startswith('llm_') and not attr_name.startswith('llm_provider') and not attr_name.startswith('llm_model') and not attr_name.startswith('llm_use_') and not attr_name.startswith('llm_track_'):
                value = getattr(config, attr_name)
                if value is not None:
                    llm_params[attr_name] = value
        
        # Create LLM instance with all parameters
        llm_instance = LLM(
            provider=self.llm_provider, 
            model=self.llm_model,
            use_response_api=use_response_api,
            **llm_params
        )
        self.llm = llm_instance.get_llm()
        
        # Pre-compute locale-static prompt section for optimal caching
        self.locale_static_prompt = self._build_locale_static_prompt()
        self.clogger.debug(f"Pre-computed locale-static prompt for {config.legit_call_language} ({config.legit_call_region})")
    
    async def generate_conversations(self) -> List[Dict]:
        """
        Generate legitimate conversations asynchronously for faster processing.
        
        Returns:
            List of conversation dictionaries
        """
        # Use legit_sample_limit if set, otherwise fall back to total_limit
        num_conversations = self.config.legit_sample_limit if self.config.legit_sample_limit is not None else self.config.total_limit
        self.clogger.debug(f"Generating {num_conversations} legitimate conversations")
        
        # Prepare tasks
        tasks = []
        for idx in range(num_conversations):
            # Randomly select parameters
            num_turns = random.randint(
                self.config.num_turns_lower_limit,
                self.config.num_turns_upper_limit
            )
            category = random.choice(self.config.legit_call_categories)
            
            task = self._generate_single_conversation(
                idx + 1, num_turns, category
            )
            tasks.append(task)
        
        # Run tasks concurrently with progress bar
        max_concurrent = getattr(self.config, 'max_concurrent_requests', 10)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_task(task_func):
            async with semaphore:
                return await task_func
        
        # Progress bar for async operations
        pbar = tqdm(total=len(tasks), desc="Generating legitimate conversations")
        
        async def run_with_progress(task_func):
            result = await limited_task(task_func)
            pbar.update(1)
            return result
        
        # Run all tasks concurrently
        results = await asyncio.gather(
            *[run_with_progress(task) for task in tasks],
            return_exceptions=True
        )
        
        pbar.close()
        
        # Collect successful results
        all_conversations = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                self.clogger.error(f"Task {idx} failed: {result}")
            elif result:
                all_conversations.append(result)
        
        # Save conversations
        self._save_conversations(all_conversations)
        
        # Add small delay to allow async cleanup
        await asyncio.sleep(0.1)
        
        self.clogger.info(f"Generated {len(all_conversations)} legitimate conversations")
        return all_conversations
    
    async def _generate_single_conversation(self, conversation_id: int, num_turns: int,
                                          category: str) -> Optional[Dict]:
        """
        Generate a single legitimate conversation asynchronously.
        
        Args:
            conversation_id: Unique conversation ID
            num_turns: Number of dialogue turns
            category: Conversation category
            
        Returns:
            Conversation dictionary or None if generation failed
        """
        dialogue = await self._generate_dialogue(conversation_id, num_turns, category)
        
        if dialogue:
            # Check if dialogue is a dict with dialogue field
            if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                conversation = {
                    "conversation_id": conversation_id,
                    "region": self.config.legit_call_region,
                    "category": category,
                    "num_turns": num_turns,
                    "dialogue": dialogue['dialogue']
                }
            else:
                # Legacy format - just dialogue list
                conversation = {
                    "conversation_id": conversation_id,
                    "region": self.config.legit_call_region,
                    "category": category,
                    "num_turns": num_turns,
                    "dialogue": dialogue
                }
            
            return conversation
        
        return None
    
    async def _generate_dialogue(self, conversation_id: int, num_turns: int, category: str) -> Optional[List[Dict]]:
        """
        Generate dialogue turns asynchronously using LLM.
        
        Args:
            conversation_id: Unique conversation ID
            num_turns: Number of turns to generate
            category: Conversation category
            
        Returns:
            List of dialogue turns or None if generation failed
        """
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(num_turns, category)
        
        try:
            # Check if we should track tokens
            if self.token_tracker:
                response, token_info = await make_api_call(
                    llm=self.llm,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=LegitConversationResponse,
                    return_token_usage=True
                )
                # Track the token usage
                self.token_tracker.add_usage(
                    token_info,
                    self.llm_model,
                    f"legit_conversation_{conversation_id}"
                )
            else:
                response = await make_api_call(
                    llm=self.llm,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=LegitConversationResponse
                )
            
            # Convert Pydantic models to dicts and add sent_id
            if hasattr(response, 'dialogue'):
                # Add sent_id to each turn
                dialogue_with_ids = []
                for i, turn in enumerate(response.dialogue, 1):
                    turn_dict = turn.model_dump()
                    turn_dict['sent_id'] = i  # Add sequential ID
                    dialogue_with_ids.append(turn_dict)
                
                result = {'dialogue': dialogue_with_ids}
                
                return result
            else:
                self.clogger.error("Response missing dialogue field")
                return None
            
        except Exception as e:
            self.clogger.error(f"LLM API error: {e}")
            return None
    
    def _build_locale_static_prompt(self) -> str:
        """
        Pre-compute the locale-specific static prompt section.
        This section remains identical for all conversations in a batch for the same locale.
        Optimized for OpenAI prompt caching to maximize cache hits in production.
        
        Returns:
            Formatted locale-specific prompt section
        """
        # Start with language requirements
        locale_prompt = f"""
### Locale Configuration

#### Language Requirements
Generate the conversation in {self.config.legit_call_language} as spoken in {self.config.legit_call_region}.
Use natural, colloquial expressions appropriate for the region.
Ensure cultural appropriateness for {self.config.legit_call_region}.
"""
        
        # Add locale-specific natural speech patterns
        locale_id = getattr(self.config, 'locale', getattr(self.config, 'language', '')).lower()
        
        if locale_id == 'ms-my':
            locale_prompt += """
#### Natural Speech Patterns (Malay - Malaysia)

**CRITICAL: Balance Natural vs Formal**
- Natural speech has minor imperfections, NOT broken grammar
- Particles enhance meaning; they don't replace proper grammar
- Maintain grammatical foundation while adding conversational elements
- Test: Would a native Malaysian speaker actually say this phrase?

**Colloquial Particles (Use strategically, NOT excessively):**
- "lah" (emphasis, softening): "Tak boleh lah", "Saya faham lah"
  - DON'T overuse - typically 1-2 times per speaker's turn
- "kan" (confirmation seeking): "Betul kan?", "Awak tahu kan?"
- "je" (only, just): "Sikit je", "Tunggu sekejap je"
- "pun" (also, even): "Saya pun tak tahu", "Itu pun boleh"
- "ni/tu" (this/that): "Orang ni", "Macam tu lah"
- MUST appear at END of phrases, NOT mid-sentence
- Balance: Use particles to add flavor, not in every sentence

**Natural Disfluencies and Fillers (Use moderately for realism):**
- Thinking pauses: "errr", "emmm", "hmm", "aaa"
- Time-buying: "tunggu sekejap ya", "kejap", "kejap ya", "jap"
- Surprise/reaction: "eh", "ah", "wah", "alamak"
- Processing: "macam mana ya", "apa eh", "camne ni"
- Hesitations: "ha okay", "ok jap", "on lah"
- Use 1-3 fillers per turn, not every sentence

**Incomplete Sentences and Conversational Shortcuts:**
- Trail off naturally: "Kalau macam tu...", "Tapi saya rasa...", "Jadi maksudnya..."
- Quick responses: "ok jap", "on lah", "boleh je", "takpe", "noted"
- Casual questions: "macam tu ke?", "betul ke?", "ye ke?"
- Service shortcuts: "ok set", "dah settle", "ha ngam"
- Keep core meaning clear even with shortcuts

**Professional Casualness (Malaysian workplace norm):**
- Professional calls blend formality with friendliness
- Use "awak/saya" rather than "anda" in most business contexts
- Small talk is natural: "Hari ni panas kan?", "Traffic ok ke tadi?"
- Casual confirmations even in formal settings: "ok noted", "sure boleh"

**Formality Matching by Context (Speaker Education/Role):**
- Clinic/hospital staff: Moderately formal but friendly, clear grammar
- Bank/government: More formal language, occasional particles for warmth
- Education: Professional yet approachable, grammatically correct
- Service industry: Casual-friendly with polite particles
- Young urban speakers: More casual with natural code-switching
- Elderly/formal educated: Less casual, fuller sentences

**Natural Word Choices (Avoid overly technical/formal where unnecessary):**
- "sila" → use "tolong" or direct request
- "adakah" → use "ke" or "ada... tak?"
- "terima kasih" → use "thanks", or "terima kasih" occasionally
- "baik" → use "ok", "okay", "boleh"
- "mengapa" → use "kenapa"
- Choose words that match the speaker's background and context

**Code-Switching (Natural for younger/urban speakers):**
- Mix English words naturally: "ok", "sure", "sorry", "appointment", "confirm", "email"
- Professional terms often in English: "meeting", "report", "deadline"
- Keep it contextual - service staff use more English
- Older/less educated speakers: less English mixing

**Grammatical Foundation (Real speech has minor imperfections, not errors):**
- Natural imperfections: Minor word order shifts, dropped optional words
- Double subjects (natural): "Saya ni, saya nak tanya..."
- Simplified questions: "Awak tahu tak?" (instead of "Adakah awak tahu?")
- Word order variations: "Boleh ke?" (natural informal)
- Mid-thought clarifications: Natural topic shifts with context maintained
- DON'T create broken grammar that confuses meaning
- DON'T force imperfections that native speakers wouldn't make

**Common Pitfalls to AVOID:**
- Overusing particles until sentences lose meaning
- Using formal words incorrectly: "mengaku" when you mean "pastikan"
- Breaking grammar to force casualness: "kemas kini terakhir" → use "kemas kini buat kali terakhir"
- Awkward constructions: "membangun kepercayaan" → use "menguatkan kepercayaan"
- Adding unnecessary words: "langkah yang pertama" → "langkah pertama"
- Mixing formality inconsistently within same speaker
"""
        # Add more locale-specific patterns here as needed for other languages
        
        # Voice selection now handled externally, not by LLM
        
        return locale_prompt
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for legitimate conversation generation.
        Optimized for OpenAI prompt caching - keep this completely static.
        """
        return f"""You are a dialogue generator for creating realistic phone conversations.

## Core Task
Generate COMPLETE structured dialogues for legitimate (non-scam) phone calls with alternating turns between caller and callee.
The conversations should be natural, contextually appropriate, culturally relevant, and reach a proper conclusion.

## Output Format Requirements
Each dialogue turn must have exactly these fields:
- text: The actual dialogue text
- role: Either "caller" or "callee"

The dialogue must be returned as a JSON array with the exact format shown in examples.

## Generation Guidelines

### Conversation Quality
1. Create natural, realistic dialogue for the given context
2. Avoid overly generic or repetitive phrasing
3. Use shorter sentences for natural phone conversation flow
4. Maintain professional tone appropriate to the scenario
5. Generate synthetic but plausible values (no real personal data)

### Natural Speech Realism
Generate conversations that sound genuinely human, not AI-polished:

1. **Balanced Naturalness**: Real speech has minor imperfections, NOT broken grammar
   - Grammatical foundation should remain clear and understandable
   - Imperfections are subtle: minor word order shifts, dropped optional words, natural pauses
   - Test each phrase: Would a native speaker actually say this?

2. **Varied Response Lengths**: Mix very short reactions ("Ha", "Oh", "Okay", "Noted") with longer explanations

3. **Natural Interruptions**: Characters can ask for clarification mid-explanation, interrupt politely, or redirect conversation

4. **Emotional Authenticity**: Show appropriate emotions - friendly warmth, professional courtesy, slight hesitation when uncertain

5. **No Perfect Timing**: Include realistic delays, thinking pauses ("hmm", "errr", "kejap ya"), acknowledgments of multitasking
   - Use pauses/fillers moderately (1-3 per turn), not in every sentence

6. **Phrase Variety**: CRITICAL - Do NOT repeat identical phrases. Use synonymous expressions and varied sentence structures throughout

7. **Spontaneous Elements**: Include mid-sentence corrections, clarification questions, natural topic transitions

8. **Human Imperfections vs Errors**:
   - Natural: "Saya ni, saya nak tanya..." (double subject, natural Malay)
   - Natural: "Awak tahu tak?" (simplified question form)
   - Unnatural: Breaking sentences mid-thought without context
   - Unnatural: Using words incorrectly or forcing grammatical errors

## Important Rules
1. Always alternate between caller and callee roles
2. Start with the caller role
3. Generate conversations with {self.config.num_turns_lower_limit}-{self.config.num_turns_upper_limit} turns (±2 turns allowed for natural flow)
4. Keep the conversation relevant to the specified category
5. Maintain scenario consistency throughout the conversation
6. IMPORTANT: The conversation MUST reach a clear conclusion
7. Include proper greeting, main discussion, and polite closure
8. Show natural progression from opening to resolution

## Formality Consistency Rules
1. **Match Context**: Clinic/hospital = moderately formal but friendly, Bank/government = more formal, Service industry = casual-friendly, Friend referrals = very casual
2. **Professional Casualness**: Malaysian professional calls naturally blend formality with friendliness
3. **No Sudden Switches**: Avoid formal→casual→formal jumps within the same character's dialogue
4. **Maintain Character Voice**: Service providers maintain consistent professional tone, customers maintain their natural style
5. **Context-Appropriate Language**: Match vocabulary complexity and formality to the service type and relationship

## Conversation Progression for Extended Calls
When generating extended conversations (15+ turns):
1. **Opening (3-5 turns)**: Greetings, identity confirmation, state purpose
2. **Main Discussion (10-14 turns)**: Address the topic, exchange information, handle details
3. **Closure (3-5 turns)**: Summarize, confirm next steps, polite closing

For professional calls, include:
- Appropriate small talk or rapport building
- Detailed information exchange relevant to the category
- Natural back-and-forth with clarifications
- Professional courtesies and confirmations"""

    def _create_user_prompt(self, num_turns: int, category: str) -> str:
        """
        Create the user prompt for legitimate conversation generation.
        Optimized for OpenAI prompt caching with three-section structure:
        1. Universal static (same across all locales)
        2. Locale-static (pre-computed, same for all conversations in batch)
        3. Conversation-dynamic (unique per conversation)
        
        Args:
            num_turns: Number of turns
            category: Conversation category
            
        Returns:
            Formatted prompt
        """
        # SECTION 1: Universal Static Content (cacheable across all locales)
        prompt = """## Task: Generate Legitimate Phone Call Dialogue

### Output Format
Generate a JSON array of dialogue turns with this exact structure:
[
  {"text": "<dialogue text>", "role": "caller"},
  {"text": "<dialogue text>", "role": "callee"},
  ...
]

### Universal Dialogue Rules
1. Create a conversation between the caller and callee
2. Start with the caller role
3. Alternate between caller and callee for each turn
4. Keep sentences short and natural for phone conversations
5. Make the dialogue realistic and contextually appropriate
6. Use synthetic but plausible values (no real personal data)
7. Avoid overly generic or repetitive phrasing
8. Maintain professional tone appropriate to the scenario
"""
        
        # SECTION 2: Locale-Static Content (pre-computed, cacheable per locale batch)
        prompt += self.locale_static_prompt
        
        # SECTION 3: Conversation-Dynamic Content (unique per conversation)
        # Convert category from snake_case to human-readable
        category_display = category.replace('_', ' ').title()
        
        prompt += f"""
### This Conversation's Parameters

#### Conversation Specifics

**Category**: {category_display}
**Number of Turns**: Generate {num_turns} dialogue turns (you may adjust ±2 turns if needed for natural flow and complete resolution)
**Context**: This is a legitimate business/service call about {category_display.lower()}

#### Professional Casualness Guidelines (Malaysian Context)
Malaysian professional calls naturally blend formality with friendliness:

**Small Talk Elements (Use sparingly, context-appropriate):**
- Weather/traffic: "Hari ni panas kan?", "Traffic ok ke tadi?"
- Timing context: "Eh, tengah lunch hour ni", "Sempat lagi sebelum office hour habis"
- Rapport building: "Ok je harini?", "Macam mana weekend?"

**Service Staff Natural Speech:**
- Professional but friendly tone with particles: "Boleh je, saya check sekejap ya"
- Use fillers between system checks: "Tunggu sekejap ya...", "Hmm, saya tengok dulu"
- Acknowledging delays: "Sorry lambat sikit, sistem slow", "Kejap, line busy"
- Natural confirmations with variety: "Ok noted", "Dah record", "Ok saya dah tandakan"

**Customer Natural Speech:**
- Questions aren't perfect sentences: "Parking macam mana?", "Kena bawa apa?"
- Multitasking references: "Saya tengah drive ni", "Jap, saya sambil-sambil je"
- Natural concerns: "Takut tersalah", "Confirm ye slot tu?", "Kalau lambat sikit boleh?"
- Casual confirmations: "Ok faham", "Noted", "On lah", "Ok set"

**Context-Specific Formality:**
- Medical/clinic: Moderately formal but empathetic, use particles for warmth
- Banking/government: More formal language but still use "awak/saya", occasional particles
- Education: Professional yet approachable, balance authority with friendliness
- Service bookings: Casual-friendly, full particle use, conversational
- Customer support: Problem-solving friendly, patient, use confirmatory particles

### Generate the Dialogue

Based on the above parameters, generate a COMPLETE conversation with approximately {num_turns} dialogue turns (±2 turns allowed for natural flow) for a legitimate {category_display.lower()} phone call.

CRITICAL: The conversation MUST:
- Have a clear beginning (greeting and introduction)
- Develop the main topic thoroughly
- Reach a definitive conclusion (appointment scheduled, information provided, issue resolved, etc.)
- End with proper closure (thank you, goodbye, next steps)
- Feel natural and complete, not cut off abruptly

**Anti-Repetition Requirements (CRITICAL):**
- Use VARIED expressions for similar ideas throughout the conversation
- AVOID repeating identical phrases or sentence structures
- When expressing similar concepts, use synonyms and rephrase naturally
- Each character should have DISTINCT verbal habits, not mirror each other's exact phrases
- If a phrase was used once, find a different way to express the same idea later
- Vary greeting patterns, confirmation phrases, and transitional expressions
- Service staff may have patterns but should still vary their wording naturally

Follow all the specified rules and requirements to create a realistic conversation."""
        
        return prompt
    
    def _save_conversations(self, conversations: List[Dict]):
        """
        Save conversations to JSON file.
        
        Args:
            conversations: List of conversation dictionaries
        """
        output_path = self.config.legit_call_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create comprehensive dataset metadata
        from datetime import datetime
        generation_metadata = {
            "generation_timestamp": datetime.now().isoformat(),
            "generation_method": "category_based",
            "total_conversations": len(conversations),
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_reasoning_effort": getattr(self.config, 'llm_reasoning_effort', None),
            "locale": getattr(self.config, 'locale', getattr(self.config, 'language', 'unknown')),
            "categories": self.config.legit_call_categories
        }
        
        # Build output data structure
        output_data = {
            "generation_metadata": generation_metadata,
            "conversations": conversations
        }
        
        # Add token usage summary if tracking is enabled
        if self.token_tracker:
            # Create a wrapper with token usage info (without detailed breakdowns)
            token_summary = self.token_tracker.get_summary(include_details=False)
            cost_estimate = self.token_tracker.estimate_cost()
            
            output_data["token_usage"] = token_summary
            output_data["estimated_cost"] = cost_estimate
            
            # Print summary if verbose
            if self.config.verbose:
                self.token_tracker.print_summary()
                self.token_tracker.print_cost_estimate()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        self.clogger.info(f"Saved legitimate conversations to {output_path}")