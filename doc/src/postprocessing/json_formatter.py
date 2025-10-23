"""
JSON formatter for finalizing conversation data with proper labels and structure.
"""

import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict

from config.config_loader import Config
from utils.logging_utils import ConditionalLogger, create_progress_bar


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
        self.clogger = ConditionalLogger(__name__, config.verbose)
        
        # Load fields to exclude from config or use defaults
        self.exclude_fields = [
            "first_turn",
            "voice_mapping",
            "scenario",
            "metadata",
            "victim_awareness",
            "category"
        ]
        
        # Try to load from config if available
        try:
            import json
            from pathlib import Path
            common_config_path = Path("configs/common.json")
            if common_config_path.exists():
                with open(common_config_path, 'r') as f:
                    common_config = json.load(f)
                    self.exclude_fields = common_config.get("post_processing", {}).get("exclude_fields", self.exclude_fields)
        except Exception as e:
            self.clogger.debug(f"Using default exclude fields: {e}")
    
    def format_all(self):
        """
        Format both scam and legitimate conversation JSON files.
        """
        self.clogger.info("Formatting JSON files")
        
        # Check which files exist
        scam_exists = self.config.post_processing_scam_json_input.exists()
        legit_exists = self.config.post_processing_legit_json_input.exists()
        
        num_files = sum([scam_exists, legit_exists])
        if num_files == 0:
            self.clogger.warning("No conversation files found to format")
            return
        
        if not self.config.verbose:
            pbar = create_progress_bar(num_files, "Formatting conversations", "files")
        
        # Format scam conversations if they exist
        if scam_exists:
            self._format_scam_conversations()
            if not self.config.verbose:
                pbar.update(1)
        
        # Format legitimate conversations if they exist
        if legit_exists:
            self._format_legit_conversations()
            if not self.config.verbose:
                pbar.update(1)
        
        if not self.config.verbose and 'pbar' in locals():
            pbar.close()
    
    def _format_scam_conversations(self):
        """
        Format scam conversation JSON with region and is_vp labels.
        """
        input_path = self.config.post_processing_scam_json_input
        output_path = self.config.post_processing_scam_json_output
        
        if not input_path.exists():
            self.clogger.warning(f"Scam conversation file not found: {input_path}")
            return
        
        self.clogger.debug(f"Formatting scam conversations: {input_path}")
        
        # Load conversations
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both wrapped format (with 'conversations' key) and plain array format
        if isinstance(data, dict):
            conversations = data.get('conversations', [])
        elif isinstance(data, list):
            conversations = data
        else:
            raise ValueError(f"Unexpected data format in {input_path}: {type(data)}")
        
        # Format each conversation
        formatted_conversations = []
        for conv in conversations:
            formatted = self._format_scam_conversation(conv)
            formatted_conversations.append(formatted)
        
        # Save formatted conversations
        self._save_json(formatted_conversations, output_path)
        
        self.clogger.debug(f"Formatted {len(formatted_conversations)} scam conversations")
    
    def _format_legit_conversations(self):
        """
        Format legitimate conversation JSON with is_vp label.
        """
        input_path = self.config.post_processing_legit_json_input
        output_path = self.config.post_processing_legit_json_output
        
        if not input_path.exists():
            self.clogger.warning(f"Legitimate conversation file not found: {input_path}")
            return
        
        self.clogger.debug(f"Formatting legitimate conversations: {input_path}")
        
        # Load conversations
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both wrapped format (with 'conversations' key) and plain array format
        if isinstance(data, dict):
            conversations = data.get('conversations', [])
        elif isinstance(data, list):
            conversations = data
        else:
            raise ValueError(f"Unexpected data format in {input_path}: {type(data)}")
        
        # Format each conversation
        formatted_conversations = []
        for conv in conversations:
            formatted = self._format_legit_conversation(conv)
            formatted_conversations.append(formatted)
        
        # Save formatted conversations
        self._save_json(formatted_conversations, output_path)
        
        self.clogger.debug(f"Formatted {len(formatted_conversations)} legitimate conversations")
    
    def _format_scam_conversation(self, conversation: Dict) -> OrderedDict:
        """
        Format a single scam conversation.
        
        Args:
            conversation: Original conversation dictionary
            
        Returns:
            Formatted conversation as OrderedDict
        """
        # Transform conversation structure
        conv = conversation.copy()
        
        if "victim_awareness" in conv:
            conv.pop("victim_awareness")
        if "num_turns" in conv:
            conv.pop("num_turns")
        for utter in conv['dialogue']:
            if "role" in utter:
                utter["RX/TX"] = utter.pop("role")
                utter["RX/TX"] = utter["RX/TX"].replace('caller', 'TX').replace('callee', 'RX')
            if "text" in utter:
                utter["stt_text"] = utter.pop("text")
        conv['full_content'] = conv.pop('dialogue')
        
        # Use configured fields to exclude
        internal_fields = self.exclude_fields
        
        # Create ordered dictionary with required fields first
        formatted = OrderedDict()
        formatted["region"] = self.config.post_processing_region
        formatted["is_vp"] = self.config.post_processing_scam_label
        
        # Add remaining fields, excluding internal ones
        for key, value in conv.items():
            if key not in internal_fields:
                formatted[key] = value
        
        return formatted
    
    def _format_legit_conversation(self, conversation: Dict) -> OrderedDict:
        """
        Format a single legitimate conversation.
        
        Args:
            conversation: Original conversation dictionary
            
        Returns:
            Formatted conversation as OrderedDict
        """
        # Transform conversation structure
        conv = conversation.copy()
        
        if "victim_awareness" in conv:
            conv.pop("victim_awareness")
        if "num_turns" in conv:
            conv.pop("num_turns")
        for utter in conv['dialogue']:
            if "role" in utter:
                utter["RX/TX"] = utter.pop("role")
                utter["RX/TX"] = utter["RX/TX"].replace('caller', 'TX').replace('callee', 'RX')
            if "text" in utter:
                utter["stt_text"] = utter.pop("text")
        conv['full_content'] = conv.pop('dialogue')
        
        # Use configured fields to exclude
        internal_fields = self.exclude_fields
        
        # Create ordered dictionary with is_vp field first
        formatted = OrderedDict()
        formatted["is_vp"] = self.config.post_processing_legit_label
        
        # Add remaining fields, excluding internal ones
        for key, value in conv.items():
            if key not in internal_fields:
                formatted[key] = value
        
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
        
        self.clogger.debug(f"Saved formatted JSON to {output_path}")