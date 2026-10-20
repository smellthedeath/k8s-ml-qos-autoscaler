#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

MEANS_FILE = Path("/home/limooadmin/thesis_status_export/means.csv")
OUT_DIR = Path("/home/limooadmin/thesis_status_export/plots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load Means Data
data = {}
with MEANS_FILE.open() as f:
    r = csv.DictReader(f)
    for row in r:
        arm = row["arm"]
        dur = int(row["duration_s"])
        data.setdefault(arm, {})[dur] = {
            "req_mean": float(row["app_requests_mean"]),
            "fail_mean": float(row["failure_mean"]),
            "fail_sd": float(row["failure_sd"]) if row["failure_sd"] else 0.0,
            "p95_mean": float(row["p95_ms_mean"]),
            "p95_sd": float(row["p95_ms_sd"]) if row["p95_ms_sd"] else 0.0,
            "avg_mean": float(row["avg_ms_mean"]),
            "tput_mean": float(row["throughput_rps_mean"]),
        }

durations = [120, 240, 360, 480]
arms_config = [
    ("baseline", "Baseline (1 Replica)", "#d9534f", "o", "--"),
    ("hpa", "CPU HPA", "#f0ad4e", "s", "-."),
    ("qos", "Rule-based QoS", "#0275d8", "^", ":"),
    ("ml_qos", "ML+QoS Decision Layer", "#5cb85c", "D", "-"),
]

plt.rcParams.update({"font.size": 11, "figure.autolayout": True})

# --- Plot 1: Duration vs P95 Latency ---
plt.figure(figsize=(8, 5))
for arm, label, color, marker, ls in arms_config:
    y = [data[arm][d]["p95_mean"] for d in durations]
    yerr = [data[arm][d]["p95_sd"] for d in durations]
    plt.errorbar(durations, y, yerr=yerr, label=label, color=color, marker=marker, linestyle=ls, linewidth=2, capsize=4)
plt.title("P95 Latency vs. Test Duration (Mean +/- SD, n=3)", fontsize=13, fontweight="bold")
plt.xlabel("Duration (seconds)")
plt.ylabel("P95 Latency (ms)")
plt.xticks(durations)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True)
plt.savefig(OUT_DIR / "chart_duration_vs_p95.png", dpi=300)
plt.close()

# --- Plot 2: Duration vs Failure Rate ---
plt.figure(figsize=(8, 5))
for arm, label, color, marker, ls in arms_config:
    y = [data[arm][d]["fail_mean"] for d in durations]
    yerr = [data[arm][d]["fail_sd"] for d in durations]
    plt.errorbar(durations, y, yerr=yerr, label=label, color=color, marker=marker, linestyle=ls, linewidth=2, capsize=4)
plt.title("Request Failure Rate vs. Test Duration (Mean +/- SD, n=3)", fontsize=13, fontweight="bold")
plt.xlabel("Duration (seconds)")
plt.ylabel("Failure Rate (%)")
plt.xticks(durations)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True)
plt.savefig(OUT_DIR / "chart_duration_vs_failure.png", dpi=300)
plt.close()

# --- Plot 3: Duration vs Throughput ---
plt.figure(figsize=(8, 5))
for arm, label, color, marker, ls in arms_config:
    y = [data[arm][d]["tput_mean"] for d in durations]
    plt.plot(durations, y, label=label, color=color, marker=marker, linestyle=ls, linewidth=2)
plt.title("Throughput vs. Test Duration (Mean, n=3)", fontsize=13, fontweight="bold")
plt.xlabel("Duration (seconds)")
plt.ylabel("Throughput (req/s)")
plt.xticks(durations)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True)
plt.savefig(OUT_DIR / "chart_duration_vs_throughput.png", dpi=300)
plt.close()

# --- Plot 4: Duration vs Average Latency ---
plt.figure(figsize=(8, 5))
for arm, label, color, marker, ls in arms_config:
    y = [data[arm][d]["avg_mean"] for d in durations]
    plt.plot(durations, y, label=label, color=color, marker=marker, linestyle=ls, linewidth=2)
plt.title("Average Latency vs. Test Duration (Mean, n=3)", fontsize=13, fontweight="bold")
plt.xlabel("Duration (seconds)")
plt.ylabel("Average Latency (ms)")
plt.xticks(durations)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True)
plt.savefig(OUT_DIR / "chart_duration_vs_avg_latency.png", dpi=300)
plt.close()

# --- Plot 5: 480s Replica Timeline Comparison ---
ml_csv = Path("/root/master-thesis-evidence/10-extended-load-tests/evaluation/final_duration_study/ml_qos/480s-run1/controller.csv")
qos_csv = Path("/root/master-thesis-evidence/10-extended-load-tests/evaluation/final_duration_study/qos/480s-run1/controller.csv")

if ml_csv.exists() and qos_csv.exists():
    plt.figure(figsize=(10, 5))
    
    # ML+QoS
    ml_rows = list(csv.DictReader(ml_csv.open()))
    t0_ml = float(ml_rows[0]["ts"])
    t_ml = [float(r["ts"]) - t0_ml for r in ml_rows]
    rep_ml = [int(r["current_replicas"]) for r in ml_rows]
    plt.step(t_ml, rep_ml, label="ML+QoS Decision Layer (480s)", color="#5cb85c", linewidth=2.5, where="post")
    
    # Rule QoS
    qos_rows = list(csv.DictReader(qos_csv.open()))
    t0_qos = float(qos_rows[0]["ts"])
    t_qos = [float(r["ts"]) - t0_qos for r in qos_rows]
    rep_qos = [int(r["replicas"]) for r in qos_rows]
    plt.step(t_qos, rep_qos, label="Rule-based QoS (480s)", color="#0275d8", linewidth=2, linestyle="--", where="post")
    
    # Baseline
    plt.axhline(y=1, color="#d9534f", linestyle=":", linewidth=2, label="Baseline (Constant 1)")
    
    # HPA
    plt.step([0, 20, 480], [1, 6, 6], label="CPU HPA (Jump to 6)", color="#f0ad4e", linestyle="-.", linewidth=2, where="post")

    plt.title("Replica Scaling Trajectories (480s Duration)", fontsize=13, fontweight="bold")
    plt.xlabel("Elapsed Time (seconds)")
    plt.ylabel("Replica Count")
    plt.ylim(0.5, 6.5)
    plt.yticks([1, 2, 3, 4, 5, 6])
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, loc="lower right")
    plt.savefig(OUT_DIR / "chart_replica_timeline_480s.png", dpi=300)
    plt.close()

# Copy to evaluation/plots
eval_plots = Path("/root/master-thesis-evidence/10-extended-load-tests/evaluation/plots")
eval_plots.mkdir(parents=True, exist_ok=True)
import shutil
for p in OUT_DIR.glob("*.png"):
    shutil.copy(p, eval_plots / p.name)

print("SUCCESS: Generated all thesis plots")