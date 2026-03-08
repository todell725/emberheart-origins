"""
CharacterAgent - Autonomous NPC with personality and memory
"""
import yaml
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import RAG engine for DM knowledge retrieval
try:
    from memory.rag_engine import get_rag_engine
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG engine not available for character agents")


@dataclass
class CharacterPersonality:
    """Character personality configuration"""
    name: str
    id: str  # Unique identifier (e.g., "mareth_001")
    archetype: str
    speech_patterns: List[str]
    relationships: Dict[str, str]
    quirks: List[str]
    backstory: Optional[str] = None
    avatar_url: Optional[str] = None
    webhook_url: Optional[str] = None


class CharacterAgent:
    """
    An autonomous AI agent representing an NPC party member
    """

    def __init__(
        self,
        personality_file: str,
        llm_client,
        chronicle,
        model: Optional[str] = None
    ):
        """
        Initialize a character agent

        Args:
            personality_file: Path to YAML personality config
            llm_client: OllamaClient instance
            chronicle: Chronicle instance for memory
            model: Optional specific model for this character
        """
        self.llm = llm_client
        self.chronicle = chronicle
        self.model = model

        self.personality = self._load_personality(personality_file)
        self.emotional_state = {"mood": "neutral", "energy": 0.5}

        logger.info(f"Initialized character: {self.personality.name} ({self.personality.id})")

    def _load_personality(self, file_path: str) -> CharacterPersonality:
        """Load personality configuration from YAML"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Personality file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return CharacterPersonality(
            name=data['name'],
            id=data['id'],
            archetype=data['archetype'],
            speech_patterns=data.get('speech_patterns', []),
            relationships=data.get('relationships', {}),
            quirks=data.get('quirks', []),
            backstory=data.get('backstory'),
            avatar_url=data.get('avatar_url'),
            webhook_url=data.get('webhook_url')
        )

    async def generate_response(
        self,
        context: Dict[str, Any],
        force_response: bool = False
    ) -> Optional[str]:
        """
        Generate a response based on context

        Args:
            context: Dictionary containing:
                - last_message: The triggering message
                - history: Recent conversation history
                - location: Current location
                - other_characters: List of other present NPCs
            force_response: If True, always generate a response

        Returns:
            Generated dialogue or None if character shouldn't speak
        """
        # Retrieve relevant memories
        memories = self.chronicle.recall(
            query=context.get("last_message", ""),
            character_id=self.personality.id,
            top_k=3
        )

        # Build prompt
        prompt = self._build_prompt(context, memories)

        # Generate response
        try:
            response = await self.llm.async_generate(
                prompt=prompt,
                model=self.model,
                temperature=0.8,  # Higher for more personality variation
                max_tokens=200
            )

            # Clean up response
            response = response.strip()

            # Store in chronicle
            if response:
                self.chronicle.remember(
                    content=f"{self.personality.name}: {response}",
                    category="dialogue",
                    characters=[self.personality.id],
                    location=context.get("location")
                )

            return response

        except Exception as e:
            logger.error(f"Failed to generate response for {self.personality.name}: {e}")
            return None

    def _build_prompt(self, context: Dict[str, Any], memories: List) -> str:
        """Construct the LLM prompt with personality and context"""

        # Format memories
        memory_text = "\n".join([
            f"- {m.content}" for m in memories[:3]
        ]) if memories else "No relevant memories."

        # 🔥 RAG INTEGRATION: For DM (Flame Chronicler), add D&D knowledge context
        rag_context = ""
        if RAG_AVAILABLE and self.personality.id == "DM-00":
            rag_context = self._get_rag_context(context.get("last_message", ""))

        # Format recent conversation
        history = context.get("history", [])
        conversation = "\n".join([
            f"{msg['speaker']}: {msg['content']}"
            for msg in history[-5:]  # Last 5 messages
        ]) if history else "[No recent conversation]"

        # Format relationships
        relationships = "\n".join([
            f"- {name}: {relationship}"
            for name, relationship in self.personality.relationships.items()
        ])

        # Build base prompt
        prompt = f"""You are {self.personality.name}, a character in a fantasy roleplaying game.

CHARACTER PROFILE:
Archetype: {self.personality.archetype}

Speech Patterns:
{chr(10).join(f"- {pattern}" for pattern in self.personality.speech_patterns)}

Quirks:
{chr(10).join(f"- {quirk}" for quirk in self.personality.quirks)}

Relationships:
{relationships}

RELEVANT MEMORIES:
{memory_text}"""

        # Add RAG context for DM only
        if rag_context:
            prompt += f"""

D&D REFERENCE KNOWLEDGE:
{rag_context}"""

        prompt += f"""

RECENT CONVERSATION:
{conversation}

CURRENT SITUATION:
Location: {context.get('location', 'Unknown')}
Last message: {context.get('last_message', '')}

INSTRUCTIONS:
Respond as {self.personality.name} would, staying true to your personality and speech patterns. Keep your response natural and concise (1-3 sentences). If this message doesn't warrant a response from you specifically, respond with "PASS".

Your response:"""

        return prompt

    def _get_rag_context(self, message: str) -> str:
        """
        Get relevant D&D knowledge from RAG system for DM responses

        Args:
            message: The player's message

        Returns:
            Formatted D&D reference context
        """
        try:
            rag = get_rag_engine()

            # Check if RAG is indexed
            if not rag.documents:
                logger.debug("RAG not indexed yet, skipping knowledge retrieval")
                return ""

            # Detect if message is asking about D&D rules/mechanics
            keywords = ["spell", "magic", "item", "monster", "rule", "how does", "what is",
                       "damage", "attack", "ability", "class", "race", "feat"]

            if any(keyword in message.lower() for keyword in keywords):
                # Get relevant context
                context = rag.get_context(message, max_tokens=500, category=None)

                if context and "No relevant" not in context:
                    logger.info(f"RAG provided D&D knowledge for DM response")
                    return context

            return ""

        except Exception as e:
            logger.error(f"RAG context retrieval failed: {e}")
            return ""

    def should_respond(self, message: str, context: Dict[str, Any]) -> float:
        """
        Calculate likelihood that this character should respond (0.0-1.0)

        Args:
            message: The message to potentially respond to
            context: Additional context

        Returns:
            Score from 0.0 (definitely don't respond) to 1.0 (definitely respond)
        """
        score = 0.1  # Base score to give everyone a small chance

        # 🔥 DM BOOST: Flame Chronicler should respond to D&D rules questions
        if self.personality.id == "DM-00":
            rules_keywords = [
                "spell", "magic", "cast", "damage", "attack", "ability",
                "how does", "what is", "rule", "class", "race", "feat",
                "item", "weapon", "armor", "monster", "creature",
                "can i", "am i able", "is it possible", "how do i"
            ]
            if any(keyword in message.lower() for keyword in rules_keywords):
                score += 0.8  # MASSIVE boost for rules questions
                logger.info(f"DM boosted for rules question: '{message[:50]}...'")

        # Mentioned by name
        if self.personality.name.lower() in message.lower():
            score += 0.5

        # Related to character's expertise/archetype
        archetype_keywords = self.personality.archetype.lower().split()
        if any(keyword in message.lower() for keyword in archetype_keywords):
            score += 0.3

        # Group-wide mentions
        group_keywords = ["party", "everyone", "all", "group", "team", "guys", "ladies", "folks"]
        if any(keyword in message.lower() for keyword in group_keywords):
            score += 0.3

        # Recent activity (avoid dominating conversation)
        recent_messages = context.get("history", [])[-5:]
        self_messages = sum(1 for msg in recent_messages if msg.get("speaker") == self.personality.name)
        if self_messages >= 2:
            score -= 0.3  # Penalize if spoke recently

        # Random factor for variety
        import random
        score += random.uniform(-0.05, 0.15)

        return max(0.0, min(1.0, score))

    @property
    def name(self) -> str:
        return self.personality.name

    @property
    def id(self) -> str:
        return self.personality.id

    @property
    def avatar_url(self) -> Optional[str]:
        return self.personality.avatar_url

    @property
    def webhook_url(self) -> Optional[str]:
        return self.personality.webhook_url
