"""
Tag extraction module for preprocessing Chinese scam text.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, Tuple

from config.config_loader import Config


logger = logging.getLogger(__name__)


class TagExtractor:
    """
    Extracts placeholder tags from Chinese text and creates mapping files.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the tag extractor.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.tag_pattern = re.compile(r'<[^>]+>')
    
    def extract_tags(self) -> Tuple[Dict[str, str], Dict[str, Dict]]:
        """
        Extract tags from input file and create placeholder mappings.
        
        Returns:
            Tuple of (tag_to_code_mapping, code_to_info_mapping)
        """
        logger.info(f"Extracting tags from {self.config.preprocessing_input_path}")
        
        # Initialize mappings
        tag_to_code = {}
        code_to_info = {}
        
        # Process input file
        with open(self.config.preprocessing_input_path, 'r', encoding='utf-8') as infile, \
             open(self.config.preprocessing_output_path, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                # Replace tags with codes
                processed_line = self._process_line(line, tag_to_code, code_to_info)
                outfile.write(processed_line)
                
                if line_num % 100 == 0:
                    logger.debug(f"Processed {line_num} lines")
        
        # Save mapping to JSON
        self._save_mapping(code_to_info)
        
        logger.info(f"Extracted {len(tag_to_code)} unique tags")
        logger.info(f"Output written to {self.config.preprocessing_output_path}")
        logger.info(f"Mapping saved to {self.config.preprocessing_map_path}")
        
        return tag_to_code, code_to_info
    
    def _process_line(self, line: str, tag_to_code: Dict[str, str], 
                      code_to_info: Dict[str, Dict]) -> str:
        """
        Process a single line, replacing tags with codes.
        
        Args:
            line: Input line
            tag_to_code: Mapping from tags to codes
            code_to_info: Mapping from codes to tag info
            
        Returns:
            Processed line with tags replaced by codes
        """
        def replace_tag(match):
            tag = match.group(0)
            
            # Get or create code for this tag
            if tag not in tag_to_code:
                code = f"{{{len(tag_to_code) + 1:05d}}}"
                tag_to_code[tag] = code
                code_to_info[code] = {
                    "tag": tag,
                    "substitutions": [],
                    "translations": []
                }
                logger.debug(f"New tag found: {tag} -> {code}")
            
            return tag_to_code[tag]
        
        return self.tag_pattern.sub(replace_tag, line)
    
    def _save_mapping(self, code_to_info: Dict[str, Dict]):
        """
        Save the code-to-info mapping to JSON file.
        
        This creates a dynamic mapping file in the output directory that tracks
        what placeholders were actually found in the source data.
        
        Args:
            code_to_info: Mapping to save
        """
        # Save the dynamic mapping to output directory
        dynamic_map_path = self.config.output_dir / "intermediate" / "preprocessed" / "dynamic_placeholder_map.json"
        dynamic_map_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dynamic_map_path, 'w', encoding='utf-8') as f:
            json.dump(code_to_info, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved dynamic mapping to {dynamic_map_path}")
        
        # Also validate against pre-populated map if it exists
        if self.config.preprocessing_map_path.exists():
            self._validate_against_prepopulated_map(code_to_info)
    
    def validate_mapping(self) -> bool:
        """
        Validate that the mapping file has proper substitutions for all codes.
        
        Returns:
            True if mapping is valid, False otherwise
        """
        if not self.config.preprocessing_map_path.exists():
            logger.error(f"Mapping file not found: {self.config.preprocessing_map_path}")
            return False
        
        with open(self.config.preprocessing_map_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        missing_substitutions = []
        for code, info in mapping.items():
            if not info.get('substitutions'):
                missing_substitutions.append(code)
        
        if missing_substitutions:
            logger.warning(f"Codes missing substitutions: {', '.join(missing_substitutions[:5])}")
            if len(missing_substitutions) > 5:
                logger.warning(f"... and {len(missing_substitutions) - 5} more")
            return False
        
        logger.info("Mapping validation passed")
        return True
    
    def _validate_against_prepopulated_map(self, dynamic_mapping: Dict[str, Dict]):
        """
        Validate dynamic mapping against pre-populated map.
        
        Args:
            dynamic_mapping: The dynamically generated mapping
        """
        try:
            with open(self.config.preprocessing_map_path, 'r', encoding='utf-8') as f:
                prepopulated_map = json.load(f)
            
            # Check for missing entries in pre-populated map
            missing_in_prepopulated = []
            for code, info in dynamic_mapping.items():
                if code not in prepopulated_map:
                    missing_in_prepopulated.append(f"{code} ({info['tag']})")
            
            # Check for extra entries in pre-populated map
            extra_in_prepopulated = []
            for code in prepopulated_map:
                if code not in dynamic_mapping:
                    extra_in_prepopulated.append(code)
            
            # Report findings
            if missing_in_prepopulated:
                logger.warning(f"Tags found in source but missing in pre-populated map: {', '.join(missing_in_prepopulated)}")
                logger.warning("Consider adding these to the pre-populated map with appropriate substitutions")
            
            if extra_in_prepopulated:
                logger.info(f"Tags in pre-populated map but not in source: {', '.join(extra_in_prepopulated)}")
                logger.info("These may be used in other source files or can be removed if obsolete")
            
            if not missing_in_prepopulated and not extra_in_prepopulated:
                logger.info("Pre-populated map is in sync with source tags")
                
        except Exception as e:
            logger.error(f"Could not validate against pre-populated map: {e}")