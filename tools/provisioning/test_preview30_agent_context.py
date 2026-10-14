"""Actual Data Agent serialization is distinct from native context readiness."""
import base64
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data-agent'))
from measured_contract_profile import ONTOLOGY_SCHEMA
from preview30_agent import build_profile
from preview30_deploy import agent_definition_contract
from preview30_runtime import SafetyError


def fixture(stage='draft', native=True):
    workspace='11111111-1111-4111-8111-111111111111'
    kinds={'lakehouse_tables':'lakehouse','kusto':'kqlDatabase','ontology':'ontology','semantic_model':'semanticModel'}
    docs={f'Files/Config/{stage}/stage_config.json':{'experimental':{'codeInterpreterEnabled':True}}}
    items={}
    for index,(kind,key) in enumerate(kinds.items(),2):
        item={'id':str(index)*8+'-'+str(index)*4+'-4'+str(index)*3+'-8'+str(index)*3+'-'+str(index)*12,
              'displayName':'Owned_'+key}
        items[key]=item
        source={'workspaceId':workspace,'artifactId':item['id'],'displayName':item['displayName'],
                'type':kind,'elements':[{'id':'source-entity','is_selected':True}]}
        path=f'Files/Config/{stage}/{kind}/datasource.json'
        if kind=='ontology' and native:
            source.pop('type');source['$schema']=ONTOLOGY_SCHEMA
            source['entitiesWithUserAuthoredDescriptions']=[]
            path=f'Files/Config/{stage}/ontologies/{item["displayName"]}/ontology.json'
        docs[path]=source
    definition={'parts':[{'path':path,'payloadType':'InlineBase64',
        'payload':base64.b64encode(json.dumps(value).encode()).decode()} for path,value in docs.items()]}
    deployment=SimpleNamespace(scope={'workspaceId':workspace},state={'items':items})
    return deployment,definition


class DataAgentContextTests(unittest.TestCase):
    def test_both_stages_accept_actual_migration_without_readiness_claim(self):
        for stage in ['draft','published']:
            for native in [False,True]:
                d,definition=fixture(stage,native)
                before=copy.deepcopy(definition)
                result=agent_definition_contract(d,definition,stage)
                self.assertEqual(definition,before)
                self.assertEqual(result['logicalSourceCount'],4)
                self.assertEqual(result['physicalDatasourceCount'],3 if native else 4)
                self.assertEqual(result['ontologyCount'],1)
                self.assertFalse(result['nativeOntologyContextChecked'])
                self.assertIsNone(result['nativeOntologyContextReady'])

    def test_all_logical_bindings_are_checked_not_only_model(self):
        for key in ['lakehouse','kqlDatabase','ontology','semanticModel']:
            for field in ['id','displayName']:
                d,definition=fixture()
                d.state['items'][key][field]='different'
                with self.subTest(key=key,field=field),self.assertRaises(SafetyError):
                    agent_definition_contract(d,definition,'draft')
        d,definition=fixture();d.scope['workspaceId']='foreign'
        with self.assertRaises(SafetyError):agent_definition_contract(d,definition,'draft')

    def test_unknown_native_context_or_disabled_interpreter_fails(self):
        for mutation in ['context','interpreter','mixed']:
            d,definition=fixture()
            for part in definition['parts']:
                value=json.loads(base64.b64decode(part['payload']))
                if mutation=='context' and part['path'].endswith('/ontology.json'):
                    value['userDescription']='Not an observed field'
                if mutation=='interpreter' and part['path'].endswith('/stage_config.json'):
                    value['experimental']['codeInterpreterEnabled']=False
                part['payload']=base64.b64encode(json.dumps(value).encode()).decode()
            if mutation=='mixed':
                _,legacy=fixture(native=False)
                definition['parts'].append(next(p for p in legacy['parts'] if '/ontology/' in p['path']))
            with self.subTest(mutation=mutation),self.assertRaises(SafetyError):
                agent_definition_contract(d,definition,'draft')

    def test_create_bootstrap_is_explicit_and_does_not_promote_context_availability(self):
        files,contract=build_profile()
        self.assertEqual(contract['definitionInputSerialization'],'legacy-datasource-bootstrap')
        self.assertTrue(contract['serviceMayMigrateOntologyToSeparateContext'])
        self.assertFalse(contract['nativeOntologyContextAvailabilityVerified'])
        self.assertFalse(contract['accuracyAccepted'])
        self.assertEqual(len([p for p in files if p.endswith('/datasource.json')]),4)
