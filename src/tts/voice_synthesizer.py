"""
Voice synthesizer using ElevenLabs TTS API.
"""

import json
import os
import random
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from elevenlabs import generate, set_api_key, VoiceSettings
from config.config_loader import Config
from tts.audio_processor import AudioProcessor
from tts.audio_combiner import AudioCombiner


logger = logging.getLogger(__name__)


class VoiceSynthesizer:
    """
    Synthesizes voice audio from text conversations using ElevenLabs.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the voice synthesizer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        set_api_key(config.elevenlabs_api_key)
        self.audio_processor = AudioProcessor(config)
        self.audio_combiner = AudioCombiner(config)
    
    def generate_audio(self, input_file: Path, output_dir: Path, is_scam: bool = True):
        """
        Generate audio for all conversations in the input file.
        
        Args:
            input_file: Path to JSON file containing conversations
            output_dir: Directory to save audio files
            is_scam: Whether these are scam conversations
        """
        logger.info(f"Generating audio from {input_file}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load conversations
        with open(input_file, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        logger.info(f"Found {len(conversations)} conversations to process")
        
        # Process each conversation
        for i, conversation in enumerate(conversations[:self.config.voice_sample_limit]):
            logger.info(f"Processing conversation {i+1}/{min(len(conversations), self.config.voice_sample_limit)}")
            
            try:
                self._process_conversation(conversation, output_dir)
            except Exception as e:
                logger.error(f"Error processing conversation {conversation['conversation_id']}: {e}")
    
    def _process_conversation(self, conversation: Dict, output_dir: Path):
        """
        Process a single conversation to generate audio.
        
        Args:
            conversation: Conversation dictionary
            output_dir: Output directory
        """
        conversation_id = conversation["conversation_id"]
        dialogue = conversation["dialogue"]
        
        # Create conversation directory
        conv_dir = output_dir / f"conversation_{conversation_id:03d}"
        conv_dir.mkdir(exist_ok=True)
        
        # Select voices for caller and callee
        caller_voice, callee_voice = self._select_voices()
        
        logger.info(f"Conversation {conversation_id}: Using voices {caller_voice} (caller) and {callee_voice} (callee)")
        
        audio_files = []
        
        # Generate audio for each turn
        for turn in dialogue:
            audio_info = self._generate_turn_audio(turn, caller_voice, callee_voice, conv_dir)
            if audio_info:
                audio_files.append(audio_info)
        
        # Combine audio files
        combined_path = self.audio_combiner.combine_conversation(conv_dir, conversation_id)
        
        if combined_path:
            # Apply audio processing
            processed_path = self.audio_processor.process_conversation_audio(combined_path)
            
            # Save metadata
            self._save_metadata(conv_dir, conversation_id, caller_voice, callee_voice, audio_files, processed_path)
    
    def _select_voices(self) -> Tuple[str, str]:
        """
        Randomly select two different voices for caller and callee.
        
        Returns:
            Tuple of (caller_voice_id, callee_voice_id)
        """
        voice_ids = self.config.voice_ids[self.config.voice_language]
        
        if len(voice_ids) < 2:
            raise ValueError(f"Need at least 2 voices, but only {len(voice_ids)} available")
        
        selected = random.sample(voice_ids, 2)
        return selected[0], selected[1]
    
    def _generate_turn_audio(self, turn: Dict, caller_voice: str, 
                           callee_voice: str, conv_dir: Path) -> Optional[Dict]:
        """
        Generate audio for a single dialogue turn.
        
        Args:
            turn: Dialogue turn dictionary
            caller_voice: Voice ID for caller
            callee_voice: Voice ID for callee
            conv_dir: Conversation directory
            
        Returns:
            Audio file info dictionary or None if generation failed
        """
        sent_id = turn["sent_id"]
        text = turn["text"]
        role = turn["role"]
        
        # Select voice based on role
        voice_id = caller_voice if role == "caller" else callee_voice
        
        # Generate filename
        filename = f"turn_{sent_id:02d}_{role}.mp3"
        filepath = conv_dir / filename
        
        # Skip if file already exists
        if filepath.exists():
            logger.debug(f"Skipping existing file: {filename}")
            return {
                "turn_id": sent_id,
                "role": role,
                "text": text,
                "voice_id": voice_id,
                "filename": filename
            }
        
        try:
            # Generate audio
            audio_bytes = generate(
                text=text,
                voice=voice_id,
                model=self.config.voice_model_id
            )
            
            # Save audio file
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)
            
            logger.debug(f"Generated: {filename}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
            return {
                "turn_id": sent_id,
                "role": role,
                "text": text,
                "voice_id": voice_id,
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Error generating audio for turn {sent_id}: {e}")
            return None
    
    def _save_metadata(self, conv_dir: Path, conversation_id: int,
                      caller_voice: str, callee_voice: str,
                      audio_files: List[Dict], processed_path: Optional[Path]):
        """
        Save conversation metadata.
        
        Args:
            conv_dir: Conversation directory
            conversation_id: Conversation ID
            caller_voice: Caller voice ID
            callee_voice: Callee voice ID
            audio_files: List of audio file info
            processed_path: Path to processed audio file
        """
        metadata = {
            "conversation_id": conversation_id,
            "caller_voice_id": caller_voice,
            "callee_voice_id": callee_voice,
            "audio_files": audio_files,
            "combined_audio_file": processed_path.name if processed_path else None
        }
        
        metadata_file = conv_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)