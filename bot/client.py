"""
EmberHeartBot - Discord client with multi-NPC management
"""
import asyncio
import logging
import discord
from discord import Webhook
import aiohttp
from typing import Dict, List, Optional
from pathlib import Path

from llm import OllamaClient
from memory import Chronicle
from agents import CharacterAgent, CognitiveRouter, NPCResponseParser

logger = logging.getLogger(__name__)


class EmberHeartBot(discord.Client):
    """
    Main Discord bot for EmberHeart: Origins
    Manages NPC interactions, routing, and message splitting
    """

    def __init__(self, config: Dict, *args, **kwargs):
        """
        Initialize the bot

        Args:
            config: Configuration dictionary with:
                - ollama_url: Ollama API endpoint
                - default_model: Default LLM model
                - temperature: LLM temperature
                - character_dir: Path to character YAML files
                - channel_ids: Dict of channel IDs
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.webhooks = True

        super().__init__(intents=intents, *args, **kwargs)

        self.config = config

        # Initialize core systems
        self.llm = OllamaClient(
            base_url=config['ollama_url'],
            default_model=config['default_model']
        )
        self.chronicle = Chronicle()

        # Character management
        self.characters: Dict[str, CharacterAgent] = {}
        self.router: Optional[CognitiveRouter] = None
        self.parser: Optional[NPCResponseParser] = None

        # Webhook cache for custom avatars (single master webhook per channel)
        self.webhooks: Dict[int, Webhook] = {}

        # Message history for context
        self.message_history: List[Dict] = []
        self.max_history = 20

        logger.info("EmberHeartBot initialized")

    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info("Running setup hook...")

        # Load characters
        await self._load_characters()

        # Initialize router and parser
        self.router = CognitiveRouter(self.characters)
        self.parser = NPCResponseParser(self.characters)

        # Check Ollama availability
        if not self.llm.is_available():
            logger.error("Ollama is not available! Please start Ollama first.")
        else:
            models = self.llm.list_models()
            logger.info(f"Available models: {models}")

        logger.info("Setup complete!")

    async def _load_characters(self):
        """Load character agents from YAML files"""
        char_dir = Path(self.config['character_dir'])

        if not char_dir.exists():
            logger.warning(f"Character directory not found: {char_dir}")
            return

        yaml_files = list(char_dir.glob("*.yaml")) + list(char_dir.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                character = CharacterAgent(
                    personality_file=str(yaml_file),
                    llm_client=self.llm,
                    chronicle=self.chronicle
                )
                self.characters[character.id] = character
                logger.info(f"Loaded character: {character.name}")
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")

        logger.info(f"Loaded {len(self.characters)} characters total")

    async def on_ready(self):
        """Called when bot successfully connects to Discord"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore own messages
        if message.author == self.user:
            return

        # Ignore bot messages (unless configured otherwise)
        if message.author.bot:
            return

        # Check if message is in party chat channel
        party_channel_id = self.config.get('channel_ids', {}).get('party_chat')

        if message.channel.id == party_channel_id:
            await self._handle_party_chat(message)
        else:
            # Could handle other channels here (DM narration, etc.)
            pass

    async def _handle_party_chat(self, message: discord.Message):
        """
        Handle messages in the party chat channel
        Routes to appropriate NPCs, generates a multi-NPC response,
        parses the structured output, and sends split messages.
        """
        content = message.content.strip()

        if not content:
            return

        logger.info(f"Party chat message from {message.author}: {content[:50]}...")

        # Add to message history
        self._add_to_history({
            "speaker": message.author.display_name,
            "content": content,
            "timestamp": message.created_at.isoformat()
        })

        # Build context
        context = {
            "last_message": content,
            "history": self.message_history,
            "location": "The Tavern",  # TODO: Make this dynamic
            "other_characters": list(self.characters.keys())
        }

        # Select which NPCs should respond (MULTI-SPEAKER ENABLED)
        responding_npcs = self.router.select_speaker(
            message=content,
            context=context,
            allow_multiple=True,
            max_speakers=3
        )

        if not responding_npcs:
            logger.debug("No NPCs chose to respond")
            return

        # --- BUILD COMBINED MULTI-NPC PROMPT ---
        # Retrieve memories for context
        memories = self.chronicle.recall(query=content, top_k=5)
        memory_text = "\n".join([f"- {m.content}" for m in memories]) if memories else "No relevant memories."

        # Format recent conversation
        conversation = "\n".join([
            f"{msg['speaker']}: {msg['content']}"
            for msg in self.message_history[-5:]
        ]) if self.message_history else "[No recent conversation]"

        # Build character profiles for the selected NPCs
        npc_profiles = []
        for npc in responding_npcs:
            p = npc.personality
            profile = (
                f"- {p.name} (ID: {p.id})\n"
                f"  Archetype: {p.archetype}\n"
                f"  Speech: {', '.join(p.speech_patterns[:2])}\n"
                f"  Quirks: {', '.join(p.quirks[:2])}"
            )
            npc_profiles.append(profile)

        profiles_text = "\n".join(npc_profiles)

        # Get the parser's JSON format instruction
        format_instruction = self.parser.build_format_instruction()

        prompt = f"""You are roleplaying as multiple fantasy characters in a party.
Only respond as the characters listed below. Do NOT respond as the player (Kaelrath).

CHARACTERS WHO SHOULD RESPOND:
{profiles_text}

RELEVANT MEMORIES:
{memory_text}

RECENT CONVERSATION:
{conversation}

CURRENT SITUATION:
The player King Kaelrath just said: "{content}"

{format_instruction}
"""

        # Generate via async LLM
        try:
            async with message.channel.typing():
                llm_output = await self.llm.async_generate(
                    prompt=prompt,
                    temperature=self.config.get('temperature', 0.7),
                    max_tokens=500
                )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return

        if not llm_output:
            logger.warning("Empty LLM output")
            return

        logger.info(f"Raw LLM output: {llm_output[:200]}...")

        # --- PARSE THE STRUCTURED OUTPUT ---
        parsed = self.parser.parse(llm_output)
        parsed = self.parser.validate_and_log(parsed)

        if not parsed:
            logger.warning("Parser returned no valid responses")
            return

        # --- SEND SPLIT MESSAGES ---
        await self.send_party_responses(message.channel, parsed)

        # Store responses in Chronicle
        for response in parsed:
            self.chronicle.remember(
                content=f"{response.character_name}: {response.dialogue}",
                category="dialogue",
                characters=[response.character_id],
                location=context.get("location")
            )
            self._add_to_history({
                "speaker": response.character_name,
                "content": response.dialogue,
                "timestamp": message.created_at.isoformat()
            })

    async def _send_npc_message(
        self,
        channel: discord.TextChannel,
        npc: CharacterAgent,
        message: str
    ):
        """
        Send an NPC message with typing delay and custom avatar

        Args:
            channel: Discord channel to send to
            npc: CharacterAgent sending the message
            message: Message content
        """
        # Show typing indicator
        async with channel.typing():
            # Calculate realistic typing delay
            word_count = len(message.split())
            delay = min(3.0, word_count * 0.2)  # ~200ms per word, max 3 seconds
            await asyncio.sleep(delay)

        # Try to use webhook for custom avatar
        webhook = await self._get_webhook(channel, npc)

        if webhook:
            try:
                await webhook.send(
                    content=message,
                    username=npc.name,
                    avatar_url=npc.avatar_url
                )
                logger.debug(f"Sent via webhook: {npc.name}")
                return
            except Exception as e:
                logger.warning(f"Webhook send failed, falling back to normal: {e}")

        # Fallback to normal message
        await channel.send(f"**{npc.name}**: {message}")

    async def _get_webhook(
        self,
        channel: discord.TextChannel,
        npc: CharacterAgent
    ) -> Optional[Webhook]:
        """
        Get or create a single master webhook for a channel.
        All NPCs share the same webhook and override username/avatar per message.

        Args:
            channel: Discord channel
            npc: CharacterAgent (not used in webhook creation, kept for API compatibility)

        Returns:
            Webhook object or None
        """
        # Check cache first
        if channel.id in self.webhooks:
            return self.webhooks[channel.id]

        # Check if webhook already exists in the channel
        try:
            existing_webhooks = await channel.webhooks()
            for webhook in existing_webhooks:
                if webhook.name == "EmberHeart-Dynamic":
                    # Found existing master webhook, cache and return it
                    self.webhooks[channel.id] = webhook
                    logger.info(f"Reusing existing webhook 'EmberHeart-Dynamic' in {channel.name}")
                    return webhook

            # No existing webhook found, create a new one
            webhook = await channel.create_webhook(
                name="EmberHeart-Dynamic",
                reason="Shared webhook for all NPC messages"
            )

            # Cache it
            self.webhooks[channel.id] = webhook
            logger.info(f"Created new master webhook 'EmberHeart-Dynamic' in {channel.name}")

            return webhook

        except discord.Forbidden:
            logger.warning(f"No permission to create webhook in {channel.name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get/create webhook: {e}")
            return None

    def _add_to_history(self, message: Dict):
        """Add a message to conversation history"""
        self.message_history.append(message)

        # Trim history if too long
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]

    async def send_party_responses(
        self,
        channel: discord.TextChannel,
        parsed_responses: List
    ):
        """
        Send multiple parsed NPC responses with delays

        Args:
            channel: Discord channel
            parsed_responses: List of ParsedResponse objects from parser
        """
        for response in parsed_responses:
            # Get NPC
            if response.character_id not in self.characters:
                # Unknown character, send as narrator
                await channel.send(f"**{response.character_name}**: {response.dialogue}")
                await asyncio.sleep(0.5)
                continue

            npc = self.characters[response.character_id]

            # Send with typing delay
            await self._send_npc_message(channel, npc, response.dialogue)

            # Small gap between speakers
            await asyncio.sleep(0.8)
