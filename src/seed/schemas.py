from typing import List, Dict
from pydantic import BaseModel, Field

class FilteredLines(BaseModel):
    """Filtered lines from the dataset scamGen_20k_sampled."""
    keep_indices: List[int] = Field(
        description="List of 0-based indices of lines to keep from the original dataset"
    )

class SeedRecord(BaseModel):
    type: str = Field(description="Short scam type, e.g., 'tax'")
    summary: str = Field(description="One-sentence summary")
    seed: str = Field(description="Conversation skeleton/description")

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

class PlaceholderSubstitution(BaseModel):
    """Substitution values for a specific placeholder."""
    placeholder_name: str = Field(
        description="Name of the placeholder"
    )
    substitutions: List[str] = Field(
        description="List of realistic substitution values for the placeholder"
    )
    english_translation_substitutions: List[str] = Field(
        description="List of English translations for the substitutions"
    )
