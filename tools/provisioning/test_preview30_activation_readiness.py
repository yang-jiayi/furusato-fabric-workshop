"""Regression checks for actual native readiness, credentials and upload exclusion."""
from __future__ import annotations
import base64
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import preview30_activation as activation
from preview30_activation_readiness import capture_readiness, check_responses, approved_origin
from preview30_deploy import normalize_stopped_reflex
from preview30_runtime import SafetyError, BASE

W='11111111-1111-4111-8111-111111111111'
A='22222222-2222-4222-8222-222222222222'
RULE='33333333-3333-4333-8333-333333333333'
ACTION='44444444-4444-4444-8444-444444444444'
PIPE='55555555-5555-4555-8555-555555555555'
CAP='66666666-6666-4666-8666-666666666666'
HOST='wabi-test-primary-redirect.analysis.windows.net'
SECRET='DO-NOT-PERSIST-TEST-MWC-CREDENTIAL'
STATE={'timeSeriesViewState':{'type':'rule','backendRunningState':'Running','isRuleInSync':True,
                            'ruleDelayToleranceInMs':120000,'watermarkType':'DelayTolerance'}}
HEALTH={'rules':[{'ruleId':RULE,'notifications':[]}]}
ACTION_STATE={'fabricItemAction':[{'system':{'refreshToken':{'state':'Initialized','_id':'document-id'}}}]}


def encoded(entities):
    return {'parts':[{'path':'ReflexEntities.json','payloadType':'InlineBase64',
                      'payload':base64.b64encode(json.dumps(entities).encode()).decode()}]}


def decoded(definition):
    return json.loads(base64.b64decode(definition['parts'][0]['payload']))


class Reply:
    status_code=200
    def __init__(self,value,status=200):self.value=value;self.status_code=status
    def json(self):return copy.deepcopy(self.value)


class Session:
    def __init__(self,bodies):
        self.bodies=copy.deepcopy(bodies);self.calls=[];self.verify='/explicit/ca.pem'
        self.proxies={'https':'http://explicit-proxy:8080'};self.trust_env=False
    def request(self,method,url,**kwargs):
        self.calls.append((method,url,kwargs));return Reply(self.bodies.pop(0))


def deployment(path,bodies=None):
    definition=encoded([
        {'uniqueIdentifier':RULE,'payload':{'definition':{'type':'Rule','instance':'{}',
            'settings':{'shouldRun':True,'shouldApplyRuleOnUpdate':False,'delayToleranceMs':120000}}}},
        {'type':'fabricItemAction-v1','uniqueIdentifier':ACTION,
         'payload':{'fabricItem':{'workspaceId':W,'itemId':PIPE}}}])
    session=Session(bodies or [{'clusterUrl':'https://'+HOST},
        {'Token':SECRET,'TargetUriHost':HOST,'CapacityObjectId':CAP},STATE,HEALTH,{'data':ACTION_STATE}])
    client=SimpleNamespace(session=session,
        credential=SimpleNamespace(get_token=lambda scope:SimpleNamespace(token='AAD-CREDENTIAL')),
        request=lambda *args,**kwargs:Reply({'id':W,'displayName':'Workshop','capacityId':CAP}))
    return SimpleNamespace(scope={'workspaceId':W,'workspaceName':'Workshop'},evidence=path,
        prefix='/workspaces/'+W,client=client,definition=lambda *args,**kwargs:copy.deepcopy(definition),
        state={'scopeSha256':'scope-sha','nativeLifecycle':{'action':'start','status':'verified',
            'timestampUtc':'2026-01-01T00:00:00Z','result':{'state':'armed_unverified'}},
            'items':{'pipeline':{'id':PIPE}}})


class ReadinessChecks(unittest.TestCase):
    def test_null_or_changed_response_shapes_block(self):
        for state,health,action in ((None,HEALTH,ACTION_STATE),
                ({'timeSeriesViewState':None},HEALTH,ACTION_STATE),
                (STATE,{'rules':[None]},ACTION_STATE),
                (STATE,HEALTH,{'fabricItemAction':[None]}),
                (STATE,HEALTH,{'fabricItemAction':[{'system':None}]}),
                (STATE,HEALTH,{'fabricItemAction':[{'system':{'refreshToken':None}}]})):
            with self.subTest(state=state,health=health,action=action),self.assertRaises(SafetyError):
                check_responses(state,health,action,RULE,120000)
    def test_actual_runtime_required_not_only_running_setting(self):
        for field,value in [('backendRunningState','Starting'),('isRuleInSync',False),
                            ('ruleDelayToleranceInMs',0),('watermarkType','Unknown')]:
            bad=copy.deepcopy(STATE);bad['timeSeriesViewState'][field]=value
            with self.subTest(field=field),self.assertRaises(SafetyError):
                check_responses(bad,HEALTH,ACTION_STATE,RULE,120000)
    def test_missing_foreign_or_unhealthy_rule_is_not_ready(self):
        for health in ({},{'rules':[]},{'rules':[{'ruleId':A,'notifications':[]}]},
                       {'rules':[{'ruleId':RULE,'notifications':[{'severity':'Warning'}]}]}):
            with self.subTest(health=health),self.assertRaises(SafetyError):
                check_responses(STATE,health,ACTION_STATE,RULE,120000)
    def test_missing_credentials_block(self):
        for state in ({},{'fabricItemAction':[]},{'fabricItemAction':[{'system':{'refreshToken':{'state':'Uninitialized'}}}]}):
            with self.subTest(state=state),self.assertRaises(SafetyError):
                check_responses(STATE,HEALTH,state,RULE,120000)
    def test_capture_reuses_transport_and_never_saves_credentials(self):
        with TemporaryDirectory() as t:
            d=deployment(Path(t));result=capture_readiness(d,{'id':A},RULE)
            self.assertTrue(result['isRuleInSync']);self.assertFalse(result['automaticDeliveryVerified'])
            self.assertEqual(d.client.session.verify,'/explicit/ca.pem')
            self.assertEqual(d.client.session.proxies,{'https':'http://explicit-proxy:8080'})
            self.assertFalse(d.client.session.trust_env)
            self.assertEqual(len(d.client.session.calls),5)
            self.assertTrue(all(c[2]['allow_redirects'] is False for c in d.client.session.calls))
            for p in Path(t).rglob('*.json'):
                self.assertNotIn(SECRET,p.read_text());self.assertNotIn('AAD-CREDENTIAL',p.read_text())
            self.assertFalse(any(c[0] in {'PUT','DELETE','PATCH'} for c in d.client.session.calls))
    def test_capacity_mismatch_aborts_before_native_read(self):
        with TemporaryDirectory() as t:
            d=deployment(Path(t));d.client.session.bodies[1]['CapacityObjectId']=W
            with self.assertRaises(SafetyError):capture_readiness(d,{'id':A},RULE)
            self.assertEqual(len(d.client.session.calls),2)
    def test_formal_start_receipt_required_before_native_requests(self):
        for receipt in ({}, {'action':'stop','status':'verified'},
                        {'action':'start','status':'pending'},
                        {'action':'start','status':'verified','result':{'state':'running'}}):
            with TemporaryDirectory() as t:
                d=deployment(Path(t));d.state['nativeLifecycle']=receipt
                with self.subTest(receipt=receipt),self.assertRaises(SafetyError):capture_readiness(d,{'id':A},RULE)
                self.assertEqual(d.client.session.calls,[])
    def test_failed_token_response_is_not_persisted(self):
        with TemporaryDirectory() as t:
            d=deployment(Path(t));d.client.session.bodies[1]['errors']=[SECRET]
            with self.assertRaises(SafetyError):capture_readiness(d,{'id':A},RULE)
            self.assertEqual(len(d.client.session.calls),2)
            for p in Path(t).rglob('*.json'):
                self.assertNotIn(SECRET,p.read_text());self.assertNotIn('AAD-CREDENTIAL',p.read_text())
    def test_untrusted_routing_does_not_receive_credential(self):
        with TemporaryDirectory() as t:
            d=deployment(Path(t));d.client.session.bodies[0]['clusterUrl']='https://example.com'
            with self.assertRaises(SafetyError):capture_readiness(d,{'id':A},RULE)
            self.assertEqual(len(d.client.session.calls),1)
    def test_invalid_origins_are_rejected(self):
        for origin in ('http://'+HOST, 'https://'+HOST+'.example.com',
                       'https://user:pass@'+HOST, 'https://'+HOST+'/path',
                       'https://'+HOST+'?token=hidden', 'https://'+HOST+'#fragment'):
            with self.subTest(origin=origin),self.assertRaises(SafetyError):approved_origin(origin)
    def test_tls_bypass_blocks_before_authentication(self):
        with TemporaryDirectory() as t:
            d=deployment(Path(t));d.client.session.verify=False
            with self.assertRaises(SafetyError):capture_readiness(d,{'id':A},RULE)
            self.assertEqual(d.client.session.calls,[])
    def test_changed_definition_blocks_after_capture(self):
        with TemporaryDirectory() as t:
            d=deployment(Path(t));initial=d.definition();different=copy.deepcopy(initial);different['changed']=True
            with patch.object(d,'definition',side_effect=[initial,different]),self.assertRaises(SafetyError):
                capture_readiness(d,{'id':A},RULE)
    def test_bad_readiness_prevents_upload_intent(self):
        with TemporaryDirectory() as t:
            d=deployment(Path(t));d.checkpoint=lambda:self.fail('Upload intent was written')
            d.client.paged=lambda *a,**k:[]
            d.client.request=lambda *a,**k:Reply({'properties':{'oneLakeFilesPath':'unused'}})
            d.state['items']['lakehouse']={'id':A}
            with patch.object(activation,'Deployment',return_value=d),patch.object(activation,'_targets',return_value=({'id':A},RULE)),patch('preview30_activation_readiness.capture_readiness',side_effect=SafetyError('backend Starting')):
                with self.assertRaises(SafetyError):activation.deliver_increment(SimpleNamespace(increment=1))
            self.assertEqual(d.state['incrementDeliveries'],{})
            self.assertFalse(list(Path(t).rglob('upload-intent.json')))


class RenderedToleranceChecks(unittest.TestCase):
    def setUp(self):
        self.entities=json.loads((BASE/'provisioning/bundle/reflex/ReflexEntities.json').read_text())
        self.original=encoded(self.entities)
    def test_only_rendered_setting_changes_and_source_bytes_survive(self):
        raw=copy.deepcopy(self.original);result=normalize_stopped_reflex(raw)
        self.assertEqual(raw,self.original)
        expected=copy.deepcopy(self.entities)
        rule=next(e for e in expected if e.get('payload',{}).get('definition',{}).get('type')=='Rule')
        rule['payload']['definition']['settings']['delayToleranceMs']=120000
        self.assertEqual(decoded(result),expected)
        self.assertEqual(normalize_stopped_reflex(result),result)
    def test_running_or_historical_replay_source_rejected(self):
        for key in ('shouldRun','shouldApplyRuleOnUpdate'):
            entities=copy.deepcopy(self.entities)
            rule=next(e for e in entities if e.get('payload',{}).get('definition',{}).get('type')=='Rule')
            rule['payload']['definition']['settings'][key]=True
            with self.subTest(key=key),self.assertRaises(SafetyError):normalize_stopped_reflex(encoded(entities))


if __name__=='__main__':unittest.main()
