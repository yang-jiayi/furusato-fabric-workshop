"""Offline tests for the read-only Data Agent service check; no network."""

from __future__ import annotations

from pathlib import Path
import copy
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_service_check as asc


def fake_service():
    elements = {
        None: [{"id": "root", "displayName": "LH", "type": "Lakehouse", "hasSubElements": True}],
        "root": [{"id": "dbo", "displayName": "dbo", "type": "Schema", "hasSubElements": True}],
        "dbo": [
            {"id": "views", "displayName": "Views", "type": "ViewGrouping", "hasSubElements": True},
            {"id": "t1", "displayName": "ot_donation", "type": "Table", "isSelected": False},
        ],
        "views": [{"id": "v1", "displayName": "agent_view", "type": "View", "state": "Available",
                   "isSelected": True, "hasSubElements": True}],
        "v1": [{"id": "c1", "displayName": "A", "isSelected": True},
               {"id": "c2", "displayName": "B", "isSelected": False}],
    }
    fewshots = [
        {"id": "1", "validationStatus": {"value": "Valid"}},
        {"id": "2", "validationStatus": {"value": "Invalid", "reason":
            "Failed to connect to server abc-def.datawarehouse.fabric.microsoft.com "
            "for 12345678-1234-1234-1234-123456789abc"}},
    ]

    def get(path):
        if path.endswith("/datasources"):
            return {"value": [{"id": "ds", "type": "LakehouseTables", "displayName": "LH"}]}
        if "/fewshots" in path:
            return {"value": fewshots}
        root = path.split("rootId=")[1] if "rootId=" in path else None
        return {"value": elements[root]}

    return get


class AgentServiceCheckTests(unittest.TestCase):
    def test_summary_reports_validation_and_views_without_hosts_or_ids(self):
        summary, raw = asc.check(fake_service(), "ws", "agent", "published",
                                 {"agent_view": {"A", "B"}})
        source = summary["datasources"][0]
        self.assertEqual(source["examples"]["status"], {"Invalid": 1, "Valid": 1})
        reason = source["examples"]["nonValidReasons"][0]["reason"]
        self.assertIn("<host>", reason)
        self.assertIn("<id>", reason)
        self.assertNotIn("datawarehouse", reason)
        view = source["views"]["agent_view"]
        self.assertEqual((view["state"], view["selected"], view["columnsSelected"]), ("Available", True, 1))
        self.assertEqual(view["unselectedColumns"], ["B"])
        self.assertTrue(view["matchesInformationSchema"])
        self.assertEqual(source["selectedTables"], [])
        self.assertEqual(len(raw["datasource-0"]["elements"]), 7)

    def test_column_mismatch_is_reported(self):
        summary, _ = asc.check(fake_service(), "ws", "agent", "staging", {"agent_view": {"A"}})
        self.assertFalse(summary["datasources"][0]["views"]["agent_view"]["matchesInformationSchema"])

    def test_multi_label_service_hosts_are_fully_redacted(self):
        text = asc.redact("connect https://trd-6a1b2c3d4e5f6g7h8i.z9.kusto.fabric.microsoft.com/x failed")
        self.assertNotIn("trd-", text)
        self.assertIn("https://<host>/x", text)

class NativeOntologyContextTests(unittest.TestCase):
    W = '11111111-1111-4111-8111-111111111111'
    A = '22222222-2222-4222-8222-222222222222'
    O = '33333333-3333-4333-8333-333333333333'
    C = '44444444-4444-4444-8444-444444444444'

    def native_fixture(self, failed=False):
        row = {'id': self.O, 'displayName': 'Ontology', 'state': 'SchemaUnavailable' if failed else 'Available',
               'ontologyReference': {'referenceType': 'ById', 'itemId': self.O, 'workspaceId': self.W}}
        calls = []
        def get(path):
            calls.append(path)
            if path.endswith('/ontologies'):
                return {'httpStatus': 200, 'body': {'value': [row]}}
            if path.endswith('/' + self.O):
                # Actual individual registration GET has identity fields only.
                return {'httpStatus': 200, 'body': {k: v for k, v in row.items() if k != 'state'}}
            if path.endswith('/contextmarkdown'):
                return {'httpStatus': 200, 'body': '' if failed else 'Actual source context'}
            if failed:
                return {'httpStatus': 502, 'body': {'error': "Required root definition.json is missing"}}
            body = ({'documents': [{'content': 'actual context'}]} if path.endswith('/configuration') else
                    {'value': [{'id': 'actual-entity'}]} if path.endswith('/elements') else
                    {'value': [{'type': 'Lakehouse', 'state': 'Available', 'itemReference': {
                        'referenceType': 'ById', 'itemId': self.C, 'workspaceId': self.W}}]})
            return {'httpStatus': 200, 'body': body}
        return get, calls

    def test_public_stages_match_sdk_root_published_and_staging_routes(self):
        # SDK get_published_datasources/elements/fewshots use the Agent root.
        for stage in ('published', 'staging'):
            calls=[]; source=fake_service()
            def get(path): calls.append(path); return source(path)
            summary,_=asc.check(get,self.W,self.A,stage,None)
            base=f'/v1/workspaces/{self.W}/dataAgents/{self.A}'
            expected=base+('/staging' if stage=='staging' else '')+'/datasources'
            with self.subTest(stage=stage):
                self.assertEqual(calls[0],expected)
                self.assertTrue(all(path.startswith(expected) for path in calls))
                self.assertTrue(any('/fewshots' in path for path in calls))
                self.assertTrue(any('/elements' in path for path in calls))
                self.assertTrue(all('/published/' not in path for path in calls))
                if stage=='published':
                    self.assertTrue(all('/staging/' not in path for path in calls))
                self.assertIsNone(summary['ontologyContext']['ready'])
                self.assertFalse(summary['answerAccuracyVerified'])

    def test_failed_native_context_retains_error_and_is_not_missing_ontology(self):
        get,calls=self.native_fixture(failed=True)
        summary,raw=asc.ontology_context_check(get,self.W,self.A,'published')
        self.assertEqual(summary['registeredCount'],1); self.assertFalse(summary['ready'])
        self.assertEqual(len(calls),6); self.assertTrue(all('/staging/' not in path for path in calls))
        self.assertEqual(raw['registrations'][0]['probes']['configuration']['httpStatus'],502)
        self.assertIn('definition.json',raw['registrations'][0]['probes']['configuration']['body']['error'])

    def test_actual_nonempty_context_required_beyond_collection(self):
        get,calls=self.native_fixture()
        summary,_=asc.ontology_context_check(get,self.W,self.A,'staging')
        self.assertTrue(summary['ready']); self.assertFalse(summary['answerAccuracyVerified'])
        self.assertTrue(all('/staging/' in path for path in calls))
        for missing in ['configuration','elements','ontologydatasources','contextmarkdown']:
            def incomplete(path):
                return {'httpStatus':200,'body':'' if missing=='contextmarkdown' else {}} if path.endswith('/'+missing) else get(path)
            summary,_=asc.ontology_context_check(incomplete,self.W,self.A,'staging')
            self.assertFalse(summary['ready'])

    def test_collection_state_is_required_but_individual_state_is_optional(self):
        # Availability comes from the collection; an explicitly contradictory
        # individual state must still fail, even with all context probes healthy.
        for collection_state, individual_state, expected in [
                ('Available', None, True),
                ('Available', 'SchemaUnavailable', False),
                ('SchemaUnavailable', None, False)]:
            native, _ = self.native_fixture()
            def get(path):
                record = copy.deepcopy(native(path))
                if path.endswith('/ontologies'):
                    record['body']['value'][0]['state'] = collection_state
                elif path.endswith('/' + self.O) and individual_state is not None:
                    record['body']['state'] = individual_state
                return record
            with self.subTest(collection=collection_state, individual=individual_state):
                summary, raw = asc.ontology_context_check(get, self.W, self.A, 'published')
                self.assertIs(summary['ready'], expected)
                registration = raw['registrations'][0]['probes']['registration']['body']
                if individual_state is None:
                    self.assertNotIn('state', registration)
                self.assertFalse(summary['answerAccuracyVerified'])

    def test_foreign_registration_is_retained_but_not_followed(self):
        get,calls=self.native_fixture()
        def foreign(path):
            record=get(path)
            if path.endswith('/ontologies'):
                record['body']['value'][0]['ontologyReference']['workspaceId']=self.C
            return record
        summary,raw=asc.ontology_context_check(foreign,self.W,self.A,'staging')
        self.assertEqual(len(calls),1);self.assertFalse(summary['ready'])
        self.assertEqual(summary['registeredCount'],1)

    def test_stale_registration_incomplete_elements_or_invalid_derived_source_do_not_qualify(self):
        mutations = {
            'registration_state': ('/' + self.O, lambda body: body.update(state='SchemaUnavailable')),
            'empty_element': ('/elements', lambda body: body.update(value=[{}])),
            'bad_item_id': ('/ontologydatasources', lambda body: body['value'][0]['itemReference'].update(itemId='not-an-item-id')),
            'element_pagination': ('/elements', lambda body: body.update(continuationToken='unread-page')),
            'derived_pagination': ('/ontologydatasources', lambda body: body.update(continuationToken='unread-page')),
        }
        for name, (suffix, mutate) in mutations.items():
            native, _ = self.native_fixture()
            def get(path):
                record = copy.deepcopy(native(path))
                if path.endswith(suffix):
                    mutate(record['body'])
                return record
            with self.subTest(mutation=name):
                summary, raw = asc.ontology_context_check(get, self.W, self.A, 'published')
                self.assertFalse(summary['ready'])
                self.assertEqual(len(raw['registrations']), 1)

    def test_native_origin_rejects_redirect_or_arbitrary_host(self):
        origin='https://'+self.C.replace('-','')+'.pbidedicated.windows.net'
        self.assertTrue(asc.native_base(origin,self.C,self.W).startswith(origin+'/webapi/'))
        for bad in ['https://example.com',origin+'?next=bad',origin+'/extra',origin.replace('https:','http:'),origin+':443']:
            with self.assertRaises(asc.EvaluationError):asc.native_base(bad,self.C,self.W)


if __name__ == "__main__":
    unittest.main()
