"""
Google Translate implementation for the translation module with async support.
"""

import logging
import asyncio
import time
from typing import Optional
from deep_translator import GoogleTranslator as GoogleTranslatorClient

from translation.translator import BaseTranslator
from config.config_loader import Config
from translation.language_codes import get_language_code


logger = logging.getLogger(__name__)


class GoogleTranslator(BaseTranslator):
    """
    Google Translate implementation of the translator interface with async support.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Google translator.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
        self.retry_count = 3
        self.retry_delay = 1.0
        # Create a semaphore for rate limiting Google Translate requests
        self.semaphore = asyncio.Semaphore(5)  # Conservative limit
    
    async def translate_text(self, text: str, from_code: str, to_code: str) -> str:
        """
        Translate text using Google Translate asynchronously.
        
        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code
            
        Returns:
            Translated text
        """
        if not text.strip():
            return text
        
        # Map language codes for Google Translate
        source_code = get_language_code('google', from_code)
        target_code = get_language_code('google', to_code)
        
        async with self.semaphore:
            for attempt in range(self.retry_count):
                try:
                    # Use asyncio.to_thread to run the blocking deep_translator call
                    translator = GoogleTranslatorClient(source=source_code, target=target_code)
                    translated = await asyncio.to_thread(translator.translate, text)
                    
                    if translated:
                        self.clogger.debug(f"Translated: '{text[:50]}...' -> '{translated[:50]}...'")
                        return translated
                    else:
                        raise Exception("Translation returned empty result")
                    
                except Exception as e:
                    logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                    if attempt < self.retry_count - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        logger.error(f"Translation failed after {self.retry_count} attempts: {e}")
                        return text  # Return original text if translation fails
        
        return text
    
