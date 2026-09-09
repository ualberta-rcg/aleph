"""One synthetic near-256K request through Aleph; no credentials or user data.

Run in the bounded CPU-only administrative test Job, not on the login node.
Arguments: internal gateway base URL, running engine base URL.
Only counts/verdicts are printed. Exactly one long inference request, no retries.
"""
import json
import signal
import sys
import time
import urllib.request

GATEWAY, ENGINE = (arg.rstrip('/') for arg in sys.argv[1:3])
MODEL = 'qwen38-27b'
TARGET = 261888
MARKERS = ['ALEPH_START_739241', 'ALEPH_MIDDLE_582613', 'ALEPH_END_946827']


def emit(**result):
    print(json.dumps(result), flush=True)


def post(base, path, body, timeout=60):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=timeout)


def control(stage):
    with post(GATEWAY, '/v1/chat/completions', {
        'model': MODEL, 'messages': [{'role': 'user', 'content': 'Reply only OK.'}],
        'reasoning_effort': 'none', 'max_tokens': 16,
    }) as response:
        result = json.load(response)
    ok = bool(result.get('choices', [{}])[0].get('message', {}).get('content'))
    emit(stage=stage, passed=ok, usage=result.get('usage'))
    if not ok:
        raise RuntimeError('short control failed')


def messages(n):
    half = n // 2
    text = ('This is synthetic context-limit validation. Remember the three ALEPH markers.\n'
            + MARKERS[0] + '\n' + ' filler' * half + '\n' + MARKERS[1] + '\n'
            + ' filler' * (n - half) + '\n' + MARKERS[2]
            + '\nReturn the three ALEPH markers, in their original order, and nothing else.')
    return [{'role': 'user', 'content': text}]


def count(n):
    with post(ENGINE, '/tokenize', {
        'model': MODEL, 'messages': messages(n),
        'chat_template_kwargs': {'enable_thinking': False},
        'add_generation_prompt': True,
    }, timeout=90) as response:
        result = json.load(response)
    if result.get('max_model_len') != 262144:
        raise RuntimeError('live model limit changed')
    return result['count']


def deadline(*_):
    raise TimeoutError('600-second overall inference deadline exceeded')


control('baseline_control')
small, larger = count(64), count(128)
if larger - small != 64:
    raise RuntimeError('filler is not one token per repeat; no long inference sent')
n = TARGET - (small - 64)
for attempt in range(4):
    actual = count(n)
    emit(stage='token_count', attempt=attempt + 1, rendered_input_tokens=actual)
    if actual == TARGET:
        break
    n += TARGET - actual
else:
    raise RuntimeError('exact token target not reached; no long inference sent')

body = {'model': MODEL, 'messages': messages(n), 'reasoning_effort': 'none',
        'max_tokens': 256, 'stream': True, 'stream_options': {'include_usage': True},
        'temperature': 0}
emit(stage='long_request_start', rendered_input_tokens=actual,
     requested_output_tokens=256, total_budget=actual + 256)
signal.signal(signal.SIGALRM, deadline)
signal.alarm(600)
start = time.monotonic()
pieces, usage, finish, done, first_token, failure = [], {}, None, False, None, None
try:
    with post(GATEWAY, '/v1/chat/completions', body, timeout=600) as response:
        for raw in response:
            if not raw.startswith(b'data:'):
                continue
            data = raw[5:].strip()
            if data == b'[DONE]':
                done = True
                break
            event = json.loads(data)
            if event.get('error'):
                failure = 'upstream_stream_error'
                break
            if event.get('usage'):
                usage = event['usage']
            for choice in event.get('choices', []):
                content = choice.get('delta', {}).get('content')
                if content:
                    if first_token is None:
                        first_token = time.monotonic() - start
                    pieces.append(content)
                if choice.get('finish_reason'):
                    finish = choice['finish_reason']
except Exception as error:
    failure = type(error).__name__
    if hasattr(error, 'code'):
        failure += '_HTTP_' + str(error.code)
finally:
    signal.alarm(0)

output = ''.join(pieces)
passed = (not failure and done and finish == 'stop'
          and usage.get('prompt_tokens') == TARGET
          and 0 < usage.get('completion_tokens', 0) <= 256)
emit(stage='long_request_result', passed=passed, failure=failure,
     done=done, finish_reason=finish, usage=usage,
     marker_recall=[marker in output for marker in MARKERS],
     first_token_seconds=first_token, elapsed_seconds=round(time.monotonic() - start, 2))
control('post_control')
sys.exit(0 if passed else 1)
