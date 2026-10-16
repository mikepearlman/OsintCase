import importlib.util, json, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('bridge',Path(__file__).with_name('server.py'))
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)

class BridgeTests(unittest.TestCase):
    def test_shortlist_integrity(self):
        data=bridge.make_case()
        nodes={n['id'] for n in data['identifiers']}
        evidence={e['id'] for e in data['evidence']}
        self.assertTrue(nodes)
        self.assertEqual(len(nodes),len(data['identifiers']))
        for edge in data['connections']:
            self.assertIn(edge['source'],nodes);self.assertIn(edge['target'],nodes)
        for event in data['events']:
            self.assertTrue(set(event['evidenceIds']) <= evidence)
        with bridge.phone.connect() as c:
            expected={r[0] for r in c.execute('SELECT DISTINCT audio_id FROM audio_leads')}
        actual={n['sourceRecordId'] for n in data['identifiers'] if n.get('sourceRecordId') in expected}
        self.assertEqual(actual,expected)
        self.assertTrue(all(e['dataUrl'] is None for e in data['evidence']))
    def test_stable_ids_and_empty_selection(self):
        a=bridge.make_case();b=bridge.make_case()
        self.assertEqual([n['id'] for n in a['identifiers']],[n['id'] for n in b['identifiers']])
        self.assertEqual(bridge.make_case([])['identifiers'],[])
    def test_full_export_count_and_no_credentials(self):
        data=bridge.make_case(full=True)
        with bridge.phone.connect() as c:total=c.execute('SELECT count(*) FROM records').fetchone()[0]
        self.assertEqual(len(data['evidence']),total)
        self.assertNotIn('openrouter_key',json.dumps(data))
        self.assertNotIn('.secrets.json',json.dumps(data))

if __name__=='__main__':unittest.main()
