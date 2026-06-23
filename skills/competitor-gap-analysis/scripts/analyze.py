#!/usr/bin/env python3
"""Competitor gap analysis: where rivals win and you're silent.

Reads a single ``gap.json`` the agent assembled from SocialGPT MCP output —
the caller's own top videos plus 1-3 named competitors' top videos — then finds
the themes competitors cover heavily where you have ~no coverage (content gaps),
the themes you own that they ignore (owned territory), and how your format
(duration, sequels, engagement, views) differs. Writes an on-brand HTML report
and prints a concise Markdown summary for the agent to relay.

Usage:
    python scripts/analyze.py gap.json
    python scripts/analyze.py gap.json --out my-report.html

The model that runs this skill is responsible for first calling the MCP tools
``list_videos(sort="top", limit=15, include_analysis=true)`` for ``me`` and
``list_creator_videos(platform=..., username=..., sort="top", limit=15,
include_analysis=true)`` for each competitor, then writing ``gap.json`` shaped:

    {"me": <videos>, "competitors": [{"name": "@h", "videos": <videos>}, ...]}
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter

import sgpt_lib as L

# A theme counts as a competitor "gap" target at or above this coverage share,
# and only if it shows up for at least this many distinct competitor videos.
GAP_COMPETITOR_SHARE = 0.20
GAP_COMPETITOR_MIN_VIDEOS = 2
# Your coverage at/below this share counts as "barely covered" (a gap for you).
MINE_SILENT_SHARE = 0.0001
# Owned territory: you cover it on >= this many videos, competitors near-zero.
OWNED_MINE_MIN_VIDEOS = 2
OWNED_COMPETITOR_MAX_SHARE = 0.05
# Keyword fallback fires when fewer than this fraction of videos carry analysis
# themes; we then mine pseudo-themes from captions.
THEME_COVERAGE_FLOOR = 0.40
KEYWORD_VOCAB_SIZE = 25

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "your", "with", "this",
    "that", "have", "has", "had", "was", "were", "from", "they", "their", "them",
    "what", "when", "where", "which", "who", "how", "why", "all", "any", "can",
    "out", "get", "got", "our", "his", "her", "its", "him", "she", "him", "one",
    "two", "new", "now", "day", "way", "via", "per", "off", "too", "use", "make",
    "made", "just", "like", "more", "most", "some", "into", "over", "than", "then",
    "here", "there", "about", "after", "before", "again", "still", "every", "much",
    "many", "very", "really", "going", "gonna", "wanna", "thing", "things", "stuff",
    "video", "videos", "watch", "follow", "comment", "share", "link", "bio", "check",
    "today", "yall", "guys", "lets", "dont", "didnt", "cant", "wont", "ill", "ive",
    "youre", "youll", "youve", "isnt", "arent", "ok", "okay", "yes", "lol",
}

_TONES = ["pink", "violet", "sky", "tangerine", "lime", "butter"]


# ---------------------------------------------------------------------------
# Parsing the gap.json envelope
# ---------------------------------------------------------------------------


def _load_gap(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def _competitor_entries(data: dict) -> list[dict]:
    """Normalize the competitors list into [{name, videos:[...]}, ...]."""
    out: list[dict] = []
    comps = data.get("competitors")
    if isinstance(comps, list):
        for i, entry in enumerate(comps):
            if not isinstance(entry, dict):
                continue
            vids = L.coerce_videos(entry.get("videos", entry))
            name = str(entry.get("name") or entry.get("username") or f"competitor {i + 1}")
            out.append({"name": name, "videos": vids})
    elif isinstance(comps, dict):
        # Map shape {"@handle": <videos>, ...}.
        for name, vids in comps.items():
            out.append({"name": str(name), "videos": L.coerce_videos(vids)})
    return out


# ---------------------------------------------------------------------------
# Theme extraction
# ---------------------------------------------------------------------------


def _analysis_theme_coverage(all_videos: list[dict]) -> float:
    if not all_videos:
        return 0.0
    have = sum(1 for v in all_videos if L.themes(v))
    return have / len(all_videos)


def _tokenize(text: str) -> list[str]:
    toks = re.split(r"[^a-z0-9]+", text.lower())
    return [t for t in toks if len(t) >= 3 and t not in _STOPWORDS and not t.isdigit()]


def _keyword_vocab(all_videos: list[dict]) -> list[str]:
    counts: Counter[str] = Counter()
    for v in all_videos:
        # Count each term once per video so a wordy caption can't dominate.
        counts.update(set(_tokenize(L.text_blob(v))))
    return [term for term, _ in counts.most_common(KEYWORD_VOCAB_SIZE)]


def build_theme_getter(all_videos: list[dict]) -> tuple[callable, str]:
    """Return (getter(video)->list[str], mode) — analysis themes or keywords."""
    if _analysis_theme_coverage(all_videos) >= THEME_COVERAGE_FLOOR:
        def getter(v: dict) -> list[str]:
            return sorted({t.strip().lower() for t in L.themes(v) if t and t.strip()})
        return getter, "analysis"

    vocab = set(_keyword_vocab(all_videos))

    def getter(v: dict) -> list[str]:
        return sorted(set(_tokenize(L.text_blob(v))) & vocab)

    return getter, "keyword"


# ---------------------------------------------------------------------------
# Cohort stats
# ---------------------------------------------------------------------------


def _cohort_stats(videos: list[dict], theme_getter) -> dict:
    n = len(videos)
    theme_counts: Counter[str] = Counter()
    theme_views: dict[str, list[float]] = {}
    for v in videos:
        vw = L.views(v)
        for t in theme_getter(v):
            theme_counts[t] += 1
            if vw is not None:
                theme_views.setdefault(t, []).append(vw)
    shares = {t: c / n for t, c in theme_counts.items()} if n else {}
    return {
        "n": n,
        "theme_counts": theme_counts,
        "theme_shares": shares,
        "theme_views": {t: L.median(vs) for t, vs in theme_views.items()},
        "median_views": L.median([vw for vw in (L.views(v) for v in videos) if vw is not None]),
        "median_er": L.median([er for er in (L.engagement_rate(v) for v in videos) if er is not None]),
        "median_duration": L.median([d for d in (L.duration(v) for v in videos) if d is not None]),
        "sequel_rate": (sum(1 for v in videos if L.is_sequel(v)) / n) if n else float("nan"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="gap.json")
    ap.add_argument("--out", default="competitor-gap-report.html")
    args = ap.parse_args()

    try:
        data = _load_gap(args.input)
    except FileNotFoundError:
        print(
            f"Could not find '{args.input}'. First call the SocialGPT MCP tools "
            "`list_videos(sort='top', limit=15, include_analysis=true)` for yourself "
            "and `list_creator_videos(platform=..., username=..., sort='top', "
            "limit=15, include_analysis=true)` for each competitor, then write a "
            f"'{args.input}' file shaped "
            '{"me": <videos>, "competitors": [{"name": "@handle", "videos": <videos>}]} '
            "and run this script again.",
            file=sys.stderr,
        )
        return 2
    except json.JSONDecodeError as exc:
        print(f"'{args.input}' is not valid JSON ({exc}). Re-write it as the "
              '{"me": ..., "competitors": [...]} envelope.', file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print("Expected a JSON object with 'me' and 'competitors' keys.", file=sys.stderr)
        return 2

    mine = L.coerce_videos(data.get("me"))
    competitors = _competitor_entries(data)
    competitors = [c for c in competitors if len(c["videos"]) >= 1]

    if not competitors:
        print(
            "No competitors found in the input. Add at least one competitor with "
            "≥3 videos: call `list_creator_videos(platform=..., username=..., "
            "sort='top', limit=15, include_analysis=true)` and put the result under "
            'competitors: [{"name": "@handle", "videos": <result>}].',
            file=sys.stderr,
        )
        return 1

    usable_comps = [c for c in competitors if len(c["videos"]) >= 3]
    if not usable_comps:
        biggest = max(competitors, key=lambda c: len(c["videos"]))
        print(
            f"No competitor has ≥3 videos (largest is '{biggest['name']}' with "
            f"{len(biggest['videos'])}). Pull more with `list_creator_videos(..., "
            "limit=15, sort='top')` and re-run.",
            file=sys.stderr,
        )
        return 1

    pooled_comp_videos = [v for c in usable_comps for v in c["videos"]]
    all_videos = mine + pooled_comp_videos
    theme_getter, theme_mode = build_theme_getter(all_videos)

    # If theme extraction produced almost nothing, we can't find gaps.
    derived = sum(len(theme_getter(v)) for v in all_videos)
    if derived == 0:
        print(
            "Couldn't derive any themes — the videos have no analysis "
            "`content_themes` and captions were empty. Re-pull with "
            "`include_analysis=true` (preferred), or ensure the videos have "
            "titles/captions, then re-run.",
            file=sys.stderr,
        )
        return 1

    me_stats = _cohort_stats(mine, theme_getter)
    comp_stats = _cohort_stats(pooled_comp_videos, theme_getter)
    per_comp = [(c["name"], _cohort_stats(c["videos"], theme_getter)) for c in usable_comps]

    gaps = _find_gaps(me_stats, comp_stats)
    owned = _find_owned(me_stats, comp_stats)

    report_path = _write_report(
        args.out, mine, usable_comps, me_stats, comp_stats, per_comp,
        gaps, owned, theme_mode,
    )
    _print_summary(mine, usable_comps, me_stats, comp_stats, gaps, owned,
                   theme_mode, report_path)
    return 0


def _find_gaps(me_stats: dict, comp_stats: dict) -> list[dict]:
    """Themes competitors cover heavily where you're silent."""
    out: list[dict] = []
    for theme, share in comp_stats["theme_shares"].items():
        comp_count = comp_stats["theme_counts"][theme]
        mine_share = me_stats["theme_shares"].get(theme, 0.0)
        if (share >= GAP_COMPETITOR_SHARE
                and comp_count >= GAP_COMPETITOR_MIN_VIDEOS
                and mine_share <= MINE_SILENT_SHARE):
            out.append({
                "theme": theme,
                "comp_share": share,
                "comp_count": comp_count,
                "comp_median_views": comp_stats["theme_views"].get(theme, float("nan")),
                "mine_share": mine_share,
            })
    out.sort(key=lambda g: (g["comp_share"],
                            g["comp_median_views"] if math.isfinite(g["comp_median_views"]) else 0.0),
             reverse=True)
    return out


def _find_owned(me_stats: dict, comp_stats: dict) -> list[dict]:
    """Themes you cover that competitors barely touch."""
    out: list[dict] = []
    for theme, count in me_stats["theme_counts"].items():
        mine_share = me_stats["theme_shares"][theme]
        comp_share = comp_stats["theme_shares"].get(theme, 0.0)
        if count >= OWNED_MINE_MIN_VIDEOS and comp_share <= OWNED_COMPETITOR_MAX_SHARE:
            out.append({
                "theme": theme,
                "mine_share": mine_share,
                "mine_count": count,
                "comp_share": comp_share,
            })
    out.sort(key=lambda o: o["mine_share"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _write_report(out, mine, usable_comps, me_stats, comp_stats, per_comp,
                  gaps, owned, theme_mode):
    n_comp = len(usable_comps)
    comp_names = ", ".join(c["name"] for c in usable_comps)

    blocks: list[dict] = []

    blocks.append(L.callout("competitors", str(n_comp),
                            comp_names or "—", "violet"))
    if gaps:
        top = gaps[0]
        blocks.append(L.callout("biggest gap", top["theme"],
                                f"{L.pct(top['comp_share'])} of their videos · "
                                f"{L.human(top['comp_median_views'])} median views",
                                "pink"))
    else:
        blocks.append(L.callout("biggest gap", "none flagged",
                                "you cover what they cover", "lime"))
    if owned:
        blocks.append(L.callout("you own", owned[0]["theme"],
                                f"{L.pct(owned[0]['mine_share'])} of your videos, "
                                "they're absent", "sky"))
    else:
        blocks.append(L.callout("you own", "nothing exclusive",
                                "no theme is yours alone", "tangerine"))

    # Gap matrix table: theme, their coverage, their reach, your coverage, verdict.
    if gaps or owned:
        rows = []
        emphasize = []
        for g in gaps:
            emphasize.append(len(rows))
            rows.append([
                g["theme"], L.pct(g["comp_share"]),
                L.human(g["comp_median_views"]), L.pct(g["mine_share"]),
                {"tag": "content gap", "kind": "hi"},
            ])
        for o in owned:
            rows.append([
                o["theme"], L.pct(o["comp_share"]), "—",
                L.pct(o["mine_share"]),
                {"tag": "you own", "kind": "sig"},
            ])
        blocks.append(L.table_block(
            "Gap matrix",
            ["Theme", "Their coverage", "Their median views", "Your coverage", "Verdict"],
            rows, num_cols=(1, 2, 3), emphasize=emphasize,
            lede=("Pink = a theme they cover heavily and you don't (a content gap). "
                  "Green = a theme you cover and they ignore (owned territory). "
                  f"Themes from {'video analysis' if theme_mode == 'analysis' else 'caption keywords'}."),
        ))
    else:
        blocks.append(L.prose_block(
            "Gap matrix",
            "No clear theme gaps either way — your coverage and the competitors' "
            "coverage overlap on the themes detected. Pull more videos per cohort "
            "(or re-pull with `include_analysis=true` for sharper themes) to surface "
            "finer-grained gaps."))

    # Format comparison: Me vs Competitors (pooled).
    blocks.append(_format_block(me_stats, comp_stats))

    # Theme distribution bars: who leans where on the top shared/contested themes.
    bar_block = _theme_bars(me_stats, comp_stats)
    if bar_block:
        blocks.append(bar_block)

    # Three angles to test.
    blocks.append(L.actions_block(
        "Three angles to test", _angles(gaps, owned, me_stats, comp_stats),
        lede="Each is grounded in a measured gap above — ship one, watch the reach."))

    html = L.render_report(
        title_html='Where competitors are <span class="hl">winning</span>',
        kicker="Competitor gap analysis",
        subtitle=(f"Your top {me_stats['n']} vs. {n_comp} competitor"
                  f"{'s' if n_comp != 1 else ''} "
                  f"({comp_stats['n']} of their videos)."),
        blocks=blocks,
        footer="Generated by the **competitor-gap-analysis** SocialGPT skill. "
               "A gap is a competitor getting reach on a topic you're absent from — "
               "a lead to test, not a guarantee. See `references/methodology.md` for "
               "the method. [gpt.social](https://gpt.social)",
    )
    return L.write_report(html, out)


def _format_block(me_stats: dict, comp_stats: dict) -> dict:
    def _row(label, mine_val, comp_val, fmt, higher_is="—"):
        m_disp = fmt(mine_val)
        c_disp = fmt(comp_val)
        if not (math.isfinite(mine_val) and math.isfinite(comp_val)):
            note = "not enough data"
        elif abs(mine_val - comp_val) < 1e-9:
            note = "even"
        elif mine_val > comp_val:
            note = f"you higher ({higher_is})"
        else:
            note = f"they higher ({higher_is})"
        return [label, m_disp, c_disp, note]

    rows = [
        _row("Median duration", me_stats["median_duration"],
             comp_stats["median_duration"], lambda x: f"{x:.0f}s" if math.isfinite(x) else "—",
             "longer"),
        _row("Sequel / series rate", me_stats["sequel_rate"],
             comp_stats["sequel_rate"], L.pct, "more series"),
        _row("Median engagement", me_stats["median_er"],
             comp_stats["median_er"], L.pct, "more engaging"),
        _row("Median views", me_stats["median_views"],
             comp_stats["median_views"], L.human, "more reach"),
    ]
    return L.table_block(
        "Format comparison", ["Metric", "You", "Competitors", "Gap"],
        rows, num_cols=(1, 2),
        lede="Cohort medians (heavy-tailed metrics, so medians not means). "
             "The 'Gap' column names who leads and on what.")


def _theme_bars(me_stats: dict, comp_stats: dict):
    """Bars for the themes with the biggest you-vs-them coverage difference."""
    themes = set(me_stats["theme_shares"]) | set(comp_stats["theme_shares"])
    scored = []
    for t in themes:
        ms = me_stats["theme_shares"].get(t, 0.0)
        cs = comp_stats["theme_shares"].get(t, 0.0)
        scored.append((t, ms, cs, abs(ms - cs)))
    scored = [s for s in scored if max(s[1], s[2]) > 0]
    scored.sort(key=lambda s: s[3], reverse=True)
    top = scored[:8]
    if not top:
        return None
    rows = []
    for i, (t, ms, cs, _diff) in enumerate(top):
        leader = "you" if ms >= cs else "competitors"
        tone = "sky" if ms >= cs else "pink"
        rows.append({
            "label": t,
            "value": max(ms, cs),
            "display": f"you {L.pct(ms)} · them {L.pct(cs)}",
            "tone": tone,
            "tag": leader,
            "tag_kind": "sig" if leader == "you" else "hi",
        })
    return L.bars_block(
        "Theme coverage — you vs. them", rows,
        lede="Bar length is the leading cohort's coverage share. "
             "Blue = you lead the theme, pink = they lead it.")


def _angles(gaps, owned, me_stats, comp_stats) -> list[str]:
    out = []
    for g in gaps[:3]:
        out.append(
            f"Make a video on **{g['theme']}** — {L.pct(g['comp_share'])} of competitor "
            f"posts cover it (median {L.human(g['comp_median_views'])} views) and you "
            f"have none. Their proven reach, your absence.")
    if len(out) < 3 and owned:
        o = owned[0]
        out.append(
            f"Double down on **{o['theme']}** — it's yours ({L.pct(o['mine_share'])} of "
            "your posts, they're absent). Press the advantage before they notice.")
    if not out:
        out.append(
            "No theme gap cleared the bar — your topic mix already overlaps the "
            "competitors'. Compete on format instead: see the format table for where "
            "you trail (duration, series, engagement).")
    # Always leave a format-based angle if there's an obvious gap.
    if math.isfinite(me_stats["sequel_rate"]) and math.isfinite(comp_stats["sequel_rate"]) \
            and comp_stats["sequel_rate"] - me_stats["sequel_rate"] >= 0.15 and len(out) < 3:
        out.append(
            f"Test a series — competitors run sequels {L.pct(comp_stats['sequel_rate'])} of "
            f"the time vs. your {L.pct(me_stats['sequel_rate'])}. Serialized content compounds "
            "watch-through; pick a winning topic and make it a Part 2.")
    return out[:3] if len(out) >= 3 else out


# ---------------------------------------------------------------------------
# Stdout summary
# ---------------------------------------------------------------------------


def _print_summary(mine, usable_comps, me_stats, comp_stats, gaps, owned,
                   theme_mode, report_path):
    n_comp = len(usable_comps)
    names = ", ".join(c["name"] for c in usable_comps)
    print(f"# Competitor gap analysis — you ({me_stats['n']} videos) vs. "
          f"{n_comp} competitor{'s' if n_comp != 1 else ''} "
          f"({comp_stats['n']} videos: {names})\n")
    print(f"_Themes derived from {'video analysis' if theme_mode == 'analysis' else 'caption keywords'}._\n")

    if gaps:
        print("**Content gaps — they cover it, you don't:**\n")
        for g in gaps[:5]:
            print(f"- **{g['theme']}** — {L.pct(g['comp_share'])} of their videos "
                  f"({g['comp_count']} posts), median {L.human(g['comp_median_views'])} "
                  "views; you have none.")
    else:
        print("**Content gaps:** none — your topic coverage already overlaps theirs.")
    print()

    if owned:
        print("**Owned territory — yours, they ignore:**\n")
        for o in owned[:5]:
            print(f"- **{o['theme']}** — {L.pct(o['mine_share'])} of your videos, "
                  f"competitors {L.pct(o['comp_share'])}.")
    else:
        print("**Owned territory:** nothing is exclusively yours in this set.")
    print()

    print("**Format (medians, you vs. them):**\n")
    print(f"- Duration: {me_stats['median_duration']:.0f}s vs. {comp_stats['median_duration']:.0f}s"
          if math.isfinite(me_stats['median_duration']) and math.isfinite(comp_stats['median_duration'])
          else "- Duration: insufficient data")
    print(f"- Sequel rate: {L.pct(me_stats['sequel_rate'])} vs. {L.pct(comp_stats['sequel_rate'])}")
    print(f"- Engagement: {L.pct(me_stats['median_er'])} vs. {L.pct(comp_stats['median_er'])}")
    print(f"- Median views: {L.human(me_stats['median_views'])} vs. {L.human(comp_stats['median_views'])}")
    print()

    print("**Angles to test:**")
    for a in _angles(gaps, owned, me_stats, comp_stats):
        print(f"- {a}")
    print(f"\nFull visual report written to `{report_path}` — open it in a browser "
          "(offer it to the user to download).")


if __name__ == "__main__":
    raise SystemExit(main())
