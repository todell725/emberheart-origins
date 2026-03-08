from discord.ext import commands
import logging
from datetime import datetime
from engines.forge_engine import ForgeEngine
from core.routing import require_channel
from engines.quest_engine import QuestEngine

logger = logging.getLogger("Cog_Forge")

class ForgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forge_engine = ForgeEngine()
        self.quest_engine = QuestEngine()
        from core.transport import transport
        self.transport = transport

    @commands.group(name="forge", invoke_without_command=True)
    @require_channel("the-forge")
    async def forge(self, ctx):
        """Sovereign Forges: Craft legendary artifacts using kingdom resources."""
        active = self.forge_engine.get_active(ctx.channel.id)
        if active:
            elapsed = (datetime.now() - active['start_time']).total_seconds() / 3600
            progress = min(100, (elapsed / active['duration_hours']) * 100)
            msg = [
                f"⚒️ **Active Project:** {active['name']}",
                f"> ⏳ Progress: **{int(progress)}%** ({round(elapsed, 1)}/{active['duration_hours']}h elapsed)"
            ]
            if progress >= 100:
                msg.append("> ✅ **Construction Complete!** Use `!forge claim` to add to inventory.")
            
            channel = getattr(ctx, "target_channel", ctx.channel)
            await self.transport.send(channel, "\n".join(msg), "NPC")
        else:
            channel = getattr(ctx, "target_channel", ctx.channel)
            await self.transport.send(channel, "🏮 **Forges are idle.** Use `!forge list` to see blueprints.", "NPC")

    @forge.command(name="list")
    @require_channel("the-forge")
    async def forge_list(self, ctx):
        """List available artifact blueprints."""
        blueprints = self.forge_engine.list_blueprints()
        msg = ["**⚒️ Sovereign Forge Blueprints**"]
        for bp in blueprints:
            msg.append(f"📌 **{bp['id']}**: {bp['name']}")
            msg.append(f"> *{bp['description']}*")
            cost_str = f"{bp['cost'].get('ore_ou', 0)} OU, {bp['cost'].get('metal_m2u', 0)} M2U"
            mats = ", ".join([f"{m['quantity']}x {m['item']}" for m in bp.get('materials', [])])
            msg.append(f"> 💰 Cost: {cost_str} | 📦 Materials: {mats}")
            msg.append(f"> ⏳ Time: {bp['craft_time_hours']}h")
        
        channel = getattr(ctx, "target_channel", ctx.channel)
        await self.transport.send(channel, "\n".join(msg), "NPC")

    @forge.command(name="start")
    @require_channel("the-forge")
    async def forge_start(self, ctx, blueprint_id: str):
        """Begin crafting an artifact: !forge start ART_001"""
        success, message = await self.forge_engine.start_crafting(ctx.channel.id, blueprint_id)
        channel = getattr(ctx, "target_channel", ctx.channel)
        if success:
            await self.transport.send(channel, f"⚒️ {message}", "NPC")
        else:
            await self.transport.send(channel, f"❌ {message}", "NPC")

    @forge.command(name="claim")
    @require_channel("the-forge")
    async def forge_claim(self, ctx):
        """Claim a finished artifact."""
        success, message = await self.forge_engine.claim_artifact(ctx.channel.id)
        channel = getattr(ctx, "target_channel", ctx.channel)
        if success:
            self.quest_engine.log_deed("FORGE", "Artifact Forged", message)
            await self.transport.send(channel, message, "NPC")
        else:
            await self.transport.send(channel, f"❌ {message}", "NPC")

async def setup(bot):
    await bot.add_cog(ForgeCog(bot))
