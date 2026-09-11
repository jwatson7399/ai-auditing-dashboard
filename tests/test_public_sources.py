import contextlib
import copy
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from public_sources import AA_COLUMNS, effort_key, parse_aa_table, parse_arena_table
import rebuild


def aa_rows():
    return [['Model', *AA_COLUMNS.values()]] + [
        [f'Model {i} (high)', '50%', '60%', '70%', '$0.10'] for i in range(20)]


class SourceTests(unittest.TestCase):
    def test_reordered_columns(self):
        rows = [list(reversed(r)) for r in aa_rows()]
        result, errors = parse_aa_table(rows)
        self.assertFalse(errors)
        self.assertEqual(result['nohalluc'][0]['value'], 70)
        self.assertEqual(result['cost'][0]['value'], .1)

    def test_zero_cost_is_preserved(self):
        rows = aa_rows(); rows[1][-1] = '$0.00'
        result, _ = parse_aa_table(rows)
        self.assertEqual(result['cost'][0]['value'], 0)

    def test_missing_is_not_zero(self):
        rows = aa_rows(); rows.append(['Missing', '--', '--', '--', '--'])
        result, _ = parse_aa_table(rows)
        self.assertIsNone(result['omni'][-1]['value'])

    def test_bad_column_does_not_destroy_other_columns(self):
        rows = aa_rows(); rows[1][3] = '101%'
        result, errors = parse_aa_table(rows)
        self.assertIn('nohalluc', errors)
        self.assertNotIn('nohalluc', result)
        self.assertIn('cost', result)

    def test_rejects_units_and_schema_change(self):
        rows = aa_rows(); rows[0][1] = 'GDPval-AA v2 Elo'
        result, errors = parse_aa_table(rows)
        self.assertIn('gdpval', errors)
        rows = aa_rows(); rows[2].pop()
        with self.assertRaises(ValueError): parse_aa_table(rows)

    def test_duplicate_models_rejected(self):
        rows = aa_rows(); rows.append(rows[1])
        with self.assertRaises(ValueError): parse_aa_table(rows)

    def test_small_table_rejected(self):
        with self.assertRaises(ValueError): parse_aa_table(aa_rows()[:4])

    def test_effort_is_not_collapsed(self):
        self.assertEqual(effort_key('Claude Fable 5.1 (max with fallback)'),
                         effort_key('Claude Fable 5.1 (Adaptive Reasoning, Max Effort, Default Fallback)'))
        self.assertNotEqual(effort_key('M (max, special harness)'), effort_key('M (max)'))
        self.assertNotEqual(effort_key('Grok 4.6 (high)'), effort_key('Grok 4.6 (xhigh)'))
        self.assertNotEqual(effort_key('Claude Fable 5.1 (max)'), effort_key('Claude Fable 5.1 (max with fallback)'))
        self.assertNotEqual(effort_key('Claude Fable 5 (with fallback)'), effort_key('Claude Fable 5 (max with fallback)'))

    def arena(self):
        return {'title': 'WebDev AI Leaderboard', 'rows': [['Model', 'Score', 'Votes']] + [
            [f'model-{i}', '1507\n+5/-5', '100'] for i in range(6)]}

    def test_arena_ci_and_estimates(self):
        payload = self.arena(); payload['rows'][1][1] = '1507\n+5/-5\nAutoEval'
        data, excluded = parse_arena_table(payload, 'webdev')
        self.assertEqual(len(data), 5); self.assertEqual(len(excluded), 1)
        self.assertEqual(data['model-1'], 1507)

    def test_arena_duplicate_labels_are_excluded(self):
        payload = self.arena()
        payload['rows'].append(['model-0', '1600', '50'])
        data, excluded = parse_arena_table(payload, 'webdev')
        self.assertNotIn('model-0', data)
        self.assertEqual(len(excluded), 2)

    def test_arena_wrong_board_and_range(self):
        p = self.arena(); p['title'] = 'Leaderboard Not Found'
        with self.assertRaises(ValueError): parse_arena_table(p, 'webdev')
        p = self.arena(); p['rows'][1][1] = '15075'
        with self.assertRaises(ValueError): parse_arena_table(p, 'webdev')

    def apply(self, parsed, rows, prev=None):
        bench = {}
        with contextlib.redirect_stdout(io.StringIO()):
            notes = rebuild.apply_public_aa(parsed, {}, rows, bench, prev, '2026-09-11')
        return bench, notes

    def test_best_effort_with_provenance(self):
        parsed = {'nohalluc': [{'name':'Grok 4.6 (high)', 'value':66, 'display':'66%'},
                              {'name':'Grok 4.6 (xhigh)', 'value':76, 'display':'76%'}]}
        bench, _ = self.apply(parsed, [])
        self.assertEqual(bench['nohalluc']['d']['Grok 4.6'], 76)
        self.assertEqual(bench['nohalluc']['settings']['Grok 4.6'], 'xhigh')
        self.assertEqual(bench['nohalluc']['records']['Grok 4.6']['display'], '76%')

    def test_missing_benchmark_model_keeps_old_date(self):
        prev = {'bench':{'omni':{'d':{'Absent':55}, 'src':'old source', 'fetched':'2026-09-03'}}}
        bench, notes = self.apply({'omni':[{'name':'New', 'value':30, 'display':'30%'}]}, [], prev)
        self.assertEqual(bench['omni']['d']['Absent'],55)
        self.assertEqual(rebuild.oldest_stale_date(bench['omni']), '2026-09-03')
        self.assertTrue(notes)

    def test_cost_failure_carries_exact_effort_only(self):
        old = {'model':'Grok 4.6','effort':'high','api_name':'Grok 4.6 (high)',
               'cost_per_task':1.86,'cost_fetched':'2026-09-10'}
        rows = [dict(old), {'model':'Grok 4.6','effort':'xhigh','api_name':'Grok 4.6 (xhigh)'}]
        _, _ = self.apply({}, rows, {'eff':{'rows':[old]}})
        self.assertTrue(rows[0]['cost_stale']); self.assertEqual(rows[0]['cost_fetched'],'2026-09-10')
        self.assertIsNone(rows[1]['cost_per_task'])

    def test_ambiguous_cost_join_is_not_used(self):
        rows = [{'model':'M','effort':'high','api_name':'M (high)'},
                {'model':'M','effort':'High Effort','api_name':'M (High Effort)'}]
        self.apply({'cost':[{'name':'M (high)','value':1,'display':'$1.00'}]}, rows)
        self.assertTrue(all(r['cost_per_task'] is None for r in rows))

    def test_shift_does_not_assert_regrading(self):
        old={'d':{str(i):10 for i in range(10)}}
        new={'name':'Test','d':{str(i):20 for i in range(10)}}
        self.assertIn('cause is unconfirmed', rebuild.uniform_shift(new,old)[0])




class RebuildIntegrationTests(unittest.TestCase):
    def test_success_then_same_day_outage_retains_values_and_dates(self):
        import datetime as dt
        import json
        import tempfile
        from unittest.mock import patch
        repo = Path(__file__).resolve().parents[1]
        baseline = json.loads((repo / 'data/latest.json').read_text())
        today = (dt.date.fromisoformat(baseline['date']) + dt.timedelta(days=1)).isoformat()
        api = {k: {'d': copy.deepcopy(b['d']), 'settings': {}} for k, b in baseline['bench'].items()
               if k in ('terminal', 'scicode', 'tau', 'lcr')}
        effort = [{'model':'Grok 4.6', 'effort':'high', 'api_name':'Grok 4.6 (high)',
                   'score':44, 'access':'grok'}]
        rows = aa_rows(); rows[1] = ['Grok 4.6 (high)', '50%', '60%', '70%', '$1.23']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root/'data').mkdir(); (root/'site').mkdir()
            (root/'data/latest.json').write_text(json.dumps(baseline))
            (root/'data'/f"{baseline['date']}.json").write_text(json.dumps(baseline))
            (root/'site/template.html').write_text((repo/'site/template.html').read_text())
            def run(fail):
                with contextlib.redirect_stdout(io.StringIO()), patch.object(rebuild,'ROOT',folder), \
                     patch.object(rebuild,'fetch_aa_llms',side_effect=lambda key: (copy.deepcopy(api),copy.deepcopy(effort),{'fields':{},'index':'fixture'},{})), \
                     patch.object(rebuild,'fetch_public_table',return_value={'rows':rows},side_effect=RuntimeError('outage') if fail else None), \
                     patch.object(rebuild,'fetch_arena',side_effect=lambda board: (baseline['bench'][board]['d'],{})), \
                     patch.object(rebuild,'fetch_aa_media',side_effect=lambda key,kind: baseline['bench']['image' if kind=='text-to-image' else 'video']['d']), \
                     patch.object(rebuild,'pending_prs',return_value=[]), patch.object(rebuild,'write_xlsx'), \
                     patch.object(sys,'argv',['rebuild.py','--date',today,'--no-log']):
                    self.assertEqual(rebuild.main(),0)
                return json.loads((root/'data/latest.json').read_text())
            success = run(False)
            self.assertEqual(success['bench']['nohalluc']['d']['Grok 4.6'],70)
            self.assertFalse(success['eff']['rows'][0]['cost_stale'])
            failure = run(True)
            self.assertEqual(failure['bench']['nohalluc']['d']['Grok 4.6'],70)
            self.assertTrue(failure['bench']['nohalluc']['records']['Grok 4.6']['stale'])
            self.assertEqual(failure['bench']['nohalluc']['records']['Grok 4.6']['fetched'],today)
            self.assertTrue(failure['eff']['rows'][0]['cost_stale'])
            self.assertEqual(failure['eff']['rows'][0]['cost_fetched'],today)
            self.assertFalse((root/'log/runs-rebuild.csv').exists())


if __name__ == '__main__': unittest.main()
