# Performance Benchmarks

This report summarizes benchmark results gathered with `scripts/performance_benchmarks.py`,
which synthesizes large repositories, provisions dozens of workpads, exercises the Solo Git
engines, and captures timing metrics across critical workflows.【F:scripts/performance_benchmarks.py†L51-L200】【F:scripts/performance_benchmarks.py†L262-L343】

## Test Environment

| Property | Value |
| --- | --- |
| Python | 3.11.12 |
| OS | Linux 6.12.13 (x86_64) |
| Processor | x86_64 |
| Timestamp | 2025-10-22T03:48:03Z |

【F:docs/performance_results.json†L2-L9】

## Repository Initialization

Synthetic repositories of increasing size were generated (including a 1,200-file repository with
10,000 commits produced via `git fast-import`) and imported through `GitEngine.init_from_git`.

| Repo | Files | Commits | Initialization Time (s) |
| --- | --- | --- | --- |
| small | 120 | 200 | 0.0739 |
| medium | 600 | 2,000 | 0.1645 |
| large | 1,200 | 10,000 | 0.2848 |

【F:docs/performance_results.json†L10-L28】【F:scripts/performance_benchmarks.py†L70-L134】

## Workpad Scalability

Creating 60 concurrent workpads on the large repository averaged 60 ms per workpad, with a 95th
percentile of 75.7 ms and a worst case of 87.2 ms—demonstrating consistent branch provisioning even
under heavy load.【F:docs/performance_results.json†L32-L37】

## Test Execution (Sandbox vs. Non-Sandbox)

Running a 10-test serial suite and a 20-test parallel suite directly on the workpad took 0.656 s and
0.798 s respectively. Copying the repository to a disposable “sandbox” before executing the parallel
suite increased runtime to 1.435 s, quantifying the isolation overhead.【F:docs/performance_results.json†L100-L107】【F:scripts/performance_benchmarks.py†L173-L198】

## AI Orchestrator Throughput

Sequential planning and patch generation operations complete in ~8–10 ms with the mock
implementations, while a twelve-request burst finishes with an average latency of 93 ms (142 ms
max). This validates that concurrent AI coordination scales without contention.【F:docs/performance_results.json†L109-L122】【F:scripts/performance_benchmarks.py†L200-L248】

## State File Read/Write

Persisting 300 workpads, test runs, and AI operations (plus 900 emitted events) to the JSON state
backend required 8.85 s, and reloading the aggregate state consumed 54 ms—providing baseline
expectations for the current filesystem-backed state manager.【F:docs/performance_results.json†L123-L132】【F:scripts/performance_benchmarks.py†L300-L343】

## GUI Render Time

An instrumented Heaven Interface boot completed its first render in 0.298 s using the benchmarking
harness’ headless Textual driver.【F:docs/performance_results.json†L133-L135】【F:scripts/performance_benchmarks.py†L344-L411】

## Reproducing the Benchmarks

1. Ensure development dependencies are installed (`pip install -e .[dev]`).
2. Execute `python scripts/performance_benchmarks.py` from the repository root.
3. The script writes raw results to `docs/performance_results.json` and prints a JSON summary,
   which this report reflects.【F:scripts/performance_benchmarks.py†L412-L441】

These measurements provide a baseline for tracking performance regressions and validating scaling
improvements in future Solo Git releases.
