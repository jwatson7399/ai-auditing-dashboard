import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import delivery

TODAY = '2026-09-12'
REPO = 'owner/dashboard'
DATA = {'date': TODAY, 'status': 'partial', 'picks': {'coding': {'pick': 'M'}},
        'bench': {'coding': {'fetched': TODAY, 'stale': False, 'd': {'M': 50}},
                  'pdf': {'fetched': '2026-09-03', 'stale': True, 'd': {'M': 40}}}}
PR = {'state': 'open', 'draft': False, 'base': {'ref': 'main', 'repo': {'full_name': REPO}},
      'head': {'sha': 'reviewed-sha'}, 'changed_files': 1, 'labels': [{'name': 'commentary'}]}
PATH = f'inbox/commentary/{TODAY}.md'


class DeliveryTests(unittest.TestCase):
    def test_partial_with_real_refresh_is_ready(self):
        self.assertTrue(delivery.ready(DATA, TODAY))
        self.assertFalse(delivery.ready(DATA, '2026-09-13'))
        self.assertFalse(delivery.ready(None, TODAY))
        for status in ('blocked', 'error'):
            self.assertFalse(delivery.ready(dict(DATA, status=status), TODAY))
        old = copy.deepcopy(DATA)
        old['bench']['coding']['stale'] = True
        self.assertFalse(delivery.ready(old, TODAY))
        self.assertFalse(delivery.ready(dict(DATA, picks={}), TODAY))

    def test_eligibility_fails_closed(self):
        for files in ([], ['site/template.html'], [PATH, 'tools/rebuild.py'],
                      ['inbox/commentary/2026-09-12.md/extra']):
            self.assertEqual(delivery.merge_eligibility(PR, files, REPO), (False, False))
        for changes in ({'draft': True}, {'state': 'closed'}, {'labels': []}, {'changed_files': 2}):
            self.assertEqual(delivery.merge_eligibility(dict(PR, **changes), [PATH], REPO), (False, False))
        wrong_base = copy.deepcopy(PR); wrong_base['base']['ref'] = 'other'
        self.assertEqual(delivery.merge_eligibility(wrong_base, [PATH], REPO), (False, False))

    def test_commentary_dispatches_after_head_pinned_merge(self):
        with patch.object(delivery, 'gh', side_effect=[json.dumps(PR), json.dumps([[{'filename': PATH}]]), '', '']) as gh:
            delivery.merge_commentary(REPO, 7)
        self.assertEqual(gh.call_args_list[2].args, ('pr', 'merge', '7', '--repo', REPO,
                         '--squash', '--delete-branch', '--match-head-commit', 'reviewed-sha'))
        self.assertEqual(gh.call_args_list[3].args[:3], ('workflow', 'run', 'rebuild.yml'))

    def test_rename_from_protected_path_never_merges(self):
        entry = {'filename': PATH, 'previous_filename': 'tools/rebuild.py'}
        with patch.object(delivery, 'gh', side_effect=[json.dumps(PR), json.dumps([[entry]])]) as gh:
            delivery.merge_commentary(REPO, 7)
        self.assertEqual(gh.call_count, 2)

    def test_log_only_merges_without_dispatch(self):
        with patch.object(delivery, 'gh', side_effect=[json.dumps(PR),
                          json.dumps([[{'filename': 'log/runs-commentator.csv'}]]), '']) as gh:
            delivery.merge_commentary(REPO, 7)
        self.assertEqual(gh.call_count, 3)

    def test_repeated_event_after_merge_is_noop(self):
        with patch.object(delivery, 'gh', return_value=json.dumps(dict(PR, state='closed'))) as gh:
            delivery.merge_commentary(REPO, 7)
        self.assertEqual(gh.call_count, 1)

    def test_changed_head_or_merge_failure_never_dispatches(self):
        with patch.object(delivery, 'gh', side_effect=[json.dumps(PR), json.dumps([[{'filename': PATH}]]),
                          subprocess.CalledProcessError(1, 'gh')]) as gh:
            with self.assertRaises(subprocess.CalledProcessError):
                delivery.merge_commentary(REPO, 7)
        self.assertEqual(gh.call_count, 3)

    def test_remote_missing_and_api_failure_are_distinct(self):
        with patch.object(delivery, 'gh', return_value='[]'):
            self.assertIsNone(delivery.remote_data(REPO, TODAY))
        with patch.object(delivery, 'gh', side_effect=subprocess.CalledProcessError(1, 'gh')):
            with self.assertRaises(subprocess.CalledProcessError):
                delivery.ensure_data(REPO, 10, 1)

    def test_large_raw_snapshot_is_ready_without_dispatch(self):
        data = dict(DATA, diagnostic_text='x' * (1024 * 1024 + 1))
        raw = json.dumps(data)
        self.assertGreater(len(raw.encode()), 1024 * 1024)
        with patch.object(delivery, 'today_et', return_value=TODAY), \
             patch.object(delivery, 'gh', side_effect=[json.dumps([{'name': f'{TODAY}.json'}]), raw]) as gh:
            self.assertEqual(delivery.ensure_data(REPO, 10, 1), data)
        self.assertEqual(gh.call_count, 2)
        self.assertEqual(gh.call_args_list[1].args, ('api', '-H',
                         'Accept: application/vnd.github.raw+json',
                         f'repos/{REPO}/contents/data/{TODAY}.json?ref=main'))

    def test_raw_fetch_errors_never_dispatch_recovery(self):
        for error in (subprocess.CalledProcessError(1, 'gh', stderr='HTTP 403'),
                      subprocess.CalledProcessError(1, 'gh', stderr='HTTP 404'),
                      subprocess.TimeoutExpired('gh', 45)):
            with self.subTest(error=error), \
                 patch.object(delivery, 'today_et', return_value=TODAY), \
                 patch.object(delivery, 'gh', side_effect=[json.dumps([{'name': f'{TODAY}.json'}]), error]) as gh:
                with self.assertRaises(type(error)):
                    delivery.ensure_data(REPO, 10, 1)
                self.assertEqual(gh.call_count, 2)

    def test_invalid_raw_json_never_dispatches_recovery(self):
        with patch.object(delivery, 'today_et', return_value=TODAY), \
             patch.object(delivery, 'gh', side_effect=[json.dumps([{'name': f'{TODAY}.json'}]), '<html>error</html>']) as gh:
            with self.assertRaises(json.JSONDecodeError):
                delivery.ensure_data(REPO, 10, 1)
            self.assertEqual(gh.call_count, 2)

    @patch.object(delivery, 'today_et', return_value=TODAY)
    def test_ready_data_needs_no_dispatch(self, date):
        with patch.object(delivery, 'remote_data', return_value=DATA), patch.object(delivery, 'gh') as gh:
            self.assertEqual(delivery.ensure_data(REPO, 10, 1), DATA)
            gh.assert_not_called()

    @patch.object(delivery, 'today_et', return_value=TODAY)
    def test_missing_data_recovers_once_then_returns_main_snapshot(self, date):
        with patch.object(delivery, 'remote_data', side_effect=[None, DATA]), \
             patch.object(delivery, 'gh') as gh, patch.object(delivery.time, 'sleep'):
            self.assertEqual(delivery.ensure_data(REPO, 10, 1), DATA)
            gh.assert_called_once_with('workflow', 'run', 'rebuild.yml', '--repo', REPO,
                                       '--ref', 'main', '-f', 'ensure_daily=true')

    @patch.object(delivery, 'today_et', return_value=TODAY)
    def test_timeout_does_not_return_yesterday(self, date):
        with patch.object(delivery, 'remote_data', return_value=dict(DATA, date='2026-09-11')), \
             patch.object(delivery, 'gh') as gh, \
             patch.object(delivery.time, 'monotonic', side_effect=[0, 11]):
            with self.assertRaisesRegex(RuntimeError, 'do not write commentary from yesterday'):
                delivery.ensure_data(REPO, 10, 1)
            self.assertEqual(gh.call_count, 1)

    def test_midnight_aborts_recovery(self):
        with patch.object(delivery, 'today_et', side_effect=[TODAY, '2026-09-13']), \
             patch.object(delivery, 'remote_data', return_value=None), \
             patch.object(delivery, 'gh'), patch.object(delivery.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'ET date changed'):
                delivery.ensure_data(REPO, 10, 1)

    @patch.object(delivery, 'today_et', return_value=TODAY)
    def test_rebuild_plan_preserves_explicit_refresh_and_retries_missing_data(self, date):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'data').mkdir()
            self.assertTrue(delivery.plan_rebuild(root, 'schedule', False, False))
            for name in (f'{TODAY}.json', 'latest.json'):
                (root / 'data' / name).write_text(json.dumps(DATA))
            self.assertFalse(delivery.plan_rebuild(root, 'schedule', False, False))
            self.assertFalse(delivery.plan_rebuild(root, 'workflow_dispatch', True, False))
            self.assertTrue(delivery.plan_rebuild(root, 'workflow_dispatch', False, False))
            self.assertTrue(delivery.plan_rebuild(root, 'push', False, False))
            self.assertTrue(delivery.plan_rebuild(root, 'workflow_dispatch', True, True))
            (root / 'data' / 'latest.json').write_text(json.dumps(dict(DATA, date='2026-09-11')))
            self.assertTrue(delivery.plan_rebuild(root, 'schedule', False, False))


if __name__ == '__main__':
    unittest.main()
