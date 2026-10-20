---
name: benchmarking-and-evaluation
description: Standards for reproducible benchmarking, multi-metric measurement, and acceptance gates.
---

# Benchmarking and Evaluation Skill

## Principles
1. Benchmarks must run under identical, deterministic test workloads (fixed dataset, batch size, prompt length).
2. Separate cold-start / model loading time from steady-state inference latency. Use warm-up runs followed by multi-iteration measurement (median, P95).
3. Explicitly label metric types: Measured (hardware sensor/timer), Estimated (documented mathematical model), or Unavailable (`null`/`Unavailable`).
4. Never invent numbers. If energy or water cannot be measured defensibly, indicate that clearly.
5. Provide configurable acceptance criteria gates (e.g., maximum quality loss $\le 3\%$, size reduction $\ge 40\%$) with clear pass/fail rationale.
