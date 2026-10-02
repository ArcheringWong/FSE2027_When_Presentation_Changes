# Experimental protocol

## Interface and evidence construction

The model selects one supplied candidate entity ID or `UNKNOWN` and returns a JSON object containing that verdict, self-reported confidence, up to three supporting evidence IDs, and a short explanation. The exact system instruction and output contract are in `protocol/prompt_and_schema.json`.

A label-blind compiler aggregates telemetry into typed evidence units, ranks within modality with stable-hash tie-breaking, and interleaves modalities by fixed round robin. The medium policy selects at most 96 whole units under a 48,000-byte UTF-8 target. RCA100 topology is bounded to 32 nodes and 64 directed edges. Omitted units remain outside all compared views; there is no subsequent client-side truncation. `protocol/implementation_reference.py.txt` contains selected original compiler, packing, transformation, rendering, and validation definitions for inspection. These excerpts are not a standalone telemetry-processing application.

## Neutral orders and exact repeats

The selected evidence-unit list is globally shuffled with `random.Random(f"{seed}:{dataset}:{case_id}")`. P and R use seeds 20260829 and 20260830. Candidate lists, prompt instructions, output schema, and the multiset of evidence-unit contents remain fixed. The renderer assigns position-local handles O001, O002, and so on after permutation; sequence and those row handles therefore change together. P_prime and R_prime repeat the exact input of P and R.

`protocol/preservation_records.json` retains the archived whole-input checks and scientific-message hashes. The checks include candidate identities and order, typed evidence fields and multiplicities, topology, and exact-repeat payload equality. `verify_protocol.py` checks the completeness and consistency of these records; it does not claim to recompute whole-input equality from hashes alone. The two case files supply actual cited-unit contents and their per-view positions for direct inspection.

## Configurations and collection

`protocol/configurations.json` records the exact requested models and shared decoding settings: temperature 0, top-p 1, request seed 20260830, and a 512-token output limit. Thinking is disabled for Qwen and DeepSeek. Mistral uses the standard non-reasoning interface.

The original configurations collect the neutral pairs and repeats in different periods. Mistral's four conditions are interleaved within one execution wave through OpenRouter with the Mistral endpoint pinned and automatic fallback disabled. `protocol/original_execution.json` and `protocol/mistral_execution.json` retain the relevant schedule, provider, validity, retry, hash, and accounting records. Mistral timestamps are actual submission/completion times. Prompt-cache accounting is distinct from response replay. Account credentials, provider-assigned request IDs, and local filesystem paths are omitted.

## Population

The split reserves 16 RCA100 and 82 AIOps2025 incidents for development, leaving 87 and 318 held-out incidents. Forty-four held-out AIOps2025 roots are not representable in the public candidate set. Two more have byte-identical P/R views and are order-inapplicable. Thus the primary population contains 359 incidents: 87 RCA100 and 272 AIOps2025. The split, candidate-representable cohort, and exclusions are supplied separately. Split strata use dataset, fault group, and entity level; the exported manifest records the resulting assignments without distributing the underlying gold-label strata.

## Analysis

For each complete-valid quadruple, the primary incident score is

`0.5 * ([P != R] + [P_prime != R_prime] - [P != P_prime] - [R != R_prime])`.

Dataset means are averaged with equal weight. The incident bootstrap resamples within dataset for 10,000 replicates. Qwen/DeepSeek use the original Python RNG stream; Mistral uses its archived NumPy indexes. The main-analysis seed is 20260905; original-configuration persistence uses 20260906. INVALID-inclusive analysis retains every applicable incident. UNKNOWN is a valid verdict and is not an invalid response.

Four-response patterns, correctness transitions, and entity relations are descriptive analyses of these observations. Correctness indicators use the benchmark's accepted set, including multiple accepted IDs where present. Confidence is a response field, not a calibrated probability. The secondary serialization, temporal-origin, and topology-serialization contrasts use a transformed view, a compiler-ranked reference, and an exact repeat of that reference; their three-response estimator is distinct from the primary four-response score.
