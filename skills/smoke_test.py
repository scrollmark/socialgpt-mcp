#!/usr/bin/env python3
"""CI smoke test: run every skill's analyze.py on synthetic, MCP-shaped input.

For each skill it builds a minimal but gate-clearing input, runs the skill's
``scripts/analyze.py`` as a subprocess in a temp dir (the same way an agent
would), and asserts it exits 0 and writes an HTML report. No third-party deps —
this is the same surface the skills run on in Claude's sandbox.

    python skills/smoke_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _videos(themes_pool, base_views, n, *, with_themes, dur=30):
    out = []
    plats = ["tiktok", "instagram", "youtube"]
    for i in range(n):
        v = {
            "platform": plats[i % 3],
            "post_id": f"p{i}",
            "title": (f"Part 2 " if i % 4 == 0 else "") + " ".join(themes_pool[i % len(themes_pool):i % len(themes_pool) + 1]),
            "duration": dur + (i % 5) * 7,
            "post_created_time": f"2026-03-{(i % 27) + 1:02d}T{9 + (i % 8)}:00:00",
            "metrics": {
                "views": max(0, base_views - i * 1500 + (i % 3) * 2000),
                "likes": 800 + i * 10,
                "comments": 40 + i,
                "engagement_rate": 0.03 + (i % 5) * 0.01,
            },
        }
        if with_themes:
            v["content_themes"] = themes_pool[i % len(themes_pool):i % len(themes_pool) + 2] or [themes_pool[0]]
        out.append(v)
    return out


def _analysis(views, dur, transcript):
    return {
        "post": {"platform": "tiktok", "post_id": "p", "title": "t", "duration": dur,
                 "metrics": {"views": views, "engagement_rate": 0.05}},
        "transcript": transcript,
        "transcript_segments": [{"start": 0, "end": 3, "text": transcript.split(".")[0]}],
        "suggested_hooks": [], "hooks": [], "content_themes": [],
    }


def _build_inputs():
    cpa = {"videos": _videos(["color theory", "ai tools", "story time"], 40000, 12, with_themes=False)}

    me = _videos(["product review", "sunscreen", "skincare ingredients"], 26000, 8, with_themes=True)
    rivals = _videos(["grwm", "morning routine", "what i eat in a day"], 130000, 8, with_themes=True)
    gap = {"me": {"videos": me},
           "competitors": [{"name": "@rivalA", "videos": rivals[:4]},
                           {"name": "@rivalB", "videos": rivals[4:]}]}

    win = "Why does nobody talk about this? I tried it for 30 days and honestly the results actually shocked me. Follow for part 2."
    flop = "So today we are going to look at some tips that you might find useful for your content over time."
    teardown = {"top": [_analysis(200000, 20, win) for _ in range(3)],
                "bottom": [_analysis(3000, 45, flop) for _ in range(3)]}

    return [
        ("content-performance-audit", "videos.json", cpa),
        ("competitor-gap-analysis", "gap.json", gap),
        ("hook-retention-teardown", "teardown.json", teardown),
    ]


def main() -> int:
    failures = 0
    for skill, infile, payload in _build_inputs():
        analyze = ROOT / skill / "scripts" / "analyze.py"
        if not analyze.exists():
            print(f"FAIL {skill}: missing {analyze.relative_to(ROOT)}")
            failures += 1
            continue
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / infile).write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(analyze), infile],
                cwd=tmpdir, capture_output=True, text=True,
            )
            html = list(tmpdir.glob("*.html"))
            ok = proc.returncode == 0 and html and html[0].stat().st_size > 500
            if ok:
                print(f"PASS {skill}  (report {html[0].stat().st_size:,} bytes)")
            else:
                failures += 1
                print(f"FAIL {skill}: exit={proc.returncode}, reports={len(html)}")
                if proc.stderr.strip():
                    print("  stderr:", proc.stderr.strip()[:400])

    if failures:
        print(f"\n{failures} skill(s) failed the smoke test.")
        return 1
    print("\nAll skills passed the smoke test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
