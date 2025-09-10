"""
Configuration loader for managing language-specific and common configurations.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from src.config.schemas import validate_schema, COMMON_SCHEMA, LANGUAGE_SCHEMA

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
    
    
    # Followup turns settings
    num_turns_lower_limit: int
    num_turns_upper_limit: int
    victim_awareness_levels: list
    
    
    # Multi-turn paths
    multi_turn_input_path: Path
    multi_turn_output_path: Path
    
    
    # Legit call settings
    legit_call_output_path: Path
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
    voice_model_id: str
    voice_output_format: str
    voice_speed: float
    silence_duration_ms: int
    background_volume_reduction_db: int
    bandpass_low_freq: int
    bandpass_high_freq: int
    audio_effects: dict  # Audio effects configuration
    
    # Enhanced voice settings
    voice_stability: float
    voice_similarity_boost: float
    voice_style: float
    voice_speaker_boost: bool
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
    
    
    
    # Output control
    verbose: bool = False
    
    # Fields with default values (must be at the end)
    total_limit: int = 100  # Default value, overridden by CLI
    scam_sample_limit: Optional[int] = None  # Specific limit for scam conversations
    legit_sample_limit: Optional[int] = None  # Specific limit for legit conversations
    generation_mode: str = "both"  # "scam", "legit", or "both"
    
    # Voice profiles for intelligent voice assignment (optional)
    voice_profiles: Optional[Dict] = None
    
    # Locale identifier (e.g., 'ms-my', 'ar-sa')
    locale: Optional[str] = None
    
    # Character profiles and generation settings
    generation_profiles_file: Optional[str] = None
    generation_enable_character_profiles: bool = False
    generation_min_seed_quality: int = 70
    generation_enable_dynamic_placeholders: bool = False
    generation_random_seed: Optional[int] = None
    scenarios_per_seed: int = 1
    scenario_mode: str = "random"
    scenario_templates_file: Optional[str] = None
    scenario_assignments_file: Optional[str] = None
    
    # Generation control settings
    generation_control_mode: str = "seeds"  # "seeds" or "conversations"
    seed_limit: Optional[int] = None
    total_conversation_limit: Optional[int] = None
    
    # Raw config data
    common_config: dict = field(default_factory=dict)
    lang_config: dict = field(default_factory=dict)
    
    # Timestamp for this generation run
    generation_timestamp: Optional[str] = None
    use_timestamp: bool = True


class ConfigLoader:
    """
    Loads and validates configuration files for the voice scam dataset generator.
    """
    
    def __init__(self, config_dir: str = "./configs", output_dir: str = "./output", 
                 use_timestamp: bool = True, specific_timestamp: Optional[str] = None,
                 pipeline_steps: Optional[List[str]] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
            output_dir: Base output directory for generated files
            use_timestamp: Whether to use timestamp in output directory structure
            specific_timestamp: Specific timestamp to use (overrides smart selection)
            pipeline_steps: Pipeline steps that will be run (for smart timestamp selection)
        """
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.base_dir = Path(".")
        self.use_timestamp = use_timestamp
        self.specific_timestamp = specific_timestamp
        self.pipeline_steps = pipeline_steps or []
        
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
    
    def _find_latest_timestamp(self, locale_id: str) -> Optional[str]:
        """
        Find the latest timestamp directory for a given locale.
        Handles both base timestamps (MMDD_HHMM) and suffixed versions (MMDD_HHMM_N).
        
        Args:
            locale_id: Locale identifier
            
        Returns:
            Latest timestamp string or None if no timestamps found
        """
        locale_dir = self.output_dir / locale_id
        if not locale_dir.exists():
            return None
        
        # Find all timestamp directories (format: MMDD_HHMM or MMDD_HHMM_N)
        import re
        timestamp_pattern = re.compile(r'^(\d{4}_\d{4})(?:_(\d+))?$')
        timestamp_dirs = []
        
        for d in locale_dir.iterdir():
            if d.is_dir():
                match = timestamp_pattern.match(d.name)
                if match:
                    base_timestamp = match.group(1)
                    suffix = int(match.group(2)) if match.group(2) else 0
                    # Store as tuple for proper sorting
                    timestamp_dirs.append((base_timestamp, suffix, d.name))
        
        if not timestamp_dirs:
            return None
        
        # Sort by base timestamp first, then by suffix
        timestamp_dirs.sort(key=lambda x: (x[0], x[1]))
        latest = timestamp_dirs[-1][2]  # Get the full directory name
        logger.info(f"Found latest timestamp for {locale_id}: {latest}")
        return latest
    
    def _generate_unique_timestamp(self, locale_id: str, base_timestamp: str) -> str:
        """
        Generate a unique timestamp directory name, adding suffix if needed.
        
        Args:
            locale_id: Locale identifier
            base_timestamp: Base timestamp in format MMDD_HHMM
            
        Returns:
            Unique timestamp string (e.g., "0909_2218" or "0909_2218_1")
        """
        locale_dir = self.output_dir / locale_id
        
        # Check if base timestamp directory exists
        if not (locale_dir / base_timestamp).exists():
            return base_timestamp
        
        # Find next available suffix
        suffix = 1
        while (locale_dir / f"{base_timestamp}_{suffix}").exists():
            suffix += 1
        
        unique_timestamp = f"{base_timestamp}_{suffix}"
        logger.info(f"Generated unique timestamp with suffix: {unique_timestamp}")
        return unique_timestamp
    
    def load_language(self, language: str, model_override: Optional[str] = None,
                      reasoning_effort_override: Optional[str] = None,
                      random_seed: Optional[int] = None) -> Config:
        """
        Load configuration for a specific language (backward compatibility).
        
        Args:
            language: Language identifier (e.g., 'arabic', 'malay')
            
        Returns:
            Config object with all settings
        """
        # Check if it's an alias and redirect to locale
        locale_id = self.locale_aliases.get(language, language)
        
        # Always use the new localization structure
        return self.load_localization(locale_id, model_override, reasoning_effort_override, random_seed)
    
    def load_localization(self, locale_id: str, model_override: Optional[str] = None,
                         reasoning_effort_override: Optional[str] = None,
                         random_seed: Optional[int] = None) -> Config:
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
        return self._build_config_from_locale(locale_id, locale_config, placeholders_path,
                                             model_override, reasoning_effort_override, random_seed)
    
    def _build_config_from_locale(self, locale_id: str, locale_config: dict, placeholders_path: Path,
                                  model_override: Optional[str] = None,
                                  reasoning_effort_override: Optional[str] = None,
                                  random_seed: Optional[int] = None) -> Config:
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
        
        # Determine timestamp based on smart selection logic
        generation_timestamp = None
        if not self.use_timestamp:
            # No timestamp mode
            locale_output_dir = self.output_dir / locale_id
        else:
            # Smart timestamp selection
            generation_steps = {'conversation', 'legit'}
            has_generation = any(step in generation_steps for step in self.pipeline_steps)
            
            if self.specific_timestamp:
                # User specified a timestamp
                if self.specific_timestamp == "new":
                    base_timestamp = datetime.now().strftime("%m%d_%H%M")
                    generation_timestamp = self._generate_unique_timestamp(locale_id, base_timestamp)
                else:
                    generation_timestamp = self.specific_timestamp
                    # Validate specified timestamp directory exists
                    if not (self.output_dir / locale_id / generation_timestamp).exists():
                        raise ValueError(f"Timestamp directory does not exist: {self.output_dir / locale_id / generation_timestamp}")
            else:
                # Smart default: check if running generation steps
                if has_generation or not self.pipeline_steps:
                    # Running generation or no steps specified - create new timestamp
                    base_timestamp = datetime.now().strftime("%m%d_%H%M")
                    generation_timestamp = self._generate_unique_timestamp(locale_id, base_timestamp)
                else:
                    # Only TTS/postprocessing - use latest timestamp
                    generation_timestamp = self._find_latest_timestamp(locale_id)
                    if not generation_timestamp:
                        raise ValueError(f"No existing timestamp directories found for {locale_id}. "
                                       f"Please generate conversations first or use --use-timestamp new")
            
            locale_output_dir = self.output_dir / locale_id / generation_timestamp
        
        # Build paths using locale_id and optionally timestamp
        conversations_dir = locale_output_dir / "conversations"
        audio_dir = locale_output_dir / "audio"
        final_dir = locale_output_dir / "final"
        
        # Get input file from config
        input_filename = self.common_config.get("multi_turn", {}).get("input_file", "seeds_and_placeholders.json")
        scam_seeds_input = self.base_dir / "data" / "input" / input_filename
        
        # Conversation output paths
        scam_conversation = conversations_dir / "scam_conversations.json"
        legit_conversation = conversations_dir / "legit_conversations.json"
        
        # Audio directories
        scam_audio_dir = audio_dir / locale_config["output"]["scam_audio_dir"]
        legit_audio_dir = audio_dir / locale_config["output"]["legit_audio_dir"]
        
        # Final output paths (simplified structure)
        scam_formatted = final_dir / "scam_dataset.json"
        legit_formatted = final_dir / "legit_dataset.json"
        scam_audio_zip = audio_dir / "scam" / "scam_audio.zip"
        legit_audio_zip = audio_dir / "legit" / "legit_audio.zip"
        
        # Add LLM settings
        llm_config = self.common_config.get("llm", {})
        
        # Apply CLI overrides for LLM settings
        if model_override:
            llm_config["model"] = model_override
            logger.info(f"Overriding LLM model to: {model_override}")
        
        if reasoning_effort_override:
            llm_config["reasoning_effort"] = reasoning_effort_override
            logger.info(f"Overriding reasoning effort to: {reasoning_effort_override}")
        
        # Add generation settings
        generation_config = self.common_config.get("generation", {})
        
        # Apply random seed override
        if random_seed is not None:
            generation_config["random_seed"] = random_seed
            logger.info(f"Setting random seed to: {random_seed}")
        
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
            
            
            # Followup turns settings
            num_turns_lower_limit=self.common_config["followup_turns"]["num_turns_lower_limit"],
            num_turns_upper_limit=self.common_config["followup_turns"]["num_turns_upper_limit"],
            total_limit=100,  # Default value, overridden by CLI --total-limit
            scam_sample_limit=None,  # Specific limit for scam, overridden by CLI
            legit_sample_limit=None,  # Specific limit for legit, overridden by CLI
            generation_mode="both",  # Default to both, overridden by CLI
            victim_awareness_levels=self.common_config["followup_turns"]["victim_awareness_levels"],
            
            
            # Multi-turn paths (no translation needed)
            multi_turn_input_path=scam_seeds_input,
            multi_turn_output_path=scam_conversation,  # Direct to final output
            
            # Legitimate call settings
            legit_call_output_path=legit_conversation,
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
            voice_stability=self.common_config["voice_generation"]["voice_settings"]["stability"],
            voice_similarity_boost=self.common_config["voice_generation"]["voice_settings"]["similarity_boost"],
            voice_style=self.common_config["voice_generation"]["voice_settings"]["style"],
            voice_speaker_boost=self.common_config["voice_generation"]["voice_settings"]["speaker_boost"],
            use_audio_tags=self.common_config["voice_generation"].get("v3_features", {}).get("use_audio_tags", False),
            emotional_context=self.common_config["voice_generation"]["v3_features"]["emotional_context"],
            conversation_context=self.common_config["voice_generation"]["v3_features"]["conversation_context"],
            default_emotion_scam=self.common_config["voice_generation"]["v3_features"]["default_emotion_scam"],
            default_emotion_legit=self.common_config["voice_generation"]["v3_features"]["default_emotion_legit"],
            
            
            
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
            
            # Character profiles and generation settings
            generation_profiles_file=generation_config.get("profiles_file"),
            generation_enable_character_profiles=generation_config.get("enable_character_profiles", False),
            generation_min_seed_quality=generation_config.get("min_seed_quality", 70),
            generation_enable_dynamic_placeholders=generation_config.get("enable_dynamic_placeholders", False),
            generation_random_seed=generation_config.get("random_seed"),
            scenarios_per_seed=generation_config.get("scenarios_per_seed", 1),
            scenario_mode=generation_config.get("scenario_mode", "random"),
            scenario_templates_file=generation_config.get("scenario_templates_file"),
            scenario_assignments_file=generation_config.get("scenario_assignments_file"),
            
            # Raw config data
            common_config=self.common_config,
            lang_config=locale_config,
            
            # Timestamp information
            generation_timestamp=generation_timestamp,
            use_timestamp=self.use_timestamp
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