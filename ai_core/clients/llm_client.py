import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from .base import BaseLLMClient


class LlamaCppClient(BaseLLMClient):
    def __init__(self, endpoint: str, timeout: int = 120):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def generate(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.endpoint}/completion",
                json={
                    "prompt": prompt,
                    "max_tokens": kwargs.get("max_tokens", 2048),
                    "temperature": kwargs.get("temperature", 0.1),
                    "stop": kwargs.get("stop", []),
                },
            )
            r.raise_for_status()
            return r.json()["content"]


class OpenAICompatClient(BaseLLMClient):
    """llama.cpp /v1/chat/completions 호환 엔드포인트 (ollama 등)"""

    def __init__(self, endpoint: str, model: str, timeout: int = 120):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def generate(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": kwargs.get("max_tokens", 2048),
                    "temperature": kwargs.get("temperature", 0.1),
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
