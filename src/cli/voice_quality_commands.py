"""
CLI commands for voice quality enhancement and v3 features.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from config.config_loader import ConfigLoader


class VoiceQualityManager:
    """
    Manages voice quality settings and ElevenLabs v3 features through CLI.
    """
    
    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the voice quality manager.
        
        Args:
            config_loader: Configuration loader instance
        """
        self.config_loader = config_loader
        self.common_config_path = Path("configs/common.json")
    
    def enable_v3_features(self, enable_audio_tags: bool = True) -> bool:
        """
        Enable ElevenLabs v3 features.
        
        Args:
            enable_audio_tags: Whether to enable audio tags
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            
            # Enable v3 model
            config["voice_generation"]["model_v3_enabled"] = True
            config["voice_generation"]["model_id"] = "eleven_multilingual_v3"
            
            # Enable audio tags if requested
            if enable_audio_tags:
                config["voice_generation"]["v3_features"]["use_audio_tags"] = True
                config["voice_generation"]["v3_features"]["emotional_context"] = True
                config["voice_generation"]["v3_features"]["conversation_context"] = True
            
            self._save_common_config(config)
            print("✓ ElevenLabs v3 features enabled")
            print("  - Model: eleven_multilingual_v3")
            if enable_audio_tags:
                print("  - Audio tags: Enabled")
                print("  - Emotional context: Enabled")
            
            return True
            
        except Exception as e:
            print(f"Error enabling v3 features: {e}")
            return False
    
    def disable_v3_features(self) -> bool:
        """
        Disable ElevenLabs v3 features and revert to v2.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            
            # Disable v3 model
            config["voice_generation"]["model_v3_enabled"] = False
            config["voice_generation"]["model_id"] = "eleven_multilingual_v2"
            
            # Disable audio tags
            config["voice_generation"]["v3_features"]["use_audio_tags"] = False
            
            self._save_common_config(config)
            print("✓ ElevenLabs v3 features disabled")
            print("  - Model: eleven_multilingual_v2 (reverted)")
            print("  - Audio tags: Disabled")
            
            return True
            
        except Exception as e:
            print(f"Error disabling v3 features: {e}")
            return False
    
    def enable_high_quality_audio(self) -> bool:
        """
        Enable high-quality audio settings.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            
            config["voice_generation"]["quality_settings"]["use_high_quality"] = True
            config["voice_generation"]["quality_settings"]["high_quality_format"] = "pcm_44100"
            config["voice_generation"]["output_format"] = "pcm_44100"
            
            self._save_common_config(config)
            print("✓ High-quality audio enabled")
            print("  - Format: PCM 44.1kHz (uncompressed)")
            print("  - Note: File sizes will be larger but quality will be maximum")
            
            return True
            
        except Exception as e:
            print(f"Error enabling high-quality audio: {e}")
            return False
    
    def disable_high_quality_audio(self) -> bool:
        """
        Disable high-quality audio settings.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            
            config["voice_generation"]["quality_settings"]["use_high_quality"] = False
            config["voice_generation"]["output_format"] = "mp3_44100_128"
            
            self._save_common_config(config)
            print("✓ High-quality audio disabled")
            print("  - Format: MP3 44.1kHz 128kbps (default)")
            
            return True
            
        except Exception as e:
            print(f"Error disabling high-quality audio: {e}")
            return False
    
    def set_voice_settings(self, 
                          stability: Optional[float] = None,
                          similarity_boost: Optional[float] = None,
                          style: Optional[float] = None,
                          speaker_boost: Optional[bool] = None) -> bool:
        """
        Set voice generation settings.
        
        Args:
            stability: Voice stability (0.0-1.0)
            similarity_boost: Similarity boost (0.0-1.0)
            style: Style setting for v3 (0.0-1.0)
            speaker_boost: Enable speaker boost
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            voice_settings = config["voice_generation"]["voice_settings"]
            
            if stability is not None:
                if 0.0 <= stability <= 1.0:
                    voice_settings["stability"] = stability
                    print(f"✓ Stability set to {stability}")
                else:
                    print("Error: Stability must be between 0.0 and 1.0")
                    return False
            
            if similarity_boost is not None:
                if 0.0 <= similarity_boost <= 1.0:
                    voice_settings["similarity_boost"] = similarity_boost
                    print(f"✓ Similarity boost set to {similarity_boost}")
                else:
                    print("Error: Similarity boost must be between 0.0 and 1.0")
                    return False
            
            if style is not None:
                if 0.0 <= style <= 1.0:
                    voice_settings["style"] = style
                    print(f"✓ Style set to {style}")
                else:
                    print("Error: Style must be between 0.0 and 1.0")
                    return False
            
            if speaker_boost is not None:
                voice_settings["speaker_boost"] = speaker_boost
                print(f"✓ Speaker boost {'enabled' if speaker_boost else 'disabled'}")
            
            self._save_common_config(config)
            return True
            
        except Exception as e:
            print(f"Error setting voice settings: {e}")
            return False
    
    def show_current_settings(self) -> None:
        """
        Display current voice quality settings.
        """
        try:
            config = self._load_common_config()
            voice_gen = config["voice_generation"]
            
            print("Current Voice Quality Settings:")
            print("=" * 40)
            
            # Model settings
            print(f"Model: {voice_gen['model_id']}")
            print(f"V3 Features: {'Enabled' if voice_gen['model_v3_enabled'] else 'Disabled'}")
            
            # Quality settings
            print(f"High Quality: {'Enabled' if voice_gen['quality_settings']['use_high_quality'] else 'Disabled'}")
            print(f"Output Format: {voice_gen['output_format']}")
            
            # Voice settings
            vs = voice_gen["voice_settings"]
            print(f"Stability: {vs['stability']}")
            print(f"Similarity Boost: {vs['similarity_boost']}")
            print(f"Style: {vs['style']}")
            print(f"Speaker Boost: {'Enabled' if vs['speaker_boost'] else 'Disabled'}")
            
            # V3 features
            if voice_gen['model_v3_enabled']:
                v3_features = voice_gen["v3_features"]
                print("\nV3 Features:")
                print(f"  Audio Tags: {'Enabled' if v3_features['use_audio_tags'] else 'Disabled'}")
                print(f"  Emotional Context: {'Enabled' if v3_features['emotional_context'] else 'Disabled'}")
                print(f"  Conversation Context: {'Enabled' if v3_features['conversation_context'] else 'Disabled'}")
                print(f"  Default Scam Emotion: {v3_features['default_emotion_scam']}")
                print(f"  Default Legit Emotion: {v3_features['default_emotion_legit']}")
            
        except Exception as e:
            print(f"Error displaying settings: {e}")
    
    def reset_to_defaults(self) -> bool:
        """
        Reset all voice settings to defaults.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            
            # Reset to default v2 settings
            config["voice_generation"]["model_v3_enabled"] = False
            config["voice_generation"]["model_id"] = "eleven_multilingual_v2"
            config["voice_generation"]["output_format"] = "mp3_44100_128"
            
            # Reset voice settings
            config["voice_generation"]["voice_settings"] = {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.0,
                "speaker_boost": True
            }
            
            # Reset quality settings
            config["voice_generation"]["quality_settings"]["use_high_quality"] = False
            
            # Reset v3 features
            config["voice_generation"]["v3_features"]["use_audio_tags"] = False
            
            self._save_common_config(config)
            print("✓ Voice settings reset to defaults")
            print("  - Model: eleven_multilingual_v2")
            print("  - Quality: Standard MP3")
            print("  - V3 features: Disabled")
            
            return True
            
        except Exception as e:
            print(f"Error resetting settings: {e}")
            return False
    
    def _load_common_config(self) -> Dict:
        """Load the common configuration file."""
        with open(self.common_config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_common_config(self, config: Dict) -> None:
        """Save the common configuration file."""
        with open(self.common_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)


def add_voice_quality_commands(config_loader: ConfigLoader) -> VoiceQualityManager:
    """
    Add voice quality management commands to CLI.
    
    Args:
        config_loader: Configuration loader instance
        
    Returns:
        VoiceQualityManager instance
    """
    return VoiceQualityManager(config_loader)