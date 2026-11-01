"""Pasarela de modelos: interfaz desacoplada para modelos locales o remotos (configurable por entorno).

Soporta cualquier servicio con API compatible con ``/chat/completions``
(Ollama, llama.cpp, vLLM, OpenAI, etc.). Sin configuración -> ``NotConfiguredProvider``,
que lanza un error controlado: NUNCA se fabrica una respuesta.
La clave API solo se lee en el servidor y jamás se devuelve ni se registra.
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol, Sequence

from ai.settings import Settings
from ai.errors import EmptyProviderResponse, ProviderError, ProviderNotConfigured, ProviderTimeout


@dataclass(frozen=True)
class ProviderResult:
    text: str
    model: str
    provider: str


class AIProvider(Protocol):
    name: str

    def generate(self, messages: Sequence[dict], max_tokens: int) -> ProviderResult: ...


class NotConfiguredProvider:
    name = "none"
    configured = False

    def generate(self, messages, max_tokens):
        raise ProviderNotConfigured(
            "No hay proveedor de IA configurado. Defina PACHAADAPT_AI_PROVIDER, "
            "PACHAADAPT_AI_BASE_URL y PACHAADAPT_AI_MODEL (ver GUIA_EJECUCION.md)."
        )


class OpenAICompatibleProvider:
    name = "openai_compatible"
    configured = True

    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 30.0):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("PACHAADAPT_AI_BASE_URL debe empezar por http:// o https://")
        if not model:
            raise ValueError("PACHAADAPT_AI_MODEL es obligatorio")
        self.base_url, self.model, self._api_key, self.timeout = base_url.rstrip("/"), model, api_key, timeout

    def generate(self, messages: Sequence[dict], max_tokens: int) -> ProviderResult:
        body = json.dumps({"model": self.model, "messages": list(messages),
                           "max_tokens": max_tokens, "temperature": 0.3}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise ProviderError(f"El proveedor de IA respondió con HTTP {e.code}.", upstream_status=e.code) from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                raise ProviderTimeout("El proveedor de IA no respondió a tiempo.") from None
            raise ProviderError("No se pudo conectar con el proveedor de IA.") from None
        except (TimeoutError, socket.timeout):
            raise ProviderTimeout("El proveedor de IA no respondió a tiempo.") from None
        except OSError:
            raise ProviderError("Error de red con el proveedor de IA.") from None
        try:
            data = json.loads(raw)
            text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderError("Respuesta del proveedor de IA con formato inesperado.") from None
        if not isinstance(text, str) or not text.strip():
            raise EmptyProviderResponse("El proveedor de IA devolvió una respuesta vacía.")
        return ProviderResult(text=text.strip(), model=str(data.get("model") or self.model), provider=self.name)


def build_provider(settings: Settings):
    if settings.ai_provider == "openai_compatible" and settings.ai_base_url and settings.ai_model:
        return OpenAICompatibleProvider(settings.ai_base_url, settings.ai_model,
                                        settings.ai_api_key, settings.ai_timeout)
    return NotConfiguredProvider()
