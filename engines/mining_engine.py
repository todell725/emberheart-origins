"""
Mining Engine for EmberHeart: Origins
Passive ore and gem excavation system
"""
from engines.idle_engine import IdleTaskEngine
from typing import List
import logging

logger = logging.getLogger("EH_Mining")


class MiningEngine(IdleTaskEngine):
    """
    Mining-specific idle task engine.
    Inherits all core functionality from IdleTaskEngine.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            db_filename="MINING_DB.json",
            active_filename="MINING_ACTIVE.json",
            skill_name="Mining",
            llm_client=llm_client
        )

    async def generate_mining_report(
        self,
        task: dict,
        node_count: int,
        total_xp: int,
        loot: List[str],
        character_class: str = "Miner",
        solo: bool = False
    ) -> str:
        """
        Generate an LLM-narrated mining report

        Args:
            task: The mining task dict
            node_count: Number of nodes mined
            total_xp: Total XP earned
            loot: List of loot items
            character_class: Player's class
            solo: Whether this was a solo mining session

        Returns:
            3-sentence narrative mining report
        """
        if not self.llm or not self.llm.is_available():
            return self._generic_mining_report(task, node_count, solo)

        try:
            node_name = task.get('node_name', 'Unknown Deposit')
            description = task.get('description', 'A mineral vein')

            loot_str = ", ".join(loot[:5]) if loot else "no ore"

            prompt = f"""You are a mining expedition narrator. Write a vivid, 2-3 sentence mining report.

MINING DETAILS:
- Miner Class: {character_class}
- Deposit: {node_name} ({description})
- Nodes Mined: {node_count}
- XP Gained: {total_xp:,}
- Resources Gathered: {loot_str}
- Work Type: {"Solo excavation" if solo else "Group effort"}

Write a short, atmospheric mining report that captures the physical labor, the spark of the pickaxe, and the satisfaction of striking ore. Focus on dust, darkness, and discovery. Keep it under 50 words.

Example: "Your pickaxe rang out in steady rhythm as {node_count} veins shattered beneath your blows. Dust filled the air as glittering ore tumbled free. Exhausted but satisfied, you gather your hard-won spoils from the depths."

Your report:"""

            report = await self.llm.async_generate(
                prompt=prompt,
                temperature=0.75,
                max_tokens=100
            )

            return report.strip() if report else self._generic_mining_report(task, node_count, solo)

        except Exception as e:
            logger.error(f"Failed to generate mining report: {e}")
            return self._generic_mining_report(task, node_count, solo)

    def _generic_mining_report(self, task: dict, node_count: int, solo: bool) -> str:
        """Fallback generic mining report"""
        node = task.get('node_name', 'Unknown Deposit')
        solo_str = " Your solo work was grueling but rewarding." if solo else " The team worked efficiently together."
        return f"You successfully mined {node_count} {node} deposits.{solo_str} The earth provides its riches."
