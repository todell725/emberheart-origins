"""
Quest Cog for EmberHeart: Origins
Quest management: !quest info, !quest start, !quest choice, !quest complete
Supports reaction-based A/B choices on turn embeds.
"""
import asyncio
import discord
from discord.ext import commands
import logging
from engines.quest_engine import QuestEngine

logger = logging.getLogger("Cog_Quests")

REACTION_A = "🅰️"
REACTION_B = "🅱️"


class QuestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quest_engine = QuestEngine()
        # Track turn messages awaiting reactions: {message_id: qid}
        self.pending_turns = {}

    def _build_turn_embed(self, quest: dict, turn_data: dict, qid: str, total_turns: int) -> discord.Embed:
        """Build a rich embed for a quest turn prompt."""
        turn_num = turn_data.get("turn", 1)
        embed = discord.Embed(
            title=f"📖 {quest.get('title', qid)} — Turn {turn_num}/{total_turns}",
            description=turn_data.get("narrative", "No narrative."),
            color=0xe67e22
        )
        choice_a = turn_data.get("choice_a", "Option A")
        choice_b = turn_data.get("choice_b", "Option B")
        embed.add_field(
            name="🅰️ Choice A",
            value=choice_a,
            inline=False
        )
        embed.add_field(
            name="🅱️ Choice B",
            value=choice_b,
            inline=False
        )
        embed.set_footer(text=f"Quest {qid} | React 🅰️ or 🅱️ to choose (or type !quest choice a/b)")
        return embed

    async def _send_turn(self, channel, quest: dict, turn_data: dict, qid: str, total_turns: int):
        """Send a turn embed and add reaction buttons."""
        turn_embed = self._build_turn_embed(quest, turn_data, qid, total_turns)
        msg = await channel.send(embed=turn_embed)
        await msg.add_reaction(REACTION_A)
        await msg.add_reaction(REACTION_B)
        self.pending_turns[msg.id] = qid
        return msg

    async def _process_choice(self, channel, qid: str, choice: str, quest: dict = None):
        """Process a quest choice and send results. Shared by reaction + command handlers."""
        if not quest:
            quest = self.quest_engine.get_quest(qid)

        success, result = self.quest_engine.submit_choice(qid, choice)
        if not success:
            return await channel.send(f"❌ {result.get('error', 'Unknown error.')}")

        # Show consequence
        consequence = result.get("consequence", "")
        convergence = result.get("convergence", "")
        current_turn = result.get("current_turn", 0)
        total_turns = result.get("total_turns", 0)

        consequence_embed = discord.Embed(
            title=f"⚔️ Turn {current_turn} — {'Choice A' if choice == 'a' else 'Choice B'}",
            description=consequence,
            color=0x3498db
        )
        if convergence:
            consequence_embed.add_field(name="📍 What happens next...", value=f"*{convergence}*", inline=False)

        await channel.send(embed=consequence_embed)

        # Check if quest is complete
        if result.get("quest_complete"):
            path_list = list(result.get("path", ""))
            leveled_chars = await self.quest_engine.mark_completed(qid, path_list)

            complete_embed = discord.Embed(
                title=f"🏆 Quest Complete: {quest.get('title', qid)}",
                description=quest.get("conclusion", "The quest has concluded."),
                color=0x2ecc71
            )
            complete_embed.add_field(name="XP Gain", value=f"+{quest.get('xp_reward', 0)} XP", inline=True)
            complete_embed.add_field(name="Path", value=result.get("path", "").upper(), inline=True)

            loot = quest.get("loot_table", quest.get("loot", []))
            if loot:
                loot_str = "\n".join([f"• {item}" for item in loot[:10]])
                complete_embed.add_field(name="🎁 Loot", value=loot_str, inline=False)

            await channel.send(embed=complete_embed)

            for char_name, progress in leveled_chars.items():
                new_level = progress.get("new_level")
                if new_level:
                    await channel.send(f"🎉 **{char_name}** has reached **Level {new_level}**!")
        else:
            # Show the next turn with reactions
            next_turn = result.get("next_turn")
            if next_turn:
                await self._send_turn(channel, quest, next_turn, qid, total_turns)

    # ── Reaction Listener ─────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Listen for 🅰️/🅱️ reactions on turn embeds."""
        # Ignore bot reactions
        if user.bot:
            return

        # Check if this message is a pending turn
        msg_id = reaction.message.id
        if msg_id not in self.pending_turns:
            return

        emoji = str(reaction.emoji)
        if emoji not in (REACTION_A, REACTION_B):
            return

        qid = self.pending_turns.pop(msg_id)
        choice = "a" if emoji == REACTION_A else "b"

        # Remove reactions to show it's been processed
        try:
            await reaction.message.clear_reactions()
        except discord.Forbidden:
            pass

        quest = self.quest_engine.get_quest(qid)
        await self._process_choice(reaction.message.channel, qid, choice, quest)

    # ── Commands ──────────────────────────────────────────────────────
    @commands.group(invoke_without_command=True)
    async def quest(self, ctx):
        """Quest Management System. Usage: !quest [start/info/active/choice/complete]"""
        embed = discord.Embed(title="Quest System", color=0x3498db)
        embed.add_field(name="!quest start [ID]", value="Accept a quest and begin Turn 1.", inline=False)
        embed.add_field(name="React 🅰️/🅱️", value="Click a reaction on a turn prompt to choose.", inline=False)
        embed.add_field(name="!quest choice [a/b]", value="Alternate: type your choice instead.", inline=False)
        embed.add_field(name="!quest active", value="View all currently active quests.", inline=False)
        embed.add_field(name="!quest info [ID]", value="View quest details.", inline=False)
        embed.add_field(name="!quest complete [ID] [path]", value="Force-complete a quest (DM only).", inline=False)
        await ctx.send(embed=embed)

    @quest.command(name="start")
    async def quest_start(self, ctx, qid: str):
        """Accept a quest. Usage: !quest start SQ-001"""
        qid = qid.upper()
        success, result = self.quest_engine.start_quest(qid)
        if not success:
            return await ctx.send(f"❌ {result}")

        quest = self.quest_engine.get_quest(qid)
        description = quest.get('description', quest.get('premise', 'No description.'))

        embed = discord.Embed(
            title=f"📜 Quest Accepted: {result}",
            description=description,
            color=0xf1c40f
        )
        embed.add_field(name="Difficulty", value=quest.get('difficulty', 'Unknown'), inline=True)
        embed.add_field(name="XP Reward", value=f"{quest.get('xp_reward', 0)} XP", inline=True)

        total_turns = self.quest_engine.get_total_turns(qid)
        if total_turns > 0:
            embed.add_field(name="Turns", value=f"{total_turns} turns", inline=True)

        await ctx.send(embed=embed)

        # Immediately show Turn 1 with reactions
        turn_data = self.quest_engine.get_current_turn(qid)
        if turn_data:
            await self._send_turn(ctx.channel, quest, turn_data, qid, total_turns)

    @quest.command(name="choice")
    async def quest_choice(self, ctx, choice: str = None):
        """Fallback: type your choice. Usage: !quest choice a"""
        if not choice or choice.lower() not in ("a", "b"):
            return await ctx.send("❌ Usage: `!quest choice a` or `!quest choice b`")

        active = self.quest_engine.get_active_quests()
        if not active:
            return await ctx.send("📭 You have no active quests. Use `!quest start [ID]` first!")

        quest = active[-1]
        qid = quest.get('id', '').upper()
        await self._process_choice(ctx.channel, qid, choice.lower(), quest)

    @quest.command(name="active")
    async def quest_active(self, ctx):
        """View all currently active quests."""
        active = self.quest_engine.get_active_quests()
        if not active:
            return await ctx.send("📭 No active quests. Use `!quest start [ID]` to accept one!")

        embed = discord.Embed(title="📋 Active Quests", color=0x2ecc71)
        for q in active:
            progress = q.get('_progress', {})
            turn_num = progress.get('turn', 1)
            total = self.quest_engine.get_total_turns(q.get('id', ''))
            desc = q.get('description', q.get('premise', 'No description.'))[:100]
            embed.add_field(
                name=f"[{q.get('id')}] {q.get('title')}",
                value=f"{desc}...\nDifficulty: {q.get('difficulty', '?')} | XP: {q.get('xp_reward', 0)} | Turn: {turn_num}/{total}",
                inline=False
            )
        await ctx.send(embed=embed)

    @quest.command(name="info")
    async def quest_info(self, ctx, qid: str):
        """Lookup a specific quest ID."""
        quest = self.quest_engine.get_quest(qid)
        if not quest:
            return await ctx.send(f"Quest `{qid}` not found in the DB.")

        description = quest.get('description', quest.get('premise', 'No description.'))
        embed = discord.Embed(
            title=f"[{quest.get('id')}] {quest.get('title')}",
            description=description,
            color=0x3498db
        )
        embed.add_field(name="Difficulty", value=quest.get('difficulty', 'Unknown'), inline=True)
        embed.add_field(name="XP Reward", value=f"{quest.get('xp_reward', 0)} XP", inline=True)
        total = self.quest_engine.get_total_turns(quest.get('id', ''))
        if total > 0:
            embed.add_field(name="Turns", value=str(total), inline=True)
        await ctx.send(embed=embed)

    @quest.command(name="complete")
    async def quest_complete(self, ctx, qid: str, path: str = ""):
        """DM Override: Force-complete a quest. Defaults to best outcome (all A's)."""
        qid = qid.upper()
        if qid in self.quest_engine.completed:
            return await ctx.send(f"`{qid}` is already completed.")

        ok, missing = self.quest_engine.check_prerequisites(qid)
        if not ok:
            return await ctx.send(f"Prerequisites not met: Missing {', '.join(missing)}")

        # Default to best outcome (all A's) if no path given
        if not path:
            total = self.quest_engine.get_total_turns(qid)
            path = "a" * max(total, 1)

        path_list = list(path.lower())
        leveled_chars = await self.quest_engine.mark_completed(qid, path_list)

        quest = self.quest_engine.get_quest(qid)
        embed = discord.Embed(title=f"Quest Completed: {quest.get('title')}", color=0x2ecc71)
        embed.add_field(name="XP Gain", value=f"+{quest.get('xp_reward')} XP", inline=True)

        outcome_key = self.quest_engine.resolve_outcome(qid, path_list)
        if outcome_key:
            embed.add_field(name="Path Token", value=outcome_key, inline=True)

        await ctx.send(embed=embed)

        for char_name, progress in leveled_chars.items():
            new_level = progress.get("new_level")
            if new_level:
                await ctx.send(f"🎉 **{char_name}** has reached **Level {new_level}**!")


async def setup(bot):
    await bot.add_cog(QuestCog(bot))
