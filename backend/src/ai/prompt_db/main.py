import sqlite3
from pydantic import BaseModel, Field


class PromptDBConfig(BaseModel):
    db_path: str
    db_url: str
    db_password: str

    hash_prompts: bool = Field(default_factory=False)
    immutability: bool = Field(default_factory=False)


class PromptDB:
    """ Interface for prompt managment database based on SQLite"""
    def __init__(self):
        self.config = None

    def submit(self, filename: str, file: bytes, metadata: dict):
        pass

    def retrieve(self, filename: str, version: str):
        pass

