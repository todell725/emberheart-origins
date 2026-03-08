"""
Data models for EmberHeart: Origins
Ported from Claudes-EmberHeart (simplified to avoid pydantic dependency)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class CharacterProfile:
    """Static lore and profile data for a character."""
    id: str
    name: str
    race: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    bio: Optional[str] = None
    motivation: Optional[str] = None
    secret: Optional[str] = None


@dataclass
class CharacterState:
    """Dynamic runtime state for a character."""
    id: str
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    gold: int = 0
    inventory: Dict[str, int] = field(default_factory=dict)
    equipped_weapon: Optional[str] = None
    equipped_armor: Optional[str] = None
    status_effects: List[str] = field(default_factory=list)
    location: Optional[str] = None


@dataclass
class QuestRecord:
    """State for an active or completed quest."""
    id: str
    title: str
    description: str
    status: str = "active"  # 'active', 'completed', or 'failed'
    giver_id: Optional[str] = None
    objectives: List[str] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationTurn:
    """A single dialogue or narrative exchange."""
    speaker: str
    content: str
    speaker_id: Optional[str] = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
