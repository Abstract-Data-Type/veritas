export function computeDiversity(topic) {
  let leans = 0;
  if ((topic.coverage?.left || 0) > 0) leans += 1;
  if ((topic.coverage?.center || 0) > 0) leans += 1;
  if ((topic.coverage?.right || 0) > 0) leans += 1;
  return leans / 3; // 0..1
}

export function coverageHelperText(topic) {
  const { left = 0, center = 0, right = 0 } = topic.coverage || {};
  const total = left + center + right;
  const diversity = computeDiversity(topic);
  if (total === 0) return "No coverage yet";
  if (diversity === 1) return "Broad coverage across spectrum";
  if (diversity >= 2 / 3) return "Wide coverage across outlets";
  return "Coverage concentrated in fewer leans";
}
