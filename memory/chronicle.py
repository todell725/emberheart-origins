"""
Chronicle - Memory and context management system
Uses BM25 for retrieval-augmented generation (RAG)
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory/event in the Chronicle"""
    timestamp: str
    category: str  # "dialogue", "event", "quest", "combat", etc.
    content: str
    characters: List[str]  # Character IDs involved
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryEntry':
        return cls(**data)


class Chronicle:
    """
    Long-term memory system for the game world
    Stores and retrieves contextual information using BM25
    """

    def __init__(self, storage_path: str = "state/chronicle.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.memories: List[MemoryEntry] = []
        self.bm25: Optional[BM25Okapi] = None
        self.tokenized_corpus: List[List[str]] = []

        self._load()
        logger.info(f"Chronicle initialized with {len(self.memories)} memories")

    def remember(
        self,
        content: str,
        category: str = "general",
        characters: Optional[List[str]] = None,
        location: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """
        Store a new memory in the Chronicle

        Args:
            content: The text content of the memory
            category: Type of memory (dialogue, event, quest, etc.)
            characters: List of character IDs involved
            location: Where this took place
            metadata: Additional structured data

        Returns:
            The created MemoryEntry
        """
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            category=category,
            content=content,
            characters=characters or [],
            location=location,
            metadata=metadata or {}
        )

        self.memories.append(entry)
        self._rebuild_index()
        self._save()

        logger.debug(f"Remembered [{category}]: {content[:50]}...")
        return entry

    def recall(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        character_id: Optional[str] = None
    ) -> List[MemoryEntry]:
        """
        Retrieve relevant memories using BM25 search

        Args:
            query: Search query
            top_k: Number of results to return
            category: Filter by category
            character_id: Filter by character involvement

        Returns:
            List of relevant MemoryEntry objects
        """
        if not self.memories:
            return []

        # Filter memories by category/character if specified
        filtered_memories = self.memories
        if category:
            filtered_memories = [m for m in filtered_memories if m.category == category]
        if character_id:
            filtered_memories = [m for m in filtered_memories if character_id in m.characters]

        if not filtered_memories:
            return []

        # Rebuild index if filtering was applied
        if category or character_id:
            corpus = [self._tokenize(m.content) for m in filtered_memories]
            bm25 = BM25Okapi(corpus)
        else:
            bm25 = self.bm25
            filtered_memories = self.memories

        # Search
        tokenized_query = self._tokenize(query)
        scores = bm25.get_scores(tokenized_query)

        # Get top K indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = [filtered_memories[i] for i in top_indices if scores[i] > 0]

        logger.debug(f"Recalled {len(results)} memories for query: {query[:30]}...")
        return results

    def get_recent(self, n: int = 10, category: Optional[str] = None) -> List[MemoryEntry]:
        """Get the N most recent memories"""
        memories = self.memories
        if category:
            memories = [m for m in memories if m.category == category]
        return list(reversed(memories[-n:]))

    def get_character_context(self, character_id: str, limit: int = 20) -> List[MemoryEntry]:
        """Get memories involving a specific character"""
        character_memories = [m for m in self.memories if character_id in m.characters]
        return list(reversed(character_memories[-limit:]))

    def clear_category(self, category: str):
        """Remove all memories of a specific category"""
        original_count = len(self.memories)
        self.memories = [m for m in self.memories if m.category != category]
        removed = original_count - len(self.memories)

        if removed > 0:
            self._rebuild_index()
            self._save()
            logger.info(f"Cleared {removed} memories from category '{category}'")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        return text.lower().split()

    def _rebuild_index(self):
        """Rebuild the BM25 index from current memories"""
        if not self.memories:
            self.bm25 = None
            self.tokenized_corpus = []
            return

        self.tokenized_corpus = [self._tokenize(m.content) for m in self.memories]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def _save(self):
        """Persist memories to disk"""
        data = {
            "version": "1.0",
            "memories": [m.to_dict() for m in self.memories]
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self):
        """Load memories from disk"""
        if not self.storage_path.exists():
            logger.info("No existing chronicle found, starting fresh")
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.memories = [MemoryEntry.from_dict(m) for m in data.get("memories", [])]
            self._rebuild_index()

            logger.info(f"Loaded {len(self.memories)} memories from {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to load chronicle: {e}")
            self.memories = []
