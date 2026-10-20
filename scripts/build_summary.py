#!/usr/bin/env python3
"""Scan final_duration_study, write per-run summary.csv and per-arm means.csv (valid runs only)."""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path("/root/master-thesis-evidence/10-extended-load-tests/evaluation/final_duration_study")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/limooadmin/thesis_status_export")
OUT.mkdir(parents=True, exist_ok=True)

RUN_RE = re.compile(r"^(\d+)s-run(\d+)$")
EXCLUDE_NOTES = {
    ("qos", "120s-started-at-6"): "excluded: labelled bad in stop-point doc (k8s_before shows 1/1, label disputed)",
    ("qos", "120s-run1-archived-no-controller-csv"): "archived: controller CSV overwritten",
    ("qos", "240s-run1-archived-no-controller-csv"): "archived: controller CSV overwritten, no collector_final",
    ("hpa", "120s-not-applied"): "excluded: HPA not applied",
    ("ml_qos", "240s-bad-18080"): "excluded: wrong collector port / mixed traffic",
}


LOOPS_FROM_HISTORY = {
    ("baseline", "360s-run1"): "120000 (bash_history: LOOPS unset, qos_test_eval.js default)",
}


def loops_of(d: Path) -> str:
    if (d.parent.name, d.name) in LOOPS_FROM_HISTORY:
        return LOOPS_FROM_HISTORY[(d.parent.name, d.name)]
    meta = d / "run_meta.txt"
    if meta.exists():
        m = re.search(r"loops=(\d+)", meta.read_text())
        if m:
            return m.group(1)
    k6 = d / "k6.txt"
    if k6.exists():
        found = sorted(set(re.findall(r"loops=(\d+)", k6.read_text(errors="ignore"))))
        if found:
            return "|".join(found) + " (from k6 errors)"
    return "unknown"


def max_replicas(d: Path) -> str:
    f = d / "k8s_after.txt"
    if not f.exists():
        return ""
    m = re.search(r"deployment\.apps/cpu-app\s+(\d+)/(\d+)", f.read_text())
    return m.group(2) if m else ""


def scale_events(arm: str, d: Path) -> str:
    f = d / "controller.csv"
    if not f.exists():
        return ""
    rows = list(csv.DictReader(f.open()))
    if not rows:
        return ""
    t0 = int(float(rows[0]["ts"]))
    ev = []
    for r in rows:
        if arm == "qos":
            cur, tgt = r.get("replicas"), r.get("target_replicas")
            if cur and tgt and cur != tgt:
                ev.append(f"+{int(float(r['ts'])) - t0}s {cur}->{tgt}")
        elif arm == "ml_qos":
            if r.get("action", "none") != "none":
                ev.append(f"+{int(float(r['ts'])) - t0}s {r.get('current_replicas')}->{r.get('target_replicas')}")
    return " ".join(ev)


rows = []
for arm_dir in sorted(p for p in ROOT.iterdir() if p.is_dir()):
    arm = arm_dir.name
    for d in sorted(p for p in arm_dir.iterdir() if p.is_dir()):
        name = d.name
        m = RUN_RE.match(name)
        summ = d / "k6_summary.json"
        rec = {"arm": arm, "dir": name, "duration_s": "", "run": "", "status": "", "loops": loops_of(d),
               "app_requests": "", "throughput_rps": "", "failure_rate_percent": "", "avg_latency_ms": "",
               "p95_latency_ms": "", "max_replicas_end": max_replicas(d), "scale_events": scale_events(arm, d),
               "k6_exit": (d / "k6_exit_code.txt").read_text().strip() if (d / "k6_exit_code.txt").exists() else ""}
        if summ.exists():
            met = json.loads(summ.read_text()).get("metrics", {})
            req = met.get("app_requests", {})
            fail = met.get("app_req_failed", {})
            dur = met.get("app_req_duration", {})
            rec["app_requests"] = req.get("count", "")
            rec["throughput_rps"] = round(req.get("rate", 0), 3) if req else ""
            if "value" in fail:
                rec["failure_rate_percent"] = round(fail["value"] * 100, 3)
            rec["avg_latency_ms"] = round(dur.get("avg", 0), 1) if dur else ""
            rec["p95_latency_ms"] = round(dur.get("p(95)", 0), 1) if dur else ""
        if m:
            rec["duration_s"], rec["run"] = int(m.group(1)), int(m.group(2))
            rec["status"] = "valid" if rec["loops"].startswith("120000") and "|" not in rec["loops"] else f"check: loops={rec['loops']}"
        else:
            rec["status"] = EXCLUDE_NOTES.get((arm, name), "archived/excluded")
            if "loops30000" in name:
                rec["status"] = "archived: LOOPS=30000 (not comparable)"
        rows.append(rec)

fields = list(rows[0].keys())
with (OUT / "summary.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

agg = {}
for r in rows:
    if r["status"] == "valid" and r["failure_rate_percent"] != "":
        agg.setdefault((r["arm"], r["duration_s"]), []).append(r)

mfields = ["arm", "duration_s", "n_runs", "runs", "app_requests_mean", "failure_mean", "failure_sd",
           "p95_ms_mean", "p95_ms_sd", "avg_ms_mean", "throughput_rps_mean"]
with (OUT / "means.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=mfields)
    w.writeheader()
    for (arm, dur), rs in sorted(agg.items(), key=lambda x: (x[0][0], x[0][1])):
        fr = [float(r["failure_rate_percent"]) for r in rs]
        p95 = [float(r["p95_latency_ms"]) for r in rs]
        w.writerow({
            "arm": arm, "duration_s": dur, "n_runs": len(rs), "runs": ",".join(str(r["run"]) for r in rs),
            "app_requests_mean": round(statistics.mean(float(r["app_requests"]) for r in rs), 1),
            "failure_mean": round(statistics.mean(fr), 2),
            "failure_sd": round(statistics.stdev(fr), 2) if len(fr) > 1 else "",
            "p95_ms_mean": round(statistics.mean(p95), 0),
            "p95_ms_sd": round(statistics.stdev(p95), 0) if len(p95) > 1 else "",
            "avg_ms_mean": round(statistics.mean(float(r["avg_latency_ms"]) for r in rs), 0),
            "throughput_rps_mean": round(statistics.mean(float(r["throughput_rps"]) for r in rs), 2),
        })
print(f"wrote {OUT/'summary.csv'} ({len(rows)} dirs) and {OUT/'means.csv'}")
