from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.settings import get_settings


RUNTIME_DIR = Path(__file__).resolve().parents[2] / "runtime"
STATE_FILE = RUNTIME_DIR / "foundation_model_state.json"


@dataclass(frozen=True)
class FoundationModelProfile:
    profile_id: str
    label: str
    provider: str
    base_url: str
    model_name: str
    description: str
    requires_api_key: bool
    api_key_env: str | None = None
    api_key_literal: str | None = None


@dataclass(frozen=True)
class FoundationModelRuntimeConfig:
    profile_id: str
    label: str
    provider: str
    base_url: str
    model_name: str
    api_key: str
    enabled: bool
    configured: bool


class FoundationProfileService:
    def list_profiles(self) -> list[dict[str, object]]:
        active_profile_id = self.get_active_profile_id()
        return [self._to_public_profile(profile, active_profile_id) for profile in self._get_profiles()]

    def activate_profile(self, profile_id: str) -> None:
        if profile_id not in {profile.profile_id for profile in self._get_profiles()}:
            raise ValueError(f"Unknown foundation model profile: {profile_id}")

        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps({"active_profile_id": profile_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_active_profile_id(self) -> str:
        if STATE_FILE.exists():
            try:
                payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                profile_id = str(payload.get("active_profile_id", "")).strip()
                if profile_id:
                    return profile_id
            except json.JSONDecodeError:
                pass

        settings = get_settings()
        return "env-current" if settings.foundation_model_enabled else "foundation-disabled"

    def get_runtime_config(self) -> FoundationModelRuntimeConfig:
        profile_map = {profile.profile_id: profile for profile in self._get_profiles()}
        active_profile = profile_map.get(self.get_active_profile_id(), profile_map["foundation-disabled"])

        if active_profile.profile_id == "foundation-disabled":
            return FoundationModelRuntimeConfig(
                profile_id=active_profile.profile_id,
                label=active_profile.label,
                provider=active_profile.provider,
                base_url="",
                model_name="",
                api_key="",
                enabled=False,
                configured=True,
            )

        api_key = self._resolve_api_key(active_profile)
        configured = bool(active_profile.base_url and active_profile.model_name and (api_key or not active_profile.requires_api_key))

        return FoundationModelRuntimeConfig(
            profile_id=active_profile.profile_id,
            label=active_profile.label,
            provider=active_profile.provider,
            base_url=active_profile.base_url,
            model_name=active_profile.model_name,
            api_key=api_key,
            enabled=configured,
            configured=configured,
        )

    def _to_public_profile(self, profile: FoundationModelProfile, active_profile_id: str) -> dict[str, object]:
        api_key = self._resolve_api_key(profile)
        configured = profile.profile_id == "foundation-disabled" or bool(
            profile.base_url and profile.model_name and (api_key or not profile.requires_api_key)
        )
        return {
            "id": profile.profile_id,
            "label": profile.label,
            "provider": profile.provider,
            "base_url": profile.base_url,
            "model_name": profile.model_name,
            "description": profile.description,
            "requires_api_key": profile.requires_api_key,
            "configured": configured,
            "active": profile.profile_id == active_profile_id,
        }

    def _resolve_api_key(self, profile: FoundationModelProfile) -> str:
        if profile.api_key_literal is not None:
            return profile.api_key_literal
        if profile.api_key_env:
            return os.getenv(profile.api_key_env, "").strip()
        return ""

    def _get_profiles(self) -> list[FoundationModelProfile]:
        settings = get_settings()
        return [
            FoundationModelProfile(
                profile_id="foundation-disabled",
                label="关闭强模型",
                provider="disabled",
                base_url="",
                model_name="",
                description="仅使用规则层和本地解释层，不启用更强大模型研判。",
                requires_api_key=False,
            ),
            FoundationModelProfile(
                profile_id="env-current",
                label="当前环境配置",
                provider="env",
                base_url=settings.foundation_model_base_url,
                model_name=settings.foundation_model_name,
                description="使用 backend/.env 中当前填写的强模型配置。",
                requires_api_key=not self._looks_like_local_endpoint(settings.foundation_model_base_url),
                api_key_literal=settings.foundation_model_api_key,
            ),
            FoundationModelProfile(
                profile_id="ollama-qwen2.5",
                label="Ollama / Qwen2.5 7B",
                provider="ollama",
                base_url="http://127.0.0.1:11434/v1",
                model_name="qwen2.5:7b-instruct",
                description="适合本地部署；需要本机先安装 Ollama 并拉取 qwen2.5 模型。",
                requires_api_key=False,
                api_key_literal="EMPTY",
            ),
            FoundationModelProfile(
                profile_id="ollama-deepseek-r1",
                label="Ollama / DeepSeek-R1 8B",
                provider="ollama",
                base_url="http://127.0.0.1:11434/v1",
                model_name="deepseek-r1:8b",
                description="适合本地更强推理；需要本机先安装 Ollama 并拉取 deepseek-r1:8b。",
                requires_api_key=False,
                api_key_literal="EMPTY",
            ),
            FoundationModelProfile(
                profile_id="deepseek-chat",
                label="DeepSeek Chat",
                provider="deepseek",
                base_url="https://api.deepseek.com/v1",
                model_name="deepseek-chat",
                description="适合在线强模型接入；需要在环境变量中提供 DEEPSEEK_API_KEY。",
                requires_api_key=True,
                api_key_env="DEEPSEEK_API_KEY",
            ),
        ]

    def _looks_like_local_endpoint(self, base_url: str) -> bool:
        return "127.0.0.1" in base_url or "localhost" in base_url


@lru_cache(maxsize=1)
def get_foundation_profile_service() -> FoundationProfileService:
    return FoundationProfileService()
