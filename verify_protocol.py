"""Check consistency of exported records; does not reconstruct original payloads."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONDITIONS = ("P", "R", "P_prime", "R_prime")
ORIGINAL = {"qwen": "Qwen", "deepseek": "DeepSeek"}
VIEW_SOURCE = {"P": "evidence_order_primary", "R": "evidence_order_reserve"}
REPEAT_SOURCE = {"P_prime": "primary_exact_repeat", "R_prime": "reserve_exact_repeat"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_index(rows, fields, name):
    index = {tuple(row[field] for field in fields): row for row in rows}
    require(len(index) == len(rows), name + ": duplicate keys")
    return index


def case_key(row):
    return row["dataset"], row["case_id"]


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def load_inputs(root=ROOT):
    root = Path(root)
    def read(relative):
        return json.loads((root / relative).read_text(encoding="utf-8"))
    with (root / "data/analysis_cases.csv").open(encoding="utf-8-sig", newline="") as stream:
        cases = list(csv.DictReader(stream))
    return {
        "split": read("data/cohort_split.json"),
        "eligibility": read("data/cohort_eligibility.json"),
        "exclusions": read("data/cohort_exclusions.json"),
        "cases": cases,
        "entities": read("data/entity_relations.json")["rows"],
        "preservation": read("protocol/preservation_records.json"),
        "mistral": read("protocol/mistral_execution.json"),
        "original": read("protocol/original_execution.json"),
        "configuration": read("protocol/configurations.json"),
        "prompt": read("protocol/prompt_and_schema.json"),
    }


def check_cohorts(data):
    split = unique_index(data["split"], ("dataset", "case_id"), "split")
    require(Counter((r["dataset"], r["split"]) for r in split.values()) == {
        ("RCA100", "development"): 16, ("RCA100", "confirmatory"): 87,
        ("AIOps2025", "development"): 82, ("AIOps2025", "confirmatory"): 318,
    }, "split: archived dataset counts differ")
    require(all(str(r["seed"]) == str(data["configuration"]["split"]["seed"]) for r in split.values()),
            "split: inconsistent seed")
    held_out = {key for key, r in split.items() if r["split"] == "confirmatory"}
    eligibility = unique_index(data["eligibility"], ("dataset", "case_id"), "eligibility")
    excluded = unique_index(data["exclusions"], ("dataset", "case_id"), "exclusions")
    included = set()
    noop = set()
    for key, row in eligibility.items():
        require(key in held_out and row["candidate_representable"] is True and row["replacement"] is False,
                "eligibility: held-out membership or representability mismatch")
        if row["status"] == "INCLUDED":
            require(row["order_applicable"] is True and row["order_noop"] is False
                    and row["historical_order_provider_call_present"] is True, "included case has inconsistent flags")
            included.add(key)
        else:
            require(row["status"] == "PRE_PROVIDER_ORDER_NOOP_EXCLUSION"
                    and row["order_applicable"] is False and row["order_noop"] is True
                    and row["historical_order_provider_call_present"] is False, "no-op flags inconsistent")
            noop.add(key)
    require(len(eligibility) == 361 and len(included) == 359 and len(noop) == 2, "eligibility counts differ")
    require(len(excluded) == 46 and included.isdisjoint(excluded) and set(excluded) | included == held_out,
            "held-out inclusion/exclusion partition differs")
    require(noop == set(eligibility) & set(excluded), "no-op exclusions differ")
    for key, row in excluded.items():
        expected = "P/R byte-identical before provider calls" if key in noop else "labeled root not representable in public candidate set"
        require(row["reason"] == expected, "exclusion reason differs from eligibility")
    cases = unique_index(data["cases"], ("model", "dataset", "case_id"), "analysis cases")
    for model in ("Qwen", "DeepSeek", "Mistral"):
        require({(d, c) for m, d, c in cases if m == model} == included, "model case roster differs from cohort")
    require(len(cases) == 1077, "analysis case row count differs")
    complete = Counter()
    for row in cases.values():
        for condition in CONDITIONS:
            flag = row[condition + "_valid"]
            require(flag in {"0", "1"}, "non-binary validity")
            if flag == "0":
                require(row[condition] == "INVALID" and row[condition + "_correct"] == "", "invalid output fields inconsistent")
            else:
                require(row[condition] != "INVALID" and row[condition + "_correct"] in {"0", "1"}, "valid output fields inconsistent")
                if row[condition] == "UNKNOWN":
                    require(row[condition + "_correct"] == "0", "UNKNOWN scored as correct")
        if all(row[c + "_valid"] == "1" for c in CONDITIONS):
            complete[row["model"]] += 1
    require(complete == {"Qwen": 355, "DeepSeek": 319, "Mistral": 359}, "complete-valid counts differ")
    return {"included": included, "noop": noop, "eligible": set(eligibility), "cases": cases,
            "complete": dict(complete)}


def check_preservation(data, cohort):
    records = data["preservation"]
    order = unique_index(records["order_views"], ("dataset", "case_id"), "order views")
    require(set(order) == cohort["eligible"], "preservation roster differs")
    equal_fields = ("same_case_id", "same_parent_bounded_view_hash", "same_candidate_ids", "same_candidate_order",
                    "same_candidate_types", "same_evidence_multiset_with_multiplicity", "same_evidence_payloads",
                    "same_timestamps_and_values", "same_topology", "preservation_validator_passes")
    for key, row in order.items():
        require(all(row[f] is True for f in equal_fields), "recorded preservation check failed")
        applicable = key in cohort["included"]
        require(row["order_applicable"] is applicable and row["only_evidence_order_differs"] is applicable
                and row["p_r_byte_identical"] is (not applicable), "order preservation/no-op flags inconsistent")
        require(row["status"] == ("PASS_APPLICABLE" if applicable else "PASS_NOOP"), "order status differs")
        require(valid_hash(row["parent_bounded_view_hash"]), "malformed parent-view hash")
    messages = unique_index(records["scientific_messages"], ("dataset", "case_id", "condition"), "scientific messages")
    require(set(messages) == {(d, c, v) for d, c in cohort["included"] for v in ("P", "R")}, "scientific-message roster differs")
    for (dataset, case, _), row in messages.items():
        require(row["parent_bounded_view_hash"] == order[(dataset, case)]["parent_bounded_view_hash"], "message parent-view hash differs")
        require(row["cross_provider_equality"] is True and row["eligibility_status"] == "ORDER_APPLICABLE", "scientific-message flags differ")
        require(all(valid_hash(row[f]) for f in ("source_prompt_hash", "canonical_scientific_message_hash",
                                               "qwen_source_payload_hash", "deepseek_source_payload_hash")), "malformed scientific-message hashes")
    repeats = unique_index(records["exact_repeats"], ("provider", "dataset", "case_id", "repeat_condition"), "exact-repeat checks")
    require(set(repeats) == {(p, d, c, v) for p in ORIGINAL for d, c in cohort["included"] for v in REPEAT_SOURCE}, "exact-repeat roster differs")
    boolean_fields = ("source_payload_file_hash_equal", "reconstructed_payload_hash_equal", "required_payload_hash_equal",
                      "raw_submitted_payload_hash_equal", "model_id_equal", "system_message_equal", "user_message_equal",
                      "response_schema_equal", "generation_parameters_equal", "max_output_equal", "thinking_setting_equal", "tools_stream_equal")
    for (provider, dataset, case, repeat), row in repeats.items():
        view = repeat[0]
        message = messages[(dataset, case, view)]
        require(all(row[f] is True for f in boolean_fields) and row["status"] == "EXACT_MATCH", "archived exact-repeat equality check differs")
        require(row["source_condition"] == VIEW_SOURCE[view], "repeat source condition differs")
        require(row["source_payload_sha256"] == message[provider + "_source_payload_hash"], "repeat source payload hash differs")
        # This legacy audit hashes {messages, response_format}; the common
        # scientific bundle hashes {messages, output_contract}. They have
        # different domains. Join the records by the full source-payload hash.
        require(valid_hash(row["canonical_scientific_sha256"]), "malformed legacy scientific hash")
    return messages, repeats


def check_mistral(data, cohort, messages):
    execution = data["mistral"]
    requests = unique_index(execution["requests"], ("schedule_ordinal",), "Mistral requests")
    require({int(k[0]) for k in requests} == set(range(1, 1437)), "Mistral schedule is not contiguous")
    keyed = unique_index(execution["requests"], ("dataset", "case_id", "condition"), "Mistral conditions")
    require(set(keyed) == {(d, c, v) for d, c in cohort["included"] for v in CONDITIONS}, "Mistral condition roster differs")
    blocks = defaultdict(list)
    model = next(m for m in data["configuration"]["models"] if m["model"] == "Mistral")
    for row in requests.values():
        key = case_key(row)
        condition = row["condition"]
        require(row["request_model"] == row["returned_model"] == model["requested_model"], "Mistral model mismatch")
        require(row["frozen_provider_slug"] == row["selected_endpoint"] == model["provider_slug"]
                and row["actual_upstream_required"] == row["selected_provider"] == row["actual_provider"] == model["upstream"], "Mistral route mismatch")
        require(all(row[f] is True for f in ("model_match", "provider_pinning_ok", "strict_valid", "candidate_valid", "evidence_ids_valid"))
                and row["unauthorized_fallback"] is False and row["invalid_reason"] == "", "Mistral validation flags differ")
        require(all(valid_hash(row[f]) for f in ("canonical_scientific_message_sha256", "request_body_sha256",
                                               "routing_configuration_sha256", "plugin_control_sha256")), "Mistral malformed hash")
        require(row["canonical_scientific_message_sha256"] == messages[(*key, condition[0])]["canonical_scientific_message_hash"], "Mistral scientific hash differs")
        require(cohort["cases"][("Mistral", *key)][condition + "_valid"] == "1", "Mistral analysis validity differs")
        blocks[int(row["case_block_ordinal"])].append(row)
    require(set(blocks) == set(range(1, 360)), "Mistral case blocks differ")
    require(len({r["execution_wave"] for r in requests.values()}) == len({r["schedule_seed"] for r in requests.values()}) == 1, "Mistral execution wave or seed differs")
    for block_id, block in blocks.items():
        require(len(block) == 4 and len({case_key(r) for r in block}) == 1 and {r["condition"] for r in block} == set(CONDITIONS), "Mistral block does not contain one case and four conditions")
        require({int(r["within_block_position"]) for r in block} == {1, 2, 3, 4}, "Mistral within-block positions differ")
        for row in block:
            require(int(row["schedule_ordinal"]) == 4 * (block_id - 1) + int(row["within_block_position"]), "Mistral ordinal/block mapping differs")
        by_condition = {r["condition"]: r for r in block}
        for view in ("P", "R"):
            require(by_condition[view]["request_body_sha256"] == by_condition[view + "_prime"]["request_body_sha256"], "Mistral exact-repeat body hashes differ")
    attempts = defaultdict(list)
    for attempt in execution["attempts"]:
        ordinal = attempt["schedule_ordinal"]
        require((ordinal,) in requests, "attempt has no scheduled request")
        request = requests[(ordinal,)]
        require(all(attempt[f] == request[f] for f in ("dataset", "case_id", "condition", "request_body_sha256")), "attempt/request join mismatch")
        submitted, completed = (datetime.fromisoformat(attempt[f]) for f in ("submitted_utc", "completed_utc"))
        require(submitted.tzinfo is not None and completed.tzinfo is not None and completed >= submitted, "attempt timestamps inconsistent")
        require(float(attempt["latency_ms"]) >= 0 and int(attempt["response_bytes"]) >= 0 and valid_hash(attempt["response_sha256"]), "attempt accounting malformed")
        attempts[ordinal].append(attempt)
    require(len(execution["attempts"]) == 1439 and set(attempts) == {k[0] for k in requests}, "attempt roster/count differs")
    retry_count = 0
    for entries in attempts.values():
        entries.sort(key=lambda r: int(r["attempt"]))
        require([int(r["attempt"]) for r in entries] == list(range(1, len(entries) + 1)), "attempt numbering differs")
        require(entries[-1]["http_status"] == "200" and entries[-1]["retryable"] is False, "last attempt not successful")
        for previous, following in zip(entries, entries[1:]):
            require(previous["http_status"] == "0" and previous["retryable"] is True
                    and datetime.fromisoformat(following["submitted_utc"]) >= datetime.fromisoformat(previous["completed_utc"]), "retry sequence differs")
            retry_count += 1
    require(retry_count == 3, "Mistral transport-retry count differs")
    accounting = unique_index(execution["accounting"], ("schedule_ordinal",), "Mistral accounting")
    cache = unique_index(execution["cache"], ("schedule_ordinal",), "Mistral cache")
    require(set(accounting) == set(cache) == set(requests), "cache/accounting rosters differ")
    for key in accounting:
        row, record = accounting[key], cache[key]
        for field in ("prompt_cached_tokens", "prompt_cache_write_tokens"):
            # Prefix/prompt caching is separately recorded, not response replay.
            require(0 <= int(row[field]) == int(record[field]) <= int(row["input_tokens"]), "recorded cache token count differs")
        require(record["classified_as_response_replay"] is False, "recorded replay flag differs")
        require(int(row["input_tokens"]) > 0 and 0 < int(row["output_tokens"]) <= data["configuration"]["generation"]["max_tokens"]
                and float(row["reported_cost_usd"]) >= 0, "token/cost accounting invalid")
    return {"requests": len(requests), "attempts": len(execution["attempts"]), "transport_retries": retry_count,
            "requests_with_prompt_cached_tokens": sum(int(r["prompt_cached_tokens"]) > 0 for r in accounting.values())}


def check_original(data, cohort, messages, repeats):
    original = data["original"]
    historical = unique_index(original["historical_responses"], ("provider", "dataset", "case_id", "condition"), "historical responses")
    require(len(historical) == 4498, "historical response count differs")
    models = {m["model"]: m["requested_model"] for m in data["configuration"]["models"]}
    expected_historical = set()
    for provider in ORIGINAL:
        for condition in ("baseline", "identity_repeat", "serialization", "temporal_origin"):
            expected_historical.update((provider, d, c, condition) for d, c in cohort["eligible"])
        expected_historical.update((provider, d, c, "topology_serialization") for d, c in cohort["eligible"] if d == "RCA100")
        expected_historical.update((provider, d, c, condition) for d, c in cohort["included"] for condition in VIEW_SOURCE.values())
    require(set(historical) == expected_historical, "historical response roster differs")
    for (provider, dataset, case, condition), row in historical.items():
        require(row["requested_model"] == row["response_model"] == models[ORIGINAL[provider]], "historical model mismatch")
        require(row["received"] is True and row["missing_raw"] is False and row["transport_failure"] is False, "historical receipt flags differ")
        if condition in VIEW_SOURCE.values():
            view = next(k for k, value in VIEW_SOURCE.items() if value == condition)
            analysis = cohort["cases"][(ORIGINAL[provider], dataset, case)]
            require(row["valid"] is (analysis[view + "_valid"] == "1"), "historical/analysis validity mismatch")
    schedule = unique_index(original["repeat_schedule"], ("provider", "dataset", "case_id", "new_condition"), "original repeat schedule")
    responses = unique_index(original["exact_repeat_responses"], ("provider", "dataset", "case_id", "condition"), "original repeat responses")
    expected = {(p, d, c, v) for p in ORIGINAL for d, c in cohort["included"] for v in REPEAT_SOURCE.values()}
    require(set(schedule) == set(responses) == expected, "original repeat roster differs")
    require({int(r["schedule_ordinal"]) for r in schedule.values()} == set(range(1, 1437)), "original repeat ordinal coverage differs")
    blocks = defaultdict(list)
    for (provider, dataset, case, condition), row in schedule.items():
        repeat = next(k for k, value in REPEAT_SOURCE.items() if value == condition)
        view = repeat[0]
        response = responses[(provider, dataset, case, condition)]
        preserved = repeats[(provider, dataset, case, repeat)]
        message = messages[(dataset, case, view)]
        require(row["requested_model_id"] == response["requested_model"] == response["returned_model"] == models[ORIGINAL[provider]], "original repeat model differs")
        require(row["source_condition"] == preserved["source_condition"] == VIEW_SOURCE[view], "original repeat source differs")
        require(row["source_prompt_hash"] == message["source_prompt_hash"], "original repeat prompt hash differs")
        require(row["source_payload_file_sha256"] == row["reconstructed_submitted_payload_sha256"]
                == row["required_exact_submitted_payload_sha256"] == preserved["source_payload_sha256"], "original repeat payload hash records differ")
        require(valid_hash(response["request_hash"]) and valid_hash(response["raw_response_hash"]), "malformed original-response hashes")
        require(response["status"] == "PASS" and response["operational_status"] == "SCIENTIFIC_RESPONSE_RECORDED", "original operational status differs")
        analysis = cohort["cases"][(ORIGINAL[provider], dataset, case)]
        require(response["parsed_status"] == ("VALID" if analysis[repeat + "_valid"] == "1" else "INVALID"), "original repeat/analysis validity differs")
        require(int(response["transport_retries"]) >= 0 and int(response["input_tokens"]) > 0 and int(response["output_tokens"]) > 0, "original response accounting invalid")
        block = int(row["case_block_ordinal"])
        require(int(row["schedule_ordinal"]) == 4 * (block - 1) + int(row["within_block_position"]), "original ordinal/block mapping differs")
        blocks[block].append(row)
    require(set(blocks) == set(range(1, 360)), "original repeat blocks differ")
    for rows in blocks.values():
        require(len(rows) == 4 and len({case_key(r) for r in rows}) == 1
                and {int(r["within_block_position"]) for r in rows} == {1, 2, 3, 4}
                and {(r["provider"], r["new_condition"]) for r in rows} == {(p, c) for p in ORIGINAL for c in REPEAT_SOURCE.values()},
                "original block membership differs")
    return {"historical_responses": len(historical), "exact_repeat_responses": len(responses)}


def check_entity_join(data, cohort):
    expected = {key: row for key, row in cohort["cases"].items()
                if all(row[c + "_valid"] == "1" for c in CONDITIONS)
                and row["P"] == row["P_prime"] and row["R"] == row["R_prime"] and row["P"] != row["R"]}
    entities = unique_index(data["entities"], ("model", "dataset", "case_id"), "entity rows")
    require(len(entities) == 358 and set(entities) == set(expected), "entity subset is not the complete observed repeat-consistent subset")
    for key, entity in entities.items():
        source = expected[key]
        for condition in CONDITIONS:
            response = entity["responses"][condition]
            require(response["root_entity_id"] == source[condition]
                    and response["benchmark_correct"] is (source[condition + "_correct"] == "1"), "entity/core verdict or correctness join mismatch")
    return {"model_incidents": len(entities), "by_model": dict(Counter(r["model"] for r in entities.values()))}


def verify(data):
    require(set(data["configuration"]["conditions"]) == set(CONDITIONS), "configured conditions differ")
    schema = data["prompt"]["output_schema"]
    require(set(schema["required"]) == set(schema["properties"])
            == {"root_entity_id", "confidence", "supporting_evidence_ids", "brief_justification"}, "output schema fields differ")
    cohort = check_cohorts(data)
    messages, repeats = check_preservation(data, cohort)
    return {
        "checks_passed": True,
        "scope": "Internal consistency of exported protocol records and analysis joins. No original payload or telemetry reconstruction is performed.",
        "cohort": {"held_out": 405, "candidate_representable": 361, "order_applicable": 359,
                   "no_op_exclusions": 2, "complete_valid": cohort["complete"]},
        "preservation": {"order_view_records": len(data["preservation"]["order_views"]),
                         "scientific_message_records": len(messages), "exact_repeat_records": len(repeats)},
        "mistral": check_mistral(data, cohort, messages),
        "original": check_original(data, cohort, messages, repeats),
        "entity_join": check_entity_join(data, cohort),
    }


def run():
    return verify(load_inputs())


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
