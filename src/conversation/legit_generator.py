"""
Legitimate conversation generator using OpenAI GPT-4.
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
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = "gpt-4.1"
    
    def generate_conversations(self) -> List[Dict]:
        """
        Generate legitimate conversations for various categories.
        
        Returns:
            List of conversation dictionaries
        """
        logger.info(f"Generating {self.config.num_legit_conversation} legitimate conversations")
        
        all_conversations = []
        
        for idx in tqdm(range(self.config.num_legit_conversation), 
                       desc="Generating legitimate conversations"):
            # Randomly select parameters
            num_turns = random.randint(
                self.config.num_turns_lower_limit,
                self.config.num_turns_upper_limit
            )
            category = random.choice(self.config.legit_call_categories)
            
            # Generate conversation
            conversation = self._generate_single_conversation(
                idx + 1, num_turns, category
            )
            
            if conversation:
                all_conversations.append(conversation)
            else:
                logger.warning(f"Failed to generate conversation {idx + 1}")
        
        # Save conversations
        self._save_conversations(all_conversations)
        
        logger.info(f"Generated {len(all_conversations)} legitimate conversations")
        return all_conversations
    
    def _generate_single_conversation(self, conversation_id: int, num_turns: int,
                                    category: str) -> Optional[Dict]:
        """
        Generate a single legitimate conversation.
        
        Args:
            conversation_id: Unique conversation ID
            num_turns: Number of dialogue turns
            category: Conversation category
            
        Returns:
            Conversation dictionary or None if generation failed
        """
        dialogue = self._generate_dialogue(num_turns, category)
        
        if dialogue:
            return {
                "conversation_id": conversation_id,
                "region": self.config.legit_call_region,
                "category": category,
                "num_turns": num_turns,
                "dialogue": dialogue
            }
        
        return None
    
    def _generate_dialogue(self, num_turns: int, category: str) -> Optional[List[Dict]]:
        """
        Generate dialogue turns using GPT-4.
        
        Args:
            num_turns: Number of turns to generate
            category: Conversation category
            
        Returns:
            List of dialogue turns or None if generation failed
        """
        prompt = self._create_prompt(num_turns, category)
        
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
    
    def _create_prompt(self, num_turns: int, category: str) -> str:
        """
        Create the prompt for GPT-4.
        
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
    
    Output format (must be valid JSON):
    - Output must be a JSON array only - no comments or additional explanations.
    - Each object should have:
      - "sent_id": starting at 1 and incrementing by 1.
      - "text": the dialogue line.
      - "role": alternating exactly between "caller" and "callee", starting with "caller".

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
        output_path = self.config.legit_call_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved legitimate conversations to {output_path}")