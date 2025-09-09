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
from conversation.schemas import ScamConversationResponse, DialogueTurn
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
            
            task = self._generate_single_conversation(
                conversation_id=idx + 1,
                seed_id=seed_id,
                seed_text=seed_text,
                scam_tag=scam_tag,
                scam_category=scam_category,
                summary=summary,
                placeholders=placeholders
            )
            tasks.append(task)
        
        # Run tasks concurrently with progress bar
        max_concurrent = getattr(self.config, 'max_concurrent_requests', 10)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Wrap tasks with semaphore
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
        
        # Save conversations
        self._save_conversations(all_conversations)
        
        # Add small delay to allow async cleanup
        await asyncio.sleep(0.1)
        
        self.clogger.info(f"Generated {len(all_conversations)} conversations", force=True)
        return all_conversations
    
    async def _generate_single_conversation(self, conversation_id: int, seed_id: str,
                                           seed_text: str, scam_tag: str, 
                                           scam_category: str, summary: str, 
                                           placeholders: List[str]) -> Optional[Dict]:
        """
        Generate a single conversation asynchronously.
        
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
        
        # Generate dialogue using the seed text with placeholder context
        dialogue = await self._generate_dialogue(seed_text, num_turns, victim_awareness, scam_tag, placeholders)
        
        if dialogue:
            # Check if dialogue is a dict with voice_mapping (from LLM response)
            if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                conversation = {
                    "conversation_id": conversation_id,
                    "seed_id": seed_id,
                    "scam_tag": scam_tag,
                    "scam_category": scam_category,
                    "summary": summary,
                    "seed": seed_text,
                    "num_turns": num_turns,
                    "victim_awareness": victim_awareness,
                    "dialogue": dialogue['dialogue'],
                    "placeholders": placeholders,
                    "placeholder_substitutions": selected_substitutions
                }
                # Add voice mapping if provided by LLM
                if 'voice_mapping' in dialogue:
                    conversation["voice_mapping"] = dialogue['voice_mapping']
                    self.clogger.info(f"LLM assigned voices for conversation {conversation_id}: {dialogue['voice_mapping']}")
            else:
                # Legacy format - just dialogue list
                conversation = {
                    "conversation_id": conversation_id,
                    "seed_id": seed_id,
                    "scam_tag": scam_tag,
                    "scam_category": scam_category,
                    "summary": summary,
                    "seed": seed_text,
                    "num_turns": num_turns,
                    "victim_awareness": victim_awareness,
                    "dialogue": dialogue,
                    "placeholders": placeholders,
                    "placeholder_substitutions": selected_substitutions
                }
            
            return conversation
        
        return None
    
    async def _generate_dialogue(self, seed_text: str, num_turns: int, 
                                victim_awareness: str, scam_type: str = None, 
                                placeholders: List[str] = None) -> Optional[List[Dict]]:
        """
        Generate dialogue turns asynchronously using LLM.
        
        Args:
            seed_text: Full seed description of the scam scenario
            num_turns: Number of turns to generate
            victim_awareness: Victim's awareness level
            scam_type: Category of scam for additional context
            placeholders: List of placeholder names to use
            
        Returns:
            List of dialogue turns or None if generation failed
        """
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(seed_text, num_turns, victim_awareness, scam_type, placeholders)
        
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

IMPORTANT: Each dialogue turn must have exactly these fields:
- text: The actual dialogue text (in the target language)
- role: Either "caller" or "callee"

When localized placeholder values are provided:
1. Select appropriate values from the options given
2. Use the actual values directly in the dialogue, not placeholder tags
3. Ensure the values fit naturally within the target language sentences

When voice profiles are provided:
1. Consider the gender and age implications from the conversation context
2. Match authority figures with appropriate voice characteristics
3. Ensure realistic voice assignments based on the scenario
4. Output voice_mapping with selected voice names (use just the name, not the full description)"""

    def _create_user_prompt(self, seed_text: str, num_turns: int, 
                           victim_awareness: str, scam_type: str = None, 
                           placeholders: List[str] = None) -> str:
        """
        Create the user prompt for conversation generation.
        
        Args:
            seed_text: Full seed description of the scam scenario
            num_turns: Number of turns
            victim_awareness: Victim's awareness level
            scam_type: Category of scam for additional context
            placeholders: List of placeholder names to use
            
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
        
        prompt = f"""Generate a realistic scam phone call dialogue based on the following scenario:

{type_context}
**SCENARIO**:
{seed_text}
{placeholder_context}{language_instruction}
**DIALOGUE REQUIREMENTS**:
- Create a conversation between the caller (scammer) and callee (victim)
- The victim is {victim_awareness} aware that this might be a scam
- The total number of turns must be exactly {num_turns} individual turns (lines), alternating between caller and callee
- The first turn should be the scammer's opening line based on the scenario
- Make the dialogue natural and realistic based on the scenario description
- When placeholders appear in the scenario, replace them with appropriate values from the localized options provided
- Generate all dialogue text in {target_language}

{voice_info}

**IMPORTANT RULES**: 
1. Use the actual localized values from the options provided, not placeholder tags
2. Generate the conversation directly in {target_language}
3. Keep sentences short and natural for phone conversations

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
    
    def _save_conversations(self, conversations: List[Dict]):
        """
        Save conversations to JSON file.
        
        Args:
            conversations: List of conversation dictionaries
        """
        output_path = self.config.multi_turn_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add token usage summary if tracking is enabled
        output_data = conversations
        if self.token_tracker:
            # Create a wrapper with token usage info (without detailed breakdowns)
            token_summary = self.token_tracker.get_summary(include_details=False)
            cost_estimate = self.token_tracker.estimate_cost()
            
            output_data = {
                "conversations": conversations,
                "token_usage": token_summary,
                "estimated_cost": cost_estimate
            }
            
            # Print summary if verbose
            if self.config.verbose:
                self.token_tracker.print_summary()
                self.token_tracker.print_cost_estimate()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data if self.token_tracker else conversations, f, ensure_ascii=False, indent=2)
        
        self.clogger.info(f"Saved conversations to {output_path}", force=True)