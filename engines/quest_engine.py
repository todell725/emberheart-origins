"""
Quest Engine for EmberHeart: Origins
Ported from Claudes-EmberHeart
"""
import logging
import json
from typing import Dict, List, Optional
from core.config import ROOT_DIR, DB_DIR
from engines.combat_engine import CombatTracker

logger = logging.getLogger("EH_QuestEngine")

DOCS_DIR = ROOT_DIR / "docs"

# Import romance engine for quest bonding
try:
    from engines.romance_engine import romance_engine
    ROMANCE_ENABLED = True
except ImportError:
    ROMANCE_ENABLED = False
    logger.warning("Romance engine not available - quest bonding disabled")


class QuestEngine:
    def __init__(self):
        self.db_path = DOCS_DIR / "SIDE_QUESTS_DB.json"
        self.completion_path = DOCS_DIR / "QUEST_COMPLETION.json"
        self.loot_path = DOCS_DIR / "PARTY_EQUIPMENT.json"
        self.deeds_path = DB_DIR / "QUEST_DEEDS.md"
        self._db = self._load_db()
        self.completed = self._load_completed()
        self.active_quests = self._load_active()  # dict: {qid: {"turn": int, "path": str}}
        self.combat = CombatTracker()

    def _load_db(self) -> list:
        if not self.db_path.exists():
            logger.warning(f"Quest DB not found: {self.db_path}")
            return []
        try:
            data = json.loads(self.db_path.read_text(encoding='utf-8'))
            logger.info(f"Loaded {len(data)} quests from {self.db_path.name}")
            return data
        except Exception as e:
            logger.error(f"Failed to load quests: {e}")
            return []

    def _load_completed(self) -> set:
        if not self.completion_path.exists():
            return set()
        try:
            data = json.loads(self.completion_path.read_text(encoding='utf-8'))
            return set(data.get("completed", []))
        except Exception:
            return set()

    def _load_active(self) -> dict:
        if not self.completion_path.exists():
            return {}
        try:
            data = json.loads(self.completion_path.read_text(encoding='utf-8'))
            raw = data.get("active", [])
            # Backward compat: old format was a list of IDs
            if isinstance(raw, list):
                return {qid: {"turn": 1, "path": ""} for qid in raw}
            if isinstance(raw, dict):
                return raw
            return {}
        except Exception:
            return {}

    def start_quest(self, qid: str) -> tuple:
        """Accept a quest into the active log. Returns (success, message)."""
        qid = qid.upper()
        quest = self.get_quest(qid)
        if not quest:
            return False, f"Quest `{qid}` not found."
        if qid in self.completed:
            return False, f"Quest `{qid}` is already completed."
        if qid in self.active_quests:
            return False, f"Quest `{qid}` is already active."

        ok, missing = self.check_prerequisites(qid)
        if not ok:
            return False, f"Prerequisites not met: {', '.join(missing)}"

        self.active_quests[qid] = {"turn": 1, "path": ""}
        self._save_quest_state()
        return True, quest.get('title', qid)

    def get_active_quests(self) -> list:
        """Return list of active quest dicts with progress info."""
        result = []
        for q in self._db:
            qid = q.get('id', '').upper()
            if qid in self.active_quests:
                q_copy = dict(q)
                q_copy['_progress'] = self.active_quests[qid]
                result.append(q_copy)
        return result

    def _save_quest_state(self):
        """Save both completed and active quest progress."""
        try:
            data = {
                "completed": list(self.completed),
                "active": self.active_quests  # dict with turn progress
            }
            self.completion_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to save quest state: {e}")

    def get_quest(self, qid: str) -> Optional[dict]:
        qid = qid.upper()
        for q in self._db:
            if q.get('id', '').upper() == qid:
                return q
        return None

    def check_prerequisites(self, qid: str) -> tuple:
        """Returns (ok: bool, missing: list). missing is [] when ok."""
        quest = self.get_quest(qid)
        if not quest:
            return False, [f"Quest {qid} not found"]

        prereqs = quest.get("prerequisites", [])
        
        # Handle string "None" or other string IDs
        if isinstance(prereqs, str):
            if prereqs.lower() == "none" or not prereqs.strip():
                prereqs = []
            else:
                # Treat as a single quest ID requirement
                prereqs = [prereqs]
        
        # Handle dict format (as seen in some DB entries)
        if isinstance(prereqs, dict):
            prereqs = prereqs.get("quests_completed", [])
            
        # Safety fallback
        if not isinstance(prereqs, list):
            prereqs = []

        missing = [p for p in prereqs if p.upper() not in self.completed]
        return len(missing) == 0, missing

    def get_current_turn(self, qid: str) -> Optional[dict]:
        """Get the current turn data for an active quest."""
        qid = qid.upper()
        progress = self.active_quests.get(qid)
        if not progress:
            return None

        quest = self.get_quest(qid)
        if not quest:
            return None

        turns = quest.get("turns", [])
        current_turn_num = progress.get("turn", 1)

        for t in turns:
            if t.get("turn") == current_turn_num:
                return t
        return None

    def get_total_turns(self, qid: str) -> int:
        """Get the total number of turns in a quest."""
        quest = self.get_quest(qid)
        if not quest:
            return 0
        return len(quest.get("turns", []))

    def submit_choice(self, qid: str, choice: str) -> tuple:
        """Submit a choice (a or b) for the current turn.
        Returns (success, response_dict) where response_dict contains:
          - consequence: the result of the choice
          - convergence: the convergence text
          - next_turn: the next turn dict (or None if quest is done)
          - quest_complete: bool
          - path: the full path string so far
        """
        qid = qid.upper()
        choice = choice.lower().strip()
        if choice not in ("a", "b"):
            return False, {"error": "Choice must be `a` or `b`."}

        progress = self.active_quests.get(qid)
        if not progress:
            return False, {"error": f"Quest `{qid}` is not active."}

        quest = self.get_quest(qid)
        if not quest:
            return False, {"error": f"Quest `{qid}` not found."}

        turns = quest.get("turns", [])
        current_turn_num = progress.get("turn", 1)

        # Find current turn data
        current_turn = None
        for t in turns:
            if t.get("turn") == current_turn_num:
                current_turn = t
                break

        if not current_turn:
            return False, {"error": f"Turn {current_turn_num} not found for quest `{qid}`."}

        # Get consequence
        consequence = current_turn.get(f"consequence_{choice}", "No consequence defined.")
        convergence = current_turn.get("convergence", "")

        # Update path
        progress["path"] = progress.get("path", "") + choice

        # Advance turn
        next_turn_num = current_turn_num + 1
        next_turn = None
        for t in turns:
            if t.get("turn") == next_turn_num:
                next_turn = t
                break

        quest_complete = next_turn is None
        if quest_complete:
            # Auto-complete: remove from active, mark completed
            progress["turn"] = current_turn_num  # stay on last turn
        else:
            progress["turn"] = next_turn_num

        self._save_quest_state()

        return True, {
            "consequence": consequence,
            "convergence": convergence,
            "next_turn": next_turn,
            "quest_complete": quest_complete,
            "path": progress["path"],
            "current_turn": current_turn_num,
            "total_turns": len(turns),
        }

    def resolve_outcome(self, qid: str, path: list) -> Optional[str]:
        """Map the A/B choice path to a branching_outcome key."""
        quest = self.get_quest(qid)
        if not quest:
            return None

        outcomes = quest.get("branching_outcomes", {})
        if not outcomes or not path:
            return None

        # If outcomes is a list, just return the first key or None
        if isinstance(outcomes, list):
            return "default"

        path_key = "".join(path).upper()
        if path_key in outcomes:
            return path_key

        for key in outcomes:
            if isinstance(key, str) and key.upper() == path_key:
                return key

        # No exact match — return the first outcome key as fallback
        first_key = next(iter(outcomes), None)
        return first_key

    def apply_failure(self, qid: str) -> Optional[str]:
        """Apply risk_matrix failure penalties. Returns critical_failure text."""
        quest = self.get_quest(qid)
        if not quest:
            return None

        risk = quest.get("risk_matrix", {})
        failure = risk.get("critical_failure")
        if failure:
            logger.warning(f"Quest {qid} critical failure: {failure}")
        return failure

    async def mark_completed(self, qid: str, path: list = None) -> list:
        """Mark quest finished. Awards XP, loot, logs outcome + permanent effects."""
        quest = self.get_quest(qid)
        if not quest:
            return []

        qid = qid.upper()
        self.completed.add(qid)

        try:
            from core.state_store import coordinator
            await coordinator.update_global_json_async(
                "QUEST_COMPLETION.json",
                lambda data: {"completed": list(self.completed)}
            )
        except Exception as e:
            logger.error(f"Failed to save quest completion: {e}")

        # Determine quest difficulty for romance bonding
        difficulty = quest.get("difficulty", "normal").lower()
        if difficulty not in ["normal", "hard", "deadly"]:
            difficulty = "normal"

        xp = quest.get("xp_reward", 0)
        leveled = []
        if xp > 0:
            # Pass difficulty to combat system for romance bonding
            leveled = await self.combat.add_party_xp(xp, difficulty=difficulty)

        loot = quest.get("loot_table", quest.get("loot", []))
        if loot:
            await self.sync_loot(loot)

        # 🔥 ROMANCE INTEGRATION: Bond party members after shared quest
        if ROMANCE_ENABLED:
            await self._process_quest_bonding(quest, difficulty)

        outcome_key = self.resolve_outcome(qid, path) if path else "default"
        self.log_deed(qid, quest.get("title", qid), f"Completed via path: {outcome_key}")

        return leveled

    async def _process_quest_bonding(self, quest: dict, difficulty: str):
        """Process relationship bonding after completing a quest together"""
        try:
            from core.storage import load_all_character_states

            # Get all party members
            all_states = load_all_character_states()
            party = [s for s in all_states if s.get("id", "").startswith("PC-")]
            party_ids = [c["id"] for c in party]

            if len(party_ids) < 2:
                return

            # Quality time together during quest
            for i, char1_id in enumerate(party_ids):
                for char2_id in party_ids[i+1:]:
                    romance_engine.on_quality_time(char1_id, char2_id, activity="adventure")

            # Check for trauma/rescue tags in quest description
            quest_desc = quest.get("description", "").lower()
            quest_title = quest.get("title", "").lower()
            combined_text = quest_desc + " " + quest_title

            # Shared trauma keywords
            trauma_keywords = ["collapse", "trapped", "wounded", "dying", "disaster", "tragedy", "loss"]
            if any(keyword in combined_text for keyword in trauma_keywords):
                for i, char1_id in enumerate(party_ids):
                    for char2_id in party_ids[i+1:]:
                        romance_engine.on_shared_trauma(char1_id, char2_id)
                        logger.info(f"Quest trauma bonding: {char1_id} & {char2_id}")

            logger.info(f"Quest bonding processed for {len(party_ids)} party members (difficulty: {difficulty})")

        except Exception as e:
            logger.error(f"Quest bonding failed: {e}", exc_info=True)

    async def sync_loot(self, loot_list: list) -> dict:
        """Distribute loot items to party members and return a breakdown dictionary."""
        try:
            from core.storage import load_all_character_states
            from core.state_store import coordinator
            import random
            from collections import defaultdict, Counter
            
            all_states = load_all_character_states()
            party = [s for s in all_states if s.get("id", "").startswith("PC-")]

            if not party:
                logger.warning("No party members found for loot sync")
                return {}

            # Batch loot by character ID
            batched_loot = defaultdict(list)
            for item in loot_list:
                target = random.choice(party)
                char_id = target.get("id")
                
                item_name = item if isinstance(item, str) else item.get("name", str(item))
                batched_loot[char_id].append(item_name)

            # Dictionary to return to the caller (using Character Names)
            loot_breakdown = {}

            # Do exactly ONE database write per character
            for char_state in party:
                char_id = char_state.get("id")
                if char_id not in batched_loot:
                    continue
                    
                loot_to_add = batched_loot[char_id]
                inv = char_state.get("status", {}).get("inventory", [])
                
                if isinstance(inv, list):
                    inv.extend(loot_to_add)
                
                char_state.setdefault("status", {})["inventory"] = inv
                await coordinator.update_character_state_async(char_id, char_state)
                
                char_name = char_state.get("name", char_id)
                loot_breakdown[char_name] = loot_to_add
                
                # Log a summary to prevent thousands of terminal prints
                summary = Counter(loot_to_add)
                summary_str = ", ".join([f"{item} (x{count})" for item, count in summary.most_common(5)])
                if len(summary) > 5:
                    summary_str += f" + {len(summary)-5} more item types"
                    
                logger.info(f"Batched Loot -> {char_name} received {len(loot_to_add)} items: {summary_str}")

            return loot_breakdown

        except Exception as e:
            logger.error(f"Loot sync failed: {e}", exc_info=True)
            return {}

    def log_deed(self, qid: str, title: str, outcome: str):
        """Append quest deed to the log."""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n## [{qid}] {title}\n- **Completed**: {timestamp}\n- **Outcome**: {outcome}\n"

            with open(self.deeds_path, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Failed to log deed: {e}")
