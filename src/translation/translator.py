"""
Base translator interface and factory for translation services.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import re
import random

from config.config_loader import Config
from translation.language_codes import get_language_code


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
    
    @abstractmethod
    def translate_text(self, text: str, from_code: str, to_code: str) -> str:
        """
        Translate a single text string.
        
        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code
            
        Returns:
            Translated text
        """
        pass
    
    def translate_file(self, input_path: Path, output_path: Path, 
                      from_code: str, to_code: str, max_lines: Optional[int] = None):
        """
        Translate a text file line by line.
        
        Args:
            input_path: Input file path
            output_path: Output file path
            from_code: Source language code
            to_code: Target language code
            max_lines: Maximum number of lines to translate
        """
        logger.info(f"Translating file: {input_path} ({from_code} -> {to_code})")
        
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                if max_lines and line_num > max_lines:
                    break
                
                # Translate line
                translated = self.translate_text(line.strip(), from_code, to_code)
                outfile.write(translated + '\n')
                
                if line_num % 10 == 0:
                    logger.debug(f"Translated {line_num} lines")
        
        logger.info(f"Translation complete. Output: {output_path}")
    
    def translate_conversations(self, input_path: Path, output_path: Path,
                               from_code: str, to_code: str):
        """
        Translate conversation JSON files with placeholder filling.
        
        Args:
            input_path: Input JSON file path
            output_path: Output JSON file path
            from_code: Source language code
            to_code: Target language code
        """
        logger.info(f"Translating conversations: {input_path} ({from_code} -> {to_code})")
        
        # Load conversations
        with open(input_path, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        # Load placeholder mapping
        with open(self.config.preprocessing_map_path, 'r', encoding='utf-8') as f:
            placeholder_map = json.load(f)
        
        translated_conversations = []
        
        for conv_idx, conversation in enumerate(conversations):
            logger.debug(f"Translating conversation {conv_idx + 1}/{len(conversations)}")
            
            # Create substitution cache for consistent replacements within conversation
            substitution_cache = {}
            
            translated_conv = conversation.copy()
            
            # Translate dialogue turns
            if "dialogue" in translated_conv:
                for turn in translated_conv["dialogue"]:
                    # Translate text
                    translated_text = self.translate_text(
                        turn["text"], from_code, to_code
                    )
                    
                    # Fill placeholders
                    turn["text"] = self._fill_placeholders(
                        translated_text, placeholder_map, substitution_cache
                    )
            
            # Update first_turn if present
            if translated_conv.get("dialogue"):
                translated_conv["first_turn"] = translated_conv["dialogue"][0]["text"]
            
            translated_conversations.append(translated_conv)
        
        # Save translated conversations
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translated_conversations, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Translated {len(conversations)} conversations")
    
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
            logger.warning(f"No substitution found for {code}")
            return code
        
        return self.placeholder_pattern.sub(replace_placeholder, text)


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
        else:
            raise ValueError(f"Unknown translation service: {service}")