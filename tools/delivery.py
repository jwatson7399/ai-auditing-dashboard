"""Commentary merge eligibility and bounded recovery of today's data on main.

No production fetch runs here: authenticated fetching remains in Actions.
"""
import argparse
import base64
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
COMMENTARY = re.compile(r'inbox/commentary/\d{4}-\d{2}-\d{2}\.md\Z')


def today_et():
    return dt.datetime.now(ET).date().isoformat()


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True, timeout=45)


def ready(data, today):
    """A partial refresh is usable; yesterday or an all-carried snapshot is not."""
    if not isinstance(data, dict) or data.get('date') != today:
        return False
    if data.get('status') not in ('ok', 'partial') or not data.get('picks'):
        return False
    return any(b.get('fetched') == today and not b.get('stale') and b.get('d')
               for b in data.get('bench', {}).values())


def merge_eligibility(pr, files, repo):
    if (pr['state'] != 'open' or pr['draft'] or pr['base']['ref'] != 'main'
            or pr['base']['repo']['full_name'] != repo
            or 'commentary' not in [label['name'] for label in pr['labels']]):
        return False, False
    allowed = bool(files) and len(files) == pr['changed_files'] and all(
        COMMENTARY.fullmatch(f) or f == 'log/runs-commentator.csv' for f in files)
    return allowed, allowed and any(COMMENTARY.fullmatch(f) for f in files)


def merge_commentary(repo, number):
    # The workflow serializes all events for this PR. Read live state after that
    # lock, not the stale opened/labeled/synchronize event payload.
    pr = json.loads(gh('api', f'repos/{repo}/pulls/{number}'))
    if pr['state'] != 'open':
        print('PR is no longer open; no merge or dispatch.')
        return
    pages = json.loads(gh('api', '--paginate', '--slurp',
                         f'repos/{repo}/pulls/{number}/files?per_page=100'))
    entries = [f for page in pages for f in page]
    # A rename out of a protected path also deletes that original file.
    if any(f.get('previous_filename') and not (COMMENTARY.fullmatch(f['previous_filename'])
               or f['previous_filename'] == 'log/runs-commentator.csv') for f in entries):
        print('Rename touches a path outside commentary; leave for review.')
        return
    files = [f['filename'] for f in entries]
    allowed, publish = merge_eligibility(pr, files, repo)
    if not allowed:
        print('Not eligible for commentary auto-merge; leave for review.')
        return
    gh('pr', 'merge', str(number), '--repo', repo, '--squash',
       '--delete-branch', '--match-head-commit', pr['head']['sha'])
    if publish:
        # GITHUB_TOKEN merges do not trigger the push workflow. A failure here
        # fails this job visibly; use a manual rebuild to recover after merge.
        gh('workflow', 'run', 'rebuild.yml', '--repo', repo, '--ref', 'main')
        print('Commentary merged and rebuild dispatched.')
    else:
        print('Run log merged; no commentary changed, so no rebuild dispatched.')


def remote_data(repo, today):
    # Fetch the directory listing so a missing date is distinct from an auth,
    # network, or API error. Errors must not cause a speculative dispatch.
    entries = json.loads(gh('api', f'repos/{repo}/contents/data?ref=main'))
    if f'{today}.json' not in [entry['name'] for entry in entries]:
        return None
    blob = json.loads(gh('api', f'repos/{repo}/contents/data/{today}.json?ref=main'))
    return json.loads(base64.b64decode(blob['content']))


def ensure_data(repo, timeout, interval):
    today = today_et()
    data = remote_data(repo, today)
    if ready(data, today):
        return data
    # Each caller dispatches at most once. Concurrent callers are handled by
    # the rebuild workflow's lock and its post-checkout ensure_daily guard.
    gh('workflow', 'run', 'rebuild.yml', '--repo', repo, '--ref', 'main',
       '-f', 'ensure_daily=true')
    print(f'Requested today\'s data for {today}; waiting up to {timeout}s.', file=sys.stderr)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
        if today_et() != today:
            raise RuntimeError('ET date changed while waiting; restart for the new day')
        data = remote_data(repo, today)
        if ready(data, today):
            return data
    raise RuntimeError(f'No usable {today} data on main after {timeout}s; '
                       'do not write commentary from yesterday. Inspect Daily rebuild runs.')


def plan_rebuild(root, event, ensure_daily, no_fetch):
    today = today_et()
    snapshot = None
    try:
        snapshot = json.loads((root / 'data' / f'{today}.json').read_text())
        latest = json.loads((root / 'data' / 'latest.json').read_text())
    except (OSError, ValueError):
        latest = None
    # Explicit manual refreshes and commentary pushes still rebuild. Recovery
    # requests and a delayed daily schedule can reuse today's committed refresh.
    skip = (not no_fetch and (event == 'schedule' or ensure_daily)
            and ready(snapshot, today) and snapshot == latest)
    return not skip


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    merge = sub.add_parser('merge-commentary')
    merge.add_argument('--repo', required=True)
    merge.add_argument('--pr', required=True, type=int)
    ensure = sub.add_parser('ensure-data')
    ensure.add_argument('--repo', default='jwatson7399/ai-auditing-dashboard')
    ensure.add_argument('--timeout', type=int, default=600)
    ensure.add_argument('--interval', type=int, default=15)
    plan = sub.add_parser('plan-rebuild')
    plan.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    if args.command == 'merge-commentary':
        merge_commentary(args.repo, args.pr)
    elif args.command == 'ensure-data':
        if args.timeout <= 0 or args.interval <= 0:
            ap.error('timeout and interval must be positive')
        print(json.dumps(ensure_data(args.repo, args.timeout, args.interval), ensure_ascii=False))
    else:
        run = plan_rebuild(args.root, os.getenv('GITHUB_EVENT_NAME'),
                           os.getenv('ENSURE_DAILY') == 'true', os.getenv('NO_FETCH') == 'true')
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(f'run={str(run).lower()}\n')
        print('Refresh required.' if run else 'Today already has usable data; skip duplicate refresh.')


if __name__ == '__main__':
    main()
