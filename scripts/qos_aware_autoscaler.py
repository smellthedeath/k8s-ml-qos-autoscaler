#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
import time
import urllib.request

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def cpu_to_m(cpu):
    cpu = str(cpu).strip()
    if not cpu:
        return 0.0
    if cpu.endswith("m"):
        return float(cpu[:-1])
    if cpu.endswith("n"):
        return float(cpu[:-1]) / 1000000
    if cpu.endswith("u"):
        return float(cpu[:-1]) / 1000
    return float(cpu) * 1000

def mem_to_mi(mem):
    mem = str(mem).strip()
    if not mem:
        return 0.0
    if mem.endswith("Mi"):
        return float(mem[:-2])
    if mem.endswith("Gi"):
        return float(mem[:-2]) * 1024
    if mem.endswith("Ki"):
        return float(mem[:-2]) / 1024
    return 0.0

def get_replicas(namespace, deployment):
    try:
        value = run(f"kubectl -n {namespace} get deploy {deployment} -o jsonpath='{{.spec.replicas}}'")
        return int(value)
    except Exception:
        return 1

def get_top(namespace, selector):
    total_cpu_m = 0.0
    total_mem_mi = 0.0
    pod_count = 0

    try:
        output = run(f"kubectl -n {namespace} top pod -l {selector} --no-headers")
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                pod_count += 1
                total_cpu_m += cpu_to_m(parts[1])
                total_mem_mi += mem_to_mi(parts[2])
    except Exception as e:
        print(f"[WARN] kubectl top failed: {e}")

    return pod_count, total_cpu_m, total_mem_mi

def get_qos(collector_url):
    try:
        with urllib.request.urlopen(collector_url, timeout=2) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"[WARN] collector failed: {e}")
        return {
            "requests": 0,
            "failed_rate_percent": 0,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0
        }

def scale(namespace, deployment, replicas):
    cmd = f"kubectl -n {namespace} scale deployment {deployment} --replicas={replicas}"
    subprocess.check_call(cmd, shell=True)

def decide(replicas, cpu_percent, p95, avg, fail, args):
    if fail >= args.fail_up:
        return min(args.max, replicas + args.step_up), "scale_up_failed_rate"

    if p95 >= args.p95_up:
        return min(args.max, replicas + args.step_up), "scale_up_p95_latency"

    if avg >= args.avg_up:
        return min(args.max, replicas + args.step_up), "scale_up_avg_latency"

    if cpu_percent >= args.cpu_up:
        return min(args.max, replicas + 1), "scale_up_cpu"

    if (
        fail == 0
        and p95 <= args.p95_down
        and avg <= args.avg_down
        and cpu_percent <= args.cpu_down
        and replicas > args.min
    ):
        return max(args.min, replicas - 1), "scale_down_stable"

    return replicas, "no_change"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--namespace", default="thesis-exp")
    p.add_argument("--deployment", default="cpu-app")
    p.add_argument("--selector", default="app=cpu-app")
    p.add_argument("--collector", default="http://127.0.0.1:18080/summary?window=30")
    p.add_argument("--min", type=int, default=1)
    p.add_argument("--max", type=int, default=6)
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--cooldown", type=int, default=15)
    p.add_argument("--step-up", type=int, default=2)

    p.add_argument("--cpu-request-m", type=float, default=100)
    p.add_argument("--cpu-up", type=float, default=50)
    p.add_argument("--cpu-down", type=float, default=25)

    p.add_argument("--p95-up", type=float, default=2000)
    p.add_argument("--p95-down", type=float, default=900)
    p.add_argument("--avg-up", type=float, default=1000)
    p.add_argument("--avg-down", type=float, default=500)
    p.add_argument("--fail-up", type=float, default=0.1)

    p.add_argument("--log", default="qos_controller_metrics.csv")
    args = p.parse_args()

    last_scale = 0

    with open(args.log, "w", newline="") as f:
        fields = [
            "ts",
            "replicas",
            "target_replicas",
            "pod_count",
            "cpu_percent",
            "total_cpu_m",
            "total_memory_mi",
            "requests",
            "failed_rate_percent",
            "avg_latency_ms",
            "p95_latency_ms",
            "reason"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        while True:
            replicas = get_replicas(args.namespace, args.deployment)
            pod_count, total_cpu_m, total_mem_mi = get_top(args.namespace, args.selector)
            qos = get_qos(args.collector)

            cpu_percent = 0.0
            if replicas > 0:
                cpu_percent = (total_cpu_m / (replicas * args.cpu_request_m)) * 100

            target, reason = decide(
                replicas,
                cpu_percent,
                qos.get("p95_latency_ms", 0),
                qos.get("avg_latency_ms", 0),
                qos.get("failed_rate_percent", 0),
                args
            )

            now = time.time()

            if target != replicas:
                if now - last_scale >= args.cooldown:
                    scale(args.namespace, args.deployment, target)
                    last_scale = now
                    applied = f"APPLIED {replicas}->{target}"
                else:
                    target = replicas
                    applied = "cooldown"
            else:
                applied = "no_change"

            row = {
                "ts": int(now),
                "replicas": replicas,
                "target_replicas": target,
                "pod_count": pod_count,
                "cpu_percent": round(cpu_percent, 2),
                "total_cpu_m": round(total_cpu_m, 2),
                "total_memory_mi": round(total_mem_mi, 2),
                "requests": qos.get("requests", 0),
                "failed_rate_percent": qos.get("failed_rate_percent", 0),
                "avg_latency_ms": qos.get("avg_latency_ms", 0),
                "p95_latency_ms": qos.get("p95_latency_ms", 0),
                "reason": reason
            }

            writer.writerow(row)
            f.flush()

            print(
                f"replicas={replicas}, target={target}, "
                f"cpu={row['cpu_percent']}%, "
                f"avg={row['avg_latency_ms']}ms, "
                f"p95={row['p95_latency_ms']}ms, "
                f"fail={row['failed_rate_percent']}%, "
                f"reason={reason}, {applied}"
            )

            time.sleep(args.interval)

if __name__ == "__main__":
    main()
