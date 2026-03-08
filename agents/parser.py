"""
NPCResponseParser - Robust parsing of multi-NPC responses with ID tags
**FIXED VERSION** - Handles markdown, paragraphs, and edge cases
"""
import json
import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedResponse:
    """A single parsed NPC response"""
    character_id: str
    character_name: str
    dialogue: str


class NPCResponseParser:
    """
    Multi-stage parser for NPC responses
    Uses layered defense: JSON -> ID tags -> Name patterns -> Fallback

    FIXES APPLIED:
    - Markdown-aware JSON extraction
    - Paragraph-preserving fallback
    - Better error handling
    """

    def __init__(self, npc_registry: Dict[str, Any]):
        """
        Initialize parser

        Args:
            npc_registry: Dictionary mapping character_id -> CharacterAgent
        """
        self.npc_registry = npc_registry
        logger.info(f"Parser initialized with {len(npc_registry)} NPCs")

    def parse(self, llm_output: str) -> List[ParsedResponse]:
        """
        Parse LLM output into individual NPC responses

        Args:
            llm_output: Raw output from LLM

        Returns:
            List of ParsedResponse objects
        """
        # Try parsing methods in order of reliability
        methods = [
            ("JSON format", self._parse_json),
            ("ID tag format", self._parse_id_tags),
            ("Name pattern format", self._parse_name_patterns),
            ("Fallback split", self._parse_fallback)
        ]

        for method_name, method in methods:
            try:
                parsed = method(llm_output)
                if parsed:
                    logger.debug(f"Successfully parsed using: {method_name}")
                    return parsed
            except Exception as e:
                logger.debug(f"{method_name} failed: {e}")
                continue

        # Absolute fallback - return as single DM narration
        logger.warning("All parsing methods failed, returning as single message")
        return [ParsedResponse(
            character_id="dm_narrator",
            character_name="Narrator",
            dialogue=llm_output.strip()
        )]

    def _parse_json(self, output: str) -> Optional[List[ParsedResponse]]:
        """
        Parse JSON format with markdown code block handling:
        [
          {"character_id": "mareth_001", "dialogue": "..."},
          {"character_id": "silvy_003", "dialogue": "..."}
        ]

        Also handles markdown wrapped JSON or loose dictionaries:
        ```json
        [...]
        ```
        """
        json_str = None

        # Try to extract from markdown code block first
        markdown_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', output, re.DOTALL)
        if markdown_match:
            json_str = markdown_match.group(1)
            logger.debug("Found JSON in markdown code block")
        else:
            # Try plain JSON array with tighter matching
            json_match = re.search(r'(\[\s*\{.*?\}\s*\])', output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                logger.debug("Found plain JSON array")
            else:
                # LLM didn't wrap in array brackets, just returned raw dictionaries
                # eg: {"character_id": "X", "dialogue": "Y"}, {"character_id": "A", "dialogue": "B"}
                loose_dicts = re.findall(r'(\{\s*"character_id".*?\})', output, re.DOTALL)
                if loose_dicts:
                    json_str = "[" + ",".join(loose_dicts) + "]"
                    logger.debug("Wrapped loose JSON blocks in array brackets")
                else:
                    # Final attempt: try to recover a truncated JSON string
                    # e.g., if the LLM ran out of tokens mid-string:
                    # [{"character_id": "silvy_003", "dialogue": "Hello...
                    # We look for the last valid "character_id" block and try to close it.
                    truncated_match = re.search(r'(\[\s*\{\s*"character_id".*)', output, re.DOTALL)
                    if truncated_match:
                        raw_trunc = truncated_match.group(1).strip()
                        # If it doesn't end with a bracket, brace, or quote, add a quote
                        if not raw_trunc.endswith(('}', ']', '"')):
                            raw_trunc += '"'
                        
                        # Add closing brace if missing, but only if it's currently open
                        if not raw_trunc.endswith('}'):
                            raw_trunc += "}"
                        
                        # Add closing array bracket
                        if not raw_trunc.endswith(']'):
                            raw_trunc += "]"
                            
                        json_str = raw_trunc
                        logger.debug("Attempted to auto-close truncated JSON syntax")
                    else:
                        return None

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode failed: {e}")
            return None

        if not isinstance(data, list):
            return None

        parsed = []
        for item in data:
            if not isinstance(item, dict):
                continue

            char_id = item.get("character_id")
            dialogue = item.get("dialogue", "")

            if not char_id or not dialogue:
                continue

            # Validate character exists
            if char_id not in self.npc_registry and char_id != "dm_narrator":
                logger.warning(f"Unknown character ID in JSON: {char_id}")
                continue

            char_name = self.npc_registry[char_id].name if char_id in self.npc_registry else "Narrator"

            parsed.append(ParsedResponse(
                character_id=char_id,
                character_name=char_name,
                dialogue=dialogue.strip()
            ))

        return parsed if parsed else None

    def _parse_id_tags(self, output: str) -> Optional[List[ParsedResponse]]:
        """
        Parse formats with explicit ID tags:
        - [mareth_001]: Dialogue here
        - (mareth_001): Dialogue here
        - **Mareth** (mareth_001): Dialogue
        """
        # Build regex pattern from known IDs
        id_pattern = "|".join(re.escape(cid) for cid in self.npc_registry.keys())

        # Pattern variations
        patterns = [
            # [id]: dialogue
            rf"\[({id_pattern})\]:\s*(.+?)(?=\[(?:{id_pattern})\]:|$)",
            # (id): dialogue
            rf"\(({id_pattern})\):\s*(.+?)(?=\((?:{id_pattern})\):|$)",
            # **Name** (id): dialogue
            rf"\*\*\w+\*\*\s*\(({id_pattern})\):\s*(.+?)(?=\*\*\w+\*\*\s*\((?:{id_pattern})\):|$)",
            # Name (id): dialogue
            rf"\w+\s*\(({id_pattern})\):\s*(.+?)(?=\w+\s*\((?:{id_pattern})\):|$)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, output, re.DOTALL | re.MULTILINE)
            parsed = []

            for match in matches:
                char_id = match.group(1)
                dialogue = match.group(2).strip()

                if char_id in self.npc_registry:
                    parsed.append(ParsedResponse(
                        character_id=char_id,
                        character_name=self.npc_registry[char_id].name,
                        dialogue=dialogue
                    ))

            if parsed:
                return parsed

        return None

    def _parse_name_patterns(self, output: str) -> Optional[List[ParsedResponse]]:
        """
        Parse by character names (less reliable):
        Mareth: Dialogue here
        Silvy: More dialogue
        """
        parsed = []

        # Create name -> id mapping
        name_to_id = {
            agent.name.lower(): char_id
            for char_id, agent in self.npc_registry.items()
        }

        # Pattern: Name: dialogue
        name_pattern = "|".join(re.escape(name) for name in name_to_id.keys())
        pattern = rf"({name_pattern}):\s*(.+?)(?=(?:{name_pattern}):|$)"

        matches = re.finditer(pattern, output, re.IGNORECASE | re.DOTALL)

        for match in matches:
            name = match.group(1).strip().lower()
            dialogue = match.group(2).strip()

            if name in name_to_id:
                char_id = name_to_id[name]
                parsed.append(ParsedResponse(
                    character_id=char_id,
                    character_name=self.npc_registry[char_id].name,
                    dialogue=dialogue
                ))

        return parsed if parsed else None

    def _parse_fallback(self, output: str) -> Optional[List[ParsedResponse]]:
        """
        Last resort: Split by speaker detection with paragraph support

        FIXED: Now preserves multi-paragraph responses
        """
        # Split into potential segments (preserve blank lines)
        lines = output.split('\n')

        parsed = []
        current_speaker = None
        current_text = []

        # Build detection maps
        name_to_id = {
            agent.name.lower(): char_id
            for char_id, agent in self.npc_registry.items()
        }

        for line in lines:
            stripped = line.strip()

            # Skip empty lines but track them for paragraph breaks
            if not stripped:
                if current_text and current_speaker:
                    current_text.append("")  # Mark paragraph break
                continue

            detected_speaker = None
            cleaned_line = stripped

            # Check for ID in line
            for char_id, agent in self.npc_registry.items():
                if char_id in line:
                    detected_speaker = char_id
                    # Remove ID tag from line
                    cleaned_line = re.sub(rf"[\[\(]?{re.escape(char_id)}[\]\)]?:?\s*", "", line).strip()
                    break

            # Check for name in line
            if not detected_speaker:
                for name, char_id in name_to_id.items():
                    if stripped.lower().startswith(name + ":"):
                        detected_speaker = char_id
                        cleaned_line = re.sub(rf"^{re.escape(name)}:?\s*", "", line, flags=re.IGNORECASE).strip()
                        break

            if detected_speaker:
                # Save previous speaker's accumulated text
                if current_speaker and current_text:
                    # Join paragraphs (preserve double newlines)
                    dialogue = self._join_paragraphs(current_text)
                    parsed.append(ParsedResponse(
                        character_id=current_speaker,
                        character_name=self.npc_registry[current_speaker].name,
                        dialogue=dialogue
                    ))

                # Start new speaker
                current_speaker = detected_speaker
                current_text = [cleaned_line] if cleaned_line else []
            else:
                # Continue current speaker's dialogue (paragraph continuation)
                if cleaned_line:
                    current_text.append(cleaned_line)

        # Add final speaker
        if current_speaker and current_text:
            dialogue = self._join_paragraphs(current_text)
            parsed.append(ParsedResponse(
                character_id=current_speaker,
                character_name=self.npc_registry[current_speaker].name,
                dialogue=dialogue
            ))

        return parsed if parsed else None

    def _join_paragraphs(self, lines: List[str]) -> str:
        """Join lines into paragraphs, preserving intentional breaks"""
        result = []
        current_para = []

        for line in lines:
            if line == "":  # Empty line marks paragraph break
                if current_para:
                    result.append(" ".join(current_para))
                    current_para = []
            else:
                current_para.append(line)

        # Don't forget last paragraph
        if current_para:
            result.append(" ".join(current_para))

        return "\n\n".join(result)

    def build_format_instruction(self) -> str:
        """
        Generate instruction text for LLM prompts
        Returns formatted instructions with available character IDs
        """
        char_list = "\n".join([
            f"  - {agent.name} (ID: {char_id})"
            for char_id, agent in self.npc_registry.items()
        ])

        instruction = f"""RESPONSE FORMAT:
You must format your response as a JSON array. Available characters:
{char_list}

Format:
[
  {{"character_id": "mareth_001", "dialogue": "Your dialogue here"}},
  {{"character_id": "silvy_003", "dialogue": "Another character's dialogue"}}
]

IMPORTANT:
- Use EXACT character IDs from the list above
- Only include characters who would naturally respond
- Output VALID JSON only
"""
        return instruction

    def validate_and_log(self, parsed: List[ParsedResponse]) -> List[ParsedResponse]:
        """
        Validate parsed responses and log any issues

        Args:
            parsed: List of parsed responses

        Returns:
            Validated list (with invalid entries removed)
        """
        valid = []

        for response in parsed:
            if not response.dialogue:
                logger.warning(f"Empty dialogue for {response.character_name}")
                continue

            if response.character_id not in self.npc_registry and response.character_id != "dm_narrator":
                logger.warning(f"Unknown character ID: {response.character_id}")
                continue

            valid.append(response)

        logger.info(f"Validated {len(valid)}/{len(parsed)} parsed responses")
        return valid
