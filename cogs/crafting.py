from discord.ext import commands
from engines.crafting_engine import CraftingEngine
from core.routing import require_channel
from engines.quest_engine import QuestEngine
from datetime import datetime, timedelta
from collections import Counter
import logging

logger = logging.getLogger("Cog_Crafting")

class CraftingCog(commands.Cog):
    """Cog for the Idle Crafting Skill."""

    def __init__(self, bot):
        self.bot = bot
        self.crafting_engine = CraftingEngine(llm_client=bot.llm)
        self.quest_engine = QuestEngine()
        from core.transport import transport
        self.transport = transport

    @commands.group(name="craft", invoke_without_command=True)
    @require_channel("idle-crafting")
    async def craft(self, ctx):
        """Idle Crafting Commands. Use `!craft list` to see recipes."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.crafting_engine.get_active(channel.id)

        if active:
            task = self.crafting_engine.get_task(active['task_id'])
            elapsed = (datetime.now() - active['start_time']).total_seconds()
            ttk = task['idle_mechanics']['time_to_kill_sec']

            is_solo = active.get('solo')
            if is_solo:
                ttk *= 4

            crafted = int(elapsed // ttk)
            
            msg = f"🧵 **Active Crafting:** {task['recipe_name']}{' (SOLO)' if is_solo else ''}"
            msg += f"\n> ⏳ Time Elapsed: {int(elapsed)}s"
            msg += f"\n> 🛠️ Items Pending Claim: **{crafted}**"
            msg += f"\n> ⏱️ Next item in: {int(ttk - (elapsed % ttk))}s"
            await self.transport.send(channel, msg)
        else:
            await self.transport.send(channel, "🧵 **The workshop is empty.** Use `!craft list` to find a project and `!craft recipe <id>` to start making gear.")

    @craft.command(name="list")
    @require_channel("idle-crafting")
    async def craft_list(self, ctx):
        """List all available crafting recipes."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        party_level = self.crafting_engine.get_party_level()
        tasks = self.crafting_engine.list_tasks(min_level=party_level)

        if not tasks:
            await self.transport.send(channel, f"You are not high enough level to craft anything yet.")
            return

        lines = [f"**🧵 Available Crafting Projects *(Party Lvl {party_level})***"]
        for t in tasks:
            req_str = ", ".join([f"{qty}x {item}" for item, qty in t.get("ingredients", {}).items()])
            lines.append(f"`{t['task_id']}`: **{t['recipe_name']}** (Lvl {t['requirements']['min_level']}) | Requires: {req_str}")
            
        await self.transport.send(channel, "\n".join(lines))

    @craft.command(name="recipe")
    @require_channel("idle-crafting")
    async def craft_recipe(self, ctx, task_id: str, mode: str = "party"):
        """Start a crafting project. !craft recipe CRAFT_001 [solo]"""
        channel = getattr(ctx, "target_channel", ctx.channel)
        task = self.crafting_engine.get_task(task_id)

        if not task:
            await self.transport.send(channel, f"Recipe `{task_id}` not found.")
            return

        party_level = self.crafting_engine.get_party_level()
        if party_level < task['requirements']['min_level']:
            await self.transport.send(channel, f"**Level Too Low!** You need to be level {task['requirements']['min_level']} to craft this.")
            return

        is_solo = mode.lower() == "solo"
        started = await self.crafting_engine.start_task(channel.id, task_id, solo=is_solo)

        if not started:
            await self.transport.send(channel, "Failed to start the project.")
            return

        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        req_str = ", ".join([f"{qty}x {item}" for item, qty in task.get("ingredients", {}).items()])
        await self.transport.send(channel, f"🧵 **Workshop Active:** You begin crafting **{task['recipe_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time per Item: **{ttk}s**\nConsumes: {req_str}")

    @craft.command(name="claim")
    @require_channel("idle-crafting")
    async def craft_claim(self, ctx):
        """Claim finished crafts."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.crafting_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active crafting session to claim from.")
            return

        task = self.crafting_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Work Incomplete!** Need **{remaining}s** more to finish the first **{task['recipe_name']}**.")
            return

        max_crafts = int(elapsed // ttk)
        ingredients = task.get("ingredients", {})
        
        craft_count = await self.crafting_engine.consume_party_ingredients(ingredients, max_crafts)

        if craft_count <= 0:
            req_str = ", ".join([f"{q}x {i}" for i, q in ingredients.items()])
            await self.transport.send(channel, f"🛑 **Out of materials!** You cannot craft this without resources.\n> **Required:** {req_str}")
            await self.crafting_engine.stop_task(channel.id)
            return

        if craft_count < max_crafts:
            time_spent = craft_count * ttk
            active['start_time'] = datetime.now() - timedelta(seconds=(elapsed - time_spent))
            await self.crafting_engine._save_active()
            await self.transport.send(channel, f"🛑 **Materials Depleted!** Stopped early after crafting **{craft_count}** items.")
            await self.crafting_engine.stop_task(channel.id)
        else:
            time_spent = craft_count * ttk
            active['start_time'] += timedelta(seconds=time_spent)
            await self.crafting_engine._save_active()

        logger.info(f"CRAFTING CLAIM DEBUG: crafts={craft_count}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * craft_count

        all_raw_drops = self.crafting_engine.roll_loot(
            task['drop_table'],
            task['idle_mechanics']['max_drops_per_kill'],
            kills=craft_count
        )

        target_ids = ["PC-01"] if is_solo else None
        xp_breakdown = await self.quest_engine.combat.add_party_xp(total_xp, target_ids=target_ids, difficulty="normal", kill_count=craft_count)

        loot_breakdown = {}
        if all_raw_drops:
            loot_breakdown = await self.quest_engine.sync_loot(all_raw_drops)

        self.quest_engine.log_deed(task['task_id'], f"Crafting: {task['recipe_name']} {'(SOLO)' if is_solo else ''}", f"Produced {craft_count} items. Total XP: {total_xp}")

        try:
            character_class = self.crafting_engine.get_character_class()
            crafting_report = await self.crafting_engine.generate_crafting_report(
                task=task,
                recipe_count=craft_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate crafting report: {e}")
            crafting_report = f"You successfully crafted {craft_count} {task['recipe_name']} items."

        msg_lines = [
            f"**🧵 Crafting Session Complete**",
            f"*{crafting_report}*",
            f"",
            f"> **Total XP:** +{total_xp:,}",
        ]

        # Add debug info if debug mode is enabled
        if getattr(self.bot, 'config', {}).get('debug', False):
            msg_lines.append(f"> **Debug:** Generated {craft_count} ticks of loot.")

        breakdown_lines = self.crafting_engine.build_party_breakdown_msg(
            xp_breakdown, loot_breakdown, total_xp, all_raw_drops
        )
        msg_lines.extend(breakdown_lines)

        await self.transport.send(channel, "\n".join(msg_lines))

        # Check for legendary drops to announce globally
        rare_drops = self.crafting_engine.get_rare_drops(task, all_raw_drops)
        if rare_drops:
            unique_rares = list(set([r.split(" (x")[0] for r in rare_drops]))
            event_msg = f"🔥 **[WORLD ANNOUNCEMENT]** An artisan has just crafted a legendary artifact: **{', '.join(unique_rares)}**!"
            import asyncio
            asyncio.create_task(self.bot.trigger_npc_event(event_msg))

        # Generate 5e stat blocks for new custom items in the background
        from core.item_generator import generate_custom_item_stats
        import asyncio
        
        unique_items = list(set([item for item in all_raw_drops if " (x" not in item]))
        for item_name in unique_items:
            asyncio.create_task(
                generate_custom_item_stats(self.bot.llm, item_name, task.get('description', ''))
            )

    @craft.command(name="stop")
    @require_channel("idle-crafting")
    async def craft_stop(self, ctx):
        """Stop the active crafting session and claim any finished progress."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.crafting_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active crafting session to stop.")
            return

        await self.craft_claim(ctx) # Claim first
        
        # Double check it wasn't already stopped by lack of materials inside claim
        if self.crafting_engine.get_active(channel.id):
            await self.crafting_engine.stop_task(channel.id)
            await self.transport.send(channel, "🛑 **Crafting session formally concluded.**")


async def setup(bot):
    await bot.add_cog(CraftingCog(bot))
