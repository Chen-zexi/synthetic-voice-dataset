"""
Seed manager for loading and managing scam conversation seeds from scam_samples.json.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Iterator
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScamSeed(BaseModel):
    """Schema for a scam conversation seed."""
    record_id: int = Field(description="Unique record identifier")
    scam_tag: str = Field(description="Category tag for the scam type")
    scam_category: str = Field(description="High-level category (e.g., 'technology', 'fraud_schemes')")
    scam_summary: str = Field(description="Summary of the scam technique")
    conversation_seed: str = Field(description="Detailed conversation starter/scenario")
    quality_score: int = Field(description="Quality score of the seed (0-100)")


class SeedManager:
    """
    Manages loading and accessing scam conversation seeds from scam_samples.json.
    """
    
    def __init__(self, seeds_file_path: Path):
        """
        Initialize the seed manager.
        
        Args:
            seeds_file_path: Path to the scam_samples.json file
        """
        self.seeds_file_path = seeds_file_path
        self.seeds: Dict[str, ScamSeed] = {}
        self.seeds_by_category: Dict[str, List[ScamSeed]] = {}
        self._loaded = False
        
        # Load seeds on initialization
        self.load_seeds()
    
    def load_seeds(self):
        """Load seeds from the JSON file."""
        if not self.seeds_file_path.exists():
            raise FileNotFoundError(f"Seeds file not found: {self.seeds_file_path}")
        
        logger.info(f"Loading scam seeds from {self.seeds_file_path}")
        
        with open(self.seeds_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract samples by tag
        samples_by_tag = data.get('samples_by_tag', {})
        
        for tag, sample_data in samples_by_tag.items():
            try:
                seed = ScamSeed(**sample_data)
                self.seeds[tag] = seed
                
                # Group by category
                category = seed.scam_category
                if category not in self.seeds_by_category:
                    self.seeds_by_category[category] = []
                self.seeds_by_category[category].append(seed)
                
            except Exception as e:
                logger.warning(f"Failed to parse seed for tag '{tag}': {e}")
        
        logger.info(f"Loaded {len(self.seeds)} scam seeds across {len(self.seeds_by_category)} categories")
        self._loaded = True
    
    def get_seed(self, tag: str) -> Optional[ScamSeed]:
        """
        Get a specific seed by its tag.
        
        Args:
            tag: The scam tag to retrieve
            
        Returns:
            ScamSeed object or None if not found
        """
        return self.seeds.get(tag)
    
    def get_all_seeds(self) -> List[ScamSeed]:
        """
        Get all available seeds.
        
        Returns:
            List of all ScamSeed objects
        """
        return list(self.seeds.values())
    
    def get_seeds_by_category(self, category: str) -> List[ScamSeed]:
        """
        Get all seeds in a specific category.
        
        Args:
            category: The scam category to filter by
            
        Returns:
            List of ScamSeed objects in the category
        """
        return self.seeds_by_category.get(category, [])
    
    def get_categories(self) -> List[str]:
        """
        Get all available scam categories.
        
        Returns:
            List of category names
        """
        return list(self.seeds_by_category.keys())
    
    def get_high_quality_seeds(self, min_quality: int = 80) -> List[ScamSeed]:
        """
        Get seeds with quality score above threshold.
        
        Args:
            min_quality: Minimum quality score threshold
            
        Returns:
            List of high-quality ScamSeed objects
        """
        return [seed for seed in self.seeds.values() if seed.quality_score >= min_quality]
    
    def iter_seeds(self) -> Iterator[ScamSeed]:
        """
        Iterate through all seeds.
        
        Returns:
            Iterator over ScamSeed objects
        """
        return iter(self.seeds.values())
    
    def get_stats(self) -> Dict:
        """
        Get statistics about loaded seeds.
        
        Returns:
            Dictionary with seed statistics
        """
        if not self._loaded:
            return {}
        
        quality_scores = [seed.quality_score for seed in self.seeds.values()]
        
        return {
            'total_seeds': len(self.seeds),
            'categories': len(self.seeds_by_category),
            'category_distribution': {cat: len(seeds) for cat, seeds in self.seeds_by_category.items()},
            'quality_stats': {
                'min': min(quality_scores) if quality_scores else 0,
                'max': max(quality_scores) if quality_scores else 0,
                'avg': sum(quality_scores) / len(quality_scores) if quality_scores else 0
            }
        }
