"""
Post-processing utilities for conversation quality improvements.
Handles: random interruptions/hangups, number redaction, symbol removal.
"""

import random
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ConversationPostProcessor:
    """
    Post-processes generated conversations for quality improvements.
    """
    
    def __init__(self, 
                 interruption_rate: float = 0.10,
                 enable_interruptions: bool = True,
                 enable_redaction: bool = True,
                 enable_symbol_removal: bool = True):
        """
        Initialize post-processor.
        
        Args:
            interruption_rate: Probability of conversation interruption (0.0-1.0)
            enable_interruptions: Whether to apply random interruptions
            enable_redaction: Whether to redact numbers
            enable_symbol_removal: Whether to remove formatting symbols
        """
        self.interruption_rate = interruption_rate
        self.enable_interruptions = enable_interruptions
        self.enable_redaction = enable_redaction
        self.enable_symbol_removal = enable_symbol_removal
    
    def process_conversation(self, conversation: Dict, conversation_type: str = "scam") -> Dict:
        """
        Apply all post-processing steps to a conversation.
        
        Args:
            conversation: Conversation dictionary with 'dialogue' list
            conversation_type: 'scam' or 'legit' (affects interruption reasons)
            
        Returns:
            Processed conversation dictionary
        """
        # Apply interruptions first (may shorten dialogue)
        if self.enable_interruptions and random.random() < self.interruption_rate:
            conversation = self._apply_interruption(conversation, conversation_type)
        
        # Apply text transformations to dialogue
        if conversation.get('dialogue'):
            for turn in conversation['dialogue']:
                if 'text' in turn:
                    # Remove formatting symbols
                    if self.enable_symbol_removal:
                        turn['text'] = self._remove_formatting_symbols(turn['text'])
                    
                    # Redact numbers
                    if self.enable_redaction:
                        turn['text'] = self._redact_numbers(turn['text'])
        
        return conversation
    
    def _apply_interruption(self, conversation: Dict, conversation_type: str) -> Dict:
        """
        Randomly interrupt conversation with contextual reason.
        
        Args:
            conversation: Conversation dictionary
            conversation_type: 'scam' or 'legit'
            
        Returns:
            Modified conversation with interruption
        """
        dialogue = conversation.get('dialogue', [])
        if len(dialogue) < 6:  # Don't interrupt very short conversations
            return conversation
        
        # Choose interruption point (between 40-80% through conversation)
        min_turn = int(len(dialogue) * 0.4)
        max_turn = int(len(dialogue) * 0.8)
        interruption_point = random.randint(min_turn, max_turn)
        
        # Truncate dialogue
        conversation['dialogue'] = dialogue[:interruption_point]
        
        # Add interruption reason based on type
        if conversation_type == "scam":
            interruption_reasons = [
                "victim_suspicion",
                "victim_verification_attempt", 
                "scammer_detected_resistance",
                "external_interruption"
            ]
            reason = random.choice(interruption_reasons)
            
            interruption_notes = {
                "victim_suspicion": "Victim hung up after becoming suspicious",
                "victim_verification_attempt": "Victim said they would verify and hung up",
                "scammer_detected_resistance": "Scammer ended call after detecting too much resistance",
                "external_interruption": "Call was interrupted unexpectedly"
            }
        else:  # legit
            interruption_reasons = [
                "network_issue",
                "caller_needed_to_go",
                "issue_resolved_early",
                "call_back_requested"
            ]
            reason = random.choice(interruption_reasons)
            
            interruption_notes = {
                "network_issue": "Call dropped due to network issues",
                "caller_needed_to_go": "Caller needed to attend to something else",
                "issue_resolved_early": "Issue was resolved, call ended naturally",
                "call_back_requested": "Caller said they would call back"
            }
        
        # Add metadata
        conversation['interrupted'] = True
        conversation['interruption_reason'] = reason
        conversation['interruption_note'] = interruption_notes[reason]
        conversation['original_num_turns'] = conversation.get('num_turns')
        conversation['num_turns'] = len(conversation['dialogue'])
        
        logger.debug(f"Applied interruption at turn {interruption_point}: {reason}")
        
        return conversation
    
    def _remove_formatting_symbols(self, text: str) -> str:
        """
        Remove formatting symbols that wouldn't appear in spoken dialogue.
        Keeps natural speech punctuation (periods, commas, question marks, exclamation).
        
        Args:
            text: Original dialogue text
            
        Returns:
            Cleaned text
        """
        # Replace colons in case/reference numbers (e.g., "IP-2024-8847362:" becomes "IP 2024 8847362")
        # Pattern: word/letters followed by colon
        text = re.sub(r'([A-Za-z]+):', r'\1', text)
        
        # Replace slashes in non-date contexts
        # Keep date formats like "12/2024" but remove "and/or" style uses
        text = re.sub(r'([a-zA-Z]+)/([a-zA-Z]+)', r'\1 atau \2', text)
        
        # Remove dashes in reference numbers, replace with spaces
        # Pattern: alphanumeric-dash-alphanumeric (e.g., "IP-2024-8847362")
        text = re.sub(r'([A-Za-z0-9]+)-([A-Za-z0-9]+)', r'\1 \2', text)
        
        return text
    
    def _redact_numbers(self, text: str) -> str:
        """
        Redact consecutive numbers (phone, IC, reference numbers) partially.
        Shows first 3-4 digits, redacts rest with X's.
        Preserves money values (preceded by "RM" or currency indicators).
        
        Args:
            text: Original dialogue text
            
        Returns:
            Text with redacted numbers
        """
        # Pattern: consecutive digits (4 or more) that are NOT preceded by "RM" or currency symbols
        def redact_match(match):
            number = match.group(0)
            
            # Don't redact if it's part of a money value
            start_pos = match.start()
            if start_pos >= 2:
                prefix = text[start_pos-2:start_pos]
                if 'RM' in prefix or '$' in prefix:
                    return number
            
            # Don't redact short numbers (years, small amounts)
            if len(number) < 4:
                return number
            
            # Partial redaction: show first 3 digits, redact rest
            visible_digits = 3 if len(number) <= 8 else 4
            redacted = number[:visible_digits] + 'X' * (len(number) - visible_digits)
            
            return redacted
        
        # Find sequences of 4+ digits not preceded by RM
        text = re.sub(r'(?<!RM)\b\d{4,}\b', redact_match, text)
        
        return text


def create_postprocessor_from_config(config: Dict) -> ConversationPostProcessor:
    """
    Create post-processor from configuration dictionary.
    
    Args:
        config: Configuration dictionary (from common.json)
        
    Returns:
        ConversationPostProcessor instance
    """
    post_config = config.get('conversation_postprocessing', {})
    
    return ConversationPostProcessor(
        interruption_rate=post_config.get('interruption_rate', 0.10),
        enable_interruptions=post_config.get('enable_interruptions', True),
        enable_redaction=post_config.get('enable_redaction', True),
        enable_symbol_removal=post_config.get('enable_symbol_removal', True)
    )

