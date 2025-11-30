/**
 * API Client for Veritas News Backend
 *
 * This module provides functions to interact with the backend API.
 * All endpoints are documented in backend/src/veritas_news/api/
 */

import { Article, ArticleListResponse, SummarizeResponse } from "./types";

/**
 * Get the API base URL from environment variables
 * Falls back to localhost:8000 for development
 */
function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Fetch wrapper with error handling
 */
async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `API Error: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // Ignore JSON parse errors for error responses
      }
      throw new ApiError(errorMessage, response.status, response.statusText);
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network errors or other issues
    throw new ApiError(
      `Failed to connect to API: ${error instanceof Error ? error.message : "Unknown error"}`,
      0,
      "Network Error"
    );
  }
}

/**
 * Fetch latest articles from the backend
 *
 * @param options - Query parameters
 * @param options.limit - Maximum number of articles (1-100, default 20)
 * @param options.offset - Number of articles to skip (default 0)
 * @param options.minBiasScore - Minimum bias score filter (-1.0 to 1.0)
 * @param options.maxBiasScore - Maximum bias score filter (-1.0 to 1.0)
 * @returns Promise resolving to ArticleListResponse
 */
export async function fetchArticles(options?: {
  limit?: number;
  offset?: number;
  minBiasScore?: number;
  maxBiasScore?: number;
}): Promise<ArticleListResponse> {
  const params = new URLSearchParams();

  if (options?.limit !== undefined) {
    params.set("limit", options.limit.toString());
  }
  if (options?.offset !== undefined) {
    params.set("offset", options.offset.toString());
  }
  if (options?.minBiasScore !== undefined) {
    params.set("min_bias_score", options.minBiasScore.toString());
  }
  if (options?.maxBiasScore !== undefined) {
    params.set("max_bias_score", options.maxBiasScore.toString());
  }

  const queryString = params.toString();
  const endpoint = `/articles/latest${queryString ? `?${queryString}` : ""}`;

  return apiFetch<ArticleListResponse>(endpoint);
}

/**
 * Fetch a single article by ID
 *
 * Note: The backend doesn't have a dedicated single-article endpoint,
 * so we fetch the list and find the article. In a production app,
 * you might want to add a dedicated endpoint.
 *
 * @param id - Article ID
 * @returns Promise resolving to Article or null if not found
 */
export async function fetchArticleById(id: number): Promise<Article | null> {
  // Fetch a larger list to increase chances of finding the article
  const response = await fetchArticles({ limit: 100 });

  const article = response.articles.find((a) => a.article_id === id);
  return article || null;
}

/**
 * Summarize article text using the AI service
 *
 * @param articleText - The full article text to summarize
 * @returns Promise resolving to the summary text
 */
export async function summarizeArticle(articleText: string): Promise<string> {
  const response = await apiFetch<SummarizeResponse>("/bias_ratings/summarize", {
    method: "POST",
    body: JSON.stringify({ article_text: articleText }),
  });

  return response.summary;
}

/**
 * Format a date string for display
 *
 * @param dateString - ISO date string
 * @returns Formatted date string or "Unknown date" if invalid
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return "Unknown date";

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "Unknown date";
  }
}

/**
 * Format bias score for display
 *
 * @param score - Bias score from -1.0 to 1.0
 * @returns Formatted string representation
 */
export function formatBiasScore(score: number | null): string {
  if (score === null) return "N/A";

  const percentage = Math.round(score * 100);
  if (percentage < 0) {
    return `${Math.abs(percentage)}% Left`;
  } else if (percentage > 0) {
    return `${percentage}% Right`;
  }
  return "Neutral";
}
