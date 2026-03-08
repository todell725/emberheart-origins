"""
Slayer Cog for EmberHeart: Origins
Idle monster hunting system: !slayer, !tasks, !slayer claim
Ported from Claudes-EmberHeart
"""
from discord.ext import commands
import logging
from collections import Counter
from datetime import datetime
from engines.slayer_engine import SlayerEngine
from engines.quest_engine import QuestEngine
from core.routing import require_channel

logger = logging.getLogger("Cog_Slayer")

class SlayerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slayer_engine = SlayerEngine()
        self.quest_engine = QuestEngine()
        from core.transport import transport
        self.transport = transport

    @commands.group(name="slayer", invoke_without_command=True)
    @require_channel("idle-slayer")
    async def slayer(self, ctx):
        """Idle Slayer System: Hunting monsters in the background."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.slayer_engine.get_active(ctx.channel.id)

        if active:
            task = self.slayer_engine.get_task(active['task_id'])
            elapsed = int((datetime.now() - active['start_time']).total_seconds())
            ttk = task['idle_mechanics']['time_to_kill_sec']

            if active.get('solo'):
                ttk *= 4

            if elapsed >= ttk:
                await self.transport.send(channel, f"**Hunt Complete!** You have defeated the **{task['monster_name']}**.\n> Use `!slayer claim` to collect your rewards.")
            else:
                progress = (elapsed / ttk) * 100
                await self.transport.send(channel, f"**Active Hunt:** {task['monster_name']}\n> Progress: **{int(progress)}%** ({elapsed}/{ttk}s elapsed)")
        else:
            await self.transport.send(channel, "**No active slayer task.** Use `!tasks` to see targets.")

    @slayer.command(name="list")
    @require_channel("idle-slayer")
    async def slayer_list(self, ctx):
        """List all available slayer tasks."""
        tasks = self.slayer_engine.list_tasks()
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not tasks:
            await self.transport.send(channel, "**Slayer Database is empty.**")
            return

        msg = ["**Available Slayer Tasks**"]
        for t in tasks:
            msg.append(f"- **{t['task_id']}**: {t['monster_name']} (TTK: {t['idle_mechanics']['time_to_kill_sec']}s | {t['idle_mechanics']['xp_per_kill']} XP)")
            msg.append(f"> *{t['description']}*")

        await self.transport.send(channel, "\n".join(msg))

    @slayer.command(name="task")
    @require_channel("idle-slayer")
    async def slayer_task(self, ctx, task_id: str, solo: str = None):
        """Start a slayer task: !slayer task SLAYER_001 [--solo]"""
        is_solo = solo == "--solo"
        task = await self.slayer_engine.start_task(ctx.channel.id, task_id, solo=is_solo)
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not task:
            await self.transport.send(channel, f"Task **{task_id}** not found.")
            return
        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        await self.transport.send(channel, f"**Hunt Started:** You are now hunting **{task['monster_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time to Kill: **{ttk}s**")

    @slayer.command(name="claim")
    @require_channel("idle-slayer")
    async def slayer_claim(self, ctx):
        """Claim rewards from a completed hunt."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.slayer_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active hunt to claim from.")
            return

        task = self.slayer_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Hunt Incomplete!** Need **{remaining}s** more to defeat the first **{task['monster_name']}**.")
            return

        kill_count = int(elapsed // ttk)

        # DEBUG: Show calculation
        logger.info(f"SLAYER CLAIM DEBUG: elapsed={elapsed}s, ttk={ttk}s, kills={kill_count}, math={elapsed}/{ttk}={elapsed/ttk}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * kill_count

        all_raw_drops = self.slayer_engine.roll_loot(
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

        self.quest_engine.log_deed(task['task_id'], f"Slayer Grind: {task['monster_name']} {'(SOLO)' if is_solo else ''}", f"Defeated {kill_count} times in idle combat. Total XP: {total_xp}")

        # Generate LLM battle narration
        try:
            character_class = self.slayer_engine.get_character_class()
            battle_report = await self.slayer_engine.generate_battle_report(
                task=task,
                kill_count=kill_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate battle report: {e}")
            battle_report = f"You fought valiantly against the {task['monster_name']}, slaying {kill_count} in total. Victory is yours!"

        # Calculate romance bonding multiplier for display
        import math
        if kill_count > 1:
            bonding_multiplier = 1 + math.log10(min(kill_count, 1000))
        else:
            bonding_multiplier = 1.0

        msg = [
            "⚔️ **Grind Complete!**",
            f"*{battle_report}*",
            "",
            f"> Prey: {task['monster_name']}",
            f"> Total Kills: {kill_count}",
            f"> Total XP: +{total_xp:,} XP",
        ]

        # Add debug info if debug mode is enabled
        if getattr(self.bot, 'config', {}).get('debug', False):
            msg.append(f"> Debug: {elapsed:.0f}s elapsed ÷ {ttk}s TTK = {kill_count} kills")

        if not is_solo and kill_count > 1:
            msg.append(f"> Party Bonding: {bonding_multiplier:.2f}x from fighting together")

        # Itemized Party Breakdown
        breakdown_lines = self.slayer_engine.build_party_breakdown_msg(
            xp_breakdown=xp_breakdown,
            loot_breakdown=loot_breakdown,
            total_xp=total_xp,
            all_loot=all_raw_drops
        )
        msg.extend(breakdown_lines)

        await self.transport.send(channel, "\n".join(msg))

        # Check for legendary drops to announce globally
        rare_drops = self.slayer_engine.get_rare_drops(task, all_raw_drops)
        if rare_drops:
            unique_rares = list(set([r.split(" (x")[0] for r in rare_drops]))
            event_msg = f"🔥 **[WORLD ANNOUNCEMENT]** Through tireless combat, the party has obtained a legendary drop from the {task['monster_name']}: **{', '.join(unique_rares)}**!"
            import asyncio
            asyncio.create_task(self.bot.trigger_npc_event(event_msg))

        await self.slayer_engine.stop_task(ctx.channel.id)

    @slayer.command(name="stop")
    @require_channel("idle-slayer")
    async def slayer_stop(self, ctx):
        """Stop the current slayer task."""
        await self.slayer_engine.stop_task(ctx.channel.id)
        channel = getattr(ctx, "target_channel", ctx.channel)
        await self.transport.send(channel, "**Slayer task terminated.**")

    @commands.command(name="tasks", aliases=['task'])
    @require_channel("idle-slayer")
    async def cmd_tasks(self, ctx):
        """View available slayer tasks for your level."""
        level = self.slayer_engine.get_party_level()
        tasks = self.slayer_engine.list_tasks(min_level=level)
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not tasks:
            await self.transport.send(channel, f"**No tasks available for level {level}.**")
            return

        msg = [f"**Slayer Tasks Available (Level {level})**"]
        for t in tasks:
            msg.append(f"- **{t['task_id']}**: {t['monster_name']} (Lvl {t['requirements']['min_level']}+ | TTK: {t['idle_mechanics']['time_to_kill_sec']}s)")

        await self.transport.send(channel, "\n".join(msg))


async def setup(bot):
    await bot.add_cog(SlayerCog(bot))
