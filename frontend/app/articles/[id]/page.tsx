import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchArticleById, summarizeArticle, formatDate, formatBiasScore, formatIdeologicalScore, formatEvidenceScore } from "@/lib/api/client";
import { getPoliticalLeaning, getLeaningLabel } from "@/lib/api/types";
import { layout, typography, button, badge, getLeaningTheme, cn } from "@/lib/theme";

interface PageProps {
  params: Promise<{ id: string }>;
}

// Get color class for ideological score (blue=left, gray=center, red=right)
function getIdeologicalColorClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-amber-900";
  if (score < -0.15) return "text-blue-600";
  if (score > 0.15) return "text-red-600";
  return "text-amber-900";
}

// Get color class for evidence score (red=poor, yellow=mixed, green=good)
function getEvidenceColorClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-emerald-900";
  if (score < -0.15) return "text-red-500";
  if (score < 0.15) return "text-yellow-600";
  return "text-emerald-600";
}

export default async function ArticleDetailPage({ params }: PageProps) {
  const { id } = await params;
  const articleId = parseInt(id, 10);

  if (isNaN(articleId)) {
    notFound();
  }

  const article = await fetchArticleById(articleId);

  if (!article) {
    notFound();
  }

  const leaning = getPoliticalLeaning(article.bias_rating?.bias_score);
  const theme = getLeaningTheme(leaning);

  // Generate summary from article text if available
  let summary: string | null = null;
  let summaryError: string | null = null;

  if (article.raw_text) {
    try {
      summary = await summarizeArticle(article.raw_text);
    } catch (e) {
      summaryError = e instanceof Error ? e.message : "Failed to generate summary";
    }
  }

  return (
    <div className={cn(layout.containerNarrow, layout.section)}>
      {/* Back navigation */}
      <Link href="/" className={cn(button.link, "mb-6 inline-flex items-center gap-2")}>
        <BackIcon />
        Back to articles
      </Link>

      {/* Article */}
      <article className="overflow-hidden rounded-lg border-2 border-gray-200 bg-white shadow-sm">
        {/* Title section */}
        <div className="px-6 py-6 bg-gray-50">
          {/* OLD: Legacy bias badge and score - commented out in favor of SECM
          <div className="mb-3 flex items-center gap-3">
            <span className={cn(badge.base, theme.badge)}>
              {getLeaningLabel(leaning)}
            </span>
            {article.bias_rating && (
              <span className={typography.bodySmall}>
                Bias Score: {formatBiasScore(article.bias_rating.bias_score)}
              </span>
            )}
          </div>
          */}
          <h1 className={typography.h1}>{article.title}</h1>
        </div>

        {/* Meta info */}
        <div className="flex flex-wrap items-center gap-4 border-b border-gray-200 px-6 py-4">
          {article.source && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <SourceIcon />
              <span className="font-medium">{article.source}</span>
            </div>
          )}
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <ClockIcon />
            <span>{formatDate(article.published_at)}</span>
          </div>
        </div>

        {/* Bias details */}
        {article.bias_rating && (
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className={cn(typography.h2, "mb-3")}>Bias Analysis</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {/* OLD: Legacy visual bias meter - commented out in favor of SECM
              <div className="col-span-2">
                <div className="mb-2 flex justify-between text-xs text-gray-500">
                  <span>Left (-1.0)</span>
                  <span>Center (0)</span>
                  <span>Right (+1.0)</span>
                </div>
                <div className="relative h-4 rounded-full bg-gradient-to-r from-blue-500 via-crimson to-red-500">
                  <div
                    className="absolute top-1/2 h-6 w-2 -translate-y-1/2 rounded-full bg-white shadow-lg ring-2 ring-foreground"
                    style={{
                      left: `${((article.bias_rating.bias_score ?? 0) + 1) * 50}%`,
                      transform: "translate(-50%, -50%)",
                    }}
                  />
                </div>
              </div>
              */}

              {/* NEW: Ideological Score (Beta) */}
              {article.bias_rating.secm_ideological_score !== null && 
               article.bias_rating.secm_ideological_score !== undefined && (
                <div className="col-span-2 mt-2 p-4 rounded-lg bg-amber-50 border border-amber-200">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-amber-900">Ideological Score</h3>
                    <span className="text-xs font-medium px-2 py-0.5 bg-amber-200 text-amber-800 rounded-full">
                      BETA
                    </span>
                  </div>
                  <p className="text-xs text-amber-700 mb-3">
                    New 22-question analysis based on Structural-Epistemic Coding Matrix (SECM)
                  </p>
                  <div className="flex justify-between text-xs text-amber-700 mb-4">
                    <span>Left (-1.0)</span>
                    <span>Center (0)</span>
                    <span>Right (+1.0)</span>
                  </div>
                  <div className="relative h-4 rounded-full bg-gradient-to-r from-blue-500 via-gray-300 to-red-500">
                    <div
                      className="absolute top-1/2 h-6 w-2 -translate-y-1/2 rounded-full bg-white shadow-lg ring-2 ring-amber-500"
                      style={{
                        left: `${((article.bias_rating.secm_ideological_score ?? 0) + 1) * 50}%`,
                        transform: "translate(-50%, -50%)",
                      }}
                    />
                  </div>
                  <div className="mt-4 text-center">
                    <span className={cn("font-semibold", getIdeologicalColorClass(article.bias_rating.secm_ideological_score))}>
                      {formatIdeologicalScore(article.bias_rating.secm_ideological_score)}
                    </span>
                    <span className="text-xs text-amber-700 ml-2">
                      (raw: {article.bias_rating.secm_ideological_score?.toFixed(3)})
                    </span>
                  </div>
                </div>
              )}

              {/* NEW: Evidence Rating (Epistemic Score - Beta) */}
              {article.bias_rating.secm_epistemic_score !== null && 
               article.bias_rating.secm_epistemic_score !== undefined && (
                <div className="col-span-2 mt-2 p-4 rounded-lg bg-emerald-50 border border-emerald-200">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-emerald-900">Evidence Rating</h3>
                    <span className="text-xs font-medium px-2 py-0.5 bg-emerald-200 text-emerald-800 rounded-full">
                      BETA
                    </span>
                  </div>
                  <p className="text-xs text-emerald-700 mb-3">
                    Measures journalistic integrity: source attribution, documentation, vs. emotive language
                  </p>
                  <div className="flex justify-between text-xs text-emerald-700 mb-4">
                    <span>Poor (-1.0)</span>
                    <span>Mixed (0)</span>
                    <span>Strong (+1.0)</span>
                  </div>
                  <div className="relative h-4 rounded-full bg-gradient-to-r from-red-400 via-yellow-400 to-emerald-500">
                    <div
                      className="absolute top-1/2 h-6 w-2 -translate-y-1/2 rounded-full bg-white shadow-lg ring-2 ring-emerald-500"
                      style={{
                        left: `${((article.bias_rating.secm_epistemic_score ?? 0) + 1) * 50}%`,
                        transform: "translate(-50%, -50%)",
                      }}
                    />
                  </div>
                  <div className="mt-4 text-center">
                    <span className={cn("font-semibold", getEvidenceColorClass(article.bias_rating.secm_epistemic_score))}>
                      {formatEvidenceScore(article.bias_rating.secm_epistemic_score)}
                    </span>
                    <span className="text-xs text-emerald-700 ml-2">
                      (raw: {article.bias_rating.secm_epistemic_score?.toFixed(3)})
                    </span>
                  </div>
                </div>
              )}

              {/* OLD: Individual dimension scores - commented out in favor of SECM
              {(article.bias_rating.partisan_bias !== undefined ||
                article.bias_rating.affective_bias !== undefined ||
                article.bias_rating.framing_bias !== undefined ||
                article.bias_rating.sourcing_bias !== undefined) && (
                <>
                  <BiasScoreCard label="Partisan Bias" value={article.bias_rating.partisan_bias} />
                  <BiasScoreCard label="Affective Bias" value={article.bias_rating.affective_bias} />
                  <BiasScoreCard label="Framing Bias" value={article.bias_rating.framing_bias} />
                  <BiasScoreCard label="Sourcing Bias" value={article.bias_rating.sourcing_bias} />
                </>
              )}
              */}
            </div>
          </div>
        )}

        {/* Summary section */}
        <div className="px-6 py-6">
          <h2 className={cn(typography.h2, "mb-3")}>Summary</h2>
          {summaryError ? (
            <div className="rounded-lg border-2 border-yellow-300 bg-yellow-50 p-4">
              <p className="text-sm text-yellow-700">
                <strong>Unable to generate summary:</strong> {summaryError}
              </p>
            </div>
          ) : summary ? (
            <p className="text-gray-700">{summary}</p>
          ) : (
            <p className="text-sm italic text-gray-500">
              No article content available for summarization.
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
          {article.url ? (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className={button.primary}
            >
              Read full article
              <ExternalLinkIcon />
            </a>
          ) : (
            <p className={typography.caption}>No source URL available for this article.</p>
          )}
        </div>
      </article>
    </div>
  );
}

// =============================================================================
// COMPONENTS
// =============================================================================

function BiasScoreCard({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
      <span className={typography.bodySmall}>{label}</span>
      <span className="font-medium text-foreground">{value?.toFixed(2) ?? "N/A"}</span>
    </div>
  );
}

// =============================================================================
// ICONS
// =============================================================================

function BackIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  );
}

function SourceIcon() {
  return (
    <svg className="h-4 w-4 text-crimson" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
    <svg className="h-4 w-4 text-crimson" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
      />
    </svg>
  );
}
