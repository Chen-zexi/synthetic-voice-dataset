"""
Qwen-MT translator implementation using OpenAI SDK with async support.
"""

import os
import logging
import asyncio
import time
from typing import Dict, List, Optional
from pathlib import Path
import json

from openai import OpenAI, AsyncOpenAI
from tqdm import tqdm

from translation.translator import BaseTranslator
from config.config_loader import Config
from translation.language_codes import get_language_code


logger = logging.getLogger(__name__)


class QwenTranslator(BaseTranslator):
    """
    Qwen-MT translator implementation using OpenAI SDK.
    Supports both synchronous and asynchronous translation with concurrent API calls.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Qwen translator.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
        
        # Get API key from environment or config
        self.api_key = os.getenv("DASHSCOPE_API_KEY") or getattr(config, 'dashscope_api_key', None)
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not found in environment or config")
        
        # Get base URL and model from config with defaults
        self.base_url = getattr(config, 'qwen_base_url', "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        self.model = getattr(config, 'qwen_model', "qwen-mt-turbo")
        
        # Concurrency settings
        self.max_concurrent = getattr(config, 'max_concurrent_translations', 10)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Retry settings
        self.retry_count = 3
        self.retry_delay = 1.0
        
        # Initialize OpenAI clients
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    
    async def translate_text(self, text: str, from_code: str, to_code: str, 
                            terminology: Optional[Dict[str, str]] = None,
                            domain: Optional[str] = None) -> str:
        """
        Translate text using Qwen-MT with advanced features.
        
        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code
            terminology: Optional terminology mapping for consistent translation
            domain: Optional domain for specialized translation
            
        Returns:
            Translated text
        """
        if not text.strip():
            return text
        
        # Map language codes for Qwen-MT
        source_lang = get_language_code('qwen', from_code)
        target_lang = get_language_code('qwen', to_code)
        
        async with self.semaphore:
            for attempt in range(self.retry_count):
                try:
                    # Prepare translation options
                    translation_options = {
                        "source_lang": source_lang,
                        "target_lang": target_lang
                    }
                    
                    # Add terminology if provided
                    if terminology:
                        translation_options["terminology"] = terminology
                    
                    # Add domain if provided
                    if domain:
                        translation_options["domain"] = domain
                    
                    # Make the async translation request
                    completion = await self.async_client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": text}],
                        extra_body={"translation_options": translation_options}
                    )
                    
                    # Extract translated text
                    translated = completion.choices[0].message.content
                    
                    # Track token usage if enabled
                    if self.token_tracker and hasattr(completion, 'usage'):
                        usage = completion.usage
                        token_info = {
                            'input_tokens': usage.prompt_tokens,
                            'output_tokens': usage.completion_tokens,
                            'total_tokens': usage.total_tokens
                        }
                        self.token_tracker.add_usage(
                            token_info,
                            self.model,
                            f"translate_{source_lang}_to_{target_lang}"
                        )
                    
                    self.clogger.debug(f"Translated: '{text[:50]}...' -> '{translated[:50]}...'")
                    return translated
                    
                except Exception as e:
                    logger.warning(f"Async translation attempt {attempt + 1} failed: {e}")
                    if attempt < self.retry_count - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        logger.error(f"Async translation failed after {self.retry_count} attempts")
                        return text  # Return original text if translation fails
    
    def _build_system_prompt(self, source_code: str, target_code: str,
                            terminology: Optional[Dict[str, str]] = None,
                            domain: Optional[str] = None) -> str:
        """
        Build system prompt for Qwen-MT with advanced features.
        
        Args:
            source_code: Source language code
            target_code: Target language code
            terminology: Optional terminology mapping
            domain: Optional domain specification
            
        Returns:
            System prompt string
        """
        prompt = f"Translate from {source_code} to {target_code}."
        
        if domain:
            prompt += f" Use {domain} domain-specific terminology."
        
        if terminology:
            terms_list = [f"'{src}' -> '{tgt}'" for src, tgt in terminology.items()]
            prompt += f" Use these translations: {', '.join(terms_list)}."
        
        prompt += " Only output the translation without any explanation."
        
        return prompt
    
    async def translate_conversations(self, input_path: Path, output_path: Path,
                                     from_code: str, to_code: str, max_concurrent: int = 5):
        """
        Translate conversation JSON files with concurrent processing.
        
        Args:
            input_path: Input JSON file path
            output_path: Output JSON file path
            from_code: Source language code
            to_code: Target language code
            max_concurrent: Maximum concurrent conversations to process
        """
        self.clogger.info(f"Translating conversations: {input_path} ({from_code} -> {to_code})", force=True)
        
        # Load conversations using base class helper method
        conversations = self._load_conversations_from_json(input_path)
        
        # Load placeholder mapping
        with open(self.config.preprocessing_map_path, 'r', encoding='utf-8') as f:
            placeholder_map = json.load(f)
        
        # Use semaphore for rate limiting with the specified concurrency
        if max_concurrent != self.max_concurrent:
            semaphore = asyncio.Semaphore(max_concurrent)
        else:
            semaphore = self.semaphore
        
        # Create tasks for concurrent translation with rate limiting
        async def translate_with_semaphore(conv_idx: int, conversation: Dict) -> tuple:
            async with semaphore:
                result = await self._translate_conversation_async(
                    conversation, conv_idx, len(conversations), 
                    from_code, to_code, placeholder_map
                )
                return conv_idx, result
        
        tasks = [translate_with_semaphore(i, conv) for i, conv in enumerate(conversations)]
        
        # Execute translations concurrently with progress bar
        self.clogger.info(f"Starting concurrent translation of {len(conversations)} conversations")
        
        with tqdm(total=len(tasks), desc="Translating conversations") as pbar:
            results = []
            for task in asyncio.as_completed(tasks):
                conv_idx, translated_conv = await task
                results.append((conv_idx, translated_conv))
                pbar.update(1)
        
        # Sort results by original index and extract conversations
        results.sort(key=lambda x: x[0])
        translated_conversations = [conv for _, conv in results]
        
        # Save translated conversations
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translated_conversations, f, ensure_ascii=False, indent=2)
        
        self.clogger.info(f"Translated {len(conversations)} conversations", force=True)
    
    async def _translate_conversation_async(self, conversation: Dict, conv_idx: int, 
                                          total: int, from_code: str, to_code: str,
                                          placeholder_map: Dict[str, Dict]) -> Dict:
        """
        Translate a single conversation asynchronously.
        
        Args:
            conversation: Conversation dictionary
            conv_idx: Conversation index
            total: Total number of conversations
            from_code: Source language code
            to_code: Target language code
            placeholder_map: Placeholder mapping dictionary
            
        Returns:
            Translated conversation dictionary
        """
        self.clogger.debug(f"Translating conversation {conv_idx + 1}/{total}")
        
        # Create substitution cache for consistent replacements
        substitution_cache = {}
        
        translated_conv = conversation.copy()
        
        # Translate dialogue turns
        if "dialogue" in translated_conv:
            for turn in translated_conv["dialogue"]:
                # Translate text asynchronously
                translated_text = await self.translate_text(
                    turn["text"], from_code, to_code
                )
                
                # Fill placeholders
                turn["text"] = self._fill_placeholders(
                    translated_text, placeholder_map, substitution_cache
                )
        
        # Update first_turn if present
        if translated_conv.get("dialogue"):
            translated_conv["first_turn"] = translated_conv["dialogue"][0]["text"]
        
        return translated_conv
    
    def get_token_summary(self):
        """Get token usage summary with cost estimation for Qwen models."""
        if not self.token_tracker:
            return None
        
        # Load model pricing from config
        try:
            config_path = Path(__file__).parent / "model_config.json"
            with open(config_path, 'r') as f:
                model_config = json.load(f)
            
            # Get pricing for the current model
            pricing = {}
            for model_info in model_config['models']['qwen']:
                if model_info['id'] == self.model:
                    # Convert from per 1M tokens to per 1K tokens for compatibility
                    pricing[self.model] = {
                        'input': model_info['pricing']['input'] / 1000,
                        'output': model_info['pricing']['output'] / 1000
                    }
                    break
            
            # Return summary with costs
            return {
                'summary': self.token_tracker.get_summary(include_details=False),
                'cost': self.token_tracker.estimate_cost(pricing)
            }
        except Exception as e:
            logger.warning(f"Could not load pricing config: {e}")
            return {
                'summary': self.token_tracker.get_summary(include_details=False),
                'cost': None
            }
    
