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
from preprocessing.tag_extractor import TagExtractor
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
        'preprocess': 'run_preprocessing',
        'translate': 'run_translation',
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
        
        for step in self.steps:
            method_name = self.PIPELINE_STEPS[step]
            method = getattr(self, method_name)
            
            print_step_header(step)
            start_time = time.time()
            
            try:
                # Conversation, legit generation, translation, and TTS are async methods
                if step in ['conversation', 'legit', 'tts', 'translate', 'translate_final']:
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
    
    def run_preprocessing(self):
        """Run preprocessing step: extract tags and create mappings."""
        if self.config.verbose:
            logger.info("Running preprocessing")
        
        extractor = TagExtractor(self.config)
        extractor.extract_tags()
    
    async def run_translation(self):
        """Run initial translation: Chinese to English."""
        # Check if translation cache is enabled
        use_cache = getattr(self.config, 'use_translation_cache', False)
        cache_service = getattr(self.config, 'translation_cache_service', 'google')
        force_refresh = getattr(self.config, 'force_translation_refresh', False)
        
        
        if use_cache and not force_refresh:
            # Try to use cached translation
            from translation.cache_translator import CacheTranslator
            
            logger.info(f"Checking for cached Chinese to English translation from {cache_service}")
            
            # Check if cache exists and is valid
            # For Qwen, get the model from config
            cache_model = None
            if cache_service == "qwen":
                cache_model = getattr(self.config, 'qwen_model', 'qwen-mt-turbo')
            
            translator = CacheTranslator(self.config, cache_service, cache_model)
            cached_path = translator.get_cached_translation_path()
            
            if cached_path:
                # Update config paths to point to cached file instead of copying/linking
                self.config.translation_output_path = cached_path
                self.config.multi_turn_input_path = cached_path
                
                if cache_model:
                    logger.info(f"Using cached translation from {cache_service} (model: {cache_model})")
                else:
                    logger.info(f"Using cached translation from {cache_service}")
                logger.info(f"Cache file: {cached_path}")
                # Skip actual translation - config now points to cached file
                return
            else:
                logger.warning(f"No valid cache found for {cache_service}, running fresh translation")
        
        # Build service info string
        service_info = f"service: {self.config.translation_service}"
        if self.config.translation_service == "qwen":
            service_info += f" (model: {getattr(self.config, 'qwen_model', 'qwen-mt-turbo')})"
        
        logger.info(f"Running Chinese to English translation using {service_info}")
        
        translator = TranslatorFactory.create(
            self.config.translation_service,
            self.config
        )
        await translator.translate_file(
            input_path=self.config.translation_input_path,
            output_path=self.config.translation_output_path,
            from_code=self.config.translation_from_code,
            to_code=self.config.translation_intermediate_code,
            max_lines=self.config.max_lines
        )
    
    async def run_conversation_generation(self):
        """Run conversation generation: create multi-turn scam dialogues."""
        logger.info("Generating scam conversations")
        
        generator = ScamGenerator(self.config)
        await generator.generate_conversations()
    
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
    
    async def run_legit_generation(self):
        """Run legitimate conversation generation."""
        logger.info("Generating legitimate conversations")
        
        generator = LegitGenerator(self.config)
        await generator.generate_conversations()
    
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