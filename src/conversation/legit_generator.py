"""
Legitimate conversation generator using LLM core with LangChain.
"""

import json
import random
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

from src.config.config_loader import Config
from src.llm_core.api_provider import LLM
from src.llm_core.api_call import make_api_call
from src.llm_core.token_counter import TokenUsageTracker
from src.conversation.schemas import LegitConversationResponse
from src.conversation.conversation_postprocessor import create_postprocessor_from_config
from src.utils.logging_utils import ConditionalLogger
from src.conversation.entity_tracker import UsedEntityTracker, sample_names_from_placeholders
from src.conversation.length_utils import (
    estimate_dialogue_syllables,
    estimate_minutes_from_syllables,
)


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
        # Entity tracker for names reuse
        self.entity_tracker = UsedEntityTracker(
            window_size=getattr(config, 'min_unique_name_window', 200)
        )
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
        
        # Load placeholder mappings for names and institutions (similar to scam_generator)
        self.placeholder_mappings = self._load_placeholder_mappings()
        if self.placeholder_mappings:
            self.clogger.debug(f"Loaded {len(self.placeholder_mappings)} placeholder mappings for locale {config.legit_call_language}")
        else:
            self.clogger.warning("No placeholder mappings loaded - names/institutions will not be tracked")
        
        # Pre-compute locale-static prompt section for optimal caching
        self.locale_static_prompt = self._build_locale_static_prompt()
        self.clogger.debug(f"Pre-computed locale-static prompt for {config.legit_call_language} ({config.legit_call_region})")
        
        # Initialize post-processor for conversation quality improvements
        self.postprocessor = None
        if hasattr(config, 'common_config'):
            try:
                self.postprocessor = create_postprocessor_from_config(config.common_config)
                logger.info("Post-processor initialized for conversation quality improvements")
            except Exception as e:
                logger.warning(f"Could not initialize post-processor: {e}. Continuing without post-processing.")
    
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
        # Pre-sample concrete personal names for caller/callee to reduce repetition
        concrete_values = {}
        try:
            # Sample names from placeholders (similar to scam_generator)
            if hasattr(self, 'placeholder_mappings') and self.placeholder_mappings:
                sampled_names = sample_names_from_placeholders(self.placeholder_mappings, self.entity_tracker, count=2)
                if len(sampled_names) >= 2:
                    concrete_values = {
                        "caller_name": sampled_names[0],
                        "callee_name": sampled_names[1]
                    }
                # Also sample organization values based on category (for relevant categories)
                # For legit calls, we might use institutions like bank names, clinic names, etc.
                org_vals = self._sample_org_values_for_category(category)
                if org_vals:
                    concrete_values.update(org_vals)
        except Exception as e:
            self.clogger.warning(f"Error sampling placeholders: {e}")
            concrete_values = {}

        dialogue = await self._generate_dialogue(conversation_id, num_turns, category, concrete_values)
        
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
            
            # Apply post-processing (interruptions, redaction, symbol removal)
            if self.postprocessor:
                conversation = self.postprocessor.process_conversation(conversation, "legit")
                self.clogger.debug(f"Post-processed conversation {conversation_id}")
            # Add length estimates
            try:
                syllables = estimate_dialogue_syllables(conversation["dialogue"])
                conversation["length_estimate_syllables"] = syllables
                conversation["length_estimate_minutes"] = round(estimate_minutes_from_syllables(syllables), 2)
            except Exception:
                pass
            if concrete_values:
                conversation["placeholders_used"] = concrete_values
            
            return conversation
        
        return None
    
    async def _generate_dialogue(self, conversation_id: int, num_turns: int, category: str, concrete_values: Dict = None) -> Optional[List[Dict]]:
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
        user_prompt = self._create_user_prompt(num_turns, category, concrete_values or {})
        
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

**Naming Conventions (CRITICAL - Malaysian Context):**
- **Honorifics are TITLES, not part of names**:
  - ✅ CORRECT: "Encik Ahmad" (Encik = title, Ahmad = name)
  - ✅ CORRECT: "Puan Siti" (Puan = title, Siti = name)
  - ❌ WRONG: "Encik Wen Jie" (Encik is title, Wen Jie is given name - should be "Encik Tan" or just "Wen Jie")
  - **Rule**: Honorifics (Encik, Puan, Tuan, Cik, Datuk) must be followed by surname/family name, NOT given name
- **Chinese Names**: Use surname-first format when with honorifics
  - ✅ "Encik Tan" (surname) or "Tan Wen Jie" (full name without honorific)
  - ❌ "Encik Wen Jie" (given name with honorific - incorrect)
- **Malay Names**: Typically given name + bin/binti + father's name
  - ✅ "Ahmad bin Hassan" or "Encik Ahmad"
  - ✅ "Siti binti Rahman" or "Puan Siti"
- **Use honorifics correctly**: Only when addressing formally, not as part of the actual name

**Code-Switching Fluency (Natural Transitions):**
- Code-switching should feel natural and fluent, not forced or awkward
- ❌ AWKWARD: "got little grammar error" (mixing English grammar with Malay word order)
- ✅ NATURAL: "ada sedikit kesilapan tatabahasa" (all Malay) OR "grammar ada sikit salah" (natural mixing)
- **Natural patterns**:
  - Technical/financial terms: Often in English ("transfer", "account", "TAC code", "online banking")
  - Common phrases: Mix naturally ("ok", "sure", "confirm")
  - Full sentences: Usually in one language, not mixed mid-sentence awkwardly
- **Avoid**: Awkward word-for-word translations that don't flow naturally
- **Test**: Would a native Malaysian speaker naturally mix languages this way?

**Malaysian Institution/Department Validation (CRITICAL):**
- **Department-Agency Mismatches (FORBIDDEN)**:
  - ❌ KWSP issues handled by LHDN (WRONG - KWSP issues → KWSP only)
  - ❌ LHDN handling EPF/KWSP withdrawals (WRONG - KWSP handles its own withdrawals)
  - ✅ KWSP issues → KWSP (Kumpulan Wang Simpanan Pekerja)
  - ✅ Tax issues → LHDN (Lembaga Hasil Dalam Negeri)
  - ✅ Traffic summonses → PDRM Traffic Department or "Jabatan Siasatan Dan Penguatkuasaan Trafik"
- **Full Department Names (Use Complete Names)**:
  - ❌ "Jabatan Siasatan Trafik" (INCOMPLETE)
  - ✅ "Jabatan Siasatan Dan Penguatkuasaan Trafik" (COMPLETE official name)
  - ✅ "Jabatan Siasatan Trafik Polis Diraja Malaysia" (with PDRM context)
- **Company Name Conventions**:
  - TNB = "Tenaga Nasional Berhad" or "TNB" (use consistently, don't mix "Tenaga Nasional" with "TNB" inconsistently)
  - Full name: "Tenaga Nasional Berhad"
  - Short form: "TNB"
  - Use the same form throughout conversation
- **Communication Methods (Realistic for Malaysia)**:
  - ❌ Government offices using WhatsApp for official matters (UNREALISTIC)
  - ✅ Government/bank: Phone calls, official letters, email for official matters
  - ✅ WhatsApp: Only for informal communications, NOT for official government/bank matters
- **Use "Jabatan" for government-related offices**: "Jabatan" is used for government-related offices, not for private companies
"""
        # Add more locale-specific patterns here as needed for other languages
        
        # Voice selection now handled externally, not by LLM
        
        return locale_prompt
    
    def _load_placeholder_mappings(self) -> Dict[str, Dict]:
        """
        Load placeholder mappings for the current locale.
        
        Returns:
            Dictionary mapping placeholder names to their descriptions and substitutions
        """
        # Build path to placeholders.json for the current locale
        locale_id = getattr(self.config, 'locale', getattr(self.config, 'legit_call_language', 'ms-my'))
        if not hasattr(self.config, 'config_dir'):
            # Fallback: try to find config directory
            config_dir = Path(__file__).parent.parent.parent / "configs"
        else:
            config_dir = self.config.config_dir
        
        placeholders_path = config_dir / "localizations" / locale_id / "placeholders.json"
        
        if not placeholders_path.exists():
            self.clogger.warning(f"No placeholder mappings found at {placeholders_path}")
            return {}
        
        try:
            with open(placeholders_path, 'r', encoding='utf-8') as f:
                placeholder_data = json.load(f)
            
            # Convert to dictionary for easy lookup
            mappings = {}
            for item in placeholder_data:
                placeholder_name = item.get('placeholder_name')
                if placeholder_name:
                    mappings[placeholder_name] = {
                        'description': item.get('description', ''),
                        'substitutions': item.get('substitutions', [])
                    }
            
            return mappings
            
        except Exception as e:
            self.clogger.error(f"Error loading placeholder mappings: {e}")
            return {}
    
    def _sample_org_values_for_category(self, category: str) -> Dict[str, str]:
        """Sample organization-related concrete values based on legit call category.
        
        Args:
            category: Legitimate call category (e.g., 'bank_verification_call', 'clinic_appointment')
            
        Returns:
            Dictionary of sampled organization values
        """
        if not hasattr(self, 'placeholder_mappings') or not self.placeholder_mappings:
            return {}
        
        category_lower = (category or "").lower()
        key_buckets = []
        
        # Map legit categories to relevant placeholder keys (using actual keys from placeholders.json)
        if "bank" in category_lower or "banking" in category_lower:
            key_buckets = ["<bank_name_local>"]
        elif "clinic" in category_lower or "hospital" in category_lower or "doctor" in category_lower or "medical" in category_lower:
            key_buckets = ["<health_services_provider_name>", "<health_insurance_provider_name>", "<urgent_medical_facility_name_local>"]
        elif "school" in category_lower or "academic" in category_lower or "education" in category_lower:
            key_buckets = ["<university_or_school_name>", "<bursar_or_student_finance_office_name>"]
        elif "telecom" in category_lower or "phone" in category_lower or "internet" in category_lower or "mobile" in category_lower:
            key_buckets = ["<telecom_provider_name_local>"]
        elif "utility" in category_lower or "electric" in category_lower or "water" in category_lower:
            key_buckets = ["<local_utility_provider_name>"]
        elif "insurance" in category_lower:
            key_buckets = ["<health_insurance_provider_name>"]
        elif "government" in category_lower or "permit" in category_lower or "civil" in category_lower:
            key_buckets = ["<housing_authority_name>", "<public_health_agency_name>"]
        elif "immigration" in category_lower or "visa" in category_lower or "passport" in category_lower:
            key_buckets = ["<passport_authority_name_local>"]
        elif "delivery" in category_lower or "courier" in category_lower:
            key_buckets = ["<courier_company_name_local>"]
        elif "technical" in category_lower or "support" in category_lower:
            key_buckets = ["<company_it_department_name>"]
        elif "billing" in category_lower or "dispute" in category_lower:
            # Could be utility, telecom, or bank - use multiple options
            key_buckets = ["<local_utility_provider_name>", "<telecom_provider_name_local>", "<bank_name_local>"]
        # Add more category mappings as needed
        
        values: Dict[str, str] = {}
        for key in key_buckets:
            if key in self.placeholder_mappings:
                pool = self.placeholder_mappings[key].get('substitutions', [])
                if pool:
                    pick = self.entity_tracker.sample_unique(pool, k=1)
                    if pick:
                        values[key.strip('<>')] = pick[0]
        return values
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for legitimate conversation generation.
        Optimized for OpenAI prompt caching - keep this completely static.
        """
        return f"""You are a dialogue generator for creating realistic phone conversations.

## Core Task
Generate COMPLETE structured dialogues for legitimate (non-scam) phone calls with alternating turns between caller and callee.
The conversations should be natural, contextually appropriate, culturally relevant, and reach a proper conclusion.

## 🚨 CRITICAL LENGTH REQUIREMENT 🚨
**ABSOLUTE MANDATORY REQUIREMENT**: Every conversation MUST contain between **1,500 and 1,750 syllables** total across all dialogue turns. The target is **1,625 syllables** (sweet spot). This is a NON-NEGOTIABLE requirement - conversations below 1,500 or above 1,750 syllables will be rejected. Each turn must be substantial (45-85 syllables average) to meet this requirement.

## Output Format Requirements
Each dialogue turn must have exactly these fields:
- text: The actual dialogue text
- role: Either "caller" or "callee"

The dialogue must be returned as a JSON array with the exact format shown in examples.

## Generation Guidelines

### Conversation Quality
1. Create natural, realistic dialogue for the given context
2. Avoid overly generic or repetitive phrasing
3. Use natural sentence length - aim for substantial dialogue (45-85 syllables per turn on average) to meet the 1,500 syllable requirement
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

## Formality Consistency Rules - CRITICAL MATCHING REQUIREMENT

**ABSOLUTE REQUIREMENT**: Formality levels MUST match between caller and callee based on relationship context.

1. **Friend Chats (family_checkin, friend_chat)**: 
   - **BOTH parties MUST use fully casual language**
   - **FORBIDDEN**: No honorifics ("Encik", "Tuan", "Puan", "Cik")
   - Use: "kau", "awak", "kita", casual particles ("lah", "je", "kan")
   - Example: "Eh, hi Arif!" NOT "Selamat pagi, Encik Arif"
   - Both should match each other's casual tone throughout

2. **Professional Calls** (bank, government, clinic, service):
   - **Match Formality**: If caller is formal, callee responds formally; if caller is casual-friendly, callee can be slightly casual
   - Clinic/hospital = moderately formal but friendly
   - Bank/government = more formal
   - Service industry = casual-friendly

3. **Formality Alignment**:
   - **NO formality mismatches**: If one party uses "Encik/Puan", both should maintain similar formality
   - If callee starts casual, caller should adapt OR maintain professional but warm tone (not overly formal)
   - Professional calls: Blend formality with friendliness naturally

4. **No Sudden Switches**: Avoid formal→casual→formal jumps within the same character's dialogue
5. **Maintain Character Voice**: Service providers maintain consistent professional tone, customers maintain their natural style matching the context
6. **Context-Appropriate Language**: Match vocabulary complexity and formality to the service type and relationship

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

    def _create_user_prompt(self, num_turns: int, category: str, concrete_values: Dict) -> str:
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
4. Use natural sentence length - aim for substantial dialogue (45-85 syllables per turn on average) to meet the 1,500 syllable requirement
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
        
        # Inject concrete values if provided
        if concrete_values:
            prompt += "\n#### Concrete Values (Use Exactly As Given)\n"
            for k, v in concrete_values.items():
                prompt += f"- {k}: {v}\n"
            prompt += (
                "Use the exact values above for names/organizations; do not invent other proper nouns.\n"
            )

        prompt += f"""
### This Conversation's Parameters

#### Conversation Specifics

**Category**: {category_display}

**🚨 CRITICAL SCENARIO REALISM VALIDATION 🚨**:

Some categories may represent activities typically done in-person or online. You MUST reframe them as phone-appropriate interactions:

**Unrealistic for Phone (REFRAINED AS):**
- **subscription_renewal**: Magazine subscriptions are typically done with delivery person or online. REFRAME as: Phone call to **confirm renewal status**, **discuss payment options**, or **notify about upcoming expiration** - NOT the primary transaction itself
- **product_feedback_survey**: Surveys are usually online or at physical events. REFRAME as: Phone call to **invite participation**, **follow up on previous purchase**, or **discuss specific product experience** - NOT conducting full survey on phone
- **class_schedule_change**: Class schedules are typically fixed and handled through academic office. REFRAME as: Phone call to **request consideration** (knowing it may not be possible), **discuss options if change is possible**, or **inquire about process** - NOT guaranteed change approval

**Phone-Appropriate Interactions:**
- Confirmations, notifications, follow-ups
- Scheduling and appointment management
- Information requests and clarifications
- Status updates and check-ins
- Problem resolution discussions

**CRITICAL**: If the category suggests an in-person or online activity, reframe the conversation as a phone-appropriate interaction (confirmation, follow-up, scheduling, inquiry) rather than the primary transaction itself. The conversation should be realistic for what would actually happen via phone call in Malaysian context.

**🚨 MALAYSIAN REALISM VALIDATION - CRITICAL REQUIREMENTS 🚨**:

**Family Call Openings (CRITICAL for family_checkin and similar categories):**
- ❌ UNREALISTIC: "Hi i am XXX, your brother" (unclear, unnatural, lacks context)
- ✅ NATURAL: "Hello, Assalamualaikum Kak Ana. Ini Khairul, adik awak." (clear relationship, natural greeting with context)
- ✅ NATURAL: "Hi Kak, ini Arif. Macam mana hari ni?" (uses family term, clear identity)
- Family calls should start with:
  1. Natural greeting (Hello/Hi/Assalamualaikum)
  2. Family term (Kak/Abang/Adik/Mak/Ayah) OR name
  3. Clear identification ("Ini [name]" or "Ini adik awak")
  4. Context ("your brother", "Arif dari KL")
- Use appropriate family terms (Kak, Abang, Adik, Mak, Ayah, etc.)
- The call should be meaningful - not just "I am your brother" with no purpose

**Number of Turns**: Generate EXACTLY {num_turns} dialogue turns (you may adjust ±2 turns ONLY if absolutely necessary for natural flow and complete resolution)

**🚨 CRITICAL LENGTH REQUIREMENT - MANDATORY AND NON-NEGOTIABLE 🚨**:
- **ABSOLUTE HARD REQUIREMENT**: The conversation MUST contain BETWEEN **1,500** and **1,750** syllables TOTAL across all turns.
- **EVERY SINGLE CONVERSATION MUST MEET THIS RANGE - NO EXCEPTIONS**
- Output below 1,500 syllables is AUTOMATICALLY INVALID and will be REJECTED
- Output above 1,750 syllables is AUTOMATICALLY INVALID and will be REJECTED
- **TARGET SWEET SPOT: 1,625 syllables** (aim for 1,625, with 1,600-1,650 being ideal)
- This is the HIGHEST PRIORITY requirement - all other requirements are secondary if length is not met

**📏 EXACT SYLLABLE BUDGET PER TURN**:
- **PRIMARY TARGET: 1,625 syllables total** (sweet spot in the middle of 1,500-1,750 range)
- With {num_turns} turns: **{round(1625/num_turns, 1)} syllables PER TURN is the MANDATORY average**
- **CRITICAL**: If your draft has fewer than {round(1500/num_turns, 1)} syllables per turn on average, YOU HAVE FAILED and MUST EXPAND IMMEDIATELY
- **CRITICAL**: If your draft exceeds 1,700 syllables, YOU MUST REDUCE dialogue to get closer to 1,625
- **MANDATORY**: NO turn should be shorter than 40 syllables (except max 1-2 extremely rare single-word reactions)
- **REQUIRED**: At least 85% of turns must be 45-85 syllables each
- **FORBIDDEN**: Turns under 35 syllables are NOT ALLOWED (maximum 1-2 in entire conversation)
- Short turns (35-45 syllables) MUST be balanced by turns that are 75-110+ syllables
- **VERIFY BEFORE SUBMITTING**: Count total syllables - aim for 1,625, accept 1,500-1,750 range

**📋 CONCRETE EXAMPLE - What 1,625 Syllables Looks Like**:
Example conversation with 35 turns targeting 1,625 syllables (~46.4 syllables per turn average):

Turn 1 (Service Staff, ~62 syllables): "Hello, selamat pagi. Saya Zahid dari Bank Maju. Boleh saya bercakap dengan Encik Amin tak? Saya call sebab kami ada terima permohonan baru baru ni, dan saya cuma nak sahkan beberapa maklumat penting je untuk urusan kad kredit Encik."
Turn 2 (Customer, ~55 syllables): "Hi, selamat pagi Zahid. Ya, saya Amin ni. Oh, pasal permohonan kad kredit tu ke? Saya memang ada apply beberapa minggu lepas. Jadi ada apa masalah ke, atau cuma nak verify maklumat je?"
Turn 3 (Service Staff, ~68 syllables): "Takde masalah Encik Amin, cuma untuk keselamatan dan proses approval, kami perlu confirm beberapa details lagi. Pertama sekali, boleh saya tanya, alamat rumah Encik masih di Jalan Melur 10 tu ke? Kalau ada perubahan, Encik kena update dulu sebelum kami proceed dengan approval."

**KEY OBSERVATIONS**:
- Each turn averages 48-72 syllables (NOT 28-32!)
- Most turns are 55-85 syllables long
- Only 1-2 very short turns (<40 syllables) in entire conversation
- Every explanation has 3-5 sentences with context, details, and helpful information
- Questions include background context and reasons for asking

**THIS IS WHAT YOU MUST GENERATE** - substantial dialogue, not short exchanges.

**🚨 CRITICAL TURN COUNT REQUIREMENT 🚨**:
- **YOU MUST generate AT LEAST {num_turns - 2} turns (minimum acceptable)**
- **Target: EXACTLY {num_turns} turns**
- **DO NOT END THE CONVERSATION EARLY** - if you generate fewer than {num_turns - 2} turns, the output will be REJECTED
- **If you think the conversation is "complete" at turn 20 but you need {num_turns} turns, YOU MUST CONTINUE with additional relevant dialogue**
- **Examples of how to extend conversations**:
  - Add follow-up questions or clarifications
  - Include scheduling details (date, time, location)
  - Discuss next steps or confirmation processes
  - Add polite closing conversation (small talk, well-wishes, etc.)
  - Confirm details that were mentioned earlier

**🎯 MANDATORY EXPANSION STRATEGIES - EVERY TURN MUST BE SUBSTANTIAL**:

- **Service staff turns - MINIMUM 55-85 syllables each (most should be 65-95)**:
  - **REQUIRED**: Every explanation must have 3-5 sentences, not 1-2
  - **REQUIRED**: Provide comprehensive step-by-step instructions with multiple clauses:
    Example: "Untuk appointment tu, awak boleh pilih sama ada online booking atau datang terus ke klinik. Kalau online, awak buka website kami, lepas tu register dulu kalau first time. Then awak boleh pilih slot masa yang available. Tapi kalau awak nak lebih cepat, boleh juga datang terus tapi mungkin kena tunggu kalau ramai orang."
  - **REQUIRED**: Include timing, requirements, alternatives, and helpful context in EVERY explanation
  - **REQUIRED**: Address the question AND add 2-3 additional relevant pieces of information
  
- **Customer turns - MINIMUM 45-75 syllables each (most should be 55-85)**:
  - **FORBIDDEN**: Single-word or short responses like "Ok", "Noted", "Sure", "Takpe", "Baik"
  - **REQUIRED**: Every response must include context, reasons, or follow-up questions:
    ❌ BAD: "Ok"
    ✅ REQUIRED: "Ok faham, so saya akan try online booking dulu malam ni. Kalau ada masalah atau tak dapat slot yang saya prefer, saya akan call balik esok untuk arrange alternative time. Thanks banyak-banyak for the information!"
  - **REQUIRED**: Ask 2-3 related questions in ONE turn with explanations:
    Example: "Saya nak tahu, untuk appointment ni kena bawa apa-apa dokumen ke? Saya ada medical report dari doktor lain, perlu ke bawa sekali? Dan satu lagi, kalau saya nak cancel last minute, ada penalty ke atau boleh reschedule je?"
  - **REQUIRED**: Provide detailed context when explaining needs: "Saya nak buat appointment untuk medical check-up sebab company saya require annual health screening. Tapi masa saya available agak limited sebab working hours, so kalau boleh saya prefer weekend atau after office hours. Ada slot macam tu tak?"
  
- **MANDATORY Dialogue Expansion Rules**:
  - **EVERY turn must have 3+ sentences** (no exceptions except for 1-2 extremely rare single-word reactions)
  - **EVERY question must include context, reason, or follow-up** - standalone questions are FORBIDDEN
  - **EVERY answer must address the question AND add 1-2 additional pieces of relevant information**
  - **REQUIRED**: Use natural small talk and rapport-building that expands dialogue meaningfully
  - **REQUIRED**: Include thinking-out-loud moments and natural hesitations: "Hmm, kalau macam tu... jadi maksudnya saya perlu... tapi saya nak tanya, macam mana kalau..."
  - **REQUIRED**: Add helpful additional information, alternatives, and options to every service response
  
- **ABSOLUTELY FORBIDDEN - These will cause rejection**:
  - ❌ "Ok" (must be "Ok faham, jadi...")
  - ❌ "Noted" (must be "Noted, saya akan...")
  - ❌ "Sure" (must be "Sure, tapi saya nak confirm...")
  - ❌ "Takpe" (must be "Takpe, tapi saya prefer...")
  - ❌ Any turn under 30 syllables (maximum 2-3 per entire conversation)
  
**✅ MANDATORY FINAL VERIFICATION BEFORE SUBMITTING**:
1. **Count syllables in EVERY turn** - mentally estimate or use a rough count
2. **Calculate total syllables** - add up all turns
3. **VERIFY THE TARGET**: Aim for **1,625 syllables** (ideal range: 1,600-1,650)
4. **ACCEPTABLE RANGE**: 1,500-1,750 syllables (only if you cannot hit 1,625 exactly)
5. **If below 1,500**: YOU MUST EXPAND multiple turns to reach at least 1,500
6. **If above 1,700**: YOU MUST REDUCE dialogue - prefer 1,625 over 1,700+
7. **DO NOT SUBMIT** until you have verified the total is between 1,500-1,750, ideally 1,625

**CRITICAL**: The average syllable count per turn MUST be at least {round(1500/num_turns, 1)} but SHOULD TARGET {round(1625/num_turns, 1)}. If your current draft averages less than {round(1500/num_turns, 1)}, you HAVE FAILED and MUST EXPAND. If your draft exceeds {round(1700/num_turns, 1)}, you MUST REDUCE to get closer to 1,625.
  
**Natural speech still applies** - don't pad with meaningless filler, but ensure EVERY turn has substantial, meaningful dialogue content that advances the conversation while meeting the syllable requirement.

**Context**: This is a legitimate business/service call about {category_display.lower()}

#### Conversation Flow Structure (Adapt based on category complexity and total turns)
**REMEMBER**: Complex conversations should use more phases, simpler conversations can condense phases. Each phase must contribute SUBSTANTIAL dialogue (45–80 syllables per turn) to reach ~1,625 total syllables while staying within 1,500–1,750 total.

**STRUCTURED PROGRESSION GUIDELINES** - Adapt this framework based on conversation complexity:

**For COMPLEX conversations** (appointments, verifications, problem-solving, consultations):
Use full 6-phase structure below.

**For SIMPLE conversations** (reminders, confirmations, brief updates):
Condense phases 3-4 into a single "Main Discussion" phase, and phases 5-6 can be shorter.

1. **Opening & Greeting** (3-5 turns, ~250-400 syllables):
   - Caller: Extended greeting with identity, organization (if applicable), and purpose
   - Callee: Extended response with acknowledgment, questions about identity/context
   - Build rapport: Natural small talk, confirmation of relationship/context
   - Examples:
     - Service call: "Hello, selamat pagi. Saya Zahid dari Bank Maju. Boleh saya bercakap dengan Encik Amin tak? Saya call sebab kami ada terima permohonan baru baru ni, dan saya cuma nak sahkan beberapa maklumat penting je untuk urusan kad kredit Encik."
     - Family call: "Hello, Assalamualaikum Kak Ana. Ini Khairul, adik awak. Macam mana hari ni? Saya call sebab nak check macam mana keadaan Kak Ana, dan ada benda sikit yang saya nak bincang dengan Kak Ana."

2. **Purpose Statement & Context** (4-6 turns, ~300-450 syllables):
   - Caller: Detailed explanation of why calling, background context, what's needed
   - Callee: Detailed response showing understanding, asking clarifying questions
   - Provide context: Why this call is happening now, what led to it, what's at stake
   - Examples:
     - Appointment: Explain why appointment needed, what it's for, urgency/importance
     - Verification: Explain what triggered verification, what needs to be confirmed, timeline
     - Family: Explain what's happening, why calling, what help/info is needed

3. **Detailed Discussion & Information Exchange** (8-12 turns for complex, 4-6 turns for simple):
   - **This is the MAIN phase - expand significantly here for complex conversations**
   - For COMPLEX calls: Exchange detailed information: Dates, times, requirements, procedures, options. Address questions: Multiple rounds of Q&A, clarifications, explanations. Discuss alternatives: Different options, preferences, constraints. Provide context: Background info, related details, helpful information.
   - For SIMPLE calls: Provide essential information, answer key questions, confirm details. Don't over-extend - keep it natural and realistic.
   - Examples:
     - Complex (Appointment): Available slots, preparation needed, documents required, insurance coverage, alternatives, cancellation policies
     - Complex (Verification): Information to verify, why it's needed, how to provide it, timeline, security measures
     - Simple (Reminder): What's being reminded, when, where, any changes, confirm receipt
     - Simple (Confirmation): Confirm details, provide any updates, answer brief questions

4. **Problem-Solving & Decision-Making** (3-5 turns for complex, 0-2 turns for simple):
   - **For COMPLEX conversations only**: Work through any issues, discuss solutions, make decisions
   - Address concerns: Handle objections, clarify misunderstandings, provide reassurance
   - Explore options: Discuss alternatives, compare choices, consider constraints
   - Confirm understanding: Ensure both parties understand next steps
   - **For SIMPLE conversations**: Skip or condense this phase - most simple calls don't need extensive problem-solving

5. **Confirmation & Next Steps** (4-6 turns, ~300-450 syllables):
   - Summarize: Recap what was discussed, what was decided, what's happening next
   - Confirm details: Dates, times, locations, requirements, contact information
   - Provide instructions: What each party needs to do, deadlines, follow-up actions
   - Set expectations: When to expect updates, who to contact, what happens next
   - Examples:
     - Appointment: Confirm date/time, location, preparation needed, reminder system
     - Verification: Confirm what was verified, what's complete, any follow-up needed
     - Service: Confirm service details, timeline, contact for issues

6. **Polite Closure** (3-4 turns, ~200-300 syllables):
   - Express appreciation: Thank each other, acknowledge help provided
   - Small talk: Natural closing conversation, well-wishes, family updates (if appropriate)
   - Final confirmations: Last-minute reminders, contact information
   - Goodbyes: Natural, culturally appropriate farewells

**KEY PRINCIPLES FOR EXTENDING CONVERSATIONS:**
- **Match complexity to category**: Complex calls (appointments, verifications) need detailed phases. Simple calls (reminders, confirmations) should be more concise.
- **Add natural detail**: Background context, examples, alternatives, related information - but only when relevant to the call type
- **Include natural follow-ups**: Additional questions, clarifications, confirmations - appropriate to the call's purpose
- **Build rapport**: Small talk, personal touches, cultural courtesies - but don't overdo it for simple calls
- **Provide helpful context**: Why things are happening, what to expect, what's normal - but keep it proportional
- **Address concerns naturally**: Questions, hesitations, need for clarification - but not every call needs extensive Q&A

**Category-Specific Complexity Guidelines:**
- **COMPLEX (use full 6-phase structure)**: Appointments, verifications, consultations, problem-solving, insurance claims, service requests with options
- **MODERATE (condense phases 3-4)**: Test results, status updates, follow-ups, scheduling changes
- **SIMPLE (condense significantly)**: Reminders, confirmations, brief notifications, holiday greetings, simple check-ins

**Category-Specific Expansion Strategies:**
- **Complex Appointments**: Expand with available slots discussion, preparation requirements, insurance/payment, alternatives, cancellation policies
- **Complex Verifications**: Expand with why verification needed, what information required, how to provide it, timeline, security measures
- **Family/Personal**: Expand with context of situation, updates on family members, planning, emotional support, practical help
- **Simple Reminders**: Keep concise - what, when, where, any changes, confirm receipt
- **Simple Confirmations**: Keep concise - confirm details, provide brief updates, answer essential questions

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

**Context-Appropriate Knowledge (Realistic Caller/Callee Behavior):**
Both parties should demonstrate knowledge appropriate to their role and context:

**Service Staff Knowledge:**
- Understand their own procedures, policies, and systems
- Know common requirements for their services
- Can explain processes clearly without confusion
- Example: Clinic staff know appointment procedures, required documents, insurance policies

**Customer/Caller Knowledge:**
- Should have basic understanding of services they're calling about
- Workers understand company policies, HR procedures
- Homeowners know about their utility services, condo rules
- Parents understand school systems, child-related requirements
- Business owners know business registration, licensing, banking procedures

CRITICAL: Both parties should show contextually appropriate intelligence:
- Service staff shouldn't lack knowledge of their own processes (unrealistic)
- Customers shouldn't lack basic knowledge relevant to their situation
- Example: A worker calling about condo visitor procedures should understand basic security concepts

**Context-Specific Formality:**
- Medical/clinic: Moderately formal but empathetic, use particles for warmth
- Banking/government: More formal language but still use "awak/saya", occasional particles
- Education: Professional yet approachable, balance authority with friendliness
- Service bookings: Casual-friendly, full particle use, conversational
- Customer support: Problem-solving friendly, patient, use confirmatory particles

### 🚨 FINAL REMINDER BEFORE GENERATING 🚨

**CRITICAL VERIFICATION REQUIREMENT**:
- Your output MUST contain between **1,500 and 1,750 syllables total** across all dialogue turns
- **Target: 1,625 syllables** (sweet spot in the middle of the range)
- **Before submitting**: Mentally count or estimate syllables in your generated dialogue
- **If total is below 1,500**: You MUST expand multiple turns to reach at least 1,500 syllables
- **If total is above 1,750**: You MUST reduce some turns to get under 1,750 syllables
- **Average per turn**: With {num_turns} turns, you need approximately **{round(1625/num_turns, 1)} syllables per turn on average**
- **DO NOT SUBMIT** until you have verified the total syllable count is 1,500-1,750

This is the HIGHEST PRIORITY requirement. All other requirements are secondary if length is not met.

### Generate the Dialogue

Based on the above parameters, generate a COMPLETE conversation with EXACTLY {num_turns} dialogue turns (minimum {num_turns - 2}, maximum {num_turns + 2}) for a legitimate {category_display.lower()} phone call.

**⚠️ CRITICAL**: The conversation MUST reach {num_turns - 2} to {num_turns + 2} turns. Ending earlier will cause REJECTION.

CRITICAL: The conversation MUST:
- Have a clear beginning (greeting and introduction)
- Develop the main topic thoroughly
- Reach a definitive conclusion (appointment scheduled, information provided, issue resolved, etc.)
- End with proper closure (thank you, goodbye, next steps)
- Feel natural and complete, not cut off abruptly
- **MEET LENGTH REQUIREMENT**: Total syllables MUST be 1,500–1,750 (target ≈1,625). Do not exceed 1,750.
- Use detailed turns to naturally reach the target without padding or repetition

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