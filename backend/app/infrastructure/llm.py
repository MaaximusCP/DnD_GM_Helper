from abc import ABC, abstractmethod

import httpx

from app.domain.models import ChatMessage, NPC


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def chat(self, system_prompt: str, message: str, history: list[ChatMessage]) -> str:
        raise NotImplementedError


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, npc: NPC):
        self.npc = npc

    async def chat(self, system_prompt: str, message: str, history: list[ChatMessage]) -> str:
        goal = self.npc.goals[0] if self.npc.goals else "observar la situació"
        if self.npc.relationship.trust >= 30:
            tone = "Us escolto; fins ara heu demostrat que puc confiar una mica en vosaltres."
        elif self.npc.relationship.trust < 0:
            tone = "Parleu, però no espereu que confiï en la vostra paraula."
        else:
            tone = "Us escolto, però seré prudent."
        return f"{tone} Ara mateix la meva prioritat és {goal}. Què proposeu exactament?"


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, system_prompt: str, message: str, history: list[ChatMessage]) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(item.model_dump() for item in history[-12:])
        messages.append({"role": "user", "content": message})
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            return response.json()["message"]["content"]


class LMStudioProvider(LLMProvider):
    name = "lmstudio"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, system_prompt: str, message: str, history: list[ChatMessage]) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(item.model_dump() for item in history[-12:])
        messages.append({"role": "user", "content": message})
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={"model": self.model, "messages": messages, "temperature": 0.7},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


def create_provider(name: str, base_url: str, model: str, npc: NPC) -> LLMProvider:
    providers = {
        "mock": lambda: MockProvider(npc),
        "ollama": lambda: OllamaProvider(base_url, model),
        "lmstudio": lambda: LMStudioProvider(base_url, model),
    }
    try:
        return providers[name.lower()]()
    except KeyError as exc:
        raise ValueError(f"Proveïdor LLM no compatible: {name}") from exc

