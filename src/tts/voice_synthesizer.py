"""
Voice synthesizer using ElevenLabs TTS API with async support.
"""

import json
import os
import random
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
import sys

from elevenlabs.client import AsyncElevenLabs
from config.config_loader import Config
from tts.audio_processor import AudioProcessor
from tts.audio_combiner import AudioCombiner
from tts.voice_validator import VoiceValidator
from utils.logging_utils import ConditionalLogger, create_progress_bar, format_completion_message


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
        self.client = AsyncElevenLabs(api_key=config.elevenlabs_api_key)
        self.api_key = config.elevenlabs_api_key
        self.audio_processor = AudioProcessor(config)
        self.audio_combiner = AudioCombiner(config)
        self.base_url = "https://api.elevenlabs.io/v1"
        self.voice_validator = VoiceValidator(config.elevenlabs_api_key, config.verbose)
        self.validated_voices = set()  # Cache of validated voice IDs
        self.clogger = ConditionalLogger(__name__, config.verbose)
    
    async def validate_voices(self) -> bool:
        """
        Validate all configured voice IDs before processing.
        
        Returns:
            True if all voices are valid, False otherwise
        """
        voice_ids = self.config.voice_ids[self.config.voice_language]
        
        if not voice_ids:
            logger.error("No voice IDs configured")
            return False
        
        # Skip validation if already done
        if set(voice_ids).issubset(self.validated_voices):
            return True
        
        self.clogger.info(f"Validating {len(voice_ids)} voice IDs for {self.config.voice_language}")
        
        results = await self.voice_validator.validate_voice_ids(voice_ids)
        invalid_voices = self.voice_validator.get_invalid_voices(results)
        valid_voices = self.voice_validator.get_valid_voices(results)
        
        if invalid_voices:
            self.clogger.error(f"Found {len(invalid_voices)} invalid voice IDs:")
            for invalid in invalid_voices:
                self.clogger.info(f"  - {invalid.voice_id}: {invalid.error_message}")
            
            # Show available alternatives only in verbose mode
            self.clogger.info("Fetching available voices for reference...")
            available_voices = await self.voice_validator.get_available_voices()
            if available_voices:
                self.clogger.info(f"Found {len(available_voices)} available voices")
                # Show first few as examples
                for voice in available_voices[:5]:
                    self.clogger.info(f"  - {voice.get('voice_id', 'N/A')}: {voice.get('name', 'Unknown')}")
                if len(available_voices) > 5:
                    self.clogger.info(f"  ... and {len(available_voices) - 5} more")
            
            return False
        
        # Cache valid voices and show summary
        for valid in valid_voices:
            self.validated_voices.add(valid.voice_id)
            self.clogger.info(f"✓ Voice {valid.voice_id} is valid: {valid.name}")
        
        # Show simple validation success in non-verbose mode
        if not self.config.verbose:
            print(f"Validating voices... ✓ ({len(valid_voices)}/{len(voice_ids)} valid)")
        
        return True
    
    async def generate_audio(self, input_file: Path, output_dir: Path, is_scam: bool = True):
        """
        Generate audio for all conversations in the input file asynchronously.
        
        Args:
            input_file: Path to JSON file containing conversations
            output_dir: Directory to save audio files
            is_scam: Whether these are scam conversations
        """
        self.clogger.info(f"Generating audio from {input_file}")
        
        # Validate voice IDs first
        if not await self.validate_voices():
            logger.error("Voice validation failed. Cannot proceed with audio generation.")
            raise ValueError("Invalid voice IDs detected. Please check your configuration.")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load conversations
        with open(input_file, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        self.clogger.info(f"Found {len(conversations)} conversations to process")
        
        # Limit conversations based on config
        conversations_to_process = conversations[:self.config.voice_sample_limit]
        
        # Create simplified progress bar
        audio_type = "scam" if is_scam else "legit" 
        pbar = create_progress_bar(
            total=len(conversations_to_process),
            desc=f"Generating {audio_type} audio",
            unit="conversations"
        )
        
        # Process conversations concurrently with semaphore for rate limiting
        max_concurrent = 5  # Conservative limit for ElevenLabs API
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Track progress safely
        completed_count = 0
        failed_count = 0
        start_time = asyncio.get_event_loop().time()
        
        async def process_with_progress(conversation):
            nonlocal completed_count, failed_count
            async with semaphore:
                try:
                    await self._process_conversation_async(conversation, output_dir, pbar)
                    completed_count += 1
                except Exception as e:
                    failed_count += 1
                    # Log error conditionally
                    self.clogger.progress_write(f"Error processing conversation {conversation['conversation_id']}: {e}", pbar)
                finally:
                    pbar.update(1)
        
        # Process conversations concurrently
        tasks = [process_with_progress(conv) for conv in conversations_to_process]
        await asyncio.gather(*tasks)
        
        pbar.close()
        
        # Final summary
        duration = asyncio.get_event_loop().time() - start_time
        total_processed = len(conversations_to_process)
        
        if self.config.verbose:
            self.clogger.info(f"Completed audio generation: {completed_count} successful, {failed_count} failed, {total_processed} total")
        # Simple summary is handled by the pipeline runner
    
    async def _process_conversation_async(self, conversation: Dict, output_dir: Path, pbar: tqdm):
        """
        Process a single conversation to generate audio asynchronously.
        
        Args:
            conversation: Conversation dictionary
            output_dir: Output directory
            pbar: Progress bar for safe logging
        """
        conversation_id = conversation["conversation_id"]
        dialogue = conversation["dialogue"]
        
        # Create conversation directory
        conv_dir = output_dir / f"conversation_{conversation_id:03d}"
        conv_dir.mkdir(exist_ok=True)
        
        # Select voices for caller and callee
        caller_voice, callee_voice = self._select_voices()
        
        # Show voice assignment only in verbose mode
        if self.config.verbose:
            self.clogger.progress_write(f"Conversation {conversation_id}: Using voices {caller_voice} (caller) and {callee_voice} (callee)", pbar)
        
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
                self.clogger.progress_write(f"Turn generation failed: {result}", pbar)
        
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
        
        # Skip if voice is not validated (safety check)
        if voice_id not in self.validated_voices:
            self.clogger.progress_write(f"Skipping turn {sent_id} ({role}): Voice {voice_id} not validated")
            return None
        
        # Generate filename
        filename = f"turn_{sent_id:02d}_{role}.mp3"
        filepath = conv_dir / filename
        
        # Skip if file already exists
        if filepath.exists():
            self.clogger.progress_write(f"Skipping existing file: {filename}")
            return {
                "turn_id": sent_id,
                "role": role,
                "text": text,
                "voice_id": voice_id,
                "filename": filename
            }
        
        try:
            # Use the new ElevenLabs SDK client
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=self.config.voice_model_id,
                voice_settings={
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            )
            
            # Collect audio bytes
            audio_bytes = b""
            async for chunk in audio_generator:
                audio_bytes += chunk
            
            # Save audio file (run in thread to not block)
            await asyncio.to_thread(self._save_audio_file, filepath, audio_bytes)
            
            self.clogger.progress_write(f"Generated: {filename}")
            
            return {
                "turn_id": sent_id,
                "role": role,
                "text": text,
                "voice_id": voice_id,
                "filename": filename
            }
                    
        except Exception as e:
            self.clogger.progress_write(f"Error generating audio for turn {sent_id}: {e}")
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