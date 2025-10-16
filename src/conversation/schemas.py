"""
Pydantic schemas for structured conversation outputs.

These schemas enable LangChain's with_structured_output functionality
for cleaner and more reliable conversation generation.
"""

from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field


class DialogueTurn(BaseModel):
    """A single turn in a conversation."""
    text: str = Field(description="The dialogue text for this turn")
    role: Literal["caller", "callee"] = Field(description="Speaker role")


class ScamConversationResponse(BaseModel):
    """Structured response for scam conversation generation."""
    dialogue: List[DialogueTurn] = Field(
        description="List of dialogue turns alternating between caller and callee"
    )


class ScenarioMetadata(BaseModel):
    """Metadata about the scenario used to generate a conversation."""
    scenario_id: str = Field(description="Unique scenario identifier")
    seed_tag: str = Field(description="The scam tag that was used")
    seed_record_id: Optional[int] = Field(default=None, description="Original seed record ID")
    scammer_profile_id: str = Field(description="ID of the scammer character profile")
    victim_profile_id: str = Field(description="ID of the victim character profile")
    locale: str = Field(description="Target locale for the conversation")


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


class ConversationStage(BaseModel):
    """A single stage in a multi-stage conversation generation."""
    stage_name: str = Field(description="Name of the conversation stage")
    stage_turns: int = Field(description="Number of turns in this stage")
    dialogue: List[DialogueTurn] = Field(description="Dialogue turns for this stage")
    context_summary: str = Field(description="Summary of context from this stage")


class MultiStageConversationResponse(BaseModel):
    """Structured response for multi-stage conversation generation."""
    stages: List[ConversationStage] = Field(
        description="List of conversation stages with their dialogue and context"
    )