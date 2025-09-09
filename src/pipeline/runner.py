"""
Pipeline runner for orchestrating the voice scam dataset generation process.
"""

import logging
import time
import asyncio
import warnings
from typing import List, Optional, Dict, Callable
from pathlib import Path

from config.config_loader import Config
from cli.utils import (
    print_step_header, print_step_complete,
    ensure_directory, ProgressTracker
)

# Suppress the non-fatal "Event loop is closed" error from asyncio
warnings.filterwarnings("ignore", message=".*Event loop is closed.*")
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# Import modules (to be implemented)
from translation.translator import TranslatorFactory
from conversation.scam_generator import ScamGenerator
from conversation.legit_generator import LegitGenerator
from tts.voice_synthesizer import VoiceSynthesizer
from postprocessing.json_formatter import JsonFormatter
from postprocessing.audio_packager import AudioPackager
from utils.logging_utils import format_completion_message


logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Orchestrates the execution of the voice scam dataset generation pipeline.
    """
    
    # Define pipeline steps and their execution order
    PIPELINE_STEPS = {
        'conversation': 'run_conversation_generation',
        'translate_final': 'run_final_translation',
        'legit': 'run_legit_generation',
        'tts': 'run_tts',
        'postprocess': 'run_postprocessing'
    }
    
    def __init__(self, config: Config, steps: Optional[List[str]] = None):
        """
        Initialize the pipeline runner.
        
        Args:
            config: Configuration object
            steps: List of steps to run (None for all)
        """
        self.config = config
        self.steps = self._validate_steps(steps)
        
        # Create output directories
        self._create_output_directories()
        
        # Initialize progress tracker
        self.progress = ProgressTracker(len(self.steps))
        
        # Initialize token trackers for conversation steps
        self.scam_token_tracker = None
        self.legit_token_tracker = None
        
        # Initialize token trackers for translation steps
        self.translation_token_trackers = []
    
    def _validate_steps(self, steps: Optional[List[str]]) -> List[str]:
        """
        Validate and normalize the list of steps to run.
        
        Args:
            steps: User-provided steps or None
            
        Returns:
            Validated list of steps
        """
        if not steps or 'all' in steps:
            return list(self.PIPELINE_STEPS.keys())
        
        # Validate each step
        invalid_steps = [s for s in steps if s not in self.PIPELINE_STEPS]
        if invalid_steps:
            raise ValueError(f"Invalid steps: {', '.join(invalid_steps)}")
        
        # Return steps in pipeline order
        return [s for s in self.PIPELINE_STEPS.keys() if s in steps]
    
    def _create_output_directories(self):
        """Create all necessary output directories."""
        directories = [
            self.config.output_dir / "intermediate" / "preprocessed",
            self.config.output_dir / "intermediate" / "translated",
            self.config.output_dir / "intermediate" / "conversations",
            self.config.output_dir / "audio" / "scam",
            self.config.output_dir / "audio" / "legit",
            self.config.output_dir / "final" / "json",
            self.config.output_dir / "final" / "archives"
        ]
        
        for directory in directories:
            ensure_directory(directory)
    
    def run(self):
        """Run the pipeline with configured steps."""
        logger.info(f"Starting pipeline for {self.config.language_name}")
        logger.info(f"Steps to run: {', '.join(self.steps)}")
        
        # Check if token tracking is enabled for conversation or translation steps
        conversation_steps = {'conversation', 'legit'}
        translation_steps = {'translate_final'}
        has_conversation_steps = bool(conversation_steps.intersection(set(self.steps)))
        has_translation_steps = bool(translation_steps.intersection(set(self.steps)))
        
        track_llm_tokens = getattr(self.config, 'llm_track_tokens', False) and has_conversation_steps
        track_translation_tokens = getattr(self.config, 'translation_track_tokens', False) and has_translation_steps
        track_any_tokens = track_llm_tokens or track_translation_tokens
        
        for step in self.steps:
            method_name = self.PIPELINE_STEPS[step]
            method = getattr(self, method_name)
            
            print_step_header(step)
            start_time = time.time()
            
            try:
                # Conversation, legit generation, translation, and TTS are async methods
                if step in ['conversation', 'legit', 'tts', 'translate_final']:
                    # Use asyncio.run with debug=False to suppress warnings
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(method())
                    finally:
                        # Allow time for cleanup before closing
                        loop.run_until_complete(asyncio.sleep(0.5))
                        loop.close()
                else:
                    method()
                duration = time.time() - start_time
                print_step_complete(step, duration)
                self.progress.update(step)
            except Exception as e:
                logger.error(f"Step '{step}' failed: {e}")
                raise
        
        self.progress.complete()
        
        # Print token usage summary if any token tracking was enabled
        if track_any_tokens and (self.scam_token_tracker or self.legit_token_tracker or self.translation_token_trackers):
            self._print_combined_token_summary()
    
    async def run_conversation_generation(self):
        """Run conversation generation: create multi-turn scam dialogues."""
        # Determine generation mode
        generation_mode = getattr(self.config, 'generation_source_type', 'legacy_text')
        
        if generation_mode == 'seeds':
            logger.info("Generating scam conversations using scenario-based system with character profiles")
            if hasattr(self.config, 'generation_enable_character_profiles') and self.config.generation_enable_character_profiles:
                logger.info(f"Character profiles enabled from: {getattr(self.config, 'generation_profiles_file', 'default profiles')}")
            else:
                logger.info("Using default character profiles")
            
            seeds_file = getattr(self.config, 'generation_seeds_file', 'scam_samples.json')
            logger.info(f"Loading scam seeds from: {seeds_file}")
            
            scenarios_per_seed = getattr(self.config, 'generation_scenarios_per_seed', 1)
            min_quality = getattr(self.config, 'generation_min_seed_quality', 70)
            logger.info(f"Generation settings: {scenarios_per_seed} scenarios per seed, minimum quality {min_quality}")
        else:
            logger.info("Generating scam conversations using legacy line-by-line system")
        
        generator = ScamGenerator(self.config)
        await generator.generate_conversations()
        
        # Capture token tracker if available
        if hasattr(generator, 'token_tracker') and generator.token_tracker:
            self.scam_token_tracker = generator.token_tracker
    
    async def run_final_translation(self):
        """Run final translation: English to target language."""
        # Build service info string
        service_info = f"service: {self.config.translation_service}"
        if self.config.translation_service == "qwen":
            service_info += f" (model: {getattr(self.config, 'qwen_model', 'qwen-mt-turbo')})"
        
        logger.info(f"Translating conversations to {self.config.language_name} using {service_info}")
        
        translator = TranslatorFactory.create(
            self.config.translation_service,
            self.config
        )
        await translator.translate_conversations(
            input_path=self.config.multi_turn_translated_input_path,
            output_path=self.config.multi_turn_translated_output_path,
            from_code=self.config.multi_turn_from_code,
            to_code=self.config.multi_turn_to_code
        )
        
        # Capture token tracker if available
        if hasattr(translator, 'token_tracker') and translator.token_tracker:
            self.translation_token_trackers.append((
                f'English to {self.config.language_name} Translation',
                translator.token_tracker
            ))
    
    async def run_legit_generation(self):
        """Run legitimate conversation generation."""
        logger.info("Generating legitimate conversations")
        
        generator = LegitGenerator(self.config)
        await generator.generate_conversations()
        
        # Capture token tracker if available
        if hasattr(generator, 'token_tracker') and generator.token_tracker:
            self.legit_token_tracker = generator.token_tracker
    
    async def run_tts(self):
        """Run text-to-speech conversion."""
        if self.config.verbose:
            logger.info("Converting conversations to audio")
        
        synthesizer = VoiceSynthesizer(self.config)
        
        # Generate scam audio
        if self.config.verbose:
            print("Generating scam conversation audio...")
        await synthesizer.generate_audio(
            input_file=self.config.voice_input_file_scam,
            output_dir=self.config.voice_output_dir_scam,
            is_scam=True
        )
        
        # Generate legitimate audio
        if self.config.verbose:
            print("Generating legitimate conversation audio...")
        await synthesizer.generate_audio(
            input_file=self.config.voice_input_file_legit,
            output_dir=self.config.voice_output_dir_legit,
            is_scam=False
        )
    
    def run_postprocessing(self):
        """Run postprocessing: format JSON and package audio."""
        if self.config.verbose:
            logger.info("Running postprocessing")
        
        # Format JSON files
        formatter = JsonFormatter(self.config)
        formatter.format_all()
        
        # Package audio files
        packager = AudioPackager(self.config)
        packager.package_all()
    
    def _print_combined_token_summary(self):
        """Print combined token usage summary from all generators and translators."""
        from llm_core.token_counter import TokenUsageTracker
        import json
        from pathlib import Path
        
        print("\n" + "="*80)
        print("TOKEN USAGE AND COST SUMMARY")
        print("="*80)
        
        # Track LLM conversation costs
        llm_tracker = TokenUsageTracker(verbose=False)
        
        # Add records from scam generator
        if self.scam_token_tracker:
            for record in self.scam_token_tracker.records:
                llm_tracker.records.append(record)
            print(f"\nScam Conversations: {len(self.scam_token_tracker.records)} API calls")
        
        # Add records from legit generator
        if self.legit_token_tracker:
            for record in self.legit_token_tracker.records:
                llm_tracker.records.append(record)
            print(f"Legitimate Conversations: {len(self.legit_token_tracker.records)} API calls")
        
        # Track translation costs separately
        translation_tracker = TokenUsageTracker(verbose=False)
        translation_model = None
        
        for step_name, tracker in self.translation_token_trackers:
            print(f"{step_name}: {len(tracker.records)} API calls")
            for record in tracker.records:
                translation_tracker.records.append(record)
                if not translation_model and record.model:
                    translation_model = record.model
        
        # Print LLM summary if available
        if llm_tracker.records:
            print("\n--- LLM Conversation Generation ---")
            llm_tracker.print_summary()
            llm_tracker.print_cost_estimate()
        
        # Print translation summary if available
        if translation_tracker.records:
            print("\n--- Translation Services ---")
            
            # Load translation pricing
            try:
                config_path = Path(__file__).parent.parent / "translation" / "model_config.json"
                with open(config_path, 'r') as f:
                    model_config = json.load(f)
                
                # Get pricing for translation model
                pricing = {}
                if translation_model:
                    for model_info in model_config['models']['qwen']:
                        if model_info['id'] == translation_model:
                            # Convert from per 1M to per 1K for compatibility
                            pricing[translation_model] = {
                                'input': model_info['pricing']['input'] / 1000,
                                'output': model_info['pricing']['output'] / 1000
                            }
                            break
                
                translation_tracker.print_summary()
                translation_tracker.print_cost_estimate(pricing)
            except Exception as e:
                logger.warning(f"Could not load translation pricing: {e}")
                translation_tracker.print_summary()
        
        # Calculate and print total costs
        if llm_tracker.records or translation_tracker.records:
            print("\n" + "="*80)
            print("TOTAL COMBINED COSTS")
            print("="*80)
            
            total_cost = 0.0
            if llm_tracker.records:
                llm_cost = llm_tracker.estimate_cost()
                if llm_cost and 'total_cost' in llm_cost:
                    total_cost += llm_cost['total_cost']
                    print(f"LLM Generation: ${llm_cost['total_cost']:.4f}")
            
            if translation_tracker.records and pricing:
                trans_cost = translation_tracker.estimate_cost(pricing)
                if trans_cost and 'total_cost' in trans_cost:
                    total_cost += trans_cost['total_cost']
                    print(f"Translation: ${trans_cost['total_cost']:.4f}")
            
            print(f"\nGrand Total: ${total_cost:.4f}")
            print("="*80)