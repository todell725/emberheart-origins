"""
Dream Weaving & Visions Minigame
Players get dream fragments from resting, bring them to Oracles for prophecies
"""
import discord
from discord.ext import commands
import logging
import random
from typing import Optional

logger = logging.getLogger("Cog_Dreams")


class DreamsCog(commands.Cog):
    """
    Dream weaving system - rest mechanics with prophetic visions
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rest")
    async def rest(self, ctx):
        """
        Rest to recover HP. Sometimes you'll receive a Dream Fragment...
        """
        try:
            from core.storage import load_character_state, save_character_state

            character_id = "PC-01"  # TODO: Get from user context
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            # Calculate HP restoration
            max_hp = char_state.get("max_hp", 100)
            current_hp = char_state.get("status", {}).get("hp", max_hp)
            restored_hp = min(max_hp - current_hp, max_hp // 2)  # Restore 50% HP

            char_state.setdefault("status", {})["hp"] = current_hp + restored_hp

            # 25% chance to receive a Dream Fragment
            dream_fragment_granted = False
            if random.random() < 0.25:
                char_state.setdefault("status", {}).setdefault("inventory", []).append("Dream Fragment")
                dream_fragment_granted = True

            # Save state
            from core.state_store import coordinator
            await coordinator.update_character_state_async(character_id, char_state)

            # Build response
            msg = [
                "💤 **You settle down to rest...**",
                f"> HP Restored: +{restored_hp} ({current_hp + restored_hp}/{max_hp})",
            ]

            if dream_fragment_granted:
                msg.append("\n✨ **A strange vision haunts your dreams...**")
                msg.append("> You've obtained a **Dream Fragment**!")
                msg.append("> *Seek out an Oracle or Seer in #off-topic to interpret its meaning.*")

            await ctx.send("\n".join(msg))

        except Exception as e:
            logger.error(f"Failed to process rest: {e}", exc_info=True)
            await ctx.send("❌ Failed to rest. Please try again.")

    @commands.command(name="interpret_dream", aliases=["dream", "vision"])
    async def interpret_dream(self, ctx):
        """
        Bring your Dream Fragment to an Oracle for a prophetic vision.
        Use this in #off-topic near an Oracle NPC!
        """
        try:
            from core.storage import load_character_state, save_character_state

            character_id = "PC-01"  # TODO: Get from user context
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            # Check if player has Dream Fragment
            inventory = char_state.get("status", {}).get("inventory", [])

            if "Dream Fragment" not in inventory:
                await ctx.send("❌ You don't have a **Dream Fragment**. Use `!rest` to potentially receive one.")
                return

            # Remove Dream Fragment
            inventory.remove("Dream Fragment")
            char_state["status"]["inventory"] = inventory

            # Generate prophetic vision via LLM
            vision = await self._generate_dream_vision(character_id, char_state)

            # Save state
            from core.state_store import coordinator
            await coordinator.update_character_state_async(character_id, char_state)

            # Send vision
            msg = f"""
╔═══════════════════════════════════════╗
║  ✨ **PROPHETIC VISION** ✨            ║
╚═══════════════════════════════════════╝

*The Oracle's eyes glow as she peers into the dream fragment...*

{vision}

*The vision fades, leaving you with cryptic knowledge...*
"""

            await ctx.send(msg)

        except Exception as e:
            logger.error(f"Failed to interpret dream: {e}", exc_info=True)
            await ctx.send("❌ Failed to interpret dream. Please try again.")

    async def _generate_dream_vision(self, character_id: str, char_state: dict) -> str:
        """
        Generate a prophetic vision using LLM

        Args:
            character_id: Character ID
            char_state: Character state dictionary

        Returns:
            Prophetic vision text
        """
        try:
            # Get recent Chronicle memories and active quests
            recent_memories = self.bot.chronicle.recall("quest boss battle", top_k=3)
            memory_context = "\n".join([f"- {m.content}" for m in recent_memories]) if recent_memories else "No recent events"

            # Get active/upcoming quests
            active_quests = char_state.get("quests", {}).get("active", [])
            quest_context = f"Active quests: {', '.join(active_quests[:3])}" if active_quests else "No active quests"

            # Build LLM prompt
            prompt = f"""You are an ancient Oracle interpreting a prophetic dream. Generate a cryptic, 2-3 sentence vision.

CHARACTER CONTEXT:
- Recent events: {memory_context}
- {quest_context}

The vision should:
1. Be mysterious and symbolic (use metaphors, symbols, cryptic language)
2. Hint at an upcoming challenge or hidden opportunity
3. Reference boss weaknesses or secret loot locations (subtly!)
4. Feel like a divine vision or kingdom omen

Example: "You see a crown of bone sinking into black water. Three daggers float above it, but only the silver one draws no blood. When the moon turns red, the dead king's weakness shall be revealed."

Generate a unique prophetic vision (2-3 sentences):"""

            # Generate via LLM
            if self.bot.llm and self.bot.llm.is_available():
                vision = await self.bot.llm.async_generate(
                    prompt=prompt,
                    temperature=0.85,
                    max_tokens=150
                )
                return vision.strip() if vision else self._fallback_vision()
            else:
                return self._fallback_vision()

        except Exception as e:
            logger.error(f"Failed to generate dream vision: {e}")
            return self._fallback_vision()

    def _fallback_vision(self) -> str:
        """Fallback visions if LLM unavailable"""
        visions = [
            "You see a shadow with burning eyes, standing before three doors. The middle door bleeds light. A voice whispers: 'Only the prepared survive the flame.'",
            "A silver tree grows from a skull. Its roots drink starlight. When the tree blooms, the ancient enemy shall fall to radiant wounds.",
            "You witness yourself standing victorious over a great beast. But your blade is not steel—it is made of frozen moonlight. Seek the cold to defeat the flame.",
            "Three companions stand at a crossroads. One path leads to gold, one to glory, one to graves. The Oracle whispers: 'Choose wisdom over greed, or all shall fall.'"
        ]
        return random.choice(visions)


async def setup(bot):
    await bot.add_cog(DreamsCog(bot))
