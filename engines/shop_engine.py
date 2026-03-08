"""
Shop Engine for EmberHeart: Origins
Ported from Claudes-EmberHeart
"""
import json
import logging
import random
import difflib
from datetime import datetime
from core.config import ROOT_DIR, DB_DIR

logger = logging.getLogger("EH_Shop")

# Docs directory for static catalogs
DOCS_DIR = ROOT_DIR / "docs"


class DynamicShop:
    def __init__(self):
        self.forge_path = DOCS_DIR / "FORGE_CATALOG.json"
        self.spells_path = DOCS_DIR / "DND_REFERENCE_INDEX.json"
        self.settlement_path = DOCS_DIR / "SETTLEMENT_STATE.json"
        self.stock_path = DB_DIR / "SHOP_STOCK.json"
        self.last_rotation = None
        self._load_current_stock()

    def load_data(self):
        """Load static catalog data."""
        forge_items = []
        if self.forge_path.exists():
            try:
                data = json.loads(self.forge_path.read_text(encoding='utf-8'))
                forge_items = data.get("blueprints", [])
            except Exception as e:
                logger.error(f"Failed to load Forge Catalog: {e}")

        spells = []
        if self.spells_path.exists():
            try:
                data = json.loads(self.spells_path.read_text(encoding='utf-8'))
                spells = list(data.values())
            except Exception as e:
                logger.error(f"Failed to load Spell Index: {e}")

        return forge_items, spells

    def _load_current_stock(self):
        """Loads stock from disk to ensure shared state between cog and loop."""
        if self.stock_path.exists():
            try:
                data = json.loads(self.stock_path.read_text(encoding='utf-8'))
                self.current_stock = data.get("items", [])
                self.last_rotation = datetime.fromisoformat(data["last_rotation"]) if "last_rotation" in data else None
            except Exception as e:
                logger.error(f"Failed to load shop stock: {e}")
                self.current_stock = []
        else:
            self.current_stock = []

    async def _save_current_stock(self):
        """Persists stock to disk."""
        try:
            data = {
                "last_rotation": self.last_rotation.isoformat() if self.last_rotation else None,
                "items": self.current_stock
            }
            from core.state_store import coordinator
            # Shop stock is fully replaced on rotation, so overwrite is safe here
            await coordinator.update_global_json_async("SHOP_STOCK.json", lambda existing: data)
        except Exception as e:
            logger.error(f"Failed to save shop stock: {e}")

    async def generate_stock(self):
        """Generate a random 30-item stock (15 Forge, 15 Spells)."""
        forge_items, spells = self.load_data()
        stock = []

        if forge_items:
            valid_forge = [i for i in forge_items if isinstance(i, dict) and 'name' in i]
            count = min(len(valid_forge), 15)
            selected_forge = random.sample(valid_forge, count)
            for item in selected_forge:
                stock.append({
                    "name": item['name'],
                    "type": item.get('type', 'Item'),
                    "cost": f"{item.get('cost', {}).get('ore_ou', '?')} OU",
                    "rarity": "Forge-Pattern",
                    "desc": item.get('description', 'No data.')[:100]
                })

        if spells:
            import re
            valid_spells = [s for s in spells if isinstance(s, dict) and 'title' in s]
            count = min(len(valid_spells), 15)
            selected_spells = random.sample(valid_spells, count)
            for spell in selected_spells:
                clean_title = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', spell['title'])
                stock.append({
                    "name": f"Scroll of {clean_title}",
                    "type": "Scroll",
                    "cost": "500 OU",
                    "rarity": "Common",
                    "desc": re.sub(r'[\[\]]', '', spell.get('category', 'Spell'))
                })

        random.shuffle(stock)
        self.current_stock = stock[:30]
        self.last_rotation = datetime.now()
        await self._save_current_stock()
        logger.info(f"Shop Stock Generated: {len(self.current_stock)} items.")

    async def purchase_item(self, buyer_id: str, item_query: str) -> tuple[bool, str]:
        """Buy an item from the current stock."""
        if not self.current_stock:
            return False, "The shop shelves are bare..."

        stock_names = [i['name'] for i in self.current_stock]
        matches = difflib.get_close_matches(item_query, stock_names, n=1, cutoff=0.4)

        if not matches:
            return False, f"Item not found in current rotation. Did you mean: {', '.join(difflib.get_close_matches(item_query, stock_names, n=3, cutoff=0.3))}?"

        target_name = matches[0]
        target_item = next((i for i in self.current_stock if i['name'] == target_name), None)

        try:
            cost_val = int(target_item['cost'].split()[0])
        except Exception:
            return False, "Price is invalid or not listed."

        try:
            settlement = json.loads(self.settlement_path.read_text(encoding='utf-8'))
            stock = settlement['settlement']['stockpiles']
            current_ou = stock.get('gold', stock.get('ore_stock_ou', 0))

            if current_ou < cost_val:
                return False, f"Treasury insufficient. Need **{cost_val} OU**, but only **{current_ou} OU** available."

        except Exception as e:
            logger.error(f"Transaction Failed (Settlement Read): {e}")
            return False, "Bank error processing funds."

        try:
            from core.storage import load_character_state
            char_state = load_character_state(buyer_id)

            if not char_state:
                return False, f"Buyer profile for '{buyer_id}' not found in chronicles."

            char_state.setdefault('status', {}).setdefault('inventory', []).append(target_name)
            from core.state_store import coordinator
            await coordinator.update_character_state_async(buyer_id, char_state)

        except Exception as e:
            logger.error(f"Transaction Failed (Character State): {e}", exc_info=True)
            return False, "Inventory update failed."

        try:
            if 'gold' in stock:
                stock['gold'] -= cost_val
            else:
                stock['ore_stock_ou'] -= cost_val

            from core.state_store import coordinator
            purchase_cost = cost_val
            gold_key = 'gold' if 'gold' in stock else 'ore_stock_ou'
            def _deduct_gold(fresh):
                s = fresh.get('settlement', {}).get('stockpiles', {})
                s[gold_key] = s.get(gold_key, 0) - purchase_cost
                return fresh
            await coordinator.update_global_json_async("SETTLEMENT_STATE.json", _deduct_gold)

            gold_left = stock.get('gold', stock.get('ore_stock_ou', 0))
            return True, f"**Transaction Complete:** Purchased **{target_name}** for **{cost_val} OU**. (Treasury: {gold_left} OU)"

        except Exception as e:
            logger.error(f"Transaction Failed (Settlement Save): {e}", exc_info=True)
            return False, "Payment processing failed after item was added. Contact the Sovereign."
