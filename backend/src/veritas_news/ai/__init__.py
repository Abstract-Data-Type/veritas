"""AI library module for summarization and bias analysis."""

from . import bias_analysis, config, scoring, summarization

__all__ = [
    "summarize_with_gemini",
    "rate_bias",
    "rate_bias_parallel",
    "rate_secm",
    "rate_secm_parallel",
    "score_bias",
    "score_secm",
    "get_prompts_config",
    "get_secm_config",
]

# Public API exports
summarize_with_gemini = summarization.summarize_with_gemini
rate_bias = bias_analysis.rate_bias
rate_bias_parallel = bias_analysis.rate_bias_parallel
rate_secm = bias_analysis.rate_secm
rate_secm_parallel = bias_analysis.rate_secm_parallel
score_bias = scoring.score_bias
score_secm = scoring.score_secm
get_prompts_config = config.get_prompts_config
get_secm_config = config.get_secm_config

