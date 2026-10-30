import asyncio
import base64
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
            finally:
                self.assertTrue(client.is_closed, 'disconnect must close upstream before returning')

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

    async def transcription(self, upstream):
        request = NS(headers={"content-type": "application/json"},
                     body=AsyncMock(return_value=b'{"model":"synthetic","stream":true}'))
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: upstream))
        self.addAsyncCleanup(client.aclose)
        with patch.object(g.httpx, "AsyncClient", return_value=client), \
             patch.object(g, "resolve", return_value={"host": "synthetic", "card": {}}), \
             patch.object(g, "_guard_cold", new=AsyncMock(return_value=None)), \
             patch.object(g, "upstream_url", return_value="http://synthetic/transcriptions"):
            return await g.audio_transcriptions(request)

    async def test_transcription_preserves_raw_bytes(self):
        raw = b'\x00\xffsynthetic\n\x80'
        class Bytes(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield raw
        with patch.object(g, "_log_usage") as record:
            response = await self.transcription(httpx.Response(200, stream=Bytes(),
                                                              headers={"content-type": "application/octet-stream"}))
            events = await self.consume(response)
            self.assertEqual(b''.join(e.get('body', b'') for e in events), raw)
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs['usage_obj']['audio_output_bytes'], len(raw))

    async def test_transcription_error_keeps_http_status(self):
        with patch.object(g, "_log_usage") as record:
            response = await self.transcription(httpx.Response(422, json={"error": "synthetic format error"}))
            self.assertEqual(response.status_code, 422)
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs['status'], 422)

    async def test_transcription_disconnect_finalizes_once(self):
        class Bytes(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'partial'
                yield b'final'
        with patch.object(g, "_log_usage") as record:
            response = await self.transcription(httpx.Response(200, stream=Bytes()))
            try:
                await self.consume(response, disconnect=True)
            except asyncio.CancelledError:
                pass
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.kwargs['status'], 499)


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


class TaskSystemTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import tempfile
        import tasks as t
        self.tasks_mod = t
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store = t.TaskStore(base_dir=self.tmpdir.name, redis_url="")
        self.prev_store = g.TASK_STORE
        self.prev_inline = g.TASK_INLINE_EXECUTION
        self.prev_client = g.TASK_HTTP_CLIENT
        self.prev_cards = copy.deepcopy(g.CARDS)
        self.prev_isvc = copy.deepcopy(g.ISVC_STATE)
        g.TASK_STORE = self.store
        g.TASK_INLINE_EXECUTION = True

        self.ocr_card = {
            "id": "glm-ocr",
            "type": "ocr",
            "mode": "task",
            "endpoints": {"primary": "/v1/tasks"},
            "routing": {"k8s_name": "glm-ocr", "upstream_path": "/v1/chat/completions", "no_stream": True},
            "limits": {"context_window": 16384, "max_completion_tokens": 4096},
            "defaults": {"chat": {"temperature": 0.0, "max_tokens": 4096}},
            "input_map": {
                "files": {"type": "file[]", "required": True, "description": "PDFs or images"},
                "prompt": {"type": "string", "default": "Text Recognition:"},
                "dpi": {"type": "integer", "default": 200},
            },
            "custom_params": {
                "passthrough": False,
                "schema": {
                    "repetition_penalty": {"type": "float", "default": 1.05},
                },
            },
            "tasks": {"enabled": True, "mode": "task", "loop_mode": "pdf_pages", "unit": "pages"},
        }
        self.img_card = {
            "id": "kandinsky-3",
            "type": "image",
            "mode": "both",
            "endpoints": {"primary": "/v1/images/generations", "edit": "/v1/images/edits"},
            "routing": {"k8s_name": "kandinsky-3", "upstream_path": "/v1/images/generations"},
            "input_map": {
                "prompt": {"type": "string", "required": True},
                "num_inference_steps": {"type": "integer", "default": 25},
                "n": {"type": "integer", "default": 1, "max": 1},
            },
            "custom_params": {"passthrough": True},
            "tasks": {"enabled": True, "mode": "both", "loop_mode": "items", "unit": "images"},
        }
        self.chat_card = {
            "id": "command-r-7b",
            "type": "chat",
            "mode": "api",
            "endpoints": {"primary": "/v1/chat/completions"},
            "routing": {"k8s_name": "command-r-7b"},
        }
        g.CARDS.clear()
        g.CARDS.update({
            "glm-ocr": self.ocr_card,
            "kandinsky-3": self.img_card,
            "command-r-7b": self.chat_card,
        })
        g.ISVC_STATE.clear()
        g.ISVC_STATE.update({
            "glm-ocr": {"ready": True, "resources": {"gpus": 1, "vram_mib": 12288}},
            "kandinsky-3": {"ready": True, "resources": {"gpus": 1, "vram_mib": 24576}},
            "command-r-7b": {"ready": True, "resources": {"gpus": 1, "vram_mib": 32768}},
        })

    def tearDown(self):
        g.TASK_STORE = self.prev_store
        g.TASK_INLINE_EXECUTION = self.prev_inline
        g.TASK_HTTP_CLIENT = self.prev_client
        g.CARDS.clear()
        g.CARDS.update(self.prev_cards)
        g.ISVC_STATE.clear()
        g.ISVC_STATE.update(self.prev_isvc)
        self.tmpdir.cleanup()

    async def test_models_catalog_mode_filtering_and_web_page(self):
        # Default GET /v1/models -> chat-only (command-r-7b)
        req_default = NS(headers={}, query_params={})
        res_default = await g.list_models(req_default)
        self.assertEqual([m["id"] for m in res_default["data"]], ["command-r-7b"])
        self.assertEqual(res_default["data"][0]["mode"], "api")

        # GET /v1/models?all=true -> all 3 models with mode field and tasks info
        req_all = NS(headers={}, query_params={"all": "true"})
        res_all = await g.list_models(req_all)
        by_id = {m["id"]: m for m in res_all["data"]}
        self.assertEqual(set(by_id.keys()), {"command-r-7b", "glm-ocr", "kandinsky-3"})
        self.assertEqual(by_id["glm-ocr"]["mode"], "task")
        self.assertEqual(by_id["kandinsky-3"]["mode"], "both")
        self.assertTrue(by_id["glm-ocr"]["tasks"]["enabled"])
        self.assertIn("dpi", by_id["glm-ocr"]["tasks"]["properties"])
        self.assertIn("repetition_penalty", by_id["glm-ocr"]["tasks"]["properties"])

        # GET /v1/models?tasks=true -> glm-ocr and kandinsky-3
        req_tasks = NS(headers={}, query_params={"tasks": "true"})
        res_tasks = await g.list_models(req_tasks)
        self.assertEqual([m["id"] for m in res_tasks["data"]], ["glm-ocr", "kandinsky-3"])

        # Web catalog GET / includes task-card class and mode badges
        html_page = g._catalog_html()
        self.assertIn("task-card", html_page)
        self.assertIn("async task", html_page)
        self.assertIn("api + task", html_page)
        self.assertIn("/v1/tasks", html_page)

    async def test_sync_chat_rejects_task_only_model(self):
        req = NS(
            headers={"content-type": "application/json"},
            body=AsyncMock(return_value=b'{"model":"glm-ocr","messages":[{"role":"user","content":"hi"}]}'),
        )
        resp = await g.chat(req)
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.body)
        self.assertEqual(body["error"]["code"], "task_only_model")

    async def test_sequential_ocr_task_and_unlisted_params(self):
        recorded_Upstream: list[dict] = []

        def _mock_handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content.decode("utf-8"))
            recorded_Upstream.append(payload)
            return httpx.Response(
                200,
                json={
                    "id": f"cmpl-{len(recorded_Upstream)}",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": f"# Page {len(recorded_Upstream)} Markdown"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
        self.addAsyncCleanup(client.aclose)
        g.TASK_HTTP_CLIENT = client

        with patch.object(g, "_ensure_predictor_ready_for_task", new=AsyncMock(return_value=("http://mock-vllm", "glm-ocr-predictor.models.svc.cluster.local"))):
            t_Mod = self.tasks_mod
            png_b64 = base64.b64encode(t_Mod._FALLBACK_1X1_PNG).decode("ascii")
            req = NS(
                headers={"content-type": "application/json", "authorization": "Bearer key-alpha"},
                query_params={},
                json=AsyncMock(
                    return_value={
                        "model": "glm-ocr",
                        "params": {
                            "prompt": "Table Recognition:",
                            "custom_vllm_flag": "keep_me",
                        },
                        "inputs": [
                            {"name": "page1.png", "image_base64": png_b64},
                            {"name": "page2.png", "image_base64": png_b64, "temperature": 0.2},
                        ],
                    }
                ),
            )
            kh, manifest = await t_Mod.stage_task_submission(req, self.store, g.CARDS)
            self.assertEqual(manifest["total_units"], 2)
            final = await t_Mod.execute_task(self.store, kh, manifest["task_id"], g._task_runtime_hooks())
            self.assertIsNotNone(final)
            self.assertEqual(final["status"], "completed")
            self.assertEqual(final["completed_units"], 2)
            self.assertEqual(final["failed_units"], 0)
            self.assertEqual(len(recorded_Upstream), 2)

            # Verify image_url block precedes text prompt block (GLM-OCR best practice)
            msg_content = recorded_Upstream[0]["messages"][0]["content"]
            self.assertEqual(msg_content[0]["type"], "image_url")
            self.assertEqual(msg_content[1]["type"], "text")
            self.assertEqual(msg_content[1]["text"], "Table Recognition:")
            # Card default temperature=0.0 on item 1, overridden to 0.2 on item 2, plus unlisted custom_vllm_flag preserved
            self.assertEqual(recorded_Upstream[0]["temperature"], 0.0)
            self.assertEqual(recorded_Upstream[1]["temperature"], 0.2)
            self.assertEqual(recorded_Upstream[0]["custom_vllm_flag"], "keep_me")

            # Verify result.zip contains manifest.json and out/page1.md, out/page2.md
            zpath = self.store.result_zip_path(kh, manifest["task_id"])
            self.assertTrue(zpath.is_file())

    async def test_partial_failure_error_log_and_retention_reaper(self):
        from datetime import datetime, timedelta, timezone
        t_Mod = self.tasks_mod
        png_b64 = base64.b64encode(t_Mod._FALLBACK_1X1_PNG).decode("ascii")

        def _mock_img_handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content.decode("utf-8"))
            if payload.get("prompt") == "TRIGGER_OOM":
                return httpx.Response(500, text='{"error":"CUDA out of memory on item 2"}')
            # Verify passthrough stripped `model` and kept unlisted `width`
            assert "model" not in payload
            assert payload.get("width") == 768
            return httpx.Response(200, json={"created": 1700000000, "data": [{"b64_json": png_b64}]})

        client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_img_handler))
        self.addAsyncCleanup(client.aclose)
        g.TASK_HTTP_CLIENT = client

        with patch.object(g, "_ensure_predictor_ready_for_task", new=AsyncMock(return_value=("http://mock-img", "kandinsky-3-predictor.models.svc.cluster.local"))):
            req = NS(
                headers={"content-type": "application/json", "authorization": "Bearer key-beta"},
                query_params={},
                json=AsyncMock(
                    return_value={
                        "model": "kandinsky-3",
                        "params": {"width": 768, "height": 768},
                        "inputs": [
                            {"name": "ok1", "prompt": "A mountain sunrise"},
                            {"name": "bad2", "prompt": "TRIGGER_OOM"},
                            {"name": "ok3", "prompt": "A calm ocean"},
                        ],
                    }
                ),
            )
            kh, manifest = await t_Mod.stage_task_submission(req, self.store, g.CARDS)
            tid = manifest["task_id"]
            final = await t_Mod.execute_task(self.store, kh, tid, g._task_runtime_hooks())
            self.assertEqual(final["status"], "completed")
            self.assertEqual(final["completed_units"], 2)
            self.assertEqual(final["failed_units"], 1)
            self.assertEqual(final["error_count"], 1)

            err_log = self.store.read_error_log(kh, tid)
            self.assertIn("bad2", err_log)
            self.assertIn("CUDA out of memory on item 2", err_log)

            # Verify 24h post-completion reaper does not reap at +2h, but reaps at +25h
            now_dt = datetime.now(timezone.utc)
            self.assertEqual(self.store.reap_expired(now=now_dt + timedelta(hours=2)), [])
            reaped = self.store.reap_expired(now=now_dt + timedelta(hours=25))
            self.assertEqual(reaped, [tid])
            self.assertIsNone(self.store.load_manifest(kh, tid))


if __name__ == "__main__":
    unittest.main()
