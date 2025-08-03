"""
CLI command implementations for the voice scam dataset generator.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional

from config.config_loader import ConfigLoader
from pipeline.runner import PipelineRunner
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
    sample_limit: Optional[int] = None
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
        
    Returns:
        Exit code (0 for success)
    """
    try:
        # Load configuration
        print_info(f"Loading configuration for {language}...")
        config_loader = ConfigLoader(config_dir, output_dir)
        config = config_loader.load_language(language)
        
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
        
        print_step_header("Available Languages")
        
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
        return 0
        
    except Exception as e:
        print_error(f"Failed to list languages: {e}")
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