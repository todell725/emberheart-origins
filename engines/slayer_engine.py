"""
Slayer Engine for EmberHeart: Origins
Idle monster hunting system
"""
from engines.idle_engine import IdleTaskEngine
from typing import List
import logging

logger = logging.getLogger("EH_Slayer")


class SlayerEngine(IdleTaskEngine):
    """
    Slayer-specific idle task engine.
    Inherits all core functionality from IdleTaskEngine.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            db_filename="IDLE_SLAYER_DB.json",
            active_filename="SLAYER_ACTIVE.json",
            skill_name="Slayer",
            llm_client=llm_client
        )

    async def generate_battle_report(
        self,
        task: dict,
        kill_count: int,
        total_xp: int,
        loot: List[str],
        character_class: str = "Adventurer",
        solo: bool = False
    ) -> str:
        """
        Generate an LLM-narrated battle report

        Args:
            task: The slayer task dict
            kill_count: Number of kills
            total_xp: Total XP earned
            loot: List of loot items
            character_class: Player's class
            solo: Whether this was a solo hunt

        Returns:
            3-sentence narrative battle report
        """
        if not self.llm or not self.llm.is_available():
            # Fallback to generic report if LLM not available
            return self._generic_battle_report(task, kill_count, solo)

        try:
            monster_name = task.get('monster_name', 'Unknown Beast')
            description = task.get('description', 'A dangerous creature')

            loot_str = ", ".join(loot[:5]) if loot else "no loot"

            prompt = f"""You are a fantasy battle narrator. Write a vivid, 2-3 sentence battle report.

BATTLE DETAILS:
- Character Class: {character_class}
- Enemy: {monster_name} ({description})
- Kills: {kill_count}
- XP Gained: {total_xp:,}
- Notable Loot: {loot_str}
- Hunt Type: {"Solo (grueling)" if solo else "Party (efficient)"}

Write a short, dramatic battle report that captures the struggle and victory. Focus on the character's fighting style based on their class. Keep it under 50 words.

Example: "Your blade sang through the night as goblin after goblin fell to your fury. By dawn, {kill_count} corpses littered the forest floor. Exhausted but victorious, you claim your spoils and feel your skills sharpen from the brutal grind."

Your report:"""

            report = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.75,
                max_tokens=100
            )

            # Clean up and return
            return report.strip() if report else self._generic_battle_report(task, kill_count, solo)

        except Exception as e:
            logger.error(f"Failed to generate battle report: {e}")
            return self._generic_battle_report(task, kill_count, solo)

    def _generic_battle_report(self, task: dict, kill_count: int, solo: bool) -> str:
        """Fallback generic battle report"""
        monster = task.get('monster_name', 'Unknown Beast')
        solo_str = " Your solo battle was grueling, but you prevailed." if solo else ""
        return f"You fought valiantly against the {monster}, slaying {kill_count} in total.{solo_str} Victory is yours!"
