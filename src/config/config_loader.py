"""
Configuration loader for managing language-specific and common configurations.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from config.schemas import validate_schema, COMMON_SCHEMA, LANGUAGE_SCHEMA

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """
    Unified configuration object containing all settings for the pipeline.
    """
    # Environment variables
    openai_api_key: str
    elevenlabs_api_key: str
    
    # Base paths
    base_dir: Path
    config_dir: Path
    output_dir: Path
    
    # Language settings
    language: str
    language_code: str
    language_name: str
    region: str
    
    # Translation settings
    translation_from_code: str
    translation_to_code: str
    translation_intermediate_code: str
    translation_service: str
    qwen_model: Optional[str]
    max_lines: int
    
    # Followup turns settings
    num_turns_lower_limit: int
    num_turns_upper_limit: int
    sample_limit: int
    victim_awareness_levels: list
    
    # Preprocessing settings
    preprocessing_input_file: str
    preprocessing_input_path: Path
    preprocessing_output_path: Path
    preprocessing_map_path: Path
    
    # Translation settings
    translation_english_output: str
    translation_input_path: Path
    translation_output_path: Path
    
    # Multi-turn paths
    multi_turn_input_path: Path
    multi_turn_output_path: Path
    max_conversation: int
    
    # Multi-turn translated paths
    multi_turn_translated_input_path: Path
    multi_turn_translated_output_path: Path
    multi_turn_from_code: str
    multi_turn_to_code: str
    
    # Legit call settings
    legit_call_output_path: Path
    num_legit_conversation: int
    legit_call_region: str
    legit_call_language: str
    legit_call_categories: list
    
    # Voice generation settings
    voice_ids: Dict[str, list]
    voice_language: str
    voice_input_file_scam: Path
    voice_output_dir_scam: Path
    voice_input_file_legit: Path
    voice_output_dir_legit: Path
    voice_sample_limit: int
    voice_model_id: str
    voice_output_format: str
    voice_speed: float
    silence_duration_ms: int
    background_volume_reduction_db: int
    bandpass_low_freq: int
    bandpass_high_freq: int
    audio_effects: dict  # Audio effects configuration
    
    # Enhanced voice settings
    model_v3_enabled: bool
    voice_stability: float
    voice_similarity_boost: float
    voice_style: float
    voice_speaker_boost: bool
    use_high_quality: bool
    high_quality_format: str
    optimize_streaming_latency: int
    use_audio_tags: bool
    emotional_context: bool
    conversation_context: bool
    default_emotion_scam: str
    default_emotion_legit: str
    
    # Post-processing settings
    post_processing_scam_json_input: Path
    post_processing_scam_json_output: Path
    post_processing_legit_json_input: Path
    post_processing_legit_json_output: Path
    post_processing_region: str
    post_processing_scam_audio_dir: Path
    post_processing_legit_audio_dir: Path
    post_processing_scam_audio_zip_output: Path
    post_processing_legit_audio_zip_output: Path
    post_processing_scam_label: int
    post_processing_legit_label: int
    
    # LLM settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    max_concurrent_requests: int = 10
    
    # Standard model parameters
    llm_temperature: float = 1.0
    llm_max_tokens: Optional[int] = None
    llm_top_p: float = 0.95
    llm_n: int = 1
    llm_presence_penalty: float = 0.0
    llm_frequency_penalty: float = 0.0
    
    # Reasoning model parameters
    llm_reasoning_effort: Optional[str] = None  # "minimal", "low", "medium", "high"
    llm_max_completion_tokens: Optional[int] = None
    
    # Gemini-specific parameters
    llm_thinking_budget: Optional[int] = None
    llm_max_output_tokens: Optional[int] = None
    
    # Features
    llm_use_response_api: bool = False
    llm_track_tokens: bool = False
    
    # Translation cache settings
    use_translation_cache: bool = False
    translation_cache_enabled: bool = True
    translation_cache_dir: str = "data/translation_cache"
    translation_cache_service: str = "google"
    force_translation_refresh: bool = False
    
    # Translation token tracking
    translation_track_tokens: bool = False
    
    # Output control
    verbose: bool = False
    
    # Voice profiles for intelligent voice assignment (optional)
    voice_profiles: Optional[Dict] = None
    
    # Locale identifier (e.g., 'ms-my', 'ar-sa')
    locale: Optional[str] = None
    
    # Raw config data
    common_config: dict = field(default_factory=dict)
    lang_config: dict = field(default_factory=dict)


class ConfigLoader:
    """
    Loads and validates configuration files for the voice scam dataset generator.
    """
    
    def __init__(self, config_dir: str = "./configs", output_dir: str = "./output"):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
            output_dir: Base output directory for generated files
        """
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.base_dir = Path(".")
        
        # Load common configuration
        common_path = self.config_dir / "common.json"
        if not common_path.exists():
            raise FileNotFoundError(f"Common configuration not found: {common_path}")
        
        with open(common_path, 'r', encoding='utf-8') as f:
            self.common_config = json.load(f)
        
        # Validate common configuration
        errors = validate_schema(self.common_config, COMMON_SCHEMA)
        if errors:
            raise ValueError(f"Common configuration validation failed:\n" + "\n".join(errors))
        
        # Define locale aliases for backward compatibility
        self.locale_aliases = {
            "arabic": "ar-sa",
            "malay": "ms-my"
        }
    
    def load_language(self, language: str) -> Config:
        """
        Load configuration for a specific language (backward compatibility).
        
        Args:
            language: Language identifier (e.g., 'arabic', 'malay')
            
        Returns:
            Config object with all settings
        """
        # Check if it's an alias
        locale_id = self.locale_aliases.get(language, language)
        
        # Try new localization structure first
        try:
            return self.load_localization(locale_id)
        except FileNotFoundError:
            pass
        
        # Fall back to old language structure
        lang_path = self.config_dir / "languages" / f"{language}.json"
        if not lang_path.exists():
            raise FileNotFoundError(f"Language configuration not found: {lang_path}")
        
        with open(lang_path, 'r', encoding='utf-8') as f:
            lang_config = json.load(f)
        
        # Validate language configuration
        errors = validate_schema(lang_config, LANGUAGE_SCHEMA)
        if errors:
            raise ValueError(f"Language configuration validation failed:\n" + "\n".join(errors))
    
    def load_localization(self, locale_id: str) -> Config:
        """
        Load configuration for a specific localization.
        
        Args:
            locale_id: Locale identifier (e.g., 'ar-sa', 'ms-my')
            
        Returns:
            Config object with all settings
        """
        # Check if it's an alias
        locale_id = self.locale_aliases.get(locale_id, locale_id)
        
        # Load locale-specific configuration
        locale_dir = self.config_dir / "localizations" / locale_id
        config_path = locale_dir / "config.json"
        placeholders_path = locale_dir / "placeholders.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Locale configuration not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            locale_config = json.load(f)
        
        # Create Config object from new localization structure
        return self._build_config_from_locale(locale_id, locale_config, placeholders_path)
    
    def _build_config(self, language: str, lang_config: dict) -> Config:
        """
        Build a Config object from common and language-specific configurations.
        
        Args:
            language: Language identifier
            lang_config: Language-specific configuration dictionary
            
        Returns:
            Populated Config object
        """
        # Get environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        if not elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        
        # Build paths
        lang_output_dir = self.output_dir / language
        intermediate_dir = lang_output_dir / "intermediate"
        audio_dir = lang_output_dir / "audio"
        final_dir = lang_output_dir / "final"
        
        # Preprocessing paths
        preprocessing_input = self.base_dir / "data" / "input" / self.common_config["preprocessing"]["input_file"]
        preprocessing_output = intermediate_dir / "preprocessed" / (preprocessing_input.stem + self.common_config["preprocessing"]["mapped_suffix"])
        preprocessing_map = self.base_dir / "data" / "input" / "placeholder_maps" / lang_config["placeholder_map"]
        
        # Translation paths
        translation_output = intermediate_dir / "translated" / self.common_config["translation"]["english_output"]
        
        # Multi-turn paths
        multi_turn_output = intermediate_dir / "conversations" / self.common_config["multi_turn"]["english_output"]
        
        # Language-specific output paths
        scam_conversation = intermediate_dir / "conversations" / lang_config["output_paths"]["scam_conversation"]
        legit_conversation = intermediate_dir / "conversations" / lang_config["output_paths"]["legit_conversation"]
        
        # Audio directories
        scam_audio_dir = audio_dir / lang_config["output_paths"]["scam_audio_dir"]
        legit_audio_dir = audio_dir / lang_config["output_paths"]["legit_audio_dir"]
        
        # Final output paths
        scam_formatted = final_dir / "json" / lang_config["output_paths"]["scam_formatted"]
        legit_formatted = final_dir / "json" / lang_config["output_paths"]["legit_formatted"]
        scam_audio_zip = final_dir / "archives" / self.common_config["post_processing"]["audio_zip_names"]["scam"]
        legit_audio_zip = final_dir / "archives" / self.common_config["post_processing"]["audio_zip_names"]["legit"]
        
        # Add LLM settings
        llm_config = self.common_config.get("llm", {})
        
        return Config(
            # Environment variables
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            
            # Base paths
            base_dir=self.base_dir,
            config_dir=self.config_dir,
            output_dir=lang_output_dir,
            
            # Language settings
            language=language,
            language_code=lang_config["language_code"],
            language_name=lang_config["language_name"],
            region=lang_config["region"],
            
            # Translation settings
            translation_from_code=self.common_config["translation"].get("chinese_code", lang_config["translation"]["from_code"]),
            translation_to_code=lang_config["translation"]["to_code"],
            translation_intermediate_code=lang_config["translation"]["intermediate_code"],
            translation_service=self.common_config["translation"]["service"],
            qwen_model=self.common_config["translation"].get("qwen_model"),
            max_lines=self.common_config["translation"]["max_lines"],
            
            # Followup turns settings
            num_turns_lower_limit=self.common_config["followup_turns"]["num_turns_lower_limit"],
            num_turns_upper_limit=self.common_config["followup_turns"]["num_turns_upper_limit"],
            sample_limit=self.common_config["followup_turns"]["sample_limit"],
            victim_awareness_levels=self.common_config["followup_turns"]["victim_awareness_levels"],
            
            # Preprocessing settings
            preprocessing_input_file=self.common_config["preprocessing"]["input_file"],
            preprocessing_input_path=preprocessing_input,
            preprocessing_output_path=preprocessing_output,
            preprocessing_map_path=preprocessing_map,
            
            # Translation settings
            translation_english_output=self.common_config["translation"]["english_output"],
            translation_input_path=preprocessing_output,
            translation_output_path=translation_output,
            
            # Multi-turn paths
            multi_turn_input_path=translation_output,
            multi_turn_output_path=multi_turn_output,
            max_conversation=self.common_config["multi_turn"]["max_conversation"],
            
            # Multi-turn translated paths
            multi_turn_translated_input_path=multi_turn_output,
            multi_turn_translated_output_path=scam_conversation,
            multi_turn_from_code=lang_config["translation"]["intermediate_code"],
            multi_turn_to_code=lang_config["language_code"],
            
            # Legit call settings
            legit_call_output_path=legit_conversation,
            num_legit_conversation=self.common_config["legit_call"]["num_conversations"],
            legit_call_region=lang_config["region"],
            legit_call_language=lang_config["language_name"],
            legit_call_categories=lang_config["legit_call_categories"],
            
            # Voice generation settings
            voice_ids={lang_config["language_code"]: lang_config["voices"]["ids"]},
            voice_language=lang_config["language_code"],
            voice_input_file_scam=scam_conversation,
            voice_output_dir_scam=scam_audio_dir,
            voice_input_file_legit=legit_conversation,
            voice_output_dir_legit=legit_audio_dir,
            voice_sample_limit=self.common_config["voice_generation"]["sample_limit"],
            voice_model_id=self.common_config["voice_generation"]["model_id"],
            voice_output_format=self.common_config["voice_generation"]["output_format"],
            voice_speed=self.common_config["voice_generation"]["voice_speed"],
            silence_duration_ms=self.common_config["voice_generation"]["silence_duration_ms"],
            background_volume_reduction_db=self.common_config["voice_generation"]["background_volume_reduction_db"],
            bandpass_low_freq=self.common_config["voice_generation"]["bandpass_filter"]["low_freq"],
            bandpass_high_freq=self.common_config["voice_generation"]["bandpass_filter"]["high_freq"],
            audio_effects=self.common_config["voice_generation"].get("audio_effects", {
                "enable_background_noise": True,
                "enable_call_end_effect": True,
                "enable_bandpass_filter": True,
                "background_noise_level": 0.3,
                "call_end_volume": 0.5
            }),
            
            # Enhanced voice settings
            model_v3_enabled=self.common_config["voice_generation"]["model_v3_enabled"],
            voice_stability=self.common_config["voice_generation"]["voice_settings"]["stability"],
            voice_similarity_boost=self.common_config["voice_generation"]["voice_settings"]["similarity_boost"],
            voice_style=self.common_config["voice_generation"]["voice_settings"]["style"],
            voice_speaker_boost=self.common_config["voice_generation"]["voice_settings"]["speaker_boost"],
            use_high_quality=self.common_config["voice_generation"]["quality_settings"]["use_high_quality"],
            high_quality_format=self.common_config["voice_generation"]["quality_settings"]["high_quality_format"],
            optimize_streaming_latency=self.common_config["voice_generation"]["quality_settings"]["optimize_streaming_latency"],
            use_audio_tags=self.common_config["voice_generation"]["v3_features"]["use_audio_tags"],
            emotional_context=self.common_config["voice_generation"]["v3_features"]["emotional_context"],
            conversation_context=self.common_config["voice_generation"]["v3_features"]["conversation_context"],
            default_emotion_scam=self.common_config["voice_generation"]["v3_features"]["default_emotion_scam"],
            default_emotion_legit=self.common_config["voice_generation"]["v3_features"]["default_emotion_legit"],
            
            # Translation cache configuration
            use_translation_cache=self.common_config.get("translation_cache", {}).get("use_cache", False),
            translation_cache_enabled=self.common_config.get("translation_cache", {}).get("enabled", True),
            translation_cache_dir=self.common_config.get("translation_cache", {}).get("cache_dir", "data/translation_cache"),
            translation_cache_service=self.common_config.get("translation_cache", {}).get("cache_service", "google"),
            force_translation_refresh=self.common_config.get("translation_cache", {}).get("force_refresh", False),
            
            # Translation token tracking
            translation_track_tokens=self.common_config.get("translation", {}).get("track_tokens", False),
            
            # Post-processing settings
            post_processing_scam_json_input=scam_conversation,
            post_processing_scam_json_output=scam_formatted,
            post_processing_legit_json_input=legit_conversation,
            post_processing_legit_json_output=legit_formatted,
            post_processing_region=lang_config["region"],
            post_processing_scam_audio_dir=scam_audio_dir,
            post_processing_legit_audio_dir=legit_audio_dir,
            post_processing_scam_audio_zip_output=scam_audio_zip,
            post_processing_legit_audio_zip_output=legit_audio_zip,
            post_processing_scam_label=self.common_config["post_processing"]["scam_label"],
            post_processing_legit_label=self.common_config["post_processing"]["legit_label"],
            
            # LLM settings
            llm_provider=llm_config.get("provider", "openai"),
            llm_model=llm_config.get("model", "gpt-4o"),
            max_concurrent_requests=llm_config.get("max_concurrent_requests", 10),
            
            # Standard model parameters
            llm_temperature=llm_config.get("temperature", 1.0),
            llm_max_tokens=llm_config.get("max_tokens"),
            llm_top_p=llm_config.get("top_p", 0.95),
            llm_n=llm_config.get("n", 1),
            llm_presence_penalty=llm_config.get("presence_penalty", 0.0),
            llm_frequency_penalty=llm_config.get("frequency_penalty", 0.0),
            
            # Reasoning model parameters
            llm_reasoning_effort=llm_config.get("reasoning_effort"),
            llm_max_completion_tokens=llm_config.get("max_completion_tokens"),
            
            # Gemini-specific parameters
            llm_thinking_budget=llm_config.get("thinking_budget"),
            llm_max_output_tokens=llm_config.get("max_output_tokens"),
            
            # Features
            llm_use_response_api=llm_config.get("use_response_api", False),
            llm_track_tokens=llm_config.get("track_tokens", False),
            
            # Raw config data
            common_config=self.common_config,
            lang_config=lang_config
        )
    
    def _build_config_from_locale(self, locale_id: str, locale_config: dict, placeholders_path: Path) -> Config:
        """
        Build a Config object from new locale-based configuration.
        
        Args:
            locale_id: Locale identifier (e.g., 'ar-sa')
            locale_config: Locale configuration dictionary
            placeholders_path: Path to placeholders file
            
        Returns:
            Populated Config object
        """
        # Get environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        if not elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        
        # Extract locale info
        locale_info = locale_config["locale"]
        
        # Load voice profiles if available
        voice_profiles = None
        voice_profiles_path = self.config_dir / "localizations" / locale_id / "voice_profiles.json"
        if voice_profiles_path.exists():
            try:
                with open(voice_profiles_path, 'r', encoding='utf-8') as f:
                    voice_profiles = json.load(f)
                logger.info(f"Loaded voice profiles for {locale_id}")
            except Exception as e:
                logger.warning(f"Failed to load voice profiles: {e}")
        
        # Build paths using locale_id
        locale_output_dir = self.output_dir / locale_id
        intermediate_dir = locale_output_dir / "intermediate"
        audio_dir = locale_output_dir / "audio"
        final_dir = locale_output_dir / "final"
        
        # Preprocessing paths
        preprocessing_input = self.base_dir / "data" / "input" / self.common_config["preprocessing"]["input_file"]
        preprocessing_output = intermediate_dir / "preprocessed" / (preprocessing_input.stem + self.common_config["preprocessing"]["mapped_suffix"])
        
        # Translation paths
        translation_output = intermediate_dir / "translated" / self.common_config["translation"]["english_output"]
        
        # Multi-turn paths
        multi_turn_output = intermediate_dir / "conversations" / self.common_config["multi_turn"]["english_output"]
        
        # Locale-specific output paths
        scam_conversation = intermediate_dir / "conversations" / locale_config["output"]["scam_conversation"]
        legit_conversation = intermediate_dir / "conversations" / locale_config["output"]["legit_conversation"]
        
        # Audio directories
        scam_audio_dir = audio_dir / locale_config["output"]["scam_audio_dir"]
        legit_audio_dir = audio_dir / locale_config["output"]["legit_audio_dir"]
        
        # Final output paths
        scam_formatted = final_dir / "json" / locale_config["output"]["scam_formatted"]
        legit_formatted = final_dir / "json" / locale_config["output"]["legit_formatted"]
        scam_audio_zip = final_dir / "archives" / self.common_config["post_processing"]["audio_zip_names"]["scam"]
        legit_audio_zip = final_dir / "archives" / self.common_config["post_processing"]["audio_zip_names"]["legit"]
        
        # Add LLM settings
        llm_config = self.common_config.get("llm", {})
        
        return Config(
            # Environment variables
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            
            # Base paths
            base_dir=self.base_dir,
            config_dir=self.config_dir,
            output_dir=locale_output_dir,
            
            # Language settings - using locale info
            language=locale_id,  # Use locale_id as language identifier
            language_code=locale_info["language_code"],
            language_name=locale_info["language_name"],
            region=locale_info["region_name"],
            
            # Translation settings
            translation_from_code=locale_config["translation"]["from_code"],
            translation_to_code=locale_config["translation"]["to_code"],
            translation_intermediate_code=locale_config["translation"]["intermediate_code"],
            translation_service=self.common_config["translation"]["service"],
            qwen_model=self.common_config["translation"].get("qwen_model"),
            max_lines=self.common_config["translation"]["max_lines"],
            
            # Followup turns settings
            num_turns_lower_limit=self.common_config["followup_turns"]["num_turns_lower_limit"],
            num_turns_upper_limit=self.common_config["followup_turns"]["num_turns_upper_limit"],
            sample_limit=self.common_config["followup_turns"]["sample_limit"],
            victim_awareness_levels=self.common_config["followup_turns"]["victim_awareness_levels"],
            
            # Preprocessing settings
            preprocessing_input_file=self.common_config["preprocessing"]["input_file"],
            preprocessing_input_path=preprocessing_input,
            preprocessing_output_path=preprocessing_output,
            preprocessing_map_path=placeholders_path,  # Use co-located placeholders
            
            # Translation settings
            translation_english_output=self.common_config["translation"]["english_output"],
            translation_input_path=preprocessing_output,
            translation_output_path=translation_output,
            
            # Multi-turn paths
            multi_turn_input_path=translation_output,
            multi_turn_output_path=multi_turn_output,
            max_conversation=self.common_config["multi_turn"]["max_conversation"],
            
            # Multi-turn translated paths
            multi_turn_translated_input_path=multi_turn_output,
            multi_turn_translated_output_path=scam_conversation,
            multi_turn_from_code=locale_config["translation"]["intermediate_code"],
            multi_turn_to_code=locale_config["translation"]["to_code"],
            
            # Legitimate call settings
            legit_call_output_path=legit_conversation,
            num_legit_conversation=self.common_config["legit_call"]["num_conversations"],
            legit_call_region=locale_info["region_name"],
            legit_call_language=locale_info["language_name"],
            legit_call_categories=locale_config["conversation"]["legit_categories"],
            
            # Voice generation settings
            voice_ids={locale_info["language_code"]: locale_config["voices"]["ids"]},
            voice_language=locale_info["language_code"],
            voice_input_file_scam=scam_conversation,
            voice_input_file_legit=legit_conversation,
            voice_output_dir_scam=scam_audio_dir,
            voice_output_dir_legit=legit_audio_dir,
            voice_sample_limit=self.common_config["voice_generation"]["sample_limit"],
            voice_model_id=self.common_config["voice_generation"]["model_id"],
            voice_output_format=self.common_config["voice_generation"]["output_format"],
            voice_speed=self.common_config["voice_generation"]["voice_speed"],
            silence_duration_ms=self.common_config["voice_generation"]["silence_duration_ms"],
            background_volume_reduction_db=self.common_config["voice_generation"]["background_volume_reduction_db"],
            bandpass_low_freq=self.common_config["voice_generation"]["bandpass_filter"]["low_freq"],
            bandpass_high_freq=self.common_config["voice_generation"]["bandpass_filter"]["high_freq"],
            audio_effects=self.common_config["voice_generation"].get("audio_effects", {
                "enable_background_noise": True,
                "enable_call_end_effect": True,
                "enable_bandpass_filter": True,
                "background_noise_level": 0.3,
                "call_end_volume": 0.5
            }),
            
            # Enhanced voice settings
            model_v3_enabled=self.common_config["voice_generation"]["model_v3_enabled"],
            voice_stability=self.common_config["voice_generation"]["voice_settings"]["stability"],
            voice_similarity_boost=self.common_config["voice_generation"]["voice_settings"]["similarity_boost"],
            voice_style=self.common_config["voice_generation"]["voice_settings"]["style"],
            voice_speaker_boost=self.common_config["voice_generation"]["voice_settings"]["speaker_boost"],
            use_high_quality=self.common_config["voice_generation"]["quality_settings"]["use_high_quality"],
            high_quality_format=self.common_config["voice_generation"]["quality_settings"]["high_quality_format"],
            optimize_streaming_latency=self.common_config["voice_generation"]["quality_settings"]["optimize_streaming_latency"],
            use_audio_tags=self.common_config["voice_generation"]["v3_features"]["use_audio_tags"],
            emotional_context=self.common_config["voice_generation"]["v3_features"]["emotional_context"],
            conversation_context=self.common_config["voice_generation"]["v3_features"]["conversation_context"],
            default_emotion_scam=self.common_config["voice_generation"]["v3_features"]["default_emotion_scam"],
            default_emotion_legit=self.common_config["voice_generation"]["v3_features"]["default_emotion_legit"],
            
            # Translation cache configuration
            use_translation_cache=self.common_config.get("translation_cache", {}).get("use_cache", False),
            translation_cache_enabled=self.common_config.get("translation_cache", {}).get("enabled", True),
            translation_cache_dir=self.common_config.get("translation_cache", {}).get("cache_dir", "data/translation_cache"),
            translation_cache_service=self.common_config.get("translation_cache", {}).get("cache_service", "google"),
            force_translation_refresh=self.common_config.get("translation_cache", {}).get("force_refresh", False),
            
            # Translation token tracking
            translation_track_tokens=self.common_config.get("translation", {}).get("track_tokens", False),
            
            # Post-processing settings
            post_processing_scam_json_input=scam_conversation,
            post_processing_scam_json_output=scam_formatted,
            post_processing_legit_json_input=legit_conversation,
            post_processing_legit_json_output=legit_formatted,
            post_processing_region=locale_info["region_name"],
            post_processing_scam_audio_dir=scam_audio_dir,
            post_processing_legit_audio_dir=legit_audio_dir,
            post_processing_scam_audio_zip_output=scam_audio_zip,
            post_processing_legit_audio_zip_output=legit_audio_zip,
            post_processing_scam_label=self.common_config["post_processing"]["scam_label"],
            post_processing_legit_label=self.common_config["post_processing"]["legit_label"],
            
            # LLM settings
            llm_provider=llm_config.get("provider", "openai"),
            llm_model=llm_config.get("model", "gpt-4o"),
            max_concurrent_requests=llm_config.get("max_concurrent_requests", 10),
            
            # Standard model parameters
            llm_temperature=llm_config.get("temperature", 1.0),
            llm_max_tokens=llm_config.get("max_tokens"),
            llm_top_p=llm_config.get("top_p", 0.95),
            llm_n=llm_config.get("n", 1),
            llm_presence_penalty=llm_config.get("presence_penalty", 0.0),
            llm_frequency_penalty=llm_config.get("frequency_penalty", 0.0),
            
            # Reasoning model parameters
            llm_reasoning_effort=llm_config.get("reasoning_effort"),
            llm_max_completion_tokens=llm_config.get("max_completion_tokens"),
            
            # Gemini-specific parameters
            llm_thinking_budget=llm_config.get("thinking_budget"),
            llm_max_output_tokens=llm_config.get("max_output_tokens"),
            
            # Features
            llm_use_response_api=llm_config.get("use_response_api", False),
            llm_track_tokens=llm_config.get("track_tokens", False),
            
            # Voice profiles for intelligent voice assignment
            voice_profiles=voice_profiles,
            
            # Locale identifier
            locale=locale_id,
            
            # Raw config data
            common_config=self.common_config,
            lang_config=locale_config
        )
    
    def list_languages(self) -> list:
        """
        List all available language configurations.
        
        Returns:
            List of available language identifiers
        """
        lang_dir = self.config_dir / "languages"
        if not lang_dir.exists():
            return []
        
        languages = []
        for file in lang_dir.glob("*.json"):
            if file.stem != "template":
                languages.append(file.stem)
        
        return sorted(languages)
    
    def list_localizations(self) -> dict:
        """
        List all available localization configurations.
        
        Returns:
            Dictionary mapping locale IDs to descriptions
        """
        localizations = {}
        
        # Add old language configs with aliases
        languages = self.list_languages()
        for lang in languages:
            locale_id = self.locale_aliases.get(lang, lang)
            localizations[locale_id] = f"{lang.title()} (legacy)"
        
        # Add new localization configs
        locale_dir = self.config_dir / "localizations"
        if locale_dir.exists():
            for locale_path in locale_dir.iterdir():
                if locale_path.is_dir():
                    config_path = locale_path / "config.json"
                    if config_path.exists():
                        try:
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                                locale_info = config.get("locale", {})
                                description = f"{locale_info.get('language_name', 'Unknown')} ({locale_info.get('region_name', 'Unknown')})"
                                localizations[locale_path.name] = description
                        except Exception:
                            localizations[locale_path.name] = "Unknown locale"
        
        return localizations