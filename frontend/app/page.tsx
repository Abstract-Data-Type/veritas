import { fetchArticles } from "@/lib/api/client";
import { Article } from "@/lib/api/types";
import { ArticleCard, ArticleCardSkeleton } from "./components/ArticleCard";
import { Suspense } from "react";
import { layout, typography, legend, error, skeleton, cn } from "@/lib/theme";

// =============================================================================
// HELPERS
// =============================================================================

/** Sort articles by published_at descending (most recent first) */
function sortArticlesByDate(articles: Article[]): Article[] {
  return [...articles].sort((a, b) => {
    const dateA = a.published_at ? new Date(a.published_at).getTime() : 0;
    const dateB = b.published_at ? new Date(b.published_at).getTime() : 0;
    return dateB - dateA;
  });
}

// =============================================================================
// COMPONENTS
// =============================================================================

function LoadingSkeleton() {
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <ArticleCardSkeleton key={i} />
      ))}
    </div>
  );
}

function ErrorDisplay({ message }: { message: string }) {
  return (
    <div className={error.wrapper}>
      <h2 className={error.title}>Error Loading Articles</h2>
      <p className={error.message}>{message}</p>
      <p className={error.hint}>
        Please make sure the backend is running at{" "}
        <code className={error.code}>
          {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}
        </code>
      </p>
    </div>
  );
}

function BiasLegend() {
  return (
    <div className={legend.wrapper}>
      <span className={legend.label}>Bias Scale:</span>
      <div className={legend.item}>
        <span className={cn(legend.dot, "bg-blue-600")} />
        <span className={legend.text}>Left-Leaning</span>
      </div>
      <div className={legend.item}>
        <span className={cn(legend.dot, "bg-crimson")} />
        <span className={legend.text}>Center</span>
      </div>
      <div className={legend.item}>
        <span className={cn(legend.dot, "bg-red-600")} />
        <span className={legend.text}>Right-Leaning</span>
      </div>
    </div>
  );
}

async function ArticlesGrid() {
  let articles: Article[] = [];
  let errorMsg: string | null = null;

  try {
    const response = await fetchArticles({ limit: 100 });
    articles = sortArticlesByDate(response.articles);
  } catch (e) {
    errorMsg = e instanceof Error ? e.message : "Failed to load articles";
  }

  if (errorMsg) {
    return <ErrorDisplay message={errorMsg} />;
  }

  if (articles.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg">No articles found</p>
        <p className="text-sm mt-2">Check back later for new content</p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {articles.map((article) => (
        <ArticleCard key={article.article_id} article={article} />
      ))}
    </div>
  );
}

// =============================================================================
// PAGE
// =============================================================================

export default function Home() {
  return (
    <div className={cn(layout.container, layout.section)}>
      {/* Hero Section */}
      <div className="mb-8 text-center">
        <h1 className={typography.h1}>
          News <span className={typography.accent}>Across the Spectrum</span>
        </h1>
        <p className="mt-3 text-lg text-gray-600">
          Explore news articles with AI-powered political bias analysis. Each card shows
          the detected political leaning.
        </p>
      </div>

      {/* Legend */}
      <BiasLegend />

      {/* Articles Grid */}
      <Suspense fallback={<LoadingSkeleton />}>
        <ArticlesGrid />
      </Suspense>
    </div>
  );
}
