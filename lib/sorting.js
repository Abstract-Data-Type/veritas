import { computeDiversity } from "./metrics";

export const SortMode = {
  RECENCY: "recency",
  DIVERSITY: "diversity",
  NOVELTY: "novelty",
  PERSONALIZED: "personalized" // P4
};

export function sortTopics(topics, mode, prioritizeUnfamiliar = false) {
  const byRecency = (a, b) => new Date(b.updatedAt) - new Date(a.updatedAt);
  const byDiversity = (a, b) => {
    const d = computeDiversity(b) - computeDiversity(a);
    if (d !== 0) return d;
    const ta = (a.coverage?.left || 0) + (a.coverage?.center || 0) + (a.coverage?.right || 0);
    const tb = (b.coverage?.left || 0) + (b.coverage?.center || 0) + (b.coverage?.right || 0);
    return tb - ta;
  };
  const byNovelty = (a, b) => (b.novelty?.score || 0) - (a.novelty?.score || 0);

  if (mode === SortMode.DIVERSITY) return [...topics].sort(byDiversity);
  if (mode === SortMode.NOVELTY) return [...topics].sort(byNovelty);

  if (mode === SortMode.PERSONALIZED || prioritizeUnfamiliar) {
    return [...topics].sort((a, b) => {
      const sa = computeDiversity(a) * 0.6 + (a.novelty?.score || 0) * 0.4;
      const sb = computeDiversity(b) * 0.6 + (b.novelty?.score || 0) * 0.4;
      return sb - sa;
    });
  }

  return [...topics].sort(byRecency);
}
