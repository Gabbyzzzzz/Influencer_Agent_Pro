import os
import asyncio
from abc import ABC, abstractmethod
from google import genai
from utils.logger import get_logger
from config import MAX_CONCURRENT_API

_gemini_client = None


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    name: str = "base"

    def __init__(self):
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_API)
        self.logger = get_logger(self.name)
        self.client = get_gemini_client()

    async def generate(self, prompt: str, model: str = "gemini-2.0-flash") -> str:
        async with self.semaphore:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=prompt,
            )
            return response.text

    @abstractmethod
    async def run(self, brand_requirement: str, **kwargs):
        ...
