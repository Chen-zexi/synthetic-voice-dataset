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
        
        # Get LLM parameters from config
        llm_temperature = getattr(config, 'llm_temperature', 1.0)
        llm_max_tokens = getattr(config, 'llm_max_tokens', None)
        llm_top_p = getattr(config, 'llm_top_p', 0.95)
        llm_n = getattr(config, 'llm_n', 1)
        
        # Create LLM instance with parameters
        llm_instance = LLM(
            provider=self.llm_provider, 
            model=self.llm_model,
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
            top_p=llm_top_p,
            n=llm_n
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
        dialogue = await self._generate_dialogue(num_turns, category)
        
        if dialogue:
            return {
                "conversation_id": conversation_id,
                "region": self.config.legit_call_region,
                "category": category,
                "num_turns": num_turns,
                "dialogue": dialogue
            }
        
        return None
    
    async def _generate_dialogue(self, num_turns: int, category: str) -> Optional[List[Dict]]:
        """
        Generate dialogue turns asynchronously using LLM.
        
        Args:
            num_turns: Number of turns to generate
            category: Conversation category
            
        Returns:
            List of dialogue turns or None if generation failed
        """
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(num_turns, category)
        
        try:
            # Use async structured output
            response = await make_api_call(
                llm=self.llm,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=LegitConversationResponse
            )
            
            # Convert Pydantic models to dicts
            if hasattr(response, 'dialogue'):
                return [turn.model_dump() for turn in response.dialogue]
            else:
                self.clogger.error("Response missing dialogue field")
                return None
            
        except Exception as e:
            self.clogger.error(f"LLM API error: {e}")
            return None
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for legitimate conversation generation."""
        return """You are a dialogue generator for creating realistic phone conversations.
Your task is to generate structured dialogues for legitimate (non-scam) phone calls with alternating turns between caller and callee.
The conversations should be natural, contextually appropriate, and culturally relevant."""

    def _create_user_prompt(self, num_turns: int, category: str) -> str:
        """
        Create the user prompt for legitimate conversation generation.
        
        Args:
            num_turns: Number of turns
            category: Conversation category
            
        Returns:
            Formatted prompt
        """
        # Convert category from snake_case to human-readable
        category_display = category.replace('_', ' ').title()
        
        return f"""Generate realistic {self.config.legit_call_language} phone call dialogue between a caller and a callee from {self.config.legit_call_region}.
The call content is about {category_display}.
The total number of turns must be exactly {num_turns} individual turns (i.e., lines), alternating between caller and callee.

Avoid overly generic or repetitive phrasing - the dialogue should feel natural and realistic.

To protect privacy, do not use real personal data. Instead, generate synthetic but plausible realistic-looking values.

Shorter sentences are preferred.

Generate exactly {num_turns} dialogue turns, starting with "caller" role."""
    
    def _save_conversations(self, conversations: List[Dict]):
        """
        Save conversations to JSON file.
        
        Args:
            conversations: List of conversation dictionaries
        """
        output_path = self.config.legit_call_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
        
        self.clogger.info(f"Saved legitimate conversations to {output_path}", force=True)