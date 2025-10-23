"""
Shared data models for voice validation and TTS operations.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class VoiceInfo:
    """Represents a voice from ElevenLabs API."""
    voice_id: str
    name: str
    category: str
    description: str
    preview_url: Optional[str] = None
    labels: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    accent: Optional[str] = None


@dataclass
class VoiceValidationResult:
    """Result of voice validation."""
    voice_id: str
    is_valid: bool
    name: Optional[str] = None
    error_message: Optional[str] = None
    voice_info: Optional[VoiceInfo] = None


@dataclass
class LocaleVoiceStatus:
    """Status of voice IDs for a specific locale."""
    locale_id: str
    total_voices: int
    valid_voices: int
    invalid_voices: int
    voice_results: List[VoiceValidationResult]
    meets_minimum: bool = False
    needs_attention: bool = False
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.meets_minimum = self.valid_voices >= 2
        self.needs_attention = not self.meets_minimum or self.invalid_voices > 0


@dataclass
class ValidationSummary:
    """Summary of validation results across all locales."""
    total_locales: int
    total_voice_ids: int
    valid_voice_ids: int
    invalid_voice_ids: int
    locales_below_minimum: int
    locale_statuses: List[LocaleVoiceStatus]
    
    @property
    def success_rate(self) -> float:
        """Calculate overall voice ID success rate."""
        if self.total_voice_ids == 0:
            return 0.0
        return (self.valid_voice_ids / self.total_voice_ids) * 100.0
    
    @property
    def health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        if self.total_locales == 0:
            return 0.0
        
        # Weight different factors for health score
        voice_health = (self.valid_voice_ids / max(self.total_voice_ids, 1)) * 60  # 60% weight
        minimum_compliance = ((self.total_locales - self.locales_below_minimum) / self.total_locales) * 40  # 40% weight
        
        return voice_health + minimum_compliance


@dataclass
class VoiceSuggestion:
    """Suggestion for a voice ID to add to a locale."""
    voice_id: str
    voice_info: VoiceInfo
    reason: str
    confidence: float  # 0.0 to 1.0
    
    
@dataclass 
class LocaleConfig:
    """Simplified representation of a locale configuration."""
    locale_id: str
    language_code: str
    country_code: str
    language_name: str
    region_name: str
    voice_ids: List[str]
    voice_names: List[str]
    config_path: Path
    
    
@dataclass
class VoiceDiscoveryFilter:
    """Filter criteria for discovering compatible voices."""
    language: Optional[str] = None
    accent: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    category: Optional[str] = None
    exclude_voice_ids: Optional[List[str]] = None