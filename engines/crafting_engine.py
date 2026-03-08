"""
Crafting Engine for EmberHeart: Origins
Handles converting base materials from gathering skills into usable gear.
"""
from engines.idle_engine import IdleTaskEngine
from typing import List
import logging

logger = logging.getLogger("EH_Crafting")


class CraftingEngine(IdleTaskEngine):
    """
    Crafting idle task engine.
    Inherits math and logic from IdleTaskEngine, focusing on fletching,
    leatherworking, alchemy, and legendary gemcrafting.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            db_filename="IDLE_CRAFTING_DB.json",
            active_filename="CRAFTING_ACTIVE.json",
            skill_name="Crafting",
            llm_client=llm_client
        )

    async def generate_crafting_report(
        self,
        task: dict,
        recipe_count: int,
        total_xp: int,
        loot: List[str],
        character_class: str = "Artisan",
        solo: bool = False
    ) -> str:
        """
        Generate an LLM-narrated crafting report

        Args:
            task: The crafting task dict
            recipe_count: Number of items crafted
            total_xp: Total XP earned
            loot: List of items crafted
            character_class: Player's class
            solo: Whether this was a solo session

        Returns:
            3-sentence narrative crafting report
        """
        if not self.llm or not self.llm.is_available():
            return self._generic_crafting_report(task, recipe_count, solo)

        try:
            recipe_name = task.get('recipe_name', 'Unknown Item')
            description = task.get('description', 'Crafting supplies.')

            loot_str = ", ".join(loot[:5]) if loot else "nothing usable"

            prompt = f"""You are a master artisan narrating a crafting session. Write a vivid, 2-3 sentence report.

CRAFTING DETAILS:
- Crafter Class: {character_class}
- Project: {recipe_name} ({description})
- Items Produced: {recipe_count}
- XP Gained: {total_xp:,}
- Final Products: {loot_str}
- Environment: {"Working diligently alone" if solo else "A bustling, collaborative workshop"}

Write an atmospheric, sensory crafting report. Describe the shaving of wood, the stitching of stiff leather, or the brilliant, blinding flash as a celestial gem is cut. Let the material dictate the tone. Keep it under 50 words.

Your report:"""

            report = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.75,
                max_tokens=100
            )

            return report.strip() if report else self._generic_crafting_report(task, recipe_count, solo)

        except Exception as e:
            logger.error(f"Failed to generate crafting report: {e}")
            return self._generic_crafting_report(task, recipe_count, solo)

    def _generic_crafting_report(self, task: dict, recipe_count: int, solo: bool) -> str:
        """Fallback generic crafting report"""
        recipe = task.get('recipe_name', 'Unknown Item')
        solo_str = " Working alone, you perfected each piece." if solo else " The workshop hummed with productive energy."
        return f"You successfully crafted {recipe_count} {recipe}.{solo_str} True artisan craftsmanship."
