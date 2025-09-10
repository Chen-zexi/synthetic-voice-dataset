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
from src.utils.logging_utils import ConditionalLogger


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
        
        # Use seed placeholders if available, otherwise use all locale placeholders
        placeholder_list = seed.placeholders if seed.placeholders else list(self.placeholder_mappings.keys())
        
        # Use original seed text (no processing needed)
        processed_seed_text = seed.conversation_seed
        processed_summary = seed.scam_summary
        
        # Generate dialogue using the seed text with placeholder context and optional character profiles
        dialogue = await self._generate_dialogue(
            processed_seed_text, 
            num_turns, 
            victim_awareness, 
            seed.scam_tag, 
            placeholder_list,  # Pass the full placeholder list
            character_profiles
        )
        
        if dialogue:
            # Build conversation dictionary
            conversation = {
                "conversation_id": conversation_id,
                "seed_id": seed.seed_id,
                "scam_tag": seed.scam_tag,
                "scam_category": seed.scam_category,
                "summary": processed_summary,
                "seed": processed_seed_text,
                "quality_score": seed.quality_score,
                "num_turns": num_turns,
                "victim_awareness": victim_awareness,
                "placeholders": seed.placeholders
            }
            
            # Add character profile information if used
            if character_profiles:
                conversation["character_profiles"] = {
                    "scammer_profile_id": character_profiles["scammer"].profile_id,
                    "victim_profile_id": character_profiles["victim"].profile_id
                }
            
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
            
            return conversation
        
        return None

    async def _generate_dialogue(self, seed_text: str, num_turns: int, 
                                victim_awareness: str, scam_type: str = None, 
                                placeholders: List[str] = None,
                                character_profiles: Dict = None) -> Optional[List[Dict]]:
        """
        Generate dialogue turns asynchronously using LLM.
        
        Args:
            seed_text: Full seed description of the scam scenario
            num_turns: Number of turns to generate
            victim_awareness: Victim's awareness level
            scam_type: Category of scam for additional context
            placeholders: List of placeholder names to use
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
            placeholders,
            character_profiles
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
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for conversation generation.
        Optimized for OpenAI prompt caching - keep this completely static.
        """
        return """You are a multilingual dialogue generator for creating realistic phone conversations.

## Core Capabilities
You can generate natural conversations in multiple languages including English, Malay, Arabic, Japanese, Korean, Chinese, Vietnamese, Thai, and others.
Your task is to generate structured dialogues with alternating turns between caller and callee.

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
4. Keep sentences short and natural for phone conversations

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


## Important Rules
1. Always alternate between caller and callee roles
2. Start with the caller role
3. Generate the exact number of turns requested
4. Use provided localized values, never placeholder tags
5. Maintain scenario consistency throughout the conversation"""

    def _create_user_prompt(self, seed_text: str, num_turns: int, 
                           victim_awareness: str, scam_type: str = None, 
                           placeholders: List[str] = None,
                           character_profiles: Dict = None) -> str:
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
            placeholders: List of placeholder names to use (unused - using pre-computed)
            character_profiles: Optional dict with "scammer" and "victim" CharacterProfile objects
            
        Returns:
            Formatted prompt
        """
        # SECTION 1: Universal Static Content (cacheable across all locales)
        prompt = """## Task: Generate Scam Phone Call Dialogue

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
4. Keep sentences short and natural for phone conversations
5. Make the dialogue realistic based on the scenario
6. Use actual localized values from options provided, never placeholder tags
7. Maintain consistency throughout the conversation
"""
        
        # SECTION 2: Locale-Static Content (pre-computed, cacheable per locale batch)
        prompt += self.locale_static_prompt
        
        # SECTION 3: Conversation-Dynamic Content (unique per conversation)
        prompt += "\n### This Conversation's Parameters\n"
        
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
"""
        
        # Add scenario-specific details
        prompt += f"""
#### Scenario Specifics

**Type**: {scam_type + ' scam' if scam_type else 'Scam'}
**Victim Awareness**: The victim is {victim_awareness} aware that this might be a scam
**Number of Turns**: Generate exactly {num_turns} dialogue turns

**Scenario Description**:
{seed_text}

### Generate the Dialogue

Based on the above parameters and scenario, generate exactly {num_turns} dialogue turns following all the specified rules and requirements."""
        
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