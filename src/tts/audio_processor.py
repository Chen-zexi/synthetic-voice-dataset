"""
Audio processing module for applying effects and filters.
"""

import random
import logging
from pathlib import Path
from typing import Optional

from pydub import AudioSegment
from pydub.effects import low_pass_filter, high_pass_filter
from config.config_loader import Config


logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Processes audio files to add realistic phone call effects.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the audio processor.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.sound_effects_dir = Path("data/sound_effects")
        
        # Load audio effect settings with defaults
        self.effects_config = getattr(config, 'audio_effects', {
            'enable_background_noise': True,
            'enable_call_end_effect': True,
            'enable_bandpass_filter': True,
            'background_noise_level': 0.3,
            'call_end_volume': 0.5
        })
    
    def process_conversation_audio(self, audio_path: Path) -> Optional[Path]:
        """
        Apply all processing steps to a conversation audio file.
        
        Args:
            audio_path: Path to the combined audio file
            
        Returns:
            Path to the processed audio file or None if processing failed
        """
        try:
            processed_path = audio_path
            
            # Add background and sound effects if enabled
            if self.effects_config.get('enable_background_noise') or self.effects_config.get('enable_call_end_effect'):
                processed_path = self._add_background_and_effects(processed_path)
                if not processed_path:
                    processed_path = audio_path
            
            # Apply bandpass filter for phone quality if enabled
            if self.effects_config.get('enable_bandpass_filter'):
                final_path = self._apply_bandpass_filter(processed_path)
                return final_path
            
            return processed_path
            
        except Exception as e:
            logger.error(f"Error processing audio {audio_path}: {e}")
            return None
    
    def _add_background_and_effects(self, audio_path: Path) -> Optional[Path]:
        """
        Add background noise and call end effects to the audio.
        
        Args:
            audio_path: Path to the input audio file
            
        Returns:
            Path to the audio with effects or None if processing failed
        """
        logger.debug(f"Adding background and effects to {audio_path}")
        
        try:
            # Load audio files
            call_audio = AudioSegment.from_file(audio_path)
            
            # Get sound effects based on configuration
            background_audio = None
            call_end_effect = None
            
            if self.effects_config.get('enable_background_noise'):
                background_audio = self._get_random_background()
            
            if self.effects_config.get('enable_call_end_effect'):
                call_end_effect = self._get_call_end_effect()
            
            if not background_audio and not call_end_effect:
                logger.debug("No sound effects to add")
                return audio_path
            
            combined_audio = call_audio
            
            # Add background noise if enabled and available
            if background_audio:
                # Handle background audio length
                background_audio = self._adjust_background_length(background_audio, call_audio)
                
                # Reduce background volume
                background_audio = self._reduce_background_volume(background_audio, call_audio)
                
                # Apply additional level adjustment from config
                noise_level = self.effects_config.get('background_noise_level', 0.3)
                if noise_level < 1.0:
                    # Further reduce volume based on noise level (0.0 = silent, 1.0 = full)
                    additional_reduction = -20 * (1.0 - noise_level)  # Convert to dB
                    background_audio = background_audio + additional_reduction
                
                # Overlay background with call audio
                combined_audio = call_audio.overlay(background_audio)
            
            # Append call end effect if enabled and available
            if call_end_effect:
                # Adjust call end effect volume
                end_volume = self.effects_config.get('call_end_volume', 0.5)
                if end_volume < 1.0:
                    volume_adjustment = -20 * (1.0 - end_volume)  # Convert to dB
                    call_end_effect = call_end_effect + volume_adjustment
                
                combined_audio = combined_audio + call_end_effect
            
            # Save processed audio
            output_path = audio_path.parent / audio_path.name.replace('.wav', '_with_effects.wav')
            combined_audio.export(output_path, format="wav")
            
            logger.debug(f"Saved audio with effects: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding background/effects: {e}")
            return None
    
    def _apply_bandpass_filter(self, audio_path: Path) -> Path:
        """
        Apply bandpass filter to simulate phone call quality.
        
        Args:
            audio_path: Path to the input audio file
            
        Returns:
            Path to the filtered audio file
        """
        logger.debug(f"Applying bandpass filter to {audio_path}")
        
        audio = AudioSegment.from_file(audio_path)
        
        # Apply high-pass filter (remove frequencies below 300 Hz)
        audio = high_pass_filter(audio, self.config.bandpass_low_freq)
        
        # Apply low-pass filter (remove frequencies above 3400 Hz)
        audio = low_pass_filter(audio, self.config.bandpass_high_freq)
        
        # Save filtered audio
        output_path = audio_path.parent / audio_path.name.replace('_with_effects.wav', '_final.wav')
        audio.export(output_path, format="wav")
        
        logger.debug(f"Saved filtered audio: {output_path}")
        return output_path
    
    def _get_random_background(self) -> Optional[AudioSegment]:
        """
        Get a random background sound effect.
        
        Returns:
            AudioSegment of background sound or None if not found
        """
        background_dir = self.sound_effects_dir / "backgrounds"
        
        if not background_dir.exists():
            logger.warning(f"Background sounds directory not found: {background_dir}")
            return None
        
        background_files = list(background_dir.glob("*.mp3"))
        
        if not background_files:
            logger.warning("No background sound files found")
            return None
        
        selected_file = random.choice(background_files)
        logger.debug(f"Selected background: {selected_file.name}")
        
        return AudioSegment.from_file(selected_file)
    
    def _get_call_end_effect(self) -> Optional[AudioSegment]:
        """
        Get the call end sound effect.
        
        Returns:
            AudioSegment of call end effect or None if not found
        """
        call_effects_dir = self.sound_effects_dir / "call_effects"
        
        if not call_effects_dir.exists():
            logger.warning(f"Call effects directory not found: {call_effects_dir}")
            return None
        
        call_end_files = list(call_effects_dir.glob("call_end_*.mp3"))
        
        if not call_end_files:
            logger.warning("No call end effect files found")
            return None
        
        # Use the first call end effect found
        return AudioSegment.from_file(call_end_files[0])
    
    def _adjust_background_length(self, background: AudioSegment, 
                                 call_audio: AudioSegment) -> AudioSegment:
        """
        Adjust background audio length to match call audio.
        
        Args:
            background: Background audio
            call_audio: Call audio
            
        Returns:
            Adjusted background audio
        """
        call_duration = len(call_audio)
        background_duration = len(background)
        
        if background_duration < call_duration:
            # Repeat background to match or exceed call length
            repeats = (call_duration // background_duration) + 1
            extended_background = background * repeats
            # Trim to exact length
            return extended_background[:call_duration]
        elif background_duration > call_duration:
            # Randomly sample a snippet from the background
            start = random.randint(0, background_duration - call_duration)
            return background[start:start + call_duration]
        
        return background
    
    def _reduce_background_volume(self, background: AudioSegment,
                                 call_audio: AudioSegment) -> AudioSegment:
        """
        Reduce background volume to be lower than call audio.
        
        Args:
            background: Background audio
            call_audio: Call audio
            
        Returns:
            Background audio with reduced volume
        """
        # Calculate volume difference
        call_loudness = call_audio.dBFS
        background_loudness = background.dBFS
        
        # Calculate required reduction to achieve target difference
        target_difference = self.config.background_volume_reduction_db
        required_reduction = (background_loudness - call_loudness) + target_difference
        
        # Apply volume reduction
        return background - required_reduction