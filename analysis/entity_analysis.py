"""Recompute entity partitions and verify the two examples without network access."""
from __future__ import annotations

import hashlib
import csv
import json
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("P", "R", "P_prime", "R_prime")
TYPE_LEVELS = ("same_type", "different_type", "unknown_verdict", "missing")
SERVICE_LEVELS = ("same_service", "different_service", "not_applicable", "missing", "ambiguous", "unknown_verdict")


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def content_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def type_relation(left, right):
    if "UNKNOWN" in {left["entity_id"], right["entity_id"]}:
        return "unknown_verdict"
    if not left["entity_type"] or not right["entity_type"]:
        return "missing"
    return "same_type" if left["entity_type"] == right["entity_type"] else "different_type"


def service_relation(left, right):
    states = {left["service_status"], right["service_status"]}
    for special in ("unknown_verdict", "ambiguous", "not_applicable", "missing"):
        if special in states:
            return special
    assert states == {"resolved"}
    return "same_service" if left["service_ids"] == right["service_ids"] else "different_service"


def correctness_pattern(p_correct, r_correct):
    assert type(p_correct) is bool and type(r_correct) is bool
    if p_correct and r_correct:
        return "both_correct"
    if p_correct:
        return "P_correct_R_wrong"
    if r_correct:
        return "P_wrong_R_correct"
    return "both_wrong"


def verify_row(row):
    responses = row["responses"]
    p, r = responses["P"], responses["R"]
    assert p == responses["P_prime"] and r == responses["R_prime"]
    assert p["root_entity_id"] != r["root_entity_id"]
    assert row["correctness_pattern"] == correctness_pattern(p["benchmark_correct"], r["benchmark_correct"])
    left, right = row["endpoints"]["P"], row["endpoints"]["R"]
    for condition, endpoint in (("P", left), ("R", right)):
        assert endpoint["entity_id"] == responses[condition]["root_entity_id"]
        assert len(endpoint["service_ids"]) == len(endpoint["service_names"])
        if endpoint["service_status"] == "resolved":
            assert len(endpoint["service_ids"]) == 1
            proved = {item for proof in endpoint["service_proofs"] for item in proof.get("candidate_service_ids", [])}
            assert proved == set(endpoint["service_ids"])
        if endpoint["service_status"] in {"not_applicable", "unknown_verdict", "missing"}:
            assert not endpoint["service_ids"]
        if endpoint["entity_id"] == "UNKNOWN":
            assert endpoint["service_status"] == "unknown_verdict"
            assert responses[condition]["benchmark_correct"] is False
    assert row["type_relation"] == type_relation(left, right)
    assert row["service_relation"] == service_relation(left, right)


def summarize(rows):
    summary = []
    for model in ("Qwen", "DeepSeek", "Mistral"):
        for dataset in ("ALL", "RCA100", "AIOps2025"):
            for pattern in ("ALL", "P_correct_R_wrong", "P_wrong_R_correct", "both_wrong", "both_correct"):
                part = [r for r in rows if r["model"] == model and (dataset == "ALL" or r["dataset"] == dataset)
                        and (pattern == "ALL" or r["correctness_pattern"] == pattern)]
                types = Counter(type_relation(r["endpoints"]["P"], r["endpoints"]["R"]) for r in part)
                services = Counter(service_relation(r["endpoints"]["P"], r["endpoints"]["R"]) for r in part)
                result = {"model": model, "dataset": dataset, "correctness_pattern": pattern, "n": len(part)}
                result.update({"type_" + level: types[level] for level in TYPE_LEVELS})
                result.update({"service_" + level: services[level] for level in SERVICE_LEVELS})
                assert sum(types.values()) == sum(services.values()) == len(part)
                summary.append(result)
    return summary


def verify_examples(rows):
    selection = load("examples/selection.json")
    index = {(r["model"], r["dataset"], r["case_id"]): r for r in rows}
    results = []
    for chosen in selection["selections"]:
        kind = chosen["illustration_kind"]
        example = load("examples/" + kind + ".json")
        patterns = ({"P_correct_R_wrong", "P_wrong_R_correct"} if kind == "correctness_discordant" else {"both_wrong"})
        eligible = [r for r in rows if r["model"] == "Mistral" and r["correctness_pattern"] in patterns
                    and r["type_relation"] in {"same_type", "different_type"}]
        preferred = [r for r in eligible if r["service_relation"] in {"same_service", "different_service"}]
        pool = sorted(preferred or eligible, key=lambda r: (r["dataset"], r["case_id"]))
        keys = [{"dataset": r["dataset"], "case_id": r["case_id"]} for r in pool]
        assert chosen["candidate_incidents"] == keys
        assert chosen["preferred_service_resolved"] is bool(preferred)
        assert chosen["selected"] == keys[0] == {"dataset": example["dataset"], "case_id": example["case_id"]}
        row = index[(example["model"], example["dataset"], example["case_id"])]
        assert example["endpoints"] == row["endpoints"]
        assert example["correctness_pattern"] == row["correctness_pattern"]
        units = {unit["content_identity_sha256"]: unit for unit in example["cited_evidence_excerpt"]}
        assert len(units) == len(example["cited_evidence_excerpt"])
        for identity, unit in units.items():
            assert content_hash(unit["content"]) == identity
            assert len(unit["P_positions"]) == len(unit["R_positions"]) > 0
            for view in ("P", "R"):
                assert len(unit[view + "_positions"]) == len(unit[view + "_evidence_ids"])
                for position, handle in zip(unit[view + "_positions"], unit[view + "_evidence_ids"]):
                    assert 1 <= position <= example["evidence_count"]
                    assert handle == f"O{position:03d}"
        cited = set()
        for condition in CONDITIONS:
            response = example["outputs"][condition]
            assert response["root_entity_id"] == row["responses"][condition]["root_entity_id"]
            assert response["benchmark_correct"] is row["responses"][condition]["benchmark_correct"]
            handles = response["supporting_evidence_ids"]
            identities = response["supporting_content_identities"]
            assert len(handles) == len(identities)
            assert 0 <= response["confidence"] <= 1
            for handle, identity in zip(handles, identities):
                assert identity in units
                assert handle in units[identity][condition[0] + "_evidence_ids"]
                cited.add(identity)
        assert cited == set(units)
        assert example["outputs"]["P"]["input_body_sha256"] == example["outputs"]["P_prime"]["input_body_sha256"]
        assert example["outputs"]["R"]["input_body_sha256"] == example["outputs"]["R_prime"]["input_body_sha256"]
        results.append({"illustration_kind": kind, "dataset": example["dataset"], "case_id": example["case_id"],
                        "selection_pool_size": len(pool), "cited_units": len(units), "outputs": 4})
    return results


def figure_units(example):
    """The manuscript display rule: largest cited trace count, then hash."""
    chosen = []
    for view in ("P", "R"):
        service_ids = example["endpoints"][view]["service_ids"]
        assert len(service_ids) == 1
        eligible = [u for u in example["cited_evidence_excerpt"]
                    if u["content"]["modality"] == "trace"
                    and u["content"]["target_entity_id"] == service_ids[0]
                    and "error_rate" in u["content"]["numeric_summary"]]
        assert eligible
        chosen.append(min(eligible, key=lambda u: (-u["content"]["count"], u["content_identity_sha256"])))
    return chosen


def render_examples(output_dir):
    """Create a standalone, offline Figure 3 companion and full excerpt view."""
    def text(value):
        return escape(str(value))

    def cell(value):
        return "<td>" + text(value) + "</td>"

    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<title>Two Mistral case illustrations</title>",
             "<style>body{font:16px/1.5 system-ui,sans-serif;color:#16212b;max-width:1080px;margin:32px auto;padding:0 20px}"
             "section{border:1px solid #bac2c8;padding:24px;margin:24px 0;border-radius:6px}h1,h2,h3{line-height:1.2}"
             "table{border-collapse:collapse;width:100%;margin:16px 0}th,td{padding:9px 10px;border-bottom:1px solid #dce1e4;text-align:left;vertical-align:top}"
             "th{background:#f1f4f6}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}details{margin:16px 0}"
             "code{font-family:ui-monospace,monospace}small{color:#465260}@media print{section{break-inside:avoid}body{margin:0}}</style>",
             "<h1>Two Mistral case illustrations</h1>",
             "<p>Each view has one exact repeat. C and W denote archived benchmark-correct and benchmark-wrong outcomes. "
             "Positions are one-based. The trace rows use the manuscript display rule: for each selected service, "
             "choose the cited trace with the largest count, breaking ties by its content hash.</p>"]
    for kind in ("correctness_discordant", "both_wrong"):
        example = load("examples/" + kind + ".json")
        title = "Different correctness" if kind == "correctness_discordant" else "Different wrong services"
        parts.extend(["<section><h2>" + title + "</h2>",
                      "<p><strong>" + text(example["dataset"]) + ": " + text(example["case_id"]) + "</strong><br>",
                      text(example["input_context"]["Anomaly Description"]) + "</p>",
                      "<p>The archived P and R inputs each contain " + text(example["evidence_count"]) +
                      " evidence units. This package contains the " + text(len(example["cited_evidence_excerpt"])) +
                      " units cited by at least one of the four outputs.</p>",
                      "<table><thead><tr><th>Retained trace (source to target)</th><th>Count</th><th>Error rate</th><th>P position</th><th>R position</th></tr></thead><tbody>"])
        for unit in figure_units(example):
            content = unit["content"]
            description = content["name"].rsplit("/", 1)[-1] + " (" + content["canonical_entity_id"] + " to " + content["target_entity_id"] + ")"
            parts.append("<tr>" + "".join(cell(value) for value in (
                description, content["count"], f'{content["numeric_summary"]["error_rate"]:.2f}',
                ", ".join(map(str, unit["P_positions"])), ", ".join(map(str, unit["R_positions"])))) + "</tr>")
        parts.append("</tbody></table><table><thead><tr><th>Call</th><th>Root verdict</th><th>Correctness</th><th>Self-reported confidence</th><th>Cited handles</th></tr></thead><tbody>")
        for condition in ("P", "P_prime", "R", "R_prime"):
            response = example["outputs"][condition]
            endpoint = example["endpoints"][condition[0]]
            parts.append("<tr>" + "".join(cell(value) for value in (
                condition, response["root_entity_id"] + " — " + endpoint["entity_name"] + " (" + endpoint["entity_type"] + ")",
                "C" if response["benchmark_correct"] else "W", response["confidence"], ", ".join(response["supporting_evidence_ids"]))) + "</tr>")
        parts.append("</tbody></table><p><strong>Resolved services:</strong> " +
                     " / ".join(text(", ".join(example["endpoints"][view]["service_names"])) + " (" +
                                text(", ".join(example["endpoints"][view]["service_ids"])) + ")" for view in ("P", "R")) + "</p>")
        parts.append("<details><summary>All four recorded explanations</summary>")
        for condition in CONDITIONS:
            parts.append("<h3>" + text(condition) + "</h3><p>" + text(example["outputs"][condition]["brief_justification"]) + "</p>")
        parts.append("</details><details><summary>All cited input units and their P/R positions</summary>")
        for unit in example["cited_evidence_excerpt"]:
            parts.append("<h3>" + text(", ".join(unit["P_evidence_ids"])) + " in P; " +
                         text(", ".join(unit["R_evidence_ids"])) + " in R</h3><pre>" +
                         text(json.dumps(unit["content"], ensure_ascii=False, indent=2)) + "</pre>")
        parts.append("</details></section>")
    parts.append("<p><small>The displayed scores are reproduced from archived evaluations. Accepted-answer sets and full telemetry are not included. "
                 "The excerpt hashes and citation-to-content mappings can be checked locally. Full-input preservation was checked in the archived analysis. "
                 "Dataset excerpts: AIOps Challenge 2025 Dataset © 2025 Dan Pei, CC BY-NC 4.0. "
                 "See the package's third-party notices for sources and modifications.</small></p></html>")
    (output_dir / "case_illustrations.html").write_text("\n".join(parts) + "\n", encoding="utf-8")


def verify_multi_accepted_cases():
    """Check the archived set cardinalities for the two correct-to-correct pairs."""
    metadata = load("data/multi_accepted_cases.json")
    source_hash = metadata["source_sha256"]
    assert len(source_hash) == 64 and all(c in "0123456789abcdef" for c in source_hash)
    sizes = {(r["dataset"], r["case_id"]): r["accepted_set_size"] for r in metadata["rows"]}
    assert len(sizes) == len(metadata["rows"]) == 2
    assert all(size == 3 for size in sizes.values())
    with (ROOT / "data/analysis_cases.csv").open(encoding="utf-8", newline="") as stream:
        rows = [r for r in csv.DictReader(stream) if r["model"] == "Mistral"]
    observations = []
    for row in rows:
        for left, right in (("P", "R"), ("P_prime", "R_prime")):
            if row[left] == row[right]:
                continue
            if row[left + "_correct"] == row[right + "_correct"] == "1":
                assert row[left + "_valid"] == row[right + "_valid"] == "1"
                key = (row["dataset"], row["case_id"])
                assert key in sizes
                # All four archived evaluations are correct for these incidents.
                assert all(row[c + "_correct"] == "1" for c in CONDITIONS)
                observations.append({"dataset": key[0], "case_id": key[1],
                                     "left": left, "right": right, "accepted_set_size": sizes[key]})
    assert len(observations) == 2
    assert {(r["dataset"], r["case_id"]) for r in observations} == set(sizes)
    return observations


def run(output_dir):
    rows = load("data/entity_relations.json")["rows"]
    assert len(rows) == 358
    assert len({(r["model"], r["dataset"], r["case_id"]) for r in rows}) == len(rows)
    assert Counter(r["model"] for r in rows) == {"Qwen": 118, "DeepSeek": 121, "Mistral": 119}
    for row in rows:
        verify_row(row)
    summary = summarize(rows)
    counts = Counter((r["model"], r["dataset"], r["correctness_pattern"],
                      r["endpoints"]["P"]["entity_type"], r["endpoints"]["R"]["entity_type"]) for r in rows)
    type_pairs = [dict(zip(("model", "dataset", "correctness_pattern", "P_type", "R_type", "n"), (*key, value)))
                  for key, value in sorted(counts.items())]
    expected = load("data/entity_expected.json")
    assert summary == expected["summary"]
    assert type_pairs == expected["type_pairs"]
    result = {"entity_rows": len(rows), "summary": summary, "type_pairs": type_pairs,
              "examples": verify_examples(rows),
              "multi_accepted_correct_to_correct": verify_multi_accepted_cases(), "checks_passed": True}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    render_examples(output_dir)
    (output_dir / "entity_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reproduced")
    args = parser.parse_args()
    outcome = run(args.output_dir)
    print(json.dumps({"entity_rows": outcome["entity_rows"], "checks_passed": outcome["checks_passed"]}))
