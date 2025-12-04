import Link from "next/link";
import { layout, typography, button, cn } from "@/lib/theme";

export default function ArticleNotFound() {
  return (
    <div className={cn(layout.containerNarrow, "py-16")}>
      <div className="text-center">
        <h1 className="text-6xl font-bold text-crimson">404</h1>
        <h2 className={cn(typography.h2, "mt-4 text-2xl")}>Article Not Found</h2>
        <p className="mt-2 text-gray-600">
          The article you&apos;re looking for doesn&apos;t exist or has been removed.
        </p>
        <Link href="/" className={cn(button.primary, "mt-8")}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to articles
        </Link>
      </div>
    </div>
  );
}
