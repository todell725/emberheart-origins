import json
import logging
import random

from core.config import DB_DIR

logger = logging.getLogger("EH_Tick")

# Import romance engine for daily passive updates
try:
    from engines.romance_engine import romance_engine
    ROMANCE_ENABLED = True
except ImportError:
    ROMANCE_ENABLED = False
    logger.warning("Romance engine not available - daily romance updates disabled")


class TickEngine:
    def __init__(self):
        self.settlement_path = DB_DIR / "SETTLEMENT_STATE.json"
        self.relationship_path = DB_DIR / "PARTY_RELATIONSHIPS.json"
        self.deeds_path = DB_DIR / "QUEST_DEEDS.md"

    async def run_tick(self) -> str:
        """Executes the weekly logic. Returns a dictionary of changes for the Proclamation."""
        try:
            from core.storage import (
                load_all_character_states,
                load_character_state,
                save_character_state,
                save_json,
            )

            settlement = json.loads(self.settlement_path.read_text(encoding="utf-8"))
            all_characters = load_all_character_states()

            summary = []

            # --- 1. Resource Balance ---
            stock = settlement["settlement"]["stockpiles"]
            calendar = settlement["settlement"]["calendar"]
            core = settlement["settlement"]["core_status"]

            food_status = "✨ Abundant (Infinite)" if stock.get("food_stock_fu") == "INFINITE" else f"📦 {stock.get('food_stock_fu', 0)} FU"
            summary.append(f"🍞 **Food Supply**: {food_status}")

            # --- 2. Cult Spread ---
            corruption_index = core.get("corruption_index", 0)
            exposed = []
            for char_data in all_characters:
                char_id = char_data.get("id")
                if not char_id:
                    continue

                # NPCs only for cult spread usually, but we check allegiance
                if char_data.get("cult_allegiance", 0) > 0:
                    continue

                chance = corruption_index * 2
                if random.randint(1, 100) <= chance:
                    bump = random.randint(10, 20)
                    try:
                        live_state = load_character_state(char_id) or {}
                        current = live_state.get("corruption_exposure", char_data.get("corruption_exposure", 0))
                        live_state["corruption_exposure"] = current + bump
                        from core.state_store import coordinator
                        await coordinator.update_character_state_async(char_id, live_state)
                        exposed.append(char_data.get("name", "Unknown citizen"))
                    except Exception as e:
                        logger.error(f"Failed to save state for {char_id}: {e}")

            if exposed:
                summary.append(f"👁️ **Cult Activity**: Dark rumors surround {len(exposed)} individuals.")
            else:
                summary.append("✅ **Security**: The Sovereignty remains pure.")

            # --- 3. Relationship Drift ---
            if self.relationship_path.exists():
                try:
                    rels = json.loads(self.relationship_path.read_text(encoding="utf-8"))
                    for rel in rels.get("relationships", []):
                        if rel.get("tension", 0) > 10:
                            rel["tension"] -= 1
                    from core.state_store import coordinator
                    def _drift_tension(fresh):
                        for r in fresh.get('relationships', []):
                            if r.get('tension', 0) > 10:
                                r['tension'] -= 1
                        return fresh
                    await coordinator.update_global_json_async("PARTY_RELATIONSHIPS.json", _drift_tension)
                except Exception as e:
                    logger.warning(f"Could not drift relationships: {e}")

            # --- 4. Calendar & Income ---
            income = core.get("weekly_income_gold", 0)
            if income > 0:
                if "gold" in stock:
                    stock["gold"] += income
                elif "ore_stock_ou" in stock:
                    stock["ore_stock_ou"] += income
                else:
                    stock["gold"] = income

            summary.append(f"💰 **Treasury**: +{income:,} Gold deposited to the Royal Vault.")

            # Advance Week
            if "week_index" in calendar:
                calendar["week_index"] += 1
                summary.append(f"📆 **Calendar**: It is now Week {calendar['week_index']} of the {calendar.get('season', 'Unknown Season')}.")

            # Save Settlement
            from core.state_store import coordinator
            tick_income = income
            def _apply_tick(fresh):
                s = fresh.get('settlement', {})
                st = s.get('stockpiles', {})
                cal = s.get('calendar', {})
                if tick_income > 0:
                    if 'gold' in st:
                        st['gold'] = st.get('gold', 0) + tick_income
                    elif 'ore_stock_ou' in st:
                        st['ore_stock_ou'] = st.get('ore_stock_ou', 0) + tick_income
                    else:
                        st['gold'] = tick_income
                if 'week_index' in cal:
                    cal['week_index'] = cal.get('week_index', 0) + 1
                return fresh
            await coordinator.update_global_json_async("SETTLEMENT_STATE.json", _apply_tick)

            # 🔥 ROMANCE INTEGRATION: Process daily passive relationship updates
            if ROMANCE_ENABLED:
                try:
                    romance_engine.process_daily_passive_updates()
                    summary.append("❤️ **Relationships**: Bonds naturally evolve across the settlement.")
                    logger.info("Daily romance passive updates complete")
                except Exception as e:
                    logger.error(f"Romance passive updates failed: {e}", exc_info=True)

            return "\n".join([f"> {s}" for s in summary])
        except Exception as e:
            logger.error(f"Tick Failed: {e}", exc_info=True)
            return f"❌ **Tick Failure**: {e}"
