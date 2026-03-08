"""
Living Kingdom Event Generator — EmberHeart: Origins
Autonomous AI-driven kingdom events triggered every 12-24 hours
"""
import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.config import DB_DIR, ROOT_DIR

logger = logging.getLogger("EH_EventGen")

DOCS_DIR = ROOT_DIR / "docs"


class EventGenerator:
    """
    Generates autonomous world events based on kingdom state and rumors.
    Events can spawn temporary channels, special shop items, or world changes.
    """

    def __init__(self, llm_client, bot):
        """
        Initialize event generator

        Args:
            llm_client: OllamaClient instance for AI generation
            bot: Discord bot instance for channel/message creation
        """
        self.llm = llm_client
        self.bot = bot
        self.settlement_path = DOCS_DIR / "SETTLEMENT_STATE.json"
        self.last_event_time = None
        self.event_interval_hours = 24  # Default 24 hours between events
        self.running = False

    async def start_event_loop(self):
        """Start the autonomous event generation loop"""
        self.running = True
        logger.info("🌍 Living Kingdom Event Generator started")

        while self.running:
            try:
                # Wait for interval
                await asyncio.sleep(self.event_interval_hours * 3600)

                # Generate event
                await self.generate_world_event()

            except asyncio.CancelledError:
                logger.info("Event loop cancelled")
                break
            except Exception as e:
                logger.error(f"Event loop error: {e}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(3600)

    def stop_event_loop(self):
        """Stop the event generation loop"""
        self.running = False
        logger.info("Event loop stopped")

    async def generate_world_event(self) -> Optional[dict]:
        """
        Generate a world event using AI based on kingdom state

        Returns:
            Event dictionary with type, description, and effects
        """
        try:
            # Load kingdom state
            if not self.settlement_path.exists():
                logger.warning("Settlement state not found, skipping event")
                return None

            settlement = json.loads(self.settlement_path.read_text(encoding='utf-8'))

            # Extract relevant data
            calendar = settlement.get("settlement", {}).get("calendar", {})
            stockpiles = settlement.get("settlement", {}).get("stockpiles", {})
            core_status = settlement.get("settlement", {}).get("core_status", {})

            # Build context prompt for LLM
            prompt = self._build_event_prompt(calendar, stockpiles, core_status)

            # Generate event via LLM
            logger.info("Generating world event via LLM...")
            event_description = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.8,
                max_tokens=300
            )

            if not event_description:
                logger.warning("LLM returned empty event")
                return None

            # Parse event type and create effects
            event = self._parse_event(event_description, calendar)

            # Log and execute event
            logger.info(f"📜 Generated Event: {event['name']}")
            await self._execute_event(event)

            self.last_event_time = datetime.now()
            return event

        except Exception as e:
            logger.error(f"Failed to generate world event: {e}", exc_info=True)
            return None

    def _build_event_prompt(self, calendar: dict, stockpiles: dict, core_status: dict) -> str:
        """Build the LLM prompt for event generation"""
        season = calendar.get("season", "Unknown")
        week = calendar.get("week_index", 0)
        gold = stockpiles.get("gold", stockpiles.get("ore_stock_ou", 0))
        corruption = core_status.get("corruption_index", 0)

        prompt = f"""You are the Flame Chronicler for the kingdom of Emberheart, a prosperous surface kingdom in its golden age ruled by Kaelrath Emberhide, the Flamekeeper.

CURRENT KINGDOM STATE:
- Season: {season}, Week {week}
- Treasury: {gold:,} Gold
- Population: ~24,000
- Morale: Exalted

Generate a single kingdom event that fits the current state. The event should be:
1. Thematically appropriate to the season ({season})
2. Reflect the kingdom's prosperity and golden age
3. Create interesting council discussion or roleplay opportunities

Event types: Noble Proposal, District Happening, Festival, Trade News, Golem Incident, Divine Omen, Academy Event, Military Report

IMPORTANT: Respond with ONLY the event in this exact format:
EVENT_TYPE: [Noble Proposal/Festival/Trade News/Golem Incident/Divine Omen/Academy Event/Military Report]
NAME: [Event Name]
DESCRIPTION: [2-3 sentence description of what's happening in the kingdom]

Example:
EVENT_TYPE: Noble Proposal
NAME: House Zevrix Trade Expansion
DESCRIPTION: Velra Zevrix has presented a proposal to expand the Obsidian Gate trading posts along the Silkspire Trail. She claims Fae-Craft merchants are requesting permanent stalls. The council awaits the Flamekeeper's ruling.

Now generate an event for Week {week} of {season}:"""

        return prompt

    def _parse_event(self, llm_output: str, calendar: dict) -> dict:
        """Parse LLM output into structured event"""
        lines = llm_output.strip().split('\n')

        event = {
            "type": "Generic",
            "name": "Mysterious Occurrence",
            "description": llm_output,
            "timestamp": datetime.now().isoformat(),
            "week": calendar.get("week_index", 0)
        }

        # Try to parse structured format
        for line in lines:
            if line.startswith("EVENT_TYPE:"):
                event["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("NAME:"):
                event["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("DESCRIPTION:"):
                event["description"] = line.split(":", 1)[1].strip()

        return event

    async def _execute_event(self, event: dict):
        """Execute the event in Discord"""
        try:
            # Get the off-topic or designated events channel
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if not guild:
                logger.warning("No guild found, cannot post event")
                return

            # Find appropriate channel (use off-topic or create events channel)
            off_topic_id = self.bot.config.get('channel_ids', {}).get('off_topic')
            channel = None

            if off_topic_id:
                channel = guild.get_channel(off_topic_id)

            if not channel:
                logger.warning("No suitable channel found for event posting")
                return

            # Format event announcement
            announcement = f"""
╔═══════════════════════════════════════╗
║  🌍 **WORLD EVENT** 🌍                 ║
╚═══════════════════════════════════════╝

**{event['name']}**
*{event['type']}*

{event['description']}

*— The Flame Chronicler*
"""

            # Post to channel
            await channel.send(announcement)
            logger.info(f"Posted event '{event['name']}' to {channel.name}")

            # TODO: Future enhancements
            # - Create temporary channels for festivals
            # - Add special shop items
            # - Trigger NPC reactions

        except Exception as e:
            logger.error(f"Failed to execute event: {e}", exc_info=True)
