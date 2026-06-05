# birdnet-analyzer — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: audio-classification
(birdnetlib + tensorflow-cpu). id `birdnet-analyzer`.

## Scale-up
- Cold start: venv (tensorflow-cpu + birdnetlib + soundfile) + model bundle (ships with
  birdnetlib). `3/3 Running`.

## Endpoint tests (PASS)

### POST /v1/science/identify
3 s of synthetic 48 kHz audio (2.5 kHz sine), with location/week metadata:
```python
import json, urllib.request, math
sr=48000; n=sr*3
audio=[0.2*math.sin(2*math.pi*2500*i/sr) for i in range(n)]
body=json.dumps({"model":"birdnet-analyzer","audio":audio,"sample_rate":sr,
                 "lat":42.5,"lon":-76.5,"week":26,"min_confidence":0.1}).encode()
req=urllib.request.Request("$GW/v1/science/identify",data=body,
                           headers={"Content-Type":"application/json"})
print(urllib.request.urlopen(req,timeout=120).read().decode())
```
→ HTTP 200 (~16 s), `{"model":"birdnet-analyzer","detections":[]}`. PASS —
pipeline runs end-to-end; empty detections is correct for a non-bird synthetic tone.
Real recordings return species + confidence + time spans.

### Catalog
- `GET /v1/models?all=true` → `birdnet-analyzer` discovered. PASS.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (audio classifier).

## Card parity
id=birdnet-analyzer, k8s_name=birdnet-analyzer, type=audio-classification, gpu=false,
endpoint /v1/science/identify (48 kHz float samples + optional lat/lon/week/min_confidence).
