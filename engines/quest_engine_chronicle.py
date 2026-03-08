"""
Quest Engine with Chronicle Integration
Wraps the original QuestEngine to add Chronicle logging
"""
import logging
from engines.quest_engine import QuestEngine as BaseQuestEngine

logger = logging.getLogger(__name__)


class QuestEngineWithChronicle(BaseQuestEngine):
    """Quest engine that logs to Chronicle"""

    def __init__(self, chronicle=None):
        super().__init__()
        self.chronicle = chronicle

    async def mark_completed(self, qid: str, path: list = None) -> list:
        """Mark quest complete and log to Chronicle"""
        # Call original implementation
        leveled = await super().mark_completed(qid, path)

        # Log to Chronicle if available
        if self.chronicle:
            quest = self.get_quest(qid)
            if quest:
                # Get party member IDs
                party_ids = ["PC-01", "PC-02", "PC-03", "PC-04", "PC-05"]  # Main party

                outcome_key = self.resolve_outcome(qid, path) if path else "default"

                self.chronicle.remember(
                    content=f"Quest completed: {quest.get('title', qid)} (Path: {outcome_key})",
                    category="quest",
                    characters=party_ids,
                    metadata={
                        "quest_id": qid,
                        "xp_reward": quest.get("xp_reward", 0),
                        "path": outcome_key
                    }
                )
                logger.info(f"Logged quest {qid} to Chronicle")

        return leveled
