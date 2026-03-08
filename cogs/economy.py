"""
Economy Cog for EmberHeart: Origins
Shop commands: !shop inventory, !shop buy
Ported from Claudes-EmberHeart
"""
import discord
from discord.ext import commands
from discord import ui
import logging
from engines.shop_engine import DynamicShop
from core.routing import require_channel

logger = logging.getLogger("Cog_Economy")


class ShopItemSelect(ui.Select):
    """Dropdown for selecting shop items"""
    def __init__(self, shop_items, buyer_id, shop_engine):
        self.shop_engine = shop_engine
        self.buyer_id = buyer_id

        options = []
        for idx, item in enumerate(shop_items[:25]):  # Discord limit: 25 options
            options.append(
                discord.SelectOption(
                    label=item['name'][:100],  # Max 100 chars
                    description=f"{item['cost']} - {item['type']}"[:100],
                    value=str(idx)
                )
            )

        super().__init__(
            placeholder="Choose an item to purchase...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.shop_items = shop_items

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        item = self.shop_items[idx]

        # Attempt purchase
        success, response_msg = await self.shop_engine.purchase_item(
            self.buyer_id,
            item['name']
        )

        if success:
            await interaction.response.send_message(
                f"✅ {response_msg}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ {response_msg}",
                ephemeral=True
            )


class ShopView(ui.View):
    """Interactive shop view with dropdown selection"""
    def __init__(self, shop_items, buyer_id, shop_engine):
        super().__init__(timeout=180)  # 3 minute timeout
        self.add_item(ShopItemSelect(shop_items, buyer_id, shop_engine))

    @ui.button(label="Refresh Stock", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "Use `!shop inventory` to refresh the shop display.",
            ephemeral=True
        )

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shop_engine = DynamicShop()

    @commands.group(invoke_without_command=True)
    async def shop(self, ctx):
        """Displays the current Black Market / Forge rotation. Group: !shop"""
        await ctx.send("Usage: `!shop inventory` or `!shop buy [item name]`")

    @shop.command(name="inventory", aliases=["list"])
    @require_channel("shop")
    async def shop_inventory(self, ctx):
        """Post the current shop stock with interactive purchase menu."""
        channel = getattr(ctx, "target_channel", ctx.channel)

        if not self.shop_engine.current_stock:
            await self.shop_engine.generate_stock()

        embed = discord.Embed(
            title="🏪 The Gilded Exchange",
            description="*\"Finest wares from the Forge and the Far-Realms...\"*\n\n**Use the dropdown below to purchase items!**",
            color=0xFFD700
        )

        armory, arcanum = "", ""
        for item in self.shop_engine.current_stock[:15]:
            armory += f"**{item['name']}** ({item['type']})\n-- *{item['desc']}* -- **{item['cost']}**\n"
        for item in self.shop_engine.current_stock[15:]:
            arcanum += f"**{item['name']}**\n-- *{item['desc']}* -- **{item['cost']}**\n"

        if armory: embed.add_field(name="⚔️ The Armory", value=armory[:1024], inline=False)
        if arcanum: embed.add_field(name="📜 The Arcanum", value=arcanum[:1024], inline=False)

        # Add interactive view
        buyer_id = "PC-01"  # TODO: Get from user context
        view = ShopView(self.shop_engine.current_stock, buyer_id, self.shop_engine)

        await channel.send(embed=embed, view=view)

    @shop.command(name="buy")
    @require_channel("shop")
    async def shop_buy(self, ctx, *, item_name: str):
        """Purchase an item from the current rotation."""
        channel = getattr(ctx, "target_channel", ctx.channel)

        buyer_id = "PC-01"

        success, response_msg = await self.shop_engine.purchase_item(buyer_id, item_name)

        if success:
            await channel.send(f"Transaction: {response_msg}")
        else:
            await channel.send(f"Failed: {response_msg}")

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
