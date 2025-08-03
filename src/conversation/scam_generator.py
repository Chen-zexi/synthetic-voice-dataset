"""
Scam conversation generator using OpenAI GPT-4.
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

from openai import OpenAI
from config.config_loader import Config


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
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = "gpt-4o"
    
    def generate_conversations(self) -> List[Dict]:
        """
        Generate scam conversations based on input first turns.
        
        Returns:
            List of conversation dictionaries
        """
        logger.info(f"Generating scam conversations from {self.config.multi_turn_input_path}")
        
        # Load first turns
        with open(self.config.multi_turn_input_path, 'r', encoding='utf-8') as f:
            first_turns = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(first_turns)} first turns")
        
        all_conversations = []
        
        # Process each first turn
        for idx, first_turn in enumerate(tqdm(first_turns[:self.config.sample_limit], 
                                            desc="Generating conversations")):
            if idx >= self.config.max_conversation:
                break
            
            # Generate conversation
            conversation = self._generate_single_conversation(idx + 1, first_turn)
            if conversation:
                all_conversations.append(conversation)
            else:
                logger.warning(f"Failed to generate conversation {idx + 1}")
        
        # Save conversations
        self._save_conversations(all_conversations)
        
        logger.info(f"Generated {len(all_conversations)} conversations")
        return all_conversations
    
    def _generate_single_conversation(self, conversation_id: int, first_turn: str) -> Optional[Dict]:
        """
        Generate a single conversation.
        
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
        dialogue = self._generate_dialogue(first_turn, num_turns, victim_awareness)
        
        if dialogue:
            return {
                "conversation_id": conversation_id,
                "first_turn": first_turn,
                "num_turns": num_turns,
                "victim_awareness": victim_awareness,
                "dialogue": dialogue
            }
        
        return None
    
    def _generate_dialogue(self, first_turn: str, num_turns: int, 
                          victim_awareness: str) -> Optional[List[Dict]]:
        """
        Generate dialogue turns using GPT-4.
        
        Args:
            first_turn: Opening line
            num_turns: Number of turns to generate
            victim_awareness: Victim's awareness level
            
        Returns:
            List of dialogue turns or None if generation failed
        """
        prompt = self._create_prompt(first_turn, num_turns, victim_awareness)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_tokens=3000,
                top_p=0.95,
                n=1
            )
            
            response_text = response.choices[0].message.content.strip()
            return self._parse_json_response(response_text)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def _create_prompt(self, first_turn: str, num_turns: int, 
                      victim_awareness: str) -> str:
        """
        Create the prompt for GPT-4.
        
        Args:
            first_turn: Opening line
            num_turns: Number of turns
            victim_awareness: Victim's awareness level
            
        Returns:
            Formatted prompt
        """
        return f"""Continue the scam phone call dialogue between the caller (scammer) and callee (victim). The victim is {victim_awareness} aware of the scam.

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
    
    Output format (must be valid JSON):
    A list of {num_turns} objects, where:
    - The first object must have `"text"` equal to the shortened version of the first sentence (as defined above).
    - The `"role"` alternates between `"caller"` and `"callee"`.
    - The `"sent_id"` starts at 1 and increments by 1.

    Example format:
    [
        {{
            "sent_id": 1,
            "text": "...",
            "role": "caller"
        }},
        {{
            "sent_id": 2,
            "text": "...",
            "role": "callee"
        }},
        ...
    ]
    """
    
    def _parse_json_response(self, response_text: str) -> Optional[List[Dict]]:
        """
        Parse JSON response from GPT-4.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Parsed JSON list or None if parsing failed
        """
        try:
            # Find JSON array in the response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                logger.error("Could not find JSON array in response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return None
    
    def _save_conversations(self, conversations: List[Dict]):
        """
        Save conversations to JSON file.
        
        Args:
            conversations: List of conversation dictionaries
        """
        output_path = self.config.multi_turn_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved conversations to {output_path}")