import os, uuid, torch, logging
from typing import Optional, Callable
from core.config import settings

logger = logging.getLogger(__name__)
_instance = None


class FluxPipeline:

    def __init__(self, pipe):
        self.pipe = pipe

    @classmethod
    def load(cls) -> "FluxPipeline":
        global _instance
        if _instance:
            return _instance

        from diffusers import FluxPipeline as _Flux
        logger.info(f"[FLUX] Loading: {settings.FLUX_MODEL_ID}")
        kwargs = {
            "torch_dtype": torch.bfloat16,
            "cache_dir": settings.MODEL_CACHE_DIR,
        }
        if settings.HF_TOKEN:
            kwargs["token"] = settings.HF_TOKEN

        pipe = _Flux.from_pretrained(
            settings.FLUX_MODEL_ID,
            **kwargs
        )
        if hasattr(pipe, "safety_checker"):
            pipe.safety_checker = None
        if hasattr(pipe, "requires_safety_checker"):
            pipe.requires_safety_checker = False
        pipe.enable_model_cpu_offload()
        _instance = cls(pipe)
        logger.info("[FLUX] Ready.")
        return _instance

    def generate(
        self,
        prompt: str,
        lora_path: Optional[str] = None,
        steps: int = 28,
        cfg_scale: float = 3.5,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        progress_cb: Optional[Callable] = None,
    ) -> str:
        if lora_path and os.path.exists(lora_path):
            try:
                self.pipe.load_lora_weights(lora_path)
            except Exception as e:
                logger.warning(f"[FLUX] LoRA failed: {e}")

        generator = torch.Generator("cpu").manual_seed(seed) if seed else None
        if progress_cb: progress_cb(25)

        result = self.pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=cfg_scale,
            width=width,
            height=height,
            generator=generator,
        )

        if progress_cb: progress_cb(92)
        out = os.path.join(settings.OUTPUT_DIR, f"flux_{uuid.uuid4().hex}.png")
        result.images[0].save(out, quality=95)
        return out
