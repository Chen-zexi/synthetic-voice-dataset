"""
Argos Translate implementation for the translation module with async support.
"""

import logging
import asyncio
import re
import argostranslate.package
import argostranslate.translate

from translation.translator import BaseTranslator
from config.config_loader import Config
from translation.language_codes import get_language_code


logger = logging.getLogger(__name__)


class ArgosTranslator(BaseTranslator):
    """
    Argos Translate implementation of the translator interface with async support.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Argos translator.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
        self.installed_packages = {}
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent Argos translations
        self._initialize_packages()
    
    def _initialize_packages(self):
        """Download and install required translation packages."""
        logger.info("Initializing Argos Translate packages...")
        
        # Update package index
        argostranslate.package.update_package_index()
        
        # Get available packages
        available_packages = argostranslate.package.get_available_packages()
        logger.debug(f"Found {len(available_packages)} available packages")
    
    def _get_translation_package(self, from_code: str, to_code: str):
        """
        Get or install the translation package for a language pair.
        
        Args:
            from_code: Source language code
            to_code: Target language code
            
        Returns:
            Translation package
        """
        # Map language codes for Argos
        source_code = get_language_code('argos', from_code)
        target_code = get_language_code('argos', to_code)
        
        package_key = f"{source_code}-{target_code}"
        
        if package_key in self.installed_packages:
            return self.installed_packages[package_key]
        
        # Find and install package
        available_packages = argostranslate.package.get_available_packages()
        package = next(
            (pkg for pkg in available_packages 
             if pkg.from_code == source_code and pkg.to_code == target_code),
            None
        )
        
        if not package:
            raise ValueError(f"No Argos package found for {source_code} -> {target_code}")
        
        logger.info(f"Installing Argos package: {source_code} -> {target_code}")
        argostranslate.package.install_from_path(package.download())
        
        # Get installed package
        installed_packages = argostranslate.translate.get_installed_languages()
        for from_lang in installed_packages:
            if from_lang.code == source_code:
                for to_lang in from_lang.get_translation(target_code):
                    if to_lang.code == target_code:
                        self.installed_packages[package_key] = (from_lang, to_lang)
                        return self.installed_packages[package_key]
        
        raise ValueError(f"Failed to install package for {source_code} -> {target_code}")
    
    async def translate_text(self, text: str, from_code: str, to_code: str) -> str:
        """
        Translate text using Argos Translate asynchronously.
        
        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code
            
        Returns:
            Translated text
        """
        if not text.strip():
            return text
        
        async with self.semaphore:
            try:
                # Preserve placeholders
                placeholders = self.placeholder_pattern.findall(text)
                temp_text = text
                
                # Replace placeholders with temporary markers
                # Use a pattern that translation services are less likely to modify
                for i, placeholder in enumerate(placeholders):
                    temp_text = temp_text.replace(placeholder, f"###PH{i}###")
                
                # Get translation package (this is sync but fast)
                from_lang, to_lang = self._get_translation_package(from_code, to_code)
                
                # Translate using asyncio.to_thread to avoid blocking
                translation = from_lang.get_translation(to_lang)
                translated = await asyncio.to_thread(translation.translate, temp_text)
                
                # Restore placeholders
                for i, placeholder in enumerate(placeholders):
                    # Replace our marker back with original placeholder
                    translated = translated.replace(f"###PH{i}###", placeholder)
                    # Also try variations in case translation modified it
                    translated = translated.replace(f"### PH{i} ###", placeholder)
                    translated = translated.replace(f"###ph{i}###", placeholder)
                    translated = translated.replace(f"### ph{i} ###", placeholder)
                
                self.clogger.debug(f"Translated: '{text[:50]}...' -> '{translated[:50]}...'")
                return translated
                
            except Exception as e:
                logger.error(f"Argos translation failed: {e}")
                return text  # Return original text if translation fails