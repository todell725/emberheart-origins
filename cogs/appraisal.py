"""
Unidentified Relic Appraisal Minigame
Players get mystery items from slayer, must appraise them via NPCs
"""
import discord
from discord.ext import commands
import logging
import random
import json

logger = logging.getLogger("Cog_Appraisal")


class AppraisalCog(commands.Cog):
    """
    Relic appraisal system - identify cursed/magical items via NPC interaction
    """

    def __init__(self, bot):
        self.bot = bot
        # Hidden item database (player doesn't see this until appraised)
        self.unidentified_items = {}  # item_id -> true_stats

    @commands.command(name="appraise")
    async def appraise(self, ctx, *, item_name: str = None):
        """
        Bring an Unidentified Item to a merchant NPC to appraise it.
        The merchant will reveal (or lie about) its true nature!
        Usage: !appraise Unidentified Relic #3
        """
        if not item_name:
            await ctx.send("❌ Usage: `!appraise <item name>`\nExample: `!appraise Unidentified Relic #3`")
            return

        try:
            from core.storage import load_character_state

            character_id = "PC-01"  # TODO: Get from user context
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            # Check if player has the item
            inventory = char_state.get("status", {}).get("inventory", [])

            matching_items = [item for item in inventory if item_name.lower() in item.lower()]

            if not matching_items:
                await ctx.send(f"❌ You don't have an item matching **{item_name}** in your inventory.")
                return

            target_item = matching_items[0]

            # Check if it's actually an unidentified item
            if "unidentified" not in target_item.lower():
                await ctx.send(f"❌ **{target_item}** is already identified! Only mysterious items need appraisal.")
                return

            # Generate or retrieve true item stats
            item_id = target_item
            if item_id not in self.unidentified_items:
                self.unidentified_items[item_id] = self._generate_true_item()

            true_item = self.unidentified_items[item_id]

            # Generate merchant appraisal via LLM (with potential lies!)
            appraisal = await self._generate_appraisal(true_item, character_id)

            # Send appraisal
            msg = f"""
╔═══════════════════════════════════════╗
║  🔮 **MERCHANT APPRAISAL** 🔮          ║
╚═══════════════════════════════════════╝

*A greedy merchant examines the relic with a sly grin...*

{appraisal['dialogue']}

**Merchant's Offer:**
> Item: **{appraisal['revealed_name']}**
> Value: **{appraisal['offered_price']} Gold**
> Curse Status: {appraisal['curse_claim']}

**Options:**
• `!accept_appraisal` - Accept the merchant's price and identify the item
• `!haggle` - Try to get a better price (persuasion check!)
• `!threaten` - Intimidate the merchant into honesty
"""

            # Store appraisal session
            char_state.setdefault("_temp", {})["pending_appraisal"] = {
                "item": target_item,
                "true_stats": true_item,
                "merchant_offer": appraisal
            }

            from core.state_store import coordinator
            await coordinator.update_character_state_async(character_id, char_state)

            await ctx.send(msg)

        except Exception as e:
            logger.error(f"Failed to appraise item: {e}", exc_info=True)
            await ctx.send("❌ Failed to appraise item. Please try again.")

    def _generate_true_item(self) -> dict:
        """Generate the true stats of an unidentified item"""
        item_types = [
            {"name": "Cursed Blade of Shadows", "value": 500, "cursed": True, "effect": "-2 Charisma, +3 Stealth"},
            {"name": "Ring of Minor Warding", "value": 300, "cursed": False, "effect": "+1 AC"},
            {"name": "Amulet of the Damned", "value": 800, "cursed": True, "effect": "+2 Spell Power, -5 Max HP"},
            {"name": "Potion of Unknown Origin", "value": 150, "cursed": False, "effect": "??? (drink to find out)"},
            {"name": "Ancient Elven Compass", "value": 600, "cursed": False, "effect": "Points toward nearest treasure"},
            {"name": "Blood-Stained Gauntlets", "value": 400, "cursed": True, "effect": "+2 Strength, rage on critical"},
        ]

        return random.choice(item_types)

    async def _generate_appraisal(self, true_item: dict, character_id: str) -> dict:
        """
        Generate merchant appraisal (AI may lie!)

        Args:
            true_item: True item stats
            character_id: Character being appraised

        Returns:
            Appraisal dictionary with dialogue and offer
        """
        try:
            # Merchant tries to lowball or hide curse
            is_cursed = true_item.get("cursed", False)
            true_value = true_item.get("value", 100)

            # Merchant behavior: 60% lowball, 30% fair, 10% generous
            merchant_behavior = random.choices(["lowball", "fair", "generous"], weights=[0.6, 0.3, 0.1])[0]

            if merchant_behavior == "lowball":
                offered_price = int(true_value * random.uniform(0.3, 0.6))
                curse_claim = "Harmless trinket" if is_cursed else "Nothing special"
            elif merchant_behavior == "fair":
                offered_price = int(true_value * random.uniform(0.8, 1.0))
                curse_claim = "⚠️ CURSED" if is_cursed else "Clean"
            else:  # generous
                offered_price = int(true_value * random.uniform(1.1, 1.3))
                curse_claim = "⚠️ DANGEROUSLY CURSED" if is_cursed else "Blessed item"

            # Generate merchant dialogue via LLM
            if self.bot.llm and self.bot.llm.is_available():
                prompt = f"""You are a shady goblin merchant appraising a magical item. You're trying to {"lowball the customer" if merchant_behavior == "lowball" else "give a fair assessment" if merchant_behavior == "fair" else "be surprisingly generous"}.

ITEM DETAILS:
- True Name: {true_item['name']}
- True Value: {true_value} gold
- Cursed: {"Yes (but you might hide this!)" if is_cursed else "No"}
- Your Offer: {offered_price} gold

Generate a short (2-3 sentences) merchant dialogue where you:
1. Examine the item dramatically
2. {"Try to downplay its value or hide the curse" if merchant_behavior == "lowball" else "Give an honest assessment" if merchant_behavior == "fair" else "Overvalue it suspiciously"}
3. Make your offer

Example: "Hmm, this old thing? Seen hundreds like it. Probably worth... oh, maybe 50 gold if you're lucky. I'll take it off your hands, being generous as I am."

Your dialogue:"""

                dialogue = await self.bot.llm.async_generate(prompt=prompt, temperature=0.8, max_tokens=120)
                dialogue = dialogue.strip() if dialogue else f"*examines item* I'll give you {offered_price} gold for it."
            else:
                dialogue = f"*The merchant eyes the relic greedily* I'll offer {offered_price} gold for this... trinket."

            return {
                "revealed_name": true_item['name'],
                "offered_price": offered_price,
                "curse_claim": curse_claim,
                "dialogue": dialogue,
                "true_value": true_value,
                "merchant_behavior": merchant_behavior
            }

        except Exception as e:
            logger.error(f"Failed to generate appraisal: {e}")
            return {
                "revealed_name": true_item['name'],
                "offered_price": 50,
                "curse_claim": "Unknown",
                "dialogue": "I'll give you 50 gold.",
                "true_value": true_item.get("value", 100),
                "merchant_behavior": "lowball"
            }

    @commands.command(name="accept_appraisal")
    async def accept_appraisal(self, ctx):
        """Accept the merchant's appraisal and sell/identify the item"""
        try:
            from core.storage import load_character_state

            character_id = "PC-01"
            char_state = load_character_state(character_id)

            pending = char_state.get("_temp", {}).get("pending_appraisal")

            if not pending:
                await ctx.send("❌ No pending appraisal. Use `!appraise <item>` first.")
                return

            # Remove unidentified item from inventory
            inventory = char_state.get("status", {}).get("inventory", [])
            if pending['item'] in inventory:
                inventory.remove(pending['item'])

            # Add identified item
            true_item = pending['true_stats']
            inventory.append(f"{true_item['name']} [{true_item['effect']}]")

            # Add gold
            char_state.setdefault("status", {})["inventory"] = inventory

            # Clear pending
            char_state["_temp"]["pending_appraisal"] = None

            from core.state_store import coordinator
            await coordinator.update_character_state_async(character_id, char_state)

            await ctx.send(
                f"✅ **Appraisal Complete!**\n"
                f"> Item Identified: **{true_item['name']}**\n"
                f"> True Value: {true_item['value']} gold\n"
                f"> Effect: {true_item['effect']}\n"
                f"> {'⚠️ **CURSED ITEM!**' if true_item.get('cursed') else '✨ Safe to use'}"
            )

        except Exception as e:
            logger.error(f"Failed to accept appraisal: {e}", exc_info=True)
            await ctx.send("❌ Failed to complete appraisal.")


async def setup(bot):
    await bot.add_cog(AppraisalCog(bot))
