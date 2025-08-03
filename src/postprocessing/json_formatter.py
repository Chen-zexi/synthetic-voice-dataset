"""
JSON formatter for finalizing conversation data with proper labels and structure.
"""

import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict

from config.config_loader import Config


logger = logging.getLogger(__name__)


class JsonFormatter:
    """
    Formats conversation JSON files with region labels and scam indicators.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the JSON formatter.
        
        Args:
            config: Configuration object
        """
        self.config = config
    
    def format_all(self):
        """
        Format both scam and legitimate conversation JSON files.
        """
        logger.info("Formatting JSON files")
        
        # Format scam conversations
        self._format_scam_conversations()
        
        # Format legitimate conversations
        self._format_legit_conversations()
    
    def _format_scam_conversations(self):
        """
        Format scam conversation JSON with region and is_vp labels.
        """
        input_path = self.config.post_processing_scam_json_input
        output_path = self.config.post_processing_scam_json_output
        
        if not input_path.exists():
            logger.warning(f"Scam conversation file not found: {input_path}")
            return
        
        logger.info(f"Formatting scam conversations: {input_path}")
        
        # Load conversations
        with open(input_path, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        # Format each conversation
        formatted_conversations = []
        for conv in conversations:
            formatted = self._format_scam_conversation(conv)
            formatted_conversations.append(formatted)
        
        # Save formatted conversations
        self._save_json(formatted_conversations, output_path)
        
        logger.info(f"Formatted {len(formatted_conversations)} scam conversations")
    
    def _format_legit_conversations(self):
        """
        Format legitimate conversation JSON with is_vp label.
        """
        input_path = self.config.post_processing_legit_json_input
        output_path = self.config.post_processing_legit_json_output
        
        if not input_path.exists():
            logger.warning(f"Legitimate conversation file not found: {input_path}")
            return
        
        logger.info(f"Formatting legitimate conversations: {input_path}")
        
        # Load conversations
        with open(input_path, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        # Format each conversation
        formatted_conversations = []
        for conv in conversations:
            formatted = self._format_legit_conversation(conv)
            formatted_conversations.append(formatted)
        
        # Save formatted conversations
        self._save_json(formatted_conversations, output_path)
        
        logger.info(f"Formatted {len(formatted_conversations)} legitimate conversations")
    
    def _format_scam_conversation(self, conversation: Dict) -> OrderedDict:
        """
        Format a single scam conversation.
        
        Args:
            conversation: Original conversation dictionary
            
        Returns:
            Formatted conversation as OrderedDict
        """
        # Remove 'first_turn' if it exists
        conversation.pop("first_turn", None)
        
        # Create ordered dictionary with required fields first
        formatted = OrderedDict()
        formatted["region"] = self.config.post_processing_region
        formatted["is_vp"] = self.config.post_processing_scam_label
        
        # Add remaining fields
        formatted.update(conversation)
        
        return formatted
    
    def _format_legit_conversation(self, conversation: Dict) -> OrderedDict:
        """
        Format a single legitimate conversation.
        
        Args:
            conversation: Original conversation dictionary
            
        Returns:
            Formatted conversation as OrderedDict
        """
        # Remove 'first_turn' if it exists (shouldn't exist for legit)
        conversation.pop("first_turn", None)
        
        # Create ordered dictionary with is_vp field first
        formatted = OrderedDict()
        formatted["is_vp"] = self.config.post_processing_legit_label
        
        # Add remaining fields
        formatted.update(conversation)
        
        return formatted
    
    def _save_json(self, data: List[Dict], output_path: Path):
        """
        Save formatted data to JSON file.
        
        Args:
            data: List of formatted conversations
            output_path: Path to save the file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save with proper formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved formatted JSON to {output_path}")