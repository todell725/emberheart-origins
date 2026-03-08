"""
Idle Task Engine - Base Class for Passive Skill Systems
Provides shared functionality for Slayer, Hunting, Mining, Fishing, etc.
"""
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from core.config import ROOT_DIR, DB_DIR

logger = logging.getLogger("EH_IdleEngine")

DOCS_DIR = ROOT_DIR / "docs"


class IdleTaskEngine:
    """
    Base class for all idle/passive skill systems.

    Handles:
    - Task database loading
    - Active task tracking and persistence
    - Time manipulation (start, stop, skip)
    - Loot rolling
    - Party breakdown message formatting
    """

    def __init__(self, db_filename: str, active_filename: str, skill_name: str = "Task", llm_client=None):
        """
        Initialize the idle task engine.

        Args:
            db_filename: Name of the JSON file in docs/ (e.g., "IDLE_SLAYER_DB.json")
            active_filename: Name of the JSON file in state/ (e.g., "SLAYER_ACTIVE.json")
            skill_name: Display name for logging (e.g., "Slayer", "Hunting")
            llm_client: Optional LLM client for narration
        """
        self.skill_name = skill_name
        self.db_path = DOCS_DIR / db_filename
        self.active_path = DB_DIR / active_filename
        self._db = self._load_db()
        self.active_tasks: Dict[int, dict] = self._load_active()
        self.llm = llm_client

    def _load_db(self) -> List[dict]:
        """Load the task database from JSON"""
        if not self.db_path.exists():
            logger.warning(f"{self.skill_name} DB not found: {self.db_path}")
            return []
        try:
            raw = self.db_path.read_text(encoding='utf-8')
            data = json.loads(raw)
            logger.info(f"Loaded {len(data)} {self.skill_name.lower()} tasks from {self.db_path.name}")
            return data
        except Exception as e:
            logger.error(f"Failed to load {self.skill_name.lower()} tasks: {e}")
            return []

    def _load_active(self) -> Dict[int, dict]:
        """Load active tasks from JSON, converting ISO timestamps to datetime objects"""
        if not self.active_path.exists():
            return {}
        try:
            data = json.loads(self.active_path.read_text(encoding='utf-8'))
            processed = {}
            for cid, task in data.items():
                task['start_time'] = datetime.fromisoformat(task['start_time'])
                processed[int(cid)] = task
            return processed
        except Exception as e:
            logger.error(f"Failed to load active {self.skill_name.lower()} tasks: {e}")
            return {}

    async def _save_active(self):
        """Save active tasks to JSON, converting datetime objects to ISO timestamps"""
        try:
            formatted = {}
            for cid, task in self.active_tasks.items():
                task_copy = dict(task)
                task_copy['start_time'] = task_copy['start_time'].isoformat()
                formatted[str(cid)] = task_copy
            from core.state_store import coordinator
            # Active task state is fully owned by this engine instance, overwrite is safe
            await coordinator.update_global_json_async(self.active_path.name, lambda existing: formatted)
        except Exception as e:
            logger.error(f"Failed to save active {self.skill_name.lower()} tasks: {e}")

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a task by its ID (case-insensitive)"""
        for task in self._db:
            if task['task_id'].upper() == task_id.upper():
                return task
        return None

    def list_tasks(self, min_level: int = 0) -> List[dict]:
        """List all tasks, optionally filtered by minimum level requirement"""
        if min_level > 0:
            return [t for t in self._db if t['requirements']['min_level'] <= min_level]
        return self._db

    async def start_task(self, channel_id: int, task_id: str, solo: bool = False) -> Optional[dict]:
        """
        Start a new task in a channel.

        Args:
            channel_id: Discord channel ID
            task_id: Task identifier (e.g., "SLAYER_001")
            solo: Whether this is a solo task (4x slower)

        Returns:
            The task dict if found, None otherwise
        """
        task = self.get_task(task_id)
        if not task:
            return None
        self.active_tasks[channel_id] = {
            "task_id": task_id.upper(),
            "start_time": datetime.now(),
            "solo": solo
        }
        await self._save_active()
        return task

    def get_active(self, channel_id: int) -> Optional[dict]:
        """Get the active task for a channel"""
        return self.active_tasks.get(channel_id)

    async def stop_task(self, channel_id: int):
        """Stop/cancel the active task in a channel"""
        if channel_id in self.active_tasks:
            del self.active_tasks[channel_id]
            await self._save_active()

    async def skip_time(self, channel_id: int, hours: float) -> bool:
        """
        Skip time on an active task by moving its start_time backwards.

        Args:
            channel_id: Discord channel ID
            hours: Number of hours to skip

        Returns:
            True if a task was found and skipped, False otherwise
        """
        if channel_id in self.active_tasks:
            self.active_tasks[channel_id]['start_time'] -= timedelta(hours=hours)
            await self._save_active()
            return True
        return False

    async def consume_party_ingredients(self, required_items: Dict[str, int], max_possible_crafts: int) -> int:
        """
        Attempts to consume required items from the collective party inventory.
        
        Args:
            required_items: Dictionary of {item_name: quantity_needed_per_craft}
            max_possible_crafts: Maximum times the recipe can be crafted based on elapsed time.
            
        Returns:
            The actual number of times the recipe was crafted based on available ingredients.
            If 0, not enough ingredients for even 1 craft.
        """
        if not required_items:
            return max_possible_crafts
            
        try:
            from core.storage import load_all_character_states
            from core.state_store import coordinator
            
            all_states = load_all_character_states()
            party = [s for s in all_states if s.get("id", "").startswith("PC-")]
            
            # 1. Count total available resources
            # Use case-insensitive matching to avoid issues
            available_counts = {}
            item_name_mapping = {}  # Maps lowercase -> actual name
            for state in party:
                inv = state.get("status", {}).get("inventory", [])
                if isinstance(inv, list):
                    for item in inv:
                        item_name = item if isinstance(item, str) else item.get("name", str(item))
                        # Store both the actual name and lowercase key
                        item_lower = item_name.lower()
                        if item_lower not in item_name_mapping:
                            item_name_mapping[item_lower] = item_name
                        available_counts[item_lower] = available_counts.get(item_lower, 0) + 1

            # Debug logging
            logger.info(f"Required items: {required_items}")
            logger.info(f"Available counts (case-insensitive): {available_counts}")
            logger.info(f"Item name mapping: {item_name_mapping}")

            # 2. Determine max crafts possible
            possible_crafts = max_possible_crafts
            for item, req_qty in required_items.items():
                if req_qty <= 0: continue
                # Case-insensitive lookup
                avail = available_counts.get(item.lower(), 0)
                logger.info(f"Checking {item}: need {req_qty} per craft, have {avail}, max crafts so far: {possible_crafts}")
                possible_crafts = min(possible_crafts, avail // req_qty)

            logger.info(f"Final possible_crafts: {possible_crafts}")

            if possible_crafts <= 0:
                logger.warning(f"Not enough materials! Required: {required_items}, Available: {available_counts}")
                return 0
                
            # 3. Deduct the items (greedy deduction across all party members)
            # Create case-insensitive removal counter
            items_to_remove = {}
            for item, req_qty in required_items.items():
                items_to_remove[item.lower()] = req_qty * possible_crafts

            for state in party:
                inv = state.get("status", {}).get("inventory", [])
                if not isinstance(inv, list) or not inv:
                    continue

                modified = False
                new_inv = []
                for item in inv:
                    item_name = item if isinstance(item, str) else item.get("name", str(item))
                    item_lower = item_name.lower()
                    # Check case-insensitive
                    if items_to_remove.get(item_lower, 0) > 0:
                        items_to_remove[item_lower] -= 1
                        modified = True
                    else:
                        new_inv.append(item)

                if modified:
                    state.setdefault("status", {})["inventory"] = new_inv
                    await coordinator.update_character_state_async(state["id"], state)
                    
            return int(possible_crafts)
            
        except Exception as e:
            logger.error(f"Failed to consume party ingredients: {e}", exc_info=True)
            return 0

    def roll_loot(self, drop_table: list, max_drops: int, kills: int = 1) -> List[str]:
        """
        Roll for loot drops based on a drop table. Supports both legacy chance-based 
        tables and modern manufacturing weight-based tables.

        Args:
            drop_table: List of dicts with 'chance' or 'weight' keys
            max_drops: Maximum number of items per kill
            kills: Number of kills to roll for

        Returns:
            List of item names that dropped
        """
        all_drops = []
        if not drop_table:
            return all_drops
            
        # Determine what kind of table this is
        is_weighted = any("weight" in d for d in drop_table)

        if is_weighted:
            # Manufacturing table logic (Guaranteed output, weighted rarity)
            items = []
            weights = []
            for d in drop_table:
                items.append(d)
                weights.append(d.get("weight", 10))
                
            for _ in range(kills):
                # Choose max_drops number of items based on relative weights
                selected_drops = random.choices(items, weights=weights, k=max_drops)
                for drop in selected_drops:
                    min_q = drop.get("min_qty", 1)
                    max_q = drop.get("max_qty", 1)
                    qty = random.randint(min_q, max_q)
                    for _ in range(qty):
                        all_drops.append(drop["item"])
        else:
            # Legacy gathering table logic (Probability based)
            for _ in range(kills):
                drops_this_kill = 0
                available = list(drop_table)
                random.shuffle(available)
                for d in available:
                    if drops_this_kill >= max_drops:
                        break
                    if random.random() <= d.get('chance', 0):
                        all_drops.append(d['item'])
                        drops_this_kill += 1
                        
        return all_drops

    def get_rare_drops(self, task: dict, rolled_loot: List[str]) -> List[str]:
        """
        Identify legendary/rare drops from a loot roll.
        
        Args:
            task: The current idle task dictionary
            rolled_loot: The list of items exactly as returned by roll_loot
            
        Returns:
            List of rare items that should trigger a global announcement.
        """
        rare_items = set()
        
        # Determine if the task itself is legendary/god-tier (for crafting/smithing/High Tier)
        is_legendary_task = task.get('difficulty', '') in ['Legendary', 'God-Tier', 'Extreme']

        for drop in task.get("drop_table", []):
            item_name = drop.get("item")
            is_rare = False
            
            # Check chance-based tables (slayer, hunting, mining, fishing, woodcutting)
            if "chance" in drop:
                # 5% or less, or explicitly marked Rare
                if drop["chance"] <= 0.05 or drop.get("type", "") == "Rare":
                    is_rare = True
                    
            # Check weight-based tables (crafting, smithing)
            elif "weight" in drop:
                if is_legendary_task:
                    is_rare = True
                    
            if is_rare:
                rare_items.add(item_name)
                
        # Filter the actual dropped loot to only the rare pulls
        found_rares = []
        for loot in rolled_loot:
            # Strip off the stack size (e.g., "Goblin Ear (x2)" -> "Goblin Ear")
            base_name = loot.split(" (x")[0]
            if base_name in rare_items:
                found_rares.append(loot)
                
        return found_rares

    def get_party_level(self) -> int:
        """Get the highest level among party members"""
        try:
            from core.storage import load_all_character_states
            all_states = load_all_character_states()
            levels = [s.get('level', 1) for s in all_states if s.get('id', '').startswith('PC-')]
            return max(levels) if levels else 1
        except Exception as e:
            logger.error(f"Failed to get party level: {e}")
            return 1

    def get_character_class(self, character_id: str = "PC-01") -> str:
        """
        Get the character class for a specific character.

        Args:
            character_id: The character ID (default: PC-01 for main character)

        Returns:
            Character class string or default based on skill type
        """
        try:
            from core.storage import load_all_character_states
            all_states = load_all_character_states()

            # Find the specific character
            for state in all_states:
                if state.get('id') == character_id:
                    return state.get('class', self._get_default_class())

            # Fallback to first PC
            for state in all_states:
                if state.get('id', '').startswith('PC-'):
                    return state.get('class', self._get_default_class())

            return self._get_default_class()
        except Exception as e:
            logger.error(f"Failed to get character class: {e}")
            return self._get_default_class()

    def _get_default_class(self) -> str:
        """Get a skill-appropriate default class name"""
        defaults = {
            "Slayer": "Adventurer",
            "Hunting": "Hunter",
            "Mining": "Miner",
            "Fishing": "Fisher",
            "Woodcutting": "Lumberjack",
            "Cooking": "Chef",
            "Crafting": "Artisan",
            "Smithing": "Blacksmith"
        }
        return defaults.get(self.skill_name, "Adventurer")

    def build_party_breakdown_msg(
        self,
        xp_breakdown: Dict[str, int],
        loot_breakdown: Dict[str, List[str]],
        total_xp: int,
        all_loot: List[str]
    ) -> List[str]:
        """
        Build a formatted message showing per-character XP and loot breakdown.

        Args:
            xp_breakdown: Dict mapping character names to XP earned
            loot_breakdown: Dict mapping character names to their loot lists
            total_xp: Total XP earned across all characters
            all_loot: Complete list of all loot items (with duplicates)

        Returns:
            List of formatted message lines
        """
        from collections import Counter

        lines = []

        # Per-character breakdown
        all_chars = set(xp_breakdown.keys()) | set(loot_breakdown.keys())
        if not all_chars:
            lines.append("No rewards distributed.")
        else:
            lines.append("")
            lines.append("**— Party Breakdown —**")
            for char_name in sorted(list(all_chars)):
                # Formatting XP & Levels
                rewards = []
                xp_data = xp_breakdown.get(char_name, {})
                if isinstance(xp_data, dict) and xp_data.get("xp_gained"):
                    xp_str = f"+{xp_data['xp_gained']:,} XP"
                    if xp_data.get("new_level"):
                        xp_str += f" (**Level Up! -> {xp_data['new_level']}**)"
                    rewards.append(xp_str)
                elif isinstance(xp_data, int) and xp_data > 0:
                    rewards.append(f"+{xp_data:,} XP")

                # Formatting Loot
                char_loot = loot_breakdown.get(char_name, [])
                if char_loot:
                    loot_counts = Counter(char_loot)
                    loot_str = ", ".join([f"`{item}` (x{count})" if count > 1 else f"`{item}`" for item, count in loot_counts.items()])
                    rewards.append(f"Found: {loot_str}")

                if rewards:
                    lines.append(f"**{char_name}**: {' | '.join(rewards)}")

        # Total summary
        lines.append("")
        lines.append("**Total Summary:**")
        lines.append(f"  • Total XP: +{total_xp:,}")

        if all_loot:
            total_counts = Counter(all_loot)
            total_display = ', '.join([f"`{item}` (x{count})" if count > 1 else f"`{item}`"
                                      for item, count in total_counts.items()])
            lines.append(f"  • Total Loot: {total_display}")
        else:
            lines.append(f"  • Total Loot: None")

        return lines
