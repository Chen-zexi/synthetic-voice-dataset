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
    show_pipeline_steps
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
  %(prog)s --language arabic                    # Run full pipeline for Arabic
  %(prog)s --language malay --steps preprocess  # Run only preprocessing for Malay
  %(prog)s --list-languages                     # Show available languages
  %(prog)s --validate-config arabic             # Validate Arabic configuration
        """
    )
    
    # Main operation arguments
    parser.add_argument(
        '--language', '-l',
        type=str,
        help='Language to process (e.g., arabic, malay) - for backward compatibility'
    )
    
    parser.add_argument(
        '--locale',
        type=str,
        help='Locale to process (e.g., ar-sa, ms-my, ar-ae)'
    )
    
    parser.add_argument(
        '--steps', '-s',
        type=str,
        nargs='+',
        help='Pipeline steps to run (default: all). Available: preprocess, translate, conversation, tts, postprocess'
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
        '--sample-limit',
        type=int,
        help='Limit the number of samples to process (for testing)'
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
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'WARNING' if args.quiet else 'INFO'
    setup_logging(level=log_level)
    
    # Handle interactive mode first
    if args.interactive or len(sys.argv) == 1:
        if not args.quiet:
            print_banner()
        ui = InteractiveUI(config_dir=args.config_dir, output_dir=args.output_dir)
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
    
    if args.show_steps:
        return show_pipeline_steps()
    
    # Determine which identifier to use
    identifier = None
    if args.locale:
        identifier = args.locale
    elif args.language:
        identifier = args.language
    else:
        parser.error("Either --locale or --language is required to run the pipeline. Use --help for more information.")
    
    # Run the pipeline
    try:
        run_pipeline(
            language=identifier,  # ConfigLoader will handle both languages and locales
            steps=args.steps,
            config_dir=args.config_dir,
            output_dir=args.output_dir,
            force=args.force,
            sample_limit=args.sample_limit
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