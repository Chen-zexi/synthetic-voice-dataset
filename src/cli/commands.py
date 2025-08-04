"""
CLI command implementations for the voice scam dataset generator.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Optional

from config.config_loader import ConfigLoader
from pipeline.runner import PipelineRunner
from tts.voice_validator import VoiceValidator
from translation.cache_translator import CacheTranslator
from cli.utils import (
    print_error, print_info, print_warning,
    print_step_header, format_language_info,
    ensure_directory
)


logger = logging.getLogger(__name__)


def run_pipeline(
    language: str,
    steps: Optional[List[str]] = None,
    config_dir: str = "./configs",
    output_dir: str = "./output",
    force: bool = False,
    sample_limit: Optional[int] = None,
    verbose: bool = False
) -> int:
    """
    Run the voice scam dataset generation pipeline.
    
    Args:
        language: Language to process
        steps: Specific steps to run (None for all)
        config_dir: Configuration directory
        output_dir: Output directory
        force: Force overwrite existing files
        sample_limit: Optional limit on number of samples to process
        verbose: Enable verbose output
        
    Returns:
        Exit code (0 for success)
    """
    try:
        # Load configuration
        print_info(f"Loading configuration for {language}...")
        config_loader = ConfigLoader(config_dir, output_dir)
        config = config_loader.load_language(language)
        config.verbose = verbose  # Set verbose flag
        
        # Display configuration info
        print(format_language_info(config))
        
        # Check for existing output
        if config.output_dir.exists() and not force:
            print_warning(f"Output directory already exists: {config.output_dir}")
            print_warning("Use --force to overwrite existing files")
            return 1
        
        # Create output directories
        ensure_directory(config.output_dir)
        
        # Override sample limits if specified
        if sample_limit:
            config.sample_limit = sample_limit
            config.max_lines = sample_limit
            config.max_conversation = sample_limit
            config.num_legit_conversation = sample_limit
            config.voice_sample_limit = sample_limit
            print_info(f"Sample limit set to {sample_limit} for testing")
        
        # Initialize and run pipeline
        runner = PipelineRunner(config, steps)
        runner.run()
        
        print_info("Pipeline completed successfully!")
        return 0
        
    except FileNotFoundError as e:
        print_error(f"Configuration file not found: {e}")
        return 1
    except ValueError as e:
        print_error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        print_error(f"Pipeline failed: {e}")
        logger.exception("Pipeline error")
        return 1


def list_languages(config_dir: str = "./configs") -> int:
    """
    List all available language configurations.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Exit code (0 for success)
    """
    try:
        config_loader = ConfigLoader(config_dir)
        languages = config_loader.list_languages()
        
        if not languages:
            print_warning("No language configurations found")
            return 1
        
        print_step_header("Available Languages (Legacy)")
        
        for lang in languages:
            # Try to load and display info for each language
            try:
                config = config_loader.load_language(lang)
                print(f"\n{lang}:")
                print(f"  Name: {config.language_name}")
                print(f"  Region: {config.region}")
                print(f"  Code: {config.language_code}")
            except Exception as e:
                print(f"\n{lang}: ERROR - {e}")
        
        print(f"\nTotal: {len(languages)} languages")
        print("\nNote: Use --list-locales for the new localization-based configurations")
        return 0
        
    except Exception as e:
        print_error(f"Failed to list languages: {e}")
        return 1


def list_locales(config_dir: str = "./configs") -> int:
    """
    List all available locale configurations.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Exit code (0 for success)
    """
    try:
        config_loader = ConfigLoader(config_dir)
        localizations = config_loader.list_localizations()
        
        if not localizations:
            print_warning("No locale configurations found")
            return 1
        
        print_step_header("Available Locales")
        
        # Group by language
        by_language = {}
        for locale_id, description in localizations.items():
            lang_code = locale_id.split('-')[0] if '-' in locale_id else locale_id
            if lang_code not in by_language:
                by_language[lang_code] = []
            by_language[lang_code].append((locale_id, description))
        
        # Display grouped by language
        for lang_code in sorted(by_language.keys()):
            print(f"\n{lang_code.upper()}:")
            for locale_id, description in sorted(by_language[lang_code]):
                print(f"  {locale_id:<10} - {description}")
        
        print(f"\nTotal: {len(localizations)} locales")
        print("\nExamples:")
        print("  python main.py --locale ar-sa    # Run pipeline for Saudi Arabia (Arabic)")
        print("  python main.py --locale ms-my    # Run pipeline for Malaysia (Malay)")
        return 0
        
    except Exception as e:
        print_error(f"Failed to list locales: {e}")
        return 1


def validate_config(language: str, config_dir: str = "./configs") -> int:
    """
    Validate configuration for a specific language.
    
    Args:
        language: Language to validate
        config_dir: Configuration directory
        
    Returns:
        Exit code (0 for success)
    """
    try:
        print_info(f"Validating configuration for {language}...")
        
        config_loader = ConfigLoader(config_dir)
        config = config_loader.load_language(language)
        
        # Check required files
        print("\nChecking required files:")
        
        # Input files
        files_to_check = [
            ("Chinese input", config.preprocessing_input_path),
            ("Placeholder map", config.preprocessing_map_path),
        ]
        
        # Sound effects
        sound_dir = Path("data/sound_effects")
        if sound_dir.exists():
            backgrounds = list((sound_dir / "backgrounds").glob("*.mp3"))
            call_effects = list((sound_dir / "call_effects").glob("*.mp3"))
            files_to_check.append(("Background sounds", f"{len(backgrounds)} files"))
            files_to_check.append(("Call effects", f"{len(call_effects)} files"))
        
        all_valid = True
        for name, path in files_to_check:
            if isinstance(path, str):
                status = "✓"
            elif path.exists():
                status = "✓"
            else:
                status = "✗"
                all_valid = False
            print(f"  {status} {name}: {path}")
        
        # Check environment variables
        print("\nChecking environment variables:")
        env_vars = [
            ("OPENAI_API_KEY", bool(config.openai_api_key)),
            ("ELEVENLABS_API_KEY", bool(config.elevenlabs_api_key)),
        ]
        
        for var, is_set in env_vars:
            status = "✓" if is_set else "✗"
            if not is_set:
                all_valid = False
            print(f"  {status} {var}")
        
        # Display configuration summary
        print("\nConfiguration summary:")
        print(format_language_info(config))
        
        if all_valid:
            print_info("Configuration is valid!")
            return 0
        else:
            print_error("Configuration has errors!")
            return 1
            
    except Exception as e:
        print_error(f"Validation failed: {e}")
        return 1


def show_pipeline_steps() -> int:
    """
    Show all available pipeline steps and their descriptions.
    
    Returns:
        Exit code (0 for success)
    """
    print_step_header("Pipeline Steps")
    
    steps = [
        ("preprocess", "Extract tags and create placeholder mappings from Chinese source"),
        ("translate", "Translate Chinese text to English intermediate format"),
        ("conversation", "Generate multi-turn scam conversations using GPT-4"),
        ("translate_final", "Translate conversations from English to target language"),
        ("legit", "Generate legitimate (non-scam) conversations"),
        ("tts", "Convert text conversations to audio using ElevenLabs TTS"),
        ("postprocess", "Format JSON files and package audio into ZIP archives"),
    ]
    
    print("Available steps (in execution order):\n")
    for step, description in steps:
        print(f"  {step:<15} - {description}")
    
    print("\nUsage examples:")
    print("  python main.py --language arabic --steps preprocess translate")
    print("  python main.py --language malay --steps tts postprocess")
    print("  python main.py --language arabic  # Run all steps")
    
    return 0


def cache_translation(
    service: str = "google",
    model: Optional[str] = None,
    force_refresh: bool = False,
    config_dir: str = "./configs",
    verbose: bool = False
) -> int:
    """
    Run standalone Chinese to English translation and cache the results.
    
    Args:
        service: Translation service to use (google, qwen, argos)
        model: Optional model name for services that support it
        force_refresh: Force new translation even if cache exists
        config_dir: Path to configuration directory
        verbose: Enable verbose output
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load base configuration
        config_loader = ConfigLoader(config_dir)
        # Use a locale to load config
        config = config_loader.load_localization("ar-sa")
        
        # Override translation service
        config.translation_service = service
        
        # For Qwen, use model from parameter or fall back to config
        if service == "qwen":
            if model:
                config.qwen_model = model
            else:
                # Use model from config (already loaded)
                model = getattr(config, 'qwen_model', 'qwen-mt-turbo')
        
        print_step_header("Translation Cache")
        
        # Create cache translator
        translator = CacheTranslator(config, service, model)
        
        # Check existing caches
        if not force_refresh:
            cached = CacheTranslator.list_cached_translations()
            if cached:
                print("Existing cached translations:")
                for svc_key, metadata in cached.items():
                    display_name = svc_key
                    if metadata.get('model'):
                        display_name = f"{svc_key} ({metadata['model']})"
                    print(f"  - {display_name}: {metadata['line_count']} lines, "
                          f"cached on {metadata['timestamp'][:10]}")
                print()
        
        # Run translation
        print(f"Service: {service}")
        if model:
            print(f"Model: {model}")
        print(f"Force refresh: {force_refresh}")
        print()
        
        metadata = translator.run_cached_translation(force_refresh)
        
        print_info(f"\nTranslation cached successfully!")
        print(f"Lines translated: {metadata['line_count']}")
        print(f"Cache location: data/translation_cache/{service}/")
        
        return 0
        
    except Exception as e:
        print_error(f"Translation cache failed: {e}")
        logger.exception("Translation cache error")
        return 1


def list_cached_translations(verbose: bool = False) -> int:
    """
    List all available cached translations.
    
    Args:
        verbose: Enable verbose output
        
    Returns:
        Exit code (0 for success)
    """
    print_step_header("Cached Translations")
    
    cached = CacheTranslator.list_cached_translations()
    
    if not cached:
        print("No cached translations found.")
        print("\nTo create a cache, run:")
        print("  python main.py --cache-translation --service google")
        return 0
    
    print("Available cached translations:\n")
    
    for service_key, metadata in cached.items():
        # Handle service/model format for Qwen
        if '/' in service_key:
            service, model = service_key.split('/', 1)
            print(f"Service: {service}")
            print(f"  Model: {model}")
        else:
            print(f"Service: {service_key}")
            if metadata.get('model'):
                print(f"  Model: {metadata['model']}")
        print(f"  Lines: {metadata['line_count']}")
        print(f"  Cached: {metadata['timestamp'][:19]}")
        print(f"  Source: {metadata['source_file']}")
        print()
    
    print("To use a cached translation in the pipeline:")
    print("  1. Set 'use_cache': true in configs/common.json")
    print("  2. Set 'cache_service' to the desired service")
    print("  3. Run the pipeline normally")
    
    return 0


def validate_voices(language: str, config_dir: str = "./configs", output_dir: str = "./output") -> int:
    """
    Validate ElevenLabs voice IDs for a specific locale using the comprehensive validation script.
    
    Args:
        language: Language to validate voices for
        config_dir: Configuration directory
        output_dir: Output directory
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        print_step_header(f"Voice Validation for {language}")
        
        # Get the path to the validation script
        script_dir = Path(__file__).parent.parent.parent
        validation_script = script_dir / "validate_voice_ids.py"
        
        if not validation_script.exists():
            print_error(f"Validation script not found: {validation_script}")
            return 1
        
        # Run the validation script for the specific locale
        cmd = [sys.executable, str(validation_script), "--locale", language]
        
        print_info(f"Running voice validation for {language}...")
        result = subprocess.run(cmd, cwd=str(script_dir), capture_output=False)
        
        return result.returncode
        
    except Exception as e:
        print_error(f"Voice validation failed: {e}")
        logger.exception("Voice validation error")
        return 1


def validate_all_voices(config_dir: str = "./configs", update_configs: bool = False) -> int:
    """
    Validate all ElevenLabs voice IDs across all locales.
    
    Args:
        config_dir: Configuration directory
        update_configs: Whether to update configuration files automatically
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        print_step_header("Voice Validation for All Locales")
        
        # Get the path to the validation script
        script_dir = Path(__file__).parent.parent.parent
        validation_script = script_dir / "validate_voice_ids.py"
        
        if not validation_script.exists():
            print_error(f"Validation script not found: {validation_script}")
            return 1
        
        # Build command
        cmd = [sys.executable, str(validation_script)]
        if update_configs:
            cmd.append("--update-configs")
        
        print_info("Running comprehensive voice validation for all locales...")
        result = subprocess.run(cmd, cwd=str(script_dir), capture_output=False)
        
        return result.returncode
        
    except Exception as e:
        print_error(f"Voice validation failed: {e}")
        logger.exception("Voice validation error")
        return 1


def update_voice_configs(config_dir: str = "./configs") -> int:
    """
    Update configuration files to remove invalid voice IDs.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        print_step_header("Updating Voice Configurations")
        
        # Get the path to the validation script
        script_dir = Path(__file__).parent.parent.parent
        validation_script = script_dir / "validate_voice_ids.py"
        
        if not validation_script.exists():
            print_error(f"Validation script not found: {validation_script}")
            return 1
        
        # Run with update flag
        cmd = [sys.executable, str(validation_script), "--update-configs"]
        
        print_info("Updating configuration files to remove invalid voice IDs...")
        result = subprocess.run(cmd, cwd=str(script_dir), capture_output=False)
        
        return result.returncode
        
    except Exception as e:
        print_error(f"Voice configuration update failed: {e}")
        logger.exception("Voice configuration update error")
        return 1