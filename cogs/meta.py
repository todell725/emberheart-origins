import discord
from discord.ext import commands, tasks
import logging

from engines.shop_engine import DynamicShop

logger = logging.getLogger("Cog_Meta")


class MetaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shop_engine = DynamicShop()  # Used by background loop
        # Start once when cog loads to avoid duplicate loops.
        self.rotation_loop.start()

    def cog_unload(self):
        """Cleanup when cog is reloaded."""
        self.rotation_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Connected to Discord! Logged in as: {self.bot.user.name}")
        await self.bot.change_presence(activity=discord.Game(name="Watching over Warden-Keep"))

    @tasks.loop(seconds=1200)
    async def rotation_loop(self):
        """Background loop to rotate the shop inventory."""
        await self.bot.wait_until_ready()
        logger.info("Executing periodic shop rotation...")
        await self.shop_engine.generate_stock()

        for guild in self.bot.guilds:
            try:
                channel = discord.utils.get(guild.channels, name="shop")
                if not channel:
                    continue

                try:
                    await channel.purge(limit=10)
                except Exception:
                    pass

                embed = discord.Embed(
                    title="⚖️ The Gilded Exchange",
                    description="*\"Finest wares from the Forge and the Far-Realms...\"*",
                    color=0xFFD700,
                )

                armory = ""
                arcanum = ""
                for item in self.shop_engine.current_stock[:15]:
                    armory += f"**{item['name']}** ({item['type']})\n└ *{item['desc']}* — **{item['cost']}**\n"
                for item in self.shop_engine.current_stock[15:]:
                    arcanum += f"**{item['name']}**\n└ *{item['desc']}* — **{item['cost']}**\n"

                if armory:
                    embed.add_field(name="⚒️ The Armory", value=armory[:1024], inline=False)
                if arcanum:
                    embed.add_field(name="📜 The Arcanum", value=arcanum[:1024], inline=False)

                await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Rotation failed for guild {guild.name}: {e}")

    @rotation_loop.before_loop
    async def before_rotation(self):
        await self.bot.wait_until_ready()

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx, extension: str):
        """Hot-reloads a specific cog. E.g., `!reload quests` or `!reload cogs.quests`"""
        normalized = extension.strip()
        if normalized.startswith("cogs."):
            normalized = normalized.split(".", 1)[1]

        qualified = f"cogs.{normalized}"
        try:
            await self.bot.reload_extension(qualified)
            await ctx.send(f"✅ Reloaded `{qualified}` via hot-swap.")
            logger.info(f"Hot-reloaded extension: {qualified}")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload `{qualified}`: {e}")
            logger.error(f"Reload failed for {qualified}: {e}")

    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.send("Pong! Engines Online.")

    @commands.command(name="commands")
    async def list_commands(self, ctx):
        """Display all Sovereign and Gameplay commands."""
        embed = discord.Embed(
            title="📜 EmberHeart Reborn: Master Command List",
            description="Use these commands to navigate and manage the simulation.",
            color=0x34495e,
        )

        embed.add_field(
            name="🏛️ System & Meta",
            value=(
                "`!ping`: Check bot status.\n"
                "`!reload [cog]`: Hot-swap a component.\n"
                "`!commands`: You are here."
            ),
            inline=False,
        )

        embed.add_field(
            name="📖 Narrative Control",
            value=(
                "`!clear [ID]`: Narrative rollback to a message ID.\n"
                "`!refresh [limit]`: Rebuild short-term context from history.\n"
                "`!pulse [text]`: Sync global records / Log manual event.\n"
                "`!reset`: Clear current channel history memory."
            ),
            inline=False,
        )

        embed.add_field(
            name="👑 Sovereign Mastery",
            value=(
                "`!owner setup`: Auto-initialize channels & perms.\n"
                "`!owner skip [hours]`: Warp time forward (No limit).\n"
                "`!owner tick`: Manually invoke the weekly proclamation.\n"
                "`!owner start forge [ID]`: Force-start a blueprint.\n"
                "`!purge`: Clean text history from an admin channel."
            ),
            inline=False,
        )

        embed.add_field(
            name="⚔️ Slayer & Grind",
            value=(
                "`!tasks`: View available hunts for your level.\n"
                "`!slayer task [ID] [--solo]`: Start a hunt (Solo = 4x TTK, Targeted XP).\n"
                "`!slayer claim`: Collect rewards from finished kills.\n"
                "`!slayer stop`: Terminate current hunt."
            ),
            inline=False,
        )

        embed.add_field(
            name="🌍 Game World",
            value=(
                "`!stats`: Kingdom metrics & forge status.\n"
                "`!quest [info/complete]`: Quest lookup and XP/Loot award.\n"
                "`!npc [name]`: View character card.\n"
                "`!loot [list/add/remove]`: Manage inventory.\n"
                "`!shop [inventory/buy]`: Trade at the Gilded Exchange.\n"
                "`!forge [list/start/claim]`: Artifact fabrication.\n"
                "`!journal`: Read latest campaign logs."
            ),
            inline=False,
        )

        embed.add_field(
            name="👤 Character & Social",
            value=(
                "`!dm [name] [msg]`: Open a private thread with an NPC.\n"
                "`!hp [name] [val]`: Manual health adjustment.\n"
                "`!worn`: Show current party equipment.\n"
                "`!capture`: Scan for and link character portraits.\n"
                "`!cleanup`: Purge text-only messages from gallery."
            ),
            inline=False,
        )

        embed.set_footer(text="Glory to the World-Spark. | EmberHeart Engine v2.5")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MetaCog(bot))
