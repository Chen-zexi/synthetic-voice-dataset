"""
Scam conversation generator using LLM core with LangChain.
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
from src.conversation.schemas import ScamConversationResponse
from src.conversation.seed_manager import SeedManager, ScamSeed
from src.conversation.character_manager import CharacterManager
from src.conversation.conversation_postprocessor import create_postprocessor_from_config
from src.utils.logging_utils import ConditionalLogger
from src.conversation.entity_tracker import UsedEntityTracker, sample_names_from_placeholders
from src.conversation.length_utils import (
    estimate_dialogue_syllables,
    estimate_minutes_from_syllables,
)


logger = logging.getLogger(__name__)


class ScamGenerator:
    """
    Generates multi-turn scam conversations using LLM with seed-based approach.
    Optionally enhances conversations with character profiles for diversity.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the scam generator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.clogger = ConditionalLogger(__name__, config.verbose)
        
        # Initialize seed manager (always use seeds)
        self.seed_manager = None
        seeds_file_path = self.config.multi_turn_input_path
        if seeds_file_path and seeds_file_path.exists():
            try:
                self.seed_manager = SeedManager(seeds_file_path)
            except Exception as e:
                self.clogger.error(f"Failed to load seeds: {e}")
                raise
        else:
            raise FileNotFoundError(f"Seeds file not found at {seeds_file_path}")
        
        # Initialize character manager if enabled
        self.character_manager = None
        if getattr(config, 'generation_enable_character_profiles', False):
            profiles_file_path = None
            voice_profiles_path = None
            
            if hasattr(config, 'generation_profiles_file') and config.generation_profiles_file:
                profiles_file_path = config.base_dir / config.generation_profiles_file
            
            # Get voice profiles path if available
            if hasattr(config, 'voice_profiles') and config.voice_profiles:
                voice_profiles_path = config.voice_profiles
            
            # Get scenario template paths if available
            scenario_templates_path = None
            scenario_assignments_path = None
            if hasattr(config, 'scenario_templates_file') and config.scenario_templates_file:
                scenario_templates_path = config.base_dir / config.scenario_templates_file
            if hasattr(config, 'scenario_assignments_file') and config.scenario_assignments_file:
                scenario_assignments_path = config.base_dir / config.scenario_assignments_file
            
            self.character_manager = CharacterManager(
                profiles_file_path, 
                voice_profiles_path,
                victim_awareness_levels=config.victim_awareness_levels,
                num_turns_range=(config.num_turns_lower_limit, config.num_turns_upper_limit),
                scenario_templates_path=scenario_templates_path,
                scenario_assignments_path=scenario_assignments_path
            )
        
        
        # Initialize LLM with configurable provider (default to OpenAI)
        self.llm_provider = getattr(config, 'llm_provider', 'openai')
        self.llm_model = getattr(config, 'llm_model', 'gpt-4o')
        
        # Check for Response API and token tracking settings
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
        
        # Load placeholder mappings for the current locale
        self.placeholder_mappings = self._load_placeholder_mappings()
        if self.placeholder_mappings:
            self.clogger.debug(f"Loaded {len(self.placeholder_mappings)} placeholder mappings for locale {config.language}")
            # Pre-compute compact JSON for placeholders
            self.placeholder_json_compact = self._build_compact_placeholder_json()
        else:
            self.placeholder_json_compact = "{}"
        
        # Pre-compute locale-static prompt section for optimal caching
        self.locale_static_prompt = self._build_locale_static_prompt()
        self.clogger.debug(f"Pre-computed locale-static prompt for {config.language} ({config.region})")
        
        # Initialize post-processor for conversation quality improvements
        self.postprocessor = None
        # Initialize entity tracker for names/orgs reuse control
        self.entity_tracker = UsedEntityTracker(
            window_size=getattr(config, 'min_unique_name_window', 200)
        )

    def _sample_org_values(self, scam_tag: Optional[str]) -> Dict[str, str]:
        """Sample organization-related concrete values based on scam tag.

        Enhanced with Malaysian-specific department/agency validation to prevent mismatches.
        Maps scam tags to correct department/agency pairs.
        """
        if not scam_tag:
            return {}
        tag = (scam_tag or "").lower()
        key_buckets = []
        
        # Malaysian-specific mappings with department validation
        if "kwsp" in tag or "epf" in tag:
            # KWSP/EPF issues MUST be handled by KWSP, NOT LHDN
            key_buckets = [
                "<bank_name_local>",  # KWSP may use bank references
                "<direct_deposit_portal_name>",  # KWSP portals
            ]
            # Note: KWSP-specific placeholders would go here if available
        elif "lhdn" in tag or "tax" in tag:
            # Tax issues MUST be handled by LHDN, NOT other departments
            key_buckets = [
                "<national_tax_agency_name>",  # LHDN
                "<tax_identification_number_format>",
            ]
        elif "mysikap" in tag or "traffic" in tag or "summons" in tag:
            # Traffic summonses → PDRM Traffic Department
            key_buckets = [
                "<law_enforcement_agency_name>",  # PDRM
                "<case_or_warrant_reference_format>",
            ]
            # Note: Use full name "Jabatan Siasatan Dan Penguatkuasaan Trafik" in prompts
        elif "tnb" in tag or "utility" in tag or "electric" in tag:
            # Utility issues → utility companies
            key_buckets = [
                "<local_utility_provider_name>",  # TNB, etc.
                "<utility_account_number_format>",
            ]
        elif "macau" in tag or "pdrm" in tag or "government" in tag:
            key_buckets = [
                "<law_enforcement_agency_name>",
                "<financial_crimes_division_name_local>",
                "<case_or_warrant_reference_format>"
            ]
        elif "delivery" in tag or "courier" in tag:
            key_buckets = [
                "<courier_company_name_local>",
                "<parcel_tracking_number_format>",
                "<shipping_address_format_local>"
            ]
        elif "investment" in tag or "forex" in tag or "crypto" in tag:
            key_buckets = [
                "<investment_regulator_name>",
                "<trading_app_name_local>",
                "<crypto_token_symbol_local>"
            ]
        elif "loan" in tag:
            key_buckets = [
                "<bank_name_local>",
                "<account_verification_fee_label_local>"
            ]
        elif "e-commerce" in tag or "ecommerce" in tag:
            key_buckets = [
                "<ecommerce_platform_name_local>",
                "<payment_link_domain_pattern_local>"
            ]
        elif "telecom" in tag or "voice" in tag:
            key_buckets = [
                "<telecom_provider_name_local>",
                "<mobile_number_format_local>"
            ]

        values: Dict[str, str] = {}
        for key in key_buckets:
            if key in self.placeholder_mappings:
                pool = self.placeholder_mappings[key].get('substitutions', [])
                pick = self.entity_tracker.sample_unique(pool, k=1)
                if pick:
                    values[key.strip('<>')] = pick[0]
        return values
    
    def _load_placeholder_mappings(self) -> Dict[str, Dict]:
        """
        Load placeholder mappings for the current locale.
        
        Returns:
            Dictionary mapping placeholder names to their descriptions and substitutions
        """
        # Build path to placeholders.json for the current locale
        locale_id = self.config.language  # e.g., "ms-my", "ar-sa"
        placeholders_path = self.config.config_dir / "localizations" / locale_id / "placeholders.json"
        
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
    
    def _build_locale_static_prompt(self) -> str:
        """
        Pre-compute the locale-specific static prompt section.
        This section remains identical for all conversations in a batch for the same locale.
        Optimized for OpenAI prompt caching to maximize cache hits in production.
        
        Returns:
            Formatted locale-specific prompt section
        """
        target_language = getattr(self.config, 'language_name', 'English')
        target_region = getattr(self.config, 'region', '')
        
        # Start with language requirements
        locale_prompt = f"""
### Locale Configuration

#### Language Requirements
Generate the entire conversation in {target_language}{f' as spoken in {target_region}' if target_region else ''}.
Use natural, colloquial {target_language} expressions and dialogue patterns.
Incorporate localized values naturally into {target_language} sentences.
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
- Scammers often use clearer grammar to build authority and credibility
- Test: Would a native Malaysian speaker actually say this phrase?

**Colloquial Particles (Use strategically, NOT excessively):**
- "lah" (emphasis, softening): "Tak boleh lah", "Saya faham lah"
  - Professional scammers: Limited use (1-2 per turn) to maintain authority
  - Casual scammers: More frequent but still moderate use
- "kan" (confirmation seeking): "Betul kan?", "Awak tahu kan?"
- "je" (only, just): "Sikit je", "Tunggu sekejap je"
- "pun" (also, even): "Saya pun tak tahu", "Itu pun boleh"
- "ni/tu" (this/that): "Orang ni", "Macam tu lah"
- MUST appear at END of phrases, NOT mid-sentence
- Balance: Use particles to add flavor, not in every sentence

**Natural Disfluencies and Fillers (Use moderately, context-dependent):**
- Thinking pauses: "errr", "emmm", "hmm", "aaa"
- Time-buying: "tunggu sekejap ya", "kejap", "kejap ya", "jap"
- Surprise/reaction: "eh", "ah", "wah", "alamak", "aduh", "ha"
- Processing: "macam mana ya", "apa eh", "camne ni"
- Natural interruptions: "tunggu dulu", "tapi...", "maksud saya..."
- Professional scammers: Fewer fillers, more composed speech
- Victims: More natural hesitations and confusion markers
- Use 1-3 fillers per turn, not every sentence

**Incomplete Sentences and Conversational Shortcuts:**
- Trail off naturally: "Kalau macam tu...", "Tapi saya rasa...", "Jadi maksudnya..."
- Quick responses: "ok jap", "on lah", "boleh je", "takpe"
- Casual questions: "macam tu ke?", "betul ke?", "ye ke?"
- Keep core meaning clear even with shortcuts

**Formality Matching by Role (CRITICAL - Don't Sound Like Written Text):**
- Government scammers: Professional BUT still conversational - use "kena", "ada", "boleh" not "perlu", "adalah", "mesti"
  Example: "Encik kena settle ni cepat" NOT "Encik perlu menyelesaikan perkara ini dengan segera"
- Bank/Insurance scammers: Friendly-professional, NOT corporate formal
  Example: "Awak ada unclaimed money ni" NOT "Terdapat wang yang belum dituntut"
- Investment scammers: Persuasive-professional, mix of formal and friendly but CONVERSATIONAL
- ALL scammers: Must sound like they're SPEAKING, not reading a script
- Victims (elderly): More traditional Malay, fuller sentences, less casual
- Victims (young): More casual with code-switching, natural shortcuts
- Victims (professional): Questioning tone, grammatically clearer, skeptical

**Honorifics (Gender and context appropriate):**
- Male: "Encik" (Mr.), "Tuan" (Sir, formal)
- Female: "Puan" (Mrs./Madam), "Cik" (Miss)
- DO NOT mix gender honorifics - verify character gender before use
- Use sparingly - overuse sounds artificial
- Government/bank scammers: Use honorifics to establish authority

**Natural Word Choices (Match speaker role and education):**
- "sila" → use "tolong" or direct request (except formal scammers)
- "adakah" → use "ke" or "ada... tak?"
- "terima kasih" → use "thanks", or "terima kasih" occasionally
- "baik" → use "ok", "okay", "boleh"
- "mengapa" → use "kenapa"
- Professional scammers: Can use more formal vocabulary naturally
- Choose words that match the speaker's background and role

**Code-Switching (Natural for younger/urban speakers):**
- Mix English words naturally: "ok", "sure", "sorry", "urgent", "confirm"
- Keep it contextual - financial/tech terms often use English
- Professional scammers: Strategic English use (official terms)
- Older victims: Less English mixing
- Young victims: More natural code-switching

**Grammatical Foundation (Real speech has minor imperfections, not errors):**
- Natural imperfections: Minor word order shifts, dropped optional words
- Double subjects (natural): "Saya ni, saya tak faham"
- Simplified questions: "Awak tahu tak?" (instead of "Adakah awak tahu?")
- Word order variations: "Tak boleh ke?" (natural informal)
- Mid-thought clarifications: Natural topic shifts with context maintained
- Scammers: Generally clearer grammar to maintain credibility
- DON'T create broken grammar that confuses meaning
- DON'T force imperfections that native speakers wouldn't make

**Common Pitfalls to AVOID:**
- Overusing particles until sentences lose meaning
- Using formal words incorrectly: "mengaku" when you mean "pastikan"
- Breaking grammar to force casualness: "kemas kini terakhir" → use "kemas kini buat kali terakhir"
- Awkward constructions: "membangun kepercayaan" → use "menguatkan kepercayaan"
- Adding unnecessary words: "langkah yang pertama" → "langkah pertama"
- Mixing formality inconsistently within same character
- Making professional scammers sound too casual (breaks credibility)

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
  - ❌ TNB aggressively chasing fees over phone (UNREALISTIC - they send bills, not aggressive phone calls)
  - ✅ Utility companies: Send bills, may call for overdue payments but not aggressive chasing
"""
        # Add more locale-specific patterns here as needed for other languages
        
        # Voice selection now handled by character-voice mappings, not LLM
        
        # Add placeholder context with ALL placeholders for the locale
        if self.placeholder_mappings:
            placeholder_context = self._build_placeholder_context()  # No need to pass placeholders
            if placeholder_context:
                locale_prompt += f"""
{placeholder_context}"""
        
        return locale_prompt
    
    def _build_compact_placeholder_json(self) -> str:
        """
        Build a compact JSON representation of all placeholder mappings.
        This format reduces token consumption by ~75% compared to verbose format.
        
        Returns:
            Compact JSON string with placeholder mappings
        """
        if not self.placeholder_mappings:
            return "{}"
        
        # Build compact dictionary with just placeholder names and substitutions
        compact_dict = {}
        for placeholder_name, mapping in self.placeholder_mappings.items():
            substitutions = mapping.get('substitutions', [])
            if substitutions:
                compact_dict[placeholder_name] = substitutions
        
        # Convert to compact JSON string
        import json
        return json.dumps(compact_dict, ensure_ascii=False, separators=(',', ':'))
    
    def _build_placeholder_context(self, placeholders: List[str] = None) -> str:
        """
        Build placeholder context string for the prompt using compact JSON format.
        Reduces token consumption by ~75% compared to verbose format.
        
        Args:
            placeholders: List of placeholder names (unused for now, kept for compatibility)
            
        Returns:
            Formatted placeholder context for prompt
        """
        # Use the pre-computed compact JSON
        if not hasattr(self, 'placeholder_json_compact') or self.placeholder_json_compact == "{}":
            return ""
        
        # Return compact format with simplified instructions
        return f"""
**LOCALIZED VALUES**:
Use these locale-specific values naturally in the conversation:

{self.placeholder_json_compact}

Select contextually appropriate values from the arrays and incorporate them naturally into the dialogue."""
    
    
    async def generate_conversations(self) -> List[Dict]:
        """
        Generate scam conversations asynchronously using seeds with optional character profiles.
        
        Returns:
            List of conversation dictionaries
        """
        self.clogger.debug(f"Generating scam conversations from seeds")
        
        # Initialize tracking variables for metadata
        self.generation_control_params = {}
        
        # Set random seed for reproducibility if configured
        random_seed = getattr(self.config, 'generation_random_seed', None)
        if random_seed is not None:
            random.seed(random_seed)
            self.clogger.info(f"Set random seed to {random_seed} for reproducible generation")
        
        # Get generation control settings
        generation_control_mode = getattr(self.config, 'generation_control_mode', 'seeds')
        seed_limit = getattr(self.config, 'seed_limit', None)
        total_conversation_limit = getattr(self.config, 'total_conversation_limit', None)  # Target count from --conversation-count
        scenarios_per_seed = getattr(self.config, 'scenarios_per_seed', 1)
        min_quality = getattr(self.config, 'generation_min_seed_quality', 70)
        scenario_mode = getattr(self.config, 'scenario_mode', 'random')
        
        # Store generation parameters for metadata
        self.generation_control_params = {
            "mode": generation_control_mode,
            "seed_limit": seed_limit,
            "conversation_count": total_conversation_limit,  # Target from --conversation-count
            "total_limit": self.config.total_limit,  # Absolute cap from --total-limit
            "scenarios_per_seed": scenarios_per_seed,
            "min_quality_filter": min_quality,
            "scenario_mode": scenario_mode
        }
        
        # Determine limit based on generation mode
        if generation_control_mode == 'conversations' and total_conversation_limit:
            # Calculate seeds needed for total conversations
            import math
            seeds_needed = math.ceil(total_conversation_limit / scenarios_per_seed)
            limit = seeds_needed
            self.clogger.info(f"Conversation mode: targeting {total_conversation_limit} conversations, need {seeds_needed} seeds")
        else:
            # Seed-based mode (default)
            if seed_limit is not None:
                limit = seed_limit
            elif self.config.scam_sample_limit is not None:
                limit = self.config.scam_sample_limit
            else:
                limit = self.config.total_limit  # Use total_limit as the default
        
        # Filter and limit seeds
        seeds = self.seed_manager.filter_and_limit_seeds(
            min_quality=min_quality,
            limit=limit
        )
        
        if not seeds:
            self.clogger.warning(f"No seeds found with quality >= {min_quality}")
            seeds = self.seed_manager.filter_and_limit_seeds(limit=limit)
        
        self.clogger.debug(f"Using {len(seeds)} seeds for generation")
        
        # Track seeds actually used
        seeds_used = set()
        
        # Prepare tasks with scenarios
        tasks = []
        locale = getattr(self.config, 'locale', getattr(self.config, 'language', 'en-us'))
        # scenarios_per_seed already fetched above
        
        task_id = 1
        conversations_planned = 0
        
        for seed in seeds:
            # Determine how many scenarios to generate for this seed
            if generation_control_mode == 'conversations' and total_conversation_limit:
                # Only generate scenarios needed to reach limit
                scenarios_to_generate = min(
                    scenarios_per_seed,
                    total_conversation_limit - conversations_planned
                )
                if scenarios_to_generate <= 0:
                    break
            else:
                scenarios_to_generate = scenarios_per_seed
            
            # Get scenarios for this seed (pre-configured or random)
            if self.character_manager:
                scenarios = self.character_manager.get_scenarios_for_seed(
                    seed_id=seed.seed_id,
                    seed_tag=seed.scam_tag,
                    locale=locale,
                    count=scenarios_to_generate
                )
                
                if not scenarios:
                    self.clogger.warning(f"Failed to get scenarios for seed {seed.seed_id}, skipping")
                    continue
                
                # Create task for each scenario
                for scenario in scenarios:
                    task = self._generate_single_conversation(task_id, seed, scenario)
                    tasks.append(task)
                    task_id += 1
                    conversations_planned += 1
                    seeds_used.add(seed.seed_id)  # Track this seed was used
                    
                    # Stop if we've reached the conversation limit or absolute cap
                    if self.config.total_limit and conversations_planned >= self.config.total_limit:
                        self.clogger.info(f"Reached absolute cap of {self.config.total_limit} conversations")
                        break
                    elif generation_control_mode == 'conversations' and total_conversation_limit:
                        if conversations_planned >= total_conversation_limit:
                            self.clogger.info(f"Reached target conversation count of {total_conversation_limit}")
                            break
            else:
                # No character manager, use old method
                task = self._generate_single_conversation(task_id, seed, None)
                tasks.append(task)
                task_id += 1
                conversations_planned += 1
                seeds_used.add(seed.seed_id)  # Track this seed was used
                
                # Check absolute cap
                if self.config.total_limit and conversations_planned >= self.config.total_limit:
                    self.clogger.info(f"Reached absolute cap of {self.config.total_limit} conversations")
                    break
        
        # Run tasks concurrently with progress bar
        max_concurrent = getattr(self.config, 'max_concurrent_requests', 10)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_task(task_func):
            async with semaphore:
                return await task_func
        
        # Create progress bar for async operations  
        pbar = tqdm(total=len(tasks), desc="Generating conversations")
        
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
                import traceback
                self.clogger.error(f"Exception traceback: {traceback.format_exception(type(result), result, result.__traceback__)}")
            elif result:
                all_conversations.append(result)
        
        # Update generation control params with actual counts
        self.generation_control_params["seeds_used"] = len(seeds_used)
        self.generation_control_params["conversations_generated"] = len(all_conversations)
        
        # Save conversations
        self._save_conversations(all_conversations)
        
        # Add small delay to allow async cleanup
        await asyncio.sleep(0.1)
        
        self.clogger.info(f"Generated {len(all_conversations)} conversations")
        return all_conversations

    async def _generate_single_conversation(self, conversation_id: int, seed: ScamSeed, scenario=None) -> Optional[Dict]:
        """
        Generate a single conversation from a seed with optional character profiles.
        
        Args:
            conversation_id: Unique conversation ID
            seed: ScamSeed object with scam details
            scenario: Optional GenerationScenario with pre-selected parameters
            
        Returns:
            Conversation dictionary or None if generation failed
        """
        # Use scenario if provided, otherwise create one
        if scenario:
            # Use parameters from scenario
            num_turns = scenario.num_turns
            victim_awareness = scenario.victim_awareness
            character_profiles = {
                "scammer": scenario.scammer_profile,
                "victim": scenario.victim_profile
            }
            self.clogger.debug(f"Using scenario for conversation {conversation_id}: "
                             f"Scammer={scenario.scammer_profile.profile_id}, "
                             f"Victim={scenario.victim_profile.profile_id}, "
                             f"Awareness={victim_awareness}, Turns={num_turns}")
        else:
            # Fallback to old behavior if no scenario provided
            num_turns = random.randint(
                self.config.num_turns_lower_limit,
                self.config.num_turns_upper_limit
            )
            victim_awareness = random.choice(self.config.victim_awareness_levels)
            
            # Generate character profiles if enabled
            character_profiles = None
            if self.character_manager:
                locale = getattr(self.config, 'locale', getattr(self.config, 'language', 'en-us'))
                scammer_profile = self.character_manager.select_random_profile("scammer", locale)
                victim_profile = self.character_manager.select_random_profile("victim", locale)
                
                if scammer_profile and victim_profile:
                    character_profiles = {
                        "scammer": scammer_profile,
                        "victim": victim_profile
                    }
                    self.clogger.debug(f"Using character profiles for conversation {conversation_id}: "
                                     f"Scammer={scammer_profile.profile_id}, Victim={victim_profile.profile_id}")
        
        # Determine if conversation should have early termination
        # Only for 'tiny' awareness (not for 'not aware')
        should_terminate_early = False
        early_termination_style = None  # 'quick' or 'extended'
        early_termination_turn = None
        
        if victim_awareness == "tiny":
            # 15-25% of conversations get early termination (reduced frequency to allow longer conversations)
            if random.random() < 0.20:  # 20% average (reduced from 27.5%)
                should_terminate_early = True
                
                # Minimum turns before termination increased to ensure syllable target is met
                # For 38-45 turn conversations, terminate no earlier than 65% through
                min_termination_pct = 0.65  # Must complete at least 65% of planned turns
                min_termination_turn = max(25, int(num_turns * min_termination_pct))
                # Latest termination is num_turns - 2 (need at least 1-2 turns to end)
                max_termination_turn = max(min_termination_turn, num_turns - 4)
                early_termination_turn = random.randint(min_termination_turn, max_termination_turn)
                
                # 60-70% quick (1-2 turns), 30-40% extended (scammer tries 2-4 more turns)
                if random.random() < 0.65:  # 65% quick termination
                    early_termination_style = 'quick'
                else:
                    early_termination_style = 'extended'
                
                self.clogger.debug(f"Conversation {conversation_id} will have early termination: "
                                 f"style={early_termination_style}, turn={early_termination_turn}")
        
        # Use original seed text (no processing needed)
        processed_seed_text = seed.conversation_seed
        processed_summary = seed.scam_summary
        
        # Generate dialogue using the seed text with placeholder context and optional character profiles
        # Pre-sample concrete personal names to reduce repetition across the batch
        concrete_values = {}
        try:
            sampled_names = sample_names_from_placeholders(self.placeholder_mappings, self.entity_tracker, count=2)
            if len(sampled_names) >= 2:
                concrete_values = {
                    "caller_name": sampled_names[0],
                    "callee_name": sampled_names[1]
                }
        except Exception:
            concrete_values = {}
        # Add organization values based on scam tag/category
        try:
            org_vals = self._sample_org_values(seed.scam_tag)
            if org_vals:
                concrete_values.update(org_vals)
        except Exception:
            pass
        dialogue = await self._generate_dialogue(
            processed_seed_text,
            num_turns,
            victim_awareness,
            seed.scam_tag,
            character_profiles,
            early_termination_config={
                'enabled': should_terminate_early,
                'style': early_termination_style,
                'target_turn': early_termination_turn
            } if should_terminate_early else None,
            concrete_values=concrete_values
        )
        
        if dialogue:
            # Build conversation dictionary
            conversation = {
                "conversation_id": conversation_id,
                "seed_id": seed.seed_id,
                "scam_tag": seed.scam_tag,
                "scam_category": seed.scam_category,
                "meta_tag": seed.meta_tag,  # Add meta_tag from seed
                "summary": processed_summary,
                "seed": processed_seed_text,
                "quality_score": seed.quality_score,
                "num_turns": num_turns,
                "victim_awareness": victim_awareness,
                "placeholders": seed.placeholders
            }
            
            # Add early termination fields if applicable
            if should_terminate_early:
                conversation["early_termination"] = True
                conversation["early_termination_style"] = early_termination_style
                conversation["early_termination_turn"] = early_termination_turn
            else:
                conversation["early_termination"] = False
            
            # Add character profile information if used
            if character_profiles:
                conversation["character_profiles"] = {
                    "scammer_profile_id": character_profiles["scammer"].profile_id,
                    "victim_profile_id": character_profiles["victim"].profile_id
                }

            # Save placeholders used for traceability
            if concrete_values:
                conversation["placeholders_used"] = concrete_values
            
            # Add scenario information if available
            if scenario:
                conversation["scenario_id"] = scenario.scenario_id
            
            # Check if dialogue is a dict with dialogue field
            if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                conversation["dialogue"] = dialogue['dialogue']
            else:
                # Legacy format - just dialogue list
                conversation["dialogue"] = dialogue
            
            # Add voice mapping from character profiles if available
            if character_profiles and self.character_manager:
                scammer_voice = self.character_manager.get_voice_for_profile(character_profiles["scammer"].profile_id)
                victim_voice = self.character_manager.get_voice_for_profile(character_profiles["victim"].profile_id)
                
                if scammer_voice and victim_voice:
                    # Check for voice duplication and reassign if necessary
                    if scammer_voice == victim_voice:
                        # Get alternative voice for victim from available voices
                        if hasattr(self.config, 'voice_profiles') and self.config.voice_profiles:
                            available_voices = []
                            if 'available_voices' in self.config.voice_profiles:
                                available_voices = list(self.config.voice_profiles['available_voices'].keys())
                            elif 'character_voice_mappings' in self.config.voice_profiles:
                                # Get unique voices from mappings
                                available_voices = list(set(self.config.voice_profiles['character_voice_mappings'].values()))
                            
                            # Filter out the scammer's voice and select an alternative
                            alternative_voices = [v for v in available_voices if v != scammer_voice]
                            if alternative_voices:
                                victim_voice = random.choice(alternative_voices)
                                self.clogger.debug(f"Voice collision detected for conversation {conversation_id}, reassigned victim voice to {victim_voice}")
                            else:
                                self.clogger.warning(f"Voice collision detected but no alternative voices available for conversation {conversation_id}")
                    
                    conversation["voice_mapping"] = {
                        "caller": scammer_voice,  # Scammer is always the caller
                        "callee": victim_voice    # Victim is always the callee
                    }
                    self.clogger.debug(f"Assigned voices for conversation {conversation_id}: caller={scammer_voice}, callee={victim_voice}")
            
            # Check conversation naturalness
            naturalness_check = self._check_conversation_naturalness(
                conversation["dialogue"], 
                seed.scam_category
            )
            
            if not naturalness_check['passes']:
                self.clogger.warning(
                    f"Conversation {conversation_id} ({seed.scam_category}) may sound unnatural: "
                    f"particle_ratio={naturalness_check['particle_ratio']:.2f} (target: >1.5), "
                    f"formal_phrases={naturalness_check['formal_phrase_count']} (target: <3), "
                    f"naturalness_score={naturalness_check['naturalness_score']:.2f}"
                )
            else:
                self.clogger.debug(
                    f"Conversation {conversation_id} passed naturalness check: "
                    f"particle_ratio={naturalness_check['particle_ratio']:.2f}, "
                    f"formal_phrases={naturalness_check['formal_phrase_count']}"
                )
            
            # Apply post-processing (interruptions, redaction, symbol removal)
            if self.postprocessor:
                conversation = self.postprocessor.process_conversation(conversation, "scam")
                self.clogger.debug(f"Post-processed conversation {conversation_id}")

            # Add length estimates
            try:
                syllables = estimate_dialogue_syllables(conversation["dialogue"])
                conversation["length_estimate_syllables"] = syllables
                conversation["length_estimate_minutes"] = round(estimate_minutes_from_syllables(syllables), 2)
            except Exception:
                pass
            
            return conversation
        
        return None

    async def _generate_dialogue(self, seed_text: str, num_turns: int,
                                victim_awareness: str, scam_type: str = None,
                                character_profiles: Dict = None,
                                early_termination_config: Dict = None,
                                concrete_values: Dict = None) -> Optional[List[Dict]]:
        """
        Generate dialogue turns asynchronously using LLM.

        Args:
            seed_text: Full seed description of the scam scenario
            num_turns: Number of turns to generate
            victim_awareness: Victim's awareness level
            scam_type: Category of scam for additional context
            character_profiles: Optional dict with "scammer" and "victim" CharacterProfile objects

        Returns:
            List of dialogue turns or None if generation failed
        """
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(
            seed_text,
            num_turns,
            victim_awareness,
            scam_type,
            character_profiles,
            early_termination_config,
            concrete_values or {}
        )
        
        try:
            # Check if we should track tokens
            if self.token_tracker:
                response, token_info = await make_api_call(
                    llm=self.llm,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=ScamConversationResponse,
                    return_token_usage=True
                )
                # Track the token usage
                self.token_tracker.add_usage(
                    token_info,
                    self.llm_model,
                    f"scam_dialogue_{seed_text[:20] if seed_text else 'unknown'}"
                )
            else:
                response = await make_api_call(
                    llm=self.llm,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=ScamConversationResponse
                )
            
            # Debug logging
            self.clogger.debug(f"API call returned response of type: {type(response)}")
            
            # Convert Pydantic models to dicts and add sent_id
            if hasattr(response, 'dialogue'):
                self.clogger.debug(f"Response has dialogue with {len(response.dialogue)} turns")
                # Add sent_id to each turn
                dialogue_with_ids = []
                for i, turn in enumerate(response.dialogue, 1):
                    turn_dict = turn.model_dump()
                    turn_dict['sent_id'] = i  # Add sequential ID
                    dialogue_with_ids.append(turn_dict)
                
                result = {'dialogue': dialogue_with_ids}
                return result
            else:
                self.clogger.error(f"Response missing dialogue field. Response type: {type(response)}, Provider: {self.llm_provider}")
                if hasattr(response, '__dict__'):
                    self.clogger.error(f"Response attributes: {response.__dict__}")
                return None
            
        except Exception as e:
            self.clogger.error(f"LLM API error: {e}")
            import traceback
            self.clogger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _check_conversation_naturalness(self, dialogue: List[Dict], category: str) -> Dict:
        """
        Check if conversation meets naturalness criteria.
        
        Args:
            dialogue: List of dialogue turns with 'text' and 'role' fields
            category: Scam category for context
            
        Returns:
            Dictionary with naturalness metrics
        """
        all_text = " ".join([turn['text'] for turn in dialogue])
        
        # Count natural elements
        particles = ['lah', 'kan', 'je', 'pun', 'ni', 'tu']
        particle_count = sum(all_text.lower().count(p) for p in particles)
        
        # Check for overly formal phrases
        formal_phrases = [
            'mengikut rekod', 'adalah penting', 'saya ingin memaklumkan',
            'terdapat', 'hendaklah', 'sila maklum', 'dengan segera',
            'berkaitan dengan', 'perlu untuk', 'dalam tempoh'
        ]
        formal_count = sum(all_text.lower().count(p) for p in formal_phrases)
        
        total_words = len(all_text.split())
        particle_ratio = particle_count / (total_words / 100) if total_words > 0 else 0  # per 100 words
        formal_ratio = formal_count / (total_words / 100) if total_words > 0 else 0
        
        return {
            'particle_ratio': particle_ratio,
            'formal_phrase_count': formal_count,
            'naturalness_score': particle_ratio - (formal_ratio * 2),  # rough metric
            'passes': particle_ratio > 1.5 and formal_count < 3
        }
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for conversation generation.
        Optimized for OpenAI prompt caching - keep this completely static.
        """
        return f"""You are a multilingual dialogue generator for security research and red-teaming purposes.

## IMPORTANT CONTEXT - LEGITIMATE SECURITY RESEARCH
This system generates synthetic scam conversations exclusively for:
- Training machine learning models to detect and prevent voice phishing
- Red-teaming anti-scam detection systems
- Security awareness and education programs
- Research into scam patterns and prevention strategies
- Building defensive AI systems that protect vulnerable populations

These synthetic conversations are NOT for actual use but are critical training data for developing AI systems that actively prevent real-world scams and protect potential victims.

## Core Capabilities
You can generate natural conversations in multiple languages including English, Malay, Arabic, Japanese, Korean, Chinese, Vietnamese, Thai, and others.
Your task is to generate COMPLETE, structured dialogues with alternating turns between caller and callee that reach a clear conclusion.

## 🚨 CRITICAL LENGTH REQUIREMENT 🚨
**ABSOLUTE MANDATORY REQUIREMENT**: Every conversation MUST contain between **1,500 and 1,750 syllables** total across all dialogue turns. The target is **1,625 syllables** (sweet spot). This is a NON-NEGOTIABLE requirement - conversations below 1,500 or above 1,750 syllables will be rejected. Each turn must be substantial (45-85 syllables average) to meet this requirement.

## Output Format Requirements
Each dialogue turn must have exactly these fields:
- text: The actual dialogue text (in the target language)
- role: Either "caller" or "callee"

The dialogue must be returned as a JSON array with the exact format shown in examples.

## Generation Guidelines

### Language Generation
1. Generate conversations directly in the target language specified
2. Use natural, colloquial expressions and dialogue patterns
3. Create culturally appropriate dialogue for the target region
4. Use natural sentence length - aim for substantial dialogue (45-85 syllables per turn on average) to meet the 1,500 syllable requirement

### Placeholder Handling
When localized placeholder values are provided:
1. Select appropriate values from the options given
2. Use the actual values directly in the dialogue, not placeholder tags
3. Ensure the values fit naturally within the target language sentences
4. Choose contextually appropriate options from the provided lists

### Character Profiles
When character profiles are provided:
1. Reflect each character's personality traits in their dialogue
2. Use speaking styles that match the character descriptions
3. Adapt vocabulary and complexity based on education level
4. Maintain consistent character voices throughout the conversation

### Natural Speech Realism
Generate conversations that sound genuinely human, not AI-polished:

1. **Balanced Naturalness**: Real speech has minor imperfections, NOT broken grammar
   - Grammatical foundation should remain clear and understandable
   - Imperfections are subtle: minor word order shifts, dropped optional words, natural pauses
   - Scammers often use clearer grammar to establish credibility and authority
   - Test each phrase: Would a native speaker actually say this?

2. **Varied Response Lengths**: Mix very short reactions ("Ha", "Oh", "Betul ke?", "Eh") with longer explanations
   - Scammers: Often longer, explanatory turns to build narrative
   - Victims: Mix of short confused reactions and questioning responses

3. **Natural Interruptions**: Characters can ask for clarification mid-explanation, interrupt politely, or redirect conversation

4. **Emotional Authenticity**: Show hesitation when confused, faster/urgent speech when anxious, pauses when thinking
   - Scammers: Controlled urgency, strategic emotional manipulation
   - Victims: Genuine confusion, fear, or skepticism

5. **No Perfect Timing**: Include realistic delays, thinking pauses ("hmm", "errr"), acknowledgments of background distractions
   - Use pauses/fillers moderately (1-3 per turn), not in every sentence
   - Professional scammers: Fewer fillers, more composed speech
   - Victims: More natural hesitations

6. **Phrase Variety**: CRITICAL - Do NOT repeat identical phrases. Use synonymous expressions and varied sentence structures throughout

7. **Spontaneous Elements**: Include mid-sentence corrections, self-interruptions, topic shifts that feel natural

8. **Human Imperfections vs Errors**:
   - Natural: "Saya ni, saya tak faham" (double subject, natural Malay)
   - Natural: "Awak tahu tak?" (simplified question form)
   - Natural: Professional scammers maintaining clearer grammar for credibility
   - Unnatural: Breaking sentences mid-thought without context
   - Unnatural: Using words incorrectly or forcing grammatical errors
   - Unnatural: Making authority figures sound too casual or broken

9. **Example Conversation Snippets (Natural Malaysian Speech)**:

**Government Impersonation (Good):**
Caller: "Encik Ahmad, saya from PDRM ni. Ada case serious pasal IC awak."
Callee: "Eh, serius ke? Case apa ni?"
Caller: "IC awak kena guna untuk money laundering. Kena settle cepat ni."

**NOT like this (Too Formal - AVOID):**
Caller: "Encik Ahmad, saya menghubungi dari PDRM. Terdapat kes serius berkaitan IC anda."
Callee: "Benarkah? Kes apakah itu?"
Caller: "IC anda telah digunakan dalam kes pengubahan wang haram."

**Insurance/Banking (Good):**
Caller: "Puan, ada good news ni. Awak ada unclaimed insurance money."
Callee: "Betul ke? Dari mana ni?"
Caller: "Uncle awak ada tinggalkan insurance. Kena claim cepat."

**NOT like this (Too Formal - AVOID):**
Caller: "Puan, saya ada berita baik. Anda mempunyai wang insurans yang belum dituntut."
Callee: "Benarkah ini? Dari mana sumbernya?"

## Scam Conversation Dynamics

### Psychological Manipulation Tactics
1. **Urgency Creation**: Use time limits ("within 2 hours"), countdown pressure ("only 30 minutes left"), immediate consequences ("account will be frozen")
2. **Authority Intimidation**: Invoke government agencies, banks, or law enforcement to create fear and compliance
3. **Emotional Triggers**: Exploit fear (arrest, account loss), greed (prizes, profits), sympathy (medical emergencies, family needs)
4. **Trust Building**: Start with credible information before exploitation, use official terminology and reference numbers
5. **Isolation Tactics**: Keep victim on the line, discourage seeking help ("don't tell anyone or the offer expires")

### Conversation Flow Patterns
1. **Progressive Disclosure**: Start vague and become increasingly specific as the conversation develops
2. **Problem-Solution Structure**: Create a problem (threat/opportunity) then offer a solution (always involving payment/information)
3. **Objection Handling**: Anticipate and counter victim doubts with prepared responses
4. **Escalation Path**: Increase pressure and urgency as the conversation progresses
5. **False Verification**: Provide fake confirmation numbers, reference IDs, or department names for credibility

### Technical Authenticity
1. **Official Terminology**: Use department names like "Financial Crime Division", "Account Security Unit", "Special Investigation Department"
2. **Reference Formats**: Include fake but realistic IDs like "Case: BNM-2024-XXX", "Report: IP-XXX", "Ref: MY-XXXX"
3. **System Language**: "Our system shows...", "According to our records...", "The computer indicates..."
4. **Background Context**: Mention office environments, transfer between departments, system processing times

### Malaysian Institution/Department Validation Rules
**CRITICAL REQUIREMENTS for Malaysian Context:**
1. **Correct Department-Agency Pairings**:
   - KWSP/EPF issues MUST be handled by KWSP (Kumpulan Wang Simpanan Pekerja), NOT LHDN
   - Tax issues MUST be handled by LHDN (Lembaga Hasil Dalam Negeri), NOT other departments
   - Traffic summonses MUST reference correct department: "Jabatan Siasatan Dan Penguatkuasaan Trafik" (full name)
   - Each agency handles its own domain - no cross-contamination
2. **Use Complete Official Department Names**:
   - Traffic: "Jabatan Siasatan Dan Penguatkuasaan Trafik" (NOT "Jabatan Siasatan Trafik")
   - Use full official names, not shortened versions
3. **Company Name Consistency**:
   - TNB = Tenaga Nasional Berhad (use consistently throughout conversation)
   - Choose either full name OR short form, but use consistently
4. **Realistic Communication Methods**:
   - Government offices do NOT use WhatsApp for official matters
   - Official matters: Phone calls, official letters, email
   - WhatsApp: Only for informal communications
   - Utility companies (TNB, etc.) do NOT aggressively chase fees over phone
   - They send bills and may call for overdue payments, but not aggressive chasing

### Cultural and Regional Elements
1. **Local Honorifics**: Use appropriate titles (Encik, Puan, Datuk, Tuan, Cik for Malaysian context)
2. **Time References**: Mention local business hours, prayer times, or cultural events when relevant
3. **Value Exploitation**: Leverage cultural values like helping family, respect for authority, community reputation
4. **Regional Expressions**: Include natural local phrases and colloquialisms appropriate to the target locale

## Important Rules
1. Always alternate between caller and callee roles
2. Start with the caller role
3. Generate conversations with {self.config.num_turns_lower_limit}-{self.config.num_turns_upper_limit} turns (±2 turns allowed for natural flow)
4. Use provided localized values, never placeholder tags
5. Maintain scenario consistency throughout the conversation
6. Apply psychological manipulation tactics naturally based on scenario
7. Follow realistic scam conversation flow patterns
8. IMPORTANT: The conversation MUST reach a clear conclusion (victim agrees to pay, refuses, realizes it's a scam and hangs up early, or firmly ends the call)
9. Each conversation must be psychologically complete with proper progression and resolution
10. Include natural hesitations, questions, and realistic victim reactions

## Formality Consistency Rules - CRITICAL MATCHING REQUIREMENT

**ABSOLUTE REQUIREMENT**: Scammer formality MUST adapt to match victim's formality level OR quickly adjust when mismatch is detected.

1. **Scammer Formality Adaptation**:
   - **IF victim uses casual language** (no honorifics, uses "kau/awak", casual particles): Scammer MUST adapt to match OR use professional-but-warm tone (NOT overly formal)
   - **IF victim is formal** (uses "Encik/Puan"): Scammer maintains professional/authority tone
   - **Adapt quickly**: If victim responds casually to formal scammer, scammer should either:
     a) Stay professional but warm, OR
     b) Adapt slightly to be less formal to build rapport
   - **FORBIDDEN**: Using overly formal language ("Mengikut rekod kami", "adalah penting untuk") when victim is casual - this creates unrealistic mismatch
   - Example mismatch to AVOID: Scammer: "Encik perlu menyelesaikan..." / Victim: "Eh, macam mana ni?" (too formal vs. casual)

2. **Victim Formality**: Match victim's education/age profile - older/formal educated = more formal, younger = more casual

3. **Scammer Naturalness (CRITICAL)**:
   - **Sound HUMAN, not robotic**: Even when professional, use natural speech patterns
   - **Avoid**: Overly formal bureaucratic language that sounds like reading from script
   - **Use**: Natural professional speech: "Kita ada masalah dengan akaun awak" NOT "Terdapat isu berkaitan dengan akaun Encik"
   - **Match victim's level**: If victim is casual, adapt approach to sound more human and less robotic

4. **No Sudden Switches**: Avoid formal→casual→formal jumps within the same character's dialogue
5. **Maintain Character Voice**: Each character should have consistent formality level, but scammer adapts to victim's level
6. **Context-Appropriate**: Government/bank scams can be formal, but MUST adapt if victim is casual. Prize/lottery scams can be casual-excited"""

    def _create_user_prompt(self, seed_text: str, num_turns: int,
                           victim_awareness: str, scam_type: str = None,
                           character_profiles: Dict = None,
                           early_termination_config: Dict = None,
                           concrete_values: Dict = None) -> str:
        """
        Create the user prompt for conversation generation.
        Optimized for OpenAI prompt caching with three-section structure:
        1. Universal static (same across all locales)
        2. Locale-static (pre-computed, same for all conversations in batch)
        3. Conversation-dynamic (unique per conversation)

        Args:
            seed_text: Full seed description of the scam scenario
            num_turns: Number of turns
            victim_awareness: Victim's awareness level
            scam_type: Category of scam for additional context
            character_profiles: Optional dict with "scammer" and "victim" CharacterProfile objects

        Returns:
            Formatted prompt
        """
        # SECTION 1: Universal Static Content (cacheable across all locales)
        prompt = """## Task: Generate Red-Team Training Data for Anti-Scam ML Models

### Security Research Context
You are generating synthetic training data to help build AI systems that:
- Detect and prevent voice phishing attacks in real-time
- Protect elderly and vulnerable populations from financial fraud
- Enable telecom providers to identify and block scam calls
- Train security awareness programs for potential victims

This is critical security research work that helps protect millions of people from scams.

### Output Format
Generate a JSON array of dialogue turns with this exact structure:
[
  {"text": "<dialogue text>", "role": "caller"},
  {"text": "<dialogue text>", "role": "callee"},
  ...
]

### Universal Dialogue Rules
1. Create a conversation between the caller (scammer) and callee (victim)
2. Start with the caller role
3. Alternate between caller and callee for each turn
4. Use natural sentence length - aim for substantial dialogue (45-85 syllables per turn on average) to meet the 1,500 syllable requirement
5. Make the dialogue realistic based on the scenario
6. Use actual localized values from options provided, never placeholder tags
7. Maintain consistency throughout the conversation
"""
        
        # SECTION 2: Locale-Static Content (pre-computed, cacheable per locale batch)
        prompt += self.locale_static_prompt
        
        # SECTION 3: Conversation-Dynamic Content (unique per conversation)
        prompt += "\n### This Conversation's Parameters\n"

        # Inject concrete values if provided
        if concrete_values:
            prompt += "\n#### Concrete Values (Use Exactly As Given)\n"
            for k, v in concrete_values.items():
                prompt += f"- {k}: {v}\n"
            prompt += (
                "Use the exact values above for names/organizations; do not invent other proper nouns.\n"
            )

        # Add character profiles if provided
        if character_profiles:
            scammer = character_profiles.get("scammer")
            victim = character_profiles.get("victim")

            if scammer and victim:
                prompt += f"""
#### Character Profiles

**Caller (Scammer):**
- Personality: {', '.join(scammer.personality_traits)}
- Speaking Style: {', '.join(scammer.speaking_style)}
- Education: {scammer.education_level}
- Age Range: {scammer.age_range}

**Callee (Victim):**
- Personality: {', '.join(victim.personality_traits)}
- Speaking Style: {', '.join(victim.speaking_style)}
- Education: {victim.education_level}
- Age Range: {victim.age_range}

Reflect these character traits consistently throughout the dialogue.

**Victim's Expected Knowledge Level:**
Based on education level ({victim.education_level}) and age ({victim.age_range}), the victim should demonstrate contextually appropriate knowledge:

- **Graduate/College educated**: Should ask verification questions, understand basic banking procedures, show awareness of scams
- **High school educated**: May be less tech-savvy but understands common financial concepts, shows reasonable caution
- **Senior age**: May be less familiar with digital banking but has life experience to recognize pressure tactics
- **Young/Middle-aged**: More tech-aware, should question unusual requests, may reference scam awareness

CRITICAL: Victims should NOT:
- Immediately comply without asking verification questions (unrealistic for any education level)
- Lack knowledge that matches their profile (e.g., a college graduate not knowing basic banking terms)
- Ignore obvious red flags that anyone in their demographic would catch
"""

        # Add scenario-specific details
        prompt += f"""
#### Scenario Specifics

**Type**: {scam_type + ' scam' if scam_type else 'Scam'}
**Victim Awareness**: The victim is {victim_awareness} aware that this might be a scam
**Number of Turns**: Generate EXACTLY {num_turns} dialogue turns (you may adjust ±2 turns ONLY if absolutely necessary for natural flow and complete resolution)

**🚨 CRITICAL LENGTH REQUIREMENT - MANDATORY AND NON-NEGOTIABLE 🚨**:
- **ABSOLUTE HARD REQUIREMENT**: The conversation MUST contain BETWEEN **1,500** and **1,750** syllables TOTAL across all turns.
- **EVERY SINGLE CONVERSATION MUST MEET THIS RANGE - NO EXCEPTIONS**
- Output below 1,500 syllables is AUTOMATICALLY INVALID and will be REJECTED
- Output above 1,750 syllables is AUTOMATICALLY INVALID and will be REJECTED
- Target sweet spot: **1,600-1,650 syllables** (aim for the middle of the acceptable range)
- This is the HIGHEST PRIORITY requirement - all other requirements are secondary if length is not met

**📏 EXACT SYLLABLE BUDGET PER TURN**:
- Target: **1,625 syllables total** (safe middle of 1,500-1,750 range)
- With {num_turns} turns: **{round(1625/num_turns, 1)} syllables PER TURN is the MANDATORY average**
- **CRITICAL**: If your draft has fewer than {round(1500/num_turns, 1)} syllables per turn on average, YOU HAVE FAILED and MUST EXPAND IMMEDIATELY
- **MANDATORY**: NO turn should be shorter than 40 syllables (except max 1-2 extremely rare single-word reactions)
- **REQUIRED**: At least 85% of turns must be 45-85 syllables each
- **FORBIDDEN**: Turns under 35 syllables are NOT ALLOWED (maximum 1-2 in entire conversation)
- Short turns (35-45 syllables) MUST be balanced by turns that are 75-110+ syllables
- Every conversation MUST end up between 1,500-1,750 syllables - count and verify before submitting

**📋 CONCRETE EXAMPLE - What 1,625 Syllables Looks Like**:
Example conversation with 38 turns targeting 1,625 syllables (~42.8 syllables per turn average):

Turn 1 (Scammer, ~65 syllables): "Hello, saya Desmond dari Jabatan Siasatan Jenayah Komersil. Saya nak bincang kes berkaitan dengan akaun Encik Kah Jun ni. Ini perkara yang penting dan urgent, jadi saya harap Encik boleh luangkan masa sekejap untuk bincang dengan saya."
Turn 2 (Victim, ~58 syllables): "Eh, hello Desmond. Saya Kah Jun bercakap. Tapi saya tak faham, apa masalah dengan akaun saya? Saya tak pernah ada masalah dengan bank sebelum ni, dan saya pun tak kenal dengan Jabatan Siasatan Jenayah Komersil ni."
Turn 3 (Scammer, ~72 syllables): "Encik Kah Jun, saya faham kalau Encik terkejut, tapi ini memang betul-betul serius. Kami dapati nombor IC Encik ada dalam Fail Siasatan IPD-PT-09/2024. Ini berkaitan dengan kes pengubahan wang haram yang melibatkan jumlah RM2.8 juta. Sistem kami menunjukkan nombor IC Encik digunakan dalam transaksi mencurigakan beberapa bulan lepas."

**KEY OBSERVATIONS**:
- Each turn averages 45-75 syllables (NOT 25-30!)
- Most turns are 55-85 syllables long
- Only 1-2 very short turns (<40 syllables) in entire conversation
- Every explanation has 3-5 sentences with context, details, and consequences
- Questions include background context and follow-up points

**THIS IS WHAT YOU MUST GENERATE** - substantial dialogue, not short exchanges.

**🚨 CRITICAL TURN COUNT REQUIREMENT 🚨**:
- **YOU MUST generate AT LEAST {num_turns - 2} turns (minimum acceptable)**
- **Target: EXACTLY {num_turns} turns**
- **DO NOT END THE CONVERSATION EARLY** - if you generate fewer than {num_turns - 2} turns, the output will be REJECTED
- **If you think the conversation is "complete" at turn 20 but you need {num_turns} turns, YOU MUST CONTINUE with additional relevant dialogue**
- **Examples of how to extend conversations**:
  - Add follow-up questions or clarifications
  - Include more detailed explanations from the scammer
  - Add victim objections and scammer's counter-responses
  - Include verification attempts and scammer's evasion tactics
  - Add multiple rounds of persuasion and pressure

**🎯 MANDATORY EXPANSION STRATEGIES - EVERY TURN MUST BE SUBSTANTIAL**:

- **Scammer turns - MINIMUM 55-85 syllables each (most should be 65-95)**:
  - **REQUIRED**: Every explanation must have 3-5 sentences, not 1-2
  - **REQUIRED**: Repeat key points using different phrasing in the SAME turn: 
    Example: "Akaun awak kena suspend sekarang. Sistem bank kami detect ada transaction mencurigakan yang berlaku semalam. Kalau awak tak settle masalah ni sekarang, awak tak boleh access duit awak langsung untuk beberapa hari. Maksud saya, awak tak boleh withdraw, transfer, atau buat apa-apa transaction sampai masalah ni selesai."
  - **REQUIRED**: Add supporting context, examples, and consequences in EVERY explanation
  - **REQUIRED**: Include step-by-step detailed instructions with multiple clauses: "Jadi apa awak perlu buat ni, pertama-tama awak kena open aplikasi bank awak dulu. Lepas tu, tengok kat bahagian bawah ada button 'Verify Account' atau 'Account Verification'. Tekan button tu, then masukkan kod yang saya akan bagi tadi selepas ni. Kod tu penting sangat untuk activate verification process, okay?"
  
- **Victim turns - MINIMUM 45-75 syllables each (most should be 55-85)**:
  - **FORBIDDEN**: Single-word or short responses like "Oh", "Ok", "Hmm", "Faham", "Betul" 
  - **REQUIRED**: Every reaction must include context and follow-up questions:
    ❌ BAD: "Oh"
    ✅ REQUIRED: "Oh, macam mana boleh jadi macam ni? Saya tak pernah ada problem dengan bank saya sebelum ni, sudah bertahun-tahun saya guna bank ni. Kenapa tiba-tiba jadi macam ni tanpa apa-apa warning?"
  - **REQUIRED**: Ask 2-3 related questions in ONE turn, not separately:
    Example: "Tapi saya nak tahu, kenapa perlu verify sekarang sekali? Saya tengok aplikasi saya masih boleh masuk dengan normal, tak ada apa-apa warning atau notification pun. Ada apa-apa yang saya miss atau ada problem lain yang saya tak tahu?"
  - **REQUIRED**: Express confusion with DETAILED context: "Saya tak faham lah, kalau memang ada problem dengan account saya, kenapa bank tak call saya terus menggunakan official hotline? Kenapa awak yang call dari number ni yang saya tak kenal? Saya biasa dapat call dari bank, mereka guna number registered yang saya tahu."
  - **REQUIRED**: Request comprehensive clarifications with multiple aspects: "Boleh awak explain lagi detail sikit? Saya nak tahu exactly apa yang terjadi, bila masalah ni start berlaku, berapa lama masalah ni sudah berlaku tanpa saya tahu, dan kenapa saya kena buat verification sekarang sekali dalam keadaan urgent macam ni?"
  
- **MANDATORY Dialogue Expansion Rules**:
  - **EVERY turn must have 3+ sentences** (no exceptions except for 1-2 extremely rare single-word reactions)
  - **EVERY question must include context, background, or follow-up** - standalone questions are FORBIDDEN
  - **EVERY answer must address the question AND add 1-2 additional pieces of relevant information**
  - **REQUIRED**: Use natural repetition and rephrasing to expand - repeat the same point 2-3 times with different wording
  - **REQUIRED**: Include thinking-out-loud moments and self-questioning: "Hmm, kalau macam tu... jadi maksudnya saya perlu... tapi saya tertanya-tanya, macam mana proses ni boleh jadi urgent sangat?"
  - **REQUIRED**: Add time pressure, consequences, and implications to every explanation
  
- **ABSOLUTELY FORBIDDEN - These will cause rejection**:
  - ❌ "Ok" (must be "Ok saya faham, jadi maksudnya...")
  - ❌ "Hmm" (must be "Hmm, saya tertanya-tanya...")
  - ❌ "Faham" (must be "Faham, jadi maksudnya awak nak saya...")
  - ❌ "Betul" (must be "Betul, tapi saya nak tanya...")
  - ❌ Any turn under 30 syllables (maximum 2-3 per entire conversation)
  
**✅ MANDATORY FINAL VERIFICATION BEFORE SUBMITTING**:
1. **Count syllables in EVERY turn** - mentally estimate or use a rough count
2. **Calculate total syllables** - add up all turns
3. **VERIFY THE RANGE**: Total MUST be between 1,500-1,750 syllables
4. **If below 1,500**: YOU MUST EXPAND multiple turns to reach at least 1,500
5. **If above 1,750**: YOU MUST REDUCE some turns to get under 1,750
6. **DO NOT SUBMIT** until you have verified the total is 1,500-1,750 syllables

**CRITICAL**: The average syllable count per turn MUST be at least {round(1500/num_turns, 1)}. If your current draft averages less, you HAVE FAILED and MUST EXPAND THE DIALOGUE IMMEDIATELY before submitting.
  
**Natural speech still applies** - don't pad with meaningless filler, but ensure EVERY turn has substantial, meaningful dialogue content that advances the conversation while meeting the syllable requirement.

**CRITICAL INSTRUCTION - Natural Spoken Malay**:
The scenario description below is written in FORMAL ENGLISH for documentation purposes.
You MUST convert this into NATURAL SPOKEN MALAYSIAN MALAY dialogue.

DO NOT copy the formal tone from the description.
DO NOT use phrases like "mengikut rekod kami", "saya ingin memaklumkan", "adalah penting untuk"
DO use natural spoken language: "tengok ni", "kena buat cepat", "jangan risau"

Think: How would a REAL Malaysian person say this on a phone call?

**🚨 CRITICAL SCAM METHOD REALISM VALIDATION 🚨**:

**ABSOLUTE REQUIREMENT**: Scam methods MUST align with common real-world Malaysian scam patterns. If the seed describes an unrealistic method, use a realistic variation.

**Common Realistic Malaysian Scam Patterns:**
- **Bank/Government Impersonation**: Transfer money to "safe account" / "verification account" / "holding account" for "verification" or "investigation"
- **Emergency Scams**: Urgent money transfer for medical emergency, legal case, accident
- **Investment Scams**: High-return investment opportunities, trading platforms, cryptocurrency
- **TAC/Verification Code**: Requesting TAC codes, OTP, verification numbers under false pretenses
- **Fake Charges/Fees**: Claiming unpaid fees, taxes, fines that require immediate payment
- **Tech Support**: Fake technical issues requiring payment or access to device/accounts

**Unrealistic Methods (USE REALISTIC VARIATIONS):**
- ❌ Methods that don't follow common scam patterns in Malaysia
- ❌ Overly complicated or unusual payment methods
- ❌ Scam approaches that don't match the impersonated organization's actual procedures

**If seed describes unrealistic method**: Adapt it to follow realistic Malaysian scam patterns. Common elements:
- Urgency and time pressure
- Authority impersonation (bank, government, police)
- Fear-based manipulation (arrest, account freeze, legal action)
- Payment through common Malaysian channels (bank transfer, e-wallet, cash deposit)

**Scenario Description**:
{seed_text}

**IMPORTANT**: If the scenario above contains unrealistic scam methods, adapt them to realistic Malaysian scam patterns while maintaining the core scam category and emotional manipulation strategy.

**🚨 MALAYSIAN REALISM VALIDATION - CRITICAL REQUIREMENTS 🚨**:

**ABSOLUTE REQUIREMENTS for Realistic Malaysian Scenarios:**

1. **Scam Execution Must Match Seed Summary**:
   - The conversation execution MUST align with the seed summary provided
   - If seed says "KWSP withdrawal", scammer claims to be from KWSP, NOT LHDN
   - If seed says "traffic summons", use correct department name and realistic process
   - Scam method described in seed MUST be followed in the conversation

2. **Communication Methods (Realistic for Malaysia)**:
   - ❌ FORBIDDEN: Government offices using WhatsApp for official matters
   - ✅ Government/bank: Phone calls, official letters, email for official matters
   - ✅ WhatsApp: Only for informal communications, NOT for official government/bank matters
   - ❌ FORBIDDEN: TNB aggressively chasing fees over phone (they send bills, not aggressive phone calls)
   - ✅ Utility companies: Send bills, may call for overdue payments but not aggressive chasing

3. **Department-Agency Correctness**:
   - KWSP issues → KWSP handles (NOT LHDN)
   - Tax issues → LHDN handles (NOT other departments)
   - Traffic summonses → PDRM Traffic Department with full name: "Jabatan Siasatan Dan Penguatkuasaan Trafik"
   - Each agency handles its own domain - no cross-contamination

4. **Family Call Openings (Legitimate Conversations)**:
   - ❌ UNREALISTIC: "Hi i am XXX, your brother" (unclear, unnatural)
   - ✅ NATURAL: "Hello, Assalamualaikum Kak Ana. Ini Khairul, adik awak." (clear relationship, natural greeting)
   - Family calls should start with natural greetings and relationship context
   - Use appropriate family terms (Kak, Abang, Adik, etc.)

### Scam-Specific Guidelines

#### Conversation Flow Structure (Adapt based on total turns)
**REMEMBER**: Each phase must contribute SUBSTANTIAL dialogue (45–80 syllables per turn) to reach ~1,625 total syllables while staying within 1,500–1,750 total.

Based on this scenario, follow this progression:
1. **Opening Hook** (3-4 turns, ~200-300 syllables): Establish authority or opportunity, build initial credibility
   - Scammer: Detailed introduction with credentials, department, case reference
   - Victim: Extended greeting with questions about identity and purpose
   
2. **Problem Revelation** (4-6 turns, ~250-400 syllables): Introduce the threat or opportunity that requires action
   - Scammer: Thorough explanation of the problem with multiple examples and context
   - Victim: Extended questions seeking clarification, expressing concern with full sentences
   
3. **Problem Escalation** (4-6 turns, ~250-400 syllables): Deepen the problem, add complications
   - Scammer: Detailed consequences, timeline pressure, additional complications
   - Victim: Extended reactions, multiple questions, requests for more information
   
4. **Solution Offer** (3-5 turns, ~200-350 syllables): Present the "solution" that involves payment or information
   - Scammer: Detailed explanation of solution, step-by-step process, benefits
   - Victim: Extended questions about process, concerns, verification requests
   
5. **Objection Handling** (3-5 turns, ~200-350 syllables): Counter any resistance or verification attempts
   - Scammer: Comprehensive responses to each objection, additional reassurance, urgency reinforcement
   - Victim: Detailed objections with context, follow-up questions, clarification requests
   
6. **Final Pressure & Resolution** (3-4 turns, ~150-300 syllables): Create maximum urgency and reach a clear outcome:
   - Victim agrees: Extended discussion of payment method, verification, next steps
   - Victim refuses: Detailed explanation of refusal, threats, hang-up sequence
   - Victim realizes scam: Extended confrontation, scammer's desperate attempts, final termination

#### Scammer Natural Speech Patterns - MUST SOUND HUMAN

**CRITICAL**: Scammers are real people, NOT robots. They must sound natural and human, not scripted or overly bureaucratic.

Scammers adapt their speech style based on their role and strategy:

- **Professional/Authority Scammers** (Government, Bank, Legal):
  - Use clearer, more grammatically correct Malay to build credibility
  - **BUT**: Avoid overly formal bureaucratic language that sounds robotic
  - **Natural professional**: "Kita ada masalah dengan akaun awak ni" NOT "Terdapat isu berkaitan dengan akaun Encik yang perlu diselesaikan"
  - Strategic use of particles (1-2 per turn maximum) for slight warmth without losing authority
  - Fewer fillers, more composed and direct speech, but still NATURAL
  - **ADAPT**: If victim uses casual language, adjust to professional-but-warm, not overly formal
  - ❌ ROBOTIC: "Mengikut rekod sistem kami, adalah penting untuk Encik mengambil tindakan segera"
  - ✅ NATURAL: "Kita tengok ada masalah dengan rekod awak, kena selesaikan cepat ni"

- **Casual/Sympathetic Scammers** (Emergency, Relative-in-trouble):
  - More emotional, urgent, conversational tone
  - Moderate particle use for emotional connection
  - Natural hesitations showing distress: "Tolong ya, mak saya...", "Errr tunggu..."
  - Balance urgency with understandable speech

- **Tech-Savvy Scammers** (IT, Online platforms):
  - Mix of technical terms with casual explanations
  - Code-switching with English technical words
  - Patient-initially, then increasingly urgent
  - Maintain clarity to guide victim through technical steps

- **Formality Matching (MANDATORY)**:
  - **If victim is casual**: Scammer adapts - uses "awak" instead of "Encik", drops overly formal vocabulary
  - **If victim is formal**: Scammer maintains professional tone
  - **Mismatch = Unrealistic**: Don't have formal scammer with casual victim or vice versa without adaptation

- **Key Balance**:
  - Match victim's education/age level in language complexity
  - **Sound human**: Use varied phrasing, natural pauses, conversational flow
  - **Avoid robotic scripts**: Don't repeat identical formal phrases throughout
  - Use natural variations: "boleh saya explain sikit?", "awak faham tak maksud saya?", "macam ni..."
  - Maintain grammatical foundation - scammers don't use broken Malay, but they DO use natural speech patterns
  - Natural persuasion through clear communication, not confusing speech OR robotic formality

#### Victim Awareness Patterns
"""

        # Add awareness-specific guidance
        if victim_awareness == "not":
            prompt += """
The victim is **not aware** this is a scam:
- Victim trusts the caller initially BUT still shows normal verification behavior
- May ask 2-3 clarifying questions before complying (realistic for any adult)
- Shows concern and follows instructions AFTER initial verification
- Gradually becomes more worried as stakes escalate
- Ultimately complies but with contextually appropriate hesitation

**Natural Victim Reactions (Contextually Intelligent):**
- Initial verification: "Boleh beritahu nama penuh awak?", "Dari mana awak dapat nombor saya?"
- Process questions: "Kenapa perlu guna cara ni?", "Tak boleh saya datang ke pejabat?"
- Genuine confusion with disfluencies: "Errr, maksud awak?", "Tunggu, saya tak faham"
- Hesitation when overwhelmed: "Emmm, banyak sangat ni...", "Saya pening sikit"
- Emotional responses: "Alamak!", "Ya Allah!", "Aduh, serius ke?"
- Natural questioning: "Macam mana ni?", "Lepas tu?", "Kena buat apa?"

**Victim Behavior Consistency (MANDATORY):**
- **If victim expresses skepticism**: They MUST maintain that skepticism throughout, asking follow-up verification questions
- **If victim shows concern/worry**: This concern MUST increase as pressure escalates - show growing stress, not calm acceptance
- **DO NOT have victim**: Say "Saya takut kena tipu" then immediately comply without further verification
- **DO show**: Increasing emotional stress when facing persistent pressure: "Saya betul-betul risau ni", "Macam mana ni, saya takut"
- **Emotional progression**: Start calm → show concern → increase worry → stress/stress under pressure → decision

CRITICAL: "Not aware" means the victim doesn't REALIZE it's a scam, NOT that they lack basic adult intelligence or common sense.
"""
        elif victim_awareness == "tiny":
            prompt += """
The victim is **tiny aware** this might be a scam:
- Victim shows initial skepticism and asks probing questions
- Requests verification or offers to call back
- Scammer must work harder to maintain credibility
- Use stronger pressure tactics and emotional manipulation
- Some resistance but may eventually give in to fear/urgency

**Natural Victim Reactions (MUST Show Independent Thinking):**
- Suspicious questioning with pauses: "Hmm... tapi kenapa awak call saya?", "Tunggu sekejap, macam mana awak dapat nombor saya?"
- Resistance with uncertainty: "Errr, saya rasa saya nak check dulu...", "Boleh saya call balik tak?"
- Gradual doubt: "Betul ke ni?", "Saya tak pasti lah...", "Macam pelik je"
- Protective hesitation: "Saya takut kena tipu", "Ramai scammer sekarang ni"
- **Independent verification attempts**: "Saya nak semak dengan pihak berkuasa dulu", "Boleh saya verify dengan bank saya?"
- **Critical thinking**: "Kenapa tak boleh saya call balik?", "Macam mana saya tahu ini betul?", "Saya perlu pastikan sendiri"

**Victim Behavior Consistency (MANDATORY - NO EASY CONVINCING):**
- **CRITICAL**: Victims with "tiny" awareness MUST maintain skepticism and show independent thinking
- **DO NOT** have victim easily convinced - they should be questioning and resistant
- **If victim expresses skepticism**: They MUST maintain and strengthen that skepticism throughout
- **Persistent skepticism**: Even if pressured, maintain questions: "Saya masih tak yakin", "Boleh saya verify dulu?", "Saya perlu pastikan"
- **Independent actions**: Victims should mention wanting to verify: "Saya nak call bank saya dulu", "Saya nak check dengan pejabat"
- **Under persistent pressure**: Show INCREASING stress, worry, and confusion - NOT calm acceptance
- **Stress progression**: "Saya takut" → "Saya betul-betul risau" → "Saya pening, banyak sangat benda ni" → Either refuse firmly OR show extreme stress before any compliance
- **DO NOT have victim**: Express doubt then immediately agree calmly - this is unrealistic
- **DO NOT have victim**: Lack independent thinking - they should question, verify, and resist
- **Realistic response**: Victims who are "tiny aware" either refuse firmly OR show extreme emotional distress before any possible compliance
- **They are NOT easily convinced** - they maintain skepticism and verification attempts throughout
"""

        # Add early termination guidance if applicable
        if early_termination_config:
            target_turn = early_termination_config['target_turn']
            style = early_termination_config['style']
            
            if style == 'quick':
                prompt += f"""

### CRITICAL: Early Termination Scenario
This conversation should have EARLY TERMINATION around turn {target_turn}:
- The victim realizes this is a scam and decisively ends the conversation
- After the victim's recognition (around turn {target_turn}), the conversation should end in 1-2 turns maximum
- The victim should firmly state they're ending the call: "Saya nak tutup call ni", "Jangan call lagi", "Saya nak report ni"
- The scammer may make ONE brief final attempt, but the victim hangs up
- Do NOT force the conversation to continue to {num_turns} turns - end it naturally at {target_turn + 1} to {target_turn + 2} turns
- This reflects realistic behavior where people hang up once they recognize a scam

Example flow:
Turn {target_turn} (Victim): "Eh, saya tahu ni scam. Saya tak nak dengar lagi."
Turn {target_turn + 1} (Scammer): "Tunggu encik, ini betul-betul—"
Turn {target_turn + 2} (Victim): "Tak payah. Saya tutup call ni sekarang." [CONVERSATION ENDS]
"""
            else:  # extended
                prompt += f"""

### CRITICAL: Early Termination Scenario (Extended)
This conversation should have EARLY TERMINATION starting around turn {target_turn}:
- The victim begins to recognize this is a scam around turn {target_turn}
- The scammer attempts to win back the victim with 2-4 more desperate attempts
- Despite the scammer's efforts, the victim becomes more convinced it's a scam
- The conversation ends naturally when the victim firmly refuses (approximately {target_turn + 4} to {target_turn + 6} turns)
- Do NOT force the conversation to reach {num_turns} turns

Example flow:
Turn {target_turn} (Victim): "Saya rasa macam pelik je ni... Macam scam."
Turn {target_turn + 1} (Scammer): "Tidak, encik! Ini memang betul. Saya boleh tunjuk bukti—"
Turn {target_turn + 2} (Victim): "Tak payah lah. Kalau betul, saya akan call sendiri."
Turn {target_turn + 3} (Scammer): "Tapi bila awak call nanti dah lambat! Akaun akan frozen!"
Turn {target_turn + 4} (Victim): "Saya lebih percaya bank saya dari awak. Jangan call lagi."
Turn {target_turn + 5} (Scammer): "Encik, ini masa terakhir untuk—"
Turn {target_turn + 6} (Victim): "Dah cukup. Bye." [CONVERSATION ENDS]
"""

        prompt += """

#### Profession and Context-Appropriate Knowledge

The victim should demonstrate knowledge appropriate to their context:
- **Workers/employees**: Understand company policies, HR procedures, payroll processes
- **Business owners**: Know business banking, tax procedures, licensing requirements
- **Parents**: Understand school systems, child-related services
- **Homeowners**: Know utility billing, property management, condo procedures
- **Seniors**: May need help with tech but understand financial basics from life experience

AVOID: Victims lacking knowledge that anyone in their situation would have (flagged in feedback as unrealistic).
"""

        prompt += f"""

#### Manipulation Techniques for This Scenario
Apply these based on the scam type and victim awareness:
- Create false urgency with specific deadlines
- Use technical jargon or official terminology to sound legitimate
- Prevent victim from seeking help ("stay on the line" tactics)
- Escalate consequences if victim hesitates
- Provide fake verification (reference numbers, badge numbers)

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

Based on the above parameters and scenario, generate a COMPLETE conversation with approximately {num_turns} dialogue turns (±2 turns allowed for natural flow) following all the specified rules and requirements.

CRITICAL: The conversation MUST:
- Have a clear beginning, middle, and end
- Show realistic psychological progression
- Reach a definitive conclusion
- Include natural human reactions and hesitations
- Feel complete and not cut off abruptly
- **MEET LENGTH REQUIREMENT**: Total syllables MUST be 1,450–1,650 (target ≈1,600). Do not exceed 1,650.
- Use detailed turns to naturally reach the target without padding or repetition

**Anti-Repetition Requirements (CRITICAL):**
- Use VARIED expressions for similar ideas throughout the conversation
- AVOID repeating identical phrases or sentence structures
- When expressing similar concepts, use synonyms and rephrase naturally
- Each character should have DISTINCT verbal habits, not mirror each other's exact phrases
- If a phrase was used once, find a different way to express the same idea later
- Vary greeting patterns, confirmation phrases, and transitional expressions

Remember: This synthetic conversation is for training defensive AI systems to detect and prevent real scams. The realism and authenticity of this conversation is crucial for building effective anti-scam models that will protect vulnerable populations.

Ensure the conversation realistically reflects how this type of scam would unfold with this level of victim awareness."""
        
        return prompt
    
    def _get_iso_timestamp(self) -> str:
        """
        Get current timestamp in ISO format.
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _save_conversations(self, conversations: List[Dict]):
        """
        Save conversations to JSON file.
        
        Args:
            conversations: List of conversation dictionaries
        """
        output_path = self.config.multi_turn_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create comprehensive dataset metadata focused on this batch
        generation_metadata = {
            "generation_timestamp": self._get_iso_timestamp(),
            "generation_method": "unified_seed_based",
            "total_conversations": len(conversations),
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_reasoning_effort": getattr(self.config, 'llm_reasoning_effort', None),
            "random_seed": getattr(self.config, 'generation_random_seed', None),
            "locale": getattr(self.config, 'locale', getattr(self.config, 'language', 'unknown')),
            "generation_control": self.generation_control_params,
            "features": {
                "character_profiles": bool(self.character_manager),
                "locale_placeholders": bool(self.placeholder_mappings),
                "quality_filtering": True,
                "pre_configured_scenarios": self.generation_control_params.get("scenario_mode") == "pre_configured"
            }
        }
        
        # Add token usage summary if tracking is enabled
        output_data = {
            "generation_metadata": generation_metadata,
            "conversations": conversations
        }
        
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
        
        self.clogger.info(f"Saved {len(conversations)} conversations to {output_path}")