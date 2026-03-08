"""
Smithing Engine for EmberHeart: Origins
Handles converting raw ores into ingots and basic gear.
"""
from engines.idle_engine import IdleTaskEngine
from typing import List
import logging

logger = logging.getLogger("EH_Smithing")


class SmithingEngine(IdleTaskEngine):
    """
    Smithing idle task engine.
    Inherits math from IdleTaskEngine. Focuses on the clank of the hammer
    and sparks of the forge.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            db_filename="IDLE_SMITHING_DB.json",
            active_filename="SMITHING_ACTIVE.json",
            skill_name="Smithing",
            llm_client=llm_client
        )

    async def generate_smithing_report(
        self,
        task: dict,
        recipe_count: int,
        total_xp: int,
        loot: List[str],
        character_class: str = "Blacksmith",
        solo: bool = False
    ) -> str:
        """
        Generate an LLM-narrated smithing report

        Args:
            task: The smithing task dict
            recipe_count: Number of items smithed
            total_xp: Total XP earned
            loot: List of items smithed
            character_class: Player's class
            solo: Whether this was a solo session

        Returns:
            3-sentence narrative smithing report
        """
        if not self.llm or not self.llm.is_available():
            return self._generic_smithing_report(task, recipe_count, solo)

        try:
            recipe_name = task.get('recipe_name', 'Unknown Item')
            description = task.get('description', 'Metalworking.')

            loot_str = ", ".join(loot[:5]) if loot else "slag"

            prompt = f"""You are a master blacksmith narrating a blazing forging session. Write a vivid, 2-3 sentence report.

SMITHING DETAILS:
- Smith Class: {character_class}
- Project: {recipe_name} ({description})
- Items Produced: {recipe_count}
- XP Gained: {total_xp:,}
- Final Products: {loot_str}
- Environment: {"Working diligently alone at the anvil" if solo else "A chorus of hammers ringing in unison"}

Write an atmospheric, sensory smithing report. Describe the intense heat of the forge, the rhythmic ring of the hammer, or the hiss of hot metal plunging into the quenching trough. Keep it under 50 words.

Your report:"""

            report = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.75,
                max_tokens=100
            )

            return report.strip() if report else self._generic_smithing_report(task, recipe_count, solo)

        except Exception as e:
            logger.error(f"Failed to generate smithing report: {e}")
            return self._generic_smithing_report(task, recipe_count, solo)

    def _generic_smithing_report(self, task: dict, recipe_count: int, solo: bool) -> str:
        """Fallback generic smithing report"""
        recipe = task.get('recipe_name', 'Unknown Item')
        solo_str = " The lone ring of your hammer echoed for hours." if solo else " The combined efforts of the forge produced perfect results."
        return f"You successfully smithed {recipe_count} {recipe}.{solo_str} The metal is strong."
