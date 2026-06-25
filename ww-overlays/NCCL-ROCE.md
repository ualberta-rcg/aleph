# NCCL over RoCE on Aleph GPU workers

This documents how to make NCCL collectives run over the GPU nodes' RoCE NICs
(Broadcom `bnxt_re`) instead of falling back to TCP sockets, and why it does not
"just work" out of the box.

## TL;DR

Three things are required, in order:

1. **Node modules** (gpu-worker overlay): `ib_uverbs`, `ib_umad`, `rdma_cm`,
   `rdma_ucm` loaded at boot — `overlays/gpu-worker/etc/modules-load.d/rdma.conf`.
   (`bnxt_re` auto-loads with `bnxt_en`.)
2. **Device plugin** (control-plane overlay): `70-rdma-device-plugin.yaml`
   advertises `rdma/roce` on `gpu=on` nodes and injects `/dev/infiniband` into
   pods that request it.
3. **Container userspace provider**: the pod must use the host's Broadcom verbs
   provider (`libbnxt_re`), because the inbox/upstream rdma-core provider that
   ships in most images is too old for the host kernel driver ABI. Without this
   NCCL logs `NET/IB : No device found` and silently uses TCP.

Intra-node NCCL (single node, tensor-parallel within one host) already works
fine over shared memory without any of this. RoCE matters for **multi-node**
collectives (a model sharded across both GPU nodes), and for forcing the network
path when you want RDMA throughput.

## Root cause (what we observed on the cluster)

A 2-GPU all-reduce with `rdma/roce` requested but no provider fix:

```
libibverbs: Warning: Driver bnxt_re does not support the kernel ABI of 8
            (supports 1 to 1) for device /sys/class/infiniband/bnxt_re0
NCCL INFO NET/IB : No device found.
NCCL INFO Channel 00/0 : 0[0] -> 1[1] via NET/Socket/0      <-- TCP fallback
```

The GPU hosts run Broadcom's **out-of-tree** driver stack:

- kernel module `bnxt_re` (DKMS) version `236.x` → exports verbs **ABI 8**
- matching userspace `libbnxt_re` (`bnxt-rocelib`) installed under
  `/usr/local/lib/x86_64-linux-gnu/` and registered via
  `/etc/ld.so.conf.d/libbnxt_re.conf`
- on the host, `ibv_devinfo` shows `bnxt_re0  PORT_ACTIVE  link_layer Ethernet`

Containers ship the **inbox** provider `libbnxt_re-rdmav34.so` from rdma-core,
which only speaks **ABI 1**. So even with the device injected, libibverbs refuses
to open it and NCCL has no RDMA device → TCP.

The fix is to put the host's matching Broadcom provider in front of the
container's inbox one.

## Per-pod recipe (proven on vLLM image)

After applying this, the same all-reduce reports:

```
NET/IB : Using [0]bnxt_re0:1/RoCE [RO]; OOB eth0
Channel 00/0 : 0[0] -> 1[1] via NET/IB/0                    <-- RoCE
```

Add to the pod / KServe predictor `podSpec`:

```yaml
spec:
  containers:
    - name: <your-container>            # for KServe ISVC use: kserve-container
      securityContext:
        capabilities:
          add: ["IPC_LOCK"]            # RDMA memory registration (memlock)
      env:
        - { name: NCCL_IB_HCA,         value: "bnxt_re0" }
        - { name: NCCL_IB_GID_INDEX,   value: "3" }        # RoCEv2 GID
        - { name: NCCL_SOCKET_IFNAME,  value: "eth0" }     # OOB / bootstrap NIC
        - { name: NCCL_IB_DISABLE,     value: "0" }
        # Optional, only to FORCE the IB path for testing on a single node:
        # - { name: NCCL_P2P_DISABLE,  value: "1" }
        # - { name: NCCL_SHM_DISABLE,  value: "1" }
        - { name: LD_LIBRARY_PATH,     value: "/opt/bnxt:/usr/local/nvidia/lib64" }
      resources:
        limits:
          rdma/roce: "1"
      volumeMounts:
        # Override the container's inbox provider with the host Broadcom one.
        - name: bnxt-provider
          mountPath: /usr/lib/x86_64-linux-gnu/libibverbs/libbnxt_re-rdmav34.so
          subPath: libbnxt_re-rdmav34.so
        # Provider's runtime deps (libbnxt_re.so) — put on LD_LIBRARY_PATH above.
        - name: bnxt-usrlocal
          mountPath: /opt/bnxt
        - name: ibverbs-driver
          mountPath: /etc/libibverbs.d/bnxt_re.driver
          subPath: bnxt_re.driver
  volumes:
    - name: bnxt-provider
      hostPath: { path: /usr/lib/x86_64-linux-gnu, type: Directory }
    - name: bnxt-usrlocal
      hostPath: { path: /usr/local/lib/x86_64-linux-gnu, type: Directory }
    - name: ibverbs-driver
      hostPath: { path: /etc/libibverbs.d, type: Directory }
```

Notes:

- The provider `.so` is built against the host's rdma-core (v50, Ubuntu 24.04).
  Images based on Ubuntu 24.04 (vLLM, recent PyTorch) load it cleanly. Much older
  base images may have an incompatible `libibverbs` and need rebuilding instead.
- `NCCL_IB_GID_INDEX=3` selects the RoCEv2 GID on these NICs. If a future image
  enumerates GIDs differently, check `show_gids` on the host and adjust.
- This is a runtime injection — no image rebuild required. The clean long-term
  alternative is to bake `bnxt-rocelib` into the serving images and drop the
  hostPath mounts; pin it to the host driver version so the ABI stays matched.

## Verifying

Quick device check from any pod that requests `rdma/roce` and has the provider
injected:

```bash
ibv_devinfo -d bnxt_re0    # expect: PORT_ACTIVE, link_layer Ethernet
```

NCCL transport check — look for `via NET/IB` (good) vs `via NET/Socket`
(fallback) with `NCCL_DEBUG=INFO`.
