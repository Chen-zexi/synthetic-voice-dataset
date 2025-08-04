"""
Audio combiner for merging individual turn audio files into conversations.
"""

import logging
from pathlib import Path
from typing import Optional, List

from pydub import AudioSegment
from config.config_loader import Config
from utils.logging_utils import ConditionalLogger


logger = logging.getLogger(__name__)


class AudioCombiner:
    """
    Combines individual audio turns into complete conversation files.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the audio combiner.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.clogger = ConditionalLogger(__name__, config.verbose)
    
    def combine_conversation(self, conversation_dir: Path, 
                           conversation_id: int) -> Optional[Path]:
        """
        Combine all audio files in a conversation directory into a single file.
        
        Args:
            conversation_dir: Directory containing turn audio files
            conversation_id: Conversation ID for naming
            
        Returns:
            Path to combined audio file or None if combination failed
        """
        self.clogger.debug(f"Combining audio files in {conversation_dir}")
        
        # Get all turn audio files
        audio_files = self._get_turn_files(conversation_dir)
        
        if not audio_files:
            self.clogger.warning(f"No audio files found in {conversation_dir}")
            return None
        
        try:
            # Load and combine audio files
            combined_audio = self._combine_audio_files(audio_files)
            
            # Save combined audio
            output_filename = f"conversation_{conversation_id:03d}_combined.wav"
            output_path = conversation_dir / output_filename
            
            combined_audio.export(output_path, format="wav")
            
            self.clogger.debug(f"Combined {len(audio_files)} audio files into {output_path}")
            return output_path
            
        except Exception as e:
            self.clogger.error(f"Error combining audio files: {e}")
            return None
    
    def _get_turn_files(self, conversation_dir: Path) -> List[Path]:
        """
        Get all turn audio files in order.
        
        Args:
            conversation_dir: Directory to search
            
        Returns:
            List of audio file paths sorted by turn number
        """
        # Find all turn files
        turn_files = list(conversation_dir.glob("turn_*.mp3"))
        
        # Sort by turn number
        turn_files.sort(key=lambda x: int(x.stem.split('_')[1]))
        
        return turn_files
    
    def _combine_audio_files(self, audio_files: List[Path]) -> AudioSegment:
        """
        Combine multiple audio files with silence between turns.
        
        Args:
            audio_files: List of audio file paths
            
        Returns:
            Combined AudioSegment
        """
        # Load first audio file
        combined_audio = AudioSegment.from_mp3(audio_files[0])
        
        # Create silence for between turns
        silence = AudioSegment.silent(duration=self.config.silence_duration_ms)
        
        # Add remaining audio files with silence
        for audio_file in audio_files[1:]:
            audio_segment = AudioSegment.from_mp3(audio_file)
            combined_audio = combined_audio + silence + audio_segment
        
        return combined_audio