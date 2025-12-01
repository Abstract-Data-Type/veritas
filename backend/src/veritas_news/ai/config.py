"""Configuration management for bias analysis prompts."""

from pathlib import Path
from typing import Any

from fastapi import HTTPException
import yaml


def load_prompts_config() -> list[dict[str, str]]:
    """
    Load and parse prompts.yaml configuration file.

    Returns:
        List of dimension configurations, each with 'name' and 'prompt' fields

    Raises:
        HTTPException: 500 if config file cannot be loaded
    """
    config_path = Path(__file__).parent / "prompts.yaml"

    try:
        with open(config_path) as f:
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


def get_prompts_config() -> list[dict[str, str]]:
    """Get cached prompts configuration, loading it if necessary."""
    global _PROMPTS_CONFIG
    if _PROMPTS_CONFIG is None:
        _PROMPTS_CONFIG = load_prompts_config()
    return _PROMPTS_CONFIG


def load_summarization_prompt_template() -> str:
    """
    Load the summarization prompt template from prompts.yaml.

    Returns:
        The prompt template string with {article_text} placeholder

    Raises:
        HTTPException: 500 if config file cannot be loaded or template missing
    """
    config_path = Path(__file__).parent / "prompts.yaml"

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not config or "summarization" not in config:
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: missing 'summarization' key",
            )

        summarization_config = config["summarization"]
        if not isinstance(summarization_config, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'summarization' must be a dictionary",
            )

        template = summarization_config.get("prompt_template")
        if not template or not isinstance(template, str):
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'summarization.prompt_template' must be a non-empty string",
            )

        return template

    except FileNotFoundError:
        raise HTTPException(
            status_code=500, detail=f"Configuration file not found: {config_path}"
        )
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=500, detail=f"Error parsing prompts.yaml: {str(e)}"
        )


# Cache the summarization prompt template at module level
_SUMMARIZATION_PROMPT_TEMPLATE = None


def get_summarization_prompt_template() -> str:
    """Get cached summarization prompt template, loading it if necessary."""
    global _SUMMARIZATION_PROMPT_TEMPLATE
    if _SUMMARIZATION_PROMPT_TEMPLATE is None:
        _SUMMARIZATION_PROMPT_TEMPLATE = load_summarization_prompt_template()
    return _SUMMARIZATION_PROMPT_TEMPLATE


def load_secm_config() -> dict[str, Any]:
    """
    Load SECM configuration from prompts.yaml.
    
    Returns:
        Dictionary containing:
        - epsilon: float (smoothing factor)
        - variables: List of all 22 variable configurations with 'name' and 'prompt'
    
    Raises:
        HTTPException: 500 if config file cannot be loaded or invalid
    """
    config_path = Path(__file__).parent / "prompts.yaml"
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        if not config or "secm" not in config:
            raise HTTPException(
                status_code=500, detail="Invalid prompts.yaml: missing 'secm' key"
            )
        
        secm_config = config["secm"]
        if not isinstance(secm_config, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'secm' must be a dictionary",
            )
        
        # Extract K damping constant (default to 4.0 if not specified)
        k = secm_config.get("k", 4.0)
        if not isinstance(k, (int, float)) or k <= 0:
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'secm.k' must be a positive number",
            )
        
        # Collect all variables from all clusters
        variables = []
        
        # Ideological left markers
        ideol_left = secm_config.get("ideological_variables", {}).get("left_markers", [])
        if not isinstance(ideol_left, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'secm.ideological_variables.left_markers' must be a list",
            )
        variables.extend(ideol_left)
        
        # Ideological right markers
        ideol_right = secm_config.get("ideological_variables", {}).get("right_markers", [])
        if not isinstance(ideol_right, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'secm.ideological_variables.right_markers' must be a list",
            )
        variables.extend(ideol_right)
        
        # Epistemic high integrity markers
        epist_high = secm_config.get("epistemic_variables", {}).get("high_integrity", [])
        if not isinstance(epist_high, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'secm.epistemic_variables.high_integrity' must be a list",
            )
        variables.extend(epist_high)
        
        # Epistemic low integrity markers
        epist_low = secm_config.get("epistemic_variables", {}).get("low_integrity", [])
        if not isinstance(epist_low, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid prompts.yaml: 'secm.epistemic_variables.low_integrity' must be a list",
            )
        variables.extend(epist_low)
        
        # Validate we have exactly 22 variables
        if len(variables) != 22:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid prompts.yaml: Expected 22 SECM variables, found {len(variables)}",
            )
        
        # Validate each variable has required fields
        for var in variables:
            if not isinstance(var, dict) or "name" not in var or "prompt" not in var:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid prompts.yaml: each SECM variable must have 'name' and 'prompt' fields",
                )
        
        return {
            "k": float(k),
            "variables": variables,
        }
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, detail=f"Configuration file not found: {config_path}"
        )
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=500, detail=f"Error parsing prompts.yaml: {str(e)}"
        )


# Cache the SECM config at module level
_SECM_CONFIG: dict[str, Any] | None = None


def get_secm_config() -> dict[str, Any]:
    """Get cached SECM configuration, loading it if necessary."""
    global _SECM_CONFIG
    if _SECM_CONFIG is None:
        _SECM_CONFIG = load_secm_config()
    return _SECM_CONFIG


def get_secm_k() -> float:
    """Get K damping constant from SECM config (default 4.0)."""
    config = get_secm_config()
    return config["k"]

