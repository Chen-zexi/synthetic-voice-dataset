"""
Enhanced voice synthesizer using ElevenLabs TTS API with v3 support and audio tags.
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
from tts.audio_tags import AudioTagManager
from utils.logging_utils import ConditionalLogger, create_progress_bar, format_completion_message


logger = logging.getLogger(__name__)


class VoiceSynthesizer:
    """
    Enhanced voice synthesizer using ElevenLabs with v3 support, audio tags, and improved quality settings.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the enhanced voice synthesizer.
        
        Args:
            config: Configuration object with enhanced voice settings
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
        self.voice_profiles = None  # Will be loaded lazily
        self._load_voice_profiles()
        
        # Enhanced features
        self.audio_tag_manager = AudioTagManager()
        self.current_conversation_type = None  # Track if processing scam or legit conversations
        
        # Determine model to use
        self.model_id = self._get_model_id()
        
        # Log enhancement features being used
        if config.model_v3_enabled:
            self.clogger.info("ElevenLabs v3 features enabled: audio tags, enhanced expressiveness")
        if config.use_audio_tags:
            self.clogger.info("Audio tags enabled for emotional context")
        if config.use_high_quality:
            self.clogger.info(f"High-quality audio enabled: {config.high_quality_format}")
    
    def _get_model_id(self) -> str:
        """
        Determine which model to use based on configuration.
        
        Returns:
            Model ID to use for TTS
        """
        if self.config.model_v3_enabled:
            # Use v3 model if enabled
            return "eleven_multilingual_v3"
        else:
            # Use configured model (default v2)
            return self.config.voice_model_id
    
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
        Generate enhanced audio for all conversations in the input file asynchronously.
        
        Args:
            input_file: Path to JSON file containing conversations
            output_dir: Directory to save audio files
            is_scam: Whether these are scam conversations
        """
        # Set conversation type for context-aware audio generation
        self.current_conversation_type = "scam" if is_scam else "legit"
        
        self.clogger.info(f"Generating {self.current_conversation_type} audio from {input_file}")
        self.clogger.info(f"Using model: {self.model_id}")
        
        # Validate voice IDs first
        if not await self.validate_voices():
            logger.error("Voice validation failed. Cannot proceed with audio generation.")
            raise ValueError("Invalid voice IDs detected. Please check your configuration.")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load conversations
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract conversations list from the data structure
        # Handle both dict format (with 'conversations' key) and plain array format
        if isinstance(data, dict):
            conversations = data.get('conversations', [])
        elif isinstance(data, list):
            conversations = data
        else:
            raise ValueError(f"Unexpected data format in {input_file}: {type(data)}")
        
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
                    # Log error with truncation to avoid breaking display
                    error_msg = str(e)[:200]  # Truncate long errors
                    conv_id = conversation.get('conversation_id', '?')
                    self.clogger.progress_write(
                        f"❌ Conversation {conv_id} failed: {error_msg}", 
                        pbar
                    )
                finally:
                    # Always update progress bar to maintain consistency
                    if pbar and not pbar.disable:
                        pbar.update(1)
        
        # Process conversations concurrently
        tasks = [process_with_progress(conv) for conv in conversations_to_process]
        await asyncio.gather(*tasks)
        
        pbar.close()
        
        # Final summary
        duration = asyncio.get_event_loop().time() - start_time
        total_processed = len(conversations_to_process)
        
        # Check if we had failures and warn the user
        if failed_count > 0:
            self.clogger.warning(
                f"Audio generation completed with issues: {completed_count}/{total_processed} successful, "
                f"{failed_count} failed. Please check the logs for details."
            )
            # In non-verbose mode, provide a simple warning
            if not self.config.verbose:
                print(f"\n⚠️  {failed_count} conversation(s) failed to generate completely. Run with --verbose for details.")
        elif self.config.verbose:
            self.clogger.info(f"Completed audio generation: {completed_count} successful, {failed_count} failed, {total_processed} total")
    
    async def _process_conversation_async(self, conversation: Dict, output_dir: Path, pbar: tqdm):
        """
        Process a single conversation to generate enhanced audio asynchronously.
        
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
        
        # Select voices for caller and callee based on mapping or random
        caller_voice, callee_voice = self._select_voices_for_conversation(conversation)
        
        # Show voice assignment only in verbose mode
        if self.config.verbose:
            self.clogger.progress_write(f"Conversation {conversation_id}: Using voices {caller_voice} (caller) and {callee_voice} (callee)", pbar)
        
        audio_files = []
        failed_turns = []
        
        # Generate audio for each turn concurrently with enhanced context
        turn_tasks = []
        for i, turn in enumerate(dialogue):
            # Determine turn position for context-aware tagging
            if i == 0:
                turn_position = "opening"
            elif i == len(dialogue) - 1:
                turn_position = "closing"
            else:
                turn_position = "middle"
            
            task = self._generate_turn_audio_async(turn, caller_voice, callee_voice, conv_dir, turn_position)
            turn_tasks.append(task)
        
        # Wait for all turns to complete
        turn_results = await asyncio.gather(*turn_tasks, return_exceptions=True)
        
        # Process results
        for idx, result in enumerate(turn_results):
            if isinstance(result, dict):
                audio_files.append(result)
            elif isinstance(result, Exception):
                turn_id = dialogue[idx].get('sent_id', idx + 1)
                self.clogger.progress_write(f"Conv {conversation_id}, Turn {turn_id} failed: {str(result)[:100]}", pbar)
                failed_turns.append(turn_id)
            else:
                # None or other falsy result
                failed_turns.append(dialogue[idx]['sent_id'])
        
        # Validate all turns were generated
        expected_turns = len(dialogue)
        actual_turns = len(audio_files)
        
        if actual_turns < expected_turns:
            self.clogger.progress_write(
                f"Conv {conversation_id}: Only {actual_turns}/{expected_turns} turns generated. Missing: {failed_turns}", 
                pbar
            )
            # Raise exception to mark conversation as failed
            raise ValueError(f"Incomplete audio generation: {actual_turns}/{expected_turns} turns")
        
        # Combine audio files only if all turns are present
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
    
    def _load_voice_profiles(self):
        """
        Load voice profiles configuration for the current locale.
        """
        try:
            # Try to load voice profiles for current locale
            locale = getattr(self.config, 'locale', 'ms-my')
            profiles_path = Path(self.config.config_dir) / 'localizations' / locale / 'voice_profiles.json'
            
            if profiles_path.exists():
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    self.voice_profiles = json.load(f)
                    self.clogger.info(f"Loaded voice profiles from {profiles_path}")
            else:
                self.clogger.info(f"No voice profiles found at {profiles_path}, will use random selection")
        except Exception as e:
            self.clogger.warning(f"Failed to load voice profiles: {e}, will use random selection")
            self.voice_profiles = None
    
    def _get_voice_id_from_name(self, voice_name: str) -> Optional[str]:
        """
        Convert voice name to voice ID using profiles.
        
        Args:
            voice_name: Name of the voice from profile
            
        Returns:
            Voice ID or None if not found
        """
        if not self.voice_profiles or 'available_voices' not in self.voice_profiles:
            return None
            
        voice_info = self.voice_profiles['available_voices'].get(voice_name.lower())
        if voice_info:
            return voice_info.get('id')
        
        # Try to find by name field
        for key, info in self.voice_profiles['available_voices'].items():
            if info.get('name', '').lower() == voice_name.lower():
                return info.get('id')
        
        return None
    
    def _select_voices_for_conversation(self, conversation: Dict) -> Tuple[str, str]:
        """
        Select voices based on conversation mapping or fall back to random.
        
        Args:
            conversation: Conversation dictionary
            
        Returns:
            Tuple of (caller_voice_id, callee_voice_id)
        """
        # Check for explicit voice mapping in conversation
        if 'voice_mapping' in conversation:
            mapping = conversation['voice_mapping']
            caller_name = mapping.get('caller')
            callee_name = mapping.get('callee')
            
            # Convert names to IDs
            caller_id = self._get_voice_id_from_name(caller_name) if caller_name else None
            callee_id = self._get_voice_id_from_name(callee_name) if callee_name else None
            
            if caller_id and callee_id:
                self.clogger.info(f"Using mapped voices: {caller_name}→{caller_id}, {callee_name}→{callee_id}")
                return caller_id, callee_id
            else:
                self.clogger.warning(f"Voice mapping incomplete, falling back to random selection")
        
        # Fall back to random selection
        return self._select_voices()
    
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
    
    async def _generate_turn_with_retry(self, turn: Dict, caller_voice: str,
                                      callee_voice: str, conv_dir: Path, pbar: tqdm,
                                      max_retries: int = 3) -> Optional[Dict]:
        """
        Generate audio for a turn with retry logic.
        
        Args:
            turn: Dialogue turn dictionary
            caller_voice: Voice ID for caller
            callee_voice: Voice ID for callee  
            conv_dir: Conversation directory
            pbar: Progress bar for logging
            max_retries: Maximum number of retry attempts
            
        Returns:
            Audio file info or None if all retries failed
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = await self._generate_turn_audio_async(turn, caller_voice, callee_voice, conv_dir, "middle")
                if result:
                    return result
                # If None returned (e.g., validation failed), don't retry
                return None
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    self.clogger.progress_write(
                        f"Turn {turn.get('sent_id', '?')} attempt {attempt + 1} failed, retrying in {wait_time}s...", 
                        pbar
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Final attempt failed
                    self.clogger.progress_write(
                        f"Turn {turn.get('sent_id', '?')} failed after {max_retries} attempts: {str(last_error)[:100]}",
                        pbar
                    )
        
        # All retries exhausted
        raise last_error if last_error else ValueError("Generation failed")
    
    async def _generate_turn_audio_async(self, turn: Dict, caller_voice: str, 
                                       callee_voice: str, conv_dir: Path, turn_position: str = "middle") -> Optional[Dict]:
        """
        Generate enhanced audio for a single dialogue turn asynchronously.
        
        Args:
            turn: Dialogue turn dictionary
            caller_voice: Voice ID for caller
            callee_voice: Voice ID for callee
            conv_dir: Conversation directory
            turn_position: Position in conversation (opening, middle, closing)
            
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
        
        # Enhance text with audio tags if enabled
        enhanced_text = self._enhance_text_with_tags(text, role, turn_position)
        
        # Generate filename with quality indicator
        file_extension = "wav" if self.config.use_high_quality else "mp3"
        filename = f"turn_{sent_id:02d}_{role}.{file_extension}"
        filepath = conv_dir / filename
        
        # Skip if file already exists
        if filepath.exists():
            self.clogger.progress_write(f"Skipping existing file: {filename}")
            return {
                "turn_id": sent_id,
                "role": role,
                "text": text,
                "enhanced_text": enhanced_text,
                "voice_id": voice_id,
                "filename": filename
            }
        
        try:
            # Build enhanced voice settings
            voice_settings = self._build_voice_settings()
            
            # Determine output format
            output_format = self._get_output_format()
            
            # Use the enhanced ElevenLabs SDK client
            audio_generator = self.client.text_to_speech.convert(
                text=enhanced_text,
                voice_id=voice_id,
                model_id=self.model_id,
                voice_settings=voice_settings,
                output_format=output_format,
                optimize_streaming_latency=self.config.optimize_streaming_latency
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
                "enhanced_text": enhanced_text,
                "voice_id": voice_id,
                "filename": filename,
                "audio_tags_used": self._get_last_used_tags()
            }
                    
        except Exception as e:
            # Don't log here, let retry handler manage logging
            raise e
    
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
            "combined_audio_file": processed_path.name if processed_path else None,
            "model_used": self.model_id,
            "v3_features_enabled": self.config.model_v3_enabled,
            "audio_tags_enabled": self.config.use_audio_tags,
            "high_quality_enabled": self.config.use_high_quality
        }
        
        metadata_file = conv_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def verify_conversation_completeness(self, output_dir: Path) -> Dict[str, List[int]]:
        """
        Verify that all conversations have complete audio generation.
        
        Args:
            output_dir: Directory containing conversation subdirectories
            
        Returns:
            Dictionary mapping conversation IDs to lists of missing turn IDs
        """
        incomplete_conversations = {}
        
        for conv_dir in sorted(output_dir.glob("conversation_*")):
            metadata_file = conv_dir / "metadata.json"
            
            if not metadata_file.exists():
                conv_id = conv_dir.name.replace("conversation_", "")
                incomplete_conversations[conv_id] = ["No metadata file"]
                continue
                
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check for missing audio files
            audio_files = metadata.get("audio_files", [])
            turn_ids = {af["turn_id"] for af in audio_files}
            
            # Infer expected turns from filenames or metadata
            all_turn_files = list(conv_dir.glob("turn_*.mp3"))
            expected_count = len(all_turn_files) if all_turn_files else 10  # Default to 10
            
            if len(turn_ids) < expected_count:
                missing = [i for i in range(1, expected_count + 1) if i not in turn_ids]
                if missing:
                    conv_id = metadata.get("conversation_id", conv_dir.name)
                    incomplete_conversations[str(conv_id)] = missing
        
        return incomplete_conversations
    
    def _enhance_text_with_tags(self, text: str, role: str, turn_position: str) -> str:
        """
        Enhance text with audio tags based on context.
        
        Args:
            text: Original text
            role: Speaker role (caller/callee)
            turn_position: Position in conversation
            
        Returns:
            Enhanced text with audio tags
        """
        if not self.config.use_audio_tags or not self.current_conversation_type:
            return text
        
        # Get contextual tags
        tags = self.audio_tag_manager.get_contextual_tags(
            conversation_type=self.current_conversation_type,
            turn_position=turn_position,
            role=role,
            text_content=text
        )
        
        # Store tags for metadata
        self._last_used_tags = tags
        
        # Format text with tags
        enhanced_text = self.audio_tag_manager.format_text_with_tags(text, tags)
        
        # Log tag usage in verbose mode
        if self.config.verbose and tags:
            self.clogger.info(f"Applied tags {tags} to {role} text: '{text[:50]}...'")
        
        return enhanced_text
    
    def _build_voice_settings(self) -> Dict:
        """
        Build voice settings from configuration.
        
        Returns:
            Voice settings dictionary
        """
        settings = {
            "stability": self.config.voice_stability,
            "similarity_boost": self.config.voice_similarity_boost,
            "speaker_boost": self.config.voice_speaker_boost
        }
        
        # Add style setting for v3 model
        if self.config.model_v3_enabled:
            settings["style"] = self.config.voice_style
        
        return settings
    
    def _get_output_format(self) -> str:
        """
        Get output format based on configuration.
        
        Returns:
            Output format string
        """
        if self.config.use_high_quality:
            return self.config.high_quality_format
        else:
            return self.config.voice_output_format
    
    def _get_last_used_tags(self) -> List[str]:
        """
        Get the last used audio tags for metadata.
        
        Returns:
            List of last used tags
        """
        return getattr(self, '_last_used_tags', [])