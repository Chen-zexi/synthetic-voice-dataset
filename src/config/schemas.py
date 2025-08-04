"""
Configuration schema definitions for validating language configurations.
"""

from typing import Dict, List, Any


# Common configuration schema
COMMON_SCHEMA = {
    "followup_turns": {
        "num_turns_lower_limit": int,
        "num_turns_upper_limit": int,
        "sample_limit": int,
        "victim_awareness_levels": List[str]
    },
    "preprocessing": {
        "input_file": str,
        "mapped_suffix": str
    },
    "translation": {
        "service": str,
        "max_lines": int,
        "english_output": str,
        "chinese_code": str,
        "qwen_model": str,
        "qwen_base_url": str,
        "max_concurrent_translations": int
    },
    "multi_turn": {
        "english_output": str,
        "max_conversation": int
    },
    "legit_call": {
        "num_conversations": int
    },
    "voice_generation": {
        "sample_limit": int,
        "model_id": str,
        "output_format": str,
        "voice_speed": float,
        "silence_duration_ms": int,
        "background_volume_reduction_db": int,
        "bandpass_filter": {
            "low_freq": int,
            "high_freq": int
        }
    },
    "post_processing": {
        "scam_label": int,
        "legit_label": int,
        "audio_zip_names": {
            "scam": str,
            "legit": str
        }
    },
    "llm": {
        "provider": str,
        "model": str,
        "max_concurrent_requests": int,
        "temperature": float,
        "max_tokens": (int, type(None)),
        "top_p": float,
        "n": int
    },
    "translation_cache": {
        "enabled": bool,
        "use_cache": bool,
        "cache_dir": str,
        "cache_service": str,
        "force_refresh": bool
    }
}

# Language-specific configuration schema
LANGUAGE_SCHEMA = {
    "language_code": str,
    "language_name": str,
    "region": str,
    "translation": {
        "from_code": str,
        "to_code": str,
        "intermediate_code": str
    },
    "voices": {
        "ids": List[str],
        "names": List[str]
    },
    "placeholder_map": str,
    "legit_call_categories": List[str],
    "output_paths": {
        "scam_conversation": str,
        "legit_conversation": str,
        "scam_audio_dir": str,
        "legit_audio_dir": str,
        "scam_formatted": str,
        "legit_formatted": str
    }
}


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any], path: str = "") -> List[str]:
    """
    Validate data against a schema and return list of validation errors.
    
    Args:
        data: Data to validate
        schema: Schema to validate against
        path: Current path in the data structure (for error messages)
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Check for missing required fields
    for key, expected_type in schema.items():
        if key not in data:
            errors.append(f"Missing required field: {path}.{key}" if path else key)
            continue
        
        value = data[key]
        current_path = f"{path}.{key}" if path else key
        
        # Handle nested dictionaries
        if isinstance(expected_type, dict):
            if not isinstance(value, dict):
                errors.append(f"Expected dict at {current_path}, got {type(value).__name__}")
            else:
                errors.extend(validate_schema(value, expected_type, current_path))
        
        # Handle type checking
        elif expected_type in (str, int, float, bool):
            if not isinstance(value, expected_type):
                errors.append(f"Expected {expected_type.__name__} at {current_path}, got {type(value).__name__}")
        
        # Handle tuple types (for nullable fields)
        elif isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                type_names = [t.__name__ for t in expected_type]
                errors.append(f"Expected one of {type_names} at {current_path}, got {type(value).__name__}")
        
        # Handle list type checking
        elif expected_type == List[str]:
            if not isinstance(value, list):
                errors.append(f"Expected list at {current_path}, got {type(value).__name__}")
            elif not all(isinstance(item, str) for item in value):
                errors.append(f"Expected list of strings at {current_path}")
    
    return errors