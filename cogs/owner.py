import discord
from discord.ext import commands
import logging
import asyncio
import os
from datetime import datetime
from engines.forge_engine import ForgeEngine
from engines.slayer_engine import SlayerEngine
from engines.hunting_engine import HuntingEngine
from engines.tick_engine import TickEngine
from engines.quest_engine import QuestEngine

logger = logging.getLogger("Cog_Owner")

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Don't create new engine instances - we'll fetch them from other cogs
        # to ensure we're using the same shared instances
        self.tick_engine = TickEngine()  # Tick engine is only used here
        self.quest_engine = QuestEngine()  # Quest engine is only used here
        from core.transport import transport
        self.transport = transport

    @property
    def forge_engine(self):
        """Get the forge engine from ForgeCog (shared instance)"""
        forge_cog = self.bot.get_cog('ForgeCog')
        return forge_cog.forge_engine if forge_cog else None

    @property
    def slayer_engine(self):
        """Get the slayer engine from SlayerCog (shared instance)"""
        slayer_cog = self.bot.get_cog('SlayerCog')
        return slayer_cog.slayer_engine if slayer_cog else None

    @property
    def hunting_engine(self):
        """Get the hunting engine from HuntingCog (shared instance)"""
        hunting_cog = self.bot.get_cog('HuntingCog')
        return hunting_cog.hunting_engine if hunting_cog else None

    @property
    def mining_engine(self):
        """Get the mining engine from MiningCog (shared instance)"""
        mining_cog = self.bot.get_cog('MiningCog')
        return mining_cog.mining_engine if mining_cog else None

    @property
    def fishing_engine(self):
        """Get the fishing engine from FishingCog (shared instance)"""
        fishing_cog = self.bot.get_cog('FishingCog')
        return fishing_cog.fishing_engine if fishing_cog else None

    @property
    def woodcutting_engine(self):
        """Get the woodcutting engine from WoodcuttingCog (shared instance)"""
        woodcutting_cog = self.bot.get_cog('WoodcuttingCog')
        return woodcutting_cog.woodcutting_engine if woodcutting_cog else None

    @property
    def cooking_engine(self):
        """Get the cooking engine from CookingCog (shared instance)"""
        cooking_cog = self.bot.get_cog('CookingCog')
        return cooking_cog.cooking_engine if cooking_cog else None

    @property
    def crafting_engine(self):
        """Get the crafting engine from CraftingCog (shared instance)"""
        crafting_cog = self.bot.get_cog('CraftingCog')
        return crafting_cog.crafting_engine if crafting_cog else None

    @property
    def smithing_engine(self):
        """Get the smithing engine from SmithingCog (shared instance)"""
        smithing_cog = self.bot.get_cog('SmithingCog')
        return smithing_cog.smithing_engine if smithing_cog else None

    @commands.group(name="owner", invoke_without_command=True)
    @commands.is_owner()
    async def owner(self, ctx):
        """Sovereign commands for King Kaelrath."""
        if ctx.invoked_subcommand is None:
            await self.transport.send(ctx.channel, "ðŸ‘‘ **Sovereign Authority recognized.** Options: `!owner skip [hours]`, `!owner start forge [bid]`, `!owner tick`, `!owner setup`")

    @owner.group(name="start", invoke_without_command=True)
    async def owner_start(self, ctx):
        """Start systems regardless of requirements."""
        if ctx.invoked_subcommand is None:
            await self.transport.send(ctx.channel, "ðŸ® **Please specify what to start (e.g., !owner start forge [id])**")

    @owner_start.command(name="forge")
    async def owner_start_forge(self, ctx, bid: str):
        """Start the forge regardless of missing materials."""
        success, message = self.forge_engine.start_crafting(ctx.channel.id, bid, force=True)
        if success:
            await self.transport.send(ctx.channel, f"âš¡ **Sovereign Override:** {message}")
        else:
            await self.transport.send(ctx.channel, f"âŒ **Override Failed:** {message}")

    @owner.command(name="skip")
    async def owner_skip(self, ctx, hours: float):
        """Skip time on idle activities. NO LIMIT."""
        days_skipped = int(hours / 24)
        romance_reports = []
        
        # 1. Process passive romance
        if days_skipped > 0:
            try:
                from engines.romance_engine import romance_engine
                for _ in range(days_skipped):
                    reports = romance_engine.process_daily_passive_updates()
                    if reports:
                        romance_reports.extend(reports)
                logger.info(f"Processed {days_skipped} days of passive romance bonding")
            except Exception as e:
                logger.error(f"Failed to process passive romance bonding: {e}")

        # Helper to check if a task is ready to claim globally
        def should_claim_by_id(engine, channel_id) -> bool:
            active = engine.get_active(channel_id)
            if not active: return False
            task = getattr(engine, 'get_task', lambda x: None)(active['task_id'])
            if not task: return False
            elapsed = (datetime.now() - active['start_time']).total_seconds()
            ttk = task['idle_mechanics']['time_to_kill_sec']
            if active.get('solo'): ttk *= 4
            return elapsed >= ttk

        # 2. GLOBAL SKIP MODE for Owner Channel
        # When run from the owner channel, skip affects ALL active tasks globally
        owner_channel_id = int(os.getenv('OWNER_CHANNEL_ID', 0))
        if owner_channel_id and ctx.channel.id == owner_channel_id:
            tasks_skipped = 0
            
            # Map engines to their claim commands
            engine_cmd_map = {
                self.slayer_engine: 'slayer claim',
                self.hunting_engine: 'hunt claim',
                self.mining_engine: 'mine claim',
                self.fishing_engine: 'fish claim',
                self.woodcutting_engine: 'chop claim',
                self.cooking_engine: 'cook claim',
                self.crafting_engine: 'craft claim',
                self.smithing_engine: 'smith claim'
            }
            
            for engine, claim_cmd in engine_cmd_map.items():
                if engine and hasattr(engine, 'active_tasks'):
                    for cid in list(engine.active_tasks.keys()):
                        cid_int = int(cid)
                        await engine.skip_time(cid_int, hours)
                        tasks_skipped += 1
                        
                        target_chan = self.bot.get_channel(cid_int)
                        if target_chan:
                            ctx.target_channel = target_chan
                            if should_claim_by_id(engine, cid_int):
                                cmd = self.bot.get_command(claim_cmd)
                                if cmd:
                                    await ctx.invoke(cmd)
                        else:
                            # Fallback if bot can't see channel
                            if should_claim_by_id(engine, cid_int):
                                cmd = self.bot.get_command(claim_cmd)
                                if cmd:
                                    await ctx.invoke(cmd)
                        
            # Skip all forge projects
            if self.forge_engine and hasattr(self.forge_engine, 'active_projects') and self.forge_engine.active_projects:
                for cid in list(self.forge_engine.active_projects.keys()):
                    cid_int = int(cid)
                    from datetime import timedelta
                    project = self.forge_engine.active_projects[cid]
                    project['start_time'] -= timedelta(hours=hours)
                    tasks_skipped += 1
                    
                    elapsed = (datetime.now() - project['start_time']).total_seconds() / 3600
                    if elapsed >= project['duration_hours']:
                        target_chan = self.bot.get_channel(cid_int)
                        if target_chan:
                            ctx.target_channel = target_chan
                        cmd = self.bot.get_command('forge claim')
                        if cmd:
                            await ctx.invoke(cmd)
                            
                await self.forge_engine._save_active()
            
            skip_msg = f"⏳ **Global Time Warped:** Advanced **{tasks_skipped}** operations globally by **{hours} hours**."
            if days_skipped > 0:
                if romance_reports:
                    growth_str = "\n".join([f"  💕 {report}" for report in set(romance_reports)])
                    skip_msg += f"\n**Relationships evolved** over {days_skipped} day(s) of passive bonding:\n{growth_str}"
                else:
                    skip_msg += f"\n💕 **Relationships evolved** over {days_skipped} day(s) of passive bonding."
            
            # Reset target channel back to owner channel for the final status report
            ctx.target_channel = ctx.channel
            await self.transport.send(ctx.channel, skip_msg)
            return

        # 3. LOCAL CHANNEL SKIP MODE
        def should_claim(engine) -> bool:
            """Check if the skipped time is actually enough to trigger a reward"""
            active = engine.get_active(ctx.channel.id)
            if not active: return False
            task = engine.get_task(active['task_id'])
            if not task: return False
            elapsed = (datetime.now() - active['start_time']).total_seconds()
            ttk = task['idle_mechanics']['time_to_kill_sec']
            if active.get('solo'): ttk *= 4
            return elapsed >= ttk

        slayer_skipped = False
        hunting_skipped = False
        mining_skipped = False
        fishing_skipped = False
        woodcutting_skipped = False
        cooking_skipped = False
        crafting_skipped = False
        smithing_skipped = False
        forge_active = None

        if self.slayer_engine: slayer_skipped = await self.slayer_engine.skip_time(ctx.channel.id, hours)
        if self.hunting_engine: hunting_skipped = await self.hunting_engine.skip_time(ctx.channel.id, hours)
        if self.mining_engine: mining_skipped = await self.mining_engine.skip_time(ctx.channel.id, hours)
        if self.fishing_engine: fishing_skipped = await self.fishing_engine.skip_time(ctx.channel.id, hours)
        if self.woodcutting_engine: woodcutting_skipped = await self.woodcutting_engine.skip_time(ctx.channel.id, hours)
        if self.cooking_engine: cooking_skipped = await self.cooking_engine.skip_time(ctx.channel.id, hours)
        if self.crafting_engine: crafting_skipped = await self.crafting_engine.skip_time(ctx.channel.id, hours)
        if self.smithing_engine: smithing_skipped = await self.smithing_engine.skip_time(ctx.channel.id, hours)

        if self.forge_engine:
            forge_active = self.forge_engine.get_active(ctx.channel.id)
            if forge_active:
                from datetime import timedelta
                forge_active['start_time'] -= timedelta(hours=hours)
                await self.forge_engine._save_active()
                await self.transport.send(ctx.channel, f"⏳ **Time Warped:** Advanced the forge by **{hours} hours**.")
                elapsed = (datetime.now() - forge_active['start_time']).total_seconds() / 3600
                if elapsed >= forge_active['duration_hours']:
                    cmd = self.bot.get_command('forge claim')
                    if cmd: await ctx.invoke(cmd)

        def build_local_msg(skill_name: str) -> str:
            msg = f"⏳ **Time Warped:** Advanced {skill_name} by **{hours} hours**."
            if days_skipped > 0:
                if romance_reports:
                    growth_str = "\n".join([f"  💕 {report}" for report in set(romance_reports)])
                    msg += f"\n**Relationships evolved**:\n{growth_str}"
                else:
                    msg += f"\n💕 **Relationships evolved**."
            return msg

        if slayer_skipped:
            await self.transport.send(ctx.channel, build_local_msg("the hunt"))
            if should_claim(self.slayer_engine):
                cmd = self.bot.get_command('slayer claim')
                if cmd: await ctx.invoke(cmd)

        if hunting_skipped:
            await self.transport.send(ctx.channel, build_local_msg("the hunt"))
            if should_claim(self.hunting_engine):
                cmd = self.bot.get_command('hunt claim')
                if cmd: await ctx.invoke(cmd)

        if mining_skipped:
            await self.transport.send(ctx.channel, build_local_msg("mining"))
            if should_claim(self.mining_engine):
                cmd = self.bot.get_command('mine claim')
                if cmd: await ctx.invoke(cmd)

        if fishing_skipped:
            await self.transport.send(ctx.channel, build_local_msg("fishing"))
            if should_claim(self.fishing_engine):
                cmd = self.bot.get_command('fish claim')
                if cmd: await ctx.invoke(cmd)

        if woodcutting_skipped:
            await self.transport.send(ctx.channel, build_local_msg("woodcutting"))
            if should_claim(self.woodcutting_engine):
                cmd = self.bot.get_command('chop claim')
                if cmd: await ctx.invoke(cmd)

        if cooking_skipped:
            await self.transport.send(ctx.channel, build_local_msg("cooking"))
            if should_claim(self.cooking_engine):
                cmd = self.bot.get_command('cook claim')
                if cmd: await ctx.invoke(cmd)

        if crafting_skipped:
            await self.transport.send(ctx.channel, build_local_msg("crafting"))
            if should_claim(self.crafting_engine):
                cmd = self.bot.get_command('craft claim')
                if cmd: await ctx.invoke(cmd)

        if smithing_skipped:
            await self.transport.send(ctx.channel, build_local_msg("smithing"))
            if should_claim(self.smithing_engine):
                cmd = self.bot.get_command('smith claim')
                if cmd: await ctx.invoke(cmd)

        if not any([slayer_skipped, hunting_skipped, mining_skipped, fishing_skipped, woodcutting_skipped, cooking_skipped, crafting_skipped, smithing_skipped, forge_active]):
            await self.transport.send(ctx.channel, "🎮 **Nothing to skip in this channel.**")

    @owner.command(name="wipe_idle")
    async def owner_wipe_idle(self, ctx):
        """Globally clear all active idle tasks and forge projects."""
        try:
            tasks_wiped = 0
            
            # Wipe all generic idle tasks
            idle_engines = [self.slayer_engine, self.hunting_engine, self.mining_engine, self.fishing_engine, self.woodcutting_engine, self.cooking_engine, self.crafting_engine, self.smithing_engine]
            for engine in idle_engines:
                if engine and hasattr(engine, 'active_tasks') and engine.active_tasks:
                    tasks_wiped += len(engine.active_tasks)
                    engine.active_tasks.clear()
                    await engine._save_active()
                    
            # Wipe forge projects
            if self.forge_engine and hasattr(self.forge_engine, 'active_projects') and self.forge_engine.active_projects:
                tasks_wiped += len(self.forge_engine.active_projects)
                self.forge_engine.active_projects.clear()
                await self.forge_engine._save_active()

            msg = f"🧹 **Sovereign Decree:** Globally wiped **{tasks_wiped}** active idle operations."
            await self.transport.send(ctx.channel, msg)
            logger.info(f"Owner executed global wipe_idle. Cleared {tasks_wiped} tasks.")

        except Exception as e:
            logger.error(f"Global wipe failed: {e}", exc_info=True)
            await self.transport.send(ctx.channel, f"❌ **Collapse Failed:** {e}")

    @owner.command(name="tick")
    async def owner_tick(self, ctx):
        """Manually trigger the Sovereignty Heartbeat (Weekly Tick)."""
        await self.transport.send(ctx.channel, "âš¡ **Invoking the Sovereign Heartbeat...**")
        proclamation = await self.tick_engine.run_tick()
        msg = [
            "ðŸ”Š **[THE SOVEREIGN PROCLAMATION]**",
            "***The stars have shifted. The kingdom breathes.***",
            proclamation,
            "\n*Glory to the World-Spark.*"
        ]
        self.quest_engine.log_deed("SYSTEM", "Manual Heartbeat", "The Sovereign invoked a chronal shift.")
        await self.transport.send(ctx.channel, "\n".join(msg), "NPC")

    @owner.command(name="setup")
    async def owner_setup(self, ctx):
        """Automatically create necessary channels and folder structure."""
        await self.transport.send(ctx.channel, "ðŸ› ï¸ **Initializing Sovereignty Infrastructure...**")
        
        # 1. Discord Channel Creation
        channels_to_create = [
            ("campaign-chat", "The main stage for the Chronicle. Plot-heavy and dramatic."),
            ("rumors-chat", "Whispers from the Rumor Mill. News, hooks, and localized mystery."),
            ("off-topic", "Casual roleplay, social downtime, and atmosphere. No plot pressure."),
            ("party-chat", "In-character banter and coordination between players."),
            ("npc-gallery", "NPC dossiers and party character cards."),
            ("the-forge", "Artifact fabrication and crafting queue."),
            ("world-events", "Weekly Proclamations and world-heartbeat alerts."),
            ("royal-treasury", "Full inventory listings and resource dashboards."),
            ("side-quests", "Active quest tracking and turn-based interactions."),
            ("images", "Captured visions and NPC portraits."),
            ("resources", "Rules reference and kingdom statistics."),
            ("combat", "Combat tracking and initiative order."),
            ("idle-slayer", "The eternal grind of the Ridge."),
            ("weaver-archives", "META-CHANNEL: Direct system access and meta-cognitive archives. Sovereign only.")
        ]
        
        category_name = "ðŸ° EMBERHEART"
        guild = ctx.guild
        
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            await self.transport.send(ctx.channel, f"âœ… Created Category: **{category_name}**")

        channel_count = 0
        for name, desc in channels_to_create:
            existing = discord.utils.get(guild.channels, name=name)
            if not existing:
                overwrites = None
                if name == "weaver-archives":
                    # Private: Sovereign (Owner) and Bot only
                    # Robust lookup: guild.owner can be None if not cached
                    owner_target = guild.owner or guild.get_member(guild.owner_id) or ctx.author
                    bot_target = guild.me or ctx.guild.me
                    
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        owner_target: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        bot_target: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                await guild.create_text_channel(name, category=category, topic=desc, overwrites=overwrites)
                channel_count += 1
                await self.transport.send(ctx.channel, f"âœ… Created Channel: `#{name}`{' (PRIVATE)' if overwrites else ''}")
            else:
                if existing.category != category:
                    await existing.edit(category=category)
                    await self.transport.send(ctx.channel, f"âš“ Docked `#{name}` to the Sovereignty category.")

        # 2. Filesystem Initialization
        from core.config import ROOT_DIR, DB_DIR, CHARACTERS_DIR
        folders = [
            DB_DIR,
            CHARACTERS_DIR,
            ROOT_DIR / "assets",
            ROOT_DIR / "docs" / "quests" / "Hard",
            ROOT_DIR / "docs" / "reference",
            ROOT_DIR / "session_logs"
        ]
        
        folder_count = 0
        for folder in folders:
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
                folder_count += 1
                # Create .gitkeep if empty
                gitkeep = folder / ".gitkeep"
                if not any(folder.iterdir()):
                    gitkeep.touch()
        
        await self.transport.send(ctx.channel, f"âœ¨ **Setup Complete.** {channel_count} Discord channels and {folder_count} filesystem directories established. Glory to the World-Spark.")

    @owner.command(name="debug")
    async def owner_debug(self, ctx):
        """Debug info: Show active slayer tasks and forge projects."""
        lines = ["🔍 **Debug Info:**", ""]

        # Slayer tasks
        if self.slayer_engine and self.slayer_engine.active_tasks:
            lines.append("**Active Slayer Tasks:**")
            for channel_id, task_data in self.slayer_engine.active_tasks.items():
                channel = self.bot.get_channel(channel_id)
                channel_name = f"#{channel.name}" if channel else f"Unknown ({channel_id})"
                lines.append(f"  • {channel_name}: {task_data['task_id']} (started {task_data['start_time']})")
        else:
            lines.append("**Active Slayer Tasks:** None")

        lines.append("")

        # Hunting tasks
        if self.hunting_engine and self.hunting_engine.active_tasks:
            lines.append("**Active Hunting Tasks:**")
            for channel_id, task_data in self.hunting_engine.active_tasks.items():
                channel = self.bot.get_channel(channel_id)
                channel_name = f"#{channel.name}" if channel else f"Unknown ({channel_id})"
                lines.append(f"  • {channel_name}: {task_data['task_id']} (started {task_data['start_time']})")
        else:
            lines.append("**Active Hunting Tasks:** None")

        lines.append("")

        # Mining tasks
        if self.mining_engine and self.mining_engine.active_tasks:
            lines.append("**Active Mining Tasks:**")
            for channel_id, task_data in self.mining_engine.active_tasks.items():
                channel = self.bot.get_channel(channel_id)
                channel_name = f"#{channel.name}" if channel else f"Unknown ({channel_id})"
                lines.append(f"  • {channel_name}: {task_data['task_id']} (started {task_data['start_time']})")
        else:
            lines.append("**Active Mining Tasks:** None")

        lines.append("")

        # Fishing tasks
        if self.fishing_engine and self.fishing_engine.active_tasks:
            lines.append("**Active Fishing Tasks:**")
            for channel_id, task_data in self.fishing_engine.active_tasks.items():
                channel = self.bot.get_channel(channel_id)
                channel_name = f"#{channel.name}" if channel else f"Unknown ({channel_id})"
                lines.append(f"  • {channel_name}: {task_data['task_id']} (started {task_data['start_time']})")
        else:
            lines.append("**Active Fishing Tasks:** None")

        lines.append("")

        # Woodcutting tasks
        if self.woodcutting_engine and self.woodcutting_engine.active_tasks:
            lines.append("**Active Woodcutting Tasks:**")
            for channel_id, task_data in self.woodcutting_engine.active_tasks.items():
                channel = self.bot.get_channel(channel_id)
                channel_name = f"#{channel.name}" if channel else f"Unknown ({channel_id})"
                lines.append(f"  • {channel_name}: {task_data['task_id']} (started {task_data['start_time']})")
        else:
            lines.append("**Active Woodcutting Tasks:** None")

        lines.append("")

        # Forge projects
        if self.forge_engine and self.forge_engine.active_projects:
            lines.append("**Active Forge Projects:**")
            for channel_id, proj_data in self.forge_engine.active_projects.items():
                channel = self.bot.get_channel(channel_id)
                channel_name = f"#{channel.name}" if channel else f"Unknown ({channel_id})"
                lines.append(f"  • {channel_name}: {proj_data['blueprint_id']} (started {proj_data['start_time']})")
        else:
            lines.append("**Active Forge Projects:** None")

        lines.append("")
        lines.append(f"**Current Channel:** #{ctx.channel.name} (ID: {ctx.channel.id})")

        await self.transport.send(ctx.channel, "\n".join(lines))

    @owner.command(name="reload")
    async def owner_reload(self, ctx, cog_name: str):
        """Reload a cog without restarting the bot. Usage: !owner reload slayer"""
        # Normalize cog name to module path
        if not cog_name.startswith("cogs."):
            cog_name = f"cogs.{cog_name.lower()}"

        try:
            # Try to reload the cog
            await self.bot.reload_extension(cog_name)
            await self.transport.send(ctx.channel, f"✅ **Reloaded:** `{cog_name}`")
            logger.info(f"Successfully reloaded {cog_name}")
        except commands.ExtensionNotLoaded:
            # If not loaded, try to load it
            try:
                await self.bot.load_extension(cog_name)
                await self.transport.send(ctx.channel, f"✅ **Loaded:** `{cog_name}` (was not previously loaded)")
                logger.info(f"Successfully loaded {cog_name}")
            except Exception as e:
                await self.transport.send(ctx.channel, f"❌ **Failed to load {cog_name}:** {str(e)}")
                logger.error(f"Failed to load {cog_name}: {e}")
        except Exception as e:
            await self.transport.send(ctx.channel, f"❌ **Failed to reload {cog_name}:** {str(e)}")
            logger.error(f"Failed to reload {cog_name}: {e}")

    @owner.command(name="give")
    async def owner_give(self, ctx, char_id: str, amount: int, *, item_name: str):
        """Give items to a character. Usage: !owner give PC-01 5 Iron Ore"""
        try:
            from core.state_store import coordinator
            from core.storage import load_character_state

            state = load_character_state(char_id)
            if not state:
                await self.transport.send(ctx.channel, f"❌ Character **{char_id}** not found.")
                return

            inv = state.get("status", {}).get("inventory", [])
            if isinstance(inv, list):
                inv.extend([item_name] * amount)
            else:
                inv = [item_name] * amount

            state.setdefault("status", {})["inventory"] = inv
            await coordinator.update_character_state_async(char_id, state)

            char_name = state.get("name", char_id)
            await self.transport.send(ctx.channel, f"✅ **Sovereign Grant:** Gave **{amount}x** `{item_name}` to **{char_name}** ({char_id}).")
            logger.info(f"Owner gave {amount}x {item_name} to {char_name} ({char_id})")

        except Exception as e:
            logger.error(f"Owner give failed: {e}", exc_info=True)
            await self.transport.send(ctx.channel, f"❌ **Failed:** {e}")

    @owner.command(name="gold")
    async def owner_gold(self, ctx, char_id: str, amount: int):
        """Add gold to a character. Usage: !owner gold PC-01 5000"""
        try:
            from core.state_store import coordinator
            from core.storage import load_character_state

            state = load_character_state(char_id)
            if not state:
                await self.transport.send(ctx.channel, f"❌ Character **{char_id}** not found.")
                return

            current_gold = state.get("gold", 0)
            new_gold = current_gold + amount
            state["gold"] = new_gold
            await coordinator.update_character_state_async(char_id, state)

            char_name = state.get("name", char_id)
            await self.transport.send(ctx.channel, f"✅ **Sovereign Grant:** Added **{amount:,} gold** to **{char_name}** ({char_id}). New balance: **{new_gold:,} gold**.")
            logger.info(f"Owner added {amount} gold to {char_name} ({char_id}). New balance: {new_gold}")

        except Exception as e:
            logger.error(f"Owner gold failed: {e}", exc_info=True)
            await self.transport.send(ctx.channel, f"❌ **Failed:** {e}")

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx):
        """Message Purge (Clean channel history)."""
        await ctx.channel.purge(limit=100)
        status = await ctx.send("ðŸ§¹ **Channel Purged.**")
        await asyncio.sleep(3)
        try:
            await status.delete()
        except Exception as e:
            logger.error(f"Failed to delete purge status message: {e}")
            await ctx.send(f"âŒ Error deleting status message: {e}")

async def setup(bot):
    await bot.add_cog(OwnerCog(bot))


