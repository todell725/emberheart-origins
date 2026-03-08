from discord.ext import commands
import logging

logger = logging.getLogger("Cog_Relationships")

class RelationshipsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from core.transport import transport
        from core.relationships import relationship_manager
        
        self.transport = transport
        self.rm = relationship_manager

    def _resolve_character(self, name: str):
        if name.lower() in ["kaelrath", "pc-01", "king"]:
            return {"id": "PC-01", "name": "King Kaelrath"}
            
        from core.storage import resolve_character
        return resolve_character(name)

    @commands.group(invoke_without_command=True)
    async def relationship(self, ctx):
        """Manage and view character relationships."""
        await ctx.send_help(ctx.command)

    @relationship.command()
    async def view(self, ctx, char1: str, char2: str = "Kaelrath"):
        """View relationship status between two characters (default: towards Kaelrath)."""
        channel = getattr(ctx, "target_channel", ctx.channel)

        c1 = self._resolve_character(char1)
        c2 = self._resolve_character(char2)

        if not c1:
            await self.transport.send(channel, f"🔍 Character not found: '{char1}'")
            return
        if not c2:
            await self.transport.send(channel, f"🔍 Character not found: '{char2}'")
            return

        rel = self.rm.get_relationship(c1["id"], c2["id"])
        labels = self.rm.get_status_labels(rel)
        status_text = ", ".join(labels) if labels else "Neutral"
        bond_type = rel.get("bond_type", "acquaintance")

        msg = f"❤️ **Relationship Status: {c1['name']} & {c2['name']}**\n\n"
        msg += f"**Bond Type:** {bond_type.title()}\n"
        msg += f"**Status:** {status_text}\n\n"

        # Core metrics
        msg += f"**Affection:** {rel.get('affection', 25)}/100\n"
        msg += f"**Trust:** {rel.get('trust', 40)}/100\n"
        msg += f"**Tension:** {rel.get('tension', 10)}/100\n"
        msg += f"**Intimacy:** {rel.get('intimacy', 10)}/100\n"

        # Romance metrics (if applicable)
        if bond_type in ["romantic", "platonic"]:
            rom = rel.get("romantic_interest", 0)
            commit = rel.get("commitment", 0)
            stage = rel.get("romance_stage", 0)
            confessed = rel.get("confessed", False)

            msg += f"\n**Romance Metrics:**\n"
            msg += f"  Romantic Interest: {rom}/100\n"
            msg += f"  Commitment: {commit}/100\n"
            msg += f"  Stage: {stage}/7 "
            stage_names = ["Strangers", "Acquaintances", "Friends", "Close Friends",
                          "Romantic Interest", "Partners", "Committed", "Life Partners"]
            msg += f"({stage_names[min(stage, 7)]})\n"
            msg += f"  Confessed: {'Yes ❤️' if confessed else 'No'}\n"

        await self.transport.send(channel, msg)

    @relationship.command()
    async def set(self, ctx, char1: str, char2: str, metric: str, value: int):
        """Set a specific relationship metric (DM only)."""
        channel = getattr(ctx, "target_channel", ctx.channel)

        c1 = self._resolve_character(char1)
        c2 = self._resolve_character(char2)

        if not c1 or not c2:
            await self.transport.send(channel, "🔍 One or both characters not found.")
            return

        metric = metric.lower()
        valid_metrics = ["affection", "trust", "tension", "intimacy", "public_perception",
                        "romantic_interest", "commitment", "jealousy", "sexual_compatibility"]
        if metric not in valid_metrics:
            await self.transport.send(channel, f"❌ Invalid metric. Choose from: {', '.join(valid_metrics)}")
            return

        kwargs = {metric: value}
        self.rm.set_metrics(c1["id"], c2["id"], **kwargs)

        await self.transport.send(channel, f"✅ Set {metric} to {value} for {c1['name']} & {c2['name']}")

    @relationship.command()
    async def confess(self, ctx, char1: str, char2: str = None):
        """Have one character confess romantic feelings to another."""
        channel = getattr(ctx, "target_channel", ctx.channel)

        # If only one char provided, assume confessing to Kaelrath
        if char2 is None:
            char2 = char1
            char1 = "Kaelrath"

        c1 = self._resolve_character(char1)
        c2 = self._resolve_character(char2)

        if not c1 or not c2:
            await self.transport.send(channel, "🔍 One or both characters not found.")
            return

        result = self.rm.confess_romance(c1["id"], c2["id"])

        if result["success"]:
            msg = f"💕 **{c1['name']} confesses to {c2['name']}!**\n\n"
            msg += f"_{result['reason']}_\n\n"
            msg += f"The bond deepens between them..."

            # Show updated status
            rel = result["relationship"]
            labels = self.rm.get_status_labels(rel)
            msg += f"\n\n**New Status:** {', '.join(labels)}"
            msg += f"\n**Romance Stage:** {rel.get('romance_stage', 0)}/7"
        else:
            msg = f"💔 **Confession Failed**\n\n"
            msg += f"_{result['reason']}_\n\n"
            msg += f"The relationship isn't quite there yet..."

        await self.transport.send(channel, msg)

    @relationship.command()
    async def compatibility(self, ctx, char1: str, char2: str = "Kaelrath"):
        """Check romantic compatibility between two characters."""
        channel = getattr(ctx, "target_channel", ctx.channel)

        c1 = self._resolve_character(char1)
        c2 = self._resolve_character(char2)

        if not c1 or not c2:
            await self.transport.send(channel, "🔍 One or both characters not found.")
            return

        # Get orientation data
        o1 = self.rm.get_character_orientation(c1["id"])
        o2 = self.rm.get_character_orientation(c2["id"])

        compatible = self.rm.is_orientation_compatible(c1["id"], c2["id"])
        bond_type = self.rm.get_bond_type(c1["id"], c2["id"])

        msg = f"🔮 **Romantic Compatibility: {c1['name']} & {c2['name']}**\n\n"

        # Character 1
        msg += f"**{c1['name']}** ({o1.get('gender', 'unknown').title()})\n"
        msg += f"  Orientation: {o1.get('orientation', 'unknown').title()}\n"
        msg += f"  Polyamorous: {'Yes' if o1.get('polyamorous', False) else 'No'}\n\n"

        # Character 2
        msg += f"**{c2['name']}** ({o2.get('gender', 'unknown').title()})\n"
        msg += f"  Orientation: {o2.get('orientation', 'unknown').title()}\n"
        msg += f"  Polyamorous: {'Yes' if o2.get('polyamorous', False) else 'No'}\n\n"

        # Compatibility result
        if bond_type == "romantic":
            msg += f"✅ **Romantically Compatible!**\n"
            msg += f"These characters can develop romantic feelings for each other."
        elif bond_type == "brotherhood":
            msg += f"🤝 **Brotherhood Bond**\n"
            msg += f"Not romantically compatible, but can form deep platonic bonds like brothers."
        else:
            msg += f"❌ **Not Romantically Compatible**\n"
            msg += f"These characters are unlikely to form romantic attachments."

        await self.transport.send(channel, msg)

    @relationship.command()
    async def romance(self, ctx, char1: str, char2: str = "Kaelrath"):
        """View detailed romance status between two characters."""
        channel = getattr(ctx, "target_channel", ctx.channel)

        c1 = self._resolve_character(char1)
        c2 = self._resolve_character(char2)

        if not c1 or not c2:
            await self.transport.send(channel, "🔍 One or both characters not found.")
            return

        rel = self.rm.get_relationship(c1["id"], c2["id"])
        bond_type = rel.get("bond_type", "acquaintance")
        labels = self.rm.get_status_labels(rel)

        msg = f"💖 **Romance Status: {c1['name']} & {c2['name']}**\n\n"

        if bond_type == "brotherhood":
            msg += f"🤝 **Brotherhood Bond**\n\n"
            msg += f"These two share a deep platonic bond like brothers.\n\n"
            msg += f"**Affection:** {rel.get('affection', 0)}/100\n"
            msg += f"**Trust:** {rel.get('trust', 0)}/100\n"
            msg += f"**Intimacy:** {rel.get('intimacy', 0)}/100 (Platonic)\n"
            msg += f"\n**Status:** {', '.join(labels)}"
        elif bond_type == "romantic":
            stage = rel.get("romance_stage", 0)
            stage_names = ["Strangers", "Acquaintances", "Friends", "Close Friends",
                          "Romantic Interest", "Partners", "Committed", "Life Partners"]

            msg += f"**Stage:** {stage}/7 - {stage_names[min(stage, 7)]}\n"
            msg += f"**Status:** {', '.join(labels)}\n\n"

            msg += f"**Romance Metrics:**\n"
            msg += f"  Romantic Interest: {rel.get('romantic_interest', 0)}/100\n"
            msg += f"  Sexual Compatibility: {rel.get('sexual_compatibility', 0)}/100\n"
            msg += f"  Commitment: {rel.get('commitment', 0)}/100\n"
            msg += f"  Jealousy: {rel.get('jealousy', 0)}/100\n\n"

            msg += f"**Core Metrics:**\n"
            msg += f"  Affection: {rel.get('affection', 0)}/100\n"
            msg += f"  Trust: {rel.get('trust', 0)}/100\n"
            msg += f"  Intimacy: {rel.get('intimacy', 0)}/100\n"
            msg += f"  Tension: {rel.get('tension', 0)}/100\n\n"

            msg += f"**Confessed:** {'Yes ❤️' if rel.get('confessed', False) else 'Not yet'}\n"

            # Events
            events = rel.get("events", [])
            if events:
                msg += f"\n**Key Events:** {', '.join(events)}"
        else:
            msg += f"**Bond Type:** {bond_type.title()}\n"
            msg += f"Not currently a romantic connection."

        await self.transport.send(channel, msg)

async def setup(bot):
    await bot.add_cog(RelationshipsCog(bot))
