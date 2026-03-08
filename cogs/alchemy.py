"""
Blind Alchemical Brewing Minigame
Players gather ingredients, brew mystery potions with chaotic AI-generated effects
"""
import discord
from discord.ext import commands
import logging
import random

logger = logging.getLogger("Cog_Alchemy")


class AlchemyCog(commands.Cog):
    """
    Alchemy system - gather components, brew mystery potions
    """

    def __init__(self, bot):
        self.bot = bot
        self.components = [
            "Bloodroot", "Troll Fat", "Phoenix Ash", "Dragon Scale", "Moonflower",
            "Shadow Essence", "Starlight Dust", "Goblin Spit", "Witch's Hair",
            "Giant's Tooth", "Ectoplasm", "Fairy Wings", "Snake Venom"
        ]

    @commands.command(name="gather")
    async def gather(self, ctx):
        """
        Gather random alchemical components from the wilderness.
        """
        try:
            from core.storage import load_character_state

            character_id = "PC-01"  # TODO: Get from user
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            # Gather 1-3 random components
            num_components = random.randint(1, 3)
            gathered = random.sample(self.components, num_components)

            # Add to inventory
            inventory = char_state.setdefault("status", {}).setdefault("inventory", [])
            inventory.extend(gathered)

            from core.state_store import coordinator
            await coordinator.update_character_state_async(character_id, char_state)

            await ctx.send(
                f"🌿 **Gathering Complete!**\n"
                f"> You gathered: {', '.join(f'**{c}**' for c in gathered)}\n"
                f"> Use `!brew <component1> <component2>` to create a potion!"
            )

        except Exception as e:
            logger.error(f"Failed to gather: {e}", exc_info=True)
            await ctx.send("❌ Failed to gather components.")

    @commands.command(name="brew")
    async def brew(self, ctx, comp1: str = None, comp2: str = None):
        """
        Brew a mystery potion from two components.
        You won't know what it does until you drink it!
        Usage: !brew Bloodroot "Troll Fat"
        """
        if not comp1 or not comp2:
            await ctx.send(
                "❌ Usage: `!brew <component1> <component2>`\n"
                "Example: `!brew Bloodroot Moonflower`"
            )
            return

        try:
            from core.storage import load_character_state

            character_id = "PC-01"
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            inventory = char_state.get("status", {}).get("inventory", [])

            # Check if player has both components (case-insensitive)
            comp1_match = next((item for item in inventory if comp1.lower() in item.lower()), None)
            comp2_match = next((item for item in inventory if comp2.lower() in item.lower()), None)

            if not comp1_match:
                await ctx.send(f"❌ You don't have **{comp1}** in your inventory.")
                return

            if not comp2_match:
                await ctx.send(f"❌ You don't have **{comp2}** in your inventory.")
                return

            # Remove components from inventory
            inventory.remove(comp1_match)
            inventory.remove(comp2_match)

            # Create mystery potion
            potion_id = f"potion_{random.randint(1000, 9999)}"
            mystery_potion = f"Vial of Bubbling {random.choice(['Orange', 'Green', 'Purple', 'Black', 'Silver'])} Liquid #{potion_id}"

            inventory.append(mystery_potion)
            char_state["status"]["inventory"] = inventory

            # Store hidden potion effects
            potion_recipe = f"{comp1_match}+{comp2_match}"
            char_state.setdefault("_temp", {}).setdefault("potion_effects", {})[mystery_potion] = {
                "recipe": potion_recipe,
                "components": [comp1_match, comp2_match]
            }

            from core.state_store import coordinator
            await coordinator.update_character_state_async(character_id, char_state)

            await ctx.send(
                f"🧪 **Brewing Complete!**\n"
                f"> Ingredients: **{comp1_match}** + **{comp2_match}**\n"
                f"> Result: **{mystery_potion}**\n\n"
                f"*You have no idea what this will do...*\n"
                f"Options:\n"
                f"• `!quaff {mystery_potion}` - Drink it and find out!\n"
                f"• Ask an Alchemist NPC in #off-topic for hints"
            )

        except Exception as e:
            logger.error(f"Failed to brew potion: {e}", exc_info=True)
            await ctx.send("❌ Failed to brew potion.")

    @commands.command(name="quaff")
    async def quaff(self, ctx, *, potion_name: str = None):
        """
        Drink a mystery potion and discover its effects!
        WARNING: Effects can be good OR bad!
        Usage: !quaff Vial of Bubbling Orange Liquid #1234
        """
        if not potion_name:
            await ctx.send("❌ Usage: `!quaff <potion name>`")
            return

        try:
            from core.storage import load_character_state

            character_id = "PC-01"
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            inventory = char_state.get("status", {}).get("inventory", [])

            # Find matching potion
            potion_match = next((item for item in inventory if potion_name.lower() in item.lower()), None)

            if not potion_match:
                await ctx.send(f"❌ You don't have **{potion_name}** in your inventory.")
                return

            # Check if it's actually a potion
            if "vial" not in potion_match.lower() and "potion" not in potion_match.lower():
                await ctx.send(f"❌ **{potion_match}** is not a potion!")
                return

            # Get stored recipe
            potion_data = char_state.get("_temp", {}).get("potion_effects", {}).get(potion_match, {})
            components = potion_data.get("components", ["Unknown", "Unknown"])

            # Generate potion effects via AI
            effects = await self._generate_potion_effects(components)

            # Remove potion from inventory
            inventory.remove(potion_match)
            char_state["status"]["inventory"] = inventory

            # Apply effects (simplified for demo)
            char_state.setdefault("status", {}).setdefault("active_effects", []).append(effects["mechanical_effect"])

            from core.state_store import coordinator
            await coordinator.update_character_state_async(character_id, char_state)

            # Send results
            msg = f"""
╔═══════════════════════════════════════╗
║  🧪 **POTION CONSUMED** 🧪             ║
╚═══════════════════════════════════════╝

*You drink the bubbling liquid...*

{effects['narrative']}

**Mechanical Effect:**
> {effects['mechanical_effect']}
> Duration: {effects['duration']}

{'✨ **Lucky!**' if effects['is_positive'] else '⚠️ **Beware!**'}
"""

            await ctx.send(msg)

        except Exception as e:
            logger.error(f"Failed to quaff potion: {e}", exc_info=True)
            await ctx.send("❌ Failed to drink potion.")

    async def _generate_potion_effects(self, components: list) -> dict:
        """
        Generate potion effects via AI

        Args:
            components: List of 2 component names

        Returns:
            Dictionary with narrative and mechanical effects
        """
        try:
            if self.bot.llm and self.bot.llm.is_available():
                prompt = f"""You are a chaotic alchemist describing the effects of a mystery potion.

COMPONENTS USED:
- {components[0]}
- {components[1]}

Generate a potion effect with:
1. A bizarre, vivid narrative description (2-3 sentences) of what happens when you drink it
2. A mechanical game effect (buff or debuff)

The effect should be creative and match the components' themes. Make it 50/50 chance good or bad.

Example:
NARRATIVE: Your skin turns invisible but your bones glow neon blue. You hear distant laughter as your shadow splits into three copies. The effect is... unsettling.
MECHANICAL: +3 Stealth, -2 Charisma, Shadow Clones
DURATION: 24 hours
POSITIVE: False

Now generate effects for {components[0]} + {components[1]}:"""

                result = await self.bot.llm.async_generate(prompt=prompt, temperature=0.9, max_tokens=150)

                # Parse result (simplified)
                lines = result.strip().split('\n')
                narrative = result[:200] if result else "You feel strange..."

                # Randomize mechanical effect
                is_positive = random.random() > 0.5
                if is_positive:
                    mechanical = random.choice([
                        "+2 Strength for 1 hour",
                        "+3 Intelligence for 1 hour",
                        "Invisibility for 10 minutes",
                        "+10 Temporary HP",
                        "Fly speed 30ft for 1 hour"
                    ])
                else:
                    mechanical = random.choice([
                        "-2 Charisma for 1 hour (you smell awful)",
                        "Confused for 10 minutes (roll movement randomly)",
                        "-5 Max HP for 24 hours",
                        "Uncontrollable hiccups (disadvantage on stealth)",
                        "Shrunk to half size for 1 hour"
                    ])

                return {
                    "narrative": narrative,
                    "mechanical_effect": mechanical,
                    "duration": "1 hour",
                    "is_positive": is_positive
                }

            else:
                return self._fallback_potion_effect()

        except Exception as e:
            logger.error(f"Failed to generate potion effects: {e}")
            return self._fallback_potion_effect()

    def _fallback_potion_effect(self) -> dict:
        """Fallback if LLM unavailable"""
        is_positive = random.random() > 0.5

        if is_positive:
            return {
                "narrative": "A warm energy fills your body. You feel stronger and more confident!",
                "mechanical_effect": "+2 to all stats for 1 hour",
                "duration": "1 hour",
                "is_positive": True
            }
        else:
            return {
                "narrative": "Your stomach lurches. Everything smells like rotten eggs. This was a mistake.",
                "mechanical_effect": "-2 Constitution for 1 hour (nauseous)",
                "duration": "1 hour",
                "is_positive": False
            }


async def setup(bot):
    await bot.add_cog(AlchemyCog(bot))
