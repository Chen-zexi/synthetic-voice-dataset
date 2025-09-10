#!/usr/bin/env python3
"""
Voice Scam Dataset Generator - Main Entry Point

This tool generates multilingual voice scam detection datasets by creating synthetic
phone conversations for training anti-scam ML models.
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to Python path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from cli.commands import (
    run_pipeline,
    list_languages,
    list_locales,
    validate_config,
    validate_voices,
    show_pipeline_steps,
    ensure_minimum_voices,
    suggest_voices_for_locale
)
from cli.utils import setup_logging, print_banner
from cli.ui import InteractiveUI


def main():
    """Main entry point for the voice scam dataset generator."""
    parser = argparse.ArgumentParser(
        description='Generate multilingual voice scam detection datasets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                      # Run in interactive mode
  %(prog)s --interactive                        # Run in interactive mode
  %(prog)s --locale ms-my                       # Run full pipeline for Malay (Malaysia)
  %(prog)s --locale ar-sa --steps conversation  # Generate only scam conversations for Arabic (Saudi)
  %(prog)s --locale ja-jp --steps conversation legit  # Generate both conversation types for Japanese
  %(prog)s --list-locales                       # Show available locales
  %(prog)s --validate-config ms-my              # Validate Malay configuration
  %(prog)s --validate-voices ja-jp              # Validate ElevenLabs voices for Japanese
  %(prog)s --validate-all-voices                # Validate all voice IDs across all locales
  %(prog)s --ensure-minimum-voices              # Check all locales have ≥2 voices
  %(prog)s --suggest-voices ar-sa               # Get voice suggestions for Arabic Saudi
        """
    )
    
    # Main operation arguments
    parser.add_argument(
        '--locale', '-l',
        type=str,
        help='Locale to process (e.g., ar-sa, ms-my, ar-ae)'
    )
    
    parser.add_argument(
        '--steps', '-s',
        type=str,
        nargs='+',
        help='Pipeline steps to run (default: all). Available: conversation, legit, tts, postprocess'
    )
    
    # Configuration arguments
    parser.add_argument(
        '--config-dir',
        type=str,
        default='./configs',
        help='Directory containing configuration files (default: ./configs)'
    )
    
    # Information commands
    parser.add_argument(
        '--list-languages',
        action='store_true',
        help='List all available language configurations (legacy)'
    )
    
    parser.add_argument(
        '--list-locales',
        action='store_true',
        help='List all available locale configurations'
    )
    
    parser.add_argument(
        '--validate-config',
        type=str,
        metavar='LANGUAGE',
        help='Validate configuration for specified language'
    )
    
    parser.add_argument(
        '--validate-voices',
        type=str,
        metavar='LANGUAGE',
        help='Validate ElevenLabs voice IDs for specified language'
    )
    
    parser.add_argument(
        '--validate-all-voices',
        action='store_true',
        help='Validate all ElevenLabs voice IDs across all locales'
    )
    
    parser.add_argument(
        '--update-voice-configs',
        action='store_true',
        help='Update configuration files to remove invalid voice IDs'
    )
    
    parser.add_argument(
        '--ensure-minimum-voices',
        action='store_true',
        help='Check that all locales have at least 2 valid voice IDs for reliability'
    )
    
    parser.add_argument(
        '--suggest-voices',
        type=str,
        metavar='LOCALE',
        help='Suggest additional voices for a specific locale (e.g., ar-sa, ja-jp)'
    )
    
    parser.add_argument(
        '--show-steps',
        action='store_true',
        help='Show all available pipeline steps and their descriptions'
    )
    
    # Output control
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./output',
        help='Base output directory (default: ./output)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing output files'
    )
    
    parser.add_argument(
        '--total-limit', '-limit',
        type=int,
        help='Absolute maximum number of conversations to generate (overrides all other limits)'
    )
    
    # New generation control arguments
    parser.add_argument(
        '--generation-mode',
        choices=['seeds', 'conversations'],
        default='seeds',
        help='Control whether limits apply to seeds or total conversations (default: seeds)'
    )
    
    parser.add_argument(
        '--seed-limit',
        type=int,
        help='Number of unique seeds to use for generation'
    )
    
    parser.add_argument(
        '--conversation-count',
        type=int,
        help='Target number of conversations to generate (calculates seeds needed)'
    )
    
    parser.add_argument(
        '--scenarios-per-seed',
        type=int,
        help='Override number of scenarios to generate per seed'
    )
    
    # Generation mode control
    parser.add_argument(
        '--scam',
        action='store_true',
        help='Generate scam conversations (default if neither --scam nor --legit specified)'
    )
    
    parser.add_argument(
        '--legit',
        action='store_true',
        help='Generate legitimate conversations'
    )
    
    parser.add_argument(
        '--scam-limit',
        type=int,
        help='Specific limit for scam conversation generation'
    )
    
    parser.add_argument(
        '--legit-limit',
        type=int,
        help='Specific limit for legitimate conversation generation'
    )
    
    # Interface mode
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive menu mode'
    )
    
    # Logging
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress all output except errors'
    )
    
    # Timestamp control
    parser.add_argument(
        '--no-timestamp',
        action='store_true',
        help='Do not use timestamp in output directory structure (use old structure)'
    )
    
    parser.add_argument(
        '--use-timestamp',
        type=str,
        metavar='TIMESTAMP',
        help='Use specific timestamp directory (e.g., 0909_2040) or "new" to force new timestamp'
    )
    
    # Model and generation control
    parser.add_argument(
        '--model',
        type=str,
        help='Override LLM model (e.g., gpt-4o, gpt-5-nano, claude-3-opus)'
    )
    
    parser.add_argument(
        '--reasoning-effort',
        type=str,
        choices=['low', 'medium', 'high', 'minimal'],
        help='Reasoning effort level for reasoning models (gpt-5 models)'
    )
    
    parser.add_argument(
        '--random-seed',
        type=int,
        help='Random seed for reproducible generation (ensures same seed/profile selection)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'WARNING' if args.quiet else 'INFO'
    setup_logging(level=log_level)
    
    # Handle interactive mode first
    if args.interactive or len(sys.argv) == 1:
        if not args.quiet:
            print_banner()
        ui = InteractiveUI(config_dir=args.config_dir, output_dir=args.output_dir, use_timestamp=not args.no_timestamp)
        ui.run()
        return 0
    
    # Print banner unless quiet mode
    if not args.quiet:
        print_banner()
    
    # Handle information commands
    if args.list_languages:
        return list_languages(args.config_dir)
    
    if args.list_locales:
        return list_locales(args.config_dir)
    
    if args.validate_config:
        return validate_config(args.validate_config, args.config_dir)
    
    if args.validate_voices:
        return validate_voices(args.validate_voices, args.config_dir, args.output_dir)
    
    if args.validate_all_voices:
        from cli.commands import validate_all_voices
        return validate_all_voices(args.config_dir, args.update_voice_configs)
    
    if args.update_voice_configs:
        from cli.commands import update_voice_configs
        return update_voice_configs(args.config_dir)
    
    if args.ensure_minimum_voices:
        return ensure_minimum_voices(args.config_dir)
    
    if args.suggest_voices:
        return suggest_voices_for_locale(args.suggest_voices, args.config_dir)
    
    if args.show_steps:
        return show_pipeline_steps()
    
    # Determine which identifier to use
    if not args.locale:
        parser.error("--locale is required to run the pipeline. Use --help for more information.")
    identifier = args.locale
    
    # Determine generation mode
    generation_mode = "both"
    if args.scam and not args.legit:
        generation_mode = "scam"
    elif args.legit and not args.scam:
        generation_mode = "legit"
    elif args.scam and args.legit:
        generation_mode = "both"
    # If neither flag specified, default to "both" for backward compatibility
    
    # total_limit now acts as an absolute maximum that overrides all other settings
    # No longer using sample_limit
    
    # Run the pipeline
    try:
        run_pipeline(
            language=identifier,  # ConfigLoader will handle both languages and locales
            steps=args.steps,
            config_dir=args.config_dir,
            output_dir=args.output_dir,
            force=args.force,
            scam_limit=args.scam_limit,
            legit_limit=args.legit_limit,
            generation_mode=generation_mode,
            verbose=args.verbose,
            use_timestamp=not args.no_timestamp,
            specific_timestamp=args.use_timestamp,
            model_override=args.model,
            reasoning_effort_override=args.reasoning_effort,
            random_seed=args.random_seed,
            generation_control_mode=args.generation_mode,
            seed_limit=args.seed_limit,
            total_limit=args.total_limit,  # Absolute cap on conversations
            conversation_count=args.conversation_count,  # Target conversation count
            scenarios_per_seed_override=args.scenarios_per_seed
        )
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())