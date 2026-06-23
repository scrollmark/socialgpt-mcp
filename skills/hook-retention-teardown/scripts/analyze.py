#!/usr/bin/env python3
"""Hook & retention teardown — what your best hooks do that your flops don't.

Reads a JSON file (saved by the agent) holding the *full* SocialGPT MCP
``get_video_analysis`` results for the caller's top and bottom performers, shaped:

    {
      "top":    [ <get_video_analysis result>, ... ],   # best-performing videos
      "bottom": [ <get_video_analysis result>, ... ]     # worst-performing videos
    }

For every video that has a transcript it computes deterministic text/pacing
metrics (words-per-second, time-to-first-hook, first-person vs instructional
language, specificity, curiosity-word density, CTA usage, hook style), then
compares the *top* cohort against the *bottom* cohort and surfaces the
dimensions where they differ most. Writes an on-brand HTML report and prints a
concise Markdown summary for the agent to relay.

Usage:
    python scripts/analyze.py teardown.json
    python scripts/analyze.py teardown.json --out my-report.html

The model that runs this skill is responsible for first assembling
``teardown.json`` from ``get_video_analysis`` calls (see SKILL.md).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter

import sgpt_lib as L

# ---------------------------------------------------------------------------
# Word lists / regexes (deterministic, built-in)
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[A-Za-z']+")
_NUMBER_RE = re.compile(r"\b\d[\d,.]*\b|\b\d+%|\$\d")
_FIRST_PERSON = {"i", "i'm", "i've", "i'll", "i'd", "me", "my", "mine", "we",
                 "we're", "we've", "us", "our", "ours"}
_INSTRUCTIONAL = {"you", "you're", "you've", "you'll", "you'd", "your", "yours"}
_CURIOSITY = {"actually", "honestly", "surprisingly", "nobody", "secret",
              "truth", "mistake", "never", "always", "stop", "why", "wrong",
              "everyone", "real", "really"}
_CTA_TERMS = ["follow", "comment", "link in bio", "link", "save this", "save",
              "share", "subscribe", "dm me", "sign up"]
_QUESTION_OPENERS = {"why", "what", "how", "when", "where", "who", "which",
                     "do", "does", "did", "is", "are", "can", "should", "would"}
_BOLD_CLAIM = {"never", "always", "everyone", "nobody", "stop", "the", "this",
               "biggest", "best", "worst", "only", "most"}
_STORY_OPENERS = {"i", "when", "so", "my", "last", "yesterday", "today",
                  "back", "once"}
_LISTICLE = {"here", "three", "five", "two", "four", "top", "ways"}


# ---------------------------------------------------------------------------
# Per-video metric extraction
# ---------------------------------------------------------------------------


def _transcript_text(item: dict) -> str:
    """Best-effort transcript string from a get_video_analysis result."""
    t = item.get("transcript")
    if isinstance(t, str) and t.strip():
        return t.strip()
    segs = item.get("transcript_segments")
    if isinstance(segs, list):
        parts = [str(s.get("text") or "") for s in segs if isinstance(s, dict)]
        joined = " ".join(p.strip() for p in parts if p.strip())
        if joined.strip():
            return joined.strip()
    return ""


def _opening_words(item: dict, transcript: str, n: int = 12) -> str:
    """First ~n words of the transcript, falling back to suggested/hook text."""
    words = _WORD_RE.findall(transcript)
    if words:
        return " ".join(words[:n])
    sug = item.get("suggested_hooks")
    if isinstance(sug, list) and sug:
        return str(sug[0])
    hooks = item.get("hooks")
    if isinstance(hooks, list) and hooks:
        h0 = hooks[0]
        if isinstance(h0, dict):
            return str(h0.get("text") or h0.get("hook") or h0.get("title") or "")
        return str(h0)
    return ""


def _classify_hook(opening: str) -> str:
    """question | bold-claim | story | listicle | visual/other."""
    if not opening.strip():
        return "visual/other"
    if "?" in opening:
        return "question"
    words = [w.lower() for w in _WORD_RE.findall(opening)]
    if not words:
        return "visual/other"
    first = words[0]
    if first in _QUESTION_OPENERS:
        return "question"
    if first in _LISTICLE or any(w.isdigit() for w in re.findall(r"\b\w+\b", opening)) \
            or _NUMBER_RE.search(opening):
        return "listicle"
    if first in _STORY_OPENERS:
        return "story"
    if first in _BOLD_CLAIM:
        return "bold-claim"
    return "visual/other"


def _cta_position(transcript: str) -> str:
    """early | middle | late | absent — first CTA term's relative position."""
    low = transcript.lower()
    n = len(transcript)
    if n == 0:
        return "absent"
    first_at: int | None = None
    for term in _CTA_TERMS:
        idx = low.find(term)
        if idx != -1 and (first_at is None or idx < first_at):
            first_at = idx
    if first_at is None:
        return "absent"
    frac = first_at / n
    if frac < 0.34:
        return "early"
    if frac < 0.67:
        return "middle"
    return "late"


def _time_to_hook(item: dict, transcript: str) -> float | None:
    """Approx seconds until the first segment carrying a question/number/opener."""
    segs = item.get("transcript_segments")
    if not isinstance(segs, list) or not segs:
        return 0.0  # no segment timing — treat the open itself as the hook
    for seg in segs:
        if not isinstance(seg, dict):
            continue
        text = str(seg.get("text") or "")
        if not text.strip():
            continue
        low = text.lower()
        hooky = ("?" in text or _NUMBER_RE.search(text)
                 or any(w in low.split() for w in _QUESTION_OPENERS)
                 or low.split()[:1] and low.split()[0] in _STORY_OPENERS)
        if hooky:
            start = seg.get("start")
            n = L._num(start) if hasattr(L, "_num") else None
            return float(n) if n is not None else 0.0
    return 0.0


def per_video_metrics(item: dict) -> dict | None:
    """Deterministic text/pacing metrics for one get_video_analysis result.

    Returns None when the video has no usable transcript.
    """
    if not isinstance(item, dict):
        return None
    post = item.get("post") if isinstance(item.get("post"), dict) else {}
    transcript = _transcript_text(item)
    if not transcript:
        return None

    words = _WORD_RE.findall(transcript)
    word_count = len(words)
    if word_count == 0:
        return None
    low_words = [w.lower() for w in words]

    dur = L.duration(post) or L.duration(item)
    wps = (word_count / dur) if (dur and dur > 0) else None

    fp = sum(1 for w in low_words if w in _FIRST_PERSON)
    instr = sum(1 for w in low_words if w in _INSTRUCTIONAL)
    # Ratio of first-person to instructional language (>1 = more personal).
    fp_ratio = fp / instr if instr else (float(fp) if fp else 0.0)

    numbers = len(_NUMBER_RE.findall(transcript))
    # Proper-noun-ish: Capitalized tokens that are not sentence-initial-only.
    proper = sum(1 for w in words[1:] if w[:1].isupper())
    specificity = (numbers + proper) / word_count  # per-word density

    curiosity = sum(1 for w in low_words if w in _CURIOSITY)
    curiosity_density = curiosity / word_count

    opening = _opening_words(item, transcript)
    hook_style = _classify_hook(opening)
    cta_pos = _cta_position(transcript)
    t2h = _time_to_hook(item, transcript)

    title = post.get("title") or item.get("title") or "(untitled)"

    return {
        "title": str(title),
        "platform": L.platform(post) if post else L.platform(item),
        "views": L.views(post) if post else L.views(item),
        "word_count": word_count,
        "duration": dur,
        "wps": wps,
        "time_to_hook": t2h,
        "fp_ratio": fp_ratio,
        "specificity": specificity,
        "curiosity_density": curiosity_density,
        "cta_position": cta_pos,
        "hook_style": hook_style,
        "opening": opening,
    }


# ---------------------------------------------------------------------------
# Cohort aggregation
# ---------------------------------------------------------------------------

# Numeric dimensions: (key, label, unit, "higher"/"lower" is-better-for-context).
NUMERIC_DIMS = [
    ("wps", "Words per second", "words/sec"),
    ("time_to_hook", "Time to first hook", "sec"),
    ("fp_ratio", "First-person : instructional", "ratio"),
    ("specificity", "Specificity (numbers/proper nouns)", "per word"),
    ("curiosity_density", "Curiosity-word density", "per word"),
]


def _median_of(rows: list[dict], key: str) -> float | None:
    xs = [r[key] for r in rows if isinstance(r.get(key), (int, float))
          and math.isfinite(r[key])]
    return L.median(xs) if xs else None


def _majority(rows: list[dict], key: str) -> tuple[str, float]:
    """Most common categorical value and its share of the cohort."""
    vals = [r.get(key) for r in rows if r.get(key)]
    if not vals:
        return ("—", 0.0)
    c = Counter(vals)
    val, count = c.most_common(1)[0]
    return (str(val), count / len(vals))


def _cta_present_share(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    present = sum(1 for r in rows if r.get("cta_position") not in (None, "absent"))
    return present / len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="teardown.json")
    ap.add_argument("--out", default="hook-retention-teardown.html")
    args = ap.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except FileNotFoundError:
        print(
            f"Could not find '{args.input}'. First call `list_videos(sort='top', "
            "limit=20)`, pick your ~5 best and ~5 worst by metrics.views (skip "
            "Instagram videos with views==0), call `get_video_analysis(platform, "
            "post_id)` for each, and save them as "
            f'{{"top":[...],"bottom":[...]}} to \'{args.input}\', then re-run.',
            file=sys.stderr,
        )
        return 2
    except json.JSONDecodeError as exc:
        print(f"'{args.input}' is not valid JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print(
            f"'{args.input}' must be a JSON object shaped "
            '{"top":[...],"bottom":[...]}.',
            file=sys.stderr,
        )
        return 2

    top_items = payload.get("top") if isinstance(payload.get("top"), list) else []
    bottom_items = payload.get("bottom") if isinstance(payload.get("bottom"), list) else []

    top = [m for m in (per_video_metrics(i) for i in top_items) if m]
    bottom = [m for m in (per_video_metrics(i) for i in bottom_items) if m]
    n_top, n_bottom = len(top), len(bottom)
    n_total = n_top + n_bottom

    # Degrade gracefully: need a real comparison to say anything honest.
    if not (n_top >= 2 and n_bottom >= 2) and n_total < 3:
        n_pending = (
            len([i for i in top_items if isinstance(i, dict)
                 and not _transcript_text(i)])
            + len([i for i in bottom_items if isinstance(i, dict)
                   and not _transcript_text(i)])
        )
        print(
            f"Not enough analyzed videos with transcripts (top={n_top}, "
            f"bottom={n_bottom}). Need at least 2 in each cohort, or 3 total. "
            + (
                f"{n_pending} of the supplied videos have no transcript yet — "
                "their analysis may still be pending (re-read with "
                "`get_video_analysis` after ~20s) "
                if n_pending else ""
            )
            + "— or fetch a few more top/bottom performers and re-run.",
            file=sys.stderr,
        )
        return 1

    report_path = _write_report(args.out, top, bottom)
    _print_summary(top, bottom, report_path)
    return 0


def _compute_dims(top: list[dict], bottom: list[dict]) -> list[dict]:
    """One row per dimension with top vs bottom values + a normalized gap."""
    dims: list[dict] = []
    for key, label, unit in NUMERIC_DIMS:
        t = _median_of(top, key)
        b = _median_of(bottom, key)
        gap = None
        if t is not None and b is not None:
            denom = max(abs(t), abs(b), 1e-9)
            gap = abs(t - b) / denom  # 0..~1+ relative gap
        dims.append({
            "key": key, "label": label, "unit": unit, "kind": "numeric",
            "top": t, "bottom": b, "gap": gap,
        })

    # CTA usage (share of cohort that has any CTA).
    t_cta = _cta_present_share(top)
    b_cta = _cta_present_share(bottom)
    dims.append({
        "key": "cta_usage", "label": "CTA usage (share with a CTA)", "unit": "share",
        "kind": "share", "top": t_cta, "bottom": b_cta, "gap": abs(t_cta - b_cta),
    })

    # Dominant hook style (majority + share); gap = 1 when winners/losers differ.
    t_hook, t_share = _majority(top, "hook_style")
    b_hook, b_share = _majority(bottom, "hook_style")
    dims.append({
        "key": "hook_style", "label": "Dominant hook style", "unit": "",
        "kind": "category", "top": t_hook, "bottom": b_hook,
        "top_share": t_share, "bottom_share": b_share,
        "gap": (1.0 if t_hook != b_hook else 0.0),
    })
    return dims


def _fmt_dim_value(dim: dict, which: str) -> str:
    v = dim[which]
    if dim["kind"] == "numeric":
        if v is None:
            return "—"
        if dim["key"] in ("specificity", "curiosity_density"):
            return f"{v:.3f}".rstrip("0").rstrip(".")
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if dim["kind"] == "share":
        return L.pct(v)
    # category
    share = dim.get(f"{which}_share", 0.0)
    return f"{v} ({L.pct(share)})"


def _dim_insight(dim: dict) -> str:
    """Plain-English read of which cohort leans which way."""
    if dim["kind"] == "category":
        if dim["top"] == dim["bottom"]:
            return f"both lean {dim['top']}"
        return f"winners: {dim['top']} · flops: {dim['bottom']}"
    t, b = dim["top"], dim["bottom"]
    if t is None or b is None:
        return "—"
    if dim["kind"] == "share":
        diff = (t - b) * 100
        if abs(diff) < 1:
            return "about even"
        return f"winners {'+' if diff > 0 else ''}{diff:.0f}pts"
    diff = t - b
    if abs(diff) < 1e-9:
        return "about even"
    return f"winners {'higher' if diff > 0 else 'lower'}"


def _biggest_differentiator(dims: list[dict]) -> dict | None:
    scored = [d for d in dims if isinstance(d.get("gap"), (int, float))
              and math.isfinite(d["gap"])]
    if not scored:
        return None
    return max(scored, key=lambda d: d["gap"])


def _write_report(out, top, bottom):
    dims = _compute_dims(top, bottom)
    n_top, n_bottom = len(top), len(bottom)
    n_total = n_top + n_bottom
    big = _biggest_differentiator(dims)
    top_wps = _median_of(top, "wps")

    blocks: list[dict] = []

    # Callouts.
    blocks.append(L.callout("videos analyzed", str(n_total),
                            f"{n_top} winners vs {n_bottom} flops", "violet"))
    if big is not None:
        if big["kind"] == "category":
            note = f"{_fmt_dim_value(big, 'top')} vs {_fmt_dim_value(big, 'bottom')}"
        else:
            note = f"{_fmt_dim_value(big, 'top')} vs {_fmt_dim_value(big, 'bottom')} (winners vs flops)"
        blocks.append(L.callout("biggest differentiator", big["label"], note, "pink"))
    blocks.append(L.callout("winners' pace",
                            (f"{top_wps:.2f}".rstrip("0").rstrip(".") + " w/s")
                            if top_wps is not None else "—",
                            "median words per second", "sky"))

    # Side-by-side comparison table.
    rows = []
    emphasize = []
    for i, d in enumerate(dims):
        if big is not None and d["key"] == big["key"]:
            emphasize.append(i)
        rows.append([
            d["label"],
            _fmt_dim_value(d, "top"),
            _fmt_dim_value(d, "bottom"),
            _dim_insight(d),
        ])
    blocks.append(L.table_block(
        "Winners vs flops, side by side",
        ["Dimension", "Top performers", "Bottom performers", "Gap / insight"],
        rows, num_cols=(1, 2), emphasize=emphasize,
        lede="Numeric rows are cohort medians; categorical rows show the dominant "
             "value and its share. The highlighted row is the biggest gap.",
    ))

    # Hook styles among winners (bars).
    hook_counts = Counter(r["hook_style"] for r in top)
    order = ["question", "bold-claim", "story", "listicle", "visual/other"]
    bar_rows = []
    for style in order:
        c = hook_counts.get(style, 0)
        if c == 0:
            continue
        share = c / n_top
        bar_rows.append({
            "label": style, "value": share,
            "display": f"{c}/{n_top} · {L.pct(share)}",
            "tone": "lime" if share >= 0.5 else "violet",
        })
    # Any styles not in the canonical order.
    for style, c in hook_counts.items():
        if style not in order:
            share = c / n_top
            bar_rows.append({"label": style, "value": share,
                             "display": f"{c}/{n_top} · {L.pct(share)}",
                             "tone": "violet"})
    if bar_rows:
        bar_rows.sort(key=lambda r: r["value"], reverse=True)
        blocks.append(L.bars_block(
            "Hook styles among your winners",
            bar_rows,
            lede="How your best-performing openers break down by style.",
        ))

    # Actions.
    blocks.append(L.actions_block(
        "Patterns to copy from your winners",
        _actions(top, bottom, dims, big),
        lede="Plain-English moves your best hooks make that your flops don't.",
    ))

    platforms = sorted({r["platform"] for r in top + bottom if r.get("platform")})
    html = L.render_report(
        title_html='What your <span class="hl">best hooks</span> do differently',
        kicker="Hook & retention teardown",
        subtitle=f"A line-by-line read of {n_top} winners vs {n_bottom} flops"
                 + (f" across {', '.join(platforms)}." if platforms else "."),
        blocks=blocks,
        footer="Generated by the **hook-retention-teardown** SocialGPT skill. "
               "Metrics are deterministic counts on your own transcripts — they "
               "describe *what differs*, not why it works; treat each pattern as a "
               "lead to A/B test. See `references/methodology.md` for the method. "
               "[gpt.social](https://gpt.social)",
    )
    return L.write_report(html, out)


def _actions(top, bottom, dims, big) -> list[str]:
    """Three plain-English patterns the winners use that the flops don't."""
    out: list[str] = []
    by_key = {d["key"]: d for d in dims}

    # 1. Pacing.
    wps = by_key.get("wps")
    if wps and wps["top"] is not None and wps["bottom"] is not None:
        if wps["top"] > wps["bottom"] * 1.05:
            out.append(
                f"**Talk faster up top.** Your winners pace at "
                f"{_fmt_dim_value(wps, 'top')} words/sec vs "
                f"{_fmt_dim_value(wps, 'bottom')} on flops — tighten the script and "
                "cut dead air in the first few seconds.")
        elif wps["top"] < wps["bottom"] * 0.95:
            out.append(
                f"**Slow down and land each line.** Winners sit at "
                f"{_fmt_dim_value(wps, 'top')} words/sec vs the rushed "
                f"{_fmt_dim_value(wps, 'bottom')} on flops — give the hook room to breathe.")

    # 2. Hook style.
    hook = by_key.get("hook_style")
    if hook and hook["top"] != hook["bottom"]:
        out.append(
            f"**Open with a {hook['top']} hook.** "
            f"{L.pct(hook.get('top_share', 0))} of your winners do, while your flops "
            f"lean {hook['bottom']} — match the winning opener style.")

    # 3. Language: first-person / curiosity.
    fp = by_key.get("fp_ratio")
    cur = by_key.get("curiosity_density")
    if fp and fp["top"] is not None and fp["bottom"] is not None and fp["top"] > fp["bottom"] * 1.1:
        out.append(
            "**Make it personal.** Winners skew first-person ("
            f"{_fmt_dim_value(fp, 'top')} vs {_fmt_dim_value(fp, 'bottom')} "
            "first-person-to-'you' ratio) — say 'I' and 'my' instead of lecturing.")
    elif cur and cur["top"] is not None and cur["bottom"] is not None and cur["top"] > cur["bottom"] * 1.1:
        out.append(
            "**Plant more curiosity words.** Winners pack more open-loop language "
            "('actually', 'nobody', 'secret', 'why') into the script — seed one in "
            "the first line.")

    # Fill to 3 with the single biggest differentiator if needed.
    if big is not None and len(out) < 3:
        if big["kind"] == "category":
            out.append(
                f"**Lean into your '{big['top']}' edge.** It's the dimension where "
                "winners and flops diverge most — replicate it deliberately.")
        else:
            direction = "raise" if (big["top"] or 0) > (big["bottom"] or 0) else "lower"
            out.append(
                f"**{direction.capitalize()} your {big['label'].lower()}.** It's the "
                f"widest gap between winners ({_fmt_dim_value(big, 'top')}) and flops "
                f"({_fmt_dim_value(big, 'bottom')}) — copy what your best posts do.")

    if not out:
        out.append(
            "Winners and flops look similar on these text metrics — the difference "
            "is likely visual or topical. Pull a few more of each and re-run, or "
            "lean on qualitative hook review.")
    return out[:3]


def _print_summary(top, bottom, report_path):
    dims = _compute_dims(top, bottom)
    n_top, n_bottom = len(top), len(bottom)
    big = _biggest_differentiator(dims)

    print(f"# Hook & retention teardown — {n_top} winners vs {n_bottom} flops\n")
    if big is not None:
        print(f"**Biggest differentiator:** {big['label']} — "
              f"winners {_fmt_dim_value(big, 'top')} vs flops "
              f"{_fmt_dim_value(big, 'bottom')}.\n")

    print("**Winners vs flops (median / dominant):**\n")
    for d in dims:
        print(f"- **{d['label']}** — winners {_fmt_dim_value(d, 'top')}, "
              f"flops {_fmt_dim_value(d, 'bottom')} ({_dim_insight(d)}).")

    top_hooks = Counter(r["hook_style"] for r in top)
    if top_hooks:
        styles = ", ".join(f"{s} {c}/{n_top}" for s, c in top_hooks.most_common())
        print(f"\n**Winners' hook styles:** {styles}.")

    print("\n**Patterns to copy:**")
    for a in _actions(top, bottom, dims, big):
        print(f"- {a}")

    print(f"\nFull visual report written to `{report_path}` — open it in a browser "
          "(offer it to the user to download).")


if __name__ == "__main__":
    raise SystemExit(main())
