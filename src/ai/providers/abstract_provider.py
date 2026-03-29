from abc import ABC, abstractmethod


class AbstractProviderConfig(ABC):
    @abstractmethod
    def from_env(cls):
        """Gets enviromental variables""" 


class AbstractProviderLLMClient(ABC):
    @abstractmethod
    def ainvoke(self, prompt):
        """Makes request for AI response"""


class AbstractProviderEmbedderClient(ABC):
    @abstractmethod
    def ainvoke(self, prompt):
        """Makes request for AI response"""

