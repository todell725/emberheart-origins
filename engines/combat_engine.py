"""
Combat Engine for EmberHeart: Origins
Ported from Claudes-EmberHeart (with bug fix on line 69)
"""
import logging
from core.config import XP_THRESHOLDS

logger = logging.getLogger("EH_Combat")

# Import romance engine for natural relationship progression
try:
    from engines.romance_engine import romance_engine
    ROMANCE_ENABLED = True
except ImportError:
    ROMANCE_ENABLED = False
    logger.warning("Romance engine not available - relationship bonding disabled")


class CombatTracker:
    def __init__(self):
        self.order = []
        self.current_index = -1
        self.active = False

    def add_combatant(self, name, roll, hp):
        self.order.append({"name": name, "init": roll, "hp": hp})
        self.order.sort(key=lambda x: x['init'], reverse=True)

    def next_turn(self):
        if not self.order: return None
        self.current_index = (self.current_index + 1) % len(self.order)
        return self.order[self.current_index]

    def clear(self):
        self.order = []
        self.current_index = -1
        self.active = False

    async def add_party_xp(self, xp: int, target_ids: list = None, difficulty: str = "normal", kill_count: int = 1) -> dict:
        """
        Award XP to the party. If target_ids is provided, only those IDs get XP.
        Returns a dictionary breakdown mapping character names to their earned XP and level ups.

        Args:
            xp: Experience points to award
            target_ids: Optional list of character IDs to award XP to
            difficulty: Combat difficulty ("normal", "hard", "deadly") for romance bonding
            kill_count: Number of enemies defeated (for scaling romance bonding in idle slayer)
        """
        leveled_up = []
        xp_breakdown = {}
        
        try:
            from core.storage import load_all_character_states
            all_states = load_all_character_states()

            party = [s for s in all_states if s.get("id", "").startswith("PC-")]

            if target_ids:
                party = [s for s in party if s.get("id") in target_ids]

            if not party:
                logger.warning(f"XP Sync failed: No matching party members found.")
                return {}

            # Track party IDs for romance bonding
            party_ids = []

            for char_state in party:
                char_id = char_state.get("id")
                char_name = char_state.get("name", char_id)
                party_ids.append(char_id)

                old_xp = char_state.get("experience_points", 0)
                new_xp = max(0, old_xp + xp)
                char_state["experience_points"] = new_xp

                current_level = char_state.get("level", 1)
                new_level = current_level

                for lvl, thresh in sorted(XP_THRESHOLDS.items()):
                    if new_xp >= thresh:
                        new_level = lvl
                        
                level_gained = False
                if new_level > current_level:
                    char_state["level"] = new_level
                    level_gained = new_level
                    leveled_up.append((char_name, new_level))
                    logger.info(f"[LEVEL UP] {char_name} -> Level {new_level}")

                from core.state_store import coordinator
                await coordinator.update_character_state_async(char_id, {
                    "experience_points": new_xp,
                    "level": new_level
                })
                
                # Record breakdown for the caller
                xp_breakdown[char_name] = {
                    "xp_gained": xp,
                    "new_level": level_gained
                }

            # 🔥 ROMANCE INTEGRATION: Bond party members after combat victory
            if ROMANCE_ENABLED and len(party_ids) >= 2:
                await self._process_combat_bonding(party_ids, difficulty, kill_count)

            return xp_breakdown

        except Exception as e:
            logger.error(f"XP sync failed: {e}", exc_info=True)
            return {}

    async def _process_combat_bonding(self, party_ids: list, difficulty: str, kill_count: int = 1):
        """Process romance/friendship bonding after combat"""
        try:
            # Bond each party member with each other
            for i, char1_id in enumerate(party_ids):
                for char2_id in party_ids[i+1:]:
                    romance_engine.on_combat_victory(char1_id, char2_id, difficulty, kill_count)

            logger.info(f"Combat bonding processed for {len(party_ids)} party members (difficulty: {difficulty}, kills: {kill_count})")
        except Exception as e:
            logger.error(f"Combat bonding failed: {e}", exc_info=True)
