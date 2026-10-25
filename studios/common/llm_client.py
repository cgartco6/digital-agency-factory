"""Cloud-only LLM wrapper. Never loads local models — CPU-only host safe."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class LLMClient:
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.api_key = api_key or self._resolve_key(self.provider)
        self.offline = not bool(self.api_key)

    @staticmethod
    def _resolve_key(provider: str) -> Optional[str]:
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        if provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        if provider == "replicate":
            return os.getenv("REPLICATE_API_TOKEN")
        return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.4,
    ) -> str:
        if self.offline:
            return self._offline(system, user)

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            if self.provider == "openai":
                return await self._openai(client, system, user, max_tokens, temperature)
            if self.provider == "anthropic":
                return await self._anthropic(
                    client, system, user, max_tokens, temperature
                )
            if self.provider == "replicate":
                return await self._replicate(client, system, user, max_tokens)
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _openai(self, client, system, user, max_tokens, temperature) -> str:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    async def _anthropic(self, client, system, user, max_tokens, temperature) -> str:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()

    async def _replicate(self, client, system, user, max_tokens) -> str:
        resp = await client.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "version": self.model,
                "input": {"prompt": f"{system}\n\n{user}", "max_tokens": max_tokens},
            },
        )
        resp.raise_for_status()
        return json.dumps(resp.json())

    @staticmethod
    def _offline(system: str, user: str) -> str:
        """Deterministic payload — lets the swarm + tests run airgapped."""
        digest = hashlib.sha256((system + user).encode()).hexdigest()[:12]
        return json.dumps(
            {
                "engine": "offline-deterministic",
                "digest": digest,
                "summary": "Deterministic generation engaged; no cloud credentials present.",
                "payload": {"seed": digest},
            },
            indent=2,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "offline_mode": self.offline,
        }
