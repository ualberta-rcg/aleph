"""Sequential, resumable Aleph JSONL example; Python standard library only."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path)
    parser.add_argument('results', type=Path)
    parser.add_argument('--model', required=True)
    parser.add_argument('--base-url', default='https://inference.vulcan.alliancecan.ca/v1')
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if args.inputs.resolve() == args.results.resolve():
        parser.error('input and result files must be different')
    if args.max_tokens < 1:
        parser.error('max-tokens must be positive')
    endpoint = args.base_url.rstrip('/') + '/chat/completions'
    completed = {}
    if args.results.exists():
        with args.results.open() as source:
            for line in source:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row['id'] in completed:
                    raise ValueError('duplicate result ID; review results before resuming')
                completed[row['id']] = row['request_sha256']
    planned, seen = [], set()
    with args.inputs.open() as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row.get('id'), str) or not row['id'] or not isinstance(row.get('prompt'), str):
                raise ValueError(f'line {line_number}: string id and prompt required')
            if row['id'] in seen:
                raise ValueError(f'line {line_number}: duplicate input ID')
            seen.add(row['id'])
            body = {'model': args.model, 'messages': [{'role': 'user', 'content': row['prompt']}],
                    'max_tokens': args.max_tokens, 'temperature': 0}
            fingerprint = hashlib.sha256(json.dumps({'endpoint': endpoint, 'body': body},
                                                    sort_keys=True).encode()).hexdigest()
            if row['id'] in completed:
                if completed[row['id']] != fingerprint:
                    raise ValueError(f'line {line_number}: input or parameters changed; use a new result file')
                continue
            planned.append((row['id'], body, fingerprint))
    print(f'{len(planned)} pending; {len(seen) - len(planned)} already saved')
    if args.validate_only or not planned:
        return
    key = os.environ.get('ALEPH_API_KEY')
    if not key:
        raise ValueError('provide ALEPH_API_KEY through your existing secure workflow')
    with args.results.open('a') as destination:
        for item_id, body, fingerprint in planned:
            request = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers={
                'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
            try:
                with urllib.request.urlopen(request, timeout=600) as response:
                    result = json.load(response)
            except urllib.error.HTTPError as error:
                raise RuntimeError(f'HTTP {error.code}; stopped without retrying; prior results are saved') from None
            if result.get('error') or not result.get('choices'):
                raise RuntimeError('invalid response; stopped without saving this record')
            record = {'id': item_id, 'request_sha256': fingerprint, 'endpoint': endpoint,
                      'model': args.model, 'max_tokens': args.max_tokens, 'temperature': 0,
                      'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'response': result}
            destination.write(json.dumps(record) + '\n')
            destination.flush()
            os.fsync(destination.fileno())
            print('saved one response', flush=True)


if __name__ == '__main__':
    main()
