"""Exercise public fetchers without credentials or production output."""
import argparse
import json
import tempfile
from public_sources import AA_URL, ARENA_URLS, fetch_public_table, parse_aa_table, parse_arena_table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default=None)
    args = ap.parse_args()
    output = args.output or tempfile.mkdtemp(prefix='auditor-source-check-')
    aa = fetch_public_table(AA_URL, output, 'aa-leaderboard', expand=True)
    parsed, errors = parse_aa_table(aa['rows'])
    if errors:
        raise RuntimeError(str(errors))
    result = {'aa_numeric_rows': {k: sum(r['value'] is not None for r in v) for k, v in parsed.items()}, 'output': output}
    for board in ('webdev', 'text'):
        arena = fetch_public_table(ARENA_URLS[board], output, 'arena-' + board)
        scores, excluded = parse_arena_table(arena, board)
        result[board] = {'scores': len(scores), 'excluded': excluded, 'source_updated': arena['source_updated']}
    print(json.dumps(result, indent=2))



if __name__ == '__main__':
    main()
