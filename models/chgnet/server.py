"""
CHGNet: universal neural network potential with charge distribution.
Returns energy, forces, stress from atomic structure.
API: POST /v1/science/energy — same endpoint as mace-mp-0.
"""
import os, asyncio, json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

MODEL_DIR = os.environ.get("MODEL_DIR", "/data")

app = FastAPI()
model = None
DEVICE = "cpu"

def load():
    global model, DEVICE
    import torch
    from chgnet.model import CHGNet
    from chgnet.model.dynamics import CHGNetCalculator

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading CHGNet on {DEVICE}...", flush=True)

    weight_path = os.path.join(MODEL_DIR, "checkpoint.pth")
    if os.path.exists(weight_path):
        model = CHGNet.from_file(weight_path)
    else:
        model = CHGNet.load()
    model = model.to(DEVICE)
    model.eval()
    print(f"CHGNet ready on {DEVICE}", flush=True)

@app.on_event("startup")
async def startup():
    await asyncio.get_event_loop().run_in_executor(None, load)

@app.get("/health")
async def health():
    return {"status": "ok" if model else "loading", "model": "chgnet", "device": DEVICE}

@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [
        {"id": "chgnet-v0.3", "object": "model", "created": 1700000000,
         "owned_by": "berkeley", "type": "force-field"}
    ]}

@app.post("/v1/science/energy")
async def predict_energy(request: dict):
    if model is None:
        return JSONResponse({"error": "model loading"}, 503)

    struct = request.get("structure")
    if not struct:
        return JSONResponse({"error": "'structure' field required"}, 400)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _predict, struct)
        return result
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse({"error": str(e)}, 500)

def _predict(structure: dict):
    import numpy as np
    from pymatgen.core import Structure, Lattice

    elements = structure.get("elements", [])
    positions = np.array(structure.get("positions", []), dtype=np.float64)
    cell = np.array(structure.get("cell", []), dtype=np.float64) if "cell" in structure else None

    if not elements or len(positions) == 0:
        return JSONResponse({"error": "elements and positions required"}, 400)

    n_atoms = len(elements)

    # Build a pymatgen Structure. If no cell is supplied (molecule), wrap it in a
    # large cubic box so the periodic graph builder has a valid lattice.
    if cell is not None and len(cell) > 0:
        lattice = Lattice(cell)
    else:
        span = float(positions.max() - positions.min()) if len(positions) else 0.0
        lattice = Lattice.cubic(span * 2 + 15.0)

    struct_obj = Structure(
        lattice, elements, positions, coords_are_cartesian=True,
    )

    # Canonical CHGNet inference. predict_structure returns per-atom energy (eV/atom),
    # forces (eV/A), stress (GPa) and magmoms.
    out = model.predict_structure(struct_obj)
    e_per_atom = float(np.asarray(out["e"]).flatten()[0])
    forces = np.asarray(out["f"]).tolist()
    stress = np.asarray(out["s"]).tolist() if "s" in out and out["s"] is not None else None
    magmom = np.asarray(out["m"]).tolist() if "m" in out and out["m"] is not None else None

    result = {
        "model": "chgnet-v0.3",
        "energy_eV": e_per_atom * n_atoms,
        "energy_eV_per_atom": e_per_atom,
        "forces_eV_per_A": forces,
        "n_atoms": n_atoms,
    }
    if stress is not None:
        result["stress_GPa"] = stress
    if magmom is not None:
        result["magmom_muB"] = magmom
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
