"""
Voice synthesizer using ElevenLabs TTS API with async support.
"""

import json
import os
import random
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

from elevenlabs import set_api_key, Voice, VoiceSettings
from config.config_loader import Config
from tts.audio_processor import AudioProcessor
from tts.audio_combiner import AudioCombiner


logger = logging.getLogger(__name__)


class VoiceSynthesizer:
    """
    Synthesizes voice audio from text conversations using ElevenLabs with async support.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the voice synthesizer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        set_api_key(config.elevenlabs_api_key)
        self.api_key = config.elevenlabs_api_key
        self.audio_processor = AudioProcessor(config)
        self.audio_combiner = AudioCombiner(config)
        self.base_url = "https://api.elevenlabs.io/v1"
    
    async def generate_audio(self, input_file: Path, output_dir: Path, is_scam: bool = True):
        """
        Generate audio for all conversations in the input file asynchronously.
        
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
        
        # Limit conversations based on config
        conversations_to_process = conversations[:self.config.voice_sample_limit]
        
        # Create progress bar
        pbar = tqdm(total=len(conversations_to_process), desc="Generating audio for conversations")
        
        # Process conversations concurrently with semaphore for rate limiting
        #max_concurrent = getattr(self.config, 'max_concurrent_requests', 5) - hardcoded to 5 for now per current limit
        max_concurrent = 5
        # ElevenLabs has stricter rate limits, so we'll be more conservative
        semaphore = asyncio.Semaphore(min(max_concurrent, 5))
        
        async def process_with_progress(conversation):
            async with semaphore:
                try:
                    await self._process_conversation_async(conversation, output_dir)
                except Exception as e:
                    logger.error(f"Error processing conversation {conversation['conversation_id']}: {e}")
                finally:
                    pbar.update(1)
        
        # Create async session for HTTP requests
        async with aiohttp.ClientSession() as session:
            self.session = session
            tasks = [process_with_progress(conv) for conv in conversations_to_process]
            await asyncio.gather(*tasks)
        
        pbar.close()
        logger.info(f"Completed audio generation for {len(conversations_to_process)} conversations")
    
    async def _process_conversation_async(self, conversation: Dict, output_dir: Path):
        """
        Process a single conversation to generate audio asynchronously.
        
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
        
        logger.debug(f"Conversation {conversation_id}: Using voices {caller_voice} (caller) and {callee_voice} (callee)")
        
        audio_files = []
        
        # Generate audio for each turn concurrently
        turn_tasks = []
        for turn in dialogue:
            task = self._generate_turn_audio_async(turn, caller_voice, callee_voice, conv_dir)
            turn_tasks.append(task)
        
        # Wait for all turns to complete
        turn_results = await asyncio.gather(*turn_tasks, return_exceptions=True)
        
        # Collect successful results
        for result in turn_results:
            if isinstance(result, dict):
                audio_files.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Turn generation failed: {result}")
        
        # Combine audio files (this is still sync as it involves local file operations)
        combined_path = await asyncio.to_thread(
            self.audio_combiner.combine_conversation, conv_dir, conversation_id
        )
        
        if combined_path:
            # Apply audio processing (run in thread to not block)
            processed_path = await asyncio.to_thread(
                self.audio_processor.process_conversation_audio, combined_path
            )
            
            # Save metadata
            await asyncio.to_thread(
                self._save_metadata, conv_dir, conversation_id, 
                caller_voice, callee_voice, audio_files, processed_path
            )
    
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
    
    async def _generate_turn_audio_async(self, turn: Dict, caller_voice: str, 
                                       callee_voice: str, conv_dir: Path) -> Optional[Dict]:
        """
        Generate audio for a single dialogue turn asynchronously.
        
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
            # Prepare request data
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.config.voice_model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            # Make async request
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    audio_bytes = await response.read()
                    
                    # Save audio file (run in thread to not block)
                    await asyncio.to_thread(self._save_audio_file, filepath, audio_bytes)
                    
                    logger.debug(f"Generated: {filename}")
                    
                    return {
                        "turn_id": sent_id,
                        "role": role,
                        "text": text,
                        "voice_id": voice_id,
                        "filename": filename
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"ElevenLabs API error ({response.status}): {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error generating audio for turn {sent_id}: {e}")
            return None
    
    def _save_audio_file(self, filepath: Path, audio_bytes: bytes):
        """
        Save audio bytes to file.
        
        Args:
            filepath: Path to save the file
            audio_bytes: Audio data
        """
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)
    
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