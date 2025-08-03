"""
User interface components for the Voice Scam Dataset Generator CLI.

Provides menu-driven interface components and interactive navigation.
"""

import os
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

from cli.commands import (
    run_pipeline,
    list_languages,
    list_locales, 
    validate_config,
    show_pipeline_steps
)
from cli.utils import (
    setup_logging,
    print_banner,
    print_step_header,
    print_info,
    print_warning,
    print_error,
    confirm_action
)
from config.config_loader import ConfigLoader


class InteractiveUI:
    """Interactive user interface for the pipeline."""
    
    def __init__(self, config_dir: str = "./configs", output_dir: str = "./output"):
        """
        Initialize the interactive UI.
        
        Args:
            config_dir: Configuration directory path
            output_dir: Output directory path
        """
        self.config_dir = config_dir
        self.output_dir = output_dir
        self.config_loader = ConfigLoader(config_dir, output_dir)
        self.current_locale = None
        self.pipeline_steps = [
            'preprocess',
            'translate', 
            'conversation',
            'tts',
            'postprocess'
        ]
        
    def run(self):
        """Run the interactive UI."""
        while True:
            try:
                self._show_main_menu()
                choice = input("\nEnter your choice: ").strip()
                
                if choice == '1':
                    self._select_locale_menu()
                elif choice == '2':
                    self._run_pipeline_menu()
                elif choice == '3':
                    self._run_specific_steps_menu()
                elif choice == '4':
                    self._configuration_menu()
                elif choice == '5':
                    self._monitoring_menu()
                elif choice == '6':
                    self._help_menu()
                elif choice.lower() in ['q', 'quit', 'exit']:
                    print("\nGoodbye!")
                    break
                else:
                    print_warning("Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print_error(f"An error occurred: {e}")
                
    def _show_main_menu(self):
        """Display the main menu."""
        print_step_header("Voice Scam Dataset Generator - Main Menu")
        
        # Show current locale if selected
        if self.current_locale:
            print(f"Current Locale: {self.current_locale}")
        else:
            print("No locale selected")
            
        print("\nMain Options:")
        print("  1. Select Locale/Language")
        print("  2. Run Full Pipeline")
        print("  3. Run Specific Steps")
        print("  4. Configuration Management")
        print("  5. Monitoring & Status")
        print("  6. Help & Information")
        print("  Q. Quit")
        
    def _select_locale_menu(self):
        """Show locale selection menu."""
        print_step_header("Locale Selection")
        
        # Get available localizations
        localizations = self.config_loader.list_localizations()
        
        if not localizations:
            print_warning("No locales found in configuration directory.")
            return
            
        # Group by language
        by_language = {}
        for locale_id, description in localizations.items():
            lang_code = locale_id.split('-')[0] if '-' in locale_id else locale_id
            if lang_code not in by_language:
                by_language[lang_code] = []
            by_language[lang_code].append((locale_id, description))
        
        print("Available Locales:")
        menu_items = []
        counter = 1
        
        for lang_code in sorted(by_language.keys()):
            print(f"\n{lang_code.upper()}:")
            for locale_id, description in sorted(by_language[lang_code]):
                print(f"  {counter}. {locale_id:<10} - {description}")
                menu_items.append(locale_id)
                counter += 1
        
        print(f"\n  0. Back to main menu")
        
        try:
            choice = input("\nSelect locale (number): ").strip()
            
            if choice == '0':
                return
                
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(menu_items):
                selected_locale = menu_items[choice_idx]
                self.current_locale = selected_locale
                print_info(f"Selected locale: {selected_locale}")
                
                # Show locale details
                self._show_locale_details(selected_locale)
            else:
                print_warning("Invalid selection.")
                
        except ValueError:
            print_warning("Please enter a valid number.")
        except Exception as e:
            print_error(f"Error selecting locale: {e}")
    
    def _show_locale_details(self, locale_id: str):
        """Show details for a selected locale."""
        try:
            config = self.config_loader.load_localization(locale_id)
            print(f"\nLocale Details:")
            print(f"   Language: {config.language_name} ({config.language_code})")
            print(f"   Region: {config.region}")
            print(f"   Translation: {config.translation_from_code} → {config.translation_to_code}")
            print(f"   Voice IDs: {len(config.voice_ids[config.language_code])} available")
            print(f"   Categories: {len(config.legit_call_categories)} conversation types")
        except Exception as e:
            print_warning(f"Could not load locale details: {e}")
    
    def _run_pipeline_menu(self):
        """Show full pipeline execution menu."""
        if not self.current_locale:
            print_warning("Please select a locale first.")
            return
            
        print_step_header("Run Full Pipeline")
        print(f"Locale: {self.current_locale}")
        print("\nThis will run all pipeline steps:")
        for i, step in enumerate(self.pipeline_steps, 1):
            print(f"  {i}. {step.title()}")
        
        print("\nOptions:")
        print("  1. Run with default settings")
        print("  2. Run with custom sample limit")
        print("  3. Run with force overwrite")
        print("  4. Run with sample limit + force overwrite")
        print("  0. Back to main menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            self._execute_pipeline()
        elif choice == '2':
            self._execute_pipeline_with_limit()
        elif choice == '3':
            self._execute_pipeline_with_force()
        elif choice == '4':
            self._execute_pipeline_with_limit_and_force()
        else:
            print_warning("Invalid choice.")
    
    def _run_specific_steps_menu(self):
        """Show specific steps execution menu."""
        if not self.current_locale:
            print_warning("Please select a locale first.")
            return
            
        print_step_header("Run Specific Steps")
        print(f"Locale: {self.current_locale}")
        print("\nAvailable steps:")
        
        for i, step in enumerate(self.pipeline_steps, 1):
            print(f"  {i}. {step.title()}")
        
        print("\nSelect steps to run (e.g., '1,3,5' or '1-3'):")
        print("  A. All steps")
        print("  0. Back to main menu")
        
        choice = input("\nEnter your selection: ").strip()
        
        if choice == '0':
            return
        elif choice.lower() == 'a':
            selected_steps = self.pipeline_steps
        else:
            selected_steps = self._parse_step_selection(choice)
            
        if selected_steps:
            print(f"\nSelected steps: {', '.join(selected_steps)}")
            
            # Ask for execution options
            print("\nExecution Options:")
            print("  1. Run with default settings")
            print("  2. Run with custom sample limit")
            print("  3. Run with force overwrite")
            print("  4. Run with sample limit + force overwrite")
            
            exec_choice = input("\nChoose execution option (1): ").strip() or "1"
            
            if exec_choice == "1":
                if confirm_action("Proceed with execution?", default_yes=True):
                    self._execute_pipeline(steps=selected_steps)
            elif exec_choice == "2":
                self._execute_pipeline_with_steps_and_limit(selected_steps)
            elif exec_choice == "3":
                if confirm_action("This will overwrite existing files. Continue?", default_yes=True):
                    self._execute_pipeline(steps=selected_steps, force=True)
            elif exec_choice == "4":
                self._execute_pipeline_with_steps_limit_and_force(selected_steps)
            else:
                print_warning("Invalid option selected.")
    
    def _parse_step_selection(self, selection: str) -> List[str]:
        """Parse step selection input."""
        try:
            selected_steps = []
            
            for part in selection.split(','):
                part = part.strip()
                
                if '-' in part:
                    # Range selection (e.g., "1-3")
                    start, end = map(int, part.split('-'))
                    for i in range(start, end + 1):
                        if 1 <= i <= len(self.pipeline_steps):
                            selected_steps.append(self.pipeline_steps[i - 1])
                else:
                    # Single selection
                    i = int(part)
                    if 1 <= i <= len(self.pipeline_steps):
                        selected_steps.append(self.pipeline_steps[i - 1])
            
            return list(dict.fromkeys(selected_steps))  # Remove duplicates while preserving order
            
        except ValueError:
            print_warning("Invalid selection format. Use numbers separated by commas or ranges (e.g., '1,3,5' or '1-3').")
            return []
    
    def _configuration_menu(self):
        """Show configuration management menu."""
        print_step_header("Configuration Management")
        
        print("Configuration Options:")
        print("  1. List all locales")
        print("  2. Validate current locale configuration")
        print("  3. Show pipeline steps")
        print("  4. View configuration details")
        print("  0. Back to main menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            list_locales(self.config_dir)
        elif choice == '2':
            if self.current_locale:
                validate_config(self.current_locale, self.config_dir)
            else:
                print_warning("Please select a locale first.")
        elif choice == '3':
            show_pipeline_steps()
        elif choice == '4':
            self._view_config_details()
        else:
            print_warning("Invalid choice.")
    
    def _view_config_details(self):
        """View detailed configuration information."""
        if not self.current_locale:
            print_warning("Please select a locale first.")
            return
            
        try:
            config = self.config_loader.load_localization(self.current_locale)
            
            print_step_header(f"Configuration Details - {self.current_locale}")
            print(f"Language: {config.language_name} ({config.language_code})")
            print(f"Region: {config.region}")
            print(f"Translation Service: {config.translation_service}")
            print(f"Translation Path: {config.translation_from_code} → {config.translation_intermediate_code} → {config.translation_to_code}")
            print(f"Voice Model: {config.voice_model_id}")
            print(f"Voice IDs: {', '.join(config.voice_ids[config.language_code])}")
            print(f"Max Conversations: {config.max_conversation}")
            print(f"Legit Conversations: {config.num_legit_conversation}")
            print(f"Sample Limit: {config.sample_limit}")
            
            print(f"\nPaths:")
            print(f"  Input: {config.preprocessing_input_path}")
            print(f"  Output: {config.output_dir}")
            print(f"  Placeholders: {config.preprocessing_map_path}")
            
        except Exception as e:
            print_error(f"Error loading configuration: {e}")
    
    def _monitoring_menu(self):
        """Show monitoring and status menu."""
        print_step_header("Monitoring & Status")
        
        print("Monitoring Options:")
        print("  1. Check output directory status")
        print("  2. View recent pipeline runs")
        print("  3. Clean output directory")
        print("  0. Back to main menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            self._check_output_status()
        elif choice == '2':
            self._view_recent_runs()
        elif choice == '3':
            self._clean_output_directory()
        else:
            print_warning("Invalid choice.")
    
    def _check_output_status(self):
        """Check the status of output directories."""
        if not self.current_locale:
            print_warning("Please select a locale first.")
            return
            
        output_path = Path(self.output_dir) / self.current_locale
        
        print(f"\n Output Status for {self.current_locale}:")
        print(f"Base directory: {output_path}")
        
        if output_path.exists():
            # Check each subdirectory
            subdirs = ['intermediate', 'audio', 'final']
            for subdir in subdirs:
                subdir_path = output_path / subdir
                if subdir_path.exists():
                    file_count = len(list(subdir_path.rglob('*')))
                    print(f"  ✓ {subdir}: {file_count} files")
                else:
                    print(f"  ✗ {subdir}: not found")
        else:
            print("  ✗ Output directory does not exist")
    
    def _view_recent_runs(self):
        """View information about recent pipeline runs."""
        print_info("Recent runs feature not yet implemented.")
    
    def _clean_output_directory(self):
        """Clean the output directory."""
        if not self.current_locale:
            print_warning("Please select a locale first.")
            return
            
        output_path = Path(self.output_dir) / self.current_locale
        
        if not output_path.exists():
            print_info("Output directory does not exist.")
            return
            
        if confirm_action(f"Delete all files in {output_path}? This cannot be undone."):
            try:
                import shutil
                shutil.rmtree(output_path)
                print_info("Output directory cleaned successfully.")
            except Exception as e:
                print_error(f"Error cleaning directory: {e}")
    
    def _help_menu(self):
        """Show help and information menu."""
        print_step_header("Help & Information")
        
        print("Help Options:")
        print("  1. Show pipeline overview")
        print("  2. Show command examples")
        print("  3. Show troubleshooting tips")
        print("  4. About this tool")
        print("  0. Back to main menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            self._show_pipeline_overview()
        elif choice == '2':
            self._show_command_examples()
        elif choice == '3':
            self._show_troubleshooting()
        elif choice == '4':
            self._show_about()
        else:
            print_warning("Invalid choice.")
    
    def _show_pipeline_overview(self):
        """Show pipeline overview."""
        print_step_header("Pipeline Overview")
        
        print("The Voice Scam Dataset Generator pipeline consists of 5 main steps:")
        print()
        print("1. PREPROCESS")
        print("   Extract placeholders from Chinese source text and create mappings")
        print()
        print("2. TRANSLATE") 
        print("   Translate Chinese text to English using translation services")
        print()
        print("3. CONVERSATION")
        print("   Generate multi-turn dialogues and translate to target language")
        print()
        print("4. TTS (Text-to-Speech)")
        print("   Convert conversations to audio using ElevenLabs voices")
        print()
        print("5. POSTPROCESS")
        print("   Format JSON outputs and package audio files")
    
    def _show_command_examples(self):
        """Show command examples."""
        print_step_header("Command Examples")
        
        print("Non-interactive usage examples:")
        print()
        print("# Run full pipeline for Arabic (Saudi Arabia)")
        print("python main.py --locale ar-sa")
        print()
        print("# Run specific steps only")
        print("python main.py --locale ar-sa --steps preprocess translate")
        print()
        print("# Run with sample limit for testing")
        print("python main.py --locale ar-sa --sample-limit 10")
        print()
        print("# List available locales")
        print("python main.py --list-locales")
        print()
        print("# Validate configuration")
        print("python main.py --validate-config ar-sa")
    
    def _show_troubleshooting(self):
        """Show troubleshooting tips."""
        print_step_header("Troubleshooting Tips")
        
        print("Common Issues:")
        print()
        print("API Keys Missing:")
        print("   - Ensure OPENAI_API_KEY and ELEVENLABS_API_KEY are set in .env file")
        print("   - Check that .env file is in the project root directory")
        print()
        print("Translation Errors:")
        print("   - Verify internet connection for translation services")
        print("   - Check translation service quotas and limits")
        print()
        print("Voice Generation Issues:")
        print("   - Verify ElevenLabs API key and quotas")
        print("   - Check voice IDs in configuration are valid")
        print()
        print("Memory Issues:")
        print("   - Use --sample-limit for testing with smaller datasets")
        print("   - Increase system memory or use cloud instances")
        print()
        print("Permission Errors:")
        print("   - Ensure write permissions for output directory")
        print("   - Check file system space availability")
    
    def _show_about(self):
        """Show about information."""
        print_step_header("About Voice Scam Dataset Generator")
        
        print("This tool generates multilingual voice scam detection datasets by creating")
        print("synthetic phone conversations for training anti-scam ML models.")
        print()
        print("Features:")
        print("• Multi-language support (Arabic, Malay, and extensible)")
        print("• Realistic conversation generation using GPT-4")
        print("• High-quality voice synthesis with ElevenLabs TTS")
        print("• Configurable pipeline with locale-specific settings")
        print("• Audio post-processing for phone call quality")
        print()
        print("Architecture:")
        print("• Modular design with language-agnostic components")
        print("• Configuration-driven locale support")
        print("• Placeholder system for cultural localization")
        print("• Both scam and legitimate conversation generation")
    
    def _execute_pipeline(self, steps: Optional[List[str]] = None, sample_limit: Optional[int] = None, force: bool = False):
        """Execute the pipeline with given parameters."""
        try:
            print_info(f"Starting pipeline for {self.current_locale}...")
            
            run_pipeline(
                language=self.current_locale,
                steps=steps,
                config_dir=self.config_dir,
                output_dir=self.output_dir,
                force=force,
                sample_limit=sample_limit
            )
            
        except Exception as e:
            print_error(f"Pipeline execution failed: {e}")
    
    def _execute_pipeline_with_limit(self):
        """Execute pipeline with custom sample limit."""
        try:
            sample_limit = int(input("Enter sample limit (number of samples to process): ").strip())
            self._execute_pipeline(sample_limit=sample_limit)
        except ValueError:
            print_warning("Invalid sample limit. Please enter a number.")
    
    def _execute_pipeline_with_force(self):
        """Execute pipeline with force overwrite."""
        if confirm_action("This will overwrite existing output files. Continue?", default_yes=True):
            self._execute_pipeline(force=True)
    
    def _execute_pipeline_with_limit_and_force(self):
        """Execute pipeline with custom sample limit and force overwrite."""
        try:
            sample_limit = int(input("Enter sample limit (number of samples to process): ").strip())
            if confirm_action("This will overwrite existing files. Continue?", default_yes=True):
                self._execute_pipeline(sample_limit=sample_limit, force=True)
        except ValueError:
            print_warning("Invalid sample limit. Please enter a number.")
    
    def _execute_pipeline_with_steps_and_limit(self, steps: List[str]):
        """Execute specific steps with custom sample limit."""
        try:
            sample_limit = int(input("Enter sample limit (number of samples to process): ").strip())
            if confirm_action("Proceed with execution?", default_yes=True):
                self._execute_pipeline(steps=steps, sample_limit=sample_limit)
        except ValueError:
            print_warning("Invalid sample limit. Please enter a number.")
    
    def _execute_pipeline_with_steps_limit_and_force(self, steps: List[str]):
        """Execute specific steps with custom sample limit and force overwrite."""
        try:
            sample_limit = int(input("Enter sample limit (number of samples to process): ").strip())
            if confirm_action("This will overwrite existing files. Continue?", default_yes=True):
                self._execute_pipeline(steps=steps, sample_limit=sample_limit, force=True)
        except ValueError:
            print_warning("Invalid sample limit. Please enter a number.")