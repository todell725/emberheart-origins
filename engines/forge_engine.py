import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from core.config import ROOT_DIR, DB_DIR

logger = logging.getLogger("EH_Forge")

class ForgeEngine:
    def __init__(self):
        self.catalog_path = ROOT_DIR / "docs" / "FORGE_CATALOG.json"
        self.active_path = DB_DIR / "FORGE_ACTIVE.json"
        self.settlement_path = DB_DIR / "SETTLEMENT_STATE.json"
        self.party_equip_path = DB_DIR / "PARTY_EQUIPMENT.json"
        self.party_state_path = DB_DIR / "PARTY_STATE.json"
        self.blueprints = self._load_catalog()
        self.active_projects: Dict[int, dict] = self._load_active()

    def _load_catalog(self) -> List[dict]:
        if not self.catalog_path.exists(): return []
        return json.loads(self.catalog_path.read_text(encoding='utf-8')).get('blueprints', [])

    def _load_active(self) -> dict:
        if not self.active_path.exists(): return {}
        try:
            data = json.loads(self.active_path.read_text(encoding='utf-8'))
            for cid, proj in data.items():
                proj['start_time'] = datetime.fromisoformat(proj['start_time'])
            return {int(k): v for k, v in data.items()}
        except Exception: return {}

    async def _save_active(self):
        data = {str(k): {**v, 'start_time': v['start_time'].isoformat()} for k, v in self.active_projects.items()}
        from core.state_store import coordinator
        await coordinator.update_global_json_async("FORGE_ACTIVE.json", lambda existing: data)

    def list_blueprints(self) -> List[dict]:
        return self.blueprints

    def get_blueprint(self, bid: str) -> Optional[dict]:
        return next((b for b in self.blueprints if b['id'].upper() == bid.upper()), None)

    async def start_crafting(self, channel_id: int, bid: str, force: bool = False) -> tuple:
        """Starts crafting. Returns (bool, message). Searching King, Party, and Treasury."""
        bp = self.get_blueprint(bid)
        if not bp: return False, f"Blueprint {bid} not found."
        
        if channel_id in self.active_projects:
            return False, "Forge is already busy in this channel."
        
        # 1. Load All Potential Inventories
        if not self.settlement_path.exists():
            return False, "Settlement state not found. Run `!owner setup` first."
        try:
            settlement_data = json.loads(self.settlement_path.read_text(encoding='utf-8'))
            equip_data = json.loads(self.party_equip_path.read_text(encoding='utf-8')) if self.party_equip_path.exists() else {"party_equipment": {}}
            party_data = json.loads(self.party_state_path.read_text(encoding='utf-8')) if self.party_state_path.exists() else {"party": []}
        except Exception as e:
            logger.error(f"Failed to load state files for crafting: {e}")
            return False, "Failed to read forge state files."
        
        if not force:
            # Check Kingdom Resources (Ore/Metal)
            stock = settlement_data['settlement']['stockpiles']
            needed_ou = bp['cost'].get('ore_ou', 0)
            needed_m2u = bp['cost'].get('metal_m2u', 0)
            
            if stock.get('ore_stock_ou', 0) < needed_ou or stock.get('metal_stock_m2u', 0) < needed_m2u:
                return False, "Insufficient Kingdom resources (Ore/Metal)."

            # 2. Extract All Available Material Stacks
            # Kaelrath is PC-01
            buyer_id = "PC-01"
            pe = equip_data.get("party_equipment", {})
            sources = [
                (pe.get(buyer_id, {}).get("inventory", []), buyer_id),
                (settlement_data["settlement"].get("inventory", []), "Kingdom Treasury")
            ]
            for char in party_data.get("party", []):
                if "status" not in char: char["status"] = {}
                if "inventory" not in char["status"]: char["status"]["inventory"] = []
                sources.append((char["status"]["inventory"], char["name"]))

            # 3. Check Material Availability
            all_materials = []
            for src_list, name in sources:
                all_materials.extend(src_list)
                
            for mat in bp.get('materials', []):
                count = all_materials.count(mat['item'])
                if count < mat['quantity']:
                    return False, f"Missing material: {mat['item']} (Need {mat['quantity']}, have {count} across all vaults)"

            # 4. Deduct Resources
            stock['ore_stock_ou'] -= needed_ou
            stock['metal_stock_m2u'] -= needed_m2u

            # 5. Deduct Materials (Greedy deduction from sources)
            for mat in bp.get('materials', []):
                remaining = mat['quantity']
                for src_list, name in sources:
                    while remaining > 0 and mat['item'] in src_list:
                        src_list.remove(mat['item'])
                        remaining -= 1
                    if remaining <= 0: break

            # 6. Save All Updated States Atomically
            from core.state_store import coordinator
            # Use callbacks that apply the specific deductions to fresh data
            deducted_ou = needed_ou
            deducted_m2u = needed_m2u
            mats_consumed = [(m['item'], m['quantity']) for m in bp.get('materials', [])]

            def _update_settlement(fresh):
                s = fresh.get('settlement', {}).get('stockpiles', {})
                s['ore_stock_ou'] = s.get('ore_stock_ou', 0) - deducted_ou
                s['metal_stock_m2u'] = s.get('metal_stock_m2u', 0) - deducted_m2u
                return fresh

            def _update_equip(fresh):
                pe_fresh = fresh.get('party_equipment', {})
                for mat_name, mat_qty in mats_consumed:
                    remaining = mat_qty
                    for cid in list(pe_fresh.keys()):
                        inv = pe_fresh.get(cid, {}).get('inventory', [])
                        while remaining > 0 and mat_name in inv:
                            inv.remove(mat_name)
                            remaining -= 1
                        if remaining <= 0:
                            break
                return fresh

            await coordinator.update_global_json_async(self.settlement_path.name, _update_settlement)
            await coordinator.update_global_json_async(self.party_equip_path.name, _update_equip)

        # 7. Start Project
        self.active_projects[channel_id] = {
            "bid": bp['id'],
            "name": bp['name'],
            "start_time": datetime.now(),
            "duration_hours": bp['craft_time_hours']
        }
        await self._save_active()
        return True, f"Hammer falls! Construction of **{bp['name']}** has begun using collective party resources."

    def get_active(self, channel_id: int):
        return self.active_projects.get(channel_id)

    async def claim_artifact(self, channel_id: int) -> tuple:
        """Claims finished artifact. Returns (bool, message)."""
        proj = self.get_active(channel_id)
        if not proj: return False, "No active project."
        
        elapsed = (datetime.now() - proj['start_time']).total_seconds() / 3600
        if elapsed < proj['duration_hours']:
            remaining = round(proj['duration_hours'] - elapsed, 1)
            return False, f"The forge is still glowing. Needs **{remaining} more hours**."

        # Award Item
        # Kaelrath is PC-01
        try:
            equip_data = json.loads(self.party_equip_path.read_text(encoding='utf-8')) if self.party_equip_path.exists() else {"party_equipment": {}}
        except Exception as e:
            logger.error(f"Failed to load equipment data: {e}")
            return False, "Failed to award artifact: equipment state unreadable."
        pe = equip_data.get("party_equipment", {})
        pc01 = pe.setdefault("PC-01", {})
        inventory = pc01.setdefault("inventory", [])
        inventory.append(proj['name'])
        equip_data["party_equipment"] = pe
        from core.state_store import coordinator
        item_to_add = proj['name']
        def _add_artifact(fresh):
            pe_fresh = fresh.get('party_equipment', {})
            pc01_fresh = pe_fresh.setdefault('PC-01', {})
            inv_fresh = pc01_fresh.setdefault('inventory', [])
            inv_fresh.append(item_to_add)
            fresh['party_equipment'] = pe_fresh
            return fresh
        await coordinator.update_global_json_async(self.party_equip_path.name, _add_artifact)

        # Cleanup
        del self.active_projects[channel_id]
        await self._save_active()
        
        return True, f"✨ **Artifact Forged!** {proj['name']} has been added to King Kaelrath's inventory."
