from typing import List, Dict
from pydantic import BaseModel, Field


class Placeholder(BaseModel):
    """Placeholder definition with description and example."""
    name: str = Field(
        description="Unique name for the placeholder, normalized to <placeholder_name>"
    )
    description: str = Field(
        description="Description of the placeholder's purpose"
    )
    example: str = Field(
        description="Example placeholder value in United States English"
    )

class PlaceholderCandidate(BaseModel):
    """Potential placeholder candidates for a conversation seed."""
    selected_placeholders: List[str] = Field(
        description="List of placeholder names selected from the provided "
                    "placeholder list"
    )
    added_placeholders: List[Placeholder] = Field(
        description="List of new placeholders proposed by the LLM, each with "
                    "a name, description, and example"
    )
