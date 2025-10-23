"""
Seed manager for loading and managing scam conversation seeds.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScamSeed(BaseModel):
    """
    Schema for a scam conversation seed.
    """
    seed_id: str = Field(description="Unique seed identifier")
    scam_tag: str = Field(description="Category tag for the scam type")
    scam_category: str = Field(description="High-level category (e.g., 'technology', 'banking')")
    scam_summary: str = Field(description="Summary of the scam technique")
    conversation_seed: str = Field(description="Detailed conversation starter/scenario")
    quality_score: Optional[int] = Field(default=80, description="Quality score of the seed (0-100)")
    placeholders: Optional[List[str]] = Field(default_factory=list, description="List of placeholder tags")
    processing_notes: Optional[str] = Field(default="", description="Processing notes")


class SeedManager:
    """
    Manages loading and accessing scam conversation seeds from JSON.
    Simplified to work directly with the current seed format.
    """
    
    def __init__(self, seeds_file_path: Path):
        """
        Initialize the seed manager.

        Args:
            seeds_file_path: Path to the seeds JSON file
        """
        self.seeds_file_path = seeds_file_path
        self.seeds: List[ScamSeed] = []
        self.seeds_by_category: Dict[str, List[ScamSeed]] = {}
        self.seeds_by_tag: Dict[str, ScamSeed] = {}
        self._loaded = False

        # Load seeds on initialization
        self.load_seeds()
    
    def load_seeds(self):
        """
        Load seeds from the JSON file (array format).
        """
        if not self.seeds_file_path.exists():
            raise FileNotFoundError(f"Seeds file not found: {self.seeds_file_path}")
        
        logger.debug(f"Loading scam seeds from {self.seeds_file_path}")
        
        with open(self.seeds_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both array format and object format
        if isinstance(data, list):
            # Direct array of seeds (current format)
            seed_list = data
        elif isinstance(data, dict) and 'samples_by_tag' in data:
            # Old format with samples_by_tag
            seed_list = list(data['samples_by_tag'].values())
        else:
            # Assume it's a direct list
            seed_list = data if isinstance(data, list) else []
        
        for seed_data in seed_list:
            try:
                # Convert quality_score to int if it's a string
                if 'quality_score' in seed_data and isinstance(seed_data['quality_score'], str):
                    seed_data['quality_score'] = int(seed_data['quality_score'])
                
                # Ensure placeholders is a list
                if 'placeholders' not in seed_data:
                    seed_data['placeholders'] = []
                
                seed = ScamSeed(**seed_data)
                self.seeds.append(seed)
                
                # Index by tag for quick lookup
                self.seeds_by_tag[seed.scam_tag] = seed
                
                # Group by category
                category = seed.scam_category
                if category not in self.seeds_by_category:
                    self.seeds_by_category[category] = []
                self.seeds_by_category[category].append(seed)
                
            except Exception as e:
                logger.warning(f"Failed to parse seed: {e}")
                logger.debug(f"Problematic seed data: {seed_data}")
        
        logger.debug(f"Loaded {len(self.seeds)} scam seeds across {len(self.seeds_by_category)} categories")
        self._loaded = True
    
    def get_all_seeds(self) -> List[ScamSeed]:
        """
        Get all available seeds.
        
        Returns:
            List of all ScamSeed objects
        """
        return self.seeds
    
    def get_seeds_by_category(self, category: str) -> List[ScamSeed]:
        """
        Get all seeds in a specific category.
        
        Args:
            category: The scam category to filter by
            
        Returns:
            List of ScamSeed objects in the category
        """
        return self.seeds_by_category.get(category, [])
    
    def get_high_quality_seeds(self, min_quality: int = 70) -> List[ScamSeed]:
        """
        Get seeds with quality score above threshold.
        
        Args:
            min_quality: Minimum quality score threshold
            
        Returns:
            List of high-quality ScamSeed objects
        """
        return [seed for seed in self.seeds if seed.quality_score >= min_quality]
    
    def filter_and_limit_seeds(self, min_quality: Optional[int] = None,
                              limit: Optional[int] = None) -> List[ScamSeed]:
        """
        Filter seeds by quality and limit the number returned.

        Args:
            min_quality: Minimum quality score (if None, no filtering)
            limit: Maximum number of seeds to return

        Returns:
            Filtered and limited list of seeds
        """
        seeds = self.seeds

        # Filter by quality if specified
        if min_quality is not None:
            seeds = [s for s in seeds if s.quality_score >= min_quality]
            logger.debug(f"Filtered to {len(seeds)} seeds with quality >= {min_quality}")

        # Apply limit if specified
        if limit is not None and limit < len(seeds):
            seeds = seeds[:limit]
            logger.debug(f"Limited to {limit} seeds")

        return seeds
    
    def get_stats(self) -> Dict:
        """
        Get statistics about loaded seeds.
        
        Returns:
            Dictionary with seed statistics
        """
        if not self._loaded or not self.seeds:
            return {}
        
        quality_scores = [seed.quality_score for seed in self.seeds]
        
        return {
            'total_seeds': len(self.seeds),
            'categories': len(self.seeds_by_category),
            'category_distribution': {cat: len(seeds) for cat, seeds in self.seeds_by_category.items()},
            'quality_stats': {
                'min': min(quality_scores),
                'max': max(quality_scores),
                'avg': sum(quality_scores) / len(quality_scores)
            }
        }