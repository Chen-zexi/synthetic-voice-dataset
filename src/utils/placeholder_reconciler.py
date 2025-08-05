"""
Placeholder reconciliation utility to map dynamic placeholders to pre-populated substitutions.

This module handles the mismatch between dynamically generated placeholder codes
(from preprocessing) and pre-populated placeholder mappings (locale-specific).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class PlaceholderReconciler:
    """
    Reconciles dynamic placeholder mappings with pre-populated locale-specific mappings.
    
    The issue: preprocessing dynamically assigns codes like {00001}, {00002} based on
    order of appearance in source text. Pre-populated mappings assume a different ordering.
    This class creates a reconciled mapping that uses dynamic codes with correct substitutions.
    """
    
    def __init__(self, dynamic_map_path: Path, prepopulated_map_path: Path):
        """
        Initialize the reconciler with paths to both mapping files.
        
        Args:
            dynamic_map_path: Path to dynamic placeholder map from preprocessing
            prepopulated_map_path: Path to pre-populated locale-specific placeholders
        """
        self.dynamic_map_path = dynamic_map_path
        self.prepopulated_map_path = prepopulated_map_path
        self._dynamic_map = None
        self._prepopulated_map = None
        self._reconciled_map = None
    
    def load_maps(self) -> Tuple[Dict, Dict]:
        """
        Load both mapping files.
        
        Returns:
            Tuple of (dynamic_map, prepopulated_map)
        """
        with open(self.dynamic_map_path, 'r', encoding='utf-8') as f:
            self._dynamic_map = json.load(f)
            
        with open(self.prepopulated_map_path, 'r', encoding='utf-8') as f:
            self._prepopulated_map = json.load(f)
            
        return self._dynamic_map, self._prepopulated_map
    
    def reconcile(self) -> Dict[str, Dict]:
        """
        Create reconciled mapping that uses dynamic codes with correct substitutions.
        
        Returns:
            Reconciled mapping dictionary
        """
        if not self._dynamic_map or not self._prepopulated_map:
            self.load_maps()
        
        # Create tag-to-prepopulated-data mapping
        tag_to_data = {}
        for code, data in self._prepopulated_map.items():
            tag = data.get('tag')
            if tag:
                tag_to_data[tag] = data
        
        # Build reconciled map using dynamic codes
        reconciled = {}
        missing_tags = []
        
        for dynamic_code, dynamic_data in self._dynamic_map.items():
            tag = dynamic_data.get('tag')
            
            if tag in tag_to_data:
                # Found matching tag in pre-populated data
                prepop_data = tag_to_data[tag]
                reconciled[dynamic_code] = {
                    'tag': tag,
                    'substitutions': prepop_data.get('substitutions', []),
                    'translations': prepop_data.get('translations', []),
                    'description': prepop_data.get('description', '')
                }
                logger.debug(f"Reconciled {dynamic_code} -> {tag}")
            else:
                # Tag not found in pre-populated data
                missing_tags.append(f"{dynamic_code}:{tag}")
                reconciled[dynamic_code] = dynamic_data
                logger.warning(f"No pre-populated data for {dynamic_code}:{tag}")
        
        if missing_tags:
            logger.warning(f"Tags missing from pre-populated map: {', '.join(missing_tags[:5])}")
            if len(missing_tags) > 5:
                logger.warning(f"... and {len(missing_tags) - 5} more")
        
        self._reconciled_map = reconciled
        return reconciled
    
    def validate_reconciliation(self) -> bool:
        """
        Validate the reconciled mapping for completeness and correctness.
        
        Returns:
            True if validation passes, False otherwise
        """
        if not self._reconciled_map:
            logger.error("No reconciled map to validate")
            return False
        
        issues = []
        
        # Check for empty substitutions
        for code, data in self._reconciled_map.items():
            if not data.get('substitutions'):
                issues.append(f"{code} has no substitutions")
        
        # Log validation results
        if issues:
            logger.warning(f"Validation issues found: {len(issues)}")
            for issue in issues[:10]:
                logger.warning(f"  - {issue}")
            if len(issues) > 10:
                logger.warning(f"  ... and {len(issues) - 10} more")
            return False
        
        logger.info("Placeholder reconciliation validation passed")
        return True
    
    def save_reconciled_map(self, output_path: Optional[Path] = None) -> Path:
        """
        Save the reconciled mapping to a file.
        
        Args:
            output_path: Path to save reconciled map (optional)
            
        Returns:
            Path where the file was saved
        """
        if not self._reconciled_map:
            raise ValueError("No reconciled map to save. Run reconcile() first.")
        
        if not output_path:
            # Save alongside dynamic map
            output_path = self.dynamic_map_path.parent / "reconciled_placeholder_map.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self._reconciled_map, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved reconciled map to {output_path}")
        return output_path
    
    def get_reconciled_map(self) -> Dict[str, Dict]:
        """
        Get the reconciled mapping, creating it if necessary.
        
        Returns:
            Reconciled mapping dictionary
        """
        if not self._reconciled_map:
            self.reconcile()
        return self._reconciled_map


def reconcile_placeholders(dynamic_map_path: Path, prepopulated_map_path: Path) -> Dict[str, Dict]:
    """
    Convenience function to reconcile placeholder mappings.
    
    Args:
        dynamic_map_path: Path to dynamic placeholder map
        prepopulated_map_path: Path to pre-populated placeholders
        
    Returns:
        Reconciled mapping dictionary
    """
    reconciler = PlaceholderReconciler(dynamic_map_path, prepopulated_map_path)
    return reconciler.reconcile()