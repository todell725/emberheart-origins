"""
CognitiveRouter - Determines which NPC should respond to messages
"""
import logging
import random
from typing import List, Dict, Any, Optional
from .character import CharacterAgent

logger = logging.getLogger(__name__)


class CognitiveRouter:
    """
    Intelligently routes messages to appropriate NPCs
    Uses scoring system to determine who should speak
    """

    def __init__(self, characters: Dict[str, CharacterAgent]):
        """
        Initialize the router

        Args:
            characters: Dictionary mapping character_id -> CharacterAgent
        """
        self.characters = characters
        logger.info(f"CognitiveRouter initialized with {len(characters)} characters")

    def select_speaker(
        self,
        message: str,
        context: Dict[str, Any],
        available_characters: Optional[List[str]] = None,
        allow_multiple: bool = False,
        max_speakers: int = 3
    ) -> List[CharacterAgent]:
        """
        Select which character(s) should respond

        Args:
            message: The message to respond to
            context: Conversation context
            available_characters: List of character IDs that can respond (None = all)
            allow_multiple: Whether multiple NPCs can respond
            max_speakers: Maximum number of NPCs that can respond

        Returns:
            List of CharacterAgent objects that should respond
        """
        if not self.characters:
            logger.warning("No characters available for routing")
            return []

        # Determine which characters are available
        if available_characters:
            candidates = {
                cid: char for cid, char in self.characters.items()
                if cid in available_characters
            }
        else:
            candidates = self.characters

        if not candidates:
            return []

        # Calculate response scores for each character
        scores = {}
        for char_id, character in candidates.items():
            score = character.should_respond(message, context)
            scores[char_id] = score
            logger.debug(f"{character.name} score: {score:.2f}")

        # Sort by score
        sorted_characters = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Select speaker(s)
        if not allow_multiple:
            # Single speaker - weighted random from top candidates
            top_candidates = [
                (char_id, score) for char_id, score in sorted_characters
                if score > 0.15  # Lowered from 0.3
            ]

            if not top_candidates:
                logger.debug("No character met minimum response threshold")
                return []

            # Weighted random selection
            char_id = self._weighted_random_choice(top_candidates)
            selected = [self.characters[char_id]]

        else:
            # Multiple speakers
            selected = []
            for char_id, score in sorted_characters[:max_speakers]:
                if score > 0.15:  # Lowered from 0.2 to be more responsive
                    selected.append(self.characters[char_id])
            
            # If no one met the threshold but we have candidates with at least some relevance,
            # pick the highest scoring one anyway so the player isn't ignored.
            if not selected and sorted_characters and sorted_characters[0][1] >= 0.10:
                selected.append(self.characters[sorted_characters[0][0]])

        logger.info(f"Selected speakers: {[c.name for c in selected]}")
        return selected

    def _weighted_random_choice(self, weighted_items: List[tuple]) -> str:
        """
        Select an item using weighted random selection

        Args:
            weighted_items: List of (item_id, weight) tuples

        Returns:
            Selected item_id
        """
        if not weighted_items:
            raise ValueError("Cannot select from empty list")

        total_weight = sum(weight for _, weight in weighted_items)

        if total_weight <= 0:
            # If all weights are 0 or negative, pick randomly
            return random.choice(weighted_items)[0]

        rand = random.uniform(0, total_weight)
        cumulative = 0

        for item_id, weight in weighted_items:
            cumulative += weight
            if rand <= cumulative:
                return item_id

        # Fallback (shouldn't reach here)
        return weighted_items[0][0]

    def route_multi_response(
        self,
        message: str,
        context: Dict[str, Any],
        num_responses: int = 2
    ) -> List[CharacterAgent]:
        """
        Route a message that expects multiple NPCs to respond

        Args:
            message: The triggering message
            context: Conversation context
            num_responses: Target number of responses

        Returns:
            List of characters that should respond
        """
        return self.select_speaker(
            message,
            context,
            allow_multiple=True,
            max_speakers=num_responses
        )

    def add_character(self, character: CharacterAgent):
        """Add a character to the routing pool"""
        self.characters[character.id] = character
        logger.info(f"Added character to router: {character.name}")

    def remove_character(self, character_id: str):
        """Remove a character from the routing pool"""
        if character_id in self.characters:
            name = self.characters[character_id].name
            del self.characters[character_id]
            logger.info(f"Removed character from router: {name}")
