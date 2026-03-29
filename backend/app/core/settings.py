from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    small_model_enabled: bool
    small_model_endpoint: str
    small_model_timeout: float
    foundation_model_enabled: bool
    foundation_model_base_url: str
    foundation_model_name: str
    foundation_model_api_key: str
    foundation_model_timeout: float
    foundation_model_max_tokens: float
    llm_enabled: bool
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    llm_timeout: float
    local_llm_model_path: str
    local_llm_device: str
    local_llm_max_new_tokens: float
    local_llm_temperature: float


def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        small_model_enabled=_get_bool("SMALL_MODEL_ENABLED", False),
        small_model_endpoint=os.getenv("SMALL_MODEL_ENDPOINT", "http://127.0.0.1:9001/predict"),
        small_model_timeout=_get_float("SMALL_MODEL_TIMEOUT", 10.0),
        foundation_model_enabled=_get_bool("FOUNDATION_MODEL_ENABLED", False),
        foundation_model_base_url=os.getenv("FOUNDATION_MODEL_BASE_URL", "http://127.0.0.1:11434/v1"),
        foundation_model_name=os.getenv("FOUNDATION_MODEL_NAME", "qwen2.5:7b-instruct"),
        foundation_model_api_key=os.getenv("FOUNDATION_MODEL_API_KEY", "EMPTY"),
        foundation_model_timeout=_get_float("FOUNDATION_MODEL_TIMEOUT", 25.0),
        foundation_model_max_tokens=_get_float("FOUNDATION_MODEL_MAX_TOKENS", 160.0),
        llm_enabled=_get_bool("LLM_ENABLED", False),
        llm_base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
        llm_model=os.getenv("LLM_MODEL", "qwen2.5:7b-instruct"),
        llm_api_key=os.getenv("LLM_API_KEY", "EMPTY"),
        llm_timeout=_get_float("LLM_TIMEOUT", 20.0),
        local_llm_model_path=os.getenv("LOCAL_LLM_MODEL_PATH", ""),
        local_llm_device=os.getenv("LOCAL_LLM_DEVICE", "cpu"),
        local_llm_max_new_tokens=_get_float("LOCAL_LLM_MAX_NEW_TOKENS", 96.0),
        local_llm_temperature=_get_float("LOCAL_LLM_TEMPERATURE", 0.2),
    )
