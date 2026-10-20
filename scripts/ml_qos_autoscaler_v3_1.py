#!/usr/bin/env python3

import argparse
import csv
import json
import subprocess
import time
import urllib.request

from ml_model import predict_replicas


def run(cmd):
    return subprocess.check_output(
        cmd,
        shell=True,
        text=True
    ).strip()


def cpu_to_m(cpu):
    cpu = str(cpu).strip()

    if cpu.endswith("m"):
        return float(cpu[:-1])

    if cpu.endswith("n"):
        return float(cpu[:-1]) / 1000000

    return float(cpu) * 1000


def mem_to_mi(mem):
    mem = str(mem).strip()

    if mem.endswith("Mi"):
        return float(mem[:-2])

    if mem.endswith("Gi"):
        return float(mem[:-2]) * 1024

    if mem.endswith("Ki"):
        return float(mem[:-2]) / 1024

    return 0


def get_replicas(namespace, deployment):

    try:
        return int(
            run(
                f"kubectl -n {namespace} get deploy {deployment} "
                "-o jsonpath='{.spec.replicas}'"
            )
        )

    except:
        return 1



def get_top(namespace, selector):

    cpu = 0
    memory = 0
    pods = 0

    try:

        output = run(
            f"kubectl -n {namespace} top pod "
            f"-l {selector} --no-headers"
        )

        for line in output.splitlines():

            p = line.split()

            if len(p) >= 3:

                pods += 1
                cpu += cpu_to_m(p[1])
                memory += mem_to_mi(p[2])

    except Exception as e:
        print("[WARN] top:", e)


    return pods, cpu, memory



def get_qos(url):

    try:

        with urllib.request.urlopen(
            url,
            timeout=3
        ) as r:

            return json.loads(
                r.read().decode()
            )

    except:

        return {
            "requests":0,
            "failed_rate_percent":0,
            "avg_latency_ms":0,
            "p95_latency_ms":0
        }



def scale(namespace, deployment, replicas):

    cmd = (
        f"kubectl -n {namespace} "
        f"scale deployment {deployment} "
        f"--replicas={replicas}"
    )

    subprocess.check_call(
        cmd,
        shell=True
    )



def smooth_scale(current, target, step=2):

    if target > current:

        return min(
            current + step,
            target
        )


    if target < current:

        return max(
            current - step,
            target
        )


    return current



def decide(
        current,
        ml_prediction,
        cpu,
        p95,
        avg,
        fail,
        requests
):

    if ml_prediction > current:

        if (
            p95 > 2000
            or fail > 1
            or cpu > 80
        ):

            return ml_prediction, "ml_scale_up"



    if ml_prediction < current:

        if (
            fail == 0
            and p95 < 900
            and avg < 500
            and cpu < 30
            and requests < 50
        ):

            return ml_prediction, "ml_scale_down"


    return current, "no_change"



def main():

    p = argparse.ArgumentParser()


    p.add_argument("--namespace", default="thesis-exp")
    p.add_argument("--deployment", default="cpu-app")
    p.add_argument("--selector", default="app=cpu-app")

    p.add_argument(
        "--collector",
        default="http://127.0.0.1:18081/summary"
    )

    p.add_argument("--min", type=int, default=1)
    p.add_argument("--max", type=int, default=6)

    p.add_argument("--interval", type=int, default=5)

    p.add_argument(
        "--cooldown",
        type=int,
        default=60
    )

    p.add_argument(
        "--step",
        type=int,
        default=2
    )


    p.add_argument(
        "--log",
        default="dataset/ml_qos_autoscaler_v3_1_run.csv"
    )


    args = p.parse_args()


    last_scale = 0


    with open(
        args.log,
        "w",
        newline=""
    ) as f:


        fields = [

            "ts",
            "current_replicas",
            "ml_prediction",
            "target_replicas",
            "action",
            "cpu_percent",
            "memory_mi",
            "requests",
            "failed_rate_percent",
            "avg_latency_ms",
            "p95_latency_ms"

        ]


        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()



        while True:


            current = get_replicas(
                args.namespace,
                args.deployment
            )


            pods, cpu, memory = get_top(
                args.namespace,
                args.selector
            )


            qos = get_qos(
                args.collector
            )


            cpu_percent = 0

            if current:

                cpu_percent = (
                    cpu /
                    (current * 100)
                ) * 100



            ml_prediction = predict_replicas(

                cpu_percent,

                memory,

                qos["requests"],

                qos["failed_rate_percent"],

                qos["avg_latency_ms"],

                qos["p95_latency_ms"]

            )


            ml_prediction = max(
                args.min,
                min(
                    ml_prediction,
                    args.max
                )
            )


            target, reason = decide(

                current,

                ml_prediction,

                cpu_percent,

                qos["p95_latency_ms"],

                qos["avg_latency_ms"],

                qos["failed_rate_percent"],

                qos["requests"]

            )


            action = "none"


            now = time.time()


            if target != current:


                target = smooth_scale(
                    current,
                    target,
                    args.step
                )


                if now - last_scale >= args.cooldown:


                    scale(
                        args.namespace,
                        args.deployment,
                        target
                    )


                    last_scale = now


                    action = (
                        f"APPLIED {current}->{target}"
                    )


                else:

                    target = current
                    action = "cooldown"



            row = {

                "ts": int(now),

                "current_replicas": current,

                "ml_prediction": ml_prediction,

                "target_replicas": target,

                "action": action,

                "cpu_percent": round(cpu_percent,2),

                "memory_mi": round(memory,2),

                "requests": qos["requests"],

                "failed_rate_percent":
                    qos["failed_rate_percent"],

                "avg_latency_ms":
                    qos["avg_latency_ms"],

                "p95_latency_ms":
                    qos["p95_latency_ms"]

            }


            writer.writerow(row)

            f.flush()


            print(row)


            time.sleep(
                args.interval
            )


if __name__ == "__main__":
    main()
