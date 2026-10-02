"""Recompute results from archived event-level observations, without network access.

Inputs are observations, not table summaries. Expected values are read only after
the analyses finish, for regression checks. Correctness flags are archived labels;
this module does not resolve gold labels again.
"""
from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("P", "R", "P_prime", "R_prime")
MODELS = ("Qwen", "DeepSeek", "Mistral")
DATASETS = ("RCA100", "AIOps2025")
PAIRS = (("P/R", "P", "R"), ("P'/R'", "P_prime", "R_prime"),
         ("P/P'", "P", "P_prime"), ("R/R'", "R", "R_prime"))
REPS = 10_000


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ci(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return np.percentile(values, [2.5, 97.5]).tolist() if len(values) else [None, None]


def load_cases():
    rows = read_csv(ROOT / "data/analysis_cases.csv")
    assert len({(r['model'], r['dataset'], r['case_id']) for r in rows}) == len(rows)
    for row in rows:
        scores = {}
        for c in CONDITIONS:
            assert row[c + '_valid'] in ('0', '1')
            row[c + '_valid'] = row[c + '_valid'] == '1'
            value = row[c + '_correct']
            assert value in ('', '0', '1')
            row[c + '_correct'] = None if value == '' else value == '1'
            row[c + '_confidence'] = float(row[c + '_confidence']) if row[c + '_confidence'] else None
            assert row[c] and (row[c] != 'INVALID') == row[c + '_valid']
            if row[c] in ('UNKNOWN', 'INVALID'):
                assert row[c + '_correct'] is not True
            if row[c + '_correct'] is not None:
                assert row[c] not in scores or scores[row[c]] == row[c + '_correct']
                scores[row[c]] = row[c + '_correct']
        row['complete_valid'] = all(row[c + '_valid'] for c in CONDITIONS)
        if row['complete_valid']:
            assert all(row[c + '_correct'] is not None for c in CONDITIONS)
    return rows


def python_indexes(sizes, seed, order=DATASETS):
    """Preserve the original Python RNG, stratum order and interleaved draws."""
    rng = random.Random(seed)
    indexes = {d: np.empty((REPS, sizes[d]), dtype=np.int32) for d in order}
    for b in range(REPS):
        for d in order:
            indexes[d][b] = [rng.randrange(sizes[d]) for _ in range(sizes[d])]
    return indexes


def components(rows):
    # Columns A/B are cross-view differences; C/D are exact-input repeats.
    return np.asarray([[r['P'] != r['R'], r['P_prime'] != r['R_prime'],
                        r['P'] != r['P_prime'], r['R'] != r['R_prime']] for r in rows], dtype=float)


def core(rows, indexes):
    estimates, draws = {}, {}
    for d in DATASETS:
        part = [r for r in rows if r['dataset'] == d]
        v = components(part)
        scores = (v[:, 0] + v[:, 1] - v[:, 2] - v[:, 3]) / 2
        draws[d] = scores[indexes[d]].mean(axis=1)
        estimates[d] = {'n': len(part), 'estimate': float(scores.mean()), 'ci95': ci(draws[d]),
                        'components': dict(zip(('A', 'B', 'C', 'D'), v.mean(axis=0).tolist()))}
    estimates['macro'] = {'n': len(rows), 'estimate': sum(estimates[d]['estimate'] for d in DATASETS) / 2,
                          'ci95': ci((draws[DATASETS[0]] + draws[DATASETS[1]]) / 2)}
    estimates['pooled_components'] = dict(zip(('A', 'B', 'C', 'D'), components(rows).mean(axis=0).tolist()))
    return estimates


def persistence_point(v):
    h, f = v[:, 0], v[:, 1]
    counts = {f'n{a}{b}': int(((h == a) & (f == b)).sum()) for a in (0, 1) for b in (0, 1)}
    rec, em = float(f[h == 1].mean()), float(f[h == 0].mean())
    return {'n': len(v), **counts, 'recurrence': rec, 'emergence': em,
            'gap': rec - em, 'jaccard': counts['n11'] / int(((h == 1) | (f == 1)).sum())}


def persistence_draws(v, indexes):
    h, f = v[indexes, 0], v[indexes, 1]
    both, emerged = (h * f).sum(axis=1), ((1 - h) * f).sum(axis=1)
    hs = h.sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        gaps = both / hs - emerged / (h.shape[1] - hs)
    return gaps, both, emerged, hs


def persistence(rows, indexes):
    points, sampled = {}, {}
    for d in DATASETS:
        v = components([r for r in rows if r['dataset'] == d])[:, :2]
        points[d] = persistence_point(v)
        sampled[d] = persistence_draws(v, indexes[d])
    h = sum(sampled[d][3] for d in DATASETS)
    both = sum(sampled[d][1] for d in DATASETS)
    emerged = sum(sampled[d][2] for d in DATASETS)
    with np.errstate(divide='ignore', invalid='ignore'):
        pooled = both / h - emerged / (len(rows) - h)
    return {'pooled': {**persistence_point(components(rows)[:, :2]), 'ci95': ci(pooled)},
            'macro': {key: sum(points[d][key] for d in DATASETS) / 2
                      for key in ('recurrence', 'emergence', 'gap')} | {
                          'ci95': ci(sum(sampled[d][0] for d in DATASETS) / 2)},
            'datasets': points}


def characterize(rows):
    joint, accuracy, transitions = {}, {}, {}
    for dataset in (*DATASETS, 'Pooled'):
        part = [r for r in rows if dataset == 'Pooled' or r['dataset'] == dataset]
        same = [r for r in part if len({r[c] for c in CONDITIONS}) == 1]
        stable = [r for r in part if r['P'] == r['P_prime'] and r['R'] == r['R_prime']]
        diff = [r for r in stable if r['P'] != r['R']]
        status = Counter()
        for r in diff:
            p, q = r['P_correct'], r['R_correct']
            status['both_correct' if p and q else 'P_correct_R_wrong' if p else
                   'P_wrong_R_correct' if q else 'both_wrong'] += 1
        k, n = len(diff), len(part)
        exchange = status['P_correct_R_wrong'] + status['P_wrong_R_correct']
        joint[dataset] = {'complete_quadruples': n, 'all_four_same': len(same),
                          'both_within_view_repeats_agree': len(stable),
                          'repeat_stable_cross_view_different': k,
                          'any_within_view_repeat_change': n - len(stable),
                          **{key: status[key] for key in ('both_correct', 'P_correct_R_wrong', 'P_wrong_R_correct', 'both_wrong')},
                          'correctness_exchange_unique_incidents': exchange,
                          'involving_unknown': sum('UNKNOWN' in (r['P'], r['R']) for r in diff),
                          'cross_view_different_rate_full_cohort': k / n,
                          'cross_view_different_rate_given_both_repeats_agree': k / len(stable),
                          'correctness_exchange_rate_full_cohort': exchange / n,
                          'correctness_exchange_rate_repeat_stable_different': exchange / k}
        accuracy[dataset] = {c: {'n': n, 'correct': sum(r[c + '_correct'] for r in part),
                                  'accuracy': sum(r[c + '_correct'] for r in part) / n,
                                  'unknown_count': sum(r[c] == 'UNKNOWN' for r in part)} for c in CONDITIONS}
        transitions[dataset] = {}
        for name, a, b in PAIRS:
            changed = [r for r in part if r[a] != r[b]]
            counts = Counter(('correct' if r[a + '_correct'] else 'wrong') + '_to_' +
                             ('correct' if r[b + '_correct'] else 'wrong') for r in changed)
            transitions[dataset][name] = {'complete_quadruples': n, 'same_verdict': n - len(changed),
                'changed_verdict': len(changed),
                **{k: counts[k] for k in ('correct_to_wrong', 'wrong_to_correct', 'wrong_to_wrong', 'correct_to_correct')},
                'correctness_state_change': counts['correct_to_wrong'] + counts['wrong_to_correct'],
                'entity_to_unknown': sum(r[b] == 'UNKNOWN' for r in changed),
                'unknown_to_entity': sum(r[a] == 'UNKNOWN' for r in changed),
                'entity_to_entity': sum('UNKNOWN' not in (r[a], r[b]) for r in changed)}
    return {'joint': joint, 'accuracy': accuracy, 'transitions': transitions}


def confidence(rows):
    changed = [(r, a, b) for _, a, b in PAIRS[:2] for r in rows if r[a] != r[b]]
    assert all(r[a + '_confidence'] is not None and r[b + '_confidence'] is not None for r, a, b in changed)
    high = sum(r[a + '_confidence'] >= .8 and r[b + '_confidence'] >= .8 for r, a, b in changed)
    return {'changed_cross_view_pairs': len(changed), 'both_confidences_at_least_0_8': high,
            'rate': high / len(changed)}


def boundary():
    records = read_csv(ROOT / 'data/analysis_boundary.csv')
    result = {}
    for model in MODELS[:2]:
        result[model] = {}
        for condition in ('serialization', 'temporal_origin', 'topology_serialization'):
            part = [r for r in records if r['model'] == model and r['condition'] == condition]
            datasets = sorted({r['dataset'] for r in part})
            sizes = {d: sum(r['dataset'] == d for r in part) for d in datasets}
            indexes = python_indexes(sizes, 20260905, datasets)
            estimates, draws = {}, {}
            for d in datasets:
                selected = [r for r in part if r['dataset'] == d]
                values = np.array([int(r['transformation'] != r['baseline']) - int(r['identity_repeat'] != r['baseline']) for r in selected])
                estimates[d] = float(values.mean())
                draws[d] = values[indexes[d]].mean(axis=1)
            result[model][condition] = {'complete_triple_count': len(part), 'dataset_counts': sizes,
                'estimate': sum(estimates.values()) / len(datasets),
                'ci95': ci(sum(draws.values()) / len(datasets)), 'dataset_estimates': estimates}
    return result


def topology_distance(rows):
    """Summarize archived distances; graph shortest paths are not rebuilt here."""
    records = read_csv(ROOT / 'data/analysis_topology_distances.csv')
    lookup = {(r['model'], r['dataset'], r['case_id']): r for r in rows}
    for record in records:
        row = lookup[(record['model'], record['dataset'], record['case_id'])]
        a, b = ('P', 'R') if record['period'] == 'historical' else ('P_prime', 'R_prime')
        assert row[a] == record['left_verdict'] and row[b] == record['right_verdict']
        assert row[a] != row[b] and row[a + '_correct'] is False and row[b + '_correct'] is False
    def describe(selected):
        values = np.array([float(r['topology_hops']) for r in selected if r['topology_hops'] != ''])
        return {'n': len(values), 'mean': float(values.mean()), 'median': float(np.median(values)),
                'min': float(values.min()), 'max': float(values.max()),
                'q1': float(np.percentile(values, 25)), 'q3': float(np.percentile(values, 75)),
                'more_than_one_hop': int((values > 1).sum())}
    return {'overall': describe(records), 'by_model_period': {
        model: {period: describe([r for r in records if r['model'] == model and r['period'] == period])
                for period in ('historical', 'fresh')} for model in MODELS[:2]}}


def assert_expected(actual, expected, path='results'):
    """Compare the independently recomputed result with archived reference fields."""
    checks = 0
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert key in actual, f'Missing {path}.{key}'
            checks += assert_expected(actual[key], value, f'{path}.{key}')
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for i, value in enumerate(expected):
            checks += assert_expected(actual[i], value, f'{path}[{i}]')
    elif isinstance(expected, (int, float)):
        assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10), f'{path}: {actual} != {expected}'
        checks += 1
    else:
        assert actual == expected, f'{path}: {actual} != {expected}'
        checks += 1
    return checks


def run(output_dir):
    rows = load_cases()
    result = {'models': {}, 'boundary': {}}
    with np.load(ROOT / 'data/analysis_mistral_bootstrap_indexes.npz') as saved:
        assert saved['seed'].tolist() == [20260905]
        mistral_idx = {d: saved[d].copy() for d in DATASETS}
    for model in MODELS:
        full = [r for r in rows if r['model'] == model]
        valid = [r for r in full if r['complete_valid']]
        assert len(full) == 359 and {r['dataset'] for r in full} == set(DATASETS)
        full_sizes = {d: sum(r['dataset'] == d for r in full) for d in DATASETS}
        valid_sizes = {d: sum(r['dataset'] == d for r in valid) for d in DATASETS}
        if model == 'Mistral':
            full_idx = valid_idx = p_idx = mistral_idx
            # Freeze-index alignment is the original dataset-filtered case order.
            assert all(mistral_idx[d].shape == (REPS, valid_sizes[d]) for d in DATASETS)
        else:
            valid_idx = python_indexes(valid_sizes, 20260905)
            full_idx = python_indexes(full_sizes, 20260905)
            p_idx = python_indexes(valid_sizes, 20260906)
        result['models'][model] = {'core': {'complete_valid': core(valid, valid_idx),
                                           'invalid_inclusive': core(full, full_idx)},
                                    'persistence': persistence(valid, p_idx), **characterize(valid)}
        if model == 'Mistral':
            result['models'][model]['confidence'] = confidence(valid)
    result['boundary'] = boundary()
    result['topology_distance'] = topology_distance(rows)
    expected = json.loads((ROOT / 'data/analysis_expected.json').read_text(encoding='utf-8'))
    checks = assert_expected(result, expected)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'statistical_results.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    summary = {'status': 'PASS', 'checked_reference_values': checks, 'model_incident_rows': len(rows),
               'complete_valid_by_model': {m: result['models'][m]['core']['complete_valid']['macro']['n'] for m in MODELS},
               'bootstrap_resamples': REPS, 'network_requests': 0}
    (output_dir / 'statistical_verification.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'generated')
    print(json.dumps(run(parser.parse_args().output), indent=2))
