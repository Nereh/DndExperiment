from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class OllamaClient:
    """Minimal HTTP client for an Ollama server."""

    base_url: str = "http://localhost:11434"
    timeout: int = 30

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        stream: bool = False,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Call the /api/generate endpoint.

        Returns the JSON response as a dict. For a richer client you might want to
        support streaming and typed responses.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if extra_params:
            payload.update(extra_params)

        resp = requests.post(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        js = resp.json()
        response = js.get("response") or ""
        return response
