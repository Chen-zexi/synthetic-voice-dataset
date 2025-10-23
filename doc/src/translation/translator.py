"""
Base translator interface and factory for translation services.
"""

import json
import logging
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import re
import random
from tqdm import tqdm

from config.config_loader import Config
from translation.language_codes import get_language_code
from utils.logging_utils import ConditionalLogger


logger = logging.getLogger(__name__)


class BaseTranslator(ABC):
    """
    Abstract base class for translation services.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the translator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.placeholder_pattern = re.compile(r'\{\d{5}\}')
        self.clogger = ConditionalLogger(__name__, config.verbose)
        
        # Initialize token tracker if enabled
        track_tokens = getattr(config, 'translation_track_tokens', False)
        if track_tokens:
            from llm_core.token_counter import TokenUsageTracker
            self.token_tracker = TokenUsageTracker(verbose=False)
        else:
            self.token_tracker = None
    
    def _load_conversations_from_json(self, input_path: Path) -> List[Dict]:
        """
        Load conversations from JSON file, handling wrapped structures.
        
        Args:
            input_path: Path to JSON file
            
        Returns:
            List of conversation dictionaries
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures (wrapped or plain array)
        if isinstance(data, dict):
            # If it's a wrapped structure (e.g., with token usage info), extract conversations
            if "conversations" in data:
                return data["conversations"]
            else:
                # Might be a single conversation
                return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError(f"Unexpected JSON structure in {input_path}")
    
    @abstractmethod
    async def translate_text(self, text: str, from_code: str, to_code: str) -> str:
        """
        Translate a single text string asynchronously.
        
        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code
            
        Returns:
            Translated text
        """
        pass
    
    async def translate_file(self, input_path: Path, output_path: Path, 
                            from_code: str, to_code: str, max_lines: Optional[int] = None,
                            max_concurrent: int = 10):
        """
        Translate a text file with concurrent processing.
        
        Args:
            input_path: Input file path
            output_path: Output file path
            from_code: Source language code
            to_code: Target language code
            max_lines: Maximum number of lines to translate
            max_concurrent: Maximum concurrent translations
        """
        # Get service name for logging
        service_name = self.__class__.__name__.replace('Translator', '')
        if service_name == 'Qwen' and hasattr(self, 'model'):
            service_info = f"{service_name} ({self.model})"
        else:
            service_info = service_name
            
        self.clogger.info(f"Translating file using {service_info}: {input_path} ({from_code} -> {to_code})", force=True)
        
        # Read all lines
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]
            if max_lines:
                lines = lines[:max_lines]
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def translate_with_semaphore(line_text: str, line_num: int):
            async with semaphore:
                return await self.translate_text(line_text, from_code, to_code), line_num
        
        # Process lines concurrently
        self.clogger.info(f"Starting concurrent translation of {len(lines)} lines")
        
        with tqdm(total=len(lines), desc="Translating lines", unit="line") as pbar:
            # Create tasks for all lines
            tasks = [translate_with_semaphore(line, i) for i, line in enumerate(lines) if line.strip()]
            
            # Process with progress updates
            translated_results = []
            for task in asyncio.as_completed(tasks):
                translated_text, line_num = await task
                translated_results.append((line_num, translated_text))
                pbar.update(1)
        
        # Sort results by original line order and write to file
        translated_results.sort(key=lambda x: x[0])
        
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for _, translated_text in translated_results:
                outfile.write(translated_text + '\n')
        
        self.clogger.info(f"Translation complete. Output: {output_path}", force=True)
    
    async def translate_conversations(self, input_path: Path, output_path: Path,
                                     from_code: str, to_code: str, max_concurrent: int = 5):
        """
        Translate conversation JSON files with placeholder filling and concurrent processing.
        
        Args:
            input_path: Input JSON file path
            output_path: Output JSON file path
            from_code: Source language code
            to_code: Target language code
            max_concurrent: Maximum concurrent conversations to process
        """
        # Get service name for logging
        service_name = self.__class__.__name__.replace('Translator', '')
        if service_name == 'Qwen' and hasattr(self, 'model'):
            service_info = f"{service_name} ({self.model})"
        else:
            service_info = service_name
            
        self.clogger.info(f"Translating conversations using {service_info}: {input_path} ({from_code} -> {to_code})", force=True)
        
        # Load conversations using helper method
        conversations = self._load_conversations_from_json(input_path)
        
        # Load placeholder mapping with reconciliation if needed
        placeholder_map = self._load_placeholder_map()
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def translate_conversation(conv_idx: int, conversation: Dict) -> Dict:
            async with semaphore:
                # Validate conversation is a dictionary
                if not isinstance(conversation, dict):
                    logger.warning(f"Skipping non-dict conversation at index {conv_idx}: {type(conversation)}")
                    return None
                    
                self.clogger.debug(f"Translating conversation {conv_idx + 1}/{len(conversations)}")
                
                # Create substitution cache for consistent replacements within conversation
                substitution_cache = {}
                
                translated_conv = conversation.copy()
                
                # Translate dialogue turns concurrently within the conversation
                if "dialogue" in translated_conv:
                    # Create tasks for all turns in this conversation
                    turn_tasks = []
                    for turn in translated_conv["dialogue"]:
                        task = self.translate_text(turn["text"], from_code, to_code)
                        turn_tasks.append(task)
                    
                    # Wait for all turn translations to complete
                    translated_texts = await asyncio.gather(*turn_tasks)
                    
                    # Apply translations and fill placeholders
                    for turn, translated_text in zip(translated_conv["dialogue"], translated_texts):
                        turn["text"] = self._fill_placeholders(
                            translated_text, placeholder_map, substitution_cache
                        )
                
                # Update first_turn if present
                if translated_conv.get("dialogue"):
                    translated_conv["first_turn"] = translated_conv["dialogue"][0]["text"]
                
                return translated_conv
        
        # Process conversations concurrently while maintaining order
        self.clogger.info(f"Starting concurrent translation of {len(conversations)} conversations")
        
        # Create tasks with indices to maintain order
        async def translate_with_index(i: int, conv: Dict) -> tuple:
            result = await translate_conversation(i, conv)
            return i, result
        
        tasks = [translate_with_index(i, conv) for i, conv in enumerate(conversations)]
        
        with tqdm(total=len(conversations), desc="Translating conversations", unit="conv") as pbar:
            # Process all tasks concurrently
            results = []
            for task in asyncio.as_completed(tasks):
                index, translated_conv = await task
                results.append((index, translated_conv))
                pbar.update(1)
        
        # Sort by original index and extract conversations (filter out None results)
        results.sort(key=lambda x: x[0])
        translated_conversations = [conv for _, conv in results if conv is not None]
        
        # Save translated conversations
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translated_conversations, f, ensure_ascii=False, indent=2)
        
        self.clogger.info(f"Translated {len(conversations)} conversations", force=True)
    
    def _fill_placeholders(self, text: str, placeholder_map: Dict[str, Dict],
                          substitution_cache: Dict[str, str]) -> str:
        """
        Replace placeholder codes with appropriate substitutions.
        
        Args:
            text: Text containing placeholders
            placeholder_map: Mapping of codes to substitutions
            substitution_cache: Cache for consistent substitutions
            
        Returns:
            Text with placeholders filled
        """
        def replace_placeholder(match):
            code = match.group(0)
            
            # Check cache first
            if code in substitution_cache:
                return substitution_cache[code]
            
            # Get substitution from map
            if code in placeholder_map:
                entry = placeholder_map[code]
                substitutions = entry.get('substitutions', [])
                
                if substitutions:
                    # Choose random substitution and cache it
                    substitution = random.choice(substitutions)
                    substitution_cache[code] = substitution
                    return substitution
            
            # Return code if no substitution found
            self.clogger.warning(f"No substitution found for {code}")
            return code
        
        return self.placeholder_pattern.sub(replace_placeholder, text)
    
    def _load_placeholder_map(self) -> Dict[str, Dict]:
        """
        Load placeholder mapping with reconciliation if dynamic map exists.
        
        Returns:
            Placeholder mapping dictionary
        """
        # Check if dynamic map exists
        dynamic_map_path = self.config.output_dir / "intermediate" / "preprocessed" / "dynamic_placeholder_map.json"
        
        if dynamic_map_path.exists():
            # Dynamic map exists, reconcile with pre-populated map
            self.clogger.debug(f"Found dynamic placeholder map, reconciling with pre-populated map")
            
            try:
                reconciler = PlaceholderReconciler(
                    dynamic_map_path=dynamic_map_path,
                    prepopulated_map_path=self.config.preprocessing_map_path
                )
                placeholder_map = reconciler.reconcile()
                
                # Validate and save reconciled map
                if reconciler.validate_reconciliation():
                    reconciler.save_reconciled_map()
                else:
                    self.clogger.warning("Reconciliation validation failed, using reconciled map anyway")
                
                return placeholder_map
                
            except Exception as e:
                self.clogger.error(f"Failed to reconcile placeholder maps: {e}")
                self.clogger.warning("Falling back to pre-populated map")
        
        # Fall back to pre-populated map
        self.clogger.debug(f"Using pre-populated placeholder map from {self.config.preprocessing_map_path}")
        with open(self.config.preprocessing_map_path, 'r', encoding='utf-8') as f:
            return json.load(f)


class TranslatorFactory:
    """
    Factory for creating translator instances.
    """
    
    @staticmethod
    def create(service: str, config: Config) -> BaseTranslator:
        """
        Create a translator instance based on the service type.
        
        Args:
            service: Translation service type ('google' or 'argos')
            config: Configuration object
            
        Returns:
            Translator instance
        """
        if service == "google":
            from translation.google_translator import GoogleTranslator
            return GoogleTranslator(config)
        elif service == "argos":
            from translation.argos_translator import ArgosTranslator
            return ArgosTranslator(config)
        elif service == "qwen":
            from translation.qwen_translator import QwenTranslator
            return QwenTranslator(config)
        else:
            raise ValueError(f"Unknown translation service: {service}")