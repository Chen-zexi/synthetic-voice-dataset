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

from config.config_loader import Config
from llm_core.api_provider import LLM
from llm_core.api_call import make_api_call
from llm_core.token_counter import TokenUsageTracker
from conversation.schemas import LegitConversationResponse, DialogueTurn
from utils.logging_utils import ConditionalLogger


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
    
    async def generate_conversations(self) -> List[Dict]:
        """
        Generate legitimate conversations asynchronously for faster processing.
        
        Returns:
            List of conversation dictionaries
        """
        self.clogger.info(f"Generating {self.config.num_legit_conversation} legitimate conversations", force=True)
        
        # Prepare tasks
        tasks = []
        for idx in range(self.config.num_legit_conversation):
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
        
        self.clogger.info(f"Generated {len(all_conversations)} legitimate conversations", force=True)
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
            # Check if dialogue is a dict with voice_mapping (from LLM response)
            if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                conversation = {
                    "conversation_id": conversation_id,
                    "region": self.config.legit_call_region,
                    "category": category,
                    "num_turns": num_turns,
                    "dialogue": dialogue['dialogue']
                }
                # Add voice mapping if provided by LLM
                if 'voice_mapping' in dialogue:
                    conversation["voice_mapping"] = dialogue['voice_mapping']
                    self.clogger.info(f"LLM assigned voices for conversation {conversation_id}: {dialogue['voice_mapping']}")
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
                
                # Include voice_mapping if present
                if hasattr(response, 'voice_mapping') and response.voice_mapping:
                    result['voice_mapping'] = response.voice_mapping
                return result
            else:
                self.clogger.error("Response missing dialogue field")
                return None
            
        except Exception as e:
            self.clogger.error(f"LLM API error: {e}")
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

Based on the conversation category and context, select appropriate voices:
- Consider the professional context (delivery, medical, banking, etc.)
- Match gender to natural distribution for the scenario
- Return the voice names (not the gender/age info) in the voice_mapping field
"""
        return voice_instructions
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for legitimate conversation generation."""
        return """You are a dialogue generator for creating realistic phone conversations.
Your task is to generate structured dialogues for legitimate (non-scam) phone calls with alternating turns between caller and callee.
The conversations should be natural, contextually appropriate, and culturally relevant.

IMPORTANT: Each dialogue turn must have exactly these fields:
- text: The actual dialogue text
- role: Either "caller" or "callee"

When voice profiles are provided:
1. Consider the professional context and select appropriate voices
2. Ensure natural gender distribution for the scenario
3. Match voices to the conversation category (e.g., delivery, medical, business)
4. Output voice_mapping with selected voice names (use just the name, not the full description)"""

    def _create_user_prompt(self, num_turns: int, category: str) -> str:
        """
        Create the user prompt for legitimate conversation generation.
        
        Args:
            num_turns: Number of turns
            category: Conversation category
            
        Returns:
            Formatted prompt
        """
        # Get voice profile information if available
        voice_info = self._format_voice_profiles_for_prompt()
        
        # Convert category from snake_case to human-readable
        category_display = category.replace('_', ' ').title()
        
        prompt = f"""Generate realistic {self.config.legit_call_language} phone call dialogue between a caller and a callee from {self.config.legit_call_region}.
The call content is about {category_display}.

{voice_info}

The total number of turns must be exactly {num_turns} individual turns (i.e., lines), alternating between caller and callee.

Avoid overly generic or repetitive phrasing - the dialogue should feel natural and realistic.

To protect privacy, do not use real personal data. Instead, generate synthetic but plausible realistic-looking values.

Shorter sentences are preferred.

Generate exactly {num_turns} dialogue turns, starting with "caller" role.

Example format for dialogue field:
[
  {{"text": "Hello, this is the delivery service...", "role": "caller"}},
  {{"text": "Yes, I'm expecting a package...", "role": "callee"}},
  {{"text": "Great, we'll deliver it tomorrow...", "role": "caller"}},
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
        output_path = self.config.legit_call_output_path
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
        
        self.clogger.info(f"Saved legitimate conversations to {output_path}", force=True)