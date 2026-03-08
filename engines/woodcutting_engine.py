"""
Woodcutting Engine for EmberHeart: Origins
Passive lumber harvesting system
"""
from engines.idle_engine import IdleTaskEngine
from typing import List
import logging

logger = logging.getLogger("EH_Woodcutting")


class WoodcuttingEngine(IdleTaskEngine):
    """
    Woodcutting-specific idle task engine.
    Inherits all core functionality from IdleTaskEngine.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            db_filename="WOODCUTTING_DB.json",
            active_filename="WOODCUTTING_ACTIVE.json",
            skill_name="Woodcutting",
            llm_client=llm_client
        )

    async def generate_woodcutting_report(
        self,
        task: dict,
        tree_count: int,
        total_xp: int,
        loot: List[str],
        character_class: str = "Lumberjack",
        solo: bool = False
    ) -> str:
        """
        Generate an LLM-narrated woodcutting report

        Args:
            task: The woodcutting task dict
            tree_count: Number of trees felled
            total_xp: Total XP earned
            loot: List of loot items
            character_class: Player's class
            solo: Whether this was a solo chopping session

        Returns:
            3-sentence narrative woodcutting report
        """
        if not self.llm or not self.llm.is_available():
            return self._generic_woodcutting_report(task, tree_count, solo)

        try:
            node_name = task.get('node_name', 'Unknown Trees')
            description = task.get('description', 'A stand of trees')

            loot_str = ", ".join(loot[:5]) if loot else "no lumber"

            prompt = f"""You are a forest work narrator. Write a vivid, 2-3 sentence woodcutting report.

WOODCUTTING DETAILS:
- Woodcutter Class: {character_class}
- Trees: {node_name} ({description})
- Trees Felled: {tree_count}
- XP Gained: {total_xp:,}
- Lumber Gathered: {loot_str}
- Work Type: {"Solo labor" if solo else "Logging crew"}

Write a short, rhythmic woodcutting report that captures the physical exertion, the sound of the axe, and the smell of fresh lumber. Focus on sweat, sawdust, and the satisfying crash of timber. Keep it under 50 words.

Example: "Your axe bit deep into bark as the forest echoed with steady strikes. One by one, {tree_count} trees fell with thunderous crashes. Sweat-soaked but triumphant, you stack the hewn logs high."

Your report:"""

            report = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.75,
                max_tokens=100
            )

            return report.strip() if report else self._generic_woodcutting_report(task, tree_count, solo)

        except Exception as e:
            logger.error(f"Failed to generate woodcutting report: {e}")
            return self._generic_woodcutting_report(task, tree_count, solo)

    def _generic_woodcutting_report(self, task: dict, tree_count: int, solo: bool) -> str:
        """Fallback generic woodcutting report"""
        trees = task.get('node_name', 'Unknown Trees')
        solo_str = " Your solo work tested your endurance." if solo else " The crew kept up a steady pace."
        return f"You successfully felled {tree_count} {trees}.{solo_str} The forest provides its bounty."
