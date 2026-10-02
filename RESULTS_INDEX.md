# Paper-to-package index

Run `python reproduce.py` to generate `tables.md`, the two SVG figures, the HTML case companion, and the full numerical JSON outputs. The [preview directory](preview/) contains the same tables and figures from a verified run for readers who prefer not to run Python.

Table numbers follow the manuscript and its appendix. The generated displays preserve the reported quantities, with a browsing layout rather than the manuscript's typesetting.

| Paper item | Distributed input | Recomputed result |
|---|---|---|
| Table 1: configurations | `protocol/configurations.json` | `tables.md`, Table 1 |
| Table 2: primary repeat-adjusted contrast | `data/analysis_cases.csv`, archived bootstrap indexes | `statistical_results.json`: `models.*.core`; Table 2 |
| Table 3: four-response patterns | `data/analysis_cases.csv` | `models.*.joint.Pooled`; Table 3 |
| Table 4: correctness within repeat-consistent cross-view differences | Same | `models.*.joint.Pooled`; Table 4 |
| Table 5: pooled disagreement components | Same | `models.*.core.complete_valid.pooled_components`; Table 5 |
| Table 6: pooled recurrence and emergence | Same | `models.*.persistence.pooled`; Table 6 |
| Table 7: dataset-macro recurrence and emergence | Same | `models.*.persistence.macro`; Table 7 |
| Table 8: Mistral condition accuracy | Same, archived correctness flags | `models.Mistral.accuracy`; Table 8 |
| Table 9: all-model correctness transitions | Same | `models.*.transitions.Pooled`; Table 9 |
| Table 10: joint patterns by dataset | Same | `models.*.joint`; Table 10 |
| Table 11: entity relations | `data/entity_relations.json` | `entity_results.json`: `summary`, `type_pairs`; Table 11 |
| Table 12: secondary contrasts | `data/analysis_boundary.csv` | `statistical_results.json`: `boundary`; Table 12 |
| Figure 1: control design | Configuration and protocol definitions | `design_protocol.svg` |
| Figure 2: core estimates and intervals | Core analysis above | `core_forest.svg` |
| Figure 3: two case illustrations | `examples/*.json` | `case_illustrations.html` (companion view) |

The case companion preserves the four verdicts, archived correctness, cited excerpts and positions, endpoint mappings, and display-unit selection rule. It omits full accepted-root sets and is not a pixel-for-pixel recreation of Figure 3. The selection pools are explicit in `examples/selection.json`.

Additional supporting quantities are also available:

- Mistral confidence: `models.Mistral.confidence` (response-reported confidence, not calibration).
- Original-configuration wrong-to-wrong topology distances: `topology_distance`, using the archived distances in `data/analysis_topology_distances.csv`.
- The two distinct-verdict C-to-C observations with three accepted IDs each: `data/multi_accepted_cases.json` and `entity_results.json`.
- Cohort assignments, exclusions, same-wave execution, and preservation checks: `data/cohort_*.json`, `protocol/*execution.json`, and `protocol/preservation_records.json`.

`generated/verification.json` records the release-hash check, cross-file joins, protocol-record checks, and comparison against archived numerical references. Source-level benchmark rescoring, service-map extraction, full-input compilation, and shortest-path extraction are outside this offline run; see [README.md](README.md#reproduction-scope).
