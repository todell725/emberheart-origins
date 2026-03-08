"""
Hearth Downtime Mode Cog
Interactive roleplay sessions that grant mechanical buffs
"""
import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger("Cog_Hearth")

# Import romance engine for relationship bonding
try:
    from engines.romance_engine import romance_engine
    ROMANCE_ENABLED = True
except ImportError:
    ROMANCE_ENABLED = False
    logger.warning("Romance engine not available - hearth bonding disabled")


class HearthCog(commands.Cog):
    """
    Hearth downtime mode - roleplay for buffs
    """

    def __init__(self, bot):
        self.bot = bot
        self.active_hearths = {}  # player_id -> hearth_data

    @commands.command(name="hearth")
    async def hearth(self, ctx):
        """
        Start a hearth roleplay session.
        Engage with the DM for 5 minutes to earn temporary HP and buffs!
        """
        # Check if player already has an active session
        if ctx.author.id in self.active_hearths:
            return await ctx.send("🔥 You already have an active hearth session!")

        # Get hearth channel
        hearth_channel_id = self.bot.config.get('channel_ids', {}).get('hearth')
        if not hearth_channel_id:
            return await ctx.send("❌ No hearth channel configured. Add `HEARTH_CHANNEL_ID` to your `.env`.")

        hearth_channel = self.bot.get_channel(hearth_channel_id)
        if not hearth_channel:
            return await ctx.send("❌ Hearth channel not found.")

        try:
            # Initialize hearth session
            self.active_hearths[ctx.author.id] = {
                "player_id": ctx.author.id,
                "player_name": ctx.author.display_name,
                "start_time": datetime.now(),
                "message_count": 0,
                "scenario_complete": False,
                "character_id": "PC-01",
                "channel_id": hearth_channel_id
            }

            # Generate a hearth scenario
            scenario = await self._generate_hearth_scenario()

            # Send the opening prompt to the hearth channel
            welcome_msg = f"""
╔═══════════════════════════════════════╗
║  🔥 **HEARTH DOWNTIME** 🔥             ║
╚═══════════════════════════════════════╝

*{ctx.author.display_name} settles down by the fire...*

**{scenario}**

*Respond to this scenario and roleplay for at least 5 minutes (5+ messages) to earn rewards!*

**Potential Rewards:**
• +10 Temporary HP
• +1 Inspiration Point
• Morale Buff (24h)

*— The Flame Chronicler awaits your story...*
"""

            await hearth_channel.send(welcome_msg)

            # Start listening for messages
            logger.info(f"Hearth started for {ctx.author.display_name} in #{hearth_channel.name}")

            if ctx.channel.id != hearth_channel_id:
                await ctx.send(f"🔥 Hearth started! Head to {hearth_channel.mention}")

        except Exception as e:
            logger.error(f"Failed to start hearth: {e}", exc_info=True)
            self.active_hearths.pop(ctx.author.id, None)
            await ctx.send("❌ Failed to start hearth.")

    async def _generate_hearth_scenario(self) -> str:
        """
        Generate a random hearth scenario prompt
        Later this can use LLM for dynamic scenarios
        """
        scenarios = [
            "A traveling merchant approaches your fire, offering to trade stories for a warm meal. What tales do you share?",
            "The stars above seem unusually bright tonight. One constellation catches your eye and stirs a distant memory. What do you recall?",
            "A wounded animal limps into the firelight, eyeing you warily. How do you respond?",
            "Your companion asks about your greatest fear. The fire seems to dim as you consider your answer.",
            "You hear distant music on the wind - a haunting melody that reminds you of home. What memories surface?",
            "A fellow adventurer shares a tale of treasure and tragedy. They ask what drives you to risk your life for glory.",
            "The fire reveals strange symbols in the ashes. An old fortune-teller's words echo in your mind...",
            "Your newest scar aches in the cold. How did you earn it, and was the price worth paying?"
        ]

        import random
        return random.choice(scenarios)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages in the hearth channel from active session players"""
        # Ignore bot messages
        if message.author.bot:
            return

        # Check if this player has an active hearth session
        if message.author.id not in self.active_hearths:
            return

        hearth = self.active_hearths[message.author.id]

        # Only count messages in the hearth channel
        if message.channel.id != hearth.get("channel_id"):
            return

        # Increment message count
        hearth["message_count"] += 1

        # Check if they've engaged enough (5 messages over 5 minutes)
        elapsed = (datetime.now() - hearth["start_time"]).total_seconds()
        messages_needed = 5
        time_needed = 300  # 5 minutes in seconds

        if hearth["message_count"] >= messages_needed and elapsed >= time_needed:
            if not hearth["scenario_complete"]:
                await self._grant_hearth_rewards(message.channel, hearth)
                hearth["scenario_complete"] = True
                # Clean up session
                self.active_hearths.pop(message.author.id, None)
        elif hearth["message_count"] >= messages_needed and elapsed < time_needed:
            # They've sent enough messages, but not enough time has passed
            time_remaining = int(time_needed - elapsed)
            if hearth["message_count"] == messages_needed:  # Only send once
                await message.channel.send(
                    f"*The fire crackles appreciatively. Continue your story... ({time_remaining}s remaining)*"
                )
        elif hearth["message_count"] < messages_needed:
            # Encourage them to keep going
            if hearth["message_count"] == 1:
                await message.channel.send("*The Flame Chronicler listens intently...*")
            elif hearth["message_count"] == 3:
                await message.channel.send("*The flames dance as your tale unfolds...*")

    async def _grant_hearth_rewards(self, thread: discord.Thread, hearth: dict):
        """Grant rewards for completing a hearth session"""
        try:
            character_id = hearth["character_id"]
            player_name = hearth["player_name"]

            # TODO: Actually apply buffs to character state
            # For now, just announce the rewards

            # 🔥 ROMANCE INTEGRATION: Trigger relationship bonding
            romance_confessions = []
            if ROMANCE_ENABLED:
                romance_confessions = await self._process_hearth_bonding(character_id, hearth)

            rewards_msg = f"""
╔═══════════════════════════════════════╗
║  ✨ **HEARTH COMPLETE** ✨             ║
╚═══════════════════════════════════════╝

*The fire's warmth fills your soul...*

**{player_name} has earned:**
• **+10 Temporary HP** (until next rest)
• **+1 Inspiration Point**
• **Morale Buff** (24h): +1 to all skill checks

*Your spirit is renewed. The road ahead seems less daunting.*

*The hearth fades to embers as dawn approaches...*
"""

            await thread.send(rewards_msg)

            # Send romance confession messages if any occurred
            if romance_confessions:
                await asyncio.sleep(2)  # Dramatic pause
                for confession_msg in romance_confessions:
                    await thread.send(confession_msg)

            # Log the completion
            logger.info(f"Hearth completed by {player_name} ({hearth['message_count']} messages)")

            # Archive the thread after a delay
            await asyncio.sleep(60)
            await thread.edit(archived=True)

        except Exception as e:
            logger.error(f"Failed to grant hearth rewards: {e}", exc_info=True)

    async def _process_hearth_bonding(self, character_id: str, hearth: dict) -> list:
        """Process relationship bonding from hearth conversations"""
        try:
            from core.storage import load_all_character_states
            from core.relationships import relationship_manager

            # Get all party members
            all_states = load_all_character_states()
            party = [s for s in all_states if s.get("id", "").startswith("PC-")]

            confession_messages = []

            # Bond with each party member (they were all at hearth together)
            for char_state in party:
                other_id = char_state.get("id")

                # Don't bond with yourself
                if other_id == character_id:
                    continue

                # Determine conversation depth based on message count
                message_count = hearth.get("message_count", 0)
                if message_count >= 10:
                    depth = "vulnerable"  # Deep, emotional sharing
                elif message_count >= 7:
                    depth = "normal"  # Meaningful conversation
                else:
                    depth = "normal"  # Basic hearth chat

                # Trigger deep conversation bonding
                romance_engine.on_deep_conversation(character_id, other_id, emotional_depth=depth)

                # Also trigger quality time (casual)
                romance_engine.on_quality_time(character_id, other_id, activity="casual")

                # Check if confession happened
                rel = relationship_manager.get_relationship(character_id, other_id)
                if rel.get("confessed"):
                    # Check if confession was recent (happened during this hearth)
                    events = rel.get("events", [])
                    if "confession" in events[-1:]:  # Last event was confession
                        char_name = [c["name"] for c in party if c["id"] == character_id][0]
                        other_name = char_state.get("name", "Unknown")

                        confession_messages.append(
                            f"\n💕 **Something stirs in the firelight...**\n\n"
                            f"_As the flames flicker, **{char_name}** finds the courage to confess feelings for **{other_name}**._\n\n"
                            f"_The bond between them deepens..._"
                        )

            logger.info(f"Hearth bonding processed: {character_id} with {len(party)-1} party members")
            return confession_messages

        except Exception as e:
            logger.error(f"Hearth bonding failed: {e}", exc_info=True)
            return []

    @commands.command(name="hearth_status")
    async def hearth_status(self, ctx):
        """Check your current hearth progress"""
        # Find active hearth for this user
        user_hearth = None
        for thread_id, data in self.active_hearths.items():
            if data["player_id"] == ctx.author.id:
                user_hearth = data
                break

        if not user_hearth:
            await ctx.send("❌ You don't have an active hearth session.")
            return

        elapsed = (datetime.now() - user_hearth["start_time"]).total_seconds()
        messages = user_hearth["message_count"]

        await ctx.send(
            f"🔥 **Hearth Status:**\n"
            f"• Messages: {messages}/5\n"
            f"• Time: {int(elapsed)}s / 300s\n"
            f"• Status: {'✅ Ready for rewards!' if messages >= 5 and elapsed >= 300 else '⏳ Keep roleplaying...'}"
        )


async def setup(bot):
    await bot.add_cog(HearthCog(bot))
