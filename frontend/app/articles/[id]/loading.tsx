import { layout, skeleton, cn } from "@/lib/theme";

export default function ArticleLoading() {
  return (
    <div className={cn(layout.containerNarrow, layout.section)}>
      {/* Back navigation skeleton */}
      <div className={cn(skeleton.base, "mb-6 h-5 w-32")} />

      {/* Article skeleton */}
      <div className="overflow-hidden rounded-lg border-2 border-gray-200 bg-white shadow-sm">
        {/* Title section skeleton */}
        <div className="bg-gray-50 px-6 py-6">
          <div className="mb-3 flex items-center gap-3">
            <div className={cn(skeleton.pill, "h-6 w-20")} />
            <div className={cn(skeleton.base, "h-4 w-32")} />
          </div>
          <div className={cn(skeleton.base, "h-8 w-3/4")} />
          <div className={cn(skeleton.base, "mt-2 h-8 w-1/2")} />
        </div>

        {/* Meta info skeleton */}
        <div className="flex gap-4 border-b border-gray-200 px-6 py-4">
          <div className={cn(skeleton.base, "h-4 w-24")} />
          <div className={cn(skeleton.base, "h-4 w-32")} />
        </div>

        {/* Bias details skeleton */}
        <div className="border-b border-gray-200 px-6 py-4">
          <div className={cn(skeleton.base, "mb-3 h-6 w-32")} />
          <div className={cn(skeleton.base, "h-4 rounded-full")} />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className={cn(skeleton.light, "h-12 rounded-lg")} />
            ))}
          </div>
        </div>

        {/* Summary skeleton */}
        <div className="px-6 py-6">
          <div className={cn(skeleton.base, "mb-3 h-6 w-24")} />
          <div className="space-y-2">
            <div className={cn(skeleton.base, "h-4 w-full")} />
            <div className={cn(skeleton.base, "h-4 w-full")} />
            <div className={cn(skeleton.base, "h-4 w-3/4")} />
          </div>
        </div>

        {/* Actions skeleton */}
        <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
          <div className={cn(skeleton.base, "h-12 w-44 rounded-lg")} />
        </div>
      </div>
    </div>
  );
}
