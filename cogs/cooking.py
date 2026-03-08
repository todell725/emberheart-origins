"""
Cooking Cog - Passive Culinary System
Allows players to convert raw ingredients into stat-boosting meals.
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime
from collections import Counter
from engines.cooking_engine import CookingEngine
from engines.quest_engine import QuestEngine
from core.transport import transport
from core.routing import require_channel

logger = logging.getLogger("Cog_Cooking")


class CookingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooking_engine = CookingEngine(llm_client=getattr(bot, 'llm', None))
        self.quest_engine = QuestEngine()
        self.transport = transport

    @commands.group(name="cook", invoke_without_command=True)
    @require_channel("idle-cooking")
    async def cook(self, ctx):
        """Cooking commands: recipe, claim, stop, list"""
        if ctx.invoked_subcommand is None:
            await self.transport.send(ctx.channel, "🍳 **Cooking Commands:**\n`!cook list` - Show available recipes\n`!cook recipe <id>` - Start preparing a dish\n`!cook claim` - Serve your meals\n`!cook stop` - Put out the fire")

    @cook.command(name="list")
    @require_channel("idle-cooking")
    async def cook_list(self, ctx):
        """List all available cooking recipes."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        party_level = self.cooking_engine.get_party_level()

        tasks = self.cooking_engine.list_tasks()
        if not tasks:
            await self.transport.send(channel, "No recipes available.")
            return

        msg = ["🍳 **Culinary Recipes:**", ""]
        for task in tasks:
            req_level = task['requirements']['min_level']
            ttk = task['idle_mechanics']['time_to_kill_sec']
            xp = task['idle_mechanics']['xp_per_kill']

            unlocked = "✅" if party_level >= req_level else "🔒"
            msg.append(f"{unlocked} **{task['task_id']}** - {task['recipe_name']} (Lv {req_level})")
            msg.append(f"   ⏱️ {ttk}s per dish | 💎 {xp} XP | {task['difficulty']}")
            msg.append(f"   *{task['description']}*")
            msg.append("")

        await self.transport.send(channel, "\n".join(msg))

    @cook.command(name="recipe")
    @require_channel("idle-cooking")
    async def cook_recipe(self, ctx, recipe_id: str, solo: str = None):
        """Start preparing a recipe: !cook recipe COOK_001 [--solo]"""
        is_solo = solo == "--solo"
        task = await self.cooking_engine.start_task(ctx.channel.id, recipe_id, solo=is_solo)
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not task:
            await self.transport.send(channel, f"Recipe **{recipe_id}** not found.")
            return
        ttk = task['idle_mechanics']['time_to_kill_sec']
        if is_solo:
            ttk *= 4

        await self.transport.send(channel, f"🍳 **Kitchen Hot:** You begin preparing **{task['recipe_name']}**{' (SOLO)' if is_solo else ''}.\nEstimated Time per Dish: **{ttk}s**")

    @cook.command(name="claim")
    @require_channel("idle-cooking")
    async def cook_claim(self, ctx):
        """Serve the meals from your cooking session."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.cooking_engine.get_active(channel.id)

        if not active:
            await self.transport.send(channel, "No active cooking session to claim from.")
            return

        task = self.cooking_engine.get_task(active['task_id'])
        elapsed = (datetime.now() - active['start_time']).total_seconds()
        ttk = task['idle_mechanics']['time_to_kill_sec']

        is_solo = active.get('solo')
        if is_solo:
            ttk *= 4

        if elapsed < ttk:
            remaining = int(ttk - elapsed)
            await self.transport.send(channel, f"**Dish Incomplete!** Need **{remaining}s** more to finish the first **{task['recipe_name']}**.")
            return

        max_dishes = int(elapsed // ttk)
        ingredients = task.get("ingredients", {})
        
        dish_count = await self.cooking_engine.consume_party_ingredients(ingredients, max_dishes)

        if dish_count <= 0:
            req_str = ", ".join([f"{q}x {i}" for i, q in ingredients.items()])
            await self.transport.send(channel, f"🔥 **The fire went out!** You ran out of ingredients.\n> **Required:** {req_str}")
            await self.cooking_engine.stop_task(channel.id)
            return

        # Time refund for uncookable dishes
        if dish_count < max_dishes:
            time_spent = dish_count * ttk
            active['start_time'] = datetime.now() - timedelta(seconds=(elapsed - time_spent))
            await self.cooking_engine._save_active()
            await self.transport.send(channel, f"🔥 **Ingredients Depleted!** Stopped early after cooking **{dish_count}** dishes.")
            await self.cooking_engine.stop_task(channel.id) # Reset task since we can't cook more
        else:
            # Full success, reset timer to spillover
            time_spent = dish_count * ttk
            active['start_time'] += timedelta(seconds=time_spent)
            await self.cooking_engine._save_active()


        # DEBUG: Show calculation
        logger.info(f"COOKING CLAIM DEBUG: elapsed={elapsed}s, ttk={ttk}s, dishes={dish_count}, math={elapsed}/{ttk}={elapsed/ttk}")
        total_xp = task['idle_mechanics']['xp_per_kill'] * dish_count

        all_raw_drops = self.cooking_engine.roll_loot(
            task['drop_table'],
            task['idle_mechanics']['max_drops_per_kill'],
            kills=dish_count
        )

        counts = Counter(all_raw_drops)
        display_drops = [f"{item} (x{count})" if count > 1 else item for item, count in counts.items()]

        target_ids = ["PC-01"] if is_solo else None
        xp_breakdown = await self.quest_engine.combat.add_party_xp(total_xp, target_ids=target_ids, difficulty="normal", kill_count=dish_count)

        loot_breakdown = {}
        if all_raw_drops:
            loot_breakdown = await self.quest_engine.sync_loot(all_raw_drops)

        self.quest_engine.log_deed(task['task_id'], f"Cooking: {task['recipe_name']} {'(SOLO)' if is_solo else ''}", f"Prepared {dish_count} meals. Total XP: {total_xp}")

        # Generate LLM culinary narration
        try:
            character_class = self.cooking_engine.get_character_class()
            cooking_report = await self.cooking_engine.generate_cooking_report(
                task=task,
                recipe_count=dish_count,
                total_xp=total_xp,
                loot=all_raw_drops,
                character_class=character_class,
                solo=is_solo
            )
        except Exception as e:
            logger.error(f"Failed to generate cooking report: {e}")
            cooking_report = f"You successfully plated up {dish_count} servings of {task['recipe_name']}. Delicious."

        # Calculate romance bonding multiplier for display
        import math
        if dish_count > 1:
            bonding_multiplier = 1 + math.log10(min(dish_count, 1000))
        else:
            bonding_multiplier = 1.0

        msg = [
            "🍽️ **Service Complete!**",
            f"*{cooking_report}*",
            "",
            f"> Main Course: {task['recipe_name']}",
            f"> Covers Plated: {dish_count}",
            f"> Total XP: +{total_xp:,} XP",
        ]

        # Add debug info if debug mode is enabled
        if getattr(self.bot, 'config', {}).get('debug', False):
            msg.append(f"> Debug: {elapsed:.0f}s elapsed ÷ {ttk}s TTK = {dish_count} dishes")

        if not is_solo and dish_count > 1:
            msg.append(f"> Party Bonding: {bonding_multiplier:.2f}x from cooking together")

        # Itemized Party Breakdown
        breakdown_lines = self.cooking_engine.build_party_breakdown_msg(
            xp_breakdown=xp_breakdown,
            loot_breakdown=loot_breakdown,
            total_xp=total_xp,
            all_loot=all_raw_drops
        )
        msg.extend(breakdown_lines)
        await self.transport.send(channel, "\n".join(msg))

        await self.cooking_engine.stop_task(ctx.channel.id)

    @cook.command(name="stop")
    @require_channel("idle-cooking")
    async def cook_stop(self, ctx):
        """Stop cooking and abandon current ingredients."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        active = self.cooking_engine.get_active(ctx.channel.id)
        if not active:
            await self.transport.send(channel, "You aren't cooking anything right now.")
            return

        task = self.cooking_engine.get_task(active['task_id'])
        await self.cooking_engine.stop_task(ctx.channel.id)
        await self.transport.send(channel, f"🔥 You take the **{task['recipe_name']}** off the heat. Progress abandoned.")

async def setup(bot):
    await bot.add_cog(CookingCog(bot))
