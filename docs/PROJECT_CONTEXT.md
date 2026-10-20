# SYSTEM RECOVERY CONTEXT: KUBERNETES ML/QoS-AWARE AUTOSCALING RESEARCH PROJECT

## 1. Project Identity & Research Positioning
- **Owner**: Mohammadali Nastaran
- **Degree**: Master's Thesis
- **Domain**: Cloud Computing, Kubernetes Resource Management, Machine Learning Autoscaling, QoS Assurance
- **Immutable Defense Statement (Core Scientific Claim)**:
  > "The contribution of this work is not replacing Kubernetes HPA, but introducing an extensible ML/QoS-aware decision layer that combines resource utilization and service quality indicators for Kubernetes autoscaling decisions."

### Strict Academic Guardrails
- **NEVER** claim that the system "replaces HPA" or is a "production-ready autoscaler".
- **NEVER** claim "ML always beats HPA" or that "HPA is bad".
- **NEVER** treat single experimental runs as definitive means, distributions, or confidence intervals.
- **NEVER** cite bootstrap holdout accuracy or mixed global metrics (`http_req_*`) as application QoS results.
- **NEVER** position the thesis as the first use of ML for autoscaling (predictive autoscaling with LSTM/GRU, RL, etc., already exists in literature). The specific contribution here is the extensible decision layer combining resource metrics with QoS signals, cooldown, and smooth ladder transitions.
- The evaluation is strictly an empirical comparison among four arms:
  1. Fixed-replica baseline (1 replica)
  2. Kubernetes CPU-based HPA
  3. Rule-based QoS-aware controller
  4. ML+QoS-aware decision layer (v3.1)

---

## 2. Infrastructure & Topology
- **Live Environment Tree**: `/root/master-thesis-evidence/10-extended-load-tests`
- **Host / Access**: `kind` host at `192.168.248.71:2230` (User: `limooadmin`, root privileged via `sudo -i`).
- **Cluster**: Kind v1.35.0, containerd 2.2.0, Docker Network `172.18.0.0/16`.
  - Nodes: `kind-control-plane` (172.18.0.3), `kind-worker` (172.18.0.5), `kind-worker2` (172.18.0.4), `kind-worker3` (172.18.0.2).
- **Workload / Application**:
  - Namespace: `thesis-exp` | Deployment: `cpu-app` | Service: NodePort `32232` -> Pod Port `8080`.
  - Target NodePort endpoint: `http://172.18.0.2:32232` (Note: internal IP resolved per Kind cluster instantiation).
  - Pod limits: CPU request `100m`, limit `500m`; Memory request `64Mi`, limit `256Mi`.
  - Synthetic CPU burn: `BURN_MS=40` with a linear congruential loop on GET `/?loops=${LOOPS}`.
- **Metrics Infrastructure**:
  - In-cluster `metrics-server` with `--kubelet-insecure-tls` patch.
  - External host-level Python collectors (out-of-cluster control plane):
    - `:18080` (`scripts/metrics_collector.py`): Used by Rule-based QoS controller and Baseline/HPA runs.
    - `:18081` (`scripts/metrics_collector_ml.py`): Used by ML+QoS controller.
    - Collector contract: POST `/record` (or `/ingest`), GET `/summary` (window: 30s).

---

## 3. Active Arms & Controller Logic Specifications

### Arm 1: Baseline
- Constant `replicas: 1`. Neither HPA nor host controllers are running.

### Arm 2: HPA (`manifests/hpa.yaml`)
- `autoscaling/v2`, target `CPU averageUtilization: 50%` of request (100m).
- `minReplicas: 1`, `maxReplicas: 6`.
- Policy: Scale-up stabilization `0s` (+6 pods / 15s); Scale-down stabilization `60s` (1 pod / 60s).
- *Strict Rule*: Delete HPA manifest completely before running any other controller arm.

### Arm 3: Rule-based QoS (`scripts/qos_aware_autoscaler.py`)
- Live Runtime Parameters: `interval=5s`, `cooldown=15s`, `min=1`, `max=6`, `step=2`.
- Collector: Reads `http://127.0.0.1:18080/summary?window=30`.
- Scale-up trigger: `P95 >= 2000ms` OR `avg >= 1000ms` OR `failure_rate >= 0.1%` OR `CPU >= 50%`.
- Scale-down trigger: `P95 <= 900ms` AND `avg <= 500ms` AND `CPU <= 25%`.

### Arm 4: ML+QoS Controller v3.1 (`scripts/ml_qos_autoscaler_v3_1.py` - FROZEN)
- Status: **FROZEN**. Model, feature order, thresholds, cooldown, and ladder logic are strictly locked.
- Input Features (6D Vector): `[cpu_percent, memory_mi, requests, failed_rate_percent, avg_latency_ms, p95_latency_ms]`.
- ML Model: `dataset/random_forest_model.pkl` (Random Forest Classifier predicting target replica class).
- Decision & Safety Layer:
  - Replica Ladder smoothing: Target clamped into `[1, 3, 5, 6]`.
  - QoS Safety Gate: Scale-up allowed only if stressed; scale-down allowed only if stable.
  - Cooldown: Enforces cooldown window (60s live default) between actual scaling actions.
  - Collector: Reads `http://127.0.0.1:18081/summary`.

---

## 4. Experimental Protocol & Methodological Integrity
- **Load Generator**: Grafana k6 running `scripts/qos_test_eval.js`.
- **Traffic Profile (Frozen Matrix)**:
  - Virtual Users (VUs): `20`
  - Durations: `120s`, `240s`, `360s`, `480s`
  - Workload Parameter: `LOOPS=120000` (Enforces uniform ~40ms synthetic CPU burn per request).
  - *Methodology Note*: Historical runs using `LOOPS=30000` have been archived. Under `LOOPS=120000`, the baseline arm saturates completely (~50% failure rate across all durations).
- **Metric Extraction**:
  - Filter ONLY application-specific custom metrics: `app_requests`, `app_req_failed`, `app_req_duration` (P95 and avg).
  - Explicitly discard and ignore k6 global metrics (`http_req_*`), as they include background collector telemetry.
- **Evidence Schema per Run**:
  Every executed run directory (`evaluation/final_duration_study/<arm>/<duration>s-run<N>/`) stores:
  - `k6.txt`, `k6_summary.json`, `k6_exit_code.txt`
  - `k8s_before.txt`, `k8s_after.txt`
  - `collector_final.json`, `controller.csv` (when applicable), `run_meta.txt`

---

## 5. Execution State & Status Tracking
- **Baseline Arm (n=3 replicates each: 120s, 240s, 360s, 480s)**: Completed.
- **HPA Arm (n=3 replicates each: 120s, 240s, 360s, 480s)**: Completed.
- **Rule-based QoS Arm (n=3 replicates each: 120s, 240s, 360s, 480s)**: Completed.
- **ML+QoS Arm (v3.1)**:
  - `120s-run1`: Valid and complete.
  - Remaining 11 runs: `240:1 360:1 480:1 120:2 240:2 360:2 480:2 120:3 240:3 360:3 480:3` executed via runner script `/home/limooadmin/arm_series.sh`.
- **Consolidation**:
  - Script: `/home/limooadmin/build_summary.py` compiles `summary.csv` and `means.csv`.
