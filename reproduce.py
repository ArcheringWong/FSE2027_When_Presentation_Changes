"""Reproduce the review package offline from the distributed observations."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def verify_files():
    """Check release-file hashes, rejecting paths outside the package."""
    entries = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))["sha256"]
    if not entries:
        raise ValueError("Empty file manifest")
    for name, expected in entries.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"Missing or unsafe manifest entry: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Checksum mismatch: {name}")
    return {"status": "PASS", "files_checked": len(entries)}


def main():
    if not __debug__:
        raise RuntimeError("Run without -O: verification uses Python assertions.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "generated")
    args = parser.parse_args()
    output = args.output.resolve()
    # Keep generated reports from overwriting any distributed inputs or scripts.
    if output == ROOT or (output.is_relative_to(ROOT) and output.parts[len(ROOT.parts)] != "generated"):
        raise ValueError("Within this package, output must be under generated/.")
    integrity = verify_files()
    from verify_protocol import run as verify_protocol
    from analysis import recompute, entity_analysis, presentation

    protocol = verify_protocol()
    output.mkdir(parents=True, exist_ok=True)
    print("Package files and archived protocol records: PASS", flush=True)
    statistics = recompute.run(output)
    entities = entity_analysis.run(output)
    presentation.run(output)
    report = {
        "status": "PASS", "integrity": integrity, "protocol": protocol,
        "statistics": statistics,
        "entity_analysis": {"rows": entities["entity_rows"], "checks_passed": entities["checks_passed"],
                            "examples": entities["examples"]},
        "network_requests": 0,
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Results written to {output}")


if __name__ == "__main__":
    main()
