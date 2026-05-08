"""
Real OpenAI API Client
=======================
Sends requests directly to the OpenAI REST API using the `requests` library.
No openai SDK — raw HTTP only.

Setup:
    1. Copy .env.example to .env
    2. Add your key:  OPENAI_API_KEY=sk-xxxxxxxxxxxx
    3. Run tests:     pytest tests/real_api/test_openai_api.py -v

The client is also importable from other modules:
    from src.real_api.openai_client import OpenAIChatClient
"""

import os
import time
import requests
from dotenv import load_dotenv

# Load .env automatically (no-op if already loaded or file missing)
load_dotenv()

# ── Constants ─────────────────────────────────────────────────
_BASE_URL    = "https://api.openai.com/v1/chat/completions"
_DEFAULT_MODEL  = "gpt-3.5-turbo"   # cheap, fast, good for testing
_DEFAULT_TOKENS = 200
_DEFAULT_TEMP   = 0.7
_TIMEOUT_SEC    = 30                 # hard timeout per request


class OpenAIClientError(Exception):
    """Raised when the OpenAI API returns a non-2xx status."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message     = message
        super().__init__(f"HTTP {status_code}: {message}")


class OpenAIChatClient:
    """
    Thin wrapper around the OpenAI Chat Completions endpoint.

    Usage:
        client = OpenAIChatClient()
        result = client.chat("What is the capital of France?")
        print(result["response"])   # Paris
    """

    def __init__(self, api_key: str | None = None, model: str = _DEFAULT_MODEL):
        """
        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model:   Model to use. Default: gpt-3.5-turbo.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model   = model

        if not self.api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or export it as an environment variable."
            )

        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

    # ── Public API ─────────────────────────────────────────────

    def chat(
        self,
        message:       str,
        system_prompt: str  = "You are a helpful assistant.",
        max_tokens:    int  = _DEFAULT_TOKENS,
        temperature:   float = _DEFAULT_TEMP,
    ) -> dict:
        """
        Send a user message to GPT and return a structured response dict.

        Returns:
            {
                "response":      str,    # GPT reply text
                "latency_ms":    float,  # round-trip time in milliseconds
                "tokens_used":   int,    # total tokens consumed
                "prompt_tokens": int,    # tokens in the prompt
                "reply_tokens":  int,    # tokens in the reply
                "model":         str,    # model name echoed from API
                "finish_reason": str,    # "stop", "length", etc.
            }

        Raises:
            OpenAIClientError: on any non-2xx HTTP response.
            requests.Timeout:  if the request exceeds _TIMEOUT_SEC seconds.
        """
        payload = {
            "model":       self.model,
            "messages":    [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": message},
            ],
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }

        start = time.monotonic()
        raw   = requests.post(
            _BASE_URL,
            json    = payload,
            headers = self._headers,
            timeout = _TIMEOUT_SEC,
        )
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        if not raw.ok:
            body = raw.json() if raw.headers.get("Content-Type", "").startswith("application/json") else {}
            msg  = body.get("error", {}).get("message", raw.text)
            raise OpenAIClientError(raw.status_code, msg)

        data  = raw.json()
        usage = data.get("usage", {})

        return {
            "response":      data["choices"][0]["message"]["content"].strip(),
            "latency_ms":    latency_ms,
            "tokens_used":   usage.get("total_tokens", 0),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "reply_tokens":  usage.get("completion_tokens", 0),
            "model":         data.get("model", self.model),
            "finish_reason": data["choices"][0].get("finish_reason", ""),
        }

    def is_available(self) -> bool:
        """
        Quick connectivity check — sends a tiny request.
        Returns True if the API key is valid and the endpoint is reachable.
        """
        try:
            self.chat("ping", max_tokens=5)
            return True
        except (OpenAIClientError, requests.RequestException):
            return False


# ── Manual smoke test ─────────────────────────────────────────

if __name__ == "__main__":
    client = OpenAIChatClient()

    prompts = [
        "What is the capital of France?",
        "Explain machine learning in one sentence.",
        "Say hello in Spanish.",
    ]

    for msg in prompts:
        result = client.chat(msg)
        print(f"\nQ: {msg}")
        print(f"A: {result['response']}")
        print(f"   Latency : {result['latency_ms']} ms")
        print(f"   Tokens  : {result['tokens_used']} total "
              f"({result['prompt_tokens']} prompt + {result['reply_tokens']} reply)")