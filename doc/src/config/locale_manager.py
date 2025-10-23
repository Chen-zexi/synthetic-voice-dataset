"""
Locale configuration management for voice scam dataset generator.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import asdict

from tts.models import (
    LocaleConfig, LocaleVoiceStatus, VoiceValidationResult, 
    ValidationSummary, VoiceSuggestion
)

logger = logging.getLogger(__name__)


class LocaleConfigManager:
    """Manages locale configuration files and voice ID operations."""
    
    def __init__(self, config_dir: str = "configs/localizations"):
        """
        Initialize the locale configuration manager.
        
        Args:
            config_dir: Directory containing locale configurations
        """
        self.config_dir = Path(config_dir)
        self.locales = self._discover_locales()
        logger.info(f"Discovered {len(self.locales)} locales: {', '.join(self.locales)}")
    
    def _discover_locales(self) -> List[str]:
        """
        Discover all available locale directories.
        
        Returns:
            List of locale IDs
        """
        locales = []
        if self.config_dir.exists():
            for item in self.config_dir.iterdir():
                if (item.is_dir() and 
                    item.name != 'template' and 
                    (item / 'config.json').exists()):
                    locales.append(item.name)
        return sorted(locales)
    
    def get_config_path(self, locale: str) -> Path:
        """
        Get path to locale configuration file.
        
        Args:
            locale: Locale ID
            
        Returns:
            Path to config.json file
        """
        return self.config_dir / locale / 'config.json'
    
    def load_config(self, locale: str) -> Dict:
        """
        Load configuration for a specific locale.
        
        Args:
            locale: Locale ID
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
        """
        config_path = self.get_config_path(locale)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_config(self, locale: str, config: Dict) -> None:
        """
        Save configuration for a specific locale.
        
        Args:
            locale: Locale ID
            config: Configuration dictionary to save
        """
        config_path = self.get_config_path(locale)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved configuration for locale: {locale}")
    
    def load_locale_config(self, locale: str) -> LocaleConfig:
        """
        Load locale configuration as a LocaleConfig object.
        
        Args:
            locale: Locale ID
            
        Returns:
            LocaleConfig object
        """
        config = self.load_config(locale)
        locale_info = config.get('locale', {})
        voices = config.get('voices', {})
        
        return LocaleConfig(
            locale_id=locale,
            language_code=locale_info.get('language_code', ''),
            country_code=locale_info.get('country_code', ''),
            language_name=locale_info.get('language_name', ''),
            region_name=locale_info.get('region_name', ''),
            voice_ids=voices.get('ids', []),
            voice_names=voices.get('names', []),
            config_path=self.get_config_path(locale)
        )
    
    def extract_all_voice_ids(self) -> Dict[str, List[str]]:
        """
        Extract all voice IDs from all locale configurations.
        
        Returns:
            Dictionary mapping locale IDs to their voice ID lists
        """
        all_voice_ids = {}
        
        for locale in self.locales:
            try:
                config = self.load_config(locale)
                voice_ids = config.get('voices', {}).get('ids', [])
                all_voice_ids[locale] = voice_ids
            except Exception as e:
                logger.error(f"Error loading config for {locale}: {e}")
                all_voice_ids[locale] = []
        
        return all_voice_ids
    
    def get_unique_voice_ids(self) -> Set[str]:
        """
        Get all unique voice IDs across all configurations.
        
        Returns:
            Set of unique voice IDs
        """
        all_ids = set()
        voice_ids_by_locale = self.extract_all_voice_ids()
        
        for locale, ids in voice_ids_by_locale.items():
            all_ids.update(ids)
        
        return all_ids
    
    def get_locale_voice_count(self, locale: str) -> int:
        """
        Get the number of voice IDs for a specific locale.
        
        Args:
            locale: Locale ID
            
        Returns:
            Number of voice IDs
        """
        try:
            config = self.load_config(locale)
            return len(config.get('voices', {}).get('ids', []))
        except Exception:
            return 0
    
    def get_locales_below_minimum(self, minimum: int = 2) -> List[str]:
        """
        Get locales that have fewer than the minimum number of voice IDs.
        
        Args:
            minimum: Minimum number of voice IDs required
            
        Returns:
            List of locale IDs below minimum
        """
        below_minimum = []
        
        for locale in self.locales:
            voice_count = self.get_locale_voice_count(locale)
            if voice_count < minimum:
                below_minimum.append(locale)
        
        return below_minimum
    
    def validate_locale_voice_requirements(
        self, 
        validation_results: Dict[str, Tuple[bool, Optional[object]]]
    ) -> ValidationSummary:
        """
        Validate voice requirements across all locales.
        
        Args:
            validation_results: Dictionary of voice validation results
            
        Returns:
            ValidationSummary with detailed status information
        """
        locale_statuses = []
        total_valid = 0
        total_invalid = 0
        locales_below_minimum = 0
        
        locale_voice_ids = self.extract_all_voice_ids()
        
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
    
    def add_voice_to_locale(self, locale: str, voice_id: str, voice_name: str) -> bool:
        """
        Add a voice ID to a locale configuration.
        
        Args:
            locale: Locale ID
            voice_id: Voice ID to add
            voice_name: Human-readable voice name
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            config = self.load_config(locale)
            voices = config.get('voices', {})
            
            current_ids = voices.get('ids', [])
            current_names = voices.get('names', [])
            
            # Check if voice ID already exists
            if voice_id in current_ids:
                logger.warning(f"Voice ID {voice_id} already exists in {locale}")
                return False
            
            # Add the new voice
            current_ids.append(voice_id)
            current_names.append(voice_name)
            
            voices['ids'] = current_ids
            voices['names'] = current_names
            config['voices'] = voices
            
            self.save_config(locale, config)
            logger.info(f"Added voice {voice_id} ({voice_name}) to {locale}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding voice to {locale}: {e}")
            return False
    
    def remove_invalid_voices(
        self, 
        validation_results: Dict[str, Tuple[bool, Optional[object]]]
    ) -> Dict[str, List[str]]:
        """
        Remove invalid voice IDs from all locale configurations.
        
        Args:
            validation_results: Dictionary of voice validation results
            
        Returns:
            Dictionary mapping locale IDs to lists of removed voice IDs
        """
        removed_voices = {}
        
        for locale in self.locales:
            try:
                config = self.load_config(locale)
                original_ids = config.get('voices', {}).get('ids', [])
                original_names = config.get('voices', {}).get('names', [])
                
                # Filter out invalid IDs
                valid_ids = []
                valid_names = []
                removed_ids = []
                
                for i, voice_id in enumerate(original_ids):
                    is_valid, _ = validation_results.get(voice_id, (False, None))
                    
                    if is_valid:
                        valid_ids.append(voice_id)
                        if i < len(original_names):
                            valid_names.append(original_names[i])
                    else:
                        removed_ids.append(voice_id)
                
                # Update config if changes needed
                if removed_ids:
                    config['voices']['ids'] = valid_ids
                    config['voices']['names'] = valid_names
                    
                    # Add note about removed invalid IDs
                    note = f"Invalid voice IDs removed: {', '.join(removed_ids)}. Use --validate-voices to find alternatives."
                    config['voices']['_note'] = note
                    
                    self.save_config(locale, config)
                    logger.info(f"Updated {locale}: Removed {len(removed_ids)} invalid voice IDs")
                
                removed_voices[locale] = removed_ids
                
            except Exception as e:
                logger.error(f"Error updating {locale}: {e}")
                removed_voices[locale] = []
        
        return removed_voices
    
    def get_voice_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about voice ID usage across locales.
        
        Returns:
            Dictionary with usage statistics
        """
        voice_usage = {}
        locale_voice_ids = self.extract_all_voice_ids()
        
        # Count voice ID usage
        for locale, voice_ids in locale_voice_ids.items():
            for voice_id in voice_ids:
                if voice_id not in voice_usage:
                    voice_usage[voice_id] = {'count': 0, 'locales': []}
                voice_usage[voice_id]['count'] += 1
                voice_usage[voice_id]['locales'].append(locale)
        
        # Calculate summary stats
        total_voices = len(voice_usage)
        shared_voices = sum(1 for stats in voice_usage.values() if stats['count'] > 1)
        unique_voices = total_voices - shared_voices
        
        return {
            'total_unique_voices': total_voices,
            'shared_voices': shared_voices,
            'unique_voices': unique_voices,
            'voice_details': voice_usage
        }