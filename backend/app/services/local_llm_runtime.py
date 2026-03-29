from dataclasses import dataclass
from threading import Lock
import uuid

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.core.settings import get_settings


@dataclass(frozen=True)
class LocalGenerationResult:
    text: str
    finish_reason: str = "stop"


class LocalLLMRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._lock = Lock()
        self._tokenizer = None
        self._model = None

    def is_ready(self) -> bool:
        return self._tokenizer is not None and self._model is not None

    def get_model_name(self) -> str:
        return self.settings.llm_model

    def generate(
        self,
        prompt: str,
        *,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LocalGenerationResult:
        return self.generate_from_messages(
            [
                {"role": "user", "content": prompt},
            ],
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )

    def generate_from_messages(
        self,
        messages: list[dict[str, str]],
        *,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LocalGenerationResult:
        self._ensure_loaded()
        prompt = self._build_prompt(messages)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        inputs = {
            key: value.to(self.settings.local_llm_device)
            for key, value in inputs.items()
        }
        generation_temperature = (
            float(temperature)
            if temperature is not None
            else float(self.settings.local_llm_temperature)
        )
        generation_max_new_tokens = (
            int(max_new_tokens)
            if max_new_tokens is not None
            else int(self.settings.local_llm_max_new_tokens)
        )
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=generation_max_new_tokens,
            min_new_tokens=1,
            temperature=generation_temperature,
            do_sample=generation_temperature > 0,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        text = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        return LocalGenerationResult(text=text or "未生成到有效输出。")

    def _build_prompt(self, messages: list[dict[str, str]]) -> str:
        if hasattr(self._tokenizer, "apply_chat_template"):
            try:
                return self._tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except Exception:
                pass

        return "\n".join(
            f"{message.get('role', 'user')}: {message.get('content', '')}"
            for message in messages
        )

    def _ensure_loaded(self) -> None:
        if self.is_ready():
            return

        with self._lock:
            if self.is_ready():
                return

            model_path = self.settings.local_llm_model_path
            if not model_path:
                raise ValueError("LOCAL_LLM_MODEL_PATH 未配置，无法加载本地模型。")

            self._tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                local_files_only=True,
            )
            if self._tokenizer.pad_token_id is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            self._model = AutoModelForCausalLM.from_pretrained(
                model_path,
                local_files_only=True,
                dtype=torch.float32,
            )
            self._model.to(self.settings.local_llm_device)
            self._model.eval()

    def build_response_id(self) -> str:
        return f"chatcmpl-{uuid.uuid4().hex[:24]}"
