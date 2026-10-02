"""Render manuscript-numbered tables and two SVG figures from recomputed results."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ('Qwen', 'DeepSeek', 'Mistral')
DATASETS = ('RCA100', 'AIOps2025')
CONDITIONS = ('P', 'R', 'P_prime', 'R_prime')
LABELS = {'P': 'P', 'R': 'R', 'P_prime': "P'", 'R_prime': "R'"}


def fixed(value):
    return f'{value:.4f}'


def interval(row, key='estimate'):
    return f"{fixed(row[key])} [{fixed(row['ci95'][0])}, {fixed(row['ci95'][1])}]"


def count_percent(value, total):
    return f'{value} ({100 * value / total:.1f}%)'


def table(number, title, columns, rows, note=''):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = [f'## Table {number}. {title}', '',
             '| ' + ' | '.join(map(cell, columns)) + ' |',
             '| ' + ' | '.join('---' for _ in columns) + ' |']
    lines.extend('| ' + ' | '.join(map(cell, row)) + ' |' for row in rows)
    if note:
        lines.extend(['', note])
    return '\n'.join(lines)


def tables(statistics, entities, protocol):
    models = statistics['models']
    blocks = ['# Recomputed manuscript tables',
              'Table numbers follow the submitted manuscript. Values below come from the local recomputation. '
              'Layout is adapted for review in a browser. C/W denotes benchmark-correct/wrong; '
              "P' and R' are exact-input repeats of P and R. Intervals are 95% percentile bootstrap intervals."]
    config_rows = [(r['model'], r['requested_model'], r['collection'],
                    'third-configuration replication' if r['model'] == 'Mistral' else 'original confirmation')
                   for r in protocol['models']]
    gen = protocol['generation']
    blocks.append(table(1, 'Fixed configurations and four-condition timing',
        ['Configuration', 'Exact requested model', "P/R/P'/R' collection", 'Study role'], config_rows,
        f"Shared decoding: temperature {gen['temperature']}, top-p {gen['top_p']}, request seed {gen['seed']}, "
        f"output limit {gen['max_tokens']} tokens. Tools and streaming are disabled."))
    blocks.append(table(2, 'Repeat-adjusted neutral-order disagreement',
        ['Configuration', 'Complete n', 'RCA100 estimate [CI]', 'AIOps2025 estimate [CI]',
         'Equal-dataset macro [CI]', 'INVALID-inclusive macro'],
        [(m, models[m]['core']['complete_valid']['macro']['n'],
          interval(models[m]['core']['complete_valid']['RCA100']), interval(models[m]['core']['complete_valid']['AIOps2025']),
          interval(models[m]['core']['complete_valid']['macro']), fixed(models[m]['core']['invalid_inclusive']['macro']['estimate']))
         for m in MODELS],
        'The final column uses all 359 order-applicable incidents per configuration and encodes schema-invalid responses as INVALID.'))
    blocks.append(table(3, 'Post-hoc exhaustive four-response decomposition',
        ['Configuration', 'All four same', 'Repeat-stable, cross-view different', 'Any within-view change'],
        [(m, *(count_percent(models[m]['joint']['Pooled'][k], models[m]['joint']['Pooled']['complete_quadruples'])
                for k in ('all_four_same', 'repeat_stable_cross_view_different', 'any_within_view_repeat_change'))) for m in MODELS],
        "Within-view change means P != P' or R != R'. Counts use the complete-valid cohort."))
    blocks.append(table(4, 'Joint correctness with agreement within each view and disagreement across views',
        ['Configuration', 'n', 'P:C / R:W', 'P:W / R:C', 'Both wrong', 'Both correct'],
        [(m, *(models[m]['joint']['Pooled'][k] for k in ('repeat_stable_cross_view_different', 'P_correct_R_wrong',
                  'P_wrong_R_correct', 'both_wrong', 'both_correct'))) for m in MODELS],
        "Each row is restricted to P = P', R = R', and P != R. Units are unique model-incident observations."))
    blocks.append(table(5, 'Pooled complete-valid component rates',
        ['Configuration', 'A: P != R', "B: P' != R'", "C: P != P'", "D: R != R'"],
        [(m, *(fixed(models[m]['core']['complete_valid']['pooled_components'][k]) for k in 'ABCD')) for m in MODELS],
        'These pool incidents within configuration; the primary estimand instead gives each dataset equal weight.'))
    blocks.append(table(6, 'Post-hoc incident-pooled persistence',
        ['Configuration', 'Complete n', 'Recurrence', 'Emergence', 'Gap [CI]', 'Jaccard', 'Timing'],
        [(m, models[m]['persistence']['pooled']['n'], fixed(models[m]['persistence']['pooled']['recurrence']),
          fixed(models[m]['persistence']['pooled']['emergence']), interval(models[m]['persistence']['pooled'], 'gap'),
          fixed(models[m]['persistence']['pooled']['jaccard']), 'same wave' if m == 'Mistral' else 'cross-period') for m in MODELS],
        'Recurrence = Pr(B=1 | A=1), emergence = Pr(B=1 | A=0), and gap = recurrence - emergence.'))
    blocks.append(table(7, 'Post-hoc equal-dataset persistence sensitivity',
        ['Configuration', 'RCA100 recurrence / emergence / gap', 'AIOps2025 recurrence / emergence / gap',
         'Macro recurrence', 'Macro emergence', 'Macro gap [CI]'],
        [(m, *(' / '.join(fixed(models[m]['persistence']['datasets'][d][k]) for k in ('recurrence', 'emergence', 'gap'))
                for d in DATASETS), fixed(models[m]['persistence']['macro']['recurrence']),
          fixed(models[m]['persistence']['macro']['emergence']), interval(models[m]['persistence']['macro'], 'gap')) for m in MODELS]))
    def accuracy_cell(row):
        return f"{row['correct']}/{row['n']} ({fixed(row['accuracy'])})"
    blocks.append(table(8, 'Mistral condition accuracy', ['Condition', 'Overall', *DATASETS],
        [(LABELS[c], *(accuracy_cell(models['Mistral']['accuracy'][d][c]) for d in ('Pooled', *DATASETS))) for c in CONDITIONS]))
    blocks.append(table(9, 'Post-hoc verdict consequences for all four comparisons',
        ['Configuration', 'Pair', 'Changed', 'C to W', 'W to C', 'W to W', 'C to C'],
        [(m, pair, *(models[m]['transitions']['Pooled'][pair][k] for k in ('changed_verdict', 'correct_to_wrong',
              'wrong_to_correct', 'wrong_to_wrong', 'correct_to_correct')))
         for m in MODELS for pair in ('P/R', "P'/R'", "P/P'", "R/R'")],
        'Changed means different verdict values (candidate ID or UNKNOWN), not necessarily a correctness change.'))
    joint_rows = []
    for m in MODELS:
        for d in DATASETS:
            j = models[m]['joint'][d]
            k, n = j['repeat_stable_cross_view_different'], j['both_within_view_repeats_agree']
            joint_rows.append((m, d, j['complete_quadruples'], n, f'{k}/{n} ({100*k/n:.1f}%)',
                               j['correctness_exchange_unique_incidents'], j['both_wrong']))
    blocks.append(table(10, 'Dataset-specific joint observations',
        ['Configuration', 'Dataset', 'Complete n', 'Both repeats agree', 'Different / agree', 'C/W', 'W/W'], joint_rows,
        'C/W combines the two directions of correctness exchange; W/W counts two different wrong verdicts in the repeat-stable subset.'))
    entity_rows = []
    for m in MODELS:
        e = next(r for r in entities['summary'] if r['model'] == m and r['dataset'] == 'ALL' and r['correctness_pattern'] == 'ALL')
        assert e['type_missing'] == e['service_ambiguous'] == 0
        entity_rows.append((m, e['n'], e['type_same_type'], e['type_different_type'], e['service_same_service'],
                            e['service_different_service'], e['service_missing'], e['service_not_applicable'], e['service_unknown_verdict']))
    blocks.append(table(11, 'Entity relations within repeat-consistent cross-view differences',
        ['Configuration', 'n', 'Same type', 'Different type', 'Same service', 'Different service', 'Service missing', 'Service N/A', 'UNKNOWN'],
        entity_rows, 'Type and service are separate classifications. N/A includes a host/node endpoint; missing denotes an unresolved explicit service mapping.'))
    boundary_rows = []
    for condition, title in (('serialization', 'Serialization'), ('temporal_origin', 'Temporal origin'),
                             ('topology_serialization', 'Topology serialization')):
        for m in MODELS[:2]:
            b = statistics['boundary'][m][condition]
            counts = b['dataset_counts']
            boundary_rows.append((title, m, f"{b['complete_triple_count']} ({counts.get('RCA100', '--')}/{counts.get('AIOps2025', '--')})", interval(b)))
    blocks.append(table(12, 'Single-reference repeat-adjusted boundary estimates',
        ['Transformation', 'Configuration', 'Complete n (RCA100/AIOps2025)', 'Estimate [CI]'], boundary_rows,
        'The boundary estimator uses transformed-versus-reference disagreement minus exact-repeat-versus-reference disagreement. Mistral was not evaluated under these conditions.'))
    return '\n\n'.join(blocks) + '\n'


def svg_start(width, height, title, description):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#17232d}.muted{fill:#52606c}.grid{stroke:#dce2e6;stroke-width:1}</style>',
            f'<rect width="{width}" height="{height}" fill="white"/>']


def text(x, y, value, size=16, extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def core_forest(statistics):
    parts = svg_start(1100, 610, 'Repeat-adjusted neutral-order disagreement',
        'Nine estimates with 95 percent bootstrap intervals: RCA100, AIOps2025 and equal-dataset macro for each model. The dashed vertical line is zero.')
    parts.append(text(30, 35, 'Repeat-adjusted neutral-order disagreement', 23))
    parts.append(text(30, 62, 'Complete-valid cohorts; 95% incident-bootstrap intervals', 15, 'class="muted"'))
    left, right, top, bottom = 285, 825, 91, 511
    xpos = lambda value: left + value / .6 * (right - left)
    for tick in range(7):
        x = xpos(tick / 10)
        dash = ' stroke-dasharray="5,5"' if tick == 0 else ''
        parts.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bottom}" class="grid"{dash}/>')
        parts.append(text(x, 541, f'{tick / 10:.1f}', 14, 'text-anchor="middle"'))
    colors = {'Qwen':'#27628f', 'DeepSeek':'#8b5932', 'Mistral':'#3d7660'}
    for group, model in enumerate(MODELS):
        for row, scope in enumerate((*DATASETS, 'macro')):
            y = 112 + group * 142 + row * 42
            result = statistics['models'][model]['core']['complete_valid'][scope]
            low, high = result['ci95']
            center = result['estimate']
            assert 0 <= low <= center <= high <= .6
            parts.append(text(30, y + 5, model if row == 0 else '', 17, 'font-weight="bold"'))
            parts.append(text(141, y + 5, 'Equal-dataset' if scope == 'macro' else scope, 15))
            color = colors[model]
            parts.append(f'<line data-ci="{model}-{scope}" x1="{xpos(low):.3f}" y1="{y}" x2="{xpos(high):.3f}" y2="{y}" stroke="{color}" stroke-width="3"/>')
            for value in (low, high):
                parts.append(f'<line x1="{xpos(value):.3f}" y1="{y-5}" x2="{xpos(value):.3f}" y2="{y+5}" stroke="{color}" stroke-width="2"/>')
            if scope == 'macro':
                parts.append(f'<rect x="{xpos(center)-5:.3f}" y="{y-5}" width="10" height="10" fill="{color}"/>')
            else:
                parts.append(f'<circle cx="{xpos(center):.3f}" cy="{y}" r="5" fill="{color}"/>')
            parts.append(text(854, y + 5, interval(result), 15))
    parts.extend([text((left + right) / 2, 574, 'Repeat-adjusted difference (proportion)', 16, 'text-anchor="middle"'), '</svg>'])
    return '\n'.join(parts) + '\n'


def design_protocol():
    parts = svg_start(940, 600, 'Per-incident two-view, two-call protocol',
        'P and R are diagnosis-equivalent neutral presentations; P-prime repeats P and R-prime repeats R. A and B compare views; C and D compare exact-input calls.')
    parts.extend([text(34, 40, 'Per-incident protocol', 24),
                  text(34, 70, 'Selected typed evidence multiset preserved across the two neutral views', 16, 'class="muted"'),
                  text(250, 117, 'View P', 18, 'text-anchor="middle"'), text(690, 117, 'View R', 18, 'text-anchor="middle"')])
    for x, y, call, line1, line2 in [(130,145,'P','Primary neutral order','First call'),
                                   (570,145,'R','Reserve neutral order','First call'),
                                   (130,345,"P'",'Byte-identical P input','Exact repeat'),
                                   (570,345,"R'",'Byte-identical R input','Exact repeat')]:
        parts.append(f'<rect x="{x}" y="{y}" width="240" height="110" rx="8" fill="#f3f6f8" stroke="#aebdc7"/>')
        parts.extend([text(x+120,y+35,call,26,'text-anchor="middle" font-weight="bold"'),
                      text(x+120,y+64,line1,15,'text-anchor="middle"'),
                      text(x+120,y+88,line2,14,'text-anchor="middle" class="muted"')])
    for y, label in ((200, 'A: P != R'), (400, "B: P' != R'")):
        parts.append(f'<line x1="382" y1="{y}" x2="558" y2="{y}" stroke="#27628f" stroke-width="3"/>')
        parts.append(text(470,y-14,label,17,'text-anchor="middle"'))
        parts.append(text(470,y+24,'Cross-view',14,'text-anchor="middle" class="muted"'))
    for x, label in ((250,"C: P != P'"),(690,"D: R != R'")):
        parts.append(f'<line x1="{x}" y1="263" x2="{x}" y2="337" stroke="#647d71" stroke-width="3"/>')
        parts.append(f'<rect x="{x-92}" y="280" width="184" height="34" fill="white"/>')
        parts.append(text(x,302,label,17,'text-anchor="middle"'))
    parts.extend([text(470,503,'Per-incident contrast: (A + B - C - D) / 2',20,'text-anchor="middle" font-weight="bold"'),
                  text(470,534,'Compute each dataset mean, then average the two datasets equally.',16,'text-anchor="middle"'),
                  text(470,568,'Qwen / DeepSeek: pairs and repeats across periods. Mistral: all four calls interleaved in one wave.',14,
                       'text-anchor="middle" class="muted"'), '</svg>'])
    return '\n'.join(parts) + '\n'


def run(output_dir):
    output_dir = Path(output_dir)
    statistics = json.loads((output_dir / 'statistical_results.json').read_text(encoding='utf-8'))
    entities = json.loads((output_dir / 'entity_results.json').read_text(encoding='utf-8'))
    protocol = json.loads((ROOT / 'protocol/configurations.json').read_text(encoding='utf-8'))
    rendered_tables = tables(statistics, entities, protocol)
    assert rendered_tables.count('\n## Table ') == 12
    (output_dir / 'tables.md').write_text(rendered_tables, encoding='utf-8')
    (output_dir / 'core_forest.svg').write_text(core_forest(statistics), encoding='utf-8')
    (output_dir / 'design_protocol.svg').write_text(design_protocol(), encoding='utf-8')
    return {'table_count': 12, 'forest_intervals': 9,
            'outputs': ['tables.md', 'core_forest.svg', 'design_protocol.svg']}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reproduced')
    print(json.dumps(run(parser.parse_args().output_dir), indent=2))
