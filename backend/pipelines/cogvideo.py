import os, uuid, torch, logging
from typing import Optional, Callable
from core.config import settings

logger = logging.getLogger(__name__)
_instance = None


class CogVideoPipeline:

    def __init__(self, pipe):
        self.pipe = pipe

    @classmethod
    def load(cls) -> "CogVideoPipeline":
        global _instance
        if _instance:
            return _instance

        from diffusers import CogVideoXPipeline
        logger.info(f"[CogVideo] Loading: {settings.COGVIDEO_MODEL_ID}")
        pipe = CogVideoXPipeline.from_pretrained(
            settings.COGVIDEO_MODEL_ID,
            torch_dtype=torch.bfloat16,
            cache_dir=settings.MODEL_CACHE_DIR,
        )
        if hasattr(pipe, "safety_checker"):
            pipe.safety_checker = None
        pipe.enable_model_cpu_offload()
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()
        _instance = cls(pipe)
        logger.info("[CogVideo] Ready.")
        return _instance

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        lora_path: Optional[str] = None,
        steps: int = 50,
        cfg_scale: float = 6.0,
        width: int = 720,
        height: int = 480,
        num_frames: int = 49,
        fps: int = 8,
        seed: Optional[int] = None,
        progress_cb: Optional[Callable] = None,
    ) -> str:
        from diffusers.utils import export_to_video

        if lora_path and os.path.exists(lora_path):
            try:
                self.pipe.load_lora_weights(lora_path)
            except Exception as e:
                logger.warning(f"[CogVideo] LoRA failed: {e}")

        generator = torch.Generator("cpu").manual_seed(seed) if seed else None
        if progress_cb: progress_cb(30)

        result = self.pipe(
            prompt=prompt, negative_prompt=negative_prompt,
            num_inference_steps=steps, guidance_scale=cfg_scale,
            width=width, height=height, num_frames=num_frames, generator=generator,
        )

        if progress_cb: progress_cb(90)
        out = os.path.join(settings.OUTPUT_DIR, f"cogvideo_{uuid.uuid4().hex}.mp4")
        export_to_video(result.frames[0], out, fps=fps)
        return out
