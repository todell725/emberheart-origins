"""
Hunting Cog - Passive Wildlife Hunting System
Allows players to hunt deer, rabbits, and other wildlife for resources
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime
from collections import Counter
from engines.hunting_engine import HuntingEngine
from engines.quest_engine import QuestEngine
from core.transport import transport
from core.routing import require_channel

logger = logging.getLogger("Cog_Hunting")


class HuntingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hunting_engine = HuntingEngine(llm_client=getattr(bot, 'llm', None))
        self.quest_engine = QuestEngine()
        self.transport = transport

    @commands.group(name="hunt", invoke_without_command=True)
    @require_channel("passive-hunting")
    async def hunt(self, ctx):
        """Hunting commands: task, claim, stop, list"""
        if ctx.invoked_subcommand is None:
            await self.transport.send(ctx.channel, "🏹 **Hunting Commands:**\n`!hunt list` - Show available hunts\n`!hunt task <id>` - Start hunting\n`!hunt claim` - Claim your harvest\n`!hunt stop` - Stop hunting")

    @hunt.command(name="list")
    @require_channel("passive-hunting")
    async def hunt_list(self, ctx):
        """List all available hunting tasks."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        party_level = self.hunting_engine.get_party_level()

        tasks = self.hunting_engine.list_tasks()
        if not tasks:
            await self.transport.send(channel, "No hunting tasks available.")
            return

        msg = ["🏹 **Available Hunts:**", ""]
        for task in tasks:
            req_level = task['requirements']['min_level']
            ttk = task['idle_mechanics']['time_to_kill_sec']
            xp = task['idle_mechanics']['xp_per_kill']

            unlocked = "✅" if party_level >= req_level else "🔒"
            msg.append(f"{unlocked} **{task['task_id']}** - {task['creature_name']} (Lv {req_level})")
            msg.append(f"   ⏱️ {ttk}s per kill | 💎 {xp} XP | {task['difficulty']}")
            msg.append(f"   *{task['description']}*")
            msg.append("")

        await self.transport.send(channel, "\n".join(msg))

    @hunt.command(name="task")
    @require_channel("passive-hunting")
    async def hunt_task(self, ctx, task_id: str, solo: str = None):
        """Start a hunting task: !hunt task HUNT_001 [--solo]"""
        is_solo = solo == "--solo"
        task = await self.hunting_engine.start_task(ctx.channel.id, task_id, solo=is_solo)
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not task:
            await self.transport.send(channel, f"Hunt **{task_id}** not found.")
            return
        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        await self.transport.send(channel, f"🏹 **Hunt Started:** You begin tracking **{task['creature_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time per Kill: **{ttk}s**")

    @hunt.command(name="claim")
    @require_channel("passive-hunting")
    async def hunt_claim(self, ctx):
        """Claim resources from your hunt."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.hunting_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active hunt to claim from.")
            return

        task = self.hunting_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Hunt Incomplete!** Need **{remaining}s** more to track the first **{task['creature_name']}**.")
            return

        kill_count = int(elapsed // ttk)

        # DEBUG: Show calculation
        logger.info(f"HUNT CLAIM DEBUG: elapsed={elapsed}s, ttk={ttk}s, kills={kill_count}, math={elapsed}/{ttk}={elapsed/ttk}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * kill_count

        all_raw_drops = self.hunting_engine.roll_loot(
            task['drop_table'],
            task['idle_mechanics']['max_drops_per_kill'],
            kills=kill_count
        )

        counts = Counter(all_raw_drops)
        display_drops = [f"{item} (x{count})" if count > 1 else item for item, count in counts.items()]

        target_ids = ["PC-01"] if is_solo else None
        xp_breakdown = await self.quest_engine.combat.add_party_xp(total_xp, target_ids=target_ids, difficulty="normal", kill_count=kill_count)

        loot_breakdown = {}
        if all_raw_drops:
            loot_breakdown = await self.quest_engine.sync_loot(all_raw_drops)

        self.quest_engine.log_deed(task['task_id'], f"Hunting: {task['creature_name']} {'(SOLO)' if is_solo else ''}", f"Hunted {kill_count} times. Total XP: {total_xp}")

        # Generate LLM hunt narration
        try:
            character_class = self.hunting_engine.get_character_class()
            hunt_report = await self.hunting_engine.generate_hunt_report(
                task=task,
                kill_count=kill_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate hunt report: {e}")
            hunt_report = f"You successfully hunted {kill_count} {task['creature_name']}. The wilderness provides."

        # Calculate romance bonding multiplier for display
        import math
        if kill_count > 1:
            bonding_multiplier = 1 + math.log10(min(kill_count, 1000))
        else:
            bonding_multiplier = 1.0

        msg = [
            "🏹 **Hunt Complete!**",
            f"*{hunt_report}*",
            "",
            f"> Prey: {task['creature_name']}",
            f"> Total Kills: {kill_count}",
        ]

        if not is_solo and kill_count > 1:
            msg.append(f"> Party Bonding: {bonding_multiplier:.2f}x from hunting together")

        # Itemized Party Breakdown
        breakdown_lines = self.hunting_engine.build_party_breakdown_msg(
            xp_breakdown=xp_breakdown,
            loot_breakdown=loot_breakdown,
            total_xp=total_xp,
            all_loot=all_raw_drops
        )
        msg.extend(breakdown_lines)

        await self.transport.send(channel, "\n".join(msg))

        # Check for legendary drops to announce globally
        rare_drops = self.hunting_engine.get_rare_drops(task, all_raw_drops)
        if rare_drops:
            unique_rares = list(set([r.split(" (x")[0] for r in rare_drops]))
            event_msg = f"🔥 **[WORLD ANNOUNCEMENT]** While hunting the {task['creature_name']}, the party acquired a rare legendary prize: **{', '.join(unique_rares)}**!"
            import asyncio
            asyncio.create_task(self.bot.trigger_npc_event(event_msg))

        await self.hunting_engine.stop_task(ctx.channel.id)

    @hunt.command(name="stop")
    @require_channel("passive-hunting")
    async def hunt_stop(self, ctx):
        """Stop the current hunting task."""
        await self.hunting_engine.stop_task(ctx.channel.id)
        channel = getattr(ctx, "target_channel", ctx.channel)
        await self.transport.send(channel, "🏹 **Hunting task terminated.**")


async def setup(bot):
    await bot.add_cog(HuntingCog(bot))
