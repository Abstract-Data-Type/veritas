/**
 * API Types for Veritas News Frontend
 * Based on backend models in backend/src/veritas_news/models/
 */

/**
 * Bias rating information for an article
 * Maps to BiasRatingInfo from backend
 */
export interface BiasRating {
  rating_id: number;
  bias_score: number | null;
  reasoning: string | null;
  evaluated_at: string;
  // Multi-dimensional scores (optional, available in detailed view)
  partisan_bias?: number | null;
  affective_bias?: number | null;
  framing_bias?: number | null;
  sourcing_bias?: number | null;
  // SECM scores (new ideological scoring system)
  secm_ideological_score?: number | null;
  secm_epistemic_score?: number | null;
}

/**
 * Article response model
 * Maps to ArticleResponse from backend routes_articles.py
 */
export interface Article {
  article_id: number;
  title: string;
  source: string | null;
  url: string | null;
  published_at: string | null;
  raw_text: string | null;
  created_at: string;
  bias_rating: BiasRating | null;
}

/**
 * Response from /articles/latest endpoint
 */
export interface ArticleListResponse {
  articles: Article[];
  total: number;
}

/**
 * Response from /bias_ratings/summarize endpoint
 */
export interface SummarizeResponse {
  summary: string;
}

/**
 * Maintenance state from /status endpoint
 */
export interface MaintenanceState {
  is_running: boolean;
  started_at: string | null;
  last_completed: string | null;
  next_refresh: string | null;
}

/**
 * Response from /status endpoint
 */
export interface StatusResponse {
  status: string;
  maintenance: MaintenanceState;
}

/**
 * Political leaning categories based on bias score
 * Scores range from -1.0 (far left) to 1.0 (far right)
 */
export type PoliticalLeaning = "left" | "center" | "right" | "unknown";

/**
 * Helper function to determine political leaning from bias score
 * @param biasScore - Score from -1.0 to 1.0
 * @returns Political leaning category
 */
export function getPoliticalLeaning(biasScore: number | null | undefined): PoliticalLeaning {
  if (biasScore === null || biasScore === undefined) {
    return "unknown";
  }

  // Thresholds for categorization:
  // -1.0 to -0.25: Left
  // -0.25 to 0.25: Center
  // 0.25 to 1.0: Right
  if (biasScore < -0.25) {
    return "left";
  } else if (biasScore > 0.25) {
    return "right";
  } else {
    return "center";
  }
}

/**
 * Get display label for political leaning
 */
export function getLeaningLabel(leaning: PoliticalLeaning): string {
  const labels: Record<PoliticalLeaning, string> = {
    left: "Left",
    center: "Center",
    right: "Right",
    unknown: "Unknown",
  };
  return labels[leaning];
}
