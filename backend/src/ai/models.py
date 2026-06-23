from pydantic import BaseModel


class Concept(BaseModel):
    """A concept of knowledge. """
    
    name: str
    description: str | None
    embedding: list[float] | None
