"""
Standalone Chinese-to-English translation with caching support.
This module handles translation of the base Chinese scam lines to English
and caches the results for reuse across different locale pipelines.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from config.config_loader import Config
from preprocessing.tag_extractor import TagExtractor
from translation.translator import TranslatorFactory
from utils.logging_utils import ConditionalLogger


logger = logging.getLogger(__name__)


class CacheTranslator:
    """
    Handles standalone Chinese-to-English translation with caching.
    """
    
    def __init__(self, config: Config, service: str = "google", model: Optional[str] = None):
        """
        Initialize the cache translator.
        
        Args:
            config: Configuration object
            service: Translation service to use (google, qwen, argos)
            model: Optional model name for services that support it (e.g., qwen)
        """
        self.config = config
        self.service = service
        self.model = model
        self.clogger = ConditionalLogger(__name__, config.verbose)
        
        # Set up cache paths with model-specific directories for Qwen
        self.cache_base_dir = Path("data/translation_cache")
        if service == "qwen" and model:
            # For Qwen, create model-specific subdirectory
            self.service_cache_dir = self.cache_base_dir / service / model
        else:
            # For other services, use service directory directly
            self.service_cache_dir = self.cache_base_dir / service
        
        # Get output filename from common.json configuration
        english_output = getattr(config, 'translation_english_output', 'scamGen_combined_first_20k_en.txt')
        self.cached_translation_file = self.service_cache_dir / english_output
        self.metadata_file = self.service_cache_dir / "metadata.json"
        
        # Input paths from configuration
        preprocessing_input_file = getattr(config, 'preprocessing_input_file', 'scamGen_combined_first_20k.txt')
        self.chinese_input = Path("data/input") / preprocessing_input_file
        self.preprocessed_output = Path("data/input") / preprocessing_input_file.replace('.txt', '_mapped.txt')
        self.preprocessing_map = Path("data/input/preprocessing_map.json")
    
    def run_cached_translation(self, force_refresh: bool = False) -> Dict[str, any]:
        """
        Run the standalone translation with caching.
        
        Args:
            force_refresh: Force new translation even if cache exists
            
        Returns:
            Dictionary with translation metadata
        """
        # Check if cache exists and is valid
        if not force_refresh and self._is_cache_valid():
            self.clogger.info(f"Valid cache found for {self.service}, skipping translation", force=True)
            return self._load_metadata()
        
        # Create cache directory
        self.service_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Run preprocessing
        self.clogger.info("Running preprocessing for Chinese text", force=True)
        self._run_preprocessing()
        
        # Step 2: Run translation
        self.clogger.info(f"Running Chinese to English translation using {self.service}", force=True)
        self._run_translation()
        
        # Step 3: Save metadata
        metadata = self._save_metadata()
        
        self.clogger.info(f"Translation cached successfully in {self.service_cache_dir}", force=True)
        return metadata
    
    def _run_preprocessing(self):
        """
        Run preprocessing to extract tags and create mapped file.
        """
        # Create a minimal config for tag extraction
        class PreprocessConfig:
            def __init__(self, base_config):
                self.verbose = base_config.verbose
                # Load paths from common.json configuration
                preprocessing_input_file = getattr(base_config, 'preprocessing_input_file', 'scamGen_combined_first_20k.txt')
                self.preprocessing_input_path = Path("data/input") / preprocessing_input_file
                self.preprocessing_output_path = Path("data/input") / preprocessing_input_file.replace('.txt', '_mapped.txt')
                self.preprocessing_map_path = Path("data/input/preprocessing_map.json")
                self.output_dir = Path("data/cache_temp")  # Temporary output dir for preprocessing
        
        preprocess_config = PreprocessConfig(self.config)
        extractor = TagExtractor(preprocess_config)
        extractor.extract_tags()
    
    def _run_translation(self):
        """
        Run the actual translation from Chinese to English.
        """
        # Update config for the specific service and model
        if self.service == "qwen" and self.model:
            self.config.qwen_model = self.model
        
        # Create translator
        translator = TranslatorFactory.create(self.service, self.config)
        
        # Translate the preprocessed file
        translator.translate_file(
            input_path=self.preprocessed_output,
            output_path=self.cached_translation_file,
            from_code="zh-CN",
            to_code="en",
            max_lines=getattr(self.config, 'max_lines', None)
        )
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached translation exists and is valid.
        
        Returns:
            True if cache is valid, False otherwise
        """
        if not self.cached_translation_file.exists() or not self.metadata_file.exists():
            return False
        
        # Check if source file has been modified since cache file was last modified
        try:
            # Use cache file modification time instead of metadata timestamp
            cache_mtime = datetime.fromtimestamp(self.cached_translation_file.stat().st_mtime)
            source_mtime = datetime.fromtimestamp(self.chinese_input.stat().st_mtime)
            
            if source_mtime > cache_mtime:
                self.clogger.info("Source file has been modified since cache was created")
                return False
            
            # Check if translation file has expected number of lines
            with open(self.cached_translation_file, 'r', encoding='utf-8') as f:
                cached_lines = sum(1 for _ in f)
            
            # Load metadata to get expected line count
            metadata = self._load_metadata()
            expected_lines = metadata.get('line_count', 0)
            
            if cached_lines != expected_lines:
                self.clogger.warning("Cached translation line count mismatch")
                return False
            
            return True
            
        except Exception as e:
            self.clogger.error(f"Error validating cache: {e}")
            return False
    
    def _save_metadata(self) -> Dict[str, any]:
        """
        Save metadata about the translation.
        
        Returns:
            Metadata dictionary
        """
        # Count lines in translated file
        with open(self.cached_translation_file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
        
        metadata = {
            'service': self.service,
            'model': self.model,
            'timestamp': datetime.now().isoformat(),
            'line_count': line_count,
            'source_file': str(self.chinese_input),
            'max_lines': getattr(self.config, 'max_lines', None)
        }
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return metadata
    
    def _load_metadata(self) -> Dict[str, any]:
        """
        Load metadata from cache.
        
        Returns:
            Metadata dictionary
        """
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_cached_translation_path(self) -> Optional[Path]:
        """
        Get the path to cached translation if it exists.
        
        Returns:
            Path to cached translation file or None
        """
        if self._is_cache_valid():
            return self.cached_translation_file
        return None
    
    @staticmethod
    def list_cached_translations() -> Dict[str, Dict]:
        """
        List all available cached translations, including model-specific caches for Qwen.
        
        Returns:
            Dictionary mapping service names (or service/model) to metadata
        """
        cache_base = Path("data/translation_cache")
        cached = {}
        
        if cache_base.exists():
            for service_dir in cache_base.iterdir():
                if service_dir.is_dir():
                    service_name = service_dir.name
                    
                    # Check if this is a Qwen directory with model subdirectories
                    if service_name == "qwen":
                        # Look for model subdirectories
                        has_model_dirs = False
                        for model_dir in service_dir.iterdir():
                            if model_dir.is_dir():
                                metadata_file = model_dir / "metadata.json"
                                if metadata_file.exists():
                                    has_model_dirs = True
                                    try:
                                        with open(metadata_file, 'r') as f:
                                            cache_key = f"{service_name}/{model_dir.name}"
                                            cached[cache_key] = json.load(f)
                                    except Exception as e:
                                        logger.error(f"Error reading metadata for {cache_key}: {e}")
                        
                        # If no model subdirectories, check for direct metadata (old format)
                        if not has_model_dirs:
                            metadata_file = service_dir / "metadata.json"
                            if metadata_file.exists():
                                try:
                                    with open(metadata_file, 'r') as f:
                                        cached[service_name] = json.load(f)
                                except Exception as e:
                                    logger.error(f"Error reading metadata for {service_name}: {e}")
                    else:
                        # For non-Qwen services, use the service directory directly
                        metadata_file = service_dir / "metadata.json"
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r') as f:
                                    cached[service_name] = json.load(f)
                            except Exception as e:
                                logger.error(f"Error reading metadata for {service_name}: {e}")
        
        return cached
    
