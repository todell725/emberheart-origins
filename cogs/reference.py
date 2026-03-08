"""
Reference Lookup Cog
Uses RAG engine to search D&D reference materials
"""

import discord
from discord.ext import commands
import logging
import asyncio

logger = logging.getLogger("Cog_Reference")


class ReferenceCog(commands.Cog):
    """D&D reference lookup using RAG (Retrieval Augmented Generation)"""

    def __init__(self, bot):
        self.bot = bot
        self.rag = None
        self._index_task = None

    async def cog_load(self):
        """Initialize RAG engine when cog loads"""
        try:
            from memory.rag_engine import get_rag_engine
            self.rag = get_rag_engine()

            # Index documents in background
            self._index_task = asyncio.create_task(self._index_documents_async())
            logger.info("Reference cog loaded, indexing in background")
        except Exception as e:
            logger.error(f"Failed to initialize RAG engine: {e}", exc_info=True)

    async def _index_documents_async(self):
        """Index documents in background to avoid blocking bot startup"""
        try:
            await asyncio.sleep(2)  # Let bot finish starting up
            logger.info("Starting document indexing...")

            # Run indexing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.rag.index_documents)

            logger.info("Document indexing complete!")
        except Exception as e:
            logger.error(f"Document indexing failed: {e}", exc_info=True)

    @commands.group(invoke_without_command=True)
    async def ref(self, ctx, *, query: str):
        """
        Search D&D reference materials

        Usage: !ref <search query>
        Example: !ref fireball spell
        """
        if not self.rag or not self.rag.documents:
            await ctx.send("⏳ Reference system is still indexing... Try again in a moment.")
            return

        await ctx.typing()

        try:
            results = self.rag.search(query, top_k=3)

            if not results:
                await ctx.send(f"❌ No results found for '{query}'")
                return

            # Show top result in detail
            top_result = results[0]

            embed = discord.Embed(
                title=f"📖 {top_result['title']}",
                description=self._truncate(top_result['content'], 2000),
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Relevance",
                value=f"{top_result['score']:.2f}",
                inline=True
            )

            embed.add_field(
                name="Category",
                value=top_result['category'].title(),
                inline=True
            )

            embed.set_footer(text=f"Showing 1 of {len(results)} results • Use !ref list <query> for all")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Reference search failed: {e}", exc_info=True)
            await ctx.send(f"❌ Search failed: {e}")

    @ref.command(name="list")
    async def ref_list(self, ctx, *, query: str):
        """List multiple search results"""
        if not self.rag or not self.rag.documents:
            await ctx.send("⏳ Reference system is still indexing...")
            return

        await ctx.typing()

        results = self.rag.search(query, top_k=10)

        if not results:
            await ctx.send(f"❌ No results found for '{query}'")
            return

        # Create list embed
        embed = discord.Embed(
            title=f"📚 Search Results: '{query}'",
            description=f"Found {len(results)} results",
            color=discord.Color.green()
        )

        for i, result in enumerate(results[:10], 1):
            embed.add_field(
                name=f"{i}. {result['title']}",
                value=f"Relevance: {result['score']:.2f} | Category: {result['category']}",
                inline=False
            )

        await ctx.send(embed=embed)

    @ref.command(name="item")
    async def ref_item(self, ctx, *, item_name: str):
        """Look up a magic item"""
        if not self.rag:
            await ctx.send("⏳ Reference system not ready")
            return

        await ctx.typing()

        result = self.rag.find_item(item_name)

        if not result:
            await ctx.send(f"❌ Magic item '{item_name}' not found")
            return

        embed = discord.Embed(
            title=f"✨ {result['title']}",
            description=self._truncate(result['content'], 2000),
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)

    @ref.command(name="spell")
    async def ref_spell(self, ctx, *, spell_name: str):
        """Look up a spell"""
        if not self.rag:
            await ctx.send("⏳ Reference system not ready")
            return

        await ctx.typing()

        result = self.rag.find_spell(spell_name)

        if not result:
            await ctx.send(f"❌ Spell '{spell_name}' not found")
            return

        embed = discord.Embed(
            title=f"🔮 {result['title']}",
            description=self._truncate(result['content'], 2000),
            color=discord.Color.purple()
        )

        await ctx.send(embed=embed)

    @ref.command(name="monster")
    async def ref_monster(self, ctx, *, monster_name: str):
        """Look up a monster"""
        if not self.rag:
            await ctx.send("⏳ Reference system not ready")
            return

        await ctx.typing()

        result = self.rag.find_monster(monster_name)

        if not result:
            await ctx.send(f"❌ Monster '{monster_name}' not found")
            return

        embed = discord.Embed(
            title=f"👹 {result['title']}",
            description=self._truncate(result['content'], 2000),
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)

    @ref.command(name="rules")
    async def ref_rules(self, ctx, *, query: str):
        """Search official D&D rules only"""
        if not self.rag:
            await ctx.send("⏳ Reference system not ready")
            return

        await ctx.typing()

        results = self.rag.search(query, top_k=3, category="rules")

        if not results:
            await ctx.send(f"❌ No rules found for '{query}'")
            return

        result = results[0]

        embed = discord.Embed(
            title=f"📜 {result['title']}",
            description=self._truncate(result['content'], 2000),
            color=discord.Color.dark_blue()
        )

        await ctx.send(embed=embed)

    @ref.command(name="campaign")
    async def ref_campaign(self, ctx, *, query: str):
        """Search campaign sourcebooks and scenarios"""
        if not self.rag:
            await ctx.send("⏳ Reference system not ready")
            return

        await ctx.typing()

        results = self.rag.search(query, top_k=3, category="campaigns")

        if not results:
            await ctx.send(f"❌ No campaign materials found for '{query}'")
            return

        result = results[0]

        embed = discord.Embed(
            title=f"🗺️ {result['title']}",
            description=self._truncate(result['content'], 2000),
            color=discord.Color.orange()
        )

        await ctx.send(embed=embed)

    @ref.command(name="stats")
    async def ref_stats(self, ctx):
        """Show reference system statistics"""
        if not self.rag:
            await ctx.send("⏳ Reference system not ready")
            return

        stats = self.rag.get_stats()

        embed = discord.Embed(
            title="📊 Reference System Stats",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Total Documents",
            value=f"{stats['total_documents']:,}",
            inline=True
        )

        embed.add_field(
            name="Total Size",
            value=f"{stats['total_size_mb']:.1f} MB",
            inline=True
        )

        embed.add_field(
            name="Embeddings",
            value="✅ Active" if stats['has_embeddings'] else "❌ Fallback mode",
            inline=True
        )

        for category, count in stats.get('by_category', {}).items():
            embed.add_field(
                name=category.title(),
                value=f"{count:,} documents",
                inline=True
            )

        await ctx.send(embed=embed)

    @ref.command(name="rebuild")
    @commands.has_permissions(administrator=True)
    async def ref_rebuild(self, ctx):
        """Rebuild the reference index (Admin only)"""
        if not self.rag:
            await ctx.send("❌ Reference system not initialized")
            return

        msg = await ctx.send("⏳ Rebuilding reference index... This may take a few minutes.")

        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.rag.index_documents(force_rebuild=True))

            stats = self.rag.get_stats()
            await msg.edit(content=f"✅ Index rebuilt! Indexed {stats['total_documents']:,} documents ({stats['total_size_mb']:.1f} MB)")

        except Exception as e:
            logger.error(f"Index rebuild failed: {e}", exc_info=True)
            await msg.edit(content=f"❌ Rebuild failed: {e}")

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to fit in embed"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."


async def setup(bot):
    await bot.add_cog(ReferenceCog(bot))
