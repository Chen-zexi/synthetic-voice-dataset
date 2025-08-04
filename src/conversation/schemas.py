"""
Pydantic schemas for structured conversation outputs.

These schemas enable LangChain's with_structured_output functionality
for cleaner and more reliable conversation generation.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class DialogueTurn(BaseModel):
    """A single turn in a conversation."""
    sent_id: int = Field(description="Sequential turn ID starting from 1")
    text: str = Field(description="The dialogue text for this turn")
    role: Literal["caller", "callee"] = Field(description="Speaker role")


class ScamConversationResponse(BaseModel):
    """Structured response for scam conversation generation."""
    dialogue: List[DialogueTurn] = Field(
        description="List of dialogue turns alternating between caller and callee"
    )


class LegitConversationResponse(BaseModel):
    """Structured response for legitimate conversation generation."""
    dialogue: List[DialogueTurn] = Field(
        description="List of dialogue turns for a legitimate phone call"
    )


# Additional schemas for internal use
class ScamConversation(BaseModel):
    """Complete scam conversation with metadata."""
    conversation_id: int
    first_turn: str
    num_turns: int
    victim_awareness: str
    dialogue: List[DialogueTurn]


class LegitConversation(BaseModel):
    """Complete legitimate conversation with metadata."""
    conversation_id: int
    region: str
    category: str
    num_turns: int
    dialogue: List[DialogueTurn]