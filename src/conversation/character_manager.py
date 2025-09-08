"""
Character profile manager for creating diverse conversation participants.
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CharacterProfile(BaseModel):
    """Schema for a character profile."""
    profile_id: str = Field(description="Unique identifier for this profile")
    name: str = Field(description="Display name for the character")
    gender: Literal["male", "female", "any"] = Field(description="Character gender")
    age_range: Literal["young", "middle-aged", "senior", "any"] = Field(description="Character age range")
    personality_traits: List[str] = Field(description="Personality characteristics (e.g., 'impatient', 'friendly', 'nervous')")
    speaking_style: List[str] = Field(description="Communication patterns (e.g., 'fast-paced', 'formal', 'hesitant')")
    education_level: Literal["high_school", "college", "graduate", "any"] = Field(description="Education background")
    locale_affinity: Optional[List[str]] = Field(default=None, description="Preferred locales (e.g., ['en-sg', 'ms-my'])")
    role_preference: Optional[Literal["scammer", "victim", "any"]] = Field(default="any", description="Preferred role in conversations")


class GenerationScenario(BaseModel):
    """A complete scenario for conversation generation."""
    scenario_id: str = Field(description="Unique identifier for this scenario")
    seed_tag: str = Field(description="The scam tag being used")
    scammer_profile: CharacterProfile = Field(description="Profile for the scammer character")
    victim_profile: CharacterProfile = Field(description="Profile for the victim character")
    locale: str = Field(description="Target locale for the conversation")


class CharacterManager:
    """
    Manages character profiles and creates generation scenarios.
    """
    
    def __init__(self, character_profiles_path: Optional[Path] = None):
        """
        Initialize the character manager.
        
        Args:
            character_profiles_path: Path to character profiles JSON file
        """
        self.character_profiles_path = character_profiles_path
        self.profiles: List[CharacterProfile] = []
        self._loaded = False
        
        # Load profiles if path provided
        if character_profiles_path:
            self.load_profiles()
        else:
            # Create default profiles
            self.create_default_profiles()
    
    def load_profiles(self):
        """Load character profiles from JSON file."""
        if not self.character_profiles_path or not self.character_profiles_path.exists():
            logger.warning(f"Character profiles file not found: {self.character_profiles_path}")
            self.create_default_profiles()
            return
        
        logger.info(f"Loading character profiles from {self.character_profiles_path}")
        
        with open(self.character_profiles_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        profiles_data = data.get('profiles', [])
        
        for profile_data in profiles_data:
            try:
                profile = CharacterProfile(**profile_data)
                self.profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to parse character profile: {e}")
        
        logger.info(f"Loaded {len(self.profiles)} character profiles")
        self._loaded = True
    
    def create_default_profiles(self):
        """Create default character profiles for immediate use."""
        logger.info("Creating default character profiles")
        
        # Default scammer profiles
        scammer_profiles = [
            {
                "profile_id": "authoritative_scammer_01",
                "name": "Authority Figure Scammer",
                "gender": "any",
                "age_range": "middle-aged",
                "personality_traits": ["authoritative", "confident", "urgent", "professional"],
                "speaking_style": ["formal", "commanding", "technical-terms"],
                "education_level": "college",
                "role_preference": "scammer"
            },
            {
                "profile_id": "friendly_scammer_01",
                "name": "Friendly Helper Scammer",
                "gender": "any", 
                "age_range": "young",
                "personality_traits": ["friendly", "helpful", "reassuring", "patient"],
                "speaking_style": ["conversational", "empathetic", "casual"],
                "education_level": "high_school",
                "role_preference": "scammer"
            },
            {
                "profile_id": "urgent_scammer_01",
                "name": "Time-Pressure Scammer",
                "gender": "any",
                "age_range": "middle-aged", 
                "personality_traits": ["urgent", "impatient", "persistent", "alarming"],
                "speaking_style": ["fast-paced", "interrupting", "repetitive"],
                "education_level": "any",
                "role_preference": "scammer"
            }
        ]
        
        # Default victim profiles
        victim_profiles = [
            {
                "profile_id": "trusting_victim_01",
                "name": "Trusting Individual",
                "gender": "any",
                "age_range": "senior",
                "personality_traits": ["trusting", "polite", "concerned", "cooperative"],
                "speaking_style": ["hesitant", "questioning", "polite"],
                "education_level": "high_school",
                "role_preference": "victim"
            },
            {
                "profile_id": "skeptical_victim_01", 
                "name": "Skeptical Person",
                "gender": "any",
                "age_range": "middle-aged",
                "personality_traits": ["skeptical", "cautious", "analytical", "questioning"],
                "speaking_style": ["probing", "demanding-proof", "suspicious"],
                "education_level": "college",
                "role_preference": "victim"
            },
            {
                "profile_id": "busy_victim_01",
                "name": "Busy Professional", 
                "gender": "any",
                "age_range": "young",
                "personality_traits": ["busy", "distracted", "efficient", "impatient"],
                "speaking_style": ["brief", "multitasking", "rushed"],
                "education_level": "graduate",
                "role_preference": "victim"
            },
            {
                "profile_id": "confused_victim_01",
                "name": "Confused Individual",
                "gender": "any",
                "age_range": "senior",
                "personality_traits": ["confused", "anxious", "seeking-help", "vulnerable"],
                "speaking_style": ["slow", "repetitive-questions", "uncertain"],
                "education_level": "any",
                "role_preference": "victim"
            }
        ]
        
        # Create profile objects
        all_profiles = scammer_profiles + victim_profiles
        for profile_data in all_profiles:
            try:
                profile = CharacterProfile(**profile_data)
                self.profiles.append(profile)
            except Exception as e:
                logger.error(f"Failed to create default profile: {e}")
        
        logger.info(f"Created {len(self.profiles)} default character profiles")
        self._loaded = True
    
    def get_profiles_for_role(self, role: str, locale: Optional[str] = None) -> List[CharacterProfile]:
        """
        Get character profiles suitable for a specific role.
        
        Args:
            role: Either 'scammer' or 'victim'
            locale: Optional locale to filter by affinity
            
        Returns:
            List of suitable CharacterProfile objects
        """
        suitable_profiles = []
        
        for profile in self.profiles:
            # Check role preference
            if profile.role_preference not in [role, "any"]:
                continue
            
            # Check locale affinity if specified
            if locale and profile.locale_affinity:
                if locale not in profile.locale_affinity:
                    continue
            
            suitable_profiles.append(profile)
        
        return suitable_profiles
    
    def select_random_profile(self, role: str, locale: Optional[str] = None) -> Optional[CharacterProfile]:
        """
        Randomly select a profile for a given role.
        
        Args:
            role: Either 'scammer' or 'victim'  
            locale: Optional locale for filtering
            
        Returns:
            Selected CharacterProfile or None if no suitable profiles
        """
        suitable_profiles = self.get_profiles_for_role(role, locale)
        
        if not suitable_profiles:
            logger.warning(f"No suitable profiles found for role '{role}' and locale '{locale}'")
            return None
        
        return random.choice(suitable_profiles)
    
    def create_scenario(self, seed_tag: str, locale: str, scenario_id: Optional[str] = None) -> Optional[GenerationScenario]:
        """
        Create a generation scenario by combining seed with character profiles.
        
        Args:
            seed_tag: The scam tag to use
            locale: Target locale for the conversation
            scenario_id: Optional custom scenario ID
            
        Returns:
            GenerationScenario object or None if profiles unavailable
        """
        # Select profiles
        scammer_profile = self.select_random_profile("scammer", locale)
        victim_profile = self.select_random_profile("victim", locale)
        
        if not scammer_profile or not victim_profile:
            logger.error(f"Could not create scenario for seed '{seed_tag}' - missing profiles")
            return None
        
        # Generate scenario ID
        if not scenario_id:
            scenario_id = f"{seed_tag}_{scammer_profile.profile_id}_{victim_profile.profile_id}_{locale}"
        
        return GenerationScenario(
            scenario_id=scenario_id,
            seed_tag=seed_tag,
            scammer_profile=scammer_profile,
            victim_profile=victim_profile,
            locale=locale
        )
    
    def create_multiple_scenarios(self, seed_tags: List[str], locale: str, 
                                scenarios_per_seed: int = 1) -> List[GenerationScenario]:
        """
        Create multiple scenarios for a list of seed tags.
        
        Args:
            seed_tags: List of scam tags to create scenarios for
            locale: Target locale
            scenarios_per_seed: Number of different scenarios per seed
            
        Returns:
            List of GenerationScenario objects
        """
        scenarios = []
        
        for seed_tag in seed_tags:
            for i in range(scenarios_per_seed):
                scenario = self.create_scenario(
                    seed_tag=seed_tag,
                    locale=locale,
                    scenario_id=f"{seed_tag}_{locale}_{i+1:03d}"
                )
                if scenario:
                    scenarios.append(scenario)
        
        logger.info(f"Created {len(scenarios)} scenarios from {len(seed_tags)} seed tags")
        return scenarios
    
    def get_stats(self) -> Dict:
        """
        Get statistics about loaded profiles.
        
        Returns:
            Dictionary with profile statistics
        """
        if not self._loaded:
            return {}
        
        scammer_profiles = len([p for p in self.profiles if p.role_preference == "scammer"])
        victim_profiles = len([p for p in self.profiles if p.role_preference == "victim"])
        any_profiles = len([p for p in self.profiles if p.role_preference == "any"])
        
        gender_dist = {}
        age_dist = {}
        
        for profile in self.profiles:
            gender_dist[profile.gender] = gender_dist.get(profile.gender, 0) + 1
            age_dist[profile.age_range] = age_dist.get(profile.age_range, 0) + 1
        
        return {
            'total_profiles': len(self.profiles),
            'role_distribution': {
                'scammer': scammer_profiles,
                'victim': victim_profiles, 
                'any': any_profiles
            },
            'gender_distribution': gender_dist,
            'age_distribution': age_dist
        }
