from abc import ABC, abstractmethod


class AbstractProviderLLMClient(ABC):
    @abstractmethod
    async def ainvoke(self, prompt):
        """Makes request for AI response"""
        pass


class AbstractProviderEmbedderClient(ABC):
    @abstractmethod
    async def embed(self, text):
        """Makes request for AI response"""
        pass

