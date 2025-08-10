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
    validate_voices,
    validate_all_voices,
    ensure_minimum_voices,
    suggest_voices_for_locale,
    show_pipeline_steps,
    cache_translation,
    list_cached_translations
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
from config.locale_manager import LocaleConfigManager
from tts.voice_validator import VoiceValidator
from cli.voice_quality_commands import VoiceQualityManager


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
        self.voice_quality_manager = VoiceQualityManager(self.config_loader)
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
            
            # Enhanced voice information with health status
            try:
                config_manager = LocaleConfigManager(f"{self.config_dir}/localizations")
                locale_config = config_manager.load_config(locale_id)
                voice_count = len(locale_config['voices']['ids'])
                
                # Voice status with health indicators
                if voice_count >= 2:
                    voice_status = f"✅ {voice_count} voices (meets minimum)"
                elif voice_count == 1:
                    voice_status = f"⚠️ {voice_count} voice (needs 1 more for redundancy)"
                else:
                    voice_status = f"❌ {voice_count} voices (critical - needs voices)"
                
                print(f"   Voice IDs: {voice_status}")
                
            except Exception:
                # Fallback to old format if new config structure fails
                voice_count = len(config.voice_ids[config.language_code])
                print(f"   Voice IDs: {voice_count} available")
            
            print(f"   Categories: {len(config.legit_call_categories)} conversation types")
            
            # Show quick action suggestions
            if voice_count < 2:
                print(f"\n   💡 Tip: Use Configuration > Voice ID Management to add more voices")
                
        except KeyError as e:
            print_warning(f"Locale configuration is missing required field: {e}")
            print_info("This locale may need to be updated to the new configuration format.")
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
        print("  5. Manage translation cache")
        print("  6. Voice ID Management")
        print("  7. Voice Quality & V3 Features")
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
        elif choice == '5':
            self._translation_cache_menu()
        elif choice == '6':
            self._voice_management_menu()
        elif choice == '7':
            self._voice_quality_menu()
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
            
            print(f"\nLLM Settings:")
            print(f"  Provider: {getattr(config, 'llm_provider', 'openai')}")
            print(f"  Model: {getattr(config, 'llm_model', 'gpt-4o')}")
            print(f"  Temperature: {getattr(config, 'llm_temperature', 1.0)}")
            print(f"  Max Tokens: {getattr(config, 'llm_max_tokens', None) or 'default'}")
            print(f"  Top P: {getattr(config, 'llm_top_p', 0.95)}")
            print(f"  N: {getattr(config, 'llm_n', 1)}")
            print(f"  Max Concurrent: {getattr(config, 'max_concurrent_requests', 10)}")
            
            print(f"\nVoice Settings:")
            print(f"  Model: {config.voice_model_id}")
            print(f"  Voice IDs: {', '.join(config.voice_ids[config.language_code])}")
            
            print(f"\nConversation Settings:")
            print(f"  Max Conversations: {config.max_conversation}")
            print(f"  Legit Conversations: {config.num_legit_conversation}")
            print(f"  Sample Limit: {config.sample_limit}")
            
            print(f"\nPaths:")
            print(f"  Input: {config.preprocessing_input_path}")
            print(f"  Output: {config.output_dir}")
            print(f"  Placeholders: {config.preprocessing_map_path}")
            
        except Exception as e:
            print_error(f"Error loading configuration: {e}")
    
    def _translation_cache_menu(self):
        """Show translation cache management menu."""
        print_step_header("Translation Cache Management")
        
        print("Cache Options:")
        print("  1. Generate cached translation")
        print("  2. List cached translations")
        print("  3. Clear cache")
        print("  0. Back to configuration menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            self._generate_cached_translation()
        elif choice == '2':
            list_cached_translations()
        elif choice == '3':
            self._clear_translation_cache()
        else:
            print_warning("Invalid choice.")
    
    def _generate_cached_translation(self):
        """Generate cached Chinese to English translation."""
        print_step_header("Generate Cached Translation")
        
        # Get available translation services
        services = ["google", "argos", "qwen"]
        
        print("Available translation services:")
        for i, service in enumerate(services, 1):
            print(f"  {i}. {service}")
        
        service_choice = input("\nSelect translation service (1): ").strip() or "1"
        
        try:
            service_idx = int(service_choice) - 1
            if 0 <= service_idx < len(services):
                selected_service = services[service_idx]
                
                # If Qwen is selected, ask for model
                if selected_service == "qwen":
                    self._select_qwen_model_and_generate(selected_service)
                else:
                    self._execute_cache_generation(selected_service)
            else:
                print_warning("Invalid service selection.")
        except ValueError:
            print_warning("Please enter a valid number.")
    
    def _select_qwen_model_and_generate(self, service: str):
        """Select Qwen model and generate cache."""
        models = ["qwen-mt-turbo", "qwen-mt-plus"]
        
        print("\nAvailable Qwen models:")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model}")
        
        model_choice = input("\nSelect model (1): ").strip() or "1"
        
        try:
            model_idx = int(model_choice) - 1
            if 0 <= model_idx < len(models):
                selected_model = models[model_idx]
                self._execute_cache_generation(service, model=selected_model)
            else:
                print_warning("Invalid model selection.")
        except ValueError:
            print_warning("Please enter a valid number.")
    
    def _execute_cache_generation(self, service: str, model: Optional[str] = None):
        """Execute cache generation with selected service and model."""
        print_info(f"Generating cached translation using {service}")
        if model:
            print_info(f"Model: {model}")
        
        # Ask for force refresh
        force_refresh = confirm_action("Force refresh existing cache?", default_yes=False)
        
        # Execute cache generation
        try:
            cache_translation(
                service=service,
                model=model,
                force_refresh=force_refresh,
                config_dir=self.config_dir,
                verbose=True
            )
            print_info("Cache generation completed successfully.")
        except Exception as e:
            print_error(f"Error generating cache: {e}")
    
    def _clear_translation_cache(self):
        """Clear translation cache."""
        if confirm_action("Clear all translation cache files? This cannot be undone."):
            try:
                import shutil
                cache_dir = Path(self.config_dir).parent / "data" / "translation_cache"
                if cache_dir.exists():
                    shutil.rmtree(cache_dir)
                    print_info("Translation cache cleared successfully.")
                else:
                    print_info("No cache directory found.")
            except Exception as e:
                print_error(f"Error clearing cache: {e}")
    
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
        print("1. PREPROCESSING")
        print("   Extract placeholders from Chinese source text and create mappings")
        print()
        print("2. TRANSLATE") 
        print("   Translate Chinese text to English using translation services")
        print()
        print("3. CONVERSATION")
        print("   Generate multi-turn dialogues and translate to target language")
        print()
        print("4. TTS")
        print("   Convert conversations to audio using ElevenLabs voices")
        print()
        print("5. POSTPROCESS")
        print("   Format JSON outputs and package audio files")
    
    def _show_command_examples(self):
        """Show command examples."""
        print_step_header("Command Examples")
        
        print("INTERACTIVE MODE:")
        print("python main.py                           # Launch interactive interface")
        print("python main.py --interactive             # Launch interactive interface")
        print()
        
        print("PIPELINE EXECUTION:")
        print("python main.py --locale ar-sa            # Run full pipeline for Arabic (Saudi Arabia)")
        print("python main.py --locale ko-kr            # Run full pipeline for Korean")
        print("python main.py --locale ja-jp            # Run full pipeline for Japanese")
        print("python main.py --locale ms-my            # Run full pipeline for Malay")
        print()
        print("# Run specific steps only")
        print("python main.py --locale ar-sa --steps preprocess translate")
        print("python main.py --locale ja-jp --steps conversation tts")
        print()
        print("# Run with options")
        print("python main.py --locale ar-sa --sample-limit 10 --force")
        print("python main.py --locale ko-kr --output-dir ./custom_output")
        print()
        
        print("CONFIGURATION & VALIDATION:")
        print("python main.py --list-locales            # List all available locales")
        print("python main.py --list-languages          # List legacy language mappings")
        print("python main.py --validate-config ar-sa   # Validate locale configuration")
        print("python main.py --show-steps              # Show available pipeline steps")
        print()
        
        print("VOICE ID MANAGEMENT:")
        print("python main.py --validate-voices ar-sa   # Validate voices for specific locale")
        print("python main.py --validate-all-voices     # Validate all voice IDs across locales")
        print("python main.py --update-voice-configs    # Remove invalid voice IDs from configs")
        print("python main.py --ensure-minimum-voices   # Check minimum voice requirements")
        print("python main.py --suggest-voices ar-sa    # Get voice suggestions for locale")
        print()
        
        print("TRANSLATION CACHE:")
        print("python main.py --cache-translation       # Cache Chinese→English translations")
        print("python main.py --list-cached-translations # List cached translations")
        print("python main.py --cache-service google    # Use specific translation service")
        print("python main.py --cache-model qwen-mt-turbo # Use specific model (for qwen)")
        print("python main.py --cache-force-refresh     # Force refresh translation cache")
        print()
        
        print("BACKWARD COMPATIBILITY:")
        print("python main.py --language arabic         # Maps to ar-sa locale")
        print("python main.py --language malay          # Maps to ms-my locale")
        print()
        
        print("LOGGING & OUTPUT:")
        print("python main.py --locale ar-sa --verbose  # Enable verbose logging")
        print("python main.py --locale ar-sa --quiet    # Suppress output except errors")
        print()
        
        print("COMMON WORKFLOWS:")
        print()
        print("1. First-time setup:")
        print("   python main.py --list-locales")
        print("   python main.py --validate-config ar-sa")
        print("   python main.py --validate-voices ar-sa")
        print()
        print("2. Test run with small dataset:")
        print("   python main.py --locale ar-sa --sample-limit 5")
        print()
        print("3. Voice management workflow:")
        print("   python main.py --validate-all-voices")
        print("   python main.py --suggest-voices ar-sa")
        print("   python main.py --update-voice-configs")
        print()
        print("4. Production run:")
        print("   python main.py --locale ar-sa --force")
    
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
    
    def _voice_management_menu(self):
        """Show voice ID management menu."""
        print_step_header("Voice ID Management")
        
        print("Voice Management Options:")
        print("  1. Check voice health (current locale)")
        print("  2. Check voice health (all locales)")
        print("  3. Add new voice ID")
        print("  0. Back to configuration menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            self._voice_health_check(current_locale_only=True)
        elif choice == '2':
            self._voice_health_check(current_locale_only=False)
        elif choice == '3':
            self._add_voice_interactive()
        else:
            print_warning("Invalid choice.")
    
    def _voice_health_check(self, current_locale_only: bool = True):
        """Check voice health for current locale or all locales."""
        if current_locale_only and not self.current_locale:
            print_warning("Please select a locale first.")
            return
        
        print_step_header("Voice Health Check")
        
        try:
            if current_locale_only:
                print(f"Checking voice health for: {self.current_locale}")
                result = validate_voices(self.current_locale, self.config_dir)
            else:
                print("Checking voice health for all locales...")
                result = validate_all_voices(self.config_dir)
            
            if result == 0:
                print_info("\n✅ Voice health check completed successfully!")
            else:
                print_warning("\n⚠️ Some issues were found during voice health check.")
                
                # Offer follow-up options when issues are found
                print("\nFollow-up options:")
                print("  1. Remove invalid voice IDs automatically")
                print("  2. Get voice suggestions to add new voices")
                print("  0. Continue without action")
                
                follow_up = input("\nChoose follow-up action: ").strip()
                
                if follow_up == '1':
                    self._remove_invalid_voices()
                elif follow_up == '2':
                    self._suggest_voices_menu()
                # Option 0 or any other input just continues
                
        except Exception as e:
            print_error(f"Voice health check failed: {e}")
    
    def _suggest_voices_menu(self):
        """Show voice suggestions menu with selection options."""
        if not self.current_locale:
            print_warning("Please select a locale first.")
            return
        
        print_step_header(f"Voice Suggestions for {self.current_locale}")
        
        try:
            # Get API key
            api_key = os.getenv('ELEVENLABS_API_KEY')
            if not api_key:
                print_error("ELEVENLABS_API_KEY environment variable not found")
                print_info("Please set your ElevenLabs API key to get voice suggestions.")
                return
            
            # Initialize components
            validator = VoiceValidator(api_key, verbose=False)
            config_manager = LocaleConfigManager(f"{self.config_dir}/localizations")
            
            # Load locale configuration
            locale_config = config_manager.load_locale_config(self.current_locale)
            
            print_info("Searching for compatible voices...")
            
            # Get voice suggestions
            suggestions = validator.suggest_voices_for_locale(
                self.current_locale,
                locale_config.language_code,
                locale_config.voice_ids,
                needed_count=3  # Get 3 suggestions
            )
            
            if not suggestions:
                print_warning(f"No compatible voice suggestions found for {self.current_locale}")
                return
            
            print(f"\n🔍 Found {len(suggestions)} voice suggestions:")
            print("-" * 60)
            
            # Display suggestions with selection options
            for i, suggestion in enumerate(suggestions, 1):
                voice = suggestion.voice_info
                confidence_bar = "█" * int(suggestion.confidence * 10)
                print(f"\n{i}. {voice.name} (ID: {voice.voice_id})")
                print(f"   Language: {voice.language or 'Unknown'}")
                print(f"   Accent: {voice.accent or 'Standard'}")
                print(f"   Confidence: {confidence_bar} ({suggestion.confidence:.1f})")
                print(f"   Reason: {suggestion.reason}")
            
            # Allow user to select and add voices
            print(f"\n0. Go back without adding")
            
            choice = input(f"\nSelect voice to add (1-{len(suggestions)}): ").strip()
            
            if choice == '0':
                return
            
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(suggestions):
                    selected_suggestion = suggestions[choice_idx]
                    self._add_suggested_voice(selected_suggestion)
                else:
                    print_warning("Invalid selection.")
            except ValueError:
                print_warning("Please enter a valid number.")
                
        except Exception as e:
            print_error(f"Error getting voice suggestions: {e}")
    
    def _add_suggested_voice(self, suggestion):
        """Add a suggested voice to the current locale."""
        voice = suggestion.voice_info
        
        print_step_header(f"Add Voice: {voice.name}")
        print(f"Voice ID: {voice.voice_id}")
        print(f"Language: {voice.language or 'Unknown'}")
        print(f"Accent: {voice.accent or 'Standard'}")
        print(f"Confidence: {suggestion.confidence:.1f}")
        
        if confirm_action(f"Add this voice to {self.current_locale} configuration?", default_yes=True):
            try:
                config_manager = LocaleConfigManager(f"{self.config_dir}/localizations")
                config = config_manager.load_config(self.current_locale)
                
                # Check if voice ID already exists
                if voice.voice_id in config['voices']['ids']:
                    print_warning("Voice ID already exists in configuration.")
                    return
                
                # Add voice ID and name
                config['voices']['ids'].append(voice.voice_id)
                config['voices']['names'].append(voice.name)
                
                # Save updated configuration
                config_manager.save_config(self.current_locale, config)
                
                print_info(f"✅ Successfully added voice '{voice.name}' to {self.current_locale}")
                print_info(f"Total voices for {self.current_locale}: {len(config['voices']['ids'])}")
                
            except Exception as e:
                print_error(f"Error adding voice: {e}")
    
    def _add_voice_interactive(self):
        """Interactive voice addition with manual input."""
        if not self.current_locale:
            print_warning("Please select a locale first.")
            return
        
        print_step_header(f"Add Voice ID to {self.current_locale}")
        
        # Get API key
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            print_error("ELEVENLABS_API_KEY environment variable not found")
            print_info("Please set your ElevenLabs API key to validate voice IDs.")
            return
        
        try:
            config_manager = LocaleConfigManager(f"{self.config_dir}/localizations")
            config = config_manager.load_config(self.current_locale)
            
            # Show current voices
            current_voices = config['voices']['ids']
            print(f"\nCurrent voices for {self.current_locale}: {len(current_voices)}")
            for i, (voice_id, name) in enumerate(zip(config['voices']['ids'], config['voices']['names']), 1):
                print(f"  {i}. {name} ({voice_id})")
            
            print("\nOptions:")
            print("  1. Enter voice ID manually")
            print("  2. Get voice suggestions")
            print("  0. Cancel")
            
            option = input("\nChoose option: ").strip()
            
            if option == '0':
                return
            elif option == '1':
                self._add_voice_manual()
            elif option == '2':
                self._suggest_voices_menu()
            else:
                print_warning("Invalid option.")
                
        except Exception as e:
            print_error(f"Error in voice addition: {e}")
    
    def _add_voice_manual(self):
        """Add voice ID manually with validation."""
        voice_id = input("\nEnter ElevenLabs Voice ID: ").strip()
        
        if not voice_id:
            print_warning("Voice ID cannot be empty.")
            return
        
        try:
            # Validate voice ID
            api_key = os.getenv('ELEVENLABS_API_KEY')
            validator = VoiceValidator(api_key, verbose=False)
            
            print_info("Validating voice ID...")
            is_valid, voice_info = validator.validate_single_voice_sync(voice_id)
            
            if not is_valid:
                print_error(f"Voice ID '{voice_id}' is not valid or not accessible.")
                return
                
            print_info(f"✅ Voice ID is valid: {voice_info.name}")
            
            # Get voice name (use API name or let user customize)
            default_name = voice_info.name
            voice_name = input(f"Enter voice name (default: {default_name}): ").strip()
            if not voice_name:
                voice_name = default_name
            
            # Confirm addition
            print(f"\nVoice to add:")
            print(f"  ID: {voice_id}")
            print(f"  Name: {voice_name}")
            if voice_info.language:
                print(f"  Language: {voice_info.language}")
            if voice_info.accent:
                print(f"  Accent: {voice_info.accent}")
            
            if confirm_action("Add this voice to configuration?", default_yes=True):
                config_manager = LocaleConfigManager(f"{self.config_dir}/localizations")
                config = config_manager.load_config(self.current_locale)
                
                # Check if voice ID already exists
                if voice_id in config['voices']['ids']:
                    print_warning("Voice ID already exists in configuration.")
                    return
                
                # Add voice ID and name
                config['voices']['ids'].append(voice_id)
                config['voices']['names'].append(voice_name)
                
                # Save updated configuration
                config_manager.save_config(self.current_locale, config)
                
                print_info(f"✅ Successfully added voice '{voice_name}' to {self.current_locale}")
                print_info(f"Total voices for {self.current_locale}: {len(config['voices']['ids'])}")
                
        except Exception as e:
            print_error(f"Error validating or adding voice: {e}")
    
    def _remove_invalid_voices(self):
        """Remove invalid voice IDs from configurations."""
        print_step_header("Remove Invalid Voice IDs")
        
        print("Scanning for invalid voice IDs...")
        
        try:
            result = validate_all_voices(self.config_dir, update_configs=True)
            
            if result == 0:
                print_info("\n✅ All voice IDs are valid - no cleanup needed!")
            else:
                print_info("\n🔧 Invalid voice IDs have been removed from configurations.")
                
        except Exception as e:
            print_error(f"Error removing invalid voices: {e}")
    
    def _check_minimum_requirements(self):
        """Check minimum voice requirements for all locales."""
        print_step_header("Minimum Voice Requirements Check")
        
        try:
            result = ensure_minimum_voices(self.config_dir)
            
            if result == 0:
                print_info("\n🎉 All locales meet minimum voice requirements!")
            else:
                print_warning("\n⚠️ Some locales need additional voices for reliability.")
                print("\nTip: Use 'Get voice suggestions' to find compatible voices for problematic locales.")
                
        except Exception as e:
            print_error(f"Error checking minimum requirements: {e}")

    def _show_about(self):
        """Show about information."""
        print_step_header("About Voice Scam Dataset Generator")
        
        print("This tool generates multilingual voice scam detection datasets by creating")
        print("synthetic phone conversations for training anti-scam ML models.")
        print()
        print("Features:")
        print("• Multi-language support (Arabic, Malay, and extensible)")
        print("• Flexible LLM backend with LangChain integration")
        print("• Async/concurrent conversation generation for 5-10x speedup")
        print("• High-quality voice synthesis with ElevenLabs TTS")
        print("• Configurable pipeline with locale-specific settings")
        print("• Audio post-processing for phone call quality")
        print()
        print("LLM Capabilities:")
        print("• Multiple provider support (OpenAI, Anthropic, Gemini, local)")
        print("• Native structured output with automatic JSON fallback")
        print("• Concurrent API calls with rate limiting")
        print("• Configurable models per locale")
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
    
    def _voice_quality_menu(self):
        """Show voice quality and v3 features management menu."""
        print_step_header("Voice Quality & Model Settings")
        
        # Show current settings first
        self.voice_quality_manager.show_current_settings()
        print("\n" + "=" * 40)
        
        print("Voice Configuration Options:")
        print("  1. Change TTS Model")
        print("  2. Configure V3 Features (audio tags, emotional context)")
        print("  3. Configure Voice Settings (stability, similarity, style)")
        print("  4. Change Audio Format")
        print("  5. Show Current Settings")
        print("  6. Reset All Settings to Defaults")
        print("  0. Back to configuration menu")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            self._change_tts_model()
        elif choice == '2':
            self._configure_v3_features()
        elif choice == '3':
            self._configure_voice_settings()
        elif choice == '4':
            self._change_audio_format()
        elif choice == '5':
            self.voice_quality_manager.show_current_settings()
        elif choice == '6':
            if confirm_action("Reset all voice settings to defaults?"):
                if self.voice_quality_manager.reset_to_defaults():
                    print_info("All voice settings have been reset to defaults")
        else:
            print_warning("Invalid choice.")
    
    def _change_tts_model(self):
        """Change the TTS model."""
        print_step_header("Change TTS Model")
        
        models = [
            ("eleven_turbo_v2_5", "Turbo model for faster generation (Balanced)"),
            ("eleven_flash_v2_5", "Low latency model, cost optimized (Best for testing)"),
            ("eleven_multilingual_v2", "Standard multilingual model (high quality)"),
            ("eleven_v3", "V3 model with enhanced expressiveness (In alpha, may not work)"),
        ]
        
        print("Available models:")
        for i, (model_id, description) in enumerate(models, 1):
            print(f"  {i}. {model_id}")
            print(f"     {description}")
        
        print("  0. Cancel")
        
        choice = input("\nSelect model (1-4): ").strip()
        
        if choice == '0':
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                model_id, _ = models[idx]
                if self.voice_quality_manager.set_model(model_id):
                    print_info(f"Model changed to: {model_id}")
            else:
                print_warning("Invalid selection")
        except ValueError:
            print_warning("Please enter a valid number")
    
    def _configure_v3_features(self):
        """Configure V3-specific features."""
        print_step_header("Configure V3 Features")
        
        try:
            config = self.voice_quality_manager._load_common_config()
            current_model = config["voice_generation"]["model_id"]
            
            if 'v3' not in current_model.lower():
                print_warning(f"Current model ({current_model}) is not a v3 model.")
                print_info("V3 features will only be active when using a v3 model.")
                print("\nWould you like to switch to a v3 model? (y/n): ", end="")
                if input().strip().lower() in ['y', 'yes']:
                    self.voice_quality_manager.set_model("eleven_multilingual_v3")
                    print_info("Switched to eleven_multilingual_v3")
                else:
                    print_info("You can still configure v3 features - they will activate when you switch to a v3 model")
            
            v3_features = config["voice_generation"]["v3_features"]
            
            print("\nCurrent V3 Feature Settings:")
            print(f"  Audio Tags: {'Enabled' if v3_features['use_audio_tags'] else 'Disabled'}")
            print(f"  Emotional Context: {'Enabled' if v3_features['emotional_context'] else 'Disabled'}")
            print(f"  Conversation Context: {'Enabled' if v3_features['conversation_context'] else 'Disabled'}")
            
            print("\nOptions:")
            print("  1. Enable all V3 features")
            print("  2. Disable all V3 features")
            print("  3. Configure individually")
            print("  0. Cancel")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '0':
                return
            elif choice == '1':
                v3_features["use_audio_tags"] = True
                v3_features["emotional_context"] = True
                v3_features["conversation_context"] = True
                self.voice_quality_manager._save_common_config(config)
                print_info("All V3 features enabled")
            elif choice == '2':
                v3_features["use_audio_tags"] = False
                v3_features["emotional_context"] = False
                v3_features["conversation_context"] = False
                self.voice_quality_manager._save_common_config(config)
                print_info("All V3 features disabled")
            elif choice == '3':
                # Individual configuration
                audio_tags = input("Enable audio tags? (y/n, current: {}): ".format(
                    'yes' if v3_features['use_audio_tags'] else 'no'
                )).strip().lower()
                if audio_tags in ['y', 'yes']:
                    v3_features["use_audio_tags"] = True
                elif audio_tags in ['n', 'no']:
                    v3_features["use_audio_tags"] = False
                
                emotional = input("Enable emotional context? (y/n, current: {}): ".format(
                    'yes' if v3_features['emotional_context'] else 'no'
                )).strip().lower()
                if emotional in ['y', 'yes']:
                    v3_features["emotional_context"] = True
                elif emotional in ['n', 'no']:
                    v3_features["emotional_context"] = False
                
                conversation = input("Enable conversation context? (y/n, current: {}): ".format(
                    'yes' if v3_features['conversation_context'] else 'no'
                )).strip().lower()
                if conversation in ['y', 'yes']:
                    v3_features["conversation_context"] = True
                elif conversation in ['n', 'no']:
                    v3_features["conversation_context"] = False
                
                self.voice_quality_manager._save_common_config(config)
                print_info("V3 features updated")
                
        except Exception as e:
            print_error(f"Error configuring V3 features: {e}")
    
    def _change_audio_format(self):
        """Change the audio output format."""
        print_step_header("Change Audio Format")
        
        formats = [
            ("mp3_44100_128", "MP3 44.1kHz 128kbps (default, recommended)"),
            ("mp3_22050_32", "MP3 22kHz 32kbps (smaller files, lower quality)"),
            ("mp3_44100_64", "MP3 44.1kHz 64kbps (balanced)"),
            ("mp3_44100_192", "MP3 44.1kHz 192kbps (higher quality, larger files)")
        ]
        
        print("Available formats:")
        print("⚠️ Note: Some formats may cause API errors depending on your ElevenLabs plan")
        print()
        for i, (format_id, description) in enumerate(formats, 1):
            print(f"  {i}. {format_id}")
            print(f"     {description}")
        
        print("  0. Cancel")
        
        choice = input("\nSelect format (1-4): ").strip()
        
        if choice == '0':
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(formats):
                format_id, _ = formats[idx]
                if self.voice_quality_manager.set_audio_format(format_id):
                    print_info(f"Audio format changed to: {format_id}")
            else:
                print_warning("Invalid selection")
        except ValueError:
            print_warning("Please enter a valid number")
    
    def _configure_voice_settings(self):
        """Configure individual voice settings."""
        print_step_header("Configure Voice Settings")
        
        print("Current voice settings will be updated.")
        print("Press Enter to keep current value, or enter new value:")
        
        try:
            # Stability setting
            stability_input = input("Voice Stability (0.0-1.0, current: see above): ").strip()
            stability = float(stability_input) if stability_input else None
            
            # Similarity boost setting
            similarity_input = input("Similarity Boost (0.0-1.0, current: see above): ").strip()
            similarity_boost = float(similarity_input) if similarity_input else None
            
            # Style setting (v3 only)
            style_input = input("Style (0.0-1.0, V3 only, current: see above): ").strip()
            style = float(style_input) if style_input else None
            
            # Speaker boost
            speaker_boost_input = input("Speaker Boost (true/false, current: see above): ").strip().lower()
            speaker_boost = None
            if speaker_boost_input in ['true', 't', 'yes', 'y', '1']:
                speaker_boost = True
            elif speaker_boost_input in ['false', 'f', 'no', 'n', '0']:
                speaker_boost = False
            
            # Apply settings
            self.voice_quality_manager.set_voice_settings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                speaker_boost=speaker_boost
            )
            
        except ValueError:
            print_error("Invalid input. Values must be numbers between 0.0 and 1.0.")
        except Exception as e:
            print_error(f"Error configuring voice settings: {e}")