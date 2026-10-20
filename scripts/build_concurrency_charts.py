import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_FILE = Path("/home/limooadmin/thesis_status_export/concurrency_summary.csv")
OUT_DIR = Path("/home/limooadmin/thesis_status_export/plots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

data = {}
with DATA_FILE.open() as f:
    r = csv.DictReader(f)
    for row in r:
        arm = row["arm"]
        vu = int(row["vus"])
        data.setdefault(arm, {})[vu] = {
            "req": float(row["app_requests"]),
            "tput": float(row["throughput_rps"]),
            "fail": float(row["failure_rate_percent"]),
            "p95": float(row["p95_latency_ms"]),
            "avg": float(row["avg_latency_ms"]),
        }

vus = [10, 20, 40, 60]
arms_config = [
    ("baseline", "Baseline (1 Replica)", "#d9534f", "o", "--"),
    ("hpa", "CPU HPA", "#f0ad4e", "s", "-."),
    ("qos", "Rule-based QoS", "#0275d8", "^", ":"),
    ("ml_qos", "ML+QoS Decision Layer", "#5cb85c", "D", "-"),
]

plt.rcParams.update({"font.size": 11, "figure.autolayout": True})

# 1. VU vs P95
plt.figure(figsize=(8, 5))
for arm, label, color, marker, ls in arms_config:
    y = [data[arm][v]["p95"] for v in vus]
    plt.plot(vus, y, label=label, color=color, marker=marker, linestyle=ls, linewidth=2)
plt.title("P95 Latency vs. Concurrent Load (VUs)", fontsize=13, fontweight="bold")
plt.xlabel("Virtual Users (VUs)")
plt.ylabel("P95 Latency (ms)")
plt.xticks(vus)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True)
plt.savefig(OUT_DIR / "chart_concurrency_vs_p95.png", dpi=300)
plt.close()

# 2. VU vs Failure Rate
plt.figure(figsize=(8, 5))
for arm, label, color, marker, ls in arms_config:
    y = [data[arm][v]["fail"] for v in vus]
    plt.plot(vus, y, label=label, color=color, marker=marker, linestyle=ls, linewidth=2)
plt.title("Failure Rate vs. Concurrent Load (VUs)", fontsize=13, fontweight="bold")
plt.xlabel("Virtual Users (VUs)")
plt.ylabel("Failure Rate (%)")
plt.xticks(vus)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True)
plt.savefig(OUT_DIR / "chart_concurrency_vs_failure.png", dpi=300)
plt.close()

# 3. VU vs Throughput
plt.figure(figsize=(8, 5))
for arm, label, color, marker, ls in arms_config:
    y = [data[arm][v]["tput"] for v in vus]
    plt.plot(vus, y, label=label, color=color, marker=marker, linestyle=ls, linewidth=2)
plt.title("Throughput vs. Concurrent Load (VUs)", fontsize=13, fontweight="bold")
plt.xlabel("Virtual Users (VUs)")
plt.ylabel("Throughput (req/s)")
plt.xticks(vus)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True)
plt.savefig(OUT_DIR / "chart_concurrency_vs_throughput.png", dpi=300)
plt.close()

print("Generated concurrency plots successfully!")