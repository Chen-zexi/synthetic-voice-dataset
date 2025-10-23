"""
ElevenLabs voice ID validation utility with both async and sync support.
"""

import asyncio
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

from elevenlabs.client import AsyncElevenLabs, ElevenLabs
from utils.logging_utils import ConditionalLogger
from tts.models import (
    VoiceInfo, VoiceValidationResult, VoiceDiscoveryFilter, 
    VoiceSuggestion, LocaleVoiceStatus, ValidationSummary
)

logger = logging.getLogger(__name__)


class VoiceValidator:
    """
    Validates ElevenLabs voice IDs by checking if they exist and are accessible.
    Supports both async and synchronous operations.
    """
    
    def __init__(self, api_key: str, verbose: bool = False):
        """
        Initialize the voice validator.
        
        Args:
            api_key: ElevenLabs API key
            verbose: Whether to show verbose output
        """
        self.api_key = api_key
        self.async_client = AsyncElevenLabs(api_key=api_key)
        self.sync_client = ElevenLabs(api_key=api_key)
        self.base_url = "https://api.elevenlabs.io/v1"  # Keep for backwards compatibility
        self._voice_cache: Dict[str, VoiceValidationResult] = {}
        self._all_voices_cache: Optional[Dict[str, VoiceInfo]] = None
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
        
        # Validate uncached IDs using SDK
        if uncached_ids:
            tasks = [self._validate_single_voice_sdk(voice_id) for voice_id in uncached_ids]
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
    
    async def _validate_single_voice_sdk(self, voice_id: str) -> VoiceValidationResult:
        """
        Validate a single voice ID using the ElevenLabs SDK.
        
        Args:
            voice_id: Voice ID to validate
            
        Returns:
            Validation result
        """
        try:
            voice = await self.async_client.voices.get(voice_id)
            voice_name = voice.name if hasattr(voice, 'name') else "Unknown"
            self.clogger.debug(f"Voice {voice_id} is valid: {voice_name}")
            return VoiceValidationResult(voice_id, True, voice_name)
            
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                error_msg = f"Voice not found: {voice_id}"
                self.clogger.warning(error_msg)
            else:
                self.clogger.error(f"Error validating voice {voice_id}: {error_msg}")
            return VoiceValidationResult(voice_id, False, error_message=error_msg)
    
    async def get_available_voices(self) -> List[Dict]:
        """
        Get all available voices from ElevenLabs API using SDK.
        
        Returns:
            List of voice information dictionaries
        """
        try:
            voices_response = await self.async_client.voices.get_all()
            voices = []
            
            if hasattr(voices_response, 'voices'):
                for voice in voices_response.voices:
                    voice_dict = {
                        'voice_id': voice.voice_id,
                        'name': voice.name,
                        'category': getattr(voice, 'category', 'unknown'),
                        'description': getattr(voice, 'description', ''),
                        'preview_url': getattr(voice, 'preview_url', None),
                        'labels': getattr(voice, 'labels', {})
                    }
                    voices.append(voice_dict)
                
                self.clogger.info(f"Retrieved {len(voices)} available voices")
                return voices
            else:
                self.clogger.error("Unexpected response format from voices API")
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
        self._all_voices_cache = None
        self.clogger.debug("Voice validation cache cleared")
    
    # Synchronous Methods for CLI and Testing
    
    def validate_voice_ids_sync(self, voice_ids: List[str]) -> Dict[str, Tuple[bool, Optional[VoiceInfo]]]:
        """
        Synchronously validate multiple voice IDs (compatible with original standalone script).
        
        Args:
            voice_ids: List of voice IDs to validate
            
        Returns:
            Dictionary mapping voice_id to (is_valid, voice_info) tuples
        """
        if not voice_ids:
            return {}
        
        self.clogger.info(f"Validating {len(voice_ids)} voice IDs (sync)", force=True)
        
        # Get all available voices first
        all_voices = self.get_all_voices_sync()
        
        results = {}
        for voice_id in voice_ids:
            voice_info = all_voices.get(voice_id)
            is_valid = voice_info is not None
            results[voice_id] = (is_valid, voice_info)
            
            if is_valid:
                self.clogger.debug(f"Voice {voice_id} is valid: {voice_info.name}")
            else:
                self.clogger.warning(f"Voice {voice_id} not found")
        
        return results
    
    def get_all_voices_sync(self) -> Dict[str, VoiceInfo]:
        """
        Synchronously fetch all available voices from ElevenLabs API using SDK.
        
        Returns:
            Dictionary mapping voice_id to VoiceInfo objects
        """
        if self._all_voices_cache is not None:
            return self._all_voices_cache
        
        self.clogger.info("Fetching all voices from ElevenLabs API (sync)...")
        
        try:
            voices_response = self.sync_client.voices.get_all()
            voices = {}
            
            if hasattr(voices_response, 'voices'):
                for voice_data in voices_response.voices:
                    voice_info = VoiceInfo(
                        voice_id=voice_data.voice_id,
                        name=voice_data.name,
                        category=getattr(voice_data, 'category', 'unknown'),
                        description=getattr(voice_data, 'description', ''),
                        preview_url=getattr(voice_data, 'preview_url', None),
                        labels=getattr(voice_data, 'labels', {}),
                        language=getattr(voice_data, 'labels', {}).get('language') if hasattr(voice_data, 'labels') else None,
                        accent=getattr(voice_data, 'labels', {}).get('accent') if hasattr(voice_data, 'labels') else None
                    )
                    voices[voice_info.voice_id] = voice_info
                
                self._all_voices_cache = voices
                self.clogger.info(f"Fetched {len(voices)} voices from ElevenLabs API")
                return voices
            else:
                self.clogger.error("Unexpected response format from voices API")
                raise RuntimeError("Failed to fetch voices: unexpected response format")
            
        except Exception as e:
            self.clogger.error(f"Error fetching voices from ElevenLabs API: {e}")
            raise
    
    def validate_single_voice_sync(self, voice_id: str) -> Tuple[bool, Optional[VoiceInfo]]:
        """
        Synchronously validate a single voice ID.
        
        Args:
            voice_id: Voice ID to validate
            
        Returns:
            Tuple of (is_valid, voice_info)
        """
        all_voices = self.get_all_voices_sync()
        voice_info = all_voices.get(voice_id)
        return (voice_info is not None, voice_info)
    
    # Voice Discovery and Suggestion Methods
    
    def find_compatible_voices(
        self, 
        filter_criteria: VoiceDiscoveryFilter, 
        limit: int = 10
    ) -> List[VoiceInfo]:
        """
        Find voices that match the given criteria.
        
        Args:
            filter_criteria: Criteria for filtering voices
            limit: Maximum number of voices to return
            
        Returns:
            List of matching VoiceInfo objects
        """
        all_voices = self.get_all_voices_sync()
        compatible_voices = []
        
        for voice_info in all_voices.values():
            # Skip excluded voices
            if (filter_criteria.exclude_voice_ids and 
                voice_info.voice_id in filter_criteria.exclude_voice_ids):
                continue
            
            # Check language match
            if (filter_criteria.language and 
                voice_info.language != filter_criteria.language):
                continue
            
            # Check accent match
            if (filter_criteria.accent and 
                voice_info.accent != filter_criteria.accent):
                continue
            
            # Check category match
            if (filter_criteria.category and 
                voice_info.category != filter_criteria.category):
                continue
            
            # Check gender match (extracted from labels)
            if filter_criteria.gender:
                voice_gender = voice_info.labels.get('gender') if voice_info.labels else None
                if voice_gender != filter_criteria.gender:
                    continue
            
            # Check age match (extracted from labels)
            if filter_criteria.age:
                voice_age = voice_info.labels.get('age') if voice_info.labels else None
                if voice_age != filter_criteria.age:
                    continue
            
            compatible_voices.append(voice_info)
            
            if len(compatible_voices) >= limit:
                break
        
        return compatible_voices
    
    def suggest_voices_for_locale(
        self, 
        locale_id: str, 
        language_code: str, 
        current_voice_ids: List[str], 
        needed_count: int = 1
    ) -> List[VoiceSuggestion]:
        """
        Suggest additional voices for a locale that needs more voice IDs.
        
        Args:
            locale_id: Locale identifier
            language_code: Language code for the locale
            current_voice_ids: Voice IDs already used by this locale
            needed_count: Number of additional voices needed
            
        Returns:
            List of voice suggestions
        """
        filter_criteria = VoiceDiscoveryFilter(
            language=language_code,
            exclude_voice_ids=current_voice_ids
        )
        
        compatible_voices = self.find_compatible_voices(
            filter_criteria, 
            limit=needed_count * 3  # Get more options than needed
        )
        
        suggestions = []
        for i, voice_info in enumerate(compatible_voices[:needed_count]):
            confidence = max(0.5, 1.0 - (i * 0.1))  # Decrease confidence for later suggestions
            reason = f"Compatible {language_code} voice with {voice_info.accent or 'standard'} accent"
            
            suggestion = VoiceSuggestion(
                voice_id=voice_info.voice_id,
                voice_info=voice_info,
                reason=reason,
                confidence=confidence
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def check_minimum_requirements(
        self, 
        validation_results: Dict[str, Tuple[bool, Optional[VoiceInfo]]], 
        locale_voice_ids: Dict[str, List[str]], 
        minimum: int = 2
    ) -> ValidationSummary:
        """
        Check if locales meet minimum voice ID requirements.
        
        Args:
            validation_results: Results from voice validation
            locale_voice_ids: Voice IDs by locale
            minimum: Minimum number of valid voices required per locale
            
        Returns:
            ValidationSummary with detailed status information
        """
        locale_statuses = []
        total_valid = 0
        total_invalid = 0
        locales_below_minimum = 0
        
        for locale, voice_ids in locale_voice_ids.items():
            if not voice_ids:
                continue
            
            # Create validation results for this locale
            voice_results = []
            valid_count = 0
            
            for voice_id in voice_ids:
                is_valid, voice_info = validation_results.get(voice_id, (False, None))
                
                result = VoiceValidationResult(
                    voice_id=voice_id,
                    is_valid=is_valid,
                    name=voice_info.name if voice_info else None,
                    voice_info=voice_info
                )
                voice_results.append(result)
                
                if is_valid:
                    valid_count += 1
                    total_valid += 1
                else:
                    total_invalid += 1
            
            # Create locale status
            status = LocaleVoiceStatus(
                locale_id=locale,
                total_voices=len(voice_ids),
                valid_voices=valid_count,
                invalid_voices=len(voice_ids) - valid_count,
                voice_results=voice_results
            )
            
            if not status.meets_minimum:
                locales_below_minimum += 1
            
            locale_statuses.append(status)
        
        return ValidationSummary(
            total_locales=len(locale_statuses),
            total_voice_ids=total_valid + total_invalid,
            valid_voice_ids=total_valid,
            invalid_voice_ids=total_invalid,
            locales_below_minimum=locales_below_minimum,
            locale_statuses=locale_statuses
        )