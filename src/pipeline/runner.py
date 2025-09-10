"""
Pipeline runner for orchestrating the voice scam dataset generation process.
"""

import logging
import time
import asyncio
import warnings
from typing import List, Optional, Dict, Callable
from pathlib import Path

from src.config.config_loader import Config
from src.cli.utils import (
    print_step_header, print_step_complete,
    ensure_directory, ProgressTracker
)

# Suppress the non-fatal "Event loop is closed" error from asyncio
warnings.filterwarnings("ignore", message=".*Event loop is closed.*")
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# Import modules (to be implemented)
from src.conversation.scam_generator import ScamGenerator
from src.conversation.legit_generator import LegitGenerator
from src.tts.voice_synthesizer import VoiceSynthesizer
from src.postprocessing.json_formatter import JsonFormatter
from src.postprocessing.audio_packager import AudioPackager
from src.utils.logging_utils import format_completion_message


logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Orchestrates the execution of the voice scam dataset generation pipeline.
    """
    
    # Define pipeline steps and their execution order
    PIPELINE_STEPS = {
        'conversation': 'run_conversation_generation',
        'legit': 'run_legit_generation',
        'tts': 'run_tts',
        'postprocess': 'run_postprocessing'
    }
    
    def __init__(self, config: Config, steps: Optional[List[str]] = None, generation_mode: str = "both"):
        """
        Initialize the pipeline runner.
        
        Args:
            config: Configuration object
            steps: List of steps to run (None for all)
            generation_mode: Generation mode ("scam", "legit", or "both")
        """
        self.config = config
        self.generation_mode = generation_mode
        self.steps = self._validate_steps(steps)
        
        # Create output directories
        self._create_output_directories()
        
        # Initialize progress tracker
        self.progress = ProgressTracker(len(self.steps))
        
        # Initialize token trackers for conversation steps
        self.scam_token_tracker = None
        self.legit_token_tracker = None
    
    def _validate_steps(self, steps: Optional[List[str]]) -> List[str]:
        """
        Validate and normalize the list of steps to run.
        
        Args:
            steps: User-provided steps or None
            
        Returns:
            Validated list of steps
        """
        if not steps or 'all' in steps:
            steps = list(self.PIPELINE_STEPS.keys())
        else:
            # Validate each step
            invalid_steps = [s for s in steps if s not in self.PIPELINE_STEPS]
            if invalid_steps:
                raise ValueError(f"Invalid steps: {', '.join(invalid_steps)}")
        
        # Apply generation mode filtering
        filtered_steps = []
        for step in steps:
            if self.generation_mode == "scam":
                # For scam mode, skip legit generation
                if step == "legit":
                    continue
                filtered_steps.append(step)
            elif self.generation_mode == "legit":
                # For legit mode, replace "conversation" with "legit"
                if step == "conversation":
                    if "legit" not in filtered_steps:
                        filtered_steps.append("legit")
                elif step != "legit":
                    filtered_steps.append(step)
                else:
                    filtered_steps.append(step)
            else:
                # Both mode - include all steps
                filtered_steps.append(step)
        
        # Return steps in pipeline order
        return [s for s in self.PIPELINE_STEPS.keys() if s in filtered_steps]
    
    def _create_output_directories(self):
        """Create all necessary output directories."""
        directories = [
            self.config.output_dir / "conversations",
            self.config.output_dir / "audio" / "scam",
            self.config.output_dir / "audio" / "legit",
            self.config.output_dir / "final"
        ]
        
        for directory in directories:
            ensure_directory(directory)
    
    def run(self):
        """Run the pipeline with configured steps."""
        logger.info(f"Starting pipeline for {self.config.language_name}")
        logger.info(f"Steps to run: {', '.join(self.steps)}")
        
        # Check if token tracking is enabled for conversation steps
        conversation_steps = {'conversation', 'legit'}
        has_conversation_steps = bool(conversation_steps.intersection(set(self.steps)))
        
        track_llm_tokens = getattr(self.config, 'llm_track_tokens', False) and has_conversation_steps
        track_any_tokens = track_llm_tokens
        
        for step in self.steps:
            method_name = self.PIPELINE_STEPS[step]
            method = getattr(self, method_name)
            
            print_step_header(step)
            start_time = time.time()
            
            try:
                # Conversation, legit generation, and TTS are async methods
                if step in ['conversation', 'legit', 'tts']:
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
        if track_any_tokens and (self.scam_token_tracker or self.legit_token_tracker):
            self._print_combined_token_summary()
    
    async def run_conversation_generation(self):
        """Run conversation generation: create multi-turn scam dialogues."""
        # Log generation mode
        if hasattr(self.config, 'generation_enable_character_profiles') and self.config.generation_enable_character_profiles:
            logger.debug("Generating scam conversations with character profiles enabled")
        else:
            logger.debug("Generating scam conversations from seed file")
        
        generator = ScamGenerator(self.config)
        await generator.generate_conversations()
        
        # Capture token tracker if available
        if hasattr(generator, 'token_tracker') and generator.token_tracker:
            self.scam_token_tracker = generator.token_tracker
    
    
    async def run_legit_generation(self):
        """Run legitimate conversation generation."""
        logger.debug("Generating legitimate conversations")
        
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
        
        # Generate scam audio if file exists
        if self.config.voice_input_file_scam.exists():
            if self.config.verbose:
                print("Generating scam conversation audio...")
            await synthesizer.generate_audio(
                input_file=self.config.voice_input_file_scam,
                output_dir=self.config.voice_output_dir_scam,
                is_scam=True
            )
        elif self.generation_mode in ["scam", "both"]:
            logger.warning(f"Scam conversation file not found: {self.config.voice_input_file_scam}")
        
        # Generate legitimate audio if file exists
        if self.config.voice_input_file_legit.exists():
            if self.config.verbose:
                print("Generating legitimate conversation audio...")
            await synthesizer.generate_audio(
                input_file=self.config.voice_input_file_legit,
                output_dir=self.config.voice_output_dir_legit,
                is_scam=False
            )
        elif self.generation_mode in ["legit", "both"]:
            logger.warning(f"Legitimate conversation file not found: {self.config.voice_input_file_legit}")
    
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
        from src.llm_core.token_counter import TokenUsageTracker
        
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
        
        # Print LLM summary if available
        if llm_tracker.records:
            print("\n--- LLM Conversation Generation ---")
            llm_tracker.print_summary()
            llm_tracker.print_cost_estimate()
        
        # Calculate and print total costs
        if llm_tracker.records:
            print("\n" + "="*80)
            print("TOTAL COSTS")
            print("="*80)
            
            total_cost = 0.0
            if llm_tracker.records:
                llm_cost = llm_tracker.estimate_cost()
                if llm_cost and 'total_cost' in llm_cost:
                    total_cost = llm_cost['total_cost']
                    print(f"LLM Generation: ${llm_cost['total_cost']:.4f}")
            
            print(f"\nGrand Total: ${total_cost:.4f}")
            print("="*80)