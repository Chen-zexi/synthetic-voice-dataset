"""
Pipeline runner for orchestrating the voice scam dataset generation process.
"""

import logging
import time
import asyncio
from typing import List, Optional, Dict, Callable
from pathlib import Path

from config.config_loader import Config
from cli.utils import (
    print_step_header, print_step_complete,
    ensure_directory, ProgressTracker
)

# Import modules (to be implemented)
from preprocessing.tag_extractor import TagExtractor
from translation.translator import TranslatorFactory
from conversation.scam_generator import ScamGenerator
from conversation.legit_generator import LegitGenerator
from tts.voice_synthesizer import VoiceSynthesizer
from postprocessing.json_formatter import JsonFormatter
from postprocessing.audio_packager import AudioPackager


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
                # Conversation, legit generation, and TTS are async methods
                if step in ['conversation', 'legit', 'tts']:
                    asyncio.run(method())
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
        logger.info("Running preprocessing")
        
        extractor = TagExtractor(self.config)
        extractor.extract_tags()
    
    def run_translation(self):
        """Run initial translation: Chinese to English."""
        logger.info("Running Chinese to English translation")
        
        translator = TranslatorFactory.create(
            self.config.translation_service,
            self.config
        )
        translator.translate_file(
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
    
    def run_final_translation(self):
        """Run final translation: English to target language."""
        logger.info(f"Translating conversations to {self.config.language_name}")
        
        translator = TranslatorFactory.create(
            self.config.translation_service,
            self.config
        )
        translator.translate_conversations(
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
        logger.info("Converting conversations to audio")
        
        synthesizer = VoiceSynthesizer(self.config)
        
        # Generate scam audio
        print("Generating scam conversation audio...")
        await synthesizer.generate_audio(
            input_file=self.config.voice_input_file_scam,
            output_dir=self.config.voice_output_dir_scam,
            is_scam=True
        )
        
        # Generate legitimate audio
        print("Generating legitimate conversation audio...")
        await synthesizer.generate_audio(
            input_file=self.config.voice_input_file_legit,
            output_dir=self.config.voice_output_dir_legit,
            is_scam=False
        )
    
    def run_postprocessing(self):
        """Run postprocessing: format JSON and package audio."""
        logger.info("Running postprocessing")
        
        # Format JSON files
        formatter = JsonFormatter(self.config)
        formatter.format_all()
        
        # Package audio files
        packager = AudioPackager(self.config)
        packager.package_all()