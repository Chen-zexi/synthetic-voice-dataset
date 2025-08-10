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
    
    def set_model(self, model_id: str) -> bool:
        """
        Set the TTS model to use.
        
        Args:
            model_id: ElevenLabs model ID (e.g., 'eleven_multilingual_v2', 'eleven_multilingual_v3', 'eleven_turbo_v2_5')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            config["voice_generation"]["model_id"] = model_id
            self._save_common_config(config)
            
            print(f"✓ Model set to: {model_id}")
            if 'v3' in model_id.lower():
                print("  - V3 features will be active (if configured)")
            else:
                print("  - V3 features will be ignored (non-v3 model)")
            
            return True
            
        except Exception as e:
            print(f"Error setting model: {e}")
            return False
    
    def set_audio_format(self, output_format: str) -> bool:
        """
        Set the audio output format.
        
        Args:
            output_format: Audio format (e.g., 'mp3_44100_128', 'mp3_22050_32')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_common_config()
            config["voice_generation"]["output_format"] = output_format
            
            self._save_common_config(config)
            print(f"✓ Audio format set to: {output_format}")
            
            return True
            
        except Exception as e:
            print(f"Error setting audio format: {e}")
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
            is_v3 = 'v3' in voice_gen['model_id'].lower()
            print(f"V3 Model: {'Yes' if is_v3 else 'No'}")
            
            # Audio format
            print(f"Output Format: {voice_gen['output_format']}")
            
            # Voice settings
            vs = voice_gen["voice_settings"]
            print(f"Stability: {vs['stability']}")
            print(f"Similarity Boost: {vs['similarity_boost']}")
            print(f"Style: {vs['style']}{' (v3 only)' if not is_v3 else ''}")
            print(f"Speaker Boost: {'Enabled' if vs['speaker_boost'] else 'Disabled'}")
            
            # V3 features
            v3_features = voice_gen["v3_features"]
            if is_v3:
                print("\nV3 Features (active):")
                print(f"  Audio Tags: {'Enabled' if v3_features['use_audio_tags'] else 'Disabled'}")
                print(f"  Emotional Context: {'Enabled' if v3_features['emotional_context'] else 'Disabled'}")
                print(f"  Conversation Context: {'Enabled' if v3_features['conversation_context'] else 'Disabled'}")
                print(f"  Default Scam Emotion: {v3_features['default_emotion_scam']}")
                print(f"  Default Legit Emotion: {v3_features['default_emotion_legit']}")
            else:
                print("\nV3 Features (inactive - requires v3 model):")
                print(f"  Audio Tags: {'Configured' if v3_features['use_audio_tags'] else 'Not configured'}")
                print(f"  Emotional Context: {'Configured' if v3_features['emotional_context'] else 'Not configured'}")
            
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
            config["voice_generation"]["model_id"] = "eleven_multilingual_v2"
            config["voice_generation"]["output_format"] = "mp3_44100_128"
            
            # Reset voice settings
            config["voice_generation"]["voice_settings"] = {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.0,
                "speaker_boost": True
            }
            
            # Reset v3 features
            config["voice_generation"]["v3_features"]["use_audio_tags"] = False
            config["voice_generation"]["v3_features"]["emotional_context"] = False
            config["voice_generation"]["v3_features"]["conversation_context"] = False
            
            self._save_common_config(config)
            print("✓ Voice settings reset to defaults")
            print("  - Model: eleven_multilingual_v2")
            print("  - Format: mp3_44100_128")
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