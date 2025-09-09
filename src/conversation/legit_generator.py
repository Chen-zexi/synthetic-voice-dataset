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
        self.clogger.debug(f"Generating {self.config.num_legit_conversation} legitimate conversations")
        
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
        
        # Voice selection now handled externally, not by LLM
        
        return locale_prompt
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for legitimate conversation generation.
        Optimized for OpenAI prompt caching - keep this completely static.
        """
        return """You are a dialogue generator for creating realistic phone conversations.

## Core Task
Generate structured dialogues for legitimate (non-scam) phone calls with alternating turns between caller and callee.
The conversations should be natural, contextually appropriate, and culturally relevant.

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


## Important Rules
1. Always alternate between caller and callee roles
2. Start with the caller role
3. Generate the exact number of turns requested
4. Keep the conversation relevant to the specified category
5. Maintain scenario consistency throughout the conversation"""

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
**Number of Turns**: Generate exactly {num_turns} dialogue turns
**Context**: This is a legitimate business/service call about {category_display.lower()}

### Generate the Dialogue

Based on the above parameters, generate exactly {num_turns} dialogue turns for a legitimate {category_display.lower()} phone call following all the specified rules and requirements."""
        
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
        
        self.clogger.info(f"Saved legitimate conversations to {output_path}")