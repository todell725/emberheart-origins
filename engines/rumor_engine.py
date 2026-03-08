"""
Court Whispers Engine — EmberHeart: Origins
Posts periodic AI-generated court gossip to the #whispers channel
"""
import asyncio
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import ROOT_DIR

logger = logging.getLogger("EH_RumorEngine")

DOCS_DIR = ROOT_DIR / "docs"


class RumorEngine:
    """
    Generates periodic tavern rumors based on kingdom state and active quests.
    Posts to the #rumors channel every 8-12 hours as an NPC narrator.
    """

    def __init__(self, llm_client, bot):
        self.llm = llm_client
        self.bot = bot
        self.settlement_path = DOCS_DIR / "SETTLEMENT_STATE.json"
        self.quest_db_path = DOCS_DIR / "SIDE_QUESTS_DB.json"
        self.quest_completion_path = DOCS_DIR / "QUEST_COMPLETION.json"
        self.running = False

    async def start_rumor_loop(self):
        """Start the autonomous rumor generation loop"""
        self.running = True
        logger.info("🍺 Rumor Engine started")

        while self.running:
            try:
                # Wait 8-12 hours between rumors
                wait_hours = random.uniform(8, 12)
                await asyncio.sleep(wait_hours * 3600)

                await self.generate_rumor()

            except asyncio.CancelledError:
                logger.info("Rumor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Rumor loop error: {e}", exc_info=True)
                await asyncio.sleep(3600)

    def stop_rumor_loop(self):
        """Stop the rumor generation loop"""
        self.running = False
        logger.info("Rumor loop stopped")

    async def generate_rumor(self) -> Optional[str]:
        """Generate and post a tavern rumor"""
        try:
            # Load kingdom state
            settlement = {}
            if self.settlement_path.exists():
                settlement = json.loads(self.settlement_path.read_text(encoding='utf-8'))

            # Load uncompleted quests for hints
            uncompleted_quests = self._get_uncompleted_quests()

            # Build prompt
            prompt = self._build_rumor_prompt(settlement, uncompleted_quests)

            # Generate via LLM
            logger.info("Generating tavern rumor via LLM...")
            rumor_text = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.9,
                max_tokens=200
            )

            if not rumor_text:
                logger.warning("LLM returned empty rumor")
                return None

            # Clean up
            import re
            rumor_text = re.sub(r"<think>.*?</think>", "", rumor_text, flags=re.DOTALL).strip()

            # Post to #rumors channel
            await self._post_rumor(rumor_text)
            return rumor_text

        except Exception as e:
            logger.error(f"Failed to generate rumor: {e}", exc_info=True)
            return None

    def _get_uncompleted_quests(self) -> list:
        """Get a sample of uncompleted quests for rumor hints"""
        try:
            if not self.quest_db_path.exists():
                return []

            all_quests = json.loads(self.quest_db_path.read_text(encoding='utf-8'))

            completed = set()
            if self.quest_completion_path.exists():
                comp_data = json.loads(self.quest_completion_path.read_text(encoding='utf-8'))
                completed = set(comp_data.get("completed", []))

            uncompleted = [q for q in all_quests if q.get('id', '').upper() not in completed]

            # Return up to 3 random uncompleted quests
            return random.sample(uncompleted, min(3, len(uncompleted)))

        except Exception as e:
            logger.error(f"Failed to load quests for rumors: {e}")
            return []

    def _build_rumor_prompt(self, settlement: dict, quests: list) -> str:
        """Build the LLM prompt for rumor generation"""
        kingdom = settlement.get("settlement", {})
        season = kingdom.get("calendar", {}).get("season", "Unknown")
        ruler = kingdom.get("ruler", "the King")
        corruption = kingdom.get("core_status", {}).get("corruption_index", 0)

        quest_hints = ""
        if quests:
            hints = []
            for q in quests:
                hints.append(f"- {q.get('title', 'Unknown')}: {q.get('premise', '')[:80]}")
            quest_hints = "POTENTIAL QUEST HOOKS (subtly allude to one):\n" + "\n".join(hints)

        return f"""You are a court whisperer in the kingdom of Emberheart, a prosperous surface kingdom in its golden age ruled by Kaelrath Emberhide, the Flamekeeper, God-Ascendant.

KINGDOM STATE:
- Season: {season}
- Ruler: Kaelrath Emberhide, the Flamekeeper
- Population: ~24,000
- Morale: Exalted

{quest_hints}

Write a single short court whisper (2-3 sentences max) that might be overheard near the council chambers, the Forge Academy, or the noble quarters.
The whisper should feel organic, atmospheric, and hint at political intrigue, family dynamics, noble house dealings, or divine omens without being obvious.
Do NOT use quotation marks or speaker tags. Just write the whisper itself.
Keep it mysterious and evocative."""

    async def _post_rumor(self, rumor_text: str):
        """Post the rumor to the #rumors channel"""
        try:
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if not guild:
                logger.warning("No guild found for rumor posting")
                return

            rumors_id = self.bot.config.get('channel_ids', {}).get('rumors')
            if not rumors_id:
                logger.warning("No WHISPERS_CHANNEL_ID configured")
                return

            channel = guild.get_channel(rumors_id)
            if not channel:
                logger.warning(f"Rumors channel {rumors_id} not found")
                return

            # Format the rumor
            narrators = [
                "A Court Attendant",
                "A Whispering Noble",
                "A Forge Apprentice",
                "A Palace Guard",
                "A Visiting Merchant"
            ]
            narrator = random.choice(narrators)
            timestamp = datetime.now().strftime("%I:%M %p")

            message = (
                f"🍺 *— {narrator}, {timestamp} —*\n\n"
                f"*{rumor_text}*"
            )

            await channel.send(message)
            logger.info(f"Posted rumor to #{channel.name} as '{narrator}'")

        except Exception as e:
            logger.error(f"Failed to post rumor: {e}", exc_info=True)
