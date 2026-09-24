export const SCORE_THRESHOLD_HIGH = 75;
export const SCORE_THRESHOLD_MID = 50;

// Matches passing_score used across the Screening Score contracts (Contract 1).
export const RECOMMENDATION_PASS_THRESHOLD = 60;

// Gauge geometry (semicircle arc). Kept as named constants instead of
// magic numbers scattered in the SVG path/stroke-dasharray math.
export const GAUGE_VIEWBOX = "0 0 200 110";
export const GAUGE_ARC_PATH = "M 10 100 A 90 90 0 0 1 190 100";
export const GAUGE_STROKE_WIDTH = 14;
// Arc length of the path above (πr with r=90), used for stroke-dasharray.
export const GAUGE_ARC_LENGTH = 282.7;