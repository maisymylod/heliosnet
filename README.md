# Heliosnet

A coherent mission-operations system for a fictional satellite constellation,
built as a set of standalone engineering projects that fit together as one
platform. This repo is the map: how the pieces connect, the live headline metric
for each, the exact command that regenerates each number, and how the system
keeps itself current.

Every number on this page comes from a held-out eval or benchmark that
regenerates from a clean checkout of the named repo. Nothing here is
hand-maintained: `python3 tools/collect_metrics.py` reads each repo's committed
metrics artifact and prints the same table.

## The system

```
                          +-------------------------------+
                          |          operators            |
                          |  console UI + approval gate    |
                          +---------------+----------------+
                                          |
              +---------------------------+---------------------------+
              |                           |                           |
   groundstation-console        groundstation (copilot)        argus (imagery RAG)
   Angular SPA + Go svc   <----  LangGraph agents + HITL  ----> vector search over
   profiled, SLOs, IaC          gate, RAG, tiered router        orbital frames
              |                     |        ^      ^                  ^
              |                     |        |      |                  |
              v                     v        |      |                  |
   +----------+----------+   groundstation-train    groundstation-rag  constellation-vision
   |   telemetry plane   |   SFT + DPO of the       LlamaIndex+Qdrant  from-scratch CV
   |                     |   reasoning core         CI-gated retrieval segmentation -> ONNX
   | constellation       |   (gate-compliance)                          enrichment into argus
   | constellation-stream|        |
   | Kafka->Flink->      |        | trained weights / eval
   | Iceberg->Grafana    |        v
   +----------+----------+   aegis (command authority)
              |              Ed25519 signed envelopes, adversarial defense
              |              aegis-java: cross-language parity port of the crypto core
              v
        liftoff (deploy)   slew (C++20 attitude-control simulator)
        one spec -> cloud / on-prem / air-gap
```

Telemetry flows up from the data plane (`constellation`,
`constellation-stream`) through the agentic copilot (`groundstation`) to the
operator console (`groundstation-console`). The copilot's reasoning core is
trained by `groundstation-train` and grounded by the retrieval systems
(`groundstation-rag`, `argus`). Every command the copilot proposes is
authenticated by `aegis` and only emitted after a human approves it. The whole
thing is deployed by `liftoff`; `slew` simulates the vehicle dynamics the
telemetry describes.

## Live headline metrics

Each number regenerates from a clean checkout of its repo with the listed command.

| Repo | What it measures | Headline (measured) | Regenerate |
|---|---|---|---|
| [constellation-vision](https://github.com/maisymylod/constellation-vision) | defect-segmentation quality, held-out frames | **mean IoU 0.877** (per-class 0.75 to 0.94) | `make eval` |
| [constellation-stream](https://github.com/maisymylod/constellation-stream) | stream throughput + query latency | **38,819 rec/s, p99 32.97 ms at 5,000,000 rows** | `make bench-big` |
| [groundstation-rag](https://github.com/maisymylod/groundstation-rag) | retrieval quality, held-out QA w/ gold citations | **citation-acc 0.967, recall@k 1.0, MRR 0.976** | `make eval` |
| [groundstation-train](https://github.com/maisymylod/groundstation-train) | approval-gate compliance of the reasoning core | **eval harness calibrated: oracle 1.0 vs bypass 0.0**; model lift from a GPU run | `make eval-refs` |
| [groundstation-console](https://github.com/maisymylod/groundstation-console) | profiled hot-path + bundle, before/after | **fleet endpoint ~1720x faster; bundle -17.6%** | `make profile` |
| [aegis-java](https://github.com/maisymylod/aegis-java) | cross-language parity of the crypto core | **38 shared test vectors pass byte-for-byte** | `make test` |
| [groundstation](https://github.com/maisymylod/groundstation) | anomaly-type classifier, held-out satellites | **accuracy 0.967, macro-F1 0.931** | `make train` |
| [aegis](https://github.com/maisymylod/aegis) | adversarial defense efficacy | **11/11 attacks succeed defense-off, 0/11 defense-on** | `make demo` |

**One honest caveat, stated up front:** `groundstation-train`'s model headline (a
base vs SFT+DPO lift) requires a GPU fine-tune and is left as a documented run,
not a claimed number. What is committed and CI-enforced there is the eval harness
itself, calibrated so a gate-compliant policy scores 1.0 and a gate-bypassing one
scores 0.0. Similarly, `constellation-stream`'s benchmark is a real 5,000,000-row
run on one core; the path to billions (parallelism, partitioned topics, object
storage) is documented, not claimed as executed. See each repo's "What is real vs
simulated" section.

## The repos

**Data plane**
- **constellation**: streaming telemetry ingest, anomaly detection, ops console (Redpanda to Timescale).
- **constellation-stream**: the production-scale streaming evolution: Kafka to Flink to Iceberg to Grafana, with stateful event-time windowing, late-data handling, and an exactly-once sink.

**Reasoning + retrieval**
- **groundstation**: agentic mission-ops copilot: LangGraph multi-agent graph, MCP tools, RAG over playbooks, tiered model router, a trained classifier, all behind a human-in-the-loop approval gate.
- **groundstation-train**: SFT + DPO alignment of the copilot's reasoning core to obey the approval gate, with a CI-validated held-out ops eval.
- **groundstation-rag**: retrieval over a large engineering/standards corpus (LlamaIndex + Qdrant) with retrieval quality enforced as a CI gate.
- **argus**: retrieval and vector search over orbital imagery.
- **constellation-vision**: a from-scratch segmentation model for orbital-hardware defect inspection, exported to ONNX and served as an argus enrichment step.

**Console + security + delivery**
- **groundstation-console**: production-grade ops console: Angular SPA over a Go service, Kafka push, profiled hot paths, SLO dashboards, Terraform infra, Bazel build.
- **aegis**: signed-command authority (Ed25519 envelopes, chain to an offline root, rotation, replay protection) plus an adversarial defense harness.
- **aegis-java**: a cross-language parity port of the aegis cryptographic core, proven against shared test vectors.
- **liftoff**: declarative deploy: one suite spec to validated cloud / on-prem / air-gapped artifacts.
- **slew**: a C++20 attitude-control simulator for the vehicle dynamics the telemetry reflects.

## How the system improves itself

The activity in the commit history is real work, not motion for its own sake. The
loops are honest: a job that has nothing real to commit commits nothing.

1. **Scheduled retraining with eval gating.** The model repos
   (`groundstation-train`, `constellation-vision`) run a scheduled job that
   regenerates data, retrains, runs the held-out eval, and commits the new
   checkpoint and eval report **only if the metric actually moved**, with the real
   delta in the commit message. A flat or regressed metric commits nothing.
2. **Drift detection.** `constellation-vision` and `constellation-stream` carry a
   distribution-drift guard with committed reference statistics, so a genuine
   shift in the incoming synthetic data is what triggers an update.
3. **Continuous eval reports.** Each model/retrieval repo regenerates its eval
   report and a metric-over-time history on every run, so the improvement curve is
   always current and backed by reproducible numbers.
4. **Reproduce guards.** Repos with deterministic headline numbers run a nightly
   job that re-derives those numbers from a clean checkout and fails loudly if
   they drift, catching dependency rot rather than manufacturing commits.
5. **Identity discipline.** All automated commits are authored by
   `heliosnet-ci[bot]`, distinct from the human engineering commits, so it is
   always clear which activity is the pipeline and which is hand-written.

## Reproduce the metrics table

```bash
# from a workspace containing the sibling repos:
python3 tools/collect_metrics.py            # reads each repo's committed artifact
```

It prints only what is on disk: a repo whose eval has not been run shows
"not generated" rather than a fabricated number.

## Capabilities demonstrated

Streaming data engineering (Kafka/Flink/Iceberg, exactly-once, scale benchmarking);
anomaly-detection and computer-vision model training from scratch with held-out
evaluation; large-language-model fine-tuning and preference alignment (LoRA/QLoRA,
DPO) with distributed training; retrieval systems with CI-gated quality;
multi-agent orchestration with a human-in-the-loop control gate; cryptographic
command authentication and adversarial defense; full-stack application
engineering with profiling and SLOs; infrastructure-as-code and multi-target
delivery; cross-language porting with proven parity; and C++ simulation. Across
all of it: reproducible evals, honest reporting of what is measured versus
simulated versus documented, and automation that is visibly the pipeline's rather
than dressed up as human work.

## Conventions

Every repo: MIT licensed, a one-command demo from a clean clone, tests plus a CI
quality gate, deterministic seeds, an architecture diagram, and an explicit
"What is real vs simulated" section. Headline numbers are regenerable or they are
not published. See [docs/architecture.md](docs/architecture.md) for the data-flow
detail.
