# Methodology — content-performance-audit

Load this only if you need to explain *how* a finding was computed or defend it.

## Inputs

The script consumes the `McpPostSummary` objects returned by the SocialGPT MCP
`list_videos` tool. Per video it reads:

- `metrics.views` (the response variable), `metrics.engagement_rate`,
  and the raw interaction counts (`likes`, `comments`, `shares`, `saves`).
- `duration` (seconds), `post_created_time` (ISO 8601).
- `platform`, `title`/`caption` (for sequel detection).

## View-count cleaning

View count is heavy-tailed, so all correlations are run on **log(1 + views)**.
Instagram posts reporting `views == 0` are treated as **missing** (Instagram
hides reel plays for many accounts) and excluded from the view-count analysis —
they are still counted in the "pulled" total.

## Tests

**Continuous predictors** (video length, engagement rate) → **Pearson
correlation** between the predictor and log-views. The two-sided p-value comes
from the Student-t statistic `t = r·√((n−2)/(1−r²))`, evaluated through the
regularized incomplete beta function (no SciPy). Reported effect bands:
|r| ≥ 0.5 strong, ≥ 0.3 moderate, ≥ 0.1 weak.

**Categorical predictors** (platform, day of week, time-of-day bucket, sequel
vs. standalone) → **Kruskal-Wallis H test** on the raw view ranks across groups.
It is non-parametric (rank-based), so it does not assume a normal distribution —
appropriate for view counts. The p-value uses the chi-square approximation with
`k−1` degrees of freedom (via the regularized upper incomplete gamma function),
with a tie correction. Effect size is reported as epsilon-squared
`ε² = H/(n−1)`, placed on the same 0–1 scale as |r| so factors rank together.

A factor is only tested when it has enough data: ≥6 paired points (continuous)
or ≥2 groups each with ≥2 observations (categorical). Time-of-day buckets:
late-night 0–6, morning 6–12, afternoon 12–18, evening 18–24 (post timestamp).

## Significance bands

- p < 0.01 → "highly significant"
- p < 0.05 → "significant"
- p < 0.10 → "suggestive"
- otherwise → "not significant"

## Caveats (state these to the user when relevant)

- **Correlation is not causation.** A significant factor is the best lead to
  A/B test next, not proof.
- **Confounding.** Factors interact (e.g. short videos may also be a particular
  format). Treat each test as marginal, not a controlled experiment.
- **Survivorship / small n.** A 30–50 video window is a snapshot; re-run as the
  account grows. Multiple comparisons mean an occasional false positive — prefer
  factors that persist across re-runs.
