import os, uuid, torch, logging
from typing import Optional, Callable
from core.config import settings

logger = logging.getLogger(__name__)
_instance = None


class WanPipeline:

    def __init__(self, pipe_t2v, pipe_i2v=None):
        self.pipe_t2v = pipe_t2v
        self.pipe_i2v = pipe_i2v

    @classmethod
    def load(cls) -> "WanPipeline":
        global _instance
        if _instance:
            return _instance

        from diffusers import WanPipeline as _T2V, WanImageToVideoPipeline
        dtype = torch.bfloat16

        logger.info(f"[Wan] Loading T2V: {settings.WAN_MODEL_ID}")
        kwargs = {
            "torch_dtype": dtype,
            "cache_dir": settings.MODEL_CACHE_DIR,
        }
        if settings.HF_TOKEN:
            kwargs["token"] = settings.HF_TOKEN

        pipe = _T2V.from_pretrained(
            settings.WAN_MODEL_ID,
            **kwargs
        )
        if hasattr(pipe, "safety_checker"):
            pipe.safety_checker = None
        if hasattr(pipe, "requires_safety_checker"):
            pipe.requires_safety_checker = False
        if settings.COLAB_T4_MODE:
            pipe.to("cuda", dtype)
            logger.info("[Wan] Loaded entirely to GPU (T4 mode)")
        else:
            pipe.enable_model_cpu_offload()

        pipe_i2v = None
        if not settings.COLAB_T4_MODE and settings.WAN_I2V_MODEL_ID:
            try:
                logger.info(f"[Wan] Loading I2V: {settings.WAN_I2V_MODEL_ID}")
                pipe_i2v = WanImageToVideoPipeline.from_pretrained(
                    settings.WAN_I2V_MODEL_ID,
                    **kwargs
                )
                if hasattr(pipe_i2v, "safety_checker"):
                    pipe_i2v.safety_checker = None
                if hasattr(pipe_i2v, "requires_safety_checker"):
                    pipe_i2v.requires_safety_checker = False
                pipe_i2v.enable_model_cpu_offload()
            except Exception as e:
                logger.warning(f"[Wan] I2V not loaded: {e}")
        else:
            logger.info("[Wan] I2V loading skipped (T4 mode or no model ID)")

        _instance = cls(pipe, pipe_i2v)
        logger.info("[Wan] Ready.")
        return _instance

    def _load_lora(self, pipe, lora_path: Optional[str]):
        if not lora_path or not os.path.exists(lora_path):
            return
        try:
            pipe.load_lora_weights(lora_path)
            logger.info(f"[Wan] LoRA loaded: {lora_path}")
        except Exception as e:
            logger.warning(f"[Wan] LoRA load failed: {e}")

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        mode: str = "t2v",
        input_image_url: Optional[str] = None,
        lora_path: Optional[str] = None,
        steps: int = 50,
        cfg_scale: float = 5.0,
        width: int = 832,
        height: int = 480,
        num_frames: int = 81,
        fps: int = 16,
        seed: Optional[int] = None,
        progress_cb: Optional[Callable] = None,
    ) -> str:
        from diffusers.utils import export_to_video
        from PIL import Image
        import requests
        from io import BytesIO

        generator = torch.Generator("cpu").manual_seed(seed) if seed else None

        if mode == "i2v" and self.pipe_i2v and input_image_url:
            self._load_lora(self.pipe_i2v, lora_path)
            if input_image_url.startswith("http"):
                img = Image.open(BytesIO(requests.get(input_image_url, timeout=15).content)).convert("RGB")
            else:
                img = Image.open(input_image_url.lstrip("/")).convert("RGB")
            img = img.resize((width, height))
            if progress_cb: progress_cb(30)
            result = self.pipe_i2v(
                image=img, prompt=prompt, negative_prompt=negative_prompt,
                num_inference_steps=steps, guidance_scale=cfg_scale,
                num_frames=num_frames, generator=generator,
            )
        else:
            self._load_lora(self.pipe_t2v, lora_path)
            if progress_cb: progress_cb(30)
            result = self.pipe_t2v(
                prompt=prompt, negative_prompt=negative_prompt,
                num_inference_steps=steps, guidance_scale=cfg_scale,
                width=width, height=height, num_frames=num_frames, generator=generator,
            )

        if progress_cb: progress_cb(90)
        out = os.path.join(settings.OUTPUT_DIR, f"wan_{uuid.uuid4().hex}.mp4")
        export_to_video(result.frames[0], out, fps=fps)
        return out
