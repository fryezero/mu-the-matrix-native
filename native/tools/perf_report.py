#!/usr/bin/env python3
"""Frame-time percentiles from mu-client/mu-world --perf logs (NATIVE-PERF-001).

    perf_report.py LOG.tsv [LOG.tsv ...] [--scene N] [--skip-first N] [--json]

Per log: frame count, frames per second, the frame time's mean/p50/p90/p95/p99/max
and each phase's mean and p95 (milliseconds); `work` is the frame time without
the cap's sleep (what the frame cost).  --scene keeps one scene (6 world, 5
character select, 3 login); --skip-first drops each scene visit's first frames
(loading).
"""
import argparse
import json
import sys


def percentile(values, p):
    if not values:
        return 0.0
    v = sorted(values)
    k = (len(v) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def read(path):
    with open(path) as f:
        header = f.readline().rstrip("\n").split("\t")
        rows = []
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != len(header):
                continue
            rows.append({h: float(x) for h, x in zip(header, parts)})
    return header, rows


def summarize(path, scene=None, skip_first=0):
    header, rows = read(path)
    kept, last, run = [], None, 0
    for r in rows:
        s = int(r["scene"])
        run = run + 1 if s == last else 0
        last = s
        if scene is not None and s != scene:
            continue
        if run < skip_first:
            continue
        kept.append(r)
    phases = [h[:-3] for h in header[3:]]
    total = [r["total_ms"] for r in kept]
    work = [r["total_ms"] - r["sleep_ms"] for r in kept]
    seconds = sum(total) / 1000.0
    out = {
        "log": path,
        "frames": len(kept),
        "fps": len(kept) / seconds if seconds > 0 else 0.0,
        "frame_ms": {k: percentile(total, p) for k, p in (("p50", 50), ("p90", 90), ("p95", 95), ("p99", 99))},
        "work_ms": {k: percentile(work, p) for k, p in (("p50", 50), ("p90", 90), ("p95", 95), ("p99", 99))},
        "max_ms": max(total) if total else 0.0,
        "over_40ms": sum(1 for t in total if t > 40.5) / len(total) if total else 0.0,
        "phases": {},
    }
    out["frame_ms"]["mean"] = sum(total) / len(total) if total else 0.0
    out["work_ms"]["mean"] = sum(work) / len(work) if work else 0.0
    for p in phases:
        vals = [r[p + "_ms"] for r in kept]
        mean = sum(vals) / len(vals) if vals else 0.0
        if mean >= 0.005:
            out["phases"][p] = {"mean": mean, "p95": percentile(vals, 95)}
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--scene", type=int)
    ap.add_argument("--skip-first", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    results = [summarize(p, a.scene, a.skip_first) for p in a.logs]
    if a.json:
        print(json.dumps(results, indent=1))
        return 0
    for r in results:
        f, w = r["frame_ms"], r["work_ms"]
        print(f"{r['log']}: {r['frames']} frames, {r['fps']:.1f} fps, frame p50 {f['p50']:.1f} p95 {f['p95']:.1f} "
              f"p99 {f['p99']:.1f} max {r['max_ms']:.1f} ms, >40 ms {100 * r['over_40ms']:.1f} %; "
              f"work p50 {w['p50']:.1f} p95 {w['p95']:.1f} p99 {w['p99']:.1f} ms")
        print("   " + "  ".join(f"{k} {v['mean']:.2f}/{v['p95']:.2f}" for k, v in r["phases"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
