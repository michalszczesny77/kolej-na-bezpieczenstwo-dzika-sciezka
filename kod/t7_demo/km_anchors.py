"""Kilometre anchors for the demo: one point km instead of a PLK segment range.

Anchors per line = OSM milestones (railway:position) snapped to the line + Regulamin sieci
zal. 1 stations matched to a unique OSM node by name. Same logic as t2_hazard/build_hazard.py,
without GTFS station coordinates (not needed, and not kept in the repo).

Leave-one-out check on milestones (19.11.2026): median error 7 m, p90 68 m, p95 95 m (n = 210).

Run: python kod/t7_demo/km_anchors.py  ->  dane/km_anchors.json
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "t2_hazard"))
import build_hazard as bh  # noqa: E402

OUT = ROOT.parent / "dane" / "km_anchors.json"


def leave_one_out(anchors):
    errs = []
    for anc in anchors.values():
        for i, a in enumerate(anc):
            if a["source"] != "osm_milestone" or i in (0, len(anc) - 1):
                continue
            km, gap = bh.km_at(anc[:i] + anc[i + 1:], a["xy"])
            if km is not None and gap <= bh.MAX_ANCHOR_GAP_M:
                errs.append(abs(km - a["km"]) * 1000)
    errs.sort()
    n = len(errs)
    return {"n": n, "median_m": round(statistics.median(errs)), "p90_m": round(errs[int(0.9 * n)]),
            "p95_m": round(errs[int(0.95 * n)])}


def main():
    _, _, points, _ = bh.load_annexes()
    running, nodes = bh.load_osm()
    chunks = [{"way": w, "geom": g, "lines": bh.way_lines(w)} for w in running for g in bh.chunk_way(w)]
    anchors = bh.build_anchors(points, nodes, {}, chunks)
    out = {"source": "OSM railway=milestone + PLK Regulamin sieci 2025/2026 zal. 1 (stacje, nazwy z OSM)",
           "max_gap_m": bh.MAX_ANCHOR_GAP_M, "check": leave_one_out(anchors), "lines": {}}
    for line, anc in sorted(anchors.items()):
        out["lines"][str(line)] = [[round(a["km"], 3), *(round(v, 6) for v in bh.to_4326(*a["xy"])[::-1])]
                                   for a in anc]
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT}: {sum(len(v) for v in out['lines'].values())} anchors on {len(out['lines'])} lines, check {out['check']}")


if __name__ == "__main__":
    main()
