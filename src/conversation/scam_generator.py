"""
Scam conversation generator using LLM core with LangChain.
"""

import json
import random
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

from config.config_loader import Config
from llm_core.api_provider import LLM
from llm_core.api_call import make_api_call
from llm_core.token_counter import TokenUsageTracker
from conversation.schemas import ScamConversationResponse, DialogueTurn, ScenarioMetadata
from conversation.seed_manager import SeedManager, ScamSeed
from conversation.character_manager import CharacterManager, GenerationScenario
from conversation.placeholder_processor import DynamicPlaceholderProcessor
from utils.logging_utils import ConditionalLogger


logger = logging.getLogger(__name__)


class ScamGenerator:
    """
    Generates multi-turn scam conversations using OpenAI GPT-4.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the scam generator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.clogger = ConditionalLogger(__name__, config.verbose)
        
        # Initialize seed and character managers if using new system
        self.seed_manager = None
        self.character_manager = None
        
        if getattr(config, 'generation_source_type', 'legacy_text') == 'seeds':
            # Initialize seed manager
            seeds_file_path = config.base_dir / getattr(config, 'generation_seeds_file', 'scam_samples.json')
            if seeds_file_path.exists():
                self.seed_manager = SeedManager(seeds_file_path)
                self.clogger.info(f"Loaded seed manager with {len(self.seed_manager.get_all_seeds())} seeds", force=True)
            else:
                self.clogger.warning(f"Seeds file not found at {seeds_file_path}, falling back to legacy mode")
            
            # Initialize character manager
            if getattr(config, 'generation_enable_character_profiles', False):
                profiles_file_path = None
                if hasattr(config, 'generation_profiles_file') and config.generation_profiles_file:
                    profiles_file_path = config.base_dir / config.generation_profiles_file
                
                self.character_manager = CharacterManager(profiles_file_path)
                self.clogger.info(f"Loaded character manager with {len(self.character_manager.profiles)} profiles", force=True)
            else:
                self.clogger.info("Character profiles disabled, using default profiles")
                self.character_manager = CharacterManager()  # Uses default profiles
        else:
            # Initialize character manager for legacy mode if enabled
            if getattr(config, 'generation_enable_character_profiles', False):
                profiles_file_path = None
                if hasattr(config, 'generation_profiles_file') and config.generation_profiles_file:
                    profiles_file_path = config.base_dir / config.generation_profiles_file
                
                self.character_manager = CharacterManager(profiles_file_path)
                self.clogger.info(f"Loaded character manager with {len(self.character_manager.profiles)} profiles for legacy mode", force=True)
        
        # Initialize dynamic placeholder processor if enabled
        self.placeholder_processor = None
        if getattr(config, 'generation_enable_dynamic_placeholders', False):
            placeholders_path = config.preprocessing_map_path if hasattr(config, 'preprocessing_map_path') else None
            if placeholders_path and placeholders_path.exists():
                self.placeholder_processor = DynamicPlaceholderProcessor(placeholders_path)
                self.clogger.info(f"Loaded dynamic placeholder processor with {len(self.placeholder_processor.placeholders)} placeholders", force=True)
            else:
                self.clogger.warning("Dynamic placeholders enabled but placeholders file not found")
        
        # Initialize LLM with configurable provider (default to OpenAI)
        self.llm_provider = getattr(config, 'llm_provider', 'openai')
        self.llm_model = getattr(config, 'llm_model', 'gpt-4o')
        
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
        
        # Load placeholder mappings for the current locale
        self.placeholder_mappings = self._load_placeholder_mappings()
        self.clogger.info(f"Loaded {len(self.placeholder_mappings)} placeholder mappings for locale {config.language}")
    
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
    
    def _build_placeholder_context(self, placeholders: List[str]) -> str:
        """
        Build placeholder context string for the prompt.
        
        Args:
            placeholders: List of placeholder names used in the seed
            
        Returns:
            Formatted context string for the prompt
        """
        if not self.placeholder_mappings:
            return ""
        
        # If no specific placeholders provided, use ALL available placeholders
        if not placeholders:
            placeholders = list(self.placeholder_mappings.keys())
            use_all = True
        else:
            use_all = False
        
        context_parts = []
        for placeholder_name in placeholders:
            if placeholder_name in self.placeholder_mappings:
                mapping = self.placeholder_mappings[placeholder_name]
                substitutions = mapping.get('substitutions', [])
                if substitutions:
                    # Provide all available substitutions for LLM to choose from
                    context_parts.append(
                        f"- When you see {placeholder_name} in the scenario, select and use one of these localized values:\n"
                        f"  Options: {', '.join(substitutions)}\n"
                        f"  ({mapping.get('description', 'No description')})"
                    )
        
        if context_parts:
            if use_all:
                return (
                    "\n**LOCALIZED VALUES FOR CONVERSATION**:\n"
                    "The scenario may reference various placeholders. For any that appear, "
                    "select and use appropriate values from these options:\n\n" +
                    "\n".join(context_parts) + "\n\n"
                    "IMPORTANT: Use the actual localized values directly in the dialogue, "
                    "not the placeholder tags. Choose contextually appropriate options."
                )
            else:
                return (
                    "\n**LOCALIZED VALUES FOR CONVERSATION**:\n"
                    "The scenario contains placeholders that need to be replaced with localized values. "
                    "For each placeholder mentioned:\n\n" +
                    "\n".join(context_parts) + "\n\n"
                    "IMPORTANT: Replace each placeholder with an actual value from the options provided. "
                    "Use these localized values directly in the dialogue text."
                )
        return ""
    
    def _select_placeholder_substitutions(self, placeholders: List[str]) -> Dict[str, str]:
        """
        Select specific substitutions for each placeholder in this conversation.
        
        Args:
            placeholders: List of placeholder names
            
        Returns:
            Dictionary mapping placeholder names to selected substitutions
        """
        substitutions = {}
        
        # If no specific placeholders provided, don't pre-select any substitutions
        # The LLM will choose which placeholders to use from the full list
        if not placeholders:
            return substitutions
            
        for placeholder_name in placeholders:
            if placeholder_name in self.placeholder_mappings:
                mapping = self.placeholder_mappings[placeholder_name]
                available_substitutions = mapping.get('substitutions', [])
                if available_substitutions:
                    substitutions[placeholder_name] = random.choice(available_substitutions)
        return substitutions
    
    async def generate_conversations(self) -> List[Dict]:
        """
        Generate scam conversations asynchronously for faster processing.
        
        Returns:
            List of conversation dictionaries
        """
        # Check if using new seed-based system
        if self.seed_manager and self.character_manager:
            return await self._generate_conversations_from_scenarios()
        else:
            # Fall back to legacy line-by-line generation
            return await self._generate_conversations_legacy()
    
    async def _generate_conversations_from_scenarios(self) -> List[Dict]:
        """
        Generate conversations using the new scenario-based system.
        
        Returns:
            List of conversation dictionaries
        """
        self.clogger.info("Generating scam conversations using scenario-based system", force=True)
        
        # Get high-quality seeds
        min_quality = getattr(self.config, 'generation_min_seed_quality', 70)
        high_quality_seeds = self.seed_manager.get_high_quality_seeds(min_quality)
        
        if not high_quality_seeds:
            self.clogger.warning(f"No seeds found with quality >= {min_quality}, using all seeds")
            high_quality_seeds = self.seed_manager.get_all_seeds()
        
        self.clogger.info(f"Using {len(high_quality_seeds)} seeds with quality >= {min_quality}")
        
        # Create scenarios
        scenarios_per_seed = getattr(self.config, 'generation_scenarios_per_seed', 1)
        seed_tags = [seed.scam_tag for seed in high_quality_seeds]
        
        # Limit seeds based on configuration
        max_seeds = min(len(seed_tags), self.config.max_conversation // scenarios_per_seed)
        if self.config.sample_limit:
            max_seeds = min(max_seeds, self.config.sample_limit // scenarios_per_seed)
        
        selected_seed_tags = seed_tags[:max_seeds]
        
        locale = getattr(self.config, 'locale', 'en-us')
        scenarios = self.character_manager.create_multiple_scenarios(
            seed_tags=selected_seed_tags,
            locale=locale,
            scenarios_per_seed=scenarios_per_seed
        )
        
        self.clogger.info(f"Created {len(scenarios)} scenarios from {len(selected_seed_tags)} seed tags")
        
        # Prepare tasks
        tasks = []
        for idx, scenario in enumerate(scenarios):
            task = self._generate_single_conversation_from_scenario(idx + 1, scenario)
            tasks.append(task)
        
        return await self._execute_generation_tasks(tasks, "scenarios")
    
    async def _generate_conversations_legacy(self) -> List[Dict]:
        """
        Generate conversations using the legacy line-by-line system.
        
        Returns:
            List of conversation dictionaries  
        """
        self.clogger.info(f"Generating scam conversations from {self.config.multi_turn_input_path}", force=True)
        
        # Load seed data from JSON
        with open(self.config.multi_turn_input_path, 'r', encoding='utf-8') as f:
            seed_data = json.load(f)
        
        self.clogger.info(f"Loaded {len(seed_data)} scam scenarios")
        
        # Prepare tasks with seed data
        tasks = []
        for idx, entry in enumerate(seed_data[:self.config.sample_limit]):
            if idx >= self.config.max_conversation:
                break
            
            # Extract relevant fields from seed entry with new field names
            seed_id = entry.get('seed_id', f'seed_{idx:03d}')
            seed_text = entry.get('conversation_seed', '')
            scam_tag = entry.get('scam_tag', 'Unknown')
            scam_category = entry.get('scam_category', 'Unknown')
            summary = entry.get('scam_summary', '')
            placeholders = entry.get('placeholders', [])
            
            task = self._generate_single_conversation_legacy(
                conversation_id=idx + 1,
                seed_id=seed_id,
                seed_text=seed_text,
                scam_tag=scam_tag,
                scam_category=scam_category,
                summary=summary,
                placeholders=placeholders
            )
            tasks.append(task)
        
        return await self._execute_generation_tasks(tasks, "legacy")
    
    async def _execute_generation_tasks(self, tasks: List, task_type: str) -> List[Dict]:
        """
        Execute generation tasks with progress tracking.
        
        Args:
            tasks: List of async tasks to execute
            task_type: Description for logging ("scenarios" or "legacy")
            
        Returns:
            List of generated conversations
        """
        # Run tasks concurrently with progress bar
        max_concurrent = getattr(self.config, 'max_concurrent_requests', 10)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Wrap tasks with semaphore
        async def limited_task(task_func):
            async with semaphore:
                return await task_func
        
        # Create progress bar for async operations  
        pbar = tqdm(total=len(tasks), desc=f"Generating conversations ({task_type})")
        
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
        
        # Save conversations
        self._save_conversations(all_conversations)
        
        # Add small delay to allow async cleanup
        await asyncio.sleep(0.1)
        
        self.clogger.info(f"Generated {len(all_conversations)} conversations using {task_type} approach", force=True)
        return all_conversations
    
    async def _generate_single_conversation_from_scenario(self, conversation_id: int, scenario: GenerationScenario) -> Optional[Dict]:
        """
        Generate a single conversation from a scenario asynchronously.
        
        Args:
            conversation_id: Unique conversation ID
            scenario: GenerationScenario object with seed and character info
            
        Returns:
            Conversation dictionary or None if generation failed
        """
        # Get the seed data
        seed = self.seed_manager.get_seed(scenario.seed_tag)
        if not seed:
            self.clogger.error(f"Could not find seed for tag: {scenario.seed_tag}")
            return None
        
        # Randomly select conversation parameters
        num_turns = random.randint(
            self.config.num_turns_lower_limit,
            self.config.num_turns_upper_limit
        )
        victim_awareness = random.choice(self.config.victim_awareness_levels)
        
        # Pre-process seed with placeholders if enabled
        processed_seed_for_prompt = seed
        if self.placeholder_processor:
            conversation_key = f"{scenario.scenario_id}_{conversation_id}"
            # Create a copy of the seed with processed text for the prompt
            from types import SimpleNamespace
            processed_seed_for_prompt = SimpleNamespace(**seed.model_dump())
            processed_seed_for_prompt.conversation_seed = self.placeholder_processor.process_text(seed.conversation_seed, conversation_key)
            processed_seed_for_prompt.scam_summary = self.placeholder_processor.process_text(seed.scam_summary, conversation_key)
        
        # Generate enhanced dialogue using scenario
        dialogue = await self._generate_dialogue_from_scenario(scenario, processed_seed_for_prompt, num_turns, victim_awareness)
        
        if dialogue:
            # Apply dynamic placeholders if enabled
            processed_seed = seed.conversation_seed
            processed_summary = seed.scam_summary
            
            if self.placeholder_processor:
                conversation_key = f"{scenario.scenario_id}_{conversation_id}"
                processed_seed = self.placeholder_processor.process_text(seed.conversation_seed, conversation_key)
                processed_summary = self.placeholder_processor.process_text(seed.scam_summary, conversation_key)
                
                # Process dialogue turns
                if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                    processed_dialogue_turns = []
                    for turn in dialogue['dialogue']:
                        processed_turn = turn.copy()
                        processed_turn['text'] = self.placeholder_processor.process_text(turn['text'], conversation_key)
                        processed_dialogue_turns.append(processed_turn)
                    dialogue['dialogue'] = processed_dialogue_turns
                elif isinstance(dialogue, list):
                    processed_dialogue = []
                    for turn in dialogue:
                        processed_turn = turn.copy()
                        processed_turn['text'] = self.placeholder_processor.process_text(turn['text'], conversation_key)
                        processed_dialogue.append(processed_turn)
                    dialogue = processed_dialogue
            
            # Create conversation with enhanced metadata
            conversation = {
                "conversation_id": conversation_id,
                "scenario": {
                    "scenario_id": scenario.scenario_id,
                    "seed_tag": scenario.seed_tag,
                    "seed_record_id": seed.record_id,
                    "scammer_profile_id": scenario.scammer_profile.profile_id,
                    "victim_profile_id": scenario.victim_profile.profile_id,
                    "locale": scenario.locale
                },
                "seed_summary": processed_summary,
                "conversation_seed": processed_seed,
                "num_turns": num_turns,
                "victim_awareness": victim_awareness
            }
            
            # Check if dialogue is a dict with voice_mapping (from LLM response)
            if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                conversation["dialogue"] = dialogue['dialogue']
                # Add voice mapping if provided by LLM
                if 'voice_mapping' in dialogue:
                    conversation["voice_mapping"] = dialogue['voice_mapping']
                    self.clogger.info(f"LLM assigned voices for conversation {conversation_id}: {dialogue['voice_mapping']}")
            else:
                # Legacy format - just dialogue list
                conversation["dialogue"] = dialogue
            
            # Add generation metadata
            conversation["metadata"] = {
                "generation_method": "scenario_based",
                "character_profiles_enabled": True,
                "dynamic_placeholders_enabled": bool(self.placeholder_processor),
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model,
                "generation_timestamp": self._get_iso_timestamp(),
                "locale": scenario.locale
            }
            
            # Add placeholder information if available
            if self.placeholder_processor:
                conversation_key = f"{scenario.scenario_id}_{conversation_id}"
                placeholder_selections = self.placeholder_processor.get_conversation_placeholders(conversation_key)
                if placeholder_selections:
                    conversation["placeholder_selections"] = placeholder_selections
            
            return conversation
        
        return None

    async def _generate_single_conversation_legacy(self, conversation_id: int, seed_id: str,
                                                  seed_text: str, scam_tag: str, 
                                                  scam_category: str, summary: str, 
                                                  placeholders: List[str]) -> Optional[Dict]:
        """
        Generate a single conversation using the legacy method with optional character profiles.
        
        Args:
            conversation_id: Unique conversation ID
            seed_id: Unique identifier for the seed (e.g., "seed001")
            seed_text: Full seed description of the scam scenario
            scam_tag: Tag/type of scam (e.g., "government", "romance")
            scam_category: Category of scam (e.g., "government_legal")
            summary: Brief summary of the scam
            placeholders: List of placeholder tags for localization
            
        Returns:
            Conversation dictionary or None if generation failed
        """
        # Randomly select conversation parameters
        num_turns = random.randint(
            self.config.num_turns_lower_limit,
            self.config.num_turns_upper_limit
        )
        victim_awareness = random.choice(self.config.victim_awareness_levels)
        
        # Select specific substitutions for this conversation
        selected_substitutions = self._select_placeholder_substitutions(placeholders)
        
        # Apply dynamic placeholders to seed text if enabled
        processed_seed_text = seed_text
        processed_summary = summary
        if self.placeholder_processor:
            conversation_key = f"legacy_{conversation_id}"
            processed_seed_text = self.placeholder_processor.process_text(seed_text, conversation_key)
            processed_summary = self.placeholder_processor.process_text(summary, conversation_key)
        
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
                self.clogger.info(f"Using character profiles for conversation {conversation_id}: "
                                f"Scammer={scammer_profile.profile_id}, Victim={victim_profile.profile_id}")
        
        # Generate dialogue using the seed text with placeholder context and optional character profiles
        dialogue = await self._generate_dialogue(
            processed_seed_text, 
            num_turns, 
            victim_awareness, 
            scam_tag, 
            placeholders,
            character_profiles
        )
        
        if dialogue:
            # Apply dynamic placeholders to dialogue if enabled
            if self.placeholder_processor:
                conversation_key = f"legacy_{conversation_id}"
                if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                    processed_dialogue_turns = []
                    for turn in dialogue['dialogue']:
                        processed_turn = turn.copy()
                        processed_turn['text'] = self.placeholder_processor.process_text(turn['text'], conversation_key)
                        processed_dialogue_turns.append(processed_turn)
                    dialogue['dialogue'] = processed_dialogue_turns
                elif isinstance(dialogue, list):
                    processed_dialogue = []
                    for turn in dialogue:
                        processed_turn = turn.copy() 
                        processed_turn['text'] = self.placeholder_processor.process_text(turn['text'], conversation_key)
                        processed_dialogue.append(processed_turn)
                    dialogue = processed_dialogue
            
            # Build conversation dictionary
            conversation = {
                "conversation_id": conversation_id,
                "seed_id": seed_id,
                "scam_tag": scam_tag,
                "scam_category": scam_category,
                "summary": processed_summary,
                "seed": processed_seed_text,
                "num_turns": num_turns,
                "victim_awareness": victim_awareness,
                "placeholders": placeholders,
                "placeholder_substitutions": selected_substitutions
            }
            
            # Add character profile information if used
            if character_profiles:
                conversation["character_profiles"] = {
                    "scammer_profile_id": character_profiles["scammer"].profile_id,
                    "victim_profile_id": character_profiles["victim"].profile_id
                }
            
            # Check if dialogue is a dict with voice_mapping (from LLM response)
            if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                conversation["dialogue"] = dialogue['dialogue']
                # Add voice mapping if provided by LLM
                if 'voice_mapping' in dialogue:
                    conversation["voice_mapping"] = dialogue['voice_mapping']
                    self.clogger.info(f"LLM assigned voices for conversation {conversation_id}: {dialogue['voice_mapping']}")
            else:
                # Legacy format - just dialogue list
                conversation["dialogue"] = dialogue
            
            # Add generation metadata for legacy method
            conversation["metadata"] = {
                "generation_method": "legacy_text_with_profiles" if character_profiles else "legacy_text",
                "character_profiles_enabled": bool(character_profiles),
                "dynamic_placeholders_enabled": bool(self.placeholder_processor),
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model,
                "generation_timestamp": self._get_iso_timestamp(),
                "locale": getattr(self.config, 'locale', 'unknown')
            }
            
            # Add placeholder information if available
            if self.placeholder_processor:
                conversation_key = f"legacy_{conversation_id}"
                placeholder_selections = self.placeholder_processor.get_conversation_placeholders(conversation_key)
                if placeholder_selections:
                    conversation["placeholder_selections"] = placeholder_selections
            
            return conversation
        
        return None
    
    async def _generate_dialogue_from_scenario(self, scenario: GenerationScenario, seed: ScamSeed, 
                                             num_turns: int, victim_awareness: str) -> Optional[List[Dict]]:
        """
        Generate dialogue turns using enhanced scenario-based prompts.
        
        Args:
            scenario: GenerationScenario object with character profiles
            seed: ScamSeed object with scam details
            num_turns: Number of turns to generate
            victim_awareness: Victim's awareness level
            
        Returns:
            List of dialogue turns or None if generation failed
        """
        system_prompt = self._create_scenario_system_prompt(scenario)
        user_prompt = self._create_scenario_user_prompt(scenario, seed, num_turns, victim_awareness)
        
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
                    f"scenario_{scenario.scenario_id}"
                )
            else:
                response = await make_api_call(
                    llm=self.llm,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=ScamConversationResponse
                )
            
            # Debug logging
            self.clogger.info(f"API call returned response of type: {type(response)}")
            
            # Convert Pydantic models to dicts and add sent_id
            if hasattr(response, 'dialogue'):
                self.clogger.info(f"Response has dialogue with {len(response.dialogue)} turns")
                # Add sent_id to each turn
                dialogue_with_ids = []
                for i, turn in enumerate(response.dialogue, 1):
                    turn_dict = turn.model_dump()
                    turn_dict['sent_id'] = i  # Add sequential ID
                    dialogue_with_ids.append(turn_dict)
                
                result = {'dialogue': dialogue_with_ids}
                
                # Include voice_mapping if present
                if hasattr(response, 'voice_mapping') and response.voice_mapping:
                    result['voice_mapping'] = response.voice_mapping
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
                # Use seed_text snippet as identifier
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
            self.clogger.info(f"API call returned response of type: {type(response)}")
            
            # Convert Pydantic models to dicts and add sent_id
            if hasattr(response, 'dialogue'):
                self.clogger.info(f"Response has dialogue with {len(response.dialogue)} turns")
                # Add sent_id to each turn
                dialogue_with_ids = []
                for i, turn in enumerate(response.dialogue, 1):
                    turn_dict = turn.model_dump()
                    turn_dict['sent_id'] = i  # Add sequential ID
                    dialogue_with_ids.append(turn_dict)
                
                result = {'dialogue': dialogue_with_ids}
                
                # Include voice_mapping if present
                if hasattr(response, 'voice_mapping') and response.voice_mapping:
                    result['voice_mapping'] = response.voice_mapping
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
    
    def _format_voice_profiles_for_prompt(self) -> str:
        """
        Format voice profiles dynamically for prompt injection, focusing on gender.
        
        Returns:
            Formatted string with voice options or empty string if no profiles
        """
        if not self.config.voice_profiles or 'available_voices' not in self.config.voice_profiles:
            return ""
        
        profiles = self.config.voice_profiles.get('available_voices', {})
        
        # Group by gender
        male_voices = []
        female_voices = []
        
        for name, info in profiles.items():
            gender = info.get('gender', 'unknown')
            age = info.get('age', '')
            desc = f"{name} ({gender}"
            if age:
                desc += f", {age}"
            desc += ")"
            
            if gender == 'male':
                male_voices.append(desc)
            elif gender == 'female':
                female_voices.append(desc)
        
        voice_instructions = f"""
Available voices for this locale:
- Male voices: {', '.join(male_voices) if male_voices else 'None available'}
- Female voices: {', '.join(female_voices) if female_voices else 'None available'}

Based on the conversation context, select appropriate voices and include in your response:
- For the scammer (caller): Choose a voice that fits an authority figure or professional
- For the victim (callee): Choose a voice that fits the implied gender and age from context
- Return the voice names (not the gender/age info) in the voice_mapping field
"""
        return voice_instructions
    
    def _create_scenario_system_prompt(self, scenario: GenerationScenario) -> str:
        """Create enhanced system prompt for scenario-based generation."""
        return """You are an expert dialogue generator specializing in realistic phone conversations.

You create authentic, culturally-appropriate dialogues between two distinct characters based on their detailed profiles and the cultural context of their locale.

CORE RESPONSIBILITIES:
1. Generate structured dialogues with alternating turns between caller and callee
2. Reflect each character's personality, speaking style, and background authentically
3. Adapt content to the specified cultural and regional context
4. Follow all formatting requirements precisely
5. Preserve any special codes from the original scenario

DIALOGUE STRUCTURE:
- Each turn must have: {"text": "dialogue content", "role": "caller" or "callee"}
- Start with the caller role
- Maintain consistent character voices throughout
- Use natural, region-appropriate language patterns

CHARACTER CONSISTENCY:
- Caller traits must be evident in every interaction
- Callee responses should reflect their personality and awareness level
- Speaking styles should remain consistent (formal vs casual, fast vs slow, etc.)
- Educational background should influence vocabulary and complexity

CULTURAL ADAPTATION:
- Use region-appropriate greetings, formalities, and social conventions
- Reference local institutions, landmarks, or cultural norms when relevant
- Adjust communication patterns to match regional expectations
- Maintain authenticity while respecting cultural sensitivities

When voice profiles are available, select appropriate voices based on character gender, age, and cultural context."""

    def _create_scenario_user_prompt(self, scenario: GenerationScenario, seed, 
                                   num_turns: int, victim_awareness: str) -> str:
        """Create enhanced user prompt with scenario context."""
        
        # Get locale information
        locale_info = {
            'language_name': getattr(self.config, 'language_name', 'English'),
            'region_name': getattr(self.config, 'region', 'Unknown'),
            'language_code': getattr(self.config, 'language_code', 'en')
        }
        
        # Format character profiles
        scammer_profile = scenario.scammer_profile
        victim_profile = scenario.victim_profile
        
        # Get voice profile information if available
        voice_info = self._format_voice_profiles_for_prompt()
        
        prompt = f"""Generate a {num_turns}-turn phone conversation based on this scenario:

**LOCALE CONTEXT:**
- Language: {locale_info['language_name']} ({locale_info['language_code']})
- Region: {locale_info['region_name']}
- Cultural Adaptation: Adapt all content to {locale_info['region_name']} cultural norms

**SCAM SCENARIO:**
- Type: {seed.scam_tag}
- Category: {seed.scam_category}
- Summary: {seed.scam_summary}
- Conversation Foundation: "{seed.conversation_seed}"

**CHARACTER PROFILES:**

**Caller (Scammer):**
- Profile: {scammer_profile.name} ({scammer_profile.profile_id})
- Demographics: {scammer_profile.gender.title()}, {scammer_profile.age_range}
- Education: {scammer_profile.education_level}
- Personality: {', '.join(scammer_profile.personality_traits)}
- Speaking Style: {', '.join(scammer_profile.speaking_style)}

**Callee (Victim):**
- Profile: {victim_profile.name} ({victim_profile.profile_id})
- Demographics: {victim_profile.gender.title()}, {victim_profile.age_range}
- Education: {victim_profile.education_level}
- Personality: {', '.join(victim_profile.personality_traits)}
- Speaking Style: {', '.join(victim_profile.speaking_style)}
- Awareness Level: {victim_awareness} aware of the scam

**CONVERSATION REQUIREMENTS:**

1. **Opening**: Base the first turn on the conversation foundation above, but adapt it to the caller's speaking style and personality
2. **Character Consistency**: Every turn must reflect the speaker's personality, education level, and speaking style
3. **Cultural Context**: Use {locale_info['region_name']}-appropriate language, references, and social conventions
4. **Progression**: Develop the conversation naturally based on the victim's awareness level
5. **Special Codes**: If the conversation foundation contains special codes (like {{00001}}), preserve them exactly as written
6. **Turn Count**: Generate exactly {num_turns} turns, alternating between caller and callee

**PERSONALITY GUIDANCE:**
- **{scammer_profile.name}**: Should demonstrate {', '.join(scammer_profile.personality_traits[:2])} traits through their dialogue approach
- **{victim_profile.name}**: Should respond in a {', '.join(victim_profile.personality_traits[:2])} manner, being {victim_awareness} aware of potential fraud

{voice_info}

Generate the conversation as a structured dialogue with exactly {num_turns} turns."""
        
        # Add voice mapping instruction if profiles are available
        if voice_info:
            prompt += """

Include a voice_mapping field with your selected voices:
{
  "caller": "selected_voice_name",
  "callee": "selected_voice_name"  
}"""
        
        return prompt
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for conversation generation."""
        return """You are a multilingual dialogue generator for creating realistic phone conversations.
You can generate natural conversations in multiple languages including English, Malay, Arabic, Japanese, Korean, Chinese, Vietnamese, Thai, and others.
Your task is to generate structured dialogues with alternating turns between caller and callee.

KEY CAPABILITIES:
1. Generate conversations directly in the target language specified
2. Use provided localized values (names, organizations, amounts) naturally in the dialogue
3. Create culturally appropriate dialogue patterns for the target language
4. Maintain natural conversation flow in the target language
5. Incorporate character personalities and speaking styles when provided

IMPORTANT: Each dialogue turn must have exactly these fields:
- text: The actual dialogue text (in the target language)
- role: Either "caller" or "callee"

When localized placeholder values are provided:
1. Select appropriate values from the options given
2. Use the actual values directly in the dialogue, not placeholder tags
3. Ensure the values fit naturally within the target language sentences

When character profiles are provided:
1. Reflect each character's personality traits in their dialogue
2. Use speaking styles that match the character descriptions
3. Adapt vocabulary and complexity based on education level
4. Maintain consistent character voices throughout the conversation

When voice profiles are provided:
1. Consider the gender and age implications from the conversation context
2. Match authority figures with appropriate voice characteristics
3. Ensure realistic voice assignments based on the scenario
4. Output voice_mapping with selected voice names (use just the name, not the full description)"""

    def _create_user_prompt(self, seed_text: str, num_turns: int, 
                           victim_awareness: str, scam_type: str = None, 
                           placeholders: List[str] = None,
                           character_profiles: Dict = None) -> str:
        """
        Create the user prompt for conversation generation.
        
        Args:
            seed_text: Full seed description of the scam scenario
            num_turns: Number of turns
            victim_awareness: Victim's awareness level
            scam_type: Category of scam for additional context
            placeholders: List of placeholder names to use
            character_profiles: Optional dict with "scammer" and "victim" CharacterProfile objects
            
        Returns:
            Formatted prompt
        """
        # Get voice profile information if available
        voice_info = self._format_voice_profiles_for_prompt()
        
        # Include scam type in the prompt if available
        type_context = f"This is a {scam_type} scam.\n" if scam_type else ""
        
        # Build placeholder context if placeholders are provided
        placeholder_context = self._build_placeholder_context(placeholders) if placeholders else ""
        
        # Determine target language for generation
        target_language = getattr(self.config, 'language_name', 'English')
        target_region = getattr(self.config, 'region', '')
        
        # Create language instruction
        if target_language.lower() != 'english':
            language_instruction = f"""
**LANGUAGE REQUIREMENT**:
Generate the entire conversation in {target_language}{f' as spoken in {target_region}' if target_region else ''}. 
Use natural, colloquial {target_language} expressions and dialogue patterns.
When using the localized values provided, incorporate them naturally into {target_language} sentences.
"""
        else:
            language_instruction = ""
        
        # Build character profile context if provided
        character_context = ""
        if character_profiles:
            scammer = character_profiles.get("scammer")
            victim = character_profiles.get("victim")
            
            if scammer and victim:
                character_context = f"""
**CHARACTER PROFILES**:

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

**CHARACTER REQUIREMENTS**:
1. The scammer should exhibit {', '.join(scammer.personality_traits[:2])} traits in their approach
2. The victim should respond in a {', '.join(victim.personality_traits[:2])} manner
3. Both characters should maintain their speaking styles throughout
4. Vocabulary and complexity should match their education levels
"""
        
        prompt = f"""Generate a realistic scam phone call dialogue based on the following scenario:

{type_context}
**SCENARIO**:
{seed_text}
{placeholder_context}{language_instruction}{character_context}
**DIALOGUE REQUIREMENTS**:
- Create a conversation between the caller (scammer) and callee (victim)
- The victim is {victim_awareness} aware that this might be a scam
- The total number of turns must be exactly {num_turns} individual turns (lines), alternating between caller and callee
- The first turn should be the scammer's opening line based on the scenario
- Make the dialogue natural and realistic based on the scenario description
- When placeholders appear in the scenario, replace them with appropriate values from the localized options provided
- Generate all dialogue text in {target_language}
{f"- Incorporate the character personalities and speaking styles provided" if character_profiles else ""}

{voice_info}

**IMPORTANT RULES**: 
1. Use the actual localized values from the options provided, not placeholder tags
2. Generate the conversation directly in {target_language}
3. Keep sentences short and natural for phone conversations
{f"4. Maintain character consistency throughout the conversation" if character_profiles else ""}

Generate exactly {num_turns} dialogue turns, starting with "caller" role.

Example format for dialogue field:
[
  {{"text": "Your shortened first turn here", "role": "caller"}},
  {{"text": "Victim's response", "role": "callee"}},
  {{"text": "Scammer's next line", "role": "caller"}},
  ...
]"""
        
        # Add voice mapping instruction if profiles are available
        if voice_info:
            prompt += """

Include a voice_mapping field with your selected voices:
{
  "caller": "selected_voice_name",
  "callee": "selected_voice_name"
}"""
        
        return prompt
    
    def _get_iso_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
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
        
        # Create comprehensive dataset metadata
        generation_metadata = {
            "generation_timestamp": self._get_iso_timestamp(),
            "generation_mode": "scenario_based" if (self.seed_manager and self.character_manager) else "legacy_text",
            "total_conversations": len(conversations),
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "locale": getattr(self.config, 'locale', 'unknown'),
            "features": {
                "character_profiles": bool(self.character_manager),
                "dynamic_placeholders": bool(self.placeholder_processor),
                "seed_manager": bool(self.seed_manager)
            }
        }
        
        # Add character profile statistics if available
        if self.character_manager:
            generation_metadata["character_stats"] = self.character_manager.get_stats()
        
        # Add seed statistics if available  
        if self.seed_manager:
            generation_metadata["seed_stats"] = self.seed_manager.get_stats()
        
        # Add placeholder statistics if available
        if self.placeholder_processor:
            generation_metadata["placeholder_stats"] = self.placeholder_processor.get_statistics()
        
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
        
        self.clogger.info(f"Saved {len(conversations)} conversations to {output_path}", force=True)
        if generation_metadata["generation_mode"] == "scenario_based":
            self.clogger.info(f"Generated using scenario-based system with {generation_metadata['features']}", force=True)