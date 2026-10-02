# Data dictionary

## Model incident observations

`data/analysis_cases.csv` has one row per model, dataset, and case ID, including all 359 applicable incidents per model. Original public dataset IDs are retained for joins. Row ordering is fixed because it indexes the archived resampling stream.

- `P`, `R`, `P_prime`, `R_prime`: parsed candidate ID, UNKNOWN, or INVALID.
- The matching `_valid` field is 1 for a schema-valid response and 0 otherwise.
- `_correct` is the archived benchmark score, encoded as 1/0. Empty denotes an unavailable score, not an incorrect response. Complete-valid cohorts have all four scores.
- `_confidence` is the original self-reported value. Only Mistral values are included because the paper's confidence statement concerns that configuration; empty Qwen/DeepSeek fields do not mean zero.

`data/analysis_boundary.csv` stores model/dataset/incident/transformation triples and retains their original row order. It is the complete-valid input for the six secondary estimates, not the 359-incident primary cohort. `data/analysis_topology_distances.csv` retains existing RCA100 wrong-to-wrong pair distances for the original configurations; the script summarizes these values rather than reloading the source graphs.

## Entity relations and examples

`data/entity_relations.json` contains one row per model-incident satisfying P=P_prime, R=R_prime, and P!=R. Endpoint types use the original dataset vocabulary. Service mapping distinguishes resolved, missing, ambiguous, inapplicable, and UNKNOWN states. Pair status follows the original precedence; missing mapping is not evidence of different services. Exported matching evidence supports the deterministic relation classification without distributing a complete entity registry.

`examples/selection.json` records the existing deterministic selection rule and eligible incident keys. The two case files contain the four archived outputs and the cited evidence units, including original content, per-view row handles/positions, and content hashes. They are excerpts, not complete model inputs. `analysis/entity_analysis.py` validates and displays them.

## Protocol and reference files

`data/cohort_split.json` lists development/confirmatory assignments. `cohort_eligibility.json` contains the 361 candidate-representable incidents; `cohort_exclusions.json` lists the 44 candidate exclusions and two order no-ops.

Protocol files contain archived check results and request/response provenance. Some original numeric fields are serialized as strings; the verification code converts the fields it tests explicitly. Hashes ending in `_sha256` refer to original archived bytes unless stated otherwise. They are not hashes of anonymized export rows. `MANIFEST.json` instead covers the distributed package bytes.

The legacy exact-repeat `canonical_scientific_sha256` hashes `{messages, response_format}`; the later `canonical_scientific_message_hash` hashes `{messages, output_contract}`. These are different definitions. Records are joined through matching source-payload hashes; Mistral scientific-message hashes use the later definition.

The `analysis_expected.json` and `entity_expected.json` files are regression references read after computation. They are not analysis inputs used to generate the estimates. Full-precision generated JSON uses proportions; displayed percentages multiply by 100. Pair observations and unique model-incidents are separate counting units throughout.
