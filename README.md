# When Presentation Changes the Diagnosis

This review package supports the paper **When Presentation Changes the Diagnosis: Representation Invariance in LLM-Based Root Cause Analysis**. It contains archived event-level observations, experimental records, two real case illustrations, and an offline analysis entry point.

The analysis compares two neutral evidence orders, P and R, and one exact-input repeat of each. The supplied observations cover all 359 order-applicable incidents for each of Qwen, DeepSeek, and Mistral. The Mistral conditions were interleaved in one execution wave; the original two configurations used neutral pairs and later repeats.

## Start here

1. Read [PROTOCOL.md](PROTOCOL.md) for the interface, transformations, and execution records.
2. Run the command below to recreate the statistical tables, forest plot, and case display.
3. Use [RESULTS_INDEX.md](RESULTS_INDEX.md) to find the inputs and outputs corresponding to each paper table and figure.

```sh
python -m pip install -r requirements.txt
python reproduce.py
python -m unittest discover -s analysis -p "test_*.py"
```

Python 3.11 or later is required. The package was tested with Python 3.12.14 and NumPy 2.3.5. Once NumPy is installed, reproduction runs offline, needs no API key or original telemetry download, and writes only to `generated/` (or an external directory supplied with `--output`). A typical run takes under a minute on a desktop CPU. Package file checksums are verified before analysis. Run without Python's `-O` option, because the checks use assertions.

Open `generated/tables.md`, `generated/core_forest.svg`, and `generated/case_illustrations.html`. Exact numerical outputs are in `generated/statistical_results.json` and `generated/entity_results.json`. The presentation is adapted for browsing; the underlying estimates, intervals, and counts correspond to the paper.

For a quick read without running Python, start with the [precomputed tables](preview/tables.md), [core-results plot](preview/core_forest.svg), [design schematic](preview/design_protocol.svg), and [case companion](preview/case_illustrations.html). Download the HTML file to open it locally if the repository viewer displays only its source.

## Contents

| Location | Contents |
|---|---|
| `data/analysis_cases.csv` | All 1,077 model-incident observations, including invalid responses |
| `data/analysis_boundary.csv` | Complete three-response records for the six secondary contrasts |
| `data/analysis_mistral_bootstrap_indexes.npz` | Original Mistral resampling indexes |
| `data/entity_relations.json` | The 358 repeat-consistent, cross-view-different model-incidents and endpoint mapping evidence |
| `data/cohort_*.json` | Development/held-out assignments and applicability exclusions |
| `examples/` | The paper's two cases, four outputs per case, cited input excerpts, and deterministic selection pool |
| `protocol/` | Prompt/schema, configurations, execution metadata, archived preservation records, and selected implementation definitions |
| `analysis/` | Offline statistics, entity analysis, presentation generation, and small regression tests |

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for fields and units and [DATA_NOTICE.md](DATA_NOTICE.md) for dataset attribution, licenses, and modifications.

## Reproduction scope

The scripts recompute statistics from archived verdicts and correctness flags, then compare the results with separately stored reference values. They preserve the original model-specific cohorts, bootstrap streams, UNKNOWN outcomes, and missing service mappings. The package reproduces the paper's statistical analyses without making new provider calls.

Correctness flags retain the original benchmark scoring. Entity relations are reconstructed from exported endpoint metadata and explicit mapping evidence. Raw telemetry, complete gold-label sets, full entity registries, and full model-input payloads are not distributed here; redoing those source-level steps requires access to the original datasets. The case excerpts retain their original content and position, while the full-input preservation results are archived records. Package checksums identify the distributed files; archived request/response hashes identify the original, unmodified provider artifacts.

Upon acceptance, we plan to publicly release the code, analysis scripts, and redistributable result data, subject to the source datasets' licenses and access terms.
