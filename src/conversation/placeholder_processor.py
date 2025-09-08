"""
Dynamic placeholder processor for generating diverse conversations.
"""

import json
import random
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger(__name__)


class DynamicPlaceholderProcessor:
    """
    Processes dynamic placeholders by randomly selecting from available options.
    Ensures consistency within a single conversation while providing diversity across conversations.
    """
    
    def __init__(self, placeholders_file: Optional[Path] = None):
        """
        Initialize the placeholder processor.
        
        Args:
            placeholders_file: Path to the placeholders.json file
        """
        self.placeholders_file = placeholders_file
        self.placeholders: Dict[str, Any] = {}
        self.current_selections: Dict[str, str] = {}
        
        if placeholders_file and placeholders_file.exists():
            self.load_placeholders()
    
    def load_placeholders(self):
        """Load placeholder definitions from JSON file."""
        if not self.placeholders_file or not self.placeholders_file.exists():
            logger.warning(f"Placeholders file not found: {self.placeholders_file}")
            return
        
        try:
            with open(self.placeholders_file, 'r', encoding='utf-8') as f:
                self.placeholders = json.load(f)
            logger.info(f"Loaded {len(self.placeholders)} placeholder definitions")
        except Exception as e:
            logger.error(f"Failed to load placeholders: {e}")
            self.placeholders = {}
    
    def process_text(self, text: str, conversation_id: Optional[str] = None) -> str:
        """
        Process text by replacing placeholders with dynamically selected values.
        
        Args:
            text: Text containing placeholders like {00001}, {00002}, etc.
            conversation_id: Optional ID to ensure consistency within a conversation
            
        Returns:
            Text with placeholders replaced
        """
        if not self.placeholders:
            return text
        
        # If we have a conversation_id, maintain consistency for this conversation
        if conversation_id:
            if not hasattr(self, '_conversation_selections'):
                self._conversation_selections = {}
            if conversation_id not in self._conversation_selections:
                self._conversation_selections[conversation_id] = {}
            current_selections = self._conversation_selections[conversation_id]
        else:
            # Use instance-level selections for backward compatibility
            current_selections = self.current_selections
        
        processed_text = text
        
        # Find all placeholder codes in the text
        import re
        placeholder_pattern = re.compile(r'\{(\d{5})\}')
        found_placeholders = placeholder_pattern.findall(text)
        
        for placeholder_num in found_placeholders:
            placeholder_code = f"{{{placeholder_num}}}"
            
            if placeholder_code in self.placeholders:
                # Check if we've already selected a value for this placeholder in this conversation
                if placeholder_code in current_selections:
                    replacement = current_selections[placeholder_code]
                else:
                    # Select a new value
                    replacement = self._select_value(placeholder_code)
                    current_selections[placeholder_code] = replacement
                
                # Replace all instances of this placeholder
                processed_text = processed_text.replace(placeholder_code, replacement)
        
        return processed_text
    
    def _select_value(self, placeholder_code: str) -> str:
        """
        Select a value for a placeholder, handling both single values and arrays.
        
        Args:
            placeholder_code: The placeholder code (e.g., "{00001}")
            
        Returns:
            Selected value
        """
        placeholder_data = self.placeholders.get(placeholder_code, {})
        
        # Handle different data formats
        if isinstance(placeholder_data, str):
            # Simple string value
            return placeholder_data
        elif isinstance(placeholder_data, dict):
            # Complex object with substitutions
            substitutions = placeholder_data.get('substitutions', [])
            if isinstance(substitutions, list) and substitutions:
                # Array of values - select randomly
                return random.choice(substitutions)
            elif isinstance(substitutions, str):
                # Single string value
                return substitutions
            else:
                # Fall back to the placeholder code itself
                logger.warning(f"No substitutions found for {placeholder_code}")
                return placeholder_code
        elif isinstance(placeholder_data, list):
            # Direct array
            return random.choice(placeholder_data)
        
        # Fallback
        return placeholder_code
    
    def reset_selections(self, conversation_id: Optional[str] = None):
        """
        Reset placeholder selections for a new conversation.
        
        Args:
            conversation_id: If provided, reset only this conversation's selections
        """
        if conversation_id:
            if hasattr(self, '_conversation_selections'):
                self._conversation_selections.pop(conversation_id, None)
        else:
            self.current_selections.clear()
    
    def get_conversation_placeholders(self, conversation_id: str) -> Dict[str, str]:
        """
        Get all placeholder selections for a specific conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Dictionary of placeholder selections
        """
        if hasattr(self, '_conversation_selections'):
            return self._conversation_selections.get(conversation_id, {})
        return {}
    
    def get_available_options(self, placeholder_code: str) -> List[str]:
        """
        Get all available options for a placeholder.
        
        Args:
            placeholder_code: The placeholder code
            
        Returns:
            List of available options
        """
        placeholder_data = self.placeholders.get(placeholder_code, {})
        
        if isinstance(placeholder_data, dict):
            substitutions = placeholder_data.get('substitutions', [])
            if isinstance(substitutions, list):
                return substitutions
            elif isinstance(substitutions, str):
                return [substitutions]
        elif isinstance(placeholder_data, list):
            return placeholder_data
        elif isinstance(placeholder_data, str):
            return [placeholder_data]
        
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about placeholder usage.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_placeholders': len(self.placeholders),
            'dynamic_placeholders': 0,
            'static_placeholders': 0,
            'placeholder_options': {}
        }
        
        for code, data in self.placeholders.items():
            options = self.get_available_options(code)
            stats['placeholder_options'][code] = len(options)
            
            if len(options) > 1:
                stats['dynamic_placeholders'] += 1
            else:
                stats['static_placeholders'] += 1
        
        return stats
