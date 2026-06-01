import os, torch, logging
from typing import Optional, List, Dict
from core.config import settings

logger = logging.getLogger(__name__)
_instance = None

class LLMPipeline:

    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    @classmethod
    def load(cls) -> "LLMPipeline":
        global _instance
        if _instance:
            return _instance

        if not settings.ENABLE_LLM:
            logger.info("LLM is disabled in settings.")
            return None

        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        
        logger.info(f"[LLM] Loading text model: {settings.LLM_MODEL_ID} with 4-bit quantization")
        
        # 4-bit quantization config to save VRAM on Colab
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                settings.LLM_MODEL_ID,
                token=settings.HF_TOKEN if settings.HF_TOKEN else None,
                cache_dir=settings.MODEL_CACHE_DIR,
            )
            
            # Add pad token if missing
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            model = AutoModelForCausalLM.from_pretrained(
                settings.LLM_MODEL_ID,
                quantization_config=quantization_config,
                device_map="auto",
                token=settings.HF_TOKEN if settings.HF_TOKEN else None,
                cache_dir=settings.MODEL_CACHE_DIR,
                low_cpu_mem_usage=True
            )
            
            _instance = cls(model, tokenizer)
            logger.info("[LLM] Ready.")
            return _instance
        except Exception as e:
            logger.error(f"[LLM] Failed to load LLM: {e}")
            return None

    def unload(self):
        """Unload the model to free VRAM for video generation"""
        global _instance
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        torch.cuda.empty_cache()
        _instance = None
        logger.info("[LLM] Model unloaded and VRAM cleared.")

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a response for a given chat history.
        Uses the chat template provided by the tokenizer (crucial for Dolphin/Llama3).
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("LLM not loaded properly.")

        try:
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=True if temperature > 0 else False,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decode only the newly generated tokens
            input_length = inputs["input_ids"].shape[1]
            response = self.tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)
            return response
            
        except Exception as e:
            logger.error(f"[LLM] Error during generation: {e}")
            return f"Error: {e}"
