"""AI library module for summarization and bias analysis."""

from . import bias_analysis, config, scoring, summarization

__all__ = [
    "summarize_with_gemini",
    "rate_bias",
    "rate_bias_parallel",
    "score_bias",
    "get_prompts_config",
]

# Public API exports
summarize_with_gemini = summarization.summarize_with_gemini
rate_bias = bias_analysis.rate_bias
rate_bias_parallel = bias_analysis.rate_bias_parallel
score_bias = scoring.score_bias
get_prompts_config = config.get_prompts_config

