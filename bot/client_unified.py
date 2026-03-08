"""
EmberHeart: Origins Bot — Complete Integration
Forked from Claudes-EmberHeart.
Combines:
- Flame Chronicler: Chronicle (RAG), Router, Parser, Multi-NPC dialogue
- Kingdom engines: Quest/Shop/Slayer, Cogs, JSON character system
"""
import asyncio
import logging
import discord
from discord.ext import commands
from discord import Webhook
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

import os
import re

from llm import OllamaClient
from memory import Chronicle
from agents import CharacterAgent, CognitiveRouter, NPCResponseParser
from core.character_loader import UnifiedCharacterLoader
from core.config import DM_SYSTEM_PROMPT
from engines.quest_engine_chronicle import QuestEngineWithChronicle
from engines.shop_engine import DynamicShop
from engines.slayer_engine import SlayerEngine
from engines.crafting_engine import CraftingEngine
from engines.smithing_engine import SmithingEngine
from engines.event_generator import EventGenerator
from engines.rumor_engine import RumorEngine

logger = logging.getLogger(__name__)


class EmberHeartBotUnified(commands.Bot):
    """
    EmberHeart: Origins bot combining both systems:
    - Commands (!quest, !slayer, !shop)
    - NPC Council Dialogue (#council-chambers with RAG)
    - Chronicle memory across everything
    """

    def __init__(self, config: Dict):
        # Discord bot setup
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.webhooks = True
        intents.members = True

        super().__init__(
            command_prefix=config.get('command_prefix', '!'),
            intents=intents
        )

        self.config = config

        # Core AI systems (Claude's)
        self.llm = OllamaClient(
            base_url=config['ollama_url'],
            default_model=config['default_model']
        )
        self.dm_model: Optional[str] = os.getenv('DM_MODEL') or None  # None falls back to default_model
        self.chronicle = Chronicle()

        # Character management (Unified)
        self.character_loader = UnifiedCharacterLoader(self.llm, self.chronicle)
        self.characters: Dict[str, CharacterAgent] = {}
        self.router: Optional[CognitiveRouter] = None
        self.parser: Optional[NPCResponseParser] = None

        # Game engines (User's)
        self.quest_engine = QuestEngineWithChronicle(self.chronicle)
        self.shop_engine = DynamicShop()
        self.slayer_engine = SlayerEngine(llm_client=self.llm)  # Pass LLM for narration
        self.crafting_engine = CraftingEngine(llm_client=self.llm)
        self.smithing_engine = SmithingEngine(llm_client=self.llm)
        self.event_generator: Optional[EventGenerator] = None  # Initialized in setup_hook
        self.rumor_engine: Optional[RumorEngine] = None

        # Webhook cache
        self.webhooks: Dict[int, Webhook] = {}  # Shared webhooks per channel

        # Message history
        self.message_history: List[Dict] = []
        self.max_history = 20

        logger.info("EmberHeartBotUnified initialized")

    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info("Running unified setup hook...")

        # Load all characters (YAML + JSON)
        self.characters = self.character_loader.load_all_characters()

        # Initialize router and parser
        self.router = CognitiveRouter(self.characters)
        self.parser = NPCResponseParser(self.characters)

        # Load all cogs
        cogs_to_load = [
            # Core gameplay
            "cogs.quests",
            "cogs.slayer",
            "cogs.hunting",
            "cogs.mining",
            "cogs.fishing",
            "cogs.woodcutting",
            "cogs.cooking",
            "cogs.crafting",
            "cogs.smithing",
            "cogs.economy",
            "cogs.forge",
            "cogs.world",
            "cogs.characters",
            "cogs.combat",
            # Utility
            "cogs.owner",
            "cogs.relationships",
            "cogs.rules",
            "cogs.meta",
            "cogs.reference",
            # New features & minigames
            "cogs.hearth",
            "cogs.dreams",
            "cogs.appraisal",
            "cogs.alchemy",
            "cogs.gathering",
            "cogs.translation"
        ]

        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"✓ Loaded {cog}")
            except Exception as e:
                logger.error(f"✗ Failed to load {cog}: {e}")

        # Add persistent views for interactive UI features
        # (When cogs use discord.ui.View with timeout=None, add them here)
        # Example: self.add_view(ShopView())
        # This ensures buttons survive bot restarts
        logger.info("Persistent views initialized (none currently registered)")

        # Check Ollama
        if not self.llm.is_available():
            logger.error("Ollama is not available!")
        else:
            models = self.llm.list_models()
            logger.info(f"Available models: {models}")

        # Initialize Event Generator (Living Kingdom)
        self.event_generator = EventGenerator(self.llm, self)
        logger.info("Event Generator initialized")

        # Initialize Rumor Engine
        self.rumor_engine = RumorEngine(self.llm, self)
        logger.info("Rumor Engine initialized")

        logger.info("Unified setup complete!")

    async def on_ready(self):
        """Called when bot connects to Discord"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Loaded {len(self.characters)} characters")
        
        # High visibility terminal print
        print("\n" + "="*60)
        print(f"🔥 EMBERHEART: ORIGINS HAS SUCCESSFULLY STARTED 🔥")
        print("="*60)
        print(f"Logged in as: {self.user}")
        print(f"Loaded {len(self.characters)} NPCs. The bot is actively listening in Discord.")
        print("You can safely leave this window open.\n")

        # Start Living Kingdom Event Generator
        if self.event_generator:
            try:
                asyncio.create_task(self.event_generator.start_event_loop())
                logger.info("🌍 Living Kingdom Event Generator started (24h cycle)")
            except AttributeError:
                logger.error("EventGenerator does not have start_event_loop method.")

        # Start Rumor Engine
        if self.rumor_engine:
            try:
                asyncio.create_task(self.rumor_engine.start_rumor_loop())
                logger.info("🍺 Rumor Engine started (8-12h cycle)")
            except AttributeError:
                logger.error("RumorEngine does not have start_rumor_loop method.")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore own messages
        if message.author == self.user:
            return

        # Ignore other bots
        if message.author.bot:
            return

        # Process commands first (!quest, !slayer, etc.)
        await self.process_commands(message)

        # Then handle NPC dialogue in designated channels
        council_channel_id = self.config.get('channel_ids', {}).get('council_chambers')
        off_topic_channel_id = self.config.get('channel_ids', {}).get('off_topic')
        hearth_channel_id = self.config.get('channel_ids', {}).get('hearth')
        whispers_channel_id = self.config.get('channel_ids', {}).get('whispers')

        # Don't trigger dialogue if it was a command
        if message.content.startswith(self.command_prefix):
            return

        # Route to appropriate handler based on channel
        if council_channel_id and message.channel.id == council_channel_id:
            await self._handle_party_chat(message, channel_type='council_chambers')
        elif off_topic_channel_id and message.channel.id == off_topic_channel_id:
            await self._handle_party_chat(message, channel_type='off_topic')
        elif hearth_channel_id and message.channel.id == hearth_channel_id:
            await self._handle_party_chat(message, channel_type='hearth')
        elif whispers_channel_id and message.channel.id == whispers_channel_id:
            await self._handle_party_chat(message, channel_type='whispers')

    async def _handle_party_chat(self, message: discord.Message, channel_type: str = 'party_chat'):
        """
        Handle NPC dialogue in party chat or off-topic
        Uses orchestrated generation with parser

        Args:
            message: Discord message
            channel_type: 'party_chat' or 'off_topic' - determines which NPCs can respond
        """
        content = message.content.strip()
        if not content:
            return

        logger.info(f"[{channel_type}] Message from {message.author}: {content[:50]}...")

        # Add to history
        self._add_to_history({
            "speaker": message.author.display_name,
            "content": content,
            "timestamp": message.created_at.isoformat()
        })

        # Filter characters based on channel type
        if channel_type == 'council_chambers':
            # Domain-aware council selection
            available_chars = self._get_council_characters(content)
            location = "The Council Chambers"
            max_speakers = 3
        elif channel_type == 'whispers':
            # Court whispers — gossip and intrigue
            available_chars = {k: v for k, v in self.characters.items() if k != 'PC-01'}
            location = "The Court"
            max_speakers = 4
        else:  # off_topic or hearth
            # All NPCs available
            available_chars = {k: v for k, v in self.characters.items() if k != 'PC-01'}
            location = "The Hearth"
            max_speakers = 5

        # Get player's equipped items/inventory for NPC reactions
        player_inventory = await self._get_player_inventory(message.author.display_name)

        # Build context
        context = {
            "last_message": content,
            "history": self.message_history,
            "location": location,
            "other_characters": list(available_chars.keys()),
            "player_inventory": player_inventory  # NPCs can now react to items!
        }

        # Create a temporary router with filtered characters
        from agents import CognitiveRouter
        filtered_router = CognitiveRouter(available_chars)

        # Select NPCs to respond
        responding_npcs = filtered_router.select_speaker(
            message=content,
            context=context,
            allow_multiple=True,
            max_speakers=max_speakers
        )

        if not responding_npcs:
            logger.debug("No NPCs chose to respond")
            return

        # Build orchestrated prompt
        prompt = self._build_multi_npc_prompt(content, context, responding_npcs)

        # Generate via LLM
        try:
            async with message.channel.typing():
                llm_output = await self.llm.async_generate(
                    prompt=prompt,
                    model=self.dm_model or self.config.get('default_model', 'llama3.1'),
                    temperature=self.config.get('temperature', 0.8),
                    max_tokens=1024,
                    num_ctx=8192,
                    system=DM_SYSTEM_PROMPT
                )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return

        if not llm_output:
            logger.warning("Empty LLM output")
            return

        # Strip <think>...</think> blocks before parsing so internal reasoning
        # never reaches the parser or Discord.
        llm_output = re.sub(r"<think>.*?</think>", "", llm_output, flags=re.DOTALL).strip()

        logger.debug(f"LLM output: {llm_output[:200]}...")

        # Parse multi-NPC responses
        if self.parser:
            parsed = self.parser.parse(llm_output)
            parsed = self.parser.validate_and_log(parsed)
        else:
            logger.warning("NPCResponseParser not initialized")
            return

        if not parsed:
            logger.warning("Parser returned no valid responses")
            return

        # Send split messages
        await self._send_party_responses(message.channel, parsed)

        # Store in Chronicle
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

    async def trigger_npc_event(self, message_content: str, author_name: str = "SYSTEM"):
        """
        Synthetically trigger NPC reactions to a world event (e.g. Legendary Drops)
        by broadcasting it to the off-topic channel and invoking the CognitiveRouter.
        """
        off_topic_id = self.config.get('channel_ids', {}).get('off_topic')
        if not off_topic_id:
            logger.warning("No off_topic channel configured for NPC event.")
            return

        guild = self.guilds[0] if self.guilds else None
        if not guild:
            return
            
        channel = guild.get_channel(off_topic_id)
        if not channel:
            return
            
        # Send the announcement message first
        try:
            await channel.send(message_content)
        except Exception as e:
            logger.error(f"Failed to broadcast event to off-topic: {e}")
            return

        # Now simulate a user message to trigger _handle_party_chat
        class MockAuthor:
            def __init__(self, name):
                self.display_name = name
                self.name = name
                self.bot = False
                
        class MockMessage:
            def __init__(self, content, author_name, channel):
                self.content = str(content)
                self.channel = channel
                self.created_at = datetime.now()
                self.author = MockAuthor(author_name)

        mock_msg = MockMessage(message_content, author_name, channel)
        # Process the synthetic message as if a player typed it
        await self._handle_party_chat(mock_msg, channel_type='off_topic')

    def _get_council_characters(self, message: str) -> Dict[str, 'CharacterAgent']:
        """
        Domain-aware council selection for #council-chambers.

        Scores each NPC based on how many of their domains match keywords in the
        player's message. Core council members (EH-01 through EH-07) are always
        eligible; domain-relevant NPCs from houses, military, and academy are
        pulled in when the topic matches their expertise.

        Domain → keyword map:
            military/defense → army, soldier, troops, war, defense, patrol, attack
            trade/finance    → trade, gold, treasury, merchant, tax, market, coin
            arcane/golemcraft → golem, magic, arcane, enchant, prismspire, rune
            lore/prophecy    → prophecy, archive, lore, history, record, ancient
            infrastructure   → build, road, wall, aqueduct, housing, repair
            civic/welfare    → food, welfare, housing, citizen, festival, morale
            nature/healing   → grove, druid, herb, heal, bloom, sanctuary
            industry         → forge, smith, foundry, production, output, steel
            naval            → navy, ship, dock, fleet, port, emberlake, sail
            wyrms            → wyrm, aerial, flight, sky, roost, rider
            crafting         → craft, forge, relic, memory ore, apprentice
            education        → academy, student, teacher, training, lesson
        """
        message_lower = message.lower()

        # Keyword → domain mapping
        KEYWORD_DOMAINS = {
            "military": ["army", "soldier", "troops", "war", "defense", "patrol", "attack", "barracks", "guard"],
            "defense": ["defense", "wall", "shield", "protect", "garrison", "fortify"],
            "trade": ["trade", "gold", "treasury", "merchant", "tax", "market", "coin", "caravan", "import", "export"],
            "finance": ["gold", "treasury", "budget", "tax", "cost", "fund", "coin"],
            "arcane": ["magic", "arcane", "enchant", "rune", "spell", "mana", "leyline", "ward"],
            "golemcraft": ["golem", "construct", "automaton", "prismspire"],
            "lore": ["lore", "history", "record", "ancient", "archive", "text", "scroll"],
            "prophecy": ["prophecy", "omen", "vision", "foretelling", "dream", "seer"],
            "infrastructure": ["build", "road", "wall", "aqueduct", "housing", "repair", "construction", "bridge"],
            "civic": ["citizen", "festival", "morale", "welfare", "public", "community"],
            "nature": ["grove", "druid", "herb", "bloom", "sanctuary", "tree", "forest", "plant"],
            "healing": ["heal", "cure", "medicine", "injury", "sick", "wound", "remedy"],
            "industry": ["forge", "foundry", "production", "output", "steel", "iron", "mine", "smithing"],
            "naval": ["navy", "ship", "dock", "fleet", "port", "emberlake", "sail", "admiral"],
            "wyrms": ["wyrm", "aerial", "flight", "sky", "roost", "rider", "dragon", "wing"],
            "crafting": ["craft", "relic", "memory ore", "apprentice", "artifact", "enchantment"],
            "education": ["academy", "student", "teacher", "training", "lesson", "learn"],
            "diplomacy": ["treaty", "alliance", "diplomat", "embassy", "foreign", "peace"],
            "governance": ["law", "decree", "court", "noble", "house", "council", "throne", "crown"],
            "espionage": ["spy", "shadow", "secret", "intelligence", "infiltrat"],
            "fire": ["flame", "fire", "ember", "burn", "ash", "spark"],
            "memory": ["memory", "rememb", "echo", "shard"],
        }

        # Detect matching domains from message
        matched_domains = set()
        for domain, keywords in KEYWORD_DOMAINS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    matched_domains.add(domain)
                    break

        # Core council members are ALWAYS eligible (EH-01 through EH-07 + wives)
        CORE_COUNCIL_IDS = {
            "EH-01", "EH-02", "EH-03", "EH-04", "EH-05",  # Varka, Thalos, Sybelle, Brennus, Brida
            "EH-06", "EH-07",                                 # Queen Maeryn, Prince Aereth
            "PC-02", "PC-03", "PC-04", "PC-05"                # Wives
        }

        result = {}

        for char_id, char in self.characters.items():
            # Skip Kaelrath (the player)
            if char_id == "PC-01":
                continue

            # Core council is always available
            if char_id in CORE_COUNCIL_IDS:
                result[char_id] = char
                continue

            # Domain-match: pull in relevant NPCs
            if matched_domains:
                char_domains = getattr(char, 'domains', [])
                if char_domains and matched_domains.intersection(set(char_domains)):
                    result[char_id] = char
                    continue

            # Noble house heads are always available in council
            if char_id in {"EH-08", "EH-09", "EH-10", "EH-11", "EH-12"}:
                result[char_id] = char

        # If no domains matched, fall back to all council + noble house members
        if not matched_domains:
            for char_id, char in self.characters.items():
                if char_id != "PC-01" and (char_id.startswith("EH-") and int(char_id.split("-")[1]) <= 12):
                    result[char_id] = char

        logger.debug(f"Council selection: {len(result)} NPCs for domains {matched_domains}")
        return result

    def _build_multi_npc_prompt(self, message: str, context: Dict, npcs: List) -> str:
        """Build orchestrated prompt for multiple NPCs"""
        # Get memories
        memories = self.chronicle.recall(message, top_k=5)
        memory_text = "\n".join([f"- {m.content}" for m in memories]) if memories else "No relevant memories."

        # Format conversation
        conversation = "\n".join([
            f"{msg['speaker']}: {msg['content']}"
            for msg in context['history'][-5:]
        ]) if context['history'] else "[No recent conversation]"

        # Build NPC profiles
        npc_profiles = []
        for npc in npcs:
            p = npc.personality
            profile = f"- {p.name} (ID: {p.id})\n  Archetype: {p.archetype}\n  Speech: {', '.join(p.speech_patterns[:2])}"
            npc_profiles.append(profile)

        profiles_text = "\n".join(npc_profiles)

        # Get format instructions
        format_instruction = self.parser.build_format_instruction() if self.parser else "[Format as: Character: Dialogue]"

        # Build inventory context if available
        inventory_context = ""
        if context.get("player_inventory"):
            inv = context["player_inventory"]
            if inv.get("equipped") or inv.get("notable"):
                inventory_context = "\n\nPLAYER'S VISIBLE ITEMS:"
                if inv.get("equipped"):
                    inventory_context += f"\n- Equipped: {', '.join(inv['equipped'][:3])}"
                if inv.get("notable"):
                    inventory_context += f"\n- Notable Items: {', '.join(inv['notable'][:3])}"
                inventory_context += "\n(NPCs may notice and react to these items!)"

        prompt = f"""You are managing multiple characters in a fantasy RPG party.

CHARACTERS WHO SHOULD RESPOND:
{profiles_text}

RELEVANT MEMORIES:
{memory_text}

RECENT CONVERSATION:
{conversation}
{inventory_context}

CURRENT SITUATION:
The player, King Kaelrath (PC-01), just said: "{message}"

WARNING: DO NOT write dialogue or actions for Kaelrath. Only speak for the selected NPCs.

{format_instruction}"""

        return prompt

    def _chunk_text(self, text: str, max_length: int = 2000) -> List[str]:
        """Split text into chunks that respect Discord's length limits."""
        if len(text) <= max_length:
            return [text]
            
        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
                
            # Find the best split point within max_length
            chunk = text[:max_length]
            
            split_idx = chunk.rfind('\n\n')
            if split_idx == -1:
                split_idx = chunk.rfind('\n')
            if split_idx == -1:
                split_idx = chunk.rfind(' ')
            if split_idx == -1:
                split_idx = max_length - 1
                
            chunks.append(text[:split_idx+1].strip())
            text = text[split_idx+1:].strip()
            
        return chunks

    async def _send_party_responses(self, channel: discord.TextChannel, parsed_responses: List):
        """Send multiple NPC responses with delays and chunking for long messages"""
        for response in parsed_responses:
            # Get NPC
            if response.character_id not in self.characters:
                chunks = self._chunk_text(response.dialogue)
                for i, chunk in enumerate(chunks):
                    prefix = f"**{response.character_name}**: " if i == 0 else ""
                    await channel.send(f"{prefix}{chunk}")
                await asyncio.sleep(0.5)
                continue

            npc = self.characters[response.character_id]

            # Typing delay
            async with channel.typing():
                word_count = len(response.dialogue.split())
                delay = min(3.0, word_count * 0.2)
                await asyncio.sleep(delay)

            # Get shared webhook
            webhook = await self._get_webhook(channel)

            chunks = self._chunk_text(response.dialogue)
            for chunk in chunks:
                if webhook:
                    try:
                        await webhook.send(
                            content=chunk,
                            username=npc.name,
                            avatar_url=npc.avatar_url
                        )
                        logger.debug(f"Sent chunk via webhook: {npc.name}")
                    except Exception as e:
                        logger.warning(f"Webhook failed: {e}")
                        await channel.send(f"**{npc.name}**: {chunk}")
                else:
                    await channel.send(f"**{npc.name}**: {chunk}")

            # Gap between speakers
            await asyncio.sleep(0.8)

    async def _get_webhook(self, channel: discord.TextChannel) -> Optional[Webhook]:
        """Get or create shared webhook for channel"""
        # Check cache
        if channel.id in self.webhooks:
            return self.webhooks[channel.id]

        # Look for existing webhook
        existing = await channel.webhooks()
        for wh in existing:
            if wh.name == "Origins-NPCs":
                self.webhooks[channel.id] = wh
                return wh

        # Create new shared webhook
        try:
            webhook = await channel.create_webhook(
                name="Origins-NPCs",
                reason="Shared NPC delivery for EmberHeart: Origins"
            )
            self.webhooks[channel.id] = webhook
            logger.info(f"Created shared webhook in {channel.name}")
            return webhook
        except discord.Forbidden:
            logger.warning(f"No webhook permission in {channel.name}")
            return None
        except Exception as e:
            logger.error(f"Failed to create webhook: {e}")
            return None

    def _add_to_history(self, message: Dict):
        """Add message to conversation history"""
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-int(self.max_history):]

    async def _get_player_inventory(self, player_name: str) -> Dict:
        """
        Fetch player's equipped items and notable inventory

        Args:
            player_name: Display name of the player

        Returns:
            Dictionary with equipped items and notable inventory
        """
        try:
            from core.storage import load_character_state

            # Map player name to character ID (simplified for now)
            # TODO: Create proper player -> character mapping
            character_id = "PC-01"  # Default to Kaelrath

            char_state = load_character_state(character_id)
            if not char_state:
                return {"equipped": [], "inventory": [], "notable": []}

            # Extract equipped items
            equipped = char_state.get("status", {}).get("equipped", {})
            inventory_items = char_state.get("status", {}).get("inventory", [])

            # Filter for "notable" items (cursed, legendary, magical)
            notable = []
            for item in inventory_items[:10]:  # Limit to first 10 items
                item_lower = str(item).lower()
                if any(keyword in item_lower for keyword in ["cursed", "legendary", "magic", "ancient", "dark", "blessed"]):
                    notable.append(item)

            return {
                "equipped": list(equipped.values()) if isinstance(equipped, dict) else [],
                "inventory": inventory_items[:5],  # First 5 items
                "notable": notable
            }

        except Exception as e:
            logger.error(f"Failed to get player inventory: {e}")
            return {"equipped": [], "inventory": [], "notable": []}

    # Hook for quest engine to log to Chronicle
    def log_quest_completion(self, quest_id: str, quest_title: str, party_members: List[str]):
        """Called by quest engine when quest completes"""
        self.chronicle.remember(
            content=f"Quest completed: {quest_title} ({quest_id})",
            category="quest",
            characters=party_members
        )
        logger.info(f"Logged quest {quest_id} to Chronicle")

    # Hook for shop purchases
    def log_shop_purchase(self, character_id: str, item_name: str, cost: int):
        """Called when character buys from shop"""
        self.chronicle.remember(
            content=f"Purchased {item_name} from shop for {cost} gold",
            category="shop",
            characters=[character_id]
        )

    # Hook for slayer task completion
    def log_slayer_completion(self, character_id: str, task_name: str, kills: int):
        """Called when slayer task completes"""
        self.chronicle.remember(
            content=f"Completed slayer task: {task_name} ({kills} kills)",
            category="slayer",
            characters=[character_id]
        )
