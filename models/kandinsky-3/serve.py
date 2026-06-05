import os, io, base64, time, uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import torch
from ray import serve
from ray.serve.handle import DeploymentHandle

app = FastAPI()

def parse_size(size_str: str):
    try:
        w, h = size_str.lower().split("x")
        return int(w), int(h)
    except Exception:
        return 1024, 1024

def make_response(images_b64: list, model="kandinsky-3"):
    return {
        "created": int(time.time()),
        "data": [{"b64_json": b, "revised_prompt": None} for b in images_b64]
    }

@serve.deployment(num_replicas=1)
@serve.ingress(app)
class APIIngress:
    def __init__(self, model_handle: DeploymentHandle):
        self.handle = model_handle

    @app.get("/v1/models")
    def models(self):
        return {
            "object": "list",
            "data": [{"id": "kandinsky-3", "object": "model", "owned_by": "kandinsky-community"}]
        }

    @app.post("/v1/images/generations")
    async def generate(self, request: dict):
        prompt = request.get("prompt", "")
        negative = request.get("negative_prompt", "")
        n = request.get("n", 1)
        size = request.get("size", "1024x1024")
        width, height = parse_size(size)
        width = request.get("width", width)
        height = request.get("height", height)
        steps = request.get("num_inference_steps", 25)
        guidance = request.get("guidance_scale", 4.0)
        seed = request.get("seed")
        if request.get("quality") == "hd":
            steps = max(steps, 50)

        images_b64 = []
        for i in range(min(n, 4)):
            s = seed + i if seed is not None else None
            img = await self.handle.text2img.remote(
                prompt, negative, steps, guidance, width, height, s
            )
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            images_b64.append(base64.b64encode(buf.getvalue()).decode())
        return JSONResponse(make_response(images_b64))

    @app.post("/v1/images/edits")
    async def edit(self, request: dict):
        prompt = request.get("prompt", "")
        image_b64 = request.get("image", "")
        if image_b64.startswith("data:"):
            image_b64 = image_b64.split(",", 1)[1]
        n = request.get("n", 1)
        size = request.get("size", "1024x1024")
        width, height = parse_size(size)
        width = request.get("width", width)
        height = request.get("height", height)
        steps = request.get("num_inference_steps", 25)
        strength = request.get("strength", 0.75)
        guidance = request.get("guidance_scale", 4.0)
        seed = request.get("seed")
        negative = request.get("negative_prompt", "")

        images_b64 = []
        for i in range(min(n, 4)):
            s = seed + i if seed is not None else None
            img = await self.handle.img2img.remote(
                prompt, negative, image_b64, steps, strength, guidance, width, height, s
            )
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            images_b64.append(base64.b64encode(buf.getvalue()).decode())
        return JSONResponse(make_response(images_b64))

    @app.get("/healthz")
    def health(self):
        return {"status": "ok"}

@serve.deployment(ray_actor_options={"num_gpus": 1})
class Kandinsky3:
    def __init__(self):
        from diffusers import AutoPipelineForText2Image, AutoPipelineForImage2Image
        model_path = os.environ.get("MODEL_DIR", "/mnt/models/kandinsky-3")
        self.t2i = AutoPipelineForText2Image.from_pretrained(
            model_path, variant="fp16", torch_dtype=torch.float16
        )
        self.t2i.enable_model_cpu_offload()
        try:
            self.i2i = AutoPipelineForImage2Image.from_pipe(self.t2i)
        except Exception as e:
            print(f"img2img init failed: {e}")
            self.i2i = None

    def text2img(self, prompt, negative_prompt, steps, guidance, width, height, seed):
        kwargs = dict(prompt=prompt, negative_prompt=negative_prompt,
                      num_inference_steps=steps, guidance_scale=guidance,
                      width=width, height=height)
        if seed is not None:
            kwargs["generator"] = torch.Generator(device="cpu").manual_seed(seed)
        with torch.inference_mode():
            return self.t2i(**kwargs).images[0]

    def img2img(self, prompt, negative_prompt, image_b64, steps, strength, guidance, width, height, seed):
        from PIL import Image
        image = Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
        if self.i2i is None:
            raise RuntimeError("img2img pipeline not available")
        kwargs = dict(prompt=prompt, negative_prompt=negative_prompt,
                      image=image, num_inference_steps=steps,
                      strength=strength, guidance_scale=guidance)
        if seed is not None:
            kwargs["generator"] = torch.Generator(device="cpu").manual_seed(seed)
        with torch.inference_mode():
            return self.i2i(**kwargs).images[0]

entrypoint = APIIngress.bind(Kandinsky3.bind())
