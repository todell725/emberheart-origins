"""
Fishing Engine for EmberHeart: Origins
Passive fishing and aquatic resource gathering system
"""
from engines.idle_engine import IdleTaskEngine
from typing import List
import logging

logger = logging.getLogger("EH_Fishing")


class FishingEngine(IdleTaskEngine):
    """
    Fishing-specific idle task engine.
    Inherits all core functionality from IdleTaskEngine.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            db_filename="FISHING_DB.json",
            active_filename="FISHING_ACTIVE.json",
            skill_name="Fishing",
            llm_client=llm_client
        )

    async def generate_fishing_report(
        self,
        task: dict,
        catch_count: int,
        total_xp: int,
        loot: List[str],
        character_class: str = "Fisher",
        solo: bool = False
    ) -> str:
        """
        Generate an LLM-narrated fishing report

        Args:
            task: The fishing task dict
            catch_count: Number of fish caught
            total_xp: Total XP earned
            loot: List of loot items
            character_class: Player's class
            solo: Whether this was a solo fishing session

        Returns:
            3-sentence narrative fishing report
        """
        if not self.llm or not self.llm.is_available():
            return self._generic_fishing_report(task, catch_count, solo)

        try:
            node_name = task.get('node_name', 'Unknown Waters')
            description = task.get('description', 'A fishing spot')

            loot_str = ", ".join(loot[:5]) if loot else "no fish"

            prompt = f"""You are a peaceful fishing expedition narrator. Write a vivid, 2-3 sentence fishing report.

FISHING DETAILS:
- Fisher Class: {character_class}
- Location: {node_name} ({description})
- Fish Caught: {catch_count}
- XP Gained: {total_xp:,}
- Catch: {loot_str}
- Session Type: {"Solo contemplation" if solo else "Group outing"}

Write a short, serene fishing report that captures the patience, the tension of the line, and the peaceful environment. Focus on water, weather, and the thrill of a catch. Keep it under 50 words.

Example: "You cast your line into calm waters as the sun rose. After patient hours, {catch_count} fish broke the surface in shimmering splashes. The rhythm of water and line brought both bounty and peace to your soul."

Your report:"""

            report = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.75,
                max_tokens=100
            )

            return report.strip() if report else self._generic_fishing_report(task, catch_count, solo)

        except Exception as e:
            logger.error(f"Failed to generate fishing report: {e}")
            return self._generic_fishing_report(task, catch_count, solo)

    def _generic_fishing_report(self, task: dict, catch_count: int, solo: bool) -> str:
        """Fallback generic fishing report"""
        spot = task.get('node_name', 'Unknown Waters')
        solo_str = " Your solitary patience was rewarded." if solo else " The group shared stories while waiting."
        return f"You successfully fished {catch_count} times at {spot}.{solo_str} The waters provide."
