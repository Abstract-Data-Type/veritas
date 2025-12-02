import Link from "next/link";
import { Article, getPoliticalLeaning, getLeaningLabel } from "@/lib/api/types";
import { formatDate, formatBiasScore, formatIdeologicalScore, formatEvidenceScore } from "@/lib/api/client";
import { getLeaningTheme, articleCard, badge, skeleton, cn } from "@/lib/theme";
import { Tooltip, InfoIcon } from "./Tooltip";
import { MethodologyModal } from "./MethodologyModal";

interface ArticleCardProps {
  article: Article;
}

// Get color class for ideological score (blue=left, gray=center, red=right)
function getIdeologicalColorClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-gray-600";
  if (score < -0.15) return "text-blue-600";
  if (score > 0.15) return "text-red-600";
  return "text-gray-600";
}

// Get color class for evidence score (red=poor, yellow=mixed, green=good)
function getEvidenceColorClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-gray-600";
  if (score < -0.15) return "text-red-500";
  if (score < 0.15) return "text-yellow-600";
  return "text-emerald-600";
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
          {/* OLD: Legacy bias badge - commented out in favor of SECM scores
          <span className={cn(badge.base, theme.badge)}>
            {getLeaningLabel(leaning)}
          </span>
          */}
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

        {/* SECM Scores Section */}
        {article.bias_rating ? (
          <div className={articleCard.biasSection}>
            {/* New Ideological Score */}
            {article.bias_rating.secm_ideological_score !== null && 
             article.bias_rating.secm_ideological_score !== undefined && (
              <div className="pt-2">
                <div className="flex items-center justify-between mb-2">
                  <span className={cn(articleCard.biasLabel, "flex items-center gap-1")}>
                    Ideological Spectrum
                    <Tooltip content={
                      <div className="text-left">
                        <p className="font-semibold mb-1">Ideological Spectrum</p>
                        <p className="mb-2">Detects <strong>how the text assigns blame</strong>. Does the author frame problems as failures of <span className="text-blue-300">systems and structures (Left)</span> or failures of <span className="text-red-300">individuals and choices (Right)</span>?</p>
                        <p className="text-gray-400 text-[10px]">12 binary variables · Bayesian smoothing (K=4)</p>
                      </div>
                    }>
                      <InfoIcon />
                    </Tooltip>
                  </span>
                  <span className={cn("font-semibold", getIdeologicalColorClass(article.bias_rating.secm_ideological_score))}>
                    {formatIdeologicalScore(article.bias_rating.secm_ideological_score)}
                  </span>
                </div>
                {/* Fixed gradient with position indicator */}
                <div className="relative h-2 rounded-full bg-gradient-to-r from-blue-500 via-gray-300 to-red-500">
                  <div
                    className="absolute top-1/2 h-3 w-1 -translate-y-1/2 rounded-full bg-white shadow ring-1 ring-gray-400"
                    style={{
                      left: `${((article.bias_rating.secm_ideological_score ?? 0) + 1) * 50}%`,
                      transform: "translate(-50%, -50%)",
                    }}
                  />
                </div>
              </div>
            )}

            {/* Evidence Rating (Epistemic Score - Beta) */}
            {article.bias_rating.secm_epistemic_score !== null && 
             article.bias_rating.secm_epistemic_score !== undefined && (
              <div className="mt-3 pt-2 border-t border-gray-100">
                <div className="flex items-center justify-between mb-2">
                  <span className={cn(articleCard.biasLabel, "flex items-center gap-1")}>
                    Epistemic Integrity
                    <Tooltip content={
                      <div className="text-left">
                        <p className="font-semibold mb-1">Epistemic Integrity</p>
                        <p className="mb-2">Audits <strong>information quality</strong>. Does the text cite sources and provide evidence (<span className="text-emerald-300">High Integrity</span>), or rely on emotional language and unsubstantiated claims (<span className="text-red-300">Low Integrity</span>)?</p>
                        <p className="text-gray-400 text-[10px]">10 binary variables · Bayesian smoothing (K=4)</p>
                      </div>
                    }>
                      <InfoIcon />
                    </Tooltip>
                  </span>
                  <span className={cn("font-semibold", getEvidenceColorClass(article.bias_rating.secm_epistemic_score))}>
                    {formatEvidenceScore(article.bias_rating.secm_epistemic_score)}
                  </span>
                </div>
                {/* Fixed gradient with position indicator */}
                <div className="relative h-2 rounded-full bg-gradient-to-r from-red-400 via-yellow-400 to-emerald-500">
                  <div
                    className="absolute top-1/2 h-3 w-1 -translate-y-1/2 rounded-full bg-white shadow ring-1 ring-gray-400"
                    style={{
                      left: `${((article.bias_rating.secm_epistemic_score ?? 0) + 1) * 50}%`,
                      transform: "translate(-50%, -50%)",
                    }}
                  />
                </div>
              </div>
            )}

            {/* Methodology Link or Pending */}
            {(article.bias_rating.secm_ideological_score !== null || 
              article.bias_rating.secm_epistemic_score !== null) ? (
              <div className="mt-3 pt-2 border-t border-gray-100 text-center">
                <MethodologyModal />
              </div>
            ) : (
              <div className="text-center text-gray-400 text-sm italic py-2">
                Analysis pending...
              </div>
            )}
          </div>
        ) : (
          <div className={cn(articleCard.biasSection, "text-center text-gray-400 text-sm italic")}>
            Analysis pending...
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
