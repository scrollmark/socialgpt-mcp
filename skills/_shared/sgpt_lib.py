"""Shared helpers for the SocialGPT MCP skills.

This module is intentionally **dependency-free** (Python 3.9+ standard library
only) and **vendored** into each skill's ``scripts/`` directory by ``build.py``
so that every skill folder is a self-contained, independently-installable
artifact (Claude.ai uploads one skill at a time as a zip).

It does three jobs:

1. **IO / field access** — parse whatever the SocialGPT MCP tools returned
   (an ``{"videos": [...]}`` envelope, a bare list, or NDJSON) into plain dicts,
   and read the documented ``McpPostSummary`` fields defensively.
2. **Statistics** — Pearson correlation and Kruskal-Wallis with *real* p-values
   (Student-t and chi-square tails computed from the regularized incomplete beta
   and gamma functions). No SciPy, no NumPy. This is the deterministic rigor a
   bundled script buys you over asking the model to "run a correlation".
3. **Reporting** — render a self-contained, on-brand ("Sticker Energy") HTML
   report the agent can hand back to the user.

Nothing here is SocialGPT-internal; it only consumes the public MCP tool output.
"""

from __future__ import annotations

import html
import json
import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Sequence

# ---------------------------------------------------------------------------
# IO + field access
# ---------------------------------------------------------------------------


def load_videos(path: str) -> list[dict[str, Any]]:
    """Load a list of video dicts from a file the agent saved the MCP output to.

    Accepts any of:
      * the tool envelope ``{"videos": [...]}`` (what list_videos returns),
      * a bare JSON list ``[...]``,
      * a single ``{"video": {...}}`` / video dict,
      * NDJSON (one JSON object per line).
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read().strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # NDJSON fallback.
        out: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return [v for v in out if isinstance(v, dict)]
    return coerce_videos(data)


def coerce_videos(data: Any) -> list[dict[str, Any]]:
    """Normalize a parsed JSON payload into a flat list of video dicts."""
    if isinstance(data, list):
        return [v for v in data if isinstance(v, dict)]
    if isinstance(data, dict):
        for key in ("videos", "results", "items", "data"):
            if isinstance(data.get(key), list):
                return [v for v in data[key] if isinstance(v, dict)]
        if isinstance(data.get("video"), dict):
            return [data["video"]]
        # A single video object.
        if "post_id" in data or "metrics" in data:
            return [data]
    return []


def _metrics(v: dict[str, Any]) -> dict[str, Any]:
    m = v.get("metrics")
    return m if isinstance(m, dict) else {}


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def views(v: dict[str, Any]) -> float | None:
    m = _metrics(v)
    for key in ("views", "view_count", "play_count", "plays"):
        n = _num(m.get(key) if key in m else v.get(key))
        if n is not None:
            return n
    return None


def engagement_rate(v: dict[str, Any]) -> float | None:
    m = _metrics(v)
    er = _num(m.get("engagement_rate"))
    if er is not None:
        return er
    # Derive a fallback from raw interactions / views when not provided.
    vw = views(v)
    if vw and vw > 0:
        inter = sum(
            _num(m.get(k)) or 0.0 for k in ("likes", "comments", "shares", "saves")
        )
        return inter / vw
    return None


def interactions(v: dict[str, Any]) -> float:
    m = _metrics(v)
    return sum(_num(m.get(k)) or 0.0 for k in ("likes", "comments", "shares", "saves"))


def duration(v: dict[str, Any]) -> float | None:
    for key in ("duration", "duration_seconds", "length"):
        n = _num(v.get(key))
        if n is not None and n > 0:
            return n
    return None


def platform(v: dict[str, Any]) -> str:
    return str(v.get("platform") or "unknown").lower()


def text_blob(v: dict[str, Any]) -> str:
    return " ".join(str(v.get(k) or "") for k in ("title", "caption")).strip()


def themes(v: dict[str, Any]) -> list[str]:
    """Best-effort content themes from the analysis preview / inline analysis."""
    out: list[str] = []
    for src in (v.get("content_themes"), (v.get("analysis_preview") or {}).get("content_themes")):
        if isinstance(src, list):
            out.extend(str(t) for t in src if t)
    return out


def created_at(v: dict[str, Any]) -> datetime | None:
    raw = v.get("post_created_time") or v.get("created_at") or v.get("timestamp")
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        try:
            return datetime.utcfromtimestamp(float(raw))
        except (ValueError, OverflowError, OSError):
            return None
    s = str(raw).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s[: len(fmt) + 2], fmt)
            except ValueError:
                continue
    return None


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def weekday(v: dict[str, Any]) -> str | None:
    dt = created_at(v)
    return WEEKDAYS[dt.weekday()] if dt else None


def hour_bucket(v: dict[str, Any]) -> str | None:
    dt = created_at(v)
    if not dt:
        return None
    h = dt.hour
    if h < 6:
        return "late night (0-6)"
    if h < 12:
        return "morning (6-12)"
    if h < 18:
        return "afternoon (12-18)"
    return "evening (18-24)"


_SEQUEL_RE = re.compile(r"\b(part\s*\d+|pt\s*\d+|episode\s*\d+|ep\s*\d+|#\d+)\b", re.I)


def is_sequel(v: dict[str, Any]) -> bool:
    return bool(_SEQUEL_RE.search(text_blob(v)))


# ---------------------------------------------------------------------------
# Statistics (stdlib only; real p-values)
# ---------------------------------------------------------------------------


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def stdev(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mu = mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def student_t_sf(t: float, df: float) -> float:
    """Two-sided p-value for a Student-t statistic with ``df`` degrees of freedom."""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    return betainc(df / 2.0, 0.5, x)  # already two-sided


def _gammaincc(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) = 1 - P(a, x)."""
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        # Series for the lower incomplete gamma, then complement.
        term = 1.0 / a
        total = term
        n = a
        for _ in range(500):
            n += 1.0
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        p = total * math.exp(-x + a * math.log(x) - math.lgamma(a))
        return 1.0 - p
    # Lentz continued fraction for the upper incomplete gamma.
    tiny = 1e-30
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(stat: float, df: int) -> float:
    """Survival function (upper tail p-value) of the chi-square distribution."""
    if df <= 0 or stat < 0:
        return float("nan")
    return _gammaincc(df / 2.0, stat / 2.0)


def pearson(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float, int]:
    """Pearson r, two-sided p-value, and n for paired samples."""
    pairs = [(x, y) for x, y in zip(xs, ys) if _finite(x) and _finite(y)]
    n = len(pairs)
    if n < 3:
        return float("nan"), float("nan"), n
    xv = [p[0] for p in pairs]
    yv = [p[1] for p in pairs]
    mx, my = mean(xv), mean(yv)
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    sxx = sum((x - mx) ** 2 for x in xv)
    syy = sum((y - my) ** 2 for y in yv)
    if sxx <= 0 or syy <= 0:
        return float("nan"), float("nan"), n
    r = sxy / math.sqrt(sxx * syy)
    r = max(-0.999999, min(0.999999, r))
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p = student_t_sf(t, n - 2)
    return r, p, n


def kruskal_wallis(groups: Sequence[Sequence[float]]) -> tuple[float, float, int]:
    """Kruskal-Wallis H test across 2+ groups. Returns (H, p, total_n).

    Non-parametric (rank-based), so it is robust to the heavy-tailed view-count
    distribution. p comes from the chi-square approximation with k-1 df.
    """
    clean = [[x for x in g if _finite(x)] for g in groups]
    clean = [g for g in clean if g]
    k = len(clean)
    if k < 2:
        return float("nan"), float("nan"), 0
    pooled: list[tuple[float, int]] = []
    for gi, g in enumerate(clean):
        for x in g:
            pooled.append((x, gi))
    n = len(pooled)
    if n < 3:
        return float("nan"), float("nan"), n
    pooled.sort(key=lambda t: t[0])
    ranks = _ranks_with_ties([p[0] for p in pooled])
    rank_sum = [0.0] * k
    for (_, gi), rk in zip(pooled, ranks):
        rank_sum[gi] += rk
    h = 12.0 / (n * (n + 1)) * sum(
        (rank_sum[gi] ** 2) / len(clean[gi]) for gi in range(k)
    ) - 3.0 * (n + 1)
    h = _tie_correct(h, [p[0] for p in pooled], n)
    p = chi2_sf(h, k - 1)
    return h, p, n


def _ranks_with_ties(values: Sequence[float]) -> list[float]:
    """Average ranks (1-based) for an already-sorted sequence."""
    ranks = [0.0] * len(values)
    i = 0
    n = len(values)
    while i < n:
        j = i
        while j + 1 < n and values[j + 1] == values[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    return ranks


def _tie_correct(h: float, sorted_vals: Sequence[float], n: int) -> float:
    counts = Counter(sorted_vals)
    correction = sum(c**3 - c for c in counts.values())
    denom = n**3 - n
    if denom <= 0 or correction == 0:
        return h
    return h / (1.0 - correction / denom)


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def significance_label(p: float) -> str:
    if not _finite(p):
        return "n/a"
    if p < 0.01:
        return "highly significant"
    if p < 0.05:
        return "significant"
    if p < 0.1:
        return "suggestive"
    return "not significant"


def effect_word(r: float) -> str:
    a = abs(r)
    if a >= 0.5:
        return "strong"
    if a >= 0.3:
        return "moderate"
    if a >= 0.1:
        return "weak"
    return "negligible"


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def human(n: float | None) -> str:
    if n is None or (isinstance(n, float) and not math.isfinite(n)):
        return "—"
    n = float(n)
    for unit, div in (("M", 1_000_000), ("K", 1_000)):
        if abs(n) >= div:
            return f"{n / div:.1f}".rstrip("0").rstrip(".") + unit
    if abs(n) < 1 and n != 0:
        return f"{n:.3f}".rstrip("0").rstrip(".")
    return f"{n:,.0f}"


def pct(n: float | None) -> str:
    if n is None or not math.isfinite(n):
        return "—"
    return f"{n * 100:.1f}%"


# ---------------------------------------------------------------------------
# HTML report ("Sticker Energy")
# ---------------------------------------------------------------------------

_TONES = {
    "pink": "#FF4D8D",
    "violet": "#7B5BFF",
    "lime": "#C5F53C",
    "sky": "#53CDFF",
    "tangerine": "#FF8A3D",
    "butter": "#FFD43F",
    "ink": "#211633",
}

_REPORT_CSS = """
:root{--paper:#FFFDF8;--ink:#211633;--card:#fff;--pink:#FF4D8D;--violet:#7B5BFF;
--lime:#C5F53C;--sky:#53CDFF;--tangerine:#FF8A3D;--butter:#FFD43F;
--pink-tint:#FFE9F2;--violet-tint:#EFEAFF;--lime-tint:#F3FBDC;--sky-tint:#E4F7FF;--butter-tint:#FFF5D6;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font-family:"Hanken Grotesk",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:48px 24px 96px}
.kicker{display:inline-block;font-weight:600;font-size:.8125rem;letter-spacing:.08em;
text-transform:uppercase;color:var(--violet);background:var(--violet-tint);
border:3px solid #fff;border-radius:999px;padding:8px 16px;
box-shadow:0 2px 0 rgba(33,22,51,.16),0 10px 24px rgba(33,22,51,.12);transform:rotate(-2deg)}
h1{font-family:"Bricolage Grotesque",sans-serif;font-weight:800;letter-spacing:-.03em;
line-height:1.0;font-size:clamp(2.2rem,5vw,3.4rem);margin:24px 0 8px}
h1 .hl{color:var(--pink)}
.sub{color:rgba(33,22,51,.6);font-size:1.05rem;margin:0}
h2{font-family:"Bricolage Grotesque",sans-serif;font-weight:700;letter-spacing:-.02em;
font-size:1.6rem;margin:48px 0 6px}
.lede{color:rgba(33,22,51,.6);margin:0 0 18px}
.card{background:var(--card);border-radius:20px;padding:24px;
box-shadow:0 2px 0 rgba(33,22,51,.06),0 12px 30px rgba(33,22,51,.08);margin-top:16px}
.callouts{display:flex;flex-wrap:wrap;gap:14px;margin-top:20px}
.callout{flex:1 1 160px;border-radius:18px;padding:18px 20px;border:2px solid var(--ink)}
.callout .lab{font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;opacity:.65}
.callout .val{font-family:"Bricolage Grotesque",sans-serif;font-weight:800;font-size:1.5rem;line-height:1.1;margin-top:4px}
.callout .note{font-size:.85rem;opacity:.7;margin-top:4px}
table{width:100%;border-collapse:collapse;margin-top:4px;font-size:.93rem}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid rgba(33,22,51,.08)}
th{font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;color:rgba(33,22,51,.55);font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr.em td{background:var(--lime-tint)}
.tag{display:inline-block;font-size:.74rem;font-weight:600;padding:3px 10px;border-radius:999px;
background:rgba(33,22,51,.06);color:rgba(33,22,51,.7)}
.tag.sig{background:var(--lime-tint);color:#3f5e00}
.tag.hi{background:var(--pink-tint);color:#a3174e}
.bar-row{display:grid;grid-template-columns:200px 1fr auto;align-items:center;gap:14px;margin:10px 0}
.bar-row .blab{font-weight:600;font-size:.92rem}
.bar-track{height:16px;background:rgba(33,22,51,.06);border-radius:999px;overflow:hidden}
.bar-fill{height:100%;border-radius:999px;transform-origin:left;animation:grow .8s cubic-bezier(.34,1.56,.5,1) both}
.bar-row .bval{font-variant-numeric:tabular-nums;font-size:.85rem;opacity:.7;white-space:nowrap}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
ol.actions{margin:8px 0 0;padding-left:0;counter-reset:a;list-style:none}
ol.actions li{position:relative;padding:12px 12px 12px 52px;margin-top:10px;background:var(--butter-tint);
border-radius:16px;counter-increment:a}
ol.actions li::before{content:counter(a);position:absolute;left:14px;top:12px;width:28px;height:28px;
display:flex;align-items:center;justify-content:center;background:var(--ink);color:#fff;border-radius:999px;
font-family:"Bricolage Grotesque",sans-serif;font-weight:700;font-size:.95rem}
.prose p{margin:.5em 0}
.foot{margin-top:56px;padding-top:20px;border-top:1px solid rgba(33,22,51,.1);
font-size:.82rem;color:rgba(33,22,51,.55)}
.foot a{color:var(--violet)}
@media (prefers-reduced-motion:reduce){.bar-fill{animation:none}}
@media (max-width:560px){.bar-row{grid-template-columns:1fr;gap:4px}.bar-row .bval{justify-self:start}}
"""


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _inline_md(s: str) -> str:
    out = _esc(s)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    return out


def callout(label: str, value: str, note: str = "", tone: str = "violet") -> dict[str, Any]:
    color = _TONES.get(tone, _TONES["violet"])
    return {"type": "callout", "label": label, "value": value, "note": note, "color": color}


def _render_callouts(items: list[dict[str, Any]]) -> str:
    cells = []
    for it in items:
        cells.append(
            f'<div class="callout" style="background:{_tint(it["color"])}">'
            f'<div class="lab">{_esc(it["label"])}</div>'
            f'<div class="val">{_esc(it["value"])}</div>'
            + (f'<div class="note">{_inline_md(it["note"])}</div>' if it.get("note") else "")
            + "</div>"
        )
    return f'<div class="callouts">{"".join(cells)}</div>'


def _tint(hexcolor: str) -> str:
    """A 12%-ish wash of a saturated token, for callout backgrounds."""
    h = hexcolor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = 0.14
    r = round(r * a + 255 * (1 - a))
    g = round(g * a + 255 * (1 - a))
    b = round(b * a + 255 * (1 - a))
    return f"rgb({r},{g},{b})"


def bars_block(title: str, rows: list[dict[str, Any]], lede: str = "") -> dict[str, Any]:
    """rows: [{label, value(0..1 fill fraction), display, tone, tag, tag_kind}]"""
    return {"type": "bars", "title": title, "rows": rows, "lede": lede}


def _render_bars(block: dict[str, Any]) -> str:
    rows_html = []
    for r in block["rows"]:
        color = _TONES.get(r.get("tone", "violet"), _TONES["violet"])
        frac = max(0.0, min(1.0, float(r.get("value", 0))))
        tag = ""
        if r.get("tag"):
            kind = r.get("tag_kind", "")
            tag = f' <span class="tag {kind}">{_esc(r["tag"])}</span>'
        rows_html.append(
            '<div class="bar-row">'
            f'<div class="blab">{_esc(r["label"])}{tag}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{frac*100:.0f}%;background:{color}"></div></div>'
            f'<div class="bval">{_esc(r.get("display",""))}</div>'
            "</div>"
        )
    lede = f'<p class="lede">{_inline_md(block["lede"])}</p>' if block.get("lede") else ""
    return f'<h2>{_esc(block["title"])}</h2>{lede}<div class="card">{"".join(rows_html)}</div>'


def table_block(title: str, headers: list[str], rows: list[list[Any]], lede: str = "",
                num_cols: Iterable[int] = (), emphasize: Iterable[int] = ()) -> dict[str, Any]:
    return {"type": "table", "title": title, "headers": headers, "rows": rows,
            "lede": lede, "num_cols": set(num_cols), "emphasize": set(emphasize)}


def _render_table(block: dict[str, Any]) -> str:
    num = block["num_cols"]
    head = "".join(
        f'<th class="{"num" if i in num else ""}">{_esc(h)}</th>'
        for i, h in enumerate(block["headers"])
    )
    body = []
    for ri, row in enumerate(block["rows"]):
        cls = ' class="em"' if ri in block["emphasize"] else ""
        cells = "".join(
            f'<td class="{"num" if i in num else ""}">{_cell(c)}</td>'
            for i, c in enumerate(row)
        )
        body.append(f"<tr{cls}>{cells}</tr>")
    lede = f'<p class="lede">{_inline_md(block["lede"])}</p>' if block.get("lede") else ""
    return (
        f'<h2>{_esc(block["title"])}</h2>{lede}'
        f'<div class="card"><table><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
    )


def _cell(c: Any) -> str:
    if isinstance(c, dict) and "tag" in c:
        return f'<span class="tag {c.get("kind","")}">{_esc(c["tag"])}</span>'
    return _inline_md(c if isinstance(c, str) else str(c))


def actions_block(title: str, items: list[str], lede: str = "") -> dict[str, Any]:
    return {"type": "actions", "title": title, "items": items, "lede": lede}


def _render_actions(block: dict[str, Any]) -> str:
    lis = "".join(f"<li>{_inline_md(it)}</li>" for it in block["items"])
    lede = f'<p class="lede">{_inline_md(block["lede"])}</p>' if block.get("lede") else ""
    return f'<h2>{_esc(block["title"])}</h2>{lede}<ol class="actions">{lis}</ol>'


def prose_block(title: str, body: str) -> dict[str, Any]:
    return {"type": "prose", "title": title, "body": body}


def _render_prose(block: dict[str, Any]) -> str:
    paras = "".join(f"<p>{_inline_md(p)}</p>" for p in block["body"].split("\n\n") if p.strip())
    return f'<h2>{_esc(block["title"])}</h2><div class="card prose">{paras}</div>'


_RENDERERS = {
    "bars": _render_bars,
    "table": _render_table,
    "actions": _render_actions,
    "prose": _render_prose,
}


def render_report(*, title_html: str, kicker: str, subtitle: str,
                  blocks: list[dict[str, Any]], footer: str) -> str:
    callouts = [b for b in blocks if b.get("type") == "callout"]
    body_parts = []
    if callouts:
        body_parts.append(_render_callouts(callouts))
    for b in blocks:
        if b.get("type") == "callout":
            continue
        renderer = _RENDERERS.get(b.get("type", ""))
        if renderer:
            body_parts.append(renderer(b))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(re.sub(r'<[^>]+>', '', title_html))} — SocialGPT</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Hanken+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
<style>{_REPORT_CSS}</style></head>
<body><div class="wrap">
<span class="kicker">{_esc(kicker)}</span>
<h1>{title_html}</h1>
<p class="sub">{_esc(subtitle)}</p>
{"".join(body_parts)}
<div class="foot">{_inline_md(footer)}</div>
</div></body></html>"""


def write_report(html_str: str, filename: str) -> str:
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(html_str)
    return filename
