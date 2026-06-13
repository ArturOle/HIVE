"""Base agent

Agent layer implementing all supporting functionalities of production ready AI Agent:
- logging
- validation
- normalization
- formatting

It separates the supporting code from core business logic of the Agent.

"""


from src.ai_factory.agents.abstract_agent import AbstractAgent
from src.common.logger import logger_setup



class BaseAgent(AbstractAgent):
    """Implements all helper and extension methods"""
    def __init__(self, agent_name: str):
        self.__log = logger_setup(f"{agent_name.capitalize()} logger")



