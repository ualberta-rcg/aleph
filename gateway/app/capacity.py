"""Read HAMi reservations without inventing GPU placement from model pod counts."""
import math
import re

FIELDS = {
    "hami_gpu_memory_limit_bytes": "total_bytes",
    "hami_gpu_memory_allocated_bytes": "reserved_bytes",
    "hami_gpu_core_allocated_ratio": "reserved_cores",
    "hami_gpu_shared_count": "shares",
    "hami_host_gpu_memory_used_bytes": "used_bytes",
}
LINE = re.compile(r'^(\w+)\{([^}]*)\}\s+(\S+)')
LABEL = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')


def parse_metrics(text):
    devices = {}
    for line in text.splitlines():
        match = LINE.match(line)
        if not match or match[1] not in FIELDS:
            continue
        labels = dict(LABEL.findall(match[2]))
        node, uuid = labels.get("node"), labels.get("device_uuid")
        if not node or not uuid:
            continue
        value = float(match[3])
        if not math.isfinite(value) or value < 0:
            raise ValueError("invalid HAMi metric")
        device = devices.setdefault((node, uuid), {"node": node, "uuid": uuid})
        field = FIELDS[match[1]]
        if field in device and device[field] != value:
            raise ValueError("conflicting HAMi samples")
        device[field] = value
    return devices


def fits(devices, resources, share_limit=10):
    """An ask needs N distinct cards on one node, not N times one card's memory."""
    count = int(resources.get("gpus") or 0)
    memory = int(resources.get("vram_mib") or 0) * 1024 * 1024
    cores = int(resources.get("gpucores") or 0)
    if count < 0 or memory < 0 or not 0 <= cores <= 100:
        raise ValueError("invalid GPU request")
    if count <= 0:
        return memory <= 0
    whole = memory <= 0 or cores == 100
    candidates = 0
    for gpu in devices:
        if not all(k in gpu for k in ("total_bytes", "reserved_bytes", "reserved_cores", "shares")):
            raise ValueError("incomplete GPU reservation data")
        if gpu["total_bytes"] <= 0:
            raise ValueError("invalid GPU capacity")
        if whole:
            available = (gpu["reserved_bytes"] == 0 and gpu["shares"] == 0
                         and gpu["reserved_cores"] == 0)
        else:
            available = (gpu["total_bytes"] - gpu["reserved_bytes"] >= memory
                         and gpu["reserved_cores"] + cores <= 100
                         and gpu["shares"] < share_limit)
        candidates += bool(available)
    return candidates >= count
