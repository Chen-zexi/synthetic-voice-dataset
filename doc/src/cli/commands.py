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
from tts.models import ValidationSummary, VoiceSuggestion
from config.locale_manager import LocaleConfigManager
from cli.utils import (
    print_error, print_info, print_warning,
    print_step_header, format_language_info,
    ensure_directory
)


logger = logging.getLogger(__name__)


def _print_validation_results(results, locale_voice_ids, check_minimum: bool = False):
    """Print validation results in a formatted way"""
    
    print("\n" + "="*80)
    print("ELEVENLABS VOICE ID VALIDATION RESULTS")
    print("="*80)
    
    # Summary statistics
    total_ids = len(results)
    valid_ids = sum(1 for is_valid, _ in results.values() if is_valid)
    invalid_ids = total_ids - valid_ids
    
    print(f"\nSUMMARY:")
    print(f"  Total Voice IDs: {total_ids}")
    print(f"  Valid IDs: {valid_ids}")
    print(f"  Invalid IDs: {invalid_ids}")
    print(f"  Success Rate: {(valid_ids/total_ids)*100:.1f}%")
    
    # Minimum voice analysis if requested
    if check_minimum:
        locales_below_minimum = 0
        for locale, voice_ids in locale_voice_ids.items():
            if not voice_ids:
                continue
            locale_valid = sum(1 for vid in voice_ids if results.get(vid, (False, None))[0])
            if locale_valid < 2:
                locales_below_minimum += 1
        
        print(f"  Locales Below Minimum (2 voices): {locales_below_minimum}")
        if locales_below_minimum == 0:
            print("  🎉 All locales meet minimum voice requirements!")
        else:
            print("  ⚠️  Some locales need additional voices")
    
    # Valid voices
    if valid_ids > 0:
        print(f"\n✅ VALID VOICE IDs ({valid_ids}):")
        print("-" * 50)
        for voice_id, (is_valid, voice_info) in results.items():
            if is_valid and voice_info:
                labels = voice_info.labels or {}
                lang = labels.get('language', 'Unknown')
                accent = labels.get('accent', '')
                accent_str = f" ({accent})" if accent else ""
                print(f"  {voice_id} - {voice_info.name} [{lang}{accent_str}]")
    
    # Invalid voices
    if invalid_ids > 0:
        print(f"\n❌ INVALID VOICE IDs ({invalid_ids}):")
        print("-" * 50)
        for voice_id, (is_valid, _) in results.items():
            if not is_valid:
                # Find which locales use this invalid ID
                affected_locales = [locale for locale, ids in locale_voice_ids.items() 
                                  if voice_id in ids]
                print(f"  {voice_id} - Used in: {', '.join(affected_locales)}")
    
    # Results by locale with minimum checking
    print(f"\nRESULTS BY LOCALE:")
    print("-" * 50)
    for locale, voice_ids in locale_voice_ids.items():
        if not voice_ids:
            continue
        
        locale_valid = sum(1 for vid in voice_ids if results.get(vid, (False, None))[0])
        locale_total = len(voice_ids)
        
        # Enhanced status checking for minimum requirements
        if check_minimum:
            if locale_valid >= 2 and locale_valid == locale_total:
                status = "✅"  # Perfect
            elif locale_valid >= 2 and locale_valid < locale_total:
                status = "⚠️"   # Has minimum but some invalid
            elif locale_valid == 1:
                status = "🔴"  # Critical - only 1 voice
            else:
                status = "❌"  # No valid voices
            
            print(f"  {status} {locale}: {locale_valid}/{locale_total} valid", end="")
            if locale_valid < 2:
                print(f" (NEEDS {2 - locale_valid} MORE)", end="")
            print()
        else:
            status = "✅" if locale_valid == locale_total else "⚠️" if locale_valid > 0 else "❌"
            print(f"  {status} {locale}: {locale_valid}/{locale_total} valid")
        
        # Show invalid IDs for this locale
        invalid_for_locale = [vid for vid in voice_ids if not results.get(vid, (False, None))[0]]
        if invalid_for_locale:
            print(f"     Invalid: {', '.join(invalid_for_locale)}")


def _print_voice_suggestions(suggestions, locale: str):
    """Print voice suggestions for a locale"""
    
    print(f"\n🔍 VOICE SUGGESTIONS FOR {locale.upper()}:")
    print("-" * 50)
    
    if not suggestions:
        print("  No compatible voices found.")
        return
    
    for i, suggestion in enumerate(suggestions, 1):
        voice = suggestion.voice_info
        confidence_bar = "█" * int(suggestion.confidence * 10)
        print(f"  {i}. {voice.voice_id} - {voice.name}")
        print(f"     Language: {voice.language or 'Unknown'}")
        print(f"     Accent: {voice.accent or 'Standard'}")
        print(f"     Confidence: {confidence_bar} ({suggestion.confidence:.1f})")
        print(f"     Reason: {suggestion.reason}")
        print()


def run_pipeline(
    language: str,
    steps: Optional[List[str]] = None,
    config_dir: str = "./configs",
    output_dir: str = "./output",
    force: bool = False,
    scam_limit: Optional[int] = None,
    legit_limit: Optional[int] = None,
    generation_mode: str = "both",
    verbose: bool = False,
    use_timestamp: bool = True,
    specific_timestamp: Optional[str] = None,
    model_override: Optional[str] = None,
    reasoning_effort_override: Optional[str] = None,
    random_seed: Optional[int] = None,
    generation_control_mode: str = "seeds",
    seed_limit: Optional[int] = None,
    total_limit: Optional[int] = None,
    conversation_count: Optional[int] = None,
    scenarios_per_seed_override: Optional[int] = None
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
        scam_limit: Specific limit for scam conversations
        legit_limit: Specific limit for legit conversations
        generation_mode: Generation mode ("scam", "legit", or "both")
        verbose: Enable verbose output
        use_timestamp: Whether to use timestamp in output directory structure
        specific_timestamp: Specific timestamp to use or "new" for new timestamp
        
    Returns:
        Exit code (0 for success)
    """
    try:
        # Load configuration with smart timestamp selection
        print_info(f"Loading configuration for {language}...")
        config_loader = ConfigLoader(
            config_dir, 
            output_dir, 
            use_timestamp=use_timestamp,
            specific_timestamp=specific_timestamp,
            pipeline_steps=steps
        )
        config = config_loader.load_language(
            language,
            model_override=model_override,
            reasoning_effort_override=reasoning_effort_override,
            random_seed=random_seed
        )
        config.verbose = verbose  # Set verbose flag
        
        # Display configuration info with timestamp
        print(format_language_info(config))
        if config.generation_timestamp:
            print_info(f"Generation timestamp: {config.generation_timestamp}")
            print_info(f"Output will be saved to: {config.output_dir}")
        
        # Check for existing output
        if config.output_dir.exists() and not force:
            print_warning(f"Output directory already exists: {config.output_dir}")
            print_warning("Use --force to overwrite existing files")
            return 1
        
        # Create output directories
        ensure_directory(config.output_dir)
        
        # Override generation limits and mode
        
        # Set new generation control parameters
        config.generation_control_mode = generation_control_mode
        if generation_control_mode != "seeds":
            print_info(f"Generation control mode: {generation_control_mode}")
        
        if seed_limit is not None:
            config.seed_limit = seed_limit
            print_info(f"Seed limit set to {seed_limit}")
        
        if total_limit is not None:
            # total_limit acts as absolute cap that overrides all other settings
            config.total_limit = total_limit
            print_info(f"Total conversation limit (absolute cap) set to {total_limit}")
        
        if conversation_count is not None:
            config.total_conversation_limit = conversation_count
            print_info(f"Target conversation count set to {conversation_count}")
        
        if scenarios_per_seed_override is not None:
            config.scenarios_per_seed = scenarios_per_seed_override
            print_info(f"Scenarios per seed overridden to {scenarios_per_seed_override}")
        
        # Set specific limits
        if scam_limit is not None:
            config.scam_sample_limit = scam_limit
            print_info(f"Scam conversation limit set to {scam_limit}")
        
        if legit_limit is not None:
            config.legit_sample_limit = legit_limit
            print_info(f"Legitimate conversation limit set to {legit_limit}")
        
        # Set generation mode
        config.generation_mode = generation_mode
        if generation_mode != "both":
            print_info(f"Generation mode: {generation_mode}")
        
        # Initialize and run pipeline
        runner = PipelineRunner(config, steps, generation_mode=generation_mode)
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
            # Note: preprocessing paths removed as they're no longer in new config structure
            ("Seeds input", config.multi_turn_input_path),
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
        ("conversation", "Generate multi-turn scam conversations using LLM"),
        ("legit", "Generate legitimate (non-scam) conversations"),
        ("tts", "Convert text conversations to audio using ElevenLabs TTS"),
        ("postprocess", "Format JSON files and package audio into ZIP archives"),
    ]
    
    print("Available steps (in execution order):\n")
    for step, description in steps:
        print(f"  {step:<15} - {description}")
    
    print("\nUsage examples:")
    print("  python main.py --locale ms-my --steps conversation legit")
    print("  python main.py --locale ar-sa --steps tts postprocess")
    print("  python main.py --locale ja-jp  # Run all steps")
    
    return 0


def validate_voices(language: str, config_dir: str = "./configs", output_dir: str = "./output") -> int:
    """
    Validate ElevenLabs voice IDs for a specific locale.
    
    Args:
        language: Language to validate voices for
        config_dir: Configuration directory
        output_dir: Output directory
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        print_step_header(f"Voice Validation for {language}")
        
        # Get API key
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            print_error("ELEVENLABS_API_KEY environment variable not found")
            return 1
        
        # Initialize components
        validator = VoiceValidator(api_key, verbose=True)
        config_manager = LocaleConfigManager(f"{config_dir}/localizations")
        
        # Check if locale exists
        if language not in config_manager.locales:
            print_error(f"Locale '{language}' not found")
            print_info(f"Available locales: {', '.join(config_manager.locales)}")
            return 1
        
        # Extract voice IDs for the specific locale
        locale_voice_ids = {language: config_manager.load_config(language).get('voices', {}).get('ids', [])}
        
        # Get unique voice IDs to validate
        unique_voice_ids = set()
        for ids in locale_voice_ids.values():
            unique_voice_ids.update(ids)
        
        if not unique_voice_ids:
            print_warning("No voice IDs found to validate")
            return 0
        
        # Validate voice IDs
        print_info(f"Validating {len(unique_voice_ids)} voice IDs...")
        results = validator.validate_voice_ids_sync(list(unique_voice_ids))
        
        # Print results
        _print_validation_results(results, locale_voice_ids, check_minimum=True)
        
        # Check for validation failures
        invalid_count = sum(1 for is_valid, _ in results.values() if not is_valid)
        if invalid_count > 0:
            print_error(f"Found {invalid_count} invalid voice IDs")
            return 1
        
        print_info("All voice IDs are valid!")
        return 0
        
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
        print_step_header("Voice Validation for All Locales")
        
        # Get API key
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            print_error("ELEVENLABS_API_KEY environment variable not found")
            return 1
        
        # Initialize components
        validator = VoiceValidator(api_key, verbose=True)
        config_manager = LocaleConfigManager(f"{config_dir}/localizations")
        
        # Extract all voice IDs
        locale_voice_ids = config_manager.extract_all_voice_ids()
        
        # Get unique voice IDs to validate
        unique_voice_ids = set()
        for ids in locale_voice_ids.values():
            unique_voice_ids.update(ids)
        
        if not unique_voice_ids:
            print_warning("No voice IDs found to validate")
            return 0
        
        # Validate voice IDs
        print_info(f"Validating {len(unique_voice_ids)} unique voice IDs across {len(locale_voice_ids)} locales...")
        results = validator.validate_voice_ids_sync(list(unique_voice_ids))
        
        # Print results with minimum checking
        _print_validation_results(results, locale_voice_ids, check_minimum=True)
        
        # Update configs if requested
        if update_configs:
            print_info("\nUPDATING CONFIGURATIONS:")
            print("-" * 50)
            
            removed_voices = config_manager.remove_invalid_voices(results)
            
            for locale, removed_ids in removed_voices.items():
                if removed_ids:
                    print_info(f"  Updated {locale}: Removed {len(removed_ids)} invalid voice IDs")
                else:
                    print_info(f"  {locale}: No changes needed")
        
        # Check for validation failures
        invalid_count = sum(1 for is_valid, _ in results.values() if not is_valid)
        if invalid_count > 0:
            print_error(f"Found {invalid_count} invalid voice IDs across all locales")
            if not update_configs:
                print_info("Use --update-voice-configs to automatically remove invalid IDs")
            return 1
        
        print_info("All voice IDs are valid!")
        return 0
        
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
        print_step_header("Updating Voice Configurations")
        
        # Get API key
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            print_error("ELEVENLABS_API_KEY environment variable not found")
            return 1
        
        # Initialize components
        validator = VoiceValidator(api_key, verbose=True)
        config_manager = LocaleConfigManager(f"{config_dir}/localizations")
        
        # Extract all voice IDs
        locale_voice_ids = config_manager.extract_all_voice_ids()
        
        # Get unique voice IDs to validate
        unique_voice_ids = set()
        for ids in locale_voice_ids.values():
            unique_voice_ids.update(ids)
        
        if not unique_voice_ids:
            print_warning("No voice IDs found to validate")
            return 0
        
        # Validate voice IDs
        print_info(f"Validating {len(unique_voice_ids)} unique voice IDs...")
        results = validator.validate_voice_ids_sync(list(unique_voice_ids))
        
        # Update configurations
        print_info("\nUPDATING CONFIGURATIONS:")
        print("-" * 50)
        
        removed_voices = config_manager.remove_invalid_voices(results)
        updated_count = 0
        
        for locale, removed_ids in removed_voices.items():
            if removed_ids:
                print_info(f"  Updated {locale}: Removed {len(removed_ids)} invalid voice IDs")
                updated_count += len(removed_ids)
            else:
                print_info(f"  {locale}: No changes needed")
        
        if updated_count > 0:
            print_info(f"\nSuccessfully removed {updated_count} invalid voice IDs from configurations")
        else:
            print_info("\nNo invalid voice IDs found - all configurations are up to date")
        
        return 0
        
    except Exception as e:
        print_error(f"Voice configuration update failed: {e}")
        logger.exception("Voice configuration update error")
        return 1


def ensure_minimum_voices(config_dir: str = "./configs") -> int:
    """
    Check that all locales have at least 2 valid voice IDs for reliability.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Exit code (0 for success, 1 if some locales need more voices)
    """
    try:
        print_step_header("Minimum Voice Requirements Check")
        
        # Get API key
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            print_error("ELEVENLABS_API_KEY environment variable not found")
            return 1
        
        # Initialize components
        validator = VoiceValidator(api_key, verbose=True)
        config_manager = LocaleConfigManager(f"{config_dir}/localizations")
        
        # Extract all voice IDs
        locale_voice_ids = config_manager.extract_all_voice_ids()
        
        # Get unique voice IDs to validate
        unique_voice_ids = set()
        for ids in locale_voice_ids.values():
            unique_voice_ids.update(ids)
        
        if not unique_voice_ids:
            print_warning("No voice IDs found to validate")
            return 0
        
        # Validate voice IDs
        print_info(f"Validating {len(unique_voice_ids)} unique voice IDs across {len(locale_voice_ids)} locales...")
        results = validator.validate_voice_ids_sync(list(unique_voice_ids))
        
        # Check minimum requirements
        print_info("\nMINIMUM VOICE ANALYSIS:")
        print("-" * 50)
        
        summary = validator.check_minimum_requirements(results, locale_voice_ids, minimum=2)
        
        print(f"Health Score: {summary.health_score:.1f}/100")
        
        if summary.locales_below_minimum > 0:
            print_warning(f"\nLOCALES NEEDING ATTENTION ({summary.locales_below_minimum}):")
            for status in summary.locale_statuses:
                if not status.meets_minimum:
                    needed = 2 - status.valid_voices
                    print(f"  {status.locale_id}: Needs {needed} more voice(s)")
                    print(f"    Use: python main.py --suggest-voices {status.locale_id}")
            
            print_error(f"\n{summary.locales_below_minimum} locales need additional voices for reliability")
            return 1
        else:
            print_info("\nAll locales meet minimum voice requirements!")
            return 0
        
    except Exception as e:
        print_error(f"Minimum voice check failed: {e}")
        logger.exception("Minimum voice check error")
        return 1


def suggest_voices_for_locale(locale: str, config_dir: str = "./configs") -> int:
    """
    Suggest additional voices for a specific locale.
    
    Args:
        locale: Locale to suggest voices for
        config_dir: Configuration directory
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        print_step_header(f"Voice Suggestions for {locale}")
        
        # Get API key
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            print_error("ELEVENLABS_API_KEY environment variable not found")
            return 1
        
        # Initialize components
        validator = VoiceValidator(api_key, verbose=True)
        config_manager = LocaleConfigManager(f"{config_dir}/localizations")
        
        # Check if locale exists
        if locale not in config_manager.locales:
            print_error(f"Locale '{locale}' not found")
            print_info(f"Available locales: {', '.join(config_manager.locales)}")
            return 1
        
        # Load locale configuration
        locale_config = config_manager.load_locale_config(locale)
        
        # Get voice suggestions
        print_info(f"Finding compatible voices for {locale}...")
        suggestions = validator.suggest_voices_for_locale(
            locale,
            locale_config.language_code,
            locale_config.voice_ids,
            needed_count=2
        )
        
        _print_voice_suggestions(suggestions, locale)
        
        if suggestions:
            print_info(f"\nFound {len(suggestions)} voice suggestions for {locale}")
            print_info("To add a voice, manually update the configuration file:")
            print_info(f"  configs/localizations/{locale}/config.json")
        else:
            print_warning(f"No compatible voices found for {locale}")
        
        return 0
        
    except Exception as e:
        print_error(f"Voice suggestion failed: {e}")
        logger.exception("Voice suggestion error")
        return 1