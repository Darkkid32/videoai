"""
Prompt Optimizer — domain-aware, engine-aware prompt enhancement.
Appends style tokens, quality boosters, and character context
to maximize output quality per engine and content domain.
"""
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from db.models import Character

# Domain-specific style tokens
DOMAIN_TOKENS = {
    "cinematic": (
        "cinematic quality, anamorphic lens, film grain, shallow depth of field, "
        "dramatic lighting, professional color grading, 4K resolution, "
        "motion blur, bokeh, epic cinematography"
    ),
    "influencer": (
        "high-definition, natural lighting, lifestyle photography style, "
        "vibrant colors, clean background, professional video quality, "
        "social media optimized, sharp focus, authentic atmosphere"
    ),
    "general": (
        "high quality, sharp focus, detailed, well-composed, professional"
    ),
}

# Engine-specific quality boosters
ENGINE_TOKENS = {
    "wan": "smooth motion, temporal consistency, high framerate, realistic movement",
    "cogvideo": "coherent motion, scene consistency, fluid transitions",
    "flux": "ultra-detailed, photorealistic, masterpiece, best quality",
}

# Generic quality suffix
QUALITY_SUFFIX = "high quality, no artifacts, no watermarks"

# Default negative prompts per domain
NEGATIVE_TOKENS = {
    "cinematic":  "low quality, blurry, shaky camera, overexposed, flat lighting, amateur",
    "influencer": "low quality, blurry, poor lighting, unflattering, dark, noisy",
    "general":    "low quality, blurry, distorted, artifacts, watermark",
}


class PromptOptimizer:

    def optimize(
        self,
        prompt: str,
        domain: str = "general",
        engine: str = "wan",
        character: Optional["Character"] = None,
        style_prompt: Optional[str] = None,
    ) -> str:
        parts = [prompt.strip()]

        # Inject character description if provided
        if character:
            char_desc = f"featuring {character.name}, {character.description}"
            if character.style_tags:
                char_desc += ", " + ", ".join(character.style_tags)
            parts.append(char_desc)

        # Domain tokens
        domain_tok = DOMAIN_TOKENS.get(domain, DOMAIN_TOKENS["general"])
        parts.append(domain_tok)

        # Engine tokens
        engine_tok = ENGINE_TOKENS.get(engine, "")
        if engine_tok:
            parts.append(engine_tok)

        # Custom style
        if style_prompt:
            parts.append(style_prompt.strip())

        # Quality suffix
        parts.append(QUALITY_SUFFIX)

        return ", ".join(p for p in parts if p)

    def get_default_negative(self, domain: str = "general") -> str:
        return NEGATIVE_TOKENS.get(domain, NEGATIVE_TOKENS["general"])
