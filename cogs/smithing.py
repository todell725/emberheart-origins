from discord.ext import commands
from engines.smithing_engine import SmithingEngine
from core.routing import require_channel
from engines.quest_engine import QuestEngine
from datetime import datetime, timedelta
from collections import Counter
import logging

logger = logging.getLogger("Cog_Smithing")

class SmithingCog(commands.Cog):
    """Cog for the Idle Smithing Skill."""

    def __init__(self, bot):
        self.bot = bot
        self.smithing_engine = SmithingEngine(llm_client=bot.llm)
        self.quest_engine = QuestEngine()
        from core.transport import transport
        self.transport = transport

    @commands.group(name="smith", invoke_without_command=True)
    @require_channel("idle-smithing")
    async def smith(self, ctx):
        """Idle Smithing Commands. Use `!smith list` to see blueprints."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.smithing_engine.get_active(channel.id)

        if active:
            task = self.smithing_engine.get_task(active['task_id'])
            elapsed = (datetime.now() - active['start_time']).total_seconds()
            ttk = task['idle_mechanics']['time_to_kill_sec']

            is_solo = active.get('solo')
            if is_solo:
                ttk *= 4

            smithed = int(elapsed // ttk)
            
            msg = f"⚒️ **Active Forge:** {task['recipe_name']}{' (SOLO)' if is_solo else ''}"
            msg += f"\n> ⏳ Time Elapsed: {int(elapsed)}s"
            msg += f"\n> 🛡️ Items Pending Claim: **{smithed}**"
            msg += f"\n> ⏱️ Next item in: {int(ttk - (elapsed % ttk))}s"
            await self.transport.send(channel, msg)
        else:
            await self.transport.send(channel, "⚒️ **The forge is cold.** Use `!smith list` to find a blueprint and `!smith recipe <id>` to strike the anvil.")

    @smith.command(name="list")
    @require_channel("idle-smithing")
    async def smith_list(self, ctx):
        """List all available smithing blueprints."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        party_level = self.smithing_engine.get_party_level()
        tasks = self.smithing_engine.list_tasks(min_level=party_level)

        if not tasks:
            await self.transport.send(channel, f"You are not high enough level to smith anything yet.")
            return

        lines = [f"**⚒️ Available Smithing Blueprints *(Party Lvl {party_level})***"]
        for t in tasks:
            req_str = ", ".join([f"{qty}x {item}" for item, qty in t.get("ingredients", {}).items()])
            lines.append(f"`{t['task_id']}`: **{t['recipe_name']}** (Lvl {t['requirements']['min_level']}) | Requires: {req_str}")
            
        await self.transport.send(channel, "\n".join(lines))

    @smith.command(name="recipe")
    @require_channel("idle-smithing")
    async def smith_recipe(self, ctx, task_id: str, mode: str = "party"):
        """Start a smithing project. !smith recipe SMITH_001 [solo]"""
        channel = getattr(ctx, "target_channel", ctx.channel)
        task = self.smithing_engine.get_task(task_id)

        if not task:
            await self.transport.send(channel, f"Blueprint `{task_id}` not found.")
            return

        party_level = self.smithing_engine.get_party_level()
        if party_level < task['requirements']['min_level']:
            await self.transport.send(channel, f"**Level Too Low!** You need to be level {task['requirements']['min_level']} to smith this.")
            return

        is_solo = mode.lower() == "solo"
        started = await self.smithing_engine.start_task(channel.id, task_id, solo=is_solo)

        if not started:
            await self.transport.send(channel, "Failed to light the forge.")
            return

        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        req_str = ", ".join([f"{qty}x {item}" for item, qty in task.get("ingredients", {}).items()])
        await self.transport.send(channel, f"⚒️ **Forge Lit:** You begin striking **{task['recipe_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time per Item: **{ttk}s**\nConsumes: {req_str}")

    @smith.command(name="claim")
    @require_channel("idle-smithing")
    async def smith_claim(self, ctx):
        """Claim finished products from the forge."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.smithing_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active forging session to claim from.")
            return

        task = self.smithing_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Metal still hot!** Need **{remaining}s** more to cool the first **{task['recipe_name']}**.")
            return

        max_crafts = int(elapsed // ttk)
        ingredients = task.get("ingredients", {})
        
        craft_count = await self.smithing_engine.consume_party_ingredients(ingredients, max_crafts)

        if craft_count <= 0:
            req_str = ", ".join([f"{q}x {i}" for i, q in ingredients.items()])
            await self.transport.send(channel, f"🛑 **Out of ores/coal!** You cannot forge this without resources.\n> **Required:** {req_str}")
            await self.smithing_engine.stop_task(channel.id)
            return

        if craft_count < max_crafts:
            time_spent = craft_count * ttk
            active['start_time'] = datetime.now() - timedelta(seconds=(elapsed - time_spent))
            await self.smithing_engine._save_active()
            await self.transport.send(channel, f"🛑 **Materials Depleted!** Dropped the hammer early after forging **{craft_count}** items.")
            await self.smithing_engine.stop_task(channel.id)
        else:
            time_spent = craft_count * ttk
            active['start_time'] += timedelta(seconds=time_spent)
            await self.smithing_engine._save_active()

        logger.info(f"SMITHING CLAIM DEBUG: smithed={craft_count}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * craft_count

        all_raw_drops = self.smithing_engine.roll_loot(
            task['drop_table'],
            task['idle_mechanics']['max_drops_per_kill'],
            kills=craft_count
        )

        target_ids = ["PC-01"] if is_solo else None
        xp_breakdown = await self.quest_engine.combat.add_party_xp(total_xp, target_ids=target_ids, difficulty="normal", kill_count=craft_count)

        loot_breakdown = {}
        if all_raw_drops:
            loot_breakdown = await self.quest_engine.sync_loot(all_raw_drops)

        self.quest_engine.log_deed(task['task_id'], f"Smithing: {task['recipe_name']} {'(SOLO)' if is_solo else ''}", f"Forged {craft_count} items. Total XP: {total_xp}")

        try:
            character_class = self.smithing_engine.get_character_class()
            smithing_report = await self.smithing_engine.generate_smithing_report(
                task=task,
                recipe_count=craft_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate smithing report: {e}")
            smithing_report = f"You successfully pulled {craft_count} {task['recipe_name']} items from the anvil."

        msg_lines = [
            f"**⚒️ Forging Session Complete**",
            f"*{smithing_report}*",
            f"",
            f"> **Total XP:** +{total_xp:,}",
        ]

        # Add debug info if debug mode is enabled
        if getattr(self.bot, 'config', {}).get('debug', False):
            msg_lines.append(f"> **Debug:** Generated {craft_count} ticks of loot.")

        breakdown_lines = self.smithing_engine.build_party_breakdown_msg(
            xp_breakdown, loot_breakdown, total_xp, all_raw_drops
        )
        msg_lines.extend(breakdown_lines)

        await self.transport.send(channel, "\n".join(msg_lines))

        # Check for legendary drops to announce globally
        rare_drops = self.smithing_engine.get_rare_drops(task, all_raw_drops)
        if rare_drops:
            unique_rares = list(set([r.split(" (x")[0] for r in rare_drops]))
            event_msg = f"🔥 **[WORLD ANNOUNCEMENT]** A blacksmith has just forged a legendary armament: **{', '.join(unique_rares)}**!"
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

    @smith.command(name="stop")
    @require_channel("idle-smithing")
    async def smith_stop(self, ctx):
        """Stop the active smithing session and claim any finished progress."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.smithing_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active forging session to stop.")
            return

        await self.smith_claim(ctx) # Claim first
        
        # Double check it wasn't already stopped by lack of materials inside claim
        if self.smithing_engine.get_active(channel.id):
            await self.smithing_engine.stop_task(channel.id)
            await self.transport.send(channel, "🛑 **Forge extinguished early.**")


async def setup(bot):
    await bot.add_cog(SmithingCog(bot))
