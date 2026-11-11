"""Exercise public fetchers without credentials or production output."""
import argparse
import json
import tempfile
from public_sources import AA_URL, ARENA_URLS, fetch_public_table, load_arena, parse_aa_table, parse_arena_table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default=None)
    args = ap.parse_args()
    output = args.output or tempfile.mkdtemp(prefix='auditor-source-check-')
    aa = fetch_public_table(AA_URL, output, 'aa-leaderboard', expand=True)
    parsed, errors = parse_aa_table(aa['rows'])
    if errors:
        raise RuntimeError(str(errors))
    columns = {}
    for key, values in parsed.items():
        columns[key] = {'field': values[0].get('field'), 'scale': values[0].get('scale'),
                        'numeric_rows': sum(r['value'] is not None for r in values)}
        example = next((r for r in values if r.get('raw_elo') is not None), None)
        if example:
            columns[key]['example_raw_elo'] = example['raw_elo']
            columns[key]['example_percent'] = example['value']
    result = {'aa_numeric_rows': {k: v['numeric_rows'] for k, v in columns.items()},
              'aa_columns': columns, 'output': output}
    for board in ('webdev', 'text'):
        arena = load_arena(board, output)
        scores, excluded = parse_arena_table(arena, board)
        result[board] = {'scores': len(scores), 'excluded': excluded, 'source_updated': arena['source_updated']}
    print(json.dumps(result, indent=2))



if __name__ == '__main__':
    main()
