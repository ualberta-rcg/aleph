# Using Aleph for research

Aleph provides model APIs hosted on Vulcan. Use https://inference.vulcan.alliancecan.ca/ to choose a model and inspect its individual capabilities and limits. For browser chat, use https://llm.vulcan.alliancecan.ca/ .

Use your existing API key through your normal secure workflow. Getting-started documentation is linked at https://docs.alliancecan.ca/wiki/aleph; publication of that page is handled by the operator. Model requests and support go to support@tech.alliancecan.ca . Do not send keys or confidential research content in a support request.

## Choosing a model

Start with the task: chat/coding, embeddings, reranking, speech, or a specific scientific workload. Check the card's endpoint and input schema; the same input format does not work for every model. Verify required tool/vision support, license, context window and output limit for the selected model.

Availability in the catalog means:
- **Ready:** at least one predictor pod is ready to serve.
- **Starting:** a pod is Pending or still initializing/loading.
- **Sleeping:** a deployed, eligible model has no running predictor and can wake on demand.
- **Unavailable:** it is not currently ready for use.
- **Unknown:** discovery data is too old to claim a current state.

A request to a sleeping model may return a documented cold-start error and Retry-After. Inspect the error code before retrying. `insufficient_capacity` means that a suitable placement was not available according to the gateway's current advisory view; it is not a reserved queue position. Do not retry every 400/401/403/500/503 forever. Stop on invalid input or authentication errors and investigate unrelated failures.

The capacity endpoint separates HAMi reservations from measured GPU memory. Measurements can be partial or stale. The scheduler remains authoritative; an apparent fit is not a reservation or a start-time promise.

## Qwen38-27b only

The limit is 262144 tokens total, including rendered input and output. The current output cap is 32768. System instructions, tools, images and retained reasoning consume context too. Other models retain their own limits; 256K is not a platform-wide promise.

On 2026-09-09, a single request through Aleph accepted 261888 rendered input tokens with a 256-token output allowance, returned 33 tokens and recalled markers near the beginning, middle and end. It completed in 120.15 seconds with thinking disabled. The model remained healthy. This verifies that near-boundary synthetic text case; it is not a guarantee of arbitrary-document recall, concurrent 256K sessions or multimodal boundary behavior. See [the measured result](../models/qwen38-27b/CONTEXT-256K-RESULT.md).

With a 32768-token output allowance, the arithmetic input ceiling is 229376 tokens, including template overhead. Count the rendered request rather than estimating from characters. Do not fill all 262144 tokens with input and still expect generated output. The thinking-off path has a separate 2048-token output cap.

The synthetic checks show that prior reasoning can reach Qwen's rendered prompt. Preserving history does not guarantee that a model will recall every detail or answer a behavioral test correctly. A first response with no hidden number or with a length-truncated answer makes the two-number test inconclusive.

## Reproducible runs

Record the model ID, date, endpoint, sampling/effort/output parameters, client version, the model metadata available at execution time, and any input preprocessing. Keep prompts/results in storage appropriate for their classification. A model ID or temperature of zero alone is not a reproducibility guarantee; backend versions and execution details can matter.

For repeatable processing, start with a short validated sample, bound concurrency, save completed outputs and resume after interruption. This is ordinary client-side processing; Aleph is not adding an asynchronous batch API in this release. A notebook can use the same small request shown below, then inspect metadata and save the request parameters alongside results.

Use the [standard-library notebook](examples/aleph-quickstart.ipynb) in an existing notebook environment, or the [sequential resumable client](examples/aleph-process.py). Neither requires a new package installation. Run scripts in an appropriate allocated session, not as a workload on the shared login node. Store inputs/results on your scratch workspace while working, and move important cleaned results to your project storage.

The client accepts JSONL records such as `{"id":"sample-1","prompt":"Explain a confidence interval in two sentences."}`. It sends one request at a time, saves each success and resumes only when the ID, endpoint, model and request fingerprint match. It stops on errors rather than retrying indefinitely. An interrupted request may have completed server-side before the result was saved; resuming can repeat that request and its usage. This is not exactly-once processing.

```bash
python3 examples/aleph-process.py inputs.jsonl results.jsonl --model qwen38-27b --validate-only
python3 examples/aleph-process.py inputs.jsonl results.jsonl --model qwen38-27b
```

For scientific tasks, validate a small sample against an appropriate reference or known result and inspect units, input preprocessing and uncertainty. Preserve model output separately from your scientific interpretation. Do not assume chat-model output is a validated scientific measurement.

```bash
# Supply your existing key through your normal secure workflow; never commit it.
curl --fail-with-body https://inference.vulcan.alliancecan.ca/v1/models \
  -H "Authorization: Bearer $ALEPH_API_KEY"

curl --fail-with-body https://inference.vulcan.alliancecan.ca/v1/chat/completions \
  -H "Authorization: Bearer $ALEPH_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"model":"qwen38-27b","messages":[{"role":"user","content":"Explain a confidence interval in two sentences."}],"reasoning_effort":"none","max_tokens":128}'
```

## Feedback prompts for later review

No researchers have been contacted as part of this work. Ask about the task and required capability, interactive latency versus throughput, acceptable cold-start behavior, typical input/output sizes, reproducibility needs and whether task-specific examples would help. Cover interactive chat, document processing, repeatable runs and scientific APIs separately. Error reports should include the model, endpoint, client version, timestamp, HTTP/error code and a synthetic reproducer when possible. Do not request keys or unpublished conversation content.

Usage views, project reporting and asynchronous batch support remain separate proposals informed by that feedback. This guide does not establish a data-classification, retention or service-level policy. Confirm suitability for restricted or confidential data with your project and service operator before submission; no new retention or access guarantees are introduced here.
