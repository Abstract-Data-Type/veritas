import Link from "next/link";
import { Article, getPoliticalLeaning, getLeaningLabel } from "@/lib/api/types";
import { formatDate, formatBiasScore } from "@/lib/api/client";
import { getLeaningTheme, articleCard, badge, skeleton, cn } from "@/lib/theme";

interface ArticleCardProps {
  article: Article;
}

export function ArticleCard({ article }: ArticleCardProps) {
  const leaning = getPoliticalLeaning(article.bias_rating?.bias_score);
  const theme = getLeaningTheme(leaning);

  return (
    <Link href={`/articles/${article.article_id}`} className={articleCard.wrapper}>
      <article className={cn(articleCard.article, theme.border)}>
        {/* Title and Badge */}
        <div className={articleCard.titleRow}>
          <h3 className={articleCard.title}>{article.title}</h3>
          <span className={cn(badge.base, theme.badge)}>
            {getLeaningLabel(leaning)}
          </span>
        </div>

        {/* Meta Info */}
        <div className={articleCard.meta}>
          {article.source && (
            <span className="inline-flex items-center gap-1 font-medium">
              <SourceIcon />
              {article.source}
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <ClockIcon />
            {formatDate(article.published_at)}
          </span>
        </div>

        {/* Bias Score */}
        {article.bias_rating && (
          <div className={articleCard.biasSection}>
            <div className="flex items-center justify-between mb-1">
              <span className={articleCard.biasLabel}>Bias Score</span>
              <span className={articleCard.biasScore}>
                {formatBiasScore(article.bias_rating.bias_score)}
              </span>
            </div>
            <div className={articleCard.biasBar}>
              <div
                className={cn("h-full transition-all", theme.barColor)}
                style={{
                  width: `${Math.abs((article.bias_rating.bias_score ?? 0) * 50) + 50}%`,
                  marginLeft:
                    (article.bias_rating.bias_score ?? 0) < 0
                      ? `${50 - Math.abs((article.bias_rating.bias_score ?? 0) * 50)}%`
                      : "50%",
                }}
              />
            </div>
          </div>
        )}
      </article>
    </Link>
  );
}

/** Loading skeleton for ArticleCard */
export function ArticleCardSkeleton() {
  return (
    <div className="rounded-lg border-2 border-gray-200 bg-white p-4">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className={cn(skeleton.base, "h-5 w-3/4")} />
        <div className={cn(skeleton.pill, "h-6 w-16")} />
      </div>
      <div className="mt-3 flex gap-3">
        <div className={cn(skeleton.light, "h-3 w-20")} />
        <div className={cn(skeleton.light, "h-3 w-24")} />
      </div>
      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="flex items-center justify-between mb-1">
          <div className={cn(skeleton.light, "h-3 w-16")} />
          <div className={cn(skeleton.light, "h-3 w-12")} />
        </div>
        <div className={cn(skeleton.light, "h-2 flex-1 rounded-full")} />
      </div>
    </div>
  );
}

// =============================================================================
// ICONS
// =============================================================================

function SourceIcon() {
  return (
    <svg className="h-3 w-3 text-crimson" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
      />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg className="h-3 w-3 text-crimson" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
