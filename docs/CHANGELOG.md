# Changelog - Kubernetes ML/QoS-Aware Autoscaling Research Project

## [Phase 4: Extended Load Testing & Duration Study] - 2026-10
- **Standardized Workload**: Shifted synthetic loop workload to `LOOPS=120000` to establish reproducible baseline saturation (~50% failure rate at 1 replica).
- **Comprehensive Duration Study**: Configured 4 arms across 4 durations (`120s`, `240s`, `360s`, `480s`) with $n=3$ statistical replicates per arm.
- **Custom Metric Isolation**: Configured `scripts/qos_test_eval.js` to isolate application-specific metrics (`app_requests`, `app_req_failed`, `app_req_duration`) from global k6 telemetry.
- **Automated Orchestration**: Deployed `arm_series.sh` and `arm_run.sh` to guarantee pre-flight readiness (cooldown, replica resets, residual CPU < 20m, empty collector window).
- **Status**: Baseline, HPA, and Rule-based QoS arms completed ($n=3$ replicates each). ML+QoS arm executing to achieve full $n=3$ replicate parity.

## [v3.1] - 2026-08 (FROZEN)
- **Model**: Trained Random Forest Classifier on 6D feature vector: `[cpu_percent, memory_mi, requests, failed_rate_percent, avg_latency_ms, p95_latency_ms]`.
- **Safety Gate**: Added QoS validation layer preventing improper scale-up when healthy or scale-down when stressed.
- **Replica Ladder**: Clamped scaling actions to discrete ladder values `[1, 3, 5, 6]` to eliminate oscillations.
- **Cooldown**: Added strict cooldown timer between scaling interventions to allow cluster stabilization.

## [v3.0] - 2026-07
- Integrated application latency (P95, average) and request failure rates into controller decision loop.
- Added separate metric collector pipeline for ML telemetry (:18081).

## [v2.0] - 2026-06
- Added heuristic decision validation layer in front of raw ML model predictions to prevent invalid scaling actions.

## [v1.0] - 2026-05
- Initial prototype connecting tabular Random Forest predictions directly to Kubernetes Deployment replica scaling.
