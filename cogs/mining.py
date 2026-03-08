"""
Mining Cog - Passive Ore and Gem Excavation System
Allows players to mine ores, gems, and minerals
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime
from collections import Counter
from engines.mining_engine import MiningEngine
from engines.quest_engine import QuestEngine
from core.transport import transport
from core.routing import require_channel

logger = logging.getLogger("Cog_Mining")


class MiningCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mining_engine = MiningEngine(llm_client=getattr(bot, 'llm', None))
        self.quest_engine = QuestEngine()
        self.transport = transport

    @commands.group(name="mine", invoke_without_command=True)
    @require_channel("idle-mining")
    async def mine(self, ctx):
        """Mining commands: list, node, claim, stop"""
        if ctx.invoked_subcommand is None:
            await self.transport.send(ctx.channel, "⛏️ **Mining Commands:**\n`!mine list` - Show available deposits\n`!mine node <id>` - Start mining\n`!mine claim` - Claim your ore\n`!mine stop` - Stop mining")

    @mine.command(name="list")
    @require_channel("idle-mining")
    async def mine_list(self, ctx):
        """List all available mining nodes."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        party_level = self.mining_engine.get_party_level()

        tasks = self.mining_engine.list_tasks()
        if not tasks:
            await self.transport.send(channel, "No mining nodes available.")
            return

        msg = ["⛏️ **Available Mining Nodes:**", ""]
        for task in tasks:
            req_level = task['requirements']['min_level']
            ttk = task['idle_mechanics']['time_to_kill_sec']
            xp = task['idle_mechanics']['xp_per_kill']

            unlocked = "✅" if party_level >= req_level else "🔒"
            msg.append(f"{unlocked} **{task['task_id']}** - {task['node_name']} (Lv {req_level})")
            msg.append(f"   ⏱️ {ttk}s per node | 💎 {xp} XP | {task['difficulty']}")
            msg.append(f"   *{task['description']}*")
            msg.append("")

        await self.transport.send(channel, "\n".join(msg))

    @mine.command(name="node")
    @require_channel("idle-mining")
    async def mine_node(self, ctx, task_id: str, solo: str = None):
        """Start mining a deposit: !mine node MINE_001 [--solo]"""
        is_solo = solo == "--solo"
        task = await self.mining_engine.start_task(ctx.channel.id, task_id, solo=is_solo)
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not task:
            await self.transport.send(channel, f"Mining node **{task_id}** not found.")
            return
        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        await self.transport.send(channel, f"⛏️ **Mining Started:** You begin excavating **{task['node_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time per Node: **{ttk}s**")

    @mine.command(name="claim")
    @require_channel("idle-mining")
    async def mine_claim(self, ctx):
        """Claim ore and gems from your mining session."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.mining_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active mining session to claim from.")
            return

        task = self.mining_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Mining Incomplete!** Need **{remaining}s** more to excavate the first **{task['node_name']}**.")
            return

        node_count = int(elapsed // ttk)

        # DEBUG: Show calculation
        logger.info(f"MINING CLAIM DEBUG: elapsed={elapsed}s, ttk={ttk}s, nodes={node_count}, math={elapsed}/{ttk}={elapsed/ttk}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * node_count

        all_raw_drops = self.mining_engine.roll_loot(
            task['drop_table'],
            task['idle_mechanics']['max_drops_per_kill'],
            kills=node_count
        )

        counts = Counter(all_raw_drops)
        display_drops = [f"{item} (x{count})" if count > 1 else item for item, count in counts.items()]

        target_ids = ["PC-01"] if is_solo else None
        xp_breakdown = await self.quest_engine.combat.add_party_xp(total_xp, target_ids=target_ids, difficulty="normal", kill_count=node_count)

        loot_breakdown = {}
        if all_raw_drops:
            loot_breakdown = await self.quest_engine.sync_loot(all_raw_drops)

        self.quest_engine.log_deed(task['task_id'], f"Mining: {task['node_name']} {'(SOLO)' if is_solo else ''}", f"Mined {node_count} nodes. Total XP: {total_xp}")

        # Generate LLM mining narration
        try:
            character_class = self.mining_engine.get_character_class()
            mining_report = await self.mining_engine.generate_mining_report(
                task=task,
                node_count=node_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate mining report: {e}")
            mining_report = f"You successfully mined {node_count} {task['node_name']} deposits. The earth provides its riches."

        # Calculate romance bonding multiplier for display
        import math
        if node_count > 1:
            bonding_multiplier = 1 + math.log10(min(node_count, 1000))
        else:
            bonding_multiplier = 1.0

        msg = [
            "⛏️ **Mining Complete!**",
            f"*{mining_report}*",
            "",
            f"> Deposit: {task['node_name']}",
            f"> Total Nodes: {node_count}",
            f"> Total XP: +{total_xp:,} XP",
        ]

        # Add debug info if debug mode is enabled
        if getattr(self.bot, 'config', {}).get('debug', False):
            msg.append(f"> Debug: {elapsed:.0f}s elapsed ÷ {ttk}s TTK = {node_count} nodes")

        if not is_solo and node_count > 1:
            msg.append(f"> Party Bonding: {bonding_multiplier:.2f}x from mining together")

        # Itemized Party Breakdown
        breakdown_lines = self.mining_engine.build_party_breakdown_msg(
            xp_breakdown=xp_breakdown,
            loot_breakdown=loot_breakdown,
            total_xp=total_xp,
            all_loot=all_raw_drops
        )
        msg.extend(breakdown_lines)
        await self.transport.send(channel, "\n".join(msg))

        # Check for legendary drops to announce globally
        rare_drops = self.mining_engine.get_rare_drops(task, all_raw_drops)
        if rare_drops:
            unique_rares = list(set([r.split(" (x")[0] for r in rare_drops]))
            event_msg = f"🔥 **[WORLD ANNOUNCEMENT]** Deep in the mines at {task['node_name']}, the party struck legendary resources: **{', '.join(unique_rares)}**!"
            import asyncio
            asyncio.create_task(self.bot.trigger_npc_event(event_msg))

        await self.mining_engine.stop_task(ctx.channel.id)

    @mine.command(name="stop")
    @require_channel("idle-mining")
    async def mine_stop(self, ctx):
        """Stop the current mining session."""
        await self.mining_engine.stop_task(ctx.channel.id)
        channel = getattr(ctx, "target_channel", ctx.channel)
        await self.transport.send(channel, "⛏️ **Mining session terminated.**")


async def setup(bot):
    await bot.add_cog(MiningCog(bot))
