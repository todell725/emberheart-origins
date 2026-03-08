"""
Fishing Cog - Passive Fishing and Aquatic Resource Gathering System
Allows players to fish for food, pearls, and treasures
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime
from collections import Counter
from engines.fishing_engine import FishingEngine
from engines.quest_engine import QuestEngine
from core.transport import transport
from core.routing import require_channel

logger = logging.getLogger("Cog_Fishing")


class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fishing_engine = FishingEngine(llm_client=getattr(bot, 'llm', None))
        self.quest_engine = QuestEngine()
        self.transport = transport

    @commands.group(name="fish", invoke_without_command=True)
    @require_channel("idle-fishing")
    async def fish(self, ctx):
        """Fishing commands: list, spot, claim, stop"""
        if ctx.invoked_subcommand is None:
            await self.transport.send(ctx.channel, "🎣 **Fishing Commands:**\n`!fish list` - Show available spots\n`!fish spot <id>` - Start fishing\n`!fish claim` - Claim your catch\n`!fish stop` - Stop fishing")

    @fish.command(name="list")
    @require_channel("idle-fishing")
    async def fish_list(self, ctx):
        """List all available fishing spots."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        party_level = self.fishing_engine.get_party_level()

        tasks = self.fishing_engine.list_tasks()
        if not tasks:
            await self.transport.send(channel, "No fishing spots available.")
            return

        msg = ["🎣 **Available Fishing Spots:**", ""]
        for task in tasks:
            req_level = task['requirements']['min_level']
            ttk = task['idle_mechanics']['time_to_kill_sec']
            xp = task['idle_mechanics']['xp_per_kill']

            unlocked = "✅" if party_level >= req_level else "🔒"
            msg.append(f"{unlocked} **{task['task_id']}** - {task['node_name']} (Lv {req_level})")
            msg.append(f"   ⏱️ {ttk}s per catch | 💎 {xp} XP | {task['difficulty']}")
            msg.append(f"   *{task['description']}*")
            msg.append("")

        await self.transport.send(channel, "\n".join(msg))

    @fish.command(name="spot")
    @require_channel("idle-fishing")
    async def fish_spot(self, ctx, task_id: str, solo: str = None):
        """Start fishing at a spot: !fish spot FISH_001 [--solo]"""
        is_solo = solo == "--solo"
        task = await self.fishing_engine.start_task(ctx.channel.id, task_id, solo=is_solo)
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not task:
            await self.transport.send(channel, f"Fishing spot **{task_id}** not found.")
            return
        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        await self.transport.send(channel, f"🎣 **Fishing Started:** You cast your line at **{task['node_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time per Catch: **{ttk}s**")

    @fish.command(name="claim")
    @require_channel("idle-fishing")
    async def fish_claim(self, ctx):
        """Claim fish and treasures from your fishing session."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.fishing_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active fishing session to claim from.")
            return

        task = self.fishing_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Fishing Incomplete!** Need **{remaining}s** more to catch the first fish at **{task['node_name']}**.")
            return

        catch_count = int(elapsed // ttk)

        # DEBUG: Show calculation
        logger.info(f"FISHING CLAIM DEBUG: elapsed={elapsed}s, ttk={ttk}s, catches={catch_count}, math={elapsed}/{ttk}={elapsed/ttk}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * catch_count

        all_raw_drops = self.fishing_engine.roll_loot(
            task['drop_table'],
            task['idle_mechanics']['max_drops_per_kill'],
            kills=catch_count
        )

        counts = Counter(all_raw_drops)
        display_drops = [f"{item} (x{count})" if count > 1 else item for item, count in counts.items()]

        target_ids = ["PC-01"] if is_solo else None
        xp_breakdown = await self.quest_engine.combat.add_party_xp(total_xp, target_ids=target_ids, difficulty="normal", kill_count=catch_count)

        loot_breakdown = {}
        if all_raw_drops:
            loot_breakdown = await self.quest_engine.sync_loot(all_raw_drops)

        self.quest_engine.log_deed(task['task_id'], f"Fishing: {task['node_name']} {'(SOLO)' if is_solo else ''}", f"Caught {catch_count} fish. Total XP: {total_xp}")

        # Generate LLM fishing narration
        try:
            character_class = self.fishing_engine.get_character_class()
            fishing_report = await self.fishing_engine.generate_fishing_report(
                task=task,
                catch_count=catch_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate fishing report: {e}")
            fishing_report = f"You successfully fished {catch_count} times at {task['node_name']}. The waters provide."

        # Calculate romance bonding multiplier for display
        import math
        if catch_count > 1:
            bonding_multiplier = 1 + math.log10(min(catch_count, 1000))
        else:
            bonding_multiplier = 1.0

        msg = [
            "🎣 **Fishing Complete!**",
            f"*{fishing_report}*",
            "",
            f"> Location: {task['node_name']}",
            f"> Total Catches: {catch_count}",
            f"> Total XP: +{total_xp:,} XP",
        ]

        # Add debug info if debug mode is enabled
        if getattr(self.bot, 'config', {}).get('debug', False):
            msg.append(f"> Debug: {elapsed:.0f}s elapsed ÷ {ttk}s TTK = {catch_count} catches")

        if not is_solo and catch_count > 1:
            msg.append(f"> Party Bonding: {bonding_multiplier:.2f}x from fishing together")

        # Itemized Party Breakdown
        breakdown_lines = self.fishing_engine.build_party_breakdown_msg(
            xp_breakdown=xp_breakdown,
            loot_breakdown=loot_breakdown,
            total_xp=total_xp,
            all_loot=all_raw_drops
        )
        msg.extend(breakdown_lines)
        await self.transport.send(channel, "\n".join(msg))

        # Check for legendary drops to announce globally
        rare_drops = self.fishing_engine.get_rare_drops(task, all_raw_drops)
        if rare_drops:
            unique_rares = list(set([r.split(" (x")[0] for r in rare_drops]))
            event_msg = f"🔥 **[WORLD ANNOUNCEMENT]** While fishing at {task['node_name']}, the party reeled in a legendary catch: **{', '.join(unique_rares)}**!"
            import asyncio
            asyncio.create_task(self.bot.trigger_npc_event(event_msg))

        await self.fishing_engine.stop_task(ctx.channel.id)

    @fish.command(name="stop")
    @require_channel("idle-fishing")
    async def fish_stop(self, ctx):
        """Stop the current fishing session."""
        await self.fishing_engine.stop_task(ctx.channel.id)
        channel = getattr(ctx, "target_channel", ctx.channel)
        await self.transport.send(channel, "🎣 **Fishing session terminated.**")


async def setup(bot):
    await bot.add_cog(FishingCog(bot))
