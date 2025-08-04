"""
ElevenLabs voice ID validation utility.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from utils.logging_utils import ConditionalLogger

logger = logging.getLogger(__name__)


@dataclass
class VoiceValidationResult:
    """Result of voice validation."""
    voice_id: str
    is_valid: bool
    name: Optional[str] = None
    error_message: Optional[str] = None


class VoiceValidator:
    """
    Validates ElevenLabs voice IDs by checking if they exist and are accessible.
    """
    
    def __init__(self, api_key: str, verbose: bool = False):
        """
        Initialize the voice validator.
        
        Args:
            api_key: ElevenLabs API key
            verbose: Whether to show verbose output
        """
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self._voice_cache: Dict[str, VoiceValidationResult] = {}
        self.clogger = ConditionalLogger(__name__, verbose)
    
    async def validate_voice_ids(self, voice_ids: List[str]) -> List[VoiceValidationResult]:
        """
        Validate multiple voice IDs concurrently.
        
        Args:
            voice_ids: List of voice IDs to validate
            
        Returns:
            List of validation results
        """
        if not voice_ids:
            return []
        
        self.clogger.info(f"Validating {len(voice_ids)} voice IDs", force=True)
        
        # Check cache first
        cached_results = []
        uncached_ids = []
        
        for voice_id in voice_ids:
            if voice_id in self._voice_cache:
                cached_results.append(self._voice_cache[voice_id])
            else:
                uncached_ids.append(voice_id)
        
        # Validate uncached IDs
        if uncached_ids:
            async with aiohttp.ClientSession() as session:
                tasks = [self._validate_single_voice(session, voice_id) for voice_id in uncached_ids]
                new_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and update cache
                for result in new_results:
                    if isinstance(result, VoiceValidationResult):
                        self._voice_cache[result.voice_id] = result
                        cached_results.append(result)
                    elif isinstance(result, Exception):
                        self.clogger.error(f"Error validating voice: {result}")
        
        # Sort results to match input order
        result_map = {r.voice_id: r for r in cached_results}
        return [result_map.get(voice_id, VoiceValidationResult(voice_id, False, error_message="Validation failed")) 
                for voice_id in voice_ids]
    
    async def _validate_single_voice(self, session: aiohttp.ClientSession, voice_id: str) -> VoiceValidationResult:
        """
        Validate a single voice ID.
        
        Args:
            session: HTTP session
            voice_id: Voice ID to validate
            
        Returns:
            Validation result
        """
        url = f"{self.base_url}/voices/{voice_id}"
        headers = {"xi-api-key": self.api_key}
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    voice_name = data.get("name", "Unknown")
                    self.clogger.debug(f"Voice {voice_id} is valid: {voice_name}")
                    return VoiceValidationResult(voice_id, True, voice_name)
                elif response.status == 404:
                    error_msg = f"Voice not found: {voice_id}"
                    self.clogger.warning(error_msg)
                    return VoiceValidationResult(voice_id, False, error_message=error_msg)
                else:
                    error_text = await response.text()
                    error_msg = f"API error ({response.status}): {error_text}"
                    self.clogger.error(f"Error validating voice {voice_id}: {error_msg}")
                    return VoiceValidationResult(voice_id, False, error_message=error_msg)
                    
        except Exception as e:
            error_msg = f"Exception during validation: {str(e)}"
            logger.error(f"Error validating voice {voice_id}: {error_msg}")
            return VoiceValidationResult(voice_id, False, error_message=error_msg)
    
    async def get_available_voices(self) -> List[Dict]:
        """
        Get all available voices from ElevenLabs API.
        
        Returns:
            List of voice information dictionaries
        """
        url = f"{self.base_url}/voices"
        headers = {"xi-api-key": self.api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        voices = data.get("voices", [])
                        self.clogger.info(f"Retrieved {len(voices)} available voices")
                        return voices
                    else:
                        error_text = await response.text()
                        self.clogger.error(f"Error getting available voices ({response.status}): {error_text}")
                        return []
        except Exception as e:
            self.clogger.error(f"Exception getting available voices: {e}")
            return []
    
    def get_invalid_voices(self, results: List[VoiceValidationResult]) -> List[VoiceValidationResult]:
        """
        Filter and return only invalid voice results.
        
        Args:
            results: List of validation results
            
        Returns:
            List of invalid voice results
        """
        return [r for r in results if not r.is_valid]
    
    def get_valid_voices(self, results: List[VoiceValidationResult]) -> List[VoiceValidationResult]:
        """
        Filter and return only valid voice results.
        
        Args:
            results: List of validation results
            
        Returns:
            List of valid voice results
        """
        return [r for r in results if r.is_valid]
    
    def clear_cache(self):
        """Clear the voice validation cache."""
        self._voice_cache.clear()
        self.clogger.debug("Voice validation cache cleared")