"""Native workload HTTP contract tests: no tokens acquired and no network used."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_evaluation import EvaluationError, encode
from native_responses_http import (
    API_VERSION, DEFAULT_MODEL, NativeEvidenceError, PBI_SCOPE, ResponsesHttpClient,
    diagnostics_feature_unavailable, runtime_config,
)


def config():
    return {
        "workspace_id": str(UUID(int=1)), "data_agent_id": str(UUID(int=2)),
        "capacity_id": str(UUID(int=3)), "stage": "production",
        "workload_host": "https://wabi-offline-fixture.analysis.windows.net/",
    }


class FakeCredential:
    def __init__(self):
        self.scopes = []

    def get_token(self, scope):
        self.scopes.append(scope)
        return SimpleNamespace(token="offline-placeholder")


class FakeResponse:
    def __init__(self, body, status, request_body):
        self.content, self.status_code = body, status
        self.request = SimpleNamespace(body=request_body)
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True


class FakeSession:
    def __init__(self):
        self.calls = []
        self.body = b'{"id":"offline-conversation"}'
        self.status = 200
        self.responses = []
        self.error = None
        self.closed = False

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.error:
            raise self.error
        response = FakeResponse(self.body, self.status, kwargs.get("data"))
        self.responses.append(response)
        return response

    def close(self):
        self.closed = True


class NativeHttpTests(unittest.TestCase):
    def setUp(self):
        self.credential = FakeCredential()
        self.session = FakeSession()
        self.client = ResponsesHttpClient(config(), self.credential, 17, session=self.session)

    def tearDown(self):
        self.client.close()

    def test_constructor_does_not_authenticate_or_contact_fabric(self):
        self.assertEqual(self.credential.scopes, [])
        self.assertEqual(self.session.calls, [])
        self.assertFalse(self.session.trust_env)

    def test_region_cannot_be_substituted_for_observed_workload_host(self):
        value = config()
        del value["workload_host"]
        value["capacity_region"] = "West US"
        with self.assertRaises(EvaluationError):
            ResponsesHttpClient(value, self.credential, 17, session=self.session)
        self.assertEqual(self.credential.scopes, [])

    def test_wrong_or_missing_capacity_id_rejected_before_authentication(self):
        for capacity_id in ("West US", "", None):
            with self.subTest(capacity_id=capacity_id), self.assertRaises(EvaluationError):
                runtime_config({**config(), "capacity_id": capacity_id})
        self.assertEqual(self.credential.scopes, [])

    def test_untrusted_origin_and_url_overrides_rejected(self):
        for host in (
            "http://wabi-offline-fixture.analysis.windows.net",
            "https://example.invalid", "https://wabi-offline-fixture.analysis.windows.net/other",
            "https://user@wabi-offline-fixture.analysis.windows.net",
            "https://wabi-offline-fixture.analysis.windows.net:443",
            "https://wabi-offline-fixture.analysis.windows.net?route=other",
            "https://wabi-offline-fixture.analysis.windows.net#other",
            "https://wabi-offline-fixture.analysis.windows.net.example.invalid",
        ):
            with self.subTest(host=host), self.assertRaises(EvaluationError):
                ResponsesHttpClient({**config(), "workload_host": host}, self.credential, 17, session=self.session)
        self.assertEqual(self.credential.scopes, [])

    def test_observed_dedicated_origin_must_match_the_supplied_capacity(self):
        value = {**config(), "workload_host": f"https://{UUID(int=3).hex}.pbidedicated.windows.net"}
        self.assertEqual(runtime_config(value)["workload_host"], value["workload_host"])
        with self.assertRaises(EvaluationError):
            runtime_config({**value, "capacity_id": str(UUID(int=4))})
        for host in (
            "https://fixture.pbidedicated.windows.net",
            f"https://{UUID(int=3).hex}.pbidedicated.windows.net.example.invalid",
            f"https://{UUID(int=3).hex}.pbidedicated.windows.net:443",
            f"https://{UUID(int=3).hex}.pbidedicated.windows.net/other",
        ):
            with self.subTest(host=host), self.assertRaises(EvaluationError):
                runtime_config({**value, "workload_host": host})
        self.assertEqual(self.credential.scopes, [])

    def test_create_conversation_matches_sdk_path_not_retired_assistants_path(self):
        self.client.new_conversation()
        call = self.session.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], self.client.artifact + "/conversations")
        self.assertNotIn("/aiassistant/openai", call["url"])
        self.assertEqual(json.loads(call["data"]), {})
        self.assertEqual(call["params"], {"api-version": API_VERSION})

    def test_exact_unicode_question_and_no_instruction_override(self):
        question = "合成テスト：表記ＡとA、改行\n末尾の空白も保持。 "
        self.session.body = b'data: {"type":"fixture"}\n\n'
        reply = self.client.submit(question, "offline-conversation")
        self.assertEqual(reply.body, self.session.body)
        self.assertEqual(json.loads(reply.request_body), {
            "input": question, "conversation": "offline-conversation",
            "model": DEFAULT_MODEL, "stream": False,
        })
        call = self.session.calls[0]
        self.assertEqual(call["url"], self.client.artifact + "/responses")
        self.assertEqual(reply.request_body, call["data"])
        self.assertFalse(call["allow_redirects"])

    def test_native_requests_use_pbi_audience_and_explicit_stage(self):
        self.client.new_conversation()
        self.client.submit("Synthetic question.", "offline-conversation")
        self.client.retrieve("offline-response")
        self.session.body = b'{"native":"diagnostics"}'
        self.client.diagnostics("offline-conversation", "offline-response")
        self.assertEqual(self.credential.scopes, [PBI_SCOPE] * 4)
        for call in self.session.calls:
            headers = call["headers"]
            self.assertEqual(headers["x-ms-ai-aiskill-stage"], "production")
            self.assertEqual(headers["x-ms-ai-assistant-scenario"], "aiskill")
            self.assertEqual(headers["X-Taxonomy-TrafficType"], "Production")
            self.assertEqual(headers["x-llm-service-tier"], "default")
            self.assertFalse(any("bypass" in name.lower() for name in headers))
            self.assertEqual(call["timeout"], 17)

    def test_sandbox_stage_is_not_implicitly_changed_to_published(self):
        client = ResponsesHttpClient({**config(), "stage": "sandbox"}, self.credential, 17, session=self.session)
        client.new_conversation()
        self.assertEqual(self.session.calls[0]["headers"]["x-ms-ai-aiskill-stage"], "sandbox")
        client.close()

    def test_diagnostics_uses_native_dataagents_route_and_correlated_response(self):
        self.session.body = b'{"native":"diagnostics"}'
        self.assertEqual(self.client.diagnostics("offline-conversation", "offline-response"), {"native": "diagnostics"})
        call = self.session.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], (
            f"{self.client.base}/dataagents/{config()['data_agent_id']}"
            "/conversations/offline-conversation/diagnostics"
        ))
        self.assertEqual(call["params"], {"responseId": "offline-response"})

    def test_redirect_never_replays_a_question_or_forwards_authorization(self):
        self.session.status = 307
        reply = self.client.submit("Synthetic question.", "offline-conversation")
        self.assertEqual(reply.status, 307)
        self.assertEqual(len(self.session.calls), 1)
        self.assertFalse(self.session.calls[0]["allow_redirects"])

    def test_generated_file_download_stays_in_the_same_artifact(self):
        self.session.body = b"\x89PNG\r\n\x1a\nfixture-image-bytes"
        reply = self.client.file_content("file-offline-fixture")
        self.assertEqual(reply.body, self.session.body)
        call = self.session.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], self.client.artifact + "/aiassistant/openai/files/file-offline-fixture/content")
        self.assertFalse(call["allow_redirects"])
        for identifier in ("../other", "https://example.invalid/file", "id?redirect=true"):
            with self.subTest(identifier=identifier), self.assertRaises(EvaluationError):
                self.client.file_content(identifier)
        self.assertEqual(len(self.session.calls), 1)

    def test_failed_question_post_has_no_automatic_retry(self):
        self.session.error = TimeoutError("Synthetic timeout.")
        with self.assertRaises(TimeoutError):
            self.client.submit("Synthetic question.", "offline-conversation")
        self.assertEqual(len(self.session.calls), 1)

    def test_raw_reply_does_not_contain_authentication_or_cookie_headers(self):
        reply = self.client.submit("Synthetic question.", "offline-conversation")
        serialized = reply.body + reply.request_body
        self.assertEqual(set(reply.__dict__), {"body", "status", "request_body"})
        self.assertNotIn(b"offline-placeholder", serialized)
        self.assertNotIn(b"Authorization", serialized)
        self.assertTrue(all(r.closed for r in self.session.responses))

    def test_diagnostics_errors_are_not_repaired(self):
        for body, status in ((b"{}", 403), (b"[]", 200), (b"unfinished-json", 200)):
            with self.subTest(body=body, status=status), self.assertRaises(EvaluationError):
                self.session.body, self.session.status = body, status
                self.client.diagnostics("offline-conversation", "offline-response")

    def test_failed_diagnostics_preserve_exact_body_for_private_journal(self):
        self.session.body, self.session.status = b'{"error":"synthetic-block"}', 403
        with self.assertRaises(NativeEvidenceError) as caught:
            self.client.diagnostics("offline-conversation", "offline-response")
        self.assertEqual(caught.exception.native_body, self.session.body)
        self.assertEqual(caught.exception.http_status, 403)
        self.assertNotIn("offline-placeholder", str(caught.exception))

    def test_only_exact_diagnostic_feature_gate_is_optional(self):
        payload = {
            "Message": "Data Agent diagnostics feature is not enabled.",
            "Source": "AISKILL", "error_code": "PERMISSION_DENIED",
        }
        self.assertTrue(diagnostics_feature_unavailable(encode(payload), 403))
        for body, status in (
            (encode(payload), 401), (encode(payload), 200), (b"{}", 403),
            (b"[]", 403), (b"\xff", 403),
            (encode({**payload, "Source": "KQL"}), 403),
            (encode({**payload, "Message": "Access denied."}), 403),
        ):
            self.assertFalse(diagnostics_feature_unavailable(body, status))

    def test_unrecognized_resource_id_cannot_escape_native_response_path(self):
        for response_id in ("..", "../elsewhere", "", "https://example.invalid", "id?query"):
            with self.subTest(response_id=response_id), self.assertRaises(EvaluationError):
                self.client.retrieve(response_id)
        self.assertEqual(self.credential.scopes, [])

    def test_cross_workspace_request_rejected_before_token_acquisition(self):
        with self.assertRaises(EvaluationError):
            self.client._request("GET", "https://example.invalid/other")
        self.assertEqual(self.credential.scopes, [])

    def test_close_closes_http_session(self):
        self.client.close()
        self.assertTrue(self.session.closed)


if __name__ == "__main__":
    unittest.main()
