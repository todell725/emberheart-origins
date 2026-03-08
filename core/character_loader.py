"""
Unified Character Loader for EmberHeart: Origins
Loads characters from both YAML (simple format) and JSON (full D&D stats)
"""
import logging
from pathlib import Path
from typing import Dict, Optional
import yaml

from agents.character import CharacterAgent, CharacterPersonality
from core.storage import load_character_profile, load_character_state, get_character_dir

logger = logging.getLogger(__name__)


class UnifiedCharacterLoader:
    """Loads characters from both YAML and JSON formats"""

    def __init__(self, llm_client, chronicle):
        self.llm = llm_client
        self.chronicle = chronicle

    def load_all_characters(self) -> Dict[str, CharacterAgent]:
        """
        Load all characters from:
        - characters/*.yaml (simple YAML format)
        - characters/npcs/*/ (JSON profile + state format)

        Returns dict mapping character_id -> CharacterAgent
        """
        characters = {}

        # Load YAML characters
        yaml_chars = self._load_yaml_characters()
        characters.update(yaml_chars)
        logger.info(f"Loaded {len(yaml_chars)} YAML characters")

        # Load JSON characters
        json_chars = self._load_json_characters()
        characters.update(json_chars)
        logger.info(f"Loaded {len(json_chars)} JSON characters")

        logger.info(f"Total characters loaded: {len(characters)}")
        return characters

    def _load_yaml_characters(self) -> Dict[str, CharacterAgent]:
        """Load characters from YAML files"""
        characters = {}
        yaml_dir = Path("characters")

        if not yaml_dir.exists():
            logger.warning(f"YAML directory not found: {yaml_dir}")
            return characters

        for yaml_file in yaml_dir.glob("*.yaml"):
            try:
                character = CharacterAgent(
                    personality_file=str(yaml_file),
                    llm_client=self.llm,
                    chronicle=self.chronicle
                )
                characters[character.id] = character
                logger.debug(f"Loaded YAML: {character.name} ({character.id})")
            except Exception as e:
                logger.error(f"Failed to load YAML {yaml_file}: {e}")

        return characters

    def _load_json_characters(self) -> Dict[str, CharacterAgent]:
        """Load characters from JSON profile + state format"""
        characters = {}
        npc_dir = Path("characters/npcs")

        if not npc_dir.exists():
            logger.warning(f"JSON NPC directory not found: {npc_dir}")
            return characters

        for char_dir in npc_dir.iterdir():
            if not char_dir.is_dir():
                continue

            # Extract ID from directory name (e.g., "PC-04_Mareth" → "PC-04")
            char_id = char_dir.name.split("_")[0]

            try:
                # Load profile and state
                profile_data = load_character_profile(char_id)
                state_data = load_character_state(char_id)

                if not profile_data:
                    logger.warning(f"No profile found for {char_id}")
                    continue

                # Convert to CharacterAgent
                character = self._json_to_character_agent(char_id, profile_data, state_data)
                characters[char_id] = character
                logger.debug(f"Loaded JSON: {character.name} ({char_id})")

            except Exception as e:
                logger.error(f"Failed to load JSON {char_id}: {e}")

        return characters

    def _json_to_character_agent(
        self,
        char_id: str,
        profile: dict,
        state: dict
    ) -> CharacterAgent:
        """
        Convert JSON profile + state into CharacterAgent
        Creates a pseudo-YAML personality structure
        """
        # Build personality from JSON data
        personality = CharacterPersonality(
            name=profile.get("name", char_id),
            id=char_id,
            archetype=self._build_archetype(profile),
            speech_patterns=self._infer_speech_patterns(profile),
            relationships={},  # TODO: Extract from JSON if available
            quirks=self._infer_quirks(profile, state),
            backstory=profile.get("bio", ""),
            avatar_url=profile.get("avatar_url")
        )

        # Create character agent
        character = CharacterAgent.__new__(CharacterAgent)
        character.llm = self.llm
        character.chronicle = self.chronicle
        character.model = None
        character.personality = personality
        character.emotional_state = {"mood": "neutral", "energy": 0.5}

        # Attach JSON state for reference
        character.json_profile = profile
        character.json_state = state

        # Expose domains for council filtering
        character.domains = profile.get("domains", [])

        return character

    def _build_archetype(self, profile: dict) -> str:
        """Build archetype string from JSON profile"""
        race = profile.get("race", "Unknown")
        char_class = profile.get("class", "Unknown")
        role = profile.get("role", "")

        if role:
            return f"{race} {char_class} ({role})"
        return f"{race} {char_class}"

    def _infer_speech_patterns(self, profile: dict) -> list:
        """Infer speech patterns from character data"""
        patterns = []

        # Based on class
        char_class = profile.get("class", "").lower()
        if "fighter" in char_class or "warrior" in char_class:
            patterns.append("Direct and tactical speech")
        elif "mage" in char_class or "wizard" in char_class:
            patterns.append("Formal and scholarly language")
        elif "rogue" in char_class:
            patterns.append("Sarcastic and street-smart")
        elif "cleric" in char_class or "priest" in char_class:
            patterns.append("Calm and reassuring tone")

        # Based on alignment
        alignment = profile.get("alignment", "").lower()
        if "lawful" in alignment:
            patterns.append("Speaks with honor and duty")
        elif "chaotic" in alignment:
            patterns.append("Unpredictable and spontaneous")

        # Based on background
        background = profile.get("background", "").lower()
        if "noble" in background:
            patterns.append("Refined and educated speech")
        elif "soldier" in background or "knight" in background:
            patterns.append("Military terminology and discipline")
        elif "criminal" in background:
            patterns.append("Uses slang and coded language")

        # Fallback
        if not patterns:
            patterns.append("Speaks naturally and authentically")

        return patterns

    def _infer_quirks(self, profile: dict, state: dict) -> list:
        """Infer character quirks from data"""
        quirks = []

        # From equipment
        equipment = state.get("status", {}).get("equipment", {})
        main_hand = equipment.get("main_hand", "")
        if "Greatsword" in main_hand:
            quirks.append("Maintains weapon constantly")
        if "Dragon-Bane" in main_hand:
            quirks.append("Driven by vendetta against dragons")

        # From status
        status = state.get("status", {})
        if status.get("dreamfire_active"):
            quirks.append("Touched by mystical fire")
        if status.get("cult_marked"):
            quirks.append("Bears a dark mark")

        # From motivation
        motivation = profile.get("motivation", "")
        if "Redemption" in motivation:
            quirks.append("Seeks to atone for past failures")

        # Fallback
        if not quirks:
            quirks.append("Thoughtful and observant")

        return quirks

    def get_character_stats(self, char_id: str) -> Optional[dict]:
        """Get full JSON stats for a character (if available)"""
        try:
            state = load_character_state(char_id)
            return state
        except:
            return None
