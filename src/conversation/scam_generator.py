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
    
    async def generate_conversations(self) -> List[Dict]:
        """
        Generate scam conversations asynchronously for faster processing.
        
        Returns:
            List of conversation dictionaries
        """
        self.clogger.info(f"Generating scam conversations from {self.config.multi_turn_input_path}", force=True)
        
        # Load first turns
        with open(self.config.multi_turn_input_path, 'r', encoding='utf-8') as f:
            first_turns = [line.strip() for line in f if line.strip()]
        
        self.clogger.info(f"Loaded {len(first_turns)} first turns")
        
        # Prepare tasks
        tasks = []
        for idx, first_turn in enumerate(first_turns[:self.config.sample_limit]):
            if idx >= self.config.max_conversation:
                break
            
            task = self._generate_single_conversation(idx + 1, first_turn)
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
    
    async def _generate_single_conversation(self, conversation_id: int, first_turn: str) -> Optional[Dict]:
        """
        Generate a single conversation asynchronously.
        
        Args:
            conversation_id: Unique conversation ID
            first_turn: Opening line of the scam
            
        Returns:
            Conversation dictionary or None if generation failed
        """
        # Randomly select conversation parameters
        num_turns = random.randint(
            self.config.num_turns_lower_limit,
            self.config.num_turns_upper_limit
        )
        victim_awareness = random.choice(self.config.victim_awareness_levels)
        
        # Generate dialogue
        dialogue = await self._generate_dialogue(first_turn, num_turns, victim_awareness)
        
        if dialogue:
            # Check if dialogue is a dict with voice_mapping (from LLM response)
            if isinstance(dialogue, dict) and 'dialogue' in dialogue:
                conversation = {
                    "conversation_id": conversation_id,
                    "first_turn": first_turn,
                    "num_turns": num_turns,
                    "victim_awareness": victim_awareness,
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
                    "first_turn": first_turn,
                    "num_turns": num_turns,
                    "victim_awareness": victim_awareness,
                    "dialogue": dialogue
                }
            
            return conversation
        
        return None
    
    async def _generate_dialogue(self, first_turn: str, num_turns: int, 
                                victim_awareness: str) -> Optional[List[Dict]]:
        """
        Generate dialogue turns asynchronously using LLM.
        
        Args:
            first_turn: Opening line
            num_turns: Number of turns to generate
            victim_awareness: Victim's awareness level
            
        Returns:
            List of dialogue turns or None if generation failed
        """
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(first_turn, num_turns, victim_awareness)
        
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
                # Use first_turn as identifier since we don't have conversation_id here
                self.token_tracker.add_usage(
                    token_info,
                    self.llm_model,
                    f"scam_dialogue_{first_turn[:20]}"
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
        return """You are a dialogue generator for creating realistic phone conversations.
Your task is to generate structured dialogues with alternating turns between caller and callee.
Follow all formatting requirements exactly and preserve any special codes in the input.

IMPORTANT: Each dialogue turn must have exactly these fields:
- text: The actual dialogue text
- role: Either "caller" or "callee"

When voice profiles are provided:
1. Consider the gender and age implications from the conversation context
2. Match authority figures with appropriate voice characteristics
3. Ensure realistic voice assignments based on the scenario
4. Output voice_mapping with selected voice names (use just the name, not the full description)"""

    def _create_user_prompt(self, first_turn: str, num_turns: int, 
                           victim_awareness: str) -> str:
        """
        Create the user prompt for conversation generation.
        
        Args:
            first_turn: Opening line
            num_turns: Number of turns
            victim_awareness: Victim's awareness level
            
        Returns:
            Formatted prompt
        """
        # Get voice profile information if available
        voice_info = self._format_voice_profiles_for_prompt()
        
        prompt = f"""Continue the scam phone call dialogue between the caller (scammer) and callee (victim). The victim is {victim_awareness} aware of the scam.

{voice_info}

The total number of turns must be exactly {num_turns} individual turns (i.e., lines), alternating between caller and callee.

**STRICT RULE - FIRST SENTENCE**:  
The conversation **must begin** with a **shortened version** of the first sentence below.  
This means using fewer words while preserving the original intent and **keeping all special codes unchanged and in the same position**.
First sentence to shorten and use as Turn 1: "{first_turn}"

**STRICT RULE - SPECIAL CODE**: 
Special codes (e.g., {{00001}}, {{00002}}, etc.) represent fixed values (e.g., names, organizations, or amounts).
If the first sentence includes special codes, you **must reuse** the exact same codes from the first sentence throughout the dialogue - but only in the same types of places where they were originally used, and they must appear in those places. 
If the first sentence does not include special codes, that's okay. Do **not** use any codes in this case.
Do **not** invent or introduce any new codes under any circumstances.

Shorter sentences are preferred.

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