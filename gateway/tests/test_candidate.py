import asyncio
import copy
import json
import time
import unittest
import httpx
from types import SimpleNamespace as NS
from unittest.mock import patch, AsyncMock

import gateway as g
from capacity import fits, parse_metrics
from conversation import normalize_reasoning


class HistoryTests(unittest.TestCase):
    def test_aliases_are_lossless_and_input_unchanged(self):
        messages = [{"role": "assistant", "content": "first", "reasoning_content": "hidden-9271"}]
        before = copy.deepcopy(messages)
        result = normalize_reasoning(messages)
        self.assertEqual(result[0]["reasoning"], "hidden-9271")
        self.assertEqual(result[0]["reasoning_content"], "hidden-9271")
        self.assertEqual(messages, before)
        self.assertEqual(normalize_reasoning(result), result)

    def test_canonical_empty_reasoning_is_not_overridden(self):
        result = normalize_reasoning([{"role": "assistant", "reasoning": "", "reasoning_content": "other"}])
        self.assertEqual(result[0]["reasoning_content"], "")

    def test_anthropic_thinking_and_tool_roundtrip(self):
        result = g.anth_to_openai({"model": "synthetic", "max_tokens": 40, "messages": [
            {"role": "user", "content": "start"},
            {"role": "assistant", "content": [
                {"type": "thinking", "thinking": "hidden-9271"},
                {"type": "text", "text": "checking"},
                {"type": "tool_use", "id": "call-1", "name": "lookup", "input": {"x": 3}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "call-1", "content": "result"},
                {"type": "text", "text": "continue"}]}]})
        messages = result["messages"]
        self.assertEqual([m["role"] for m in messages], ["user", "assistant", "tool", "user"])
        self.assertEqual(messages[1]["reasoning_content"], "hidden-9271")
        self.assertEqual(json.loads(messages[1]["tool_calls"][0]["function"]["arguments"]), {"x": 3})
        self.assertEqual(messages[2]["tool_call_id"], "call-1")
        self.assertEqual(messages[2]["content"], "result")


class CapacityTests(unittest.TestCase):
    def gpu(self, reserved=0, shares=0, cores=0):
        return dict(total_bytes=48000*1024**2, reserved_bytes=reserved*1024**2,
                    reserved_cores=cores, shares=shares)

    def test_distinct_cards_required_for_tensor_parallel_slices(self):
        ask = {"gpus": 2, "vram_mib": 8000, "gpucores": 20}
        self.assertFalse(fits([self.gpu()], ask))
        self.assertTrue(fits([self.gpu(), self.gpu()], ask))

    def test_occupied_card_is_not_whole_card_free(self):
        self.assertFalse(fits([self.gpu(1, 1)], {"gpus": 1}))
        self.assertFalse(fits([self.gpu(cores=10)], {"gpus": 1}))
        self.assertTrue(fits([self.gpu()], {"gpus": 1}))

    def test_memory_core_and_share_constraints(self):
        ask = {"gpus": 1, "vram_mib": 8000, "gpucores": 20}
        for gpu in (self.gpu(41000), self.gpu(cores=90), self.gpu(shares=10)):
            self.assertFalse(fits([gpu], ask))

    def test_incomplete_and_invalid_metrics_are_unknown(self):
        with self.assertRaises(ValueError):
            fits([{"total_bytes": 99}], {"gpus": 1})
        with self.assertRaises(ValueError):
            parse_metrics('hami_gpu_memory_limit_bytes{node="n",device_uuid="u"} NaN')

    def test_metric_identity_and_duplicate_conflict(self):
        text = 'hami_gpu_memory_limit_bytes{node="n",device_uuid="u"} 100\n'
        self.assertEqual(parse_metrics(text)[("n", "u")]["total_bytes"], 100)
        with self.assertRaises(ValueError):
            parse_metrics(text + text.replace(' 100', ' 200'))

    def test_stale_capacity_does_not_reject_requests(self):
        with patch.dict(g.GPU_SNAPSHOT, devices={}, updated_at=0, clear=True):
            self.assertEqual(g._can_schedule("synthetic", {"gpus": 2}), (True, "capacity-unknown"))


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tables = (g.POD_NODE, g.POD_PHASE, g.POD_READY)
        self.previous = [copy.deepcopy(t) for t in self.tables]
        for table in self.tables:
            table.clear()

    def tearDown(self):
        for table, old in zip(self.tables, self.previous):
            table.clear()
            table.update(old)

    def pod(self, name, phase="Running", ready="True"):
        return NS(metadata=NS(name=name, labels={"serving.kserve.io/inferenceservice": "synthetic"}, deletion_timestamp=None),
                  spec=NS(node_name="node"), status=NS(phase=phase, conditions=[NS(type="Ready", status=ready)]))

    def test_relist_removes_missed_deletions(self):
        g._ingest_pod(self.pod("gone"))
        snapshot = NS(items=[self.pod("new")], metadata=NS(resource_version="27"))
        self.assertEqual(g._replace_inventory("pods", snapshot), "27")
        self.assertEqual(set(g.POD_PHASE["synthetic"]), {"new"})

    def test_running_unready_counts_as_starting(self):
        for pod in (self.pod("ready"), self.pod("loading", ready="False"), self.pod("pending", "Pending", "False")):
            g._ingest_pod(pod)
        with patch.dict(g._DISCOVERY, pods_listed_at=time.time()):
            status = g._replica_status("synthetic", {}, {})
        self.assertEqual((status["ready_replicas"], status["starting_replicas"], status["pending_replicas"]), (1, 2, 1))

    def test_failed_relist_preserves_last_good_snapshot(self):
        g._ingest_pod(self.pod("keep"))
        before = copy.deepcopy(g.POD_PHASE)
        snapshot = NS(items=[None], metadata=NS(resource_version="28"))
        with self.assertRaises(Exception):
            g._replace_inventory("pods", snapshot)
        self.assertEqual(g.POD_PHASE, before)


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def forward(self, handler):
        original = httpx.AsyncClient
        client = original(transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(client.aclose)
        with patch.object(g.httpx, "AsyncClient", return_value=client), \
             patch.object(g, "upstream_url", return_value="http://synthetic/chat"), \
             patch.object(g, "upstream_headers", return_value={}):
            return await g._forward({}, "/v1/chat/completions", b"{}", True,
                                    strip_reasoning=False,
                                    log_ctx={"request": None, "endpoint": "/test", "api": "openai"})

    async def consume(self, response, disconnect=False):
        events = []
        async def send(message):
            events.append(message)
            if disconnect and message["type"] == "http.response.body":
                raise asyncio.CancelledError()
        async def receive():
            await asyncio.Event().wait()
        await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
        return events

    async def test_upstream_error_keeps_http_status(self):
        with patch.object(g, "_log_usage") as record:
            response = await self.forward(lambda r: httpx.Response(400, json={"error": "too large"}))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs["status"], 400)

    async def test_success_preserves_usage_and_finalizes_once(self):
        body = b'data: {"usage":{"completion_tokens":7},"choices":[]}\n\ndata: [DONE]\n\n'
        with patch.object(g, "_log_usage") as record:
            response = await self.forward(lambda r: httpx.Response(200, content=body))
            events = await self.consume(response)
            self.assertIn(b'[DONE]', b''.join(e.get("body", b"") for e in events))
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs["usage_obj"], {"completion_tokens": 7})
            self.assertEqual(record.call_args.kwargs["status"], 200)

    async def test_disconnect_is_not_success_and_finalizes_once(self):
        with patch.object(g, "_log_usage") as record:
            response = await self.forward(lambda r: httpx.Response(200, content=b'data: {}\n\n'))
            try:
                await self.consume(response, disconnect=True)
            except asyncio.CancelledError:
                pass  # ASGI/Starlette versions differ in cancellation propagation.
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs["status"], 499)

    async def anthropic(self, upstream, disconnect=False):
        request = NS(body=AsyncMock(return_value=json.dumps({"model": "synthetic", "max_tokens": 40,
            "stream": True, "messages": [{"role": "user", "content": "hello"}]}).encode()))
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: upstream))
        info = {"type": "chat", "ready": True, "card": {}}
        with patch.object(g.httpx, "AsyncClient", return_value=client), \
             patch.object(g, "resolve", return_value=info), \
             patch.object(g, "_guard_cold", new=AsyncMock(return_value=None)), \
             patch.object(g, "prepare_chat", side_effect=lambda info, body: (body, False)), \
             patch.object(g, "upstream_url", return_value="http://synthetic/chat"), \
             patch.object(g, "upstream_headers", return_value={}), \
             patch.object(g, "resource_block", return_value={}):
            response = await g.anthropic_messages(request)
            try:
                return await self.consume(response, disconnect=disconnect)
            except asyncio.CancelledError:
                return []

    async def test_anthropic_upstream_error_is_not_empty_success(self):
        with patch.object(g, "_log_usage") as record:
            events = await self.anthropic(httpx.Response(400, json={"error": {"message": "too large"}}))
            body = b''.join(e.get("body", b"") for e in events)
            self.assertIn(b'event: error', body)
            self.assertNotIn(b'event: message_start', body)
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs["status"], 400)

    async def test_anthropic_disconnect_finalizes_once(self):
        with patch.object(g, "_log_usage") as record:
            await self.anthropic(httpx.Response(200, content=b'data: {"choices":[]}\n\n'), disconnect=True)
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs["status"], 499)


class PageTests(unittest.TestCase):
    def test_support_docs_metadata_and_narrow_layout(self):
        with patch.dict(g.CARDS, {}, clear=True):
            page = g._catalog_html()
        self.assertIn('mailto:support@tech.alliancecan.ca', page)
        self.assertIn('https://docs.alliancecan.ca/wiki/aleph', page)
        self.assertNotIn('Request a key', page)
        self.assertIn('name="description"', page)
        self.assertIn('property="og:title"', page)
        self.assertIn('@media(max-width:480px)', page)
        self.assertIn('.titleblock{flex-wrap:nowrap;gap:12px}', page)


if __name__ == "__main__":
    unittest.main()
