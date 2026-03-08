"""
Node Gathering & Archeology Minigame
Passive idle gathering that occasionally yields mysterious relics
"""
import discord
from discord.ext import commands
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger("Cog_Gathering")


class GatheringCog(commands.Cog):
    """
    Idle gathering system - excavate, fish, mine for resources and relics
    """

    def __init__(self, bot):
        self.bot = bot
        self.active_gathers = {}  # user_id -> gather_data

    @commands.group(invoke_without_command=True)
    async def gather(self, ctx):
        """Node gathering commands. Use !gather excavate, !gather fish, or !gather mine"""
        await ctx.send(
            "**Gathering Commands:**\n"
            "• `!gather excavate` - Dig for ancient relics (4-8 hours)\n"
            "• `!gather fish` - Fish for resources (2-4 hours)\n"
            "• `!gather mine` - Mine for ore (4-6 hours)\n"
            "• `!gather collect` - Collect your gathered resources"
        )

    @gather.command(name="excavate")
    async def excavate(self, ctx):
        """
        Start excavating an archeological site.
        Takes 4-8 hours. Chance to find ancient relics!
        """
        await self._start_gather(ctx, "excavate", hours=random.uniform(4, 8))

    @gather.command(name="fish")
    async def fish(self, ctx):
        """
        Start fishing in a mystical river.
        Takes 2-4 hours. Occasionally pulls up strange artifacts!
        """
        await self._start_gather(ctx, "fish", hours=random.uniform(2, 4))

    @gather.command(name="mine")
    async def mine(self, ctx):
        """
        Start mining in ancient tunnels.
        Takes 4-6 hours. Sometimes unearth buried treasures!
        """
        await self._start_gather(ctx, "mine", hours=random.uniform(4, 6))

    async def _start_gather(self, ctx, gather_type: str, hours: float):
        """Start a gathering session"""
        user_id = ctx.author.id

        if user_id in self.active_gathers:
            await ctx.send(f"❌ You're already {self.active_gathers[user_id]['type']}ing! Use `!gather collect` first.")
            return

        self.active_gathers[user_id] = {
            "type": gather_type,
            "start_time": datetime.now(),
            "duration_hours": hours,
            "character_id": "PC-01"  # TODO: Get from user
        }

        await ctx.send(
            f"⛏️ **{gather_type.capitalize()} Started!**\n"
            f"> Duration: {hours:.1f} hours\n"
            f"> Estimated completion: <t:{int((datetime.now() + timedelta(hours=hours)).timestamp())}:R>\n"
            f"> Use `!gather collect` when ready!"
        )

    @gather.command(name="collect")
    async def collect(self, ctx):
        """Collect resources from your gathering session"""
        user_id = ctx.author.id

        if user_id not in self.active_gathers:
            await ctx.send("❌ You don't have an active gathering session. Use `!gather excavate/fish/mine` to start!")
            return

        session = self.active_gathers[user_id]
        elapsed = (datetime.now() - session["start_time"]).total_seconds() / 3600  # hours

        if elapsed < session["duration_hours"]:
            remaining = session["duration_hours"] - elapsed
            await ctx.send(
                f"⏳ **Not ready yet!**\n"
                f"> Time remaining: {remaining:.1f} hours\n"
                f"> Come back later!"
            )
            return

        # Generate loot
        loot = await self._generate_gather_loot(session["type"], elapsed)

        # Add to inventory
        try:
            from core.storage import load_character_state

            character_id = session["character_id"]
            char_state = load_character_state(character_id)

            if char_state:
                inventory = char_state.setdefault("status", {}).setdefault("inventory", [])
                inventory.extend(loot["items"])

                from core.state_store import coordinator
                await coordinator.update_character_state_async(character_id, char_state)

        except Exception as e:
            logger.error(f"Failed to add loot to inventory: {e}")

        # Remove from active gathers
        del self.active_gathers[user_id]

        # Send results
        msg = [
            f"✅ **{session['type'].capitalize()} Complete!**",
            f"> Time spent: {elapsed:.1f} hours",
            ""
        ]

        if loot["items"]:
            msg.append("**Loot Found:**")
            for item in loot["items"]:
                msg.append(f"> • {item}")

        if loot.get("relic"):
            msg.append("\n✨ **RARE DISCOVERY!**")
            msg.append(loot["relic_message"])
            msg.append("> *Bring this to a scholar NPC in #off-topic to learn its history!*")

        await ctx.send("\n".join(msg))

    async def _generate_gather_loot(self, gather_type: str, hours: float) -> dict:
        """
        Generate loot from gathering session

        Args:
            gather_type: Type of gathering (excavate, fish, mine)
            hours: Duration in hours

        Returns:
            Dictionary with items and potential relic
        """
        # Base resources
        loot_tables = {
            "excavate": ["Ancient Pottery Shard", "Rusty Coin", "Bone Fragment", "Clay"],
            "fish": ["Fish (x5)", "Seaweed", "Pearl", "Driftwood"],
            "mine": ["Iron Ore (x10)", "Coal", "Quartz Crystal", "Stone"]
        }

        base_items = random.sample(loot_tables.get(gather_type, ["Junk"]), k=random.randint(2, 4))

        # 15% chance to find an unidentified relic
        found_relic = random.random() < 0.15

        result = {"items": base_items, "relic": found_relic}

        if found_relic:
            relic_id = random.randint(1000, 9999)
            relic_name = f"Unidentified Relic #{relic_id}"
            result["items"].append(relic_name)

            # Generate mysterious description
            relic_desc = await self._generate_relic_description(gather_type)
            result["relic_message"] = relic_desc

        return result

    async def _generate_relic_description(self, gather_type: str) -> str:
        """Generate mysterious relic discovery text"""
        try:
            if self.bot.llm and self.bot.llm.is_available():
                prompt = f"""You discovered an ancient relic while {gather_type}ing. Generate a mysterious, 1-2 sentence description of pulling it from the {gather_type} site.

Make it atmospheric and intriguing. Don't reveal what it does - that's for scholars to determine.

Example: "Your shovel strikes something metallic deep in the earth. As you brush away centuries of dirt, an ornate amulet glints in the fading light, covered in runes you don't recognize."

Your description:"""

                desc = await self.bot.llm.async_generate(prompt=prompt, temperature=0.8, max_tokens=80)
                return desc.strip() if desc else self._fallback_relic_description(gather_type)
            else:
                return self._fallback_relic_description(gather_type)

        except Exception as e:
            logger.error(f"Failed to generate relic description: {e}")
            return self._fallback_relic_description(gather_type)

    def _fallback_relic_description(self, gather_type: str) -> str:
        """Fallback relic descriptions"""
        descriptions = {
            "excavate": "Your shovel unearths a strange artifact covered in ancient runes. It pulses with faint magical energy.",
            "fish": "Your line snags on something heavy. You pull up a barnacle-encrusted relic from the depths.",
            "mine": "Your pickaxe breaks through into a hidden chamber. Among the rubble lies an artifact of unknown origin."
        }
        return descriptions.get(gather_type, "You found a mysterious relic!")

    @commands.command(name="relic_lore", aliases=["examine_relic"])
    async def relic_lore(self, ctx, *, relic_name: str = None):
        """
        Ask a scholar NPC about your unidentified relic.
        Generates dynamic lore and potential plot hooks!
        """
        if not relic_name:
            await ctx.send("❌ Usage: `!relic_lore <relic name>`\nExample: `!relic_lore Unidentified Relic #1234`")
            return

        try:
            from core.storage import load_character_state

            character_id = "PC-01"
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            inventory = char_state.get("status", {}).get("inventory", [])

            relic_match = next((item for item in inventory if relic_name.lower() in item.lower()), None)

            if not relic_match:
                await ctx.send(f"❌ You don't have **{relic_name}** in your inventory.")
                return

            # Generate lore via AI
            lore = await self._generate_relic_lore(relic_match)

            msg = f"""
╔═══════════════════════════════════════╗
║  📜 **SCHOLAR'S ANALYSIS** 📜          ║
╚═══════════════════════════════════════╝

*An old wizard examines the relic carefully...*

{lore}

*The scholar returns the relic to you with a grave expression.*
"""

            await ctx.send(msg)

        except Exception as e:
            logger.error(f"Failed to examine relic: {e}", exc_info=True)
            await ctx.send("❌ Failed to examine relic.")

    async def _generate_relic_lore(self, relic_name: str) -> str:
        """Generate dynamic lore for a relic"""
        try:
            if self.bot.llm and self.bot.llm.is_available():
                prompt = f"""You are an ancient scholar examining a mysterious relic. Generate 2-3 sentences of lore about this artifact.

RELIC: {relic_name}

The lore should:
1. Hint at its dark or mysterious origin
2. Suggest a potential plot hook (lost civilization, cursed bloodline, etc.)
3. Not explicitly state its powers - keep it mysterious

Example: "This medallion bears the seal of the Shadowfell Dynasty, a kingdom that vanished 500 years ago under mysterious circumstances. Legend says the last king wore this very medallion when he made his pact with the Dark Gods. I would be... careful wearing this."

Your lore:"""

                lore = await self.bot.llm.async_generate(prompt=prompt, temperature=0.85, max_tokens=120)
                return lore.strip() if lore else "This artifact is ancient and powerful. Its true purpose remains unclear."
            else:
                return "This artifact radiates old magic. Its origins are lost to time, but it clearly holds significance."

        except Exception as e:
            logger.error(f"Failed to generate relic lore: {e}")
            return "The scholar shrugs. 'I've never seen anything like this before.'"


async def setup(bot):
    await bot.add_cog(GatheringCog(bot))
