#!/usr/bin/env python3
"""Statistical audit of what drives a creator's view count.

Reads the JSON output of the SocialGPT MCP ``list_videos`` tool (saved to a
file), then for each candidate factor runs a real significance test against view
count and ranks the factors by strength + p-value. Writes an on-brand HTML
report and prints a concise Markdown summary for the agent to relay.

Usage:
    python scripts/analyze.py videos.json
    python scripts/analyze.py videos.json --out my-report.html

The model that runs this skill is responsible for first calling the MCP tool
``list_videos(limit=50, sort="recent", include_analysis=false)`` (optionally per
connected account) and saving the returned JSON to ``videos.json``.
"""

from __future__ import annotations

import argparse
import math
import sys

import sgpt_lib as L

# Factors tested as continuous predictors of (log) view count.
CONTINUOUS = [
    ("Video length", "duration (seconds)", L.duration),
    ("Engagement rate", "interactions per view", L.engagement_rate),
]
# Factors tested as categorical predictors (Kruskal-Wallis across groups).
CATEGORICAL = [
    ("Platform", L.platform),
    ("Day of week", L.weekday),
    ("Time of day", L.hour_bucket),
    ("Sequel vs standalone", lambda v: "sequel" if L.is_sequel(v) else "standalone"),
]


def _view_value(v: dict) -> float | None:
    """View count, treating Instagram 0-view posts as missing (IG hides reel plays)."""
    vw = L.views(v)
    if vw is None:
        return None
    if vw == 0 and L.platform(v) == "instagram":
        return None
    return vw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="videos.json")
    ap.add_argument("--out", default="content-performance-report.html")
    args = ap.parse_args()

    try:
        videos = L.load_videos(args.input)
    except FileNotFoundError:
        print(
            f"Could not find '{args.input}'. First call the SocialGPT MCP tool "
            "`list_videos(limit=50, sort='recent')` and save its JSON output to "
            f"'{args.input}', then run this script again.",
            file=sys.stderr,
        )
        return 2

    scored = [(v, _view_value(v)) for v in videos]
    usable = [(v, vw) for v, vw in scored if vw is not None]
    n_total = len(videos)
    n_usable = len(usable)
    if n_usable < 6:
        print(
            f"Only {n_usable} videos with usable view counts (need ~6+). "
            "Pull more with `list_videos(limit=50)` or connect more accounts.",
            file=sys.stderr,
        )
        return 1

    log_views = [math.log1p(vw) for _, vw in usable]
    findings: list[dict] = []

    # Continuous predictors -> Pearson on log(views).
    for label, unit, getter in CONTINUOUS:
        xs, ys = [], []
        for (v, _), lv in zip(usable, log_views):
            x = getter(v)
            if x is not None:
                xs.append(x)
                ys.append(lv)
        if len(xs) >= 6 and len(set(xs)) > 2:
            r, p, n = L.pearson(xs, ys)
            if not math.isnan(r):
                findings.append({
                    "factor": label, "unit": unit, "test": "Pearson",
                    "stat_display": f"r = {r:+.2f}", "p": p,
                    "strength": abs(r), "effect": L.effect_word(r),
                    "direction": "higher" if r > 0 else "lower", "n": n,
                    "kind": "continuous",
                })

    # Categorical predictors -> Kruskal-Wallis on raw views (rank-based, scale-robust).
    for label, getter in CATEGORICAL:
        groups: dict[str, list[float]] = {}
        for (v, vw) in usable:
            key = getter(v)
            if key:
                groups.setdefault(key, []).append(vw)
        big = {k: g for k, g in groups.items() if len(g) >= 2}
        if len(big) >= 2:
            H, p, n = L.kruskal_wallis(list(big.values()))
            if not math.isnan(H):
                # epsilon-squared effect size, comparable to |r| on 0..1.
                eps2 = H / (n - 1) if n > 1 else 0.0
                best = max(big.items(), key=lambda kv: L.median(kv[1]))
                findings.append({
                    "factor": label, "unit": "", "test": "Kruskal-Wallis",
                    "stat_display": f"H = {H:.1f}", "p": p,
                    "strength": min(1.0, eps2), "effect": L.effect_word(math.sqrt(min(1.0, eps2))),
                    "direction": f"best: {best[0]}", "n": n, "kind": "categorical",
                    "groups": {k: L.median(g) for k, g in big.items()},
                })

    findings.sort(key=lambda f: (f["p"] if not math.isnan(f["p"]) else 1.0))
    significant = [f for f in findings if not math.isnan(f["p"]) and f["p"] < 0.05]

    report_path = _write_report(args.out, usable, n_total, n_usable, findings)
    _print_summary(usable, n_total, n_usable, findings, significant, report_path)
    return 0


def _write_report(out, usable, n_total, n_usable, findings):
    med_views = L.median([vw for _, vw in usable])
    top = max(usable, key=lambda t: t[1])
    platforms = sorted({L.platform(v) for v, _ in usable})

    blocks: list[dict] = []
    blocks.append(L.callout("videos analyzed", str(n_usable),
                            f"of {n_total} pulled", "violet"))
    blocks.append(L.callout("median views", L.human(med_views), "your typical post", "sky"))
    if findings:
        blocks.append(L.callout("strongest driver", findings[0]["factor"],
                                findings[0]["stat_display"] + f", p={_fp(findings[0]['p'])}",
                                "pink"))

    bar_rows = []
    for f in findings:
        sig = L.significance_label(f["p"])
        kind = "hi" if (not math.isnan(f["p"]) and f["p"] < 0.01) else (
            "sig" if (not math.isnan(f["p"]) and f["p"] < 0.05) else "")
        tone = "lime" if kind in ("sig", "hi") else "ink"
        bar_rows.append({
            "label": f["factor"], "value": f["strength"],
            "display": f["stat_display"] + f" · p={_fp(f['p'])}",
            "tone": tone, "tag": sig if kind else "", "tag_kind": kind,
        })
    if bar_rows:
        blocks.append(L.bars_block(
            "What predicts your views",
            bar_rows,
            lede="Bars show effect strength; tags flag statistical significance "
                 "(green = p<0.05, pink = p<0.01).",
        ))

    rows = []
    emphasize = []
    for i, f in enumerate(findings):
        if not math.isnan(f["p"]) and f["p"] < 0.05:
            emphasize.append(i)
        rows.append([
            f["factor"], f["test"], f["stat_display"], _fp(f["p"]),
            {"tag": L.significance_label(f["p"]),
             "kind": "hi" if (not math.isnan(f["p"]) and f["p"] < 0.01)
             else ("sig" if (not math.isnan(f["p"]) and f["p"] < 0.05) else "")},
        ])
    blocks.append(L.table_block(
        "Full results", ["Factor", "Test", "Statistic", "p-value", "Verdict"],
        rows, num_cols=(3,), emphasize=emphasize,
        lede=f"Continuous factors use Pearson on log-views; categorical factors use "
             f"Kruskal-Wallis on ranks. Platforms in this set: {', '.join(platforms)}.",
    ))

    blocks.append(L.actions_block("What to do next", _actions(findings),
                                  lede="Grounded in the significant factors above."))

    html = L.render_report(
        title_html='What drives your <span class="hl">views</span>',
        kicker="Performance audit",
        subtitle=f"A statistical read of {n_usable} of your videos across {len(platforms)} platform(s).",
        blocks=blocks,
        footer="Generated by the **content-performance-audit** SocialGPT skill. "
               "Correlation is not causation — significant factors are leads to test, "
               "not guarantees. See `references/methodology.md` for the method. "
               "[gpt.social](https://gpt.social)",
    )
    return L.write_report(html, out)


def _actions(findings):
    out = []
    sig = [f for f in findings if not math.isnan(f["p"]) and f["p"] < 0.05]
    for f in sig[:3]:
        if f["kind"] == "continuous":
            out.append(
                f"**{f['factor']}** has a {f['effect']} link to views "
                f"({f['stat_display']}) — posts with {'more' if f['direction']=='higher' else 'less'} "
                f"of it tend to get more views. Deliberately test pushing it.")
        else:
            best = f.get("direction", "")
            out.append(
                f"**{f['factor']}** matters ({best}). Bias your next 5–10 posts toward "
                f"the winning option and watch whether the lift holds.")
    if not out:
        out.append("No factor cleared statistical significance yet — most likely the "
                   "sample is small. Pull more posts (or connect more accounts) and re-run; "
                   "in the meantime, lean on the strongest-effect factor as a hypothesis.")
    out.append("Re-run this audit monthly — the drivers shift as your content and "
               "audience evolve.")
    return out


def _fp(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "n/a"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def _print_summary(usable, n_total, n_usable, findings, significant, report_path):
    print(f"# Content performance audit — {n_usable} videos analyzed "
          f"({n_total} pulled)\n")
    if significant:
        print("**Statistically significant drivers of your view count:**\n")
        for f in significant:
            print(f"- **{f['factor']}** — {f['test']} {f['stat_display']}, "
                  f"p={_fp(f['p'])} ({L.significance_label(f['p'])}); "
                  f"effect: {f['effect']}; {f['direction']}.")
    else:
        print("_No factor reached p<0.05 — likely a small sample. "
              "Strongest signal:_")
        if findings:
            f = findings[0]
            print(f"- **{f['factor']}** — {f['stat_display']}, p={_fp(f['p'])}.")
    print(f"\n**Top actions:**")
    for a in _actions(findings)[:3]:
        print(f"- {a}")
    print(f"\nFull visual report written to `{report_path}` — open it in a browser "
          "(offer it to the user to download).")


if __name__ == "__main__":
    raise SystemExit(main())
