"""
Woodcutting Cog - Passive Lumber Harvesting System
Allows players to chop trees for wood, seeds, and forest resources
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime
from collections import Counter
from engines.woodcutting_engine import WoodcuttingEngine
from engines.quest_engine import QuestEngine
from core.transport import transport
from core.routing import require_channel

logger = logging.getLogger("Cog_Woodcutting")


class WoodcuttingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.woodcutting_engine = WoodcuttingEngine(llm_client=getattr(bot, 'llm', None))
        self.quest_engine = QuestEngine()
        self.transport = transport

    @commands.group(name="chop", invoke_without_command=True)
    @require_channel("idle-woodcutting")
    async def chop(self, ctx):
        """Woodcutting commands: list, tree, claim, stop"""
        if ctx.invoked_subcommand is None:
            await self.transport.send(ctx.channel, "🪓 **Woodcutting Commands:**\n`!chop list` - Show available trees\n`!chop tree <id>` - Start chopping\n`!chop claim` - Claim your lumber\n`!chop stop` - Stop chopping")

    @chop.command(name="list")
    @require_channel("idle-woodcutting")
    async def chop_list(self, ctx):
        """List all available trees."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        party_level = self.woodcutting_engine.get_party_level()

        tasks = self.woodcutting_engine.list_tasks()
        if not tasks:
            await self.transport.send(channel, "No trees available.")
            return

        msg = ["🪓 **Available Trees:**", ""]
        for task in tasks:
            req_level = task['requirements']['min_level']
            ttk = task['idle_mechanics']['time_to_kill_sec']
            xp = task['idle_mechanics']['xp_per_kill']

            unlocked = "✅" if party_level >= req_level else "🔒"
            msg.append(f"{unlocked} **{task['task_id']}** - {task['node_name']} (Lv {req_level})")
            msg.append(f"   ⏱️ {ttk}s per tree | 💎 {xp} XP | {task['difficulty']}")
            msg.append(f"   *{task['description']}*")
            msg.append("")

        await self.transport.send(channel, "\n".join(msg))

    @chop.command(name="tree")
    @require_channel("idle-woodcutting")
    async def chop_tree(self, ctx, task_id: str, solo: str = None):
        """Start chopping a tree: !chop tree WOOD_001 [--solo]"""
        is_solo = solo == "--solo"
        task = await self.woodcutting_engine.start_task(ctx.channel.id, task_id, solo=is_solo)
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not task:
            await self.transport.send(channel, f"Tree **{task_id}** not found.")
            return
        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        await self.transport.send(channel, f"🪓 **Woodcutting Started:** You begin chopping **{task['node_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time per Tree: **{ttk}s**")

    @chop.command(name="claim")
    @require_channel("idle-woodcutting")
    async def chop_claim(self, ctx):
        """Claim lumber from your woodcutting session."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.woodcutting_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active woodcutting session to claim from.")
            return

        task = self.woodcutting_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Chopping Incomplete!** Need **{remaining}s** more to fell the first **{task['node_name']}**.")
            return

        tree_count = int(elapsed // ttk)

        # DEBUG: Show calculation
        logger.info(f"WOODCUTTING CLAIM DEBUG: elapsed={elapsed}s, ttk={ttk}s, trees={tree_count}, math={elapsed}/{ttk}={elapsed/ttk}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * tree_count

        all_raw_drops = self.woodcutting_engine.roll_loot(
            task['drop_table'],
            task['idle_mechanics']['max_drops_per_kill'],
            kills=tree_count
        )

        counts = Counter(all_raw_drops)
        display_drops = [f"{item} (x{count})" if count > 1 else item for item, count in counts.items()]

        target_ids = ["PC-01"] if is_solo else None
        xp_breakdown = await self.quest_engine.combat.add_party_xp(total_xp, target_ids=target_ids, difficulty="normal", kill_count=tree_count)

        loot_breakdown = {}
        if all_raw_drops:
            loot_breakdown = await self.quest_engine.sync_loot(all_raw_drops)

        self.quest_engine.log_deed(task['task_id'], f"Woodcutting: {task['node_name']} {'(SOLO)' if is_solo else ''}", f"Felled {tree_count} trees. Total XP: {total_xp}")

        # Generate LLM woodcutting narration
        try:
            character_class = self.woodcutting_engine.get_character_class()
            woodcutting_report = await self.woodcutting_engine.generate_woodcutting_report(
                task=task,
                tree_count=tree_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate woodcutting report: {e}")
            woodcutting_report = f"You successfully felled {tree_count} {task['node_name']}. The forest provides its bounty."

        # Calculate romance bonding multiplier for display
        import math
        if tree_count > 1:
            bonding_multiplier = 1 + math.log10(min(tree_count, 1000))
        else:
            bonding_multiplier = 1.0

        msg = [
            "🪓 **Woodcutting Complete!**",
            f"*{woodcutting_report}*",
            "",
            f"> Trees: {task['node_name']}",
            f"> Total Felled: {tree_count}",
            f"> Total XP: +{total_xp:,} XP",
        ]

        # Add debug info if debug mode is enabled
        if getattr(self.bot, 'config', {}).get('debug', False):
            msg.append(f"> Debug: {elapsed:.0f}s elapsed ÷ {ttk}s TTK = {tree_count} trees")

        if not is_solo and tree_count > 1:
            msg.append(f"> Party Bonding: {bonding_multiplier:.2f}x from chopping together")

        # Itemized Party Breakdown
        breakdown_lines = self.woodcutting_engine.build_party_breakdown_msg(
            xp_breakdown=xp_breakdown,
            loot_breakdown=loot_breakdown,
            total_xp=total_xp,
            all_loot=all_raw_drops
        )
        msg.extend(breakdown_lines)
        await self.transport.send(channel, "\n".join(msg))

        # Check for legendary drops to announce globally
        rare_drops = self.woodcutting_engine.get_rare_drops(task, all_raw_drops)
        if rare_drops:
            unique_rares = list(set([r.split(" (x")[0] for r in rare_drops]))
            event_msg = f"🔥 **[WORLD ANNOUNCEMENT]** While chopping {task['node_name']}, the party unearthed a legendary resource: **{', '.join(unique_rares)}**!"
            import asyncio
            asyncio.create_task(self.bot.trigger_npc_event(event_msg))

        await self.woodcutting_engine.stop_task(ctx.channel.id)

    @chop.command(name="stop")
    @require_channel("idle-woodcutting")
    async def chop_stop(self, ctx):
        """Stop the current woodcutting session."""
        await self.woodcutting_engine.stop_task(ctx.channel.id)
        channel = getattr(ctx, "target_channel", ctx.channel)
        await self.transport.send(channel, "🪓 **Woodcutting session terminated.**")


async def setup(bot):
    await bot.add_cog(WoodcuttingCog(bot))
