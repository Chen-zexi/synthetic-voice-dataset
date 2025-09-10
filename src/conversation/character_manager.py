"""
Character profile manager for creating diverse conversation participants.
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional, Literal, Union, Tuple
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
    victim_awareness: str = Field(description="Victim's awareness level (not/tiny/very)")
    num_turns: int = Field(description="Number of dialogue turns")


class CharacterManager:
    """
    Manages character profiles and creates generation scenarios.
    """
    
    def __init__(self, character_profiles_path: Optional[Path] = None, 
                 voice_profiles_path: Optional[Union[Path, Dict]] = None,
                 victim_awareness_levels: Optional[List[str]] = None,
                 num_turns_range: Optional[Tuple[int, int]] = None,
                 scenario_templates_path: Optional[Path] = None,
                 scenario_assignments_path: Optional[Path] = None):
        """
        Initialize the character manager.
        
        Args:
            character_profiles_path: Path to character profiles JSON file
            voice_profiles_path: Path to voice profiles JSON file for locale-specific voice mappings
            victim_awareness_levels: List of possible victim awareness levels (weighted)
            num_turns_range: Tuple of (min, max) for number of turns
            scenario_templates_path: Path to pre-configured scenario templates
            scenario_assignments_path: Path to seed-to-template assignments
        """
        self.character_profiles_path = character_profiles_path
        self.voice_profiles_path = voice_profiles_path
        self.profiles: List[CharacterProfile] = []
        self.voice_mappings: Dict[str, str] = {}  # profile_id -> voice_name
        self._loaded = False
        
        # Pre-configured scenarios
        self.scenario_templates: Dict[str, Dict] = {}  # template_id -> template data
        self.scenario_assignments: Dict[str, List[str]] = {}  # seed_id -> template_ids
        self.scenario_templates_path = scenario_templates_path
        self.scenario_assignments_path = scenario_assignments_path
        
        # Conversation parameter configuration (for fallback/random mode)
        self.victim_awareness_levels = victim_awareness_levels or ["not", "not", "not", "not", "not", "tiny", "very"]
        self.num_turns_range = num_turns_range or (7, 10)
        
        # Load profiles if path provided
        if character_profiles_path:
            self.load_profiles()
        else:
            # Create default profiles
            self.create_default_profiles()
        
        # Load voice mappings if path provided
        if voice_profiles_path:
            self.load_voice_mappings()
        
        # Load pre-configured scenarios if available
        if scenario_templates_path and scenario_assignments_path:
            self.load_scenario_templates()
            self.load_scenario_assignments()
    
    def load_profiles(self):
        """Load character profiles from JSON file."""
        if not self.character_profiles_path or not self.character_profiles_path.exists():
            logger.warning(f"Character profiles file not found: {self.character_profiles_path}")
            self.create_default_profiles()
            return
        
        logger.debug(f"Loading character profiles from {self.character_profiles_path}")
        
        with open(self.character_profiles_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        profiles_data = data.get('profiles', [])
        
        for profile_data in profiles_data:
            try:
                profile = CharacterProfile(**profile_data)
                self.profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to parse character profile: {e}")
        
        logger.debug(f"Loaded {len(self.profiles)} character profiles")
        self._loaded = True
    
    def create_default_profiles(self):
        """Create default character profiles for immediate use."""
        logger.debug("Creating default character profiles")
        
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
        
        logger.debug(f"Created {len(self.profiles)} default character profiles")
        self._loaded = True
    
    def load_voice_mappings(self):
        """
        Load character-to-voice mappings from voice profiles JSON or dict.
        """
        if not self.voice_profiles_path:
            logger.debug("No voice profiles path provided")
            return
            
        # Handle both Path objects and dicts
        if isinstance(self.voice_profiles_path, dict):
            # Already loaded as dict from config
            data = self.voice_profiles_path
        elif isinstance(self.voice_profiles_path, Path):
            # Load from file path
            if not self.voice_profiles_path.exists():
                logger.debug(f"Voice profiles file not found: {self.voice_profiles_path}")
                return
            try:
                with open(self.voice_profiles_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load voice profiles file: {e}")
                return
        else:
            logger.debug(f"Unexpected voice_profiles_path type: {type(self.voice_profiles_path)}")
            return
        
        # Load character voice mappings if present
        if 'character_voice_mappings' in data:
            self.voice_mappings = data['character_voice_mappings']
            logger.debug(f"Loaded voice mappings for {len(self.voice_mappings)} character profiles")
        else:
            logger.debug("No character_voice_mappings found in voice profiles")
    
    def load_scenario_templates(self):
        """
        Load pre-configured scenario templates from JSON file.
        """
        if not self.scenario_templates_path or not self.scenario_templates_path.exists():
            logger.debug(f"Scenario templates file not found: {self.scenario_templates_path}")
            return
        
        logger.debug(f"Loading scenario templates from {self.scenario_templates_path}")
        
        try:
            with open(self.scenario_templates_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Build template dictionary for quick lookup
            for template in data.get('templates', []):
                template_id = template.get('template_id')
                if template_id:
                    self.scenario_templates[template_id] = template
            
            logger.debug(f"Loaded {len(self.scenario_templates)} scenario templates")
        except Exception as e:
            logger.warning(f"Failed to load scenario templates: {e}")
    
    def load_scenario_assignments(self):
        """
        Load seed-to-template assignments from JSON file.
        """
        if not self.scenario_assignments_path or not self.scenario_assignments_path.exists():
            logger.debug(f"Scenario assignments file not found: {self.scenario_assignments_path}")
            return
        
        logger.debug(f"Loading scenario assignments from {self.scenario_assignments_path}")
        
        try:
            with open(self.scenario_assignments_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.scenario_assignments = data.get('seed_scenarios', {})
            logger.debug(f"Loaded assignments for {len(self.scenario_assignments)} seeds")
        except Exception as e:
            logger.warning(f"Failed to load scenario assignments: {e}")
    
    def get_profile_by_id(self, profile_id: str) -> Optional[CharacterProfile]:
        """
        Get a character profile by its ID.
        
        Args:
            profile_id: Character profile ID
            
        Returns:
            CharacterProfile object or None if not found
        """
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                return profile
        return None
    
    def get_voice_for_profile(self, profile_id: str) -> Optional[str]:
        """
        Get the voice name mapped to a character profile.
        
        Args:
            profile_id: Character profile ID
            
        Returns:
            Voice name if mapped, None otherwise
        """
        return self.voice_mappings.get(profile_id)
    
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
    
    def create_from_template(self, template_id: str, seed_tag: str, locale: str, seed_id: str = "") -> Optional[GenerationScenario]:
        """
        Create a scenario from a pre-configured template.
        
        Args:
            template_id: Template ID to use
            seed_tag: The scam tag being used
            locale: Target locale
            seed_id: Seed ID for scenario naming
            
        Returns:
            GenerationScenario object or None if creation failed
        """
        if template_id not in self.scenario_templates:
            logger.warning(f"Template {template_id} not found")
            return None
        
        template = self.scenario_templates[template_id]
        
        # Get profile objects
        scammer_profile = self.get_profile_by_id(template['scammer_profile_id'])
        victim_profile = self.get_profile_by_id(template['victim_profile_id'])
        
        if not scammer_profile or not victim_profile:
            logger.warning(f"Could not find profiles for template {template_id}")
            return None
        
        # Create scenario with template parameters
        scenario_id = f"{seed_id}_{template_id}" if seed_id else template_id
        
        return GenerationScenario(
            scenario_id=scenario_id,
            seed_tag=seed_tag,
            scammer_profile=scammer_profile,
            victim_profile=victim_profile,
            locale=locale,
            victim_awareness=template['victim_awareness'],
            num_turns=template['num_turns']
        )
    
    def get_scenarios_for_seed(self, seed_id: str, seed_tag: str, locale: str, count: int = 1) -> List[GenerationScenario]:
        """
        Get pre-assigned scenarios for a seed.
        
        Args:
            seed_id: Seed ID to get scenarios for
            seed_tag: The scam tag being used
            locale: Target locale
            count: Number of scenarios to return
            
        Returns:
            List of GenerationScenario objects
        """
        scenarios = []
        
        # Check if we have pre-configured assignments
        if self.scenario_assignments and seed_id in self.scenario_assignments:
            template_ids = self.scenario_assignments[seed_id][:count]
            
            for template_id in template_ids:
                scenario = self.create_from_template(template_id, seed_tag, locale, seed_id)
                if scenario:
                    scenarios.append(scenario)
            
            if scenarios:
                logger.debug(f"Using pre-configured scenarios for seed {seed_id}: {template_ids}")
                return scenarios
        
        # Fallback to random scenario creation
        logger.debug(f"No pre-configured scenarios for seed {seed_id}, using random generation")
        for i in range(count):
            scenario = self.create_scenario(seed_tag, locale, f"{seed_id}_{i+1}")
            if scenario:
                scenarios.append(scenario)
        
        return scenarios
    
    def create_scenario(self, seed_tag: str, locale: str, scenario_id: Optional[str] = None) -> Optional[GenerationScenario]:
        """
        Create a generation scenario by combining seed with character profiles and conversation parameters.
        
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
        
        # Select conversation parameters (affected by random seed)
        victim_awareness = random.choice(self.victim_awareness_levels)
        num_turns = random.randint(self.num_turns_range[0], self.num_turns_range[1])
        
        # Generate scenario ID
        if not scenario_id:
            scenario_id = f"{seed_tag}_{scammer_profile.profile_id}_{victim_profile.profile_id}_{locale}"
        
        return GenerationScenario(
            scenario_id=scenario_id,
            seed_tag=seed_tag,
            scammer_profile=scammer_profile,
            victim_profile=victim_profile,
            locale=locale,
            victim_awareness=victim_awareness,
            num_turns=num_turns
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
        
        logger.debug(f"Created {len(scenarios)} scenarios from {len(seed_tags)} seed tags")
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
