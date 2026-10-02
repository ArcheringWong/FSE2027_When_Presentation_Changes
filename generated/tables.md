# Recomputed manuscript tables

Table numbers follow the submitted manuscript. Values below come from the local recomputation. Layout is adapted for review in a browser. C/W denotes benchmark-correct/wrong; P' and R' are exact-input repeats of P and R. Intervals are 95% percentile bootstrap intervals.

## Table 1. Fixed configurations and four-condition timing

| Configuration | Exact requested model | P/R/P'/R' collection | Study role |
| --- | --- | --- | --- |
| Qwen | qwen3.7-plus-2026-05-26 | neutral pair then later exact repeats | original confirmation |
| DeepSeek | deepseek-v4-pro | neutral pair then later exact repeats | original confirmation |
| Mistral | mistralai/mistral-large-2512 | one interleaved execution wave | third-configuration replication |

Shared decoding: temperature 0, top-p 1, request seed 20260830, output limit 512 tokens. Tools and streaming are disabled.

## Table 2. Repeat-adjusted neutral-order disagreement

| Configuration | Complete n | RCA100 estimate [CI] | AIOps2025 estimate [CI] | Equal-dataset macro [CI] | INVALID-inclusive macro |
| --- | --- | --- | --- | --- | --- |
| Qwen | 355 | 0.2824 [0.1941, 0.3765] | 0.4370 [0.3815, 0.4926] | 0.3597 [0.3089, 0.4138] | 0.3586 |
| DeepSeek | 319 | 0.2829 [0.1842, 0.3816] | 0.4588 [0.3992, 0.5185] | 0.3709 [0.3141, 0.4297] | 0.3802 |
| Mistral | 359 | 0.3448 [0.2529, 0.4425] | 0.4228 [0.3658, 0.4779] | 0.3838 [0.3304, 0.4383] | 0.3838 |

The final column uses all 359 order-applicable incidents per configuration and encodes schema-invalid responses as INVALID.

## Table 3. Post-hoc exhaustive four-response decomposition

| Configuration | All four same | Repeat-stable, cross-view different | Any within-view change |
| --- | --- | --- | --- |
| Qwen | 140 (39.4%) | 118 (33.2%) | 97 (27.3%) |
| DeepSeek | 146 (45.8%) | 121 (37.9%) | 52 (16.3%) |
| Mistral | 105 (29.2%) | 119 (33.1%) | 135 (37.6%) |

Within-view change means P != P' or R != R'. Counts use the complete-valid cohort.

## Table 4. Joint correctness with agreement within each view and disagreement across views

| Configuration | n | P:C / R:W | P:W / R:C | Both wrong | Both correct |
| --- | --- | --- | --- | --- | --- |
| Qwen | 118 | 4 | 3 | 111 | 0 |
| DeepSeek | 121 | 3 | 6 | 112 | 0 |
| Mistral | 119 | 12 | 6 | 101 | 0 |

Each row is restricted to P = P', R = R', and P != R. Units are unique model-incident observations.

## Table 5. Pooled complete-valid component rates

| Configuration | A: P != R | B: P' != R' | C: P != P' | D: R != R' |
| --- | --- | --- | --- | --- |
| Qwen | 0.5803 | 0.5437 | 0.1606 | 0.1634 |
| DeepSeek | 0.5078 | 0.4953 | 0.0784 | 0.0909 |
| Mistral | 0.6156 | 0.6295 | 0.1950 | 0.2423 |

These pool incidents within configuration; the primary estimand instead gives each dataset equal weight.

## Table 6. Post-hoc incident-pooled persistence

| Configuration | Complete n | Recurrence | Emergence | Gap [CI] | Jaccard | Timing |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen | 355 | 0.8981 | 0.0537 | 0.8444 [0.7874, 0.8958] | 0.8645 | cross-period |
| DeepSeek | 319 | 0.9074 | 0.0701 | 0.8373 [0.7767, 0.8935] | 0.8497 | cross-period |
| Mistral | 359 | 0.8778 | 0.2319 | 0.6459 [0.5622, 0.7255] | 0.7668 | same wave |

Recurrence = Pr(B=1 | A=1), emergence = Pr(B=1 | A=0), and gap = recurrence - emergence.

## Table 7. Post-hoc equal-dataset persistence sensitivity

| Configuration | RCA100 recurrence / emergence / gap | AIOps2025 recurrence / emergence / gap | Macro recurrence | Macro emergence | Macro gap [CI] |
| --- | --- | --- | --- | --- | --- |
| Qwen | 0.8605 / 0.0714 / 0.7890 | 0.9080 / 0.0467 / 0.8612 | 0.8842 | 0.0591 | 0.8251 [0.7511, 0.8917] |
| DeepSeek | 0.7941 / 0.0952 / 0.6989 | 0.9375 / 0.0609 / 0.8766 | 0.8658 | 0.0781 | 0.7878 [0.6985, 0.8712] |
| Mistral | 0.8167 / 0.2593 / 0.5574 | 0.9006 / 0.2252 / 0.6754 | 0.8586 | 0.2422 | 0.6164 [0.5064, 0.7181] |

## Table 8. Mistral condition accuracy

| Condition | Overall | RCA100 | AIOps2025 |
| --- | --- | --- | --- |
| P | 77/359 (0.2145) | 15/87 (0.1724) | 62/272 (0.2279) |
| R | 69/359 (0.1922) | 13/87 (0.1494) | 56/272 (0.2059) |
| P' | 78/359 (0.2173) | 14/87 (0.1609) | 64/272 (0.2353) |
| R' | 68/359 (0.1894) | 13/87 (0.1494) | 55/272 (0.2022) |

## Table 9. Post-hoc verdict consequences for all four comparisons

| Configuration | Pair | Changed | C to W | W to C | W to W | C to C |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen | P/R | 206 | 6 | 6 | 193 | 1 |
| Qwen | P'/R' | 193 | 7 | 9 | 177 | 0 |
| Qwen | P/P' | 57 | 4 | 3 | 49 | 1 |
| Qwen | R/R' | 58 | 2 | 3 | 53 | 0 |
| DeepSeek | P/R | 162 | 4 | 9 | 149 | 0 |
| DeepSeek | P'/R' | 158 | 8 | 6 | 143 | 1 |
| DeepSeek | P/P' | 25 | 0 | 8 | 17 | 0 |
| DeepSeek | R/R' | 29 | 1 | 2 | 25 | 1 |
| Mistral | P/R | 221 | 22 | 14 | 183 | 2 |
| Mistral | P'/R' | 226 | 24 | 14 | 188 | 0 |
| Mistral | P/P' | 70 | 5 | 6 | 58 | 1 |
| Mistral | R/R' | 87 | 6 | 5 | 75 | 1 |

Changed means different verdict values (candidate ID or UNKNOWN), not necessarily a correctness change.

## Table 10. Dataset-specific joint observations

| Configuration | Dataset | Complete n | Both repeats agree | Different / agree | C/W | W/W |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen | RCA100 | 85 | 58 | 19/58 (32.8%) | 1 | 18 |
| Qwen | AIOps2025 | 270 | 200 | 99/200 (49.5%) | 6 | 93 |
| DeepSeek | RCA100 | 76 | 56 | 18/56 (32.1%) | 1 | 17 |
| DeepSeek | AIOps2025 | 243 | 211 | 103/211 (48.8%) | 8 | 95 |
| Mistral | RCA100 | 87 | 42 | 22/42 (52.4%) | 5 | 17 |
| Mistral | AIOps2025 | 272 | 182 | 97/182 (53.3%) | 13 | 84 |

C/W combines the two directions of correctness exchange; W/W counts two different wrong verdicts in the repeat-stable subset.

## Table 11. Entity relations within repeat-consistent cross-view differences

| Configuration | n | Same type | Different type | Same service | Different service | Service missing | Service N/A | UNKNOWN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen | 118 | 63 | 34 | 3 | 20 | 68 | 6 | 21 |
| DeepSeek | 121 | 78 | 37 | 12 | 24 | 78 | 1 | 6 |
| Mistral | 119 | 50 | 68 | 4 | 14 | 96 | 4 | 1 |

Type and service are separate classifications. N/A includes a host/node endpoint; missing denotes an unresolved explicit service mapping.

## Table 12. Single-reference repeat-adjusted boundary estimates

| Transformation | Configuration | Complete n (RCA100/AIOps2025) | Estimate [CI] |
| --- | --- | --- | --- |
| Serialization | Qwen | 358 (84/274) | 0.0823 [0.0247, 0.1386] |
| Serialization | DeepSeek | 343 (83/260) | 0.1179 [0.0790, 0.1601] |
| Temporal origin | Qwen | 358 (85/273) | 0.0004 [-0.0422, 0.0434] |
| Temporal origin | DeepSeek | 338 (82/256) | 0.0315 [0.0015, 0.0617] |
| Topology serialization | Qwen | 84 (84/--) | 0.0238 [-0.0714, 0.1190] |
| Topology serialization | DeepSeek | 78 (78/--) | 0.1026 [0.0256, 0.1923] |

The boundary estimator uses transformed-versus-reference disagreement minus exact-repeat-versus-reference disagreement. Mistral was not evaluated under these conditions.
