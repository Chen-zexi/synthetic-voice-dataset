"""
Google Translate implementation for the translation module.
"""

import logging
import time
import re
from deep_translator import GoogleTranslator as GoogleTranslatorClient

from translation.translator import BaseTranslator
from config.config_loader import Config
from translation.language_codes import get_language_code


logger = logging.getLogger(__name__)


class GoogleTranslator(BaseTranslator):
    """
    Google Translate implementation of the translator interface.
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
    
    def translate_text(self, text: str, from_code: str, to_code: str) -> str:
        """
        Translate text using Google Translate.
        
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
        
        for attempt in range(self.retry_count):
            try:
                
                # Translate using deep-translator with mapped codes
                translator = GoogleTranslatorClient(source=source_code, target=target_code)
                translated = translator.translate(text)
                
                return translated
                
            except Exception as e:
                logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Translation failed after {self.retry_count} attempts")
                    return text  # Return original text if translation fails