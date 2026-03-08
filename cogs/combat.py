from discord.ext import commands
import logging
import random
from engines.combat_engine import CombatTracker
from core.routing import require_channel

logger = logging.getLogger("Cog_Combat")

class CombatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.battle_tracker = CombatTracker()
        from core.transport import transport
        self.transport = transport

    @commands.group(invoke_without_command=True)
    @require_channel("combat")
    async def combat(self, ctx):
        """View the current combat status."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        if not self.battle_tracker.active or not self.battle_tracker.order:
            await self.transport.send(channel, "🏮 **No active combat.** Use `!init` to start.")
            return

        msg = ["**⚔️ Combat Tracker ⚔️**"]
        for i, c in enumerate(self.battle_tracker.order):
            prefix = "➡️ " if i == self.battle_tracker.current_index else "   "
            msg.append(f"{prefix}**{c['name']}** | Init: {c['init']} | HP: {c['hp']}")
        
        await self.transport.send(channel, "\n".join(msg))

    @combat.command(name="next")
    @require_channel("combat")
    async def combat_next(self, ctx):
        """Move to the next turn."""
        turn = self.battle_tracker.next_turn()
        channel = getattr(ctx, "target_channel", ctx.channel)
        if turn:
            await self.transport.send(channel, f"⚔️ **Next Turn:** It is now **{turn['name']}**'s move!")
            await ctx.invoke(self.bot.get_command('combat'))

    @combat.command(name="clear")
    @require_channel("combat")
    async def combat_clear(self, ctx):
        """End the current combat."""
        self.battle_tracker.clear()
        channel = getattr(ctx, "target_channel", ctx.channel)
        await self.transport.send(channel, "🕊️ **Combat Cleared.** The dust settles.")

    @commands.command()
    @require_channel("combat")
    async def init(self, ctx):
        """Roll initiative for the party and start combat."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        try:
            from core.storage import load_all_character_states
            all_states = load_all_character_states()
            # Party = PC- prefixed
            party = [s for s in all_states if s.get("id", "").startswith("PC-")]
            
            if not party:
                await self.transport.send(channel, "🔍 **No party members found.** Combat cancelled.")
                return
                
            self.battle_tracker.clear()
            self.battle_tracker.active = True
            
            results = []
            for p in party:
                cp = p.get("combat_profile", {})
                bonus = cp.get("initiative_bonus", 0)
                roll = random.randint(1, 20)
                total = roll + bonus
                hp = cp.get("hp", 0)
                self.battle_tracker.add_combatant(p['name'], total, hp)
                results.append(f"🎲 **{p['name']}**: {total} ({roll}+{bonus})")
                
            msg = "**⚔️ Initiative Rolled!**\n" + "\n".join(results)
            await self.transport.send(channel, msg)
            await ctx.invoke(self.bot.get_command('combat'))
            
        except Exception as e:
            await self.transport.send(channel, f"❌ Error rolling initiative: {e}")

async def setup(bot):
    await bot.add_cog(CombatCog(bot))
