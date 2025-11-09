"""Configuration management for bias analysis prompts."""

from pathlib import Path
from typing import Dict, List

import yaml
from fastapi import HTTPException


def load_prompts_config() -> List[Dict[str, str]]:
    """
    Load and parse prompts.yaml configuration file.

    Returns:
        List of dimension configurations, each with 'name' and 'prompt' fields

    Raises:
        HTTPException: 500 if config file cannot be loaded
    """
    config_path = Path(__file__).parent / "prompts.yaml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if not config or "dimensions" not in config:
            raise HTTPException(
                status_code=500, detail="Invalid prompts.yaml: missing 'dimensions' key"
            )

        dimensions = config["dimensions"]
        if not isinstance(dimensions, list) or len(dimensions) == 0:
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'dimensions' must be a non-empty list",
            )

        # Validate each dimension has required fields
        for dim in dimensions:
            if not isinstance(dim, dict) or "name" not in dim or "prompt" not in dim:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid prompts.yaml: each dimension must have 'name' and 'prompt' fields",
                )

        return dimensions

    except FileNotFoundError:
        raise HTTPException(
            status_code=500, detail=f"Configuration file not found: {config_path}"
        )
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=500, detail=f"Error parsing prompts.yaml: {str(e)}"
        )


# Cache the prompts config at module level
_PROMPTS_CONFIG = None


def get_prompts_config() -> List[Dict[str, str]]:
    """Get cached prompts configuration, loading it if necessary."""
    global _PROMPTS_CONFIG
    if _PROMPTS_CONFIG is None:
        _PROMPTS_CONFIG = load_prompts_config()
    return _PROMPTS_CONFIG
