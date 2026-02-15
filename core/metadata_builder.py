"""
Unified Metadata Builder for all generators.

This module provides standardized metadata generation for task deduplication,
parameter tracking, and reproducibility.

Version: 1.0
Author: VBVR-DataFactory Team
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional


# Black list: keys that should not appear in parameters
SKIP_KEYS = {
    'temp_path', 'temp_dir', 'temp_file',
    'video_temp_path', 'image_temp_path', 
    'cache_path', 'cache_dir',
    '_cache', '_internal', '_temp', '_tmp',
    'seed', 'random_seed',
    'tmp', 'tmpdir',
}


def build_metadata(
    task_id: str,
    generator_name: str,
    parameters: Dict[str, Any],
    seed: Optional[int] = None,
    generator_version: str = "1.0"
) -> Dict[str, Any]:
    """
    Build standardized metadata for a task.
    
    Args:
        task_id: Unique task identifier (e.g., "shape_scaling_00000001")
        generator_name: Name of the generator (domain)
        parameters: Task parameters dict (from _generate_task_data())
        seed: Random seed used for generation (does not affect param_hash)
        generator_version: Version of the generator
    
    Returns:
        Standardized metadata dict with all required fields
    
    Example:
        >>> metadata = build_metadata(
        ...     task_id="shape_scaling_00000001",
        ...     generator_name="O-9_shape_scaling_data-generator",
        ...     parameters={"shape": "circle", "scale": 1.5, "color": [255, 0, 0]},
        ...     seed=42
        ... )
        >>> metadata["param_hash"]
        'a1b2c3d4e5f6g7h8'
    """
    # Clean and normalize parameters
    clean_params = _clean_parameters(parameters)
    
    # Compute hash for deduplication (seed is NOT included)
    param_hash = _compute_param_hash(clean_params)
    
    return {
        "version": "1.0",
        "task_id": task_id,
        "generator": generator_name,
        "timestamp": datetime.now().isoformat(),
        "parameters": clean_params,
        "param_hash": param_hash,
        "generation": {
            "seed": seed,
            "generator_version": generator_version
        }
    }


def _clean_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean parameters by removing non-serializable and unnecessary keys.
    
    Args:
        params: Raw parameters dict
    
    Returns:
        Cleaned parameters dict (JSON serializable)
    """
    clean = {}
    
    for key, value in params.items():
        # Skip blacklisted keys
        if any(skip in key.lower() for skip in SKIP_KEYS):
            continue
        
        # Serialize value
        serialized = _serialize_value(value)
        if serialized is not None:
            clean[key] = serialized
    
    return clean


def _serialize_value(value: Any) -> Any:
    """
    Convert any Python value to JSON-serializable format.
    
    Args:
        value: Any Python object
    
    Returns:
        JSON-serializable representation, or None if cannot serialize
    """
    # Primitive types
    if isinstance(value, (str, int, bool, type(None))):
        return value
    
    # Float: normalize precision to 6 decimal places
    if isinstance(value, float):
        return round(value, 6)
    
    # List/Tuple: recursively serialize items
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    
    # Dict: recursively serialize keys and values
    if isinstance(value, dict):
        # Convert tuple keys to strings (e.g., (1, 2) -> "(1, 2)")
        serialized_dict = {}
        for k, v in value.items():
            if isinstance(k, tuple):
                key_str = str(k)
            else:
                key_str = _serialize_value(k) if not isinstance(k, (str, int, bool, type(None))) else k
            serialized_dict[key_str] = _serialize_value(v)
        return serialized_dict
        # Old code below (replaced)
        return {k: _serialize_value(v) for k, v in value.items()}
    
    # Object with __dict__: try to extract useful attributes
    if hasattr(value, '__dict__'):
        obj_dict = {}
        # Try common attribute names
        for attr in ['name', 'type', 'id', 'value', 'label']:
            if hasattr(value, attr):
                attr_value = getattr(value, attr)
                serialized = _serialize_value(attr_value)
                if serialized is not None:
                    obj_dict[attr] = serialized
        
        if obj_dict:
            obj_dict['_type'] = type(value).__name__
            return obj_dict
        else:
            # Fallback: just type name
            return {"_type": type(value).__name__}
    
    # Fallback: type name as string
    return type(value).__name__


def _compute_param_hash(params: Dict[str, Any]) -> str:
    """
    Compute deterministic hash for parameters.
    
    The hash is used for deduplication: same parameters → same hash.
    Uses SHA256 and returns first 16 characters.
    
    Args:
        params: Cleaned parameters dict
    
    Returns:
        16-character hash string
    """
    # Convert to canonical JSON string (sorted keys)
    param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
    
    # Compute SHA256 hash
    hash_obj = hashlib.sha256(param_str.encode('utf-8'))
    
    # Return first 16 characters
    return hash_obj.hexdigest()[:16]


def verify_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Verify that metadata has all required fields and correct format.
    
    Args:
        metadata: Metadata dict to verify
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'version', 'task_id', 'generator', 'timestamp', 
        'parameters', 'param_hash', 'generation'
    ]
    
    # Check all required fields exist
    for field in required_fields:
        if field not in metadata:
            return False
    
    # Check param_hash format (16 characters)
    if not isinstance(metadata['param_hash'], str) or len(metadata['param_hash']) != 16:
        return False
    
    # Check parameters is a dict
    if not isinstance(metadata['parameters'], dict):
        return False
    
    # Check generation has seed
    if 'seed' not in metadata['generation']:
        return False
    
    return True


if __name__ == "__main__":
    # Example usage
    example_metadata = build_metadata(
        task_id="shape_scaling_00000001",
        generator_name="O-9_shape_scaling_data-generator",
        parameters={
            "shape_a": "circle",
            "shape_c": "square",
            "scale_factor": 1.5,
            "color": [255, 0, 0],
            "position": (100, 200),
            "seed": 42  # Will be filtered out
        },
        seed=42
    )
    
    print("Example Metadata:")
    print(json.dumps(example_metadata, indent=2, ensure_ascii=False))
    print("\nVerification:", verify_metadata(example_metadata))
