"""
Hunting Engine for EmberHeart: Origins
Passive hunting/gathering system for wildlife
"""
from engines.idle_engine import IdleTaskEngine
from typing import List
import logging

logger = logging.getLogger("EH_Hunting")


class HuntingEngine(IdleTaskEngine):
    """
    Hunting-specific idle task engine.
    Inherits all core functionality from IdleTaskEngine.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            db_filename="HUNTING_DB.json",
            active_filename="HUNTING_ACTIVE.json",
            skill_name="Hunting",
            llm_client=llm_client
        )

    async def generate_hunt_report(
        self,
        task: dict,
        kill_count: int,
        total_xp: int,
        loot: List[str],
        character_class: str = "Hunter",
        solo: bool = False
    ) -> str:
        """
        Generate an LLM-narrated hunting report

        Args:
            task: The hunting task dict
            kill_count: Number of kills
            total_xp: Total XP earned
            loot: List of loot items
            character_class: Player's class
            solo: Whether this was a solo hunt

        Returns:
            3-sentence narrative hunting report
        """
        if not self.llm or not self.llm.is_available():
            # Fallback to generic report if LLM not available
            return self._generic_hunt_report(task, kill_count, solo)

        try:
            creature_name = task.get('creature_name', 'Unknown Creature')
            description = task.get('description', 'A wild creature')

            loot_str = ", ".join(loot[:5]) if loot else "no resources"

            prompt = f"""You are a wilderness hunting narrator. Write a vivid, 2-3 sentence hunting report.

HUNT DETAILS:
- Hunter Class: {character_class}
- Prey: {creature_name} ({description})
- Kills: {kill_count}
- XP Gained: {total_xp:,}
- Resources Gathered: {loot_str}
- Hunt Type: {"Solo tracking" if solo else "Group hunt"}

Write a short, atmospheric hunting report that captures the wilderness experience and the harvest. Focus on tracking, patience, and respect for nature. Keep it under 50 words.

Example: "You tracked the deer through morning mist, bow at the ready. After patient hours, {kill_count} clean kills rewarded your persistence. The forest provides, and you honor its bounty with gratitude."

Your report:"""

            report = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.75,
                max_tokens=100
            )

            # Clean up and return
            return report.strip() if report else self._generic_hunt_report(task, kill_count, solo)

        except Exception as e:
            logger.error(f"Failed to generate hunt report: {e}")
            return self._generic_hunt_report(task, kill_count, solo)

    def _generic_hunt_report(self, task: dict, kill_count: int, solo: bool) -> str:
        """Fallback generic hunt report"""
        creature = task.get('creature_name', 'Unknown Creature')
        solo_str = " Your solo tracking required patience and skill." if solo else " The group worked efficiently together."
        return f"You successfully hunted {kill_count} {creature}.{solo_str} The wilderness provides."
