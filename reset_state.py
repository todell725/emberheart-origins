import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WipeState")

ROOT = Path(r"Z:\DnD\Claudes-EmberHeart")
DOCS_DIR = ROOT / "docs"
STATE_DIR = ROOT / "state"
CHARACTERS_DIR = ROOT / "characters" / "npcs"

# 1. Clear QUEST_COMPLETION
quest_file = DOCS_DIR / "QUEST_COMPLETION.json"
if quest_file.exists():
    try:
        with open(quest_file, 'w', encoding='utf-8') as f:
            json.dump([""], f, indent=4) # it was a flat array in EmberheartReborn
        logger.info("Cleared QUEST_COMPLETION.json")
    except Exception as e:
        logger.error(f"Error clearing quests: {e}")

# 2. Clear PARTY_EQUIPMENT inventory
equip_file = DOCS_DIR / "PARTY_EQUIPMENT.json"
if equip_file.exists():
    try:
        data = json.loads(equip_file.read_text(encoding='utf-8'))
        for char_name, equip_data in data.get("party_equipment", {}).items():
            if "inventory" in equip_data:
                equip_data["inventory"] = []
        with open(equip_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info("Cleared PARTY_EQUIPMENT.json inventories")
    except Exception as e:
        logger.error(f"Error clearing party equipment: {e}")

# 3. Clear PARTY_RELATIONSHIPS
rel_file = DOCS_DIR / "PARTY_RELATIONSHIPS.json"
if rel_file.exists():
    try:
        data = {"version": "1.0", "schema": "PARTY_RELATIONSHIPS.json", "relationships": []}
        with open(rel_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info("Cleared PARTY_RELATIONSHIPS.json")
    except Exception as e:
        logger.error(f"Error clearing relationships: {e}")

# 4. Clear Chronicle (RAG memory)
chronicle_file = STATE_DIR / "chronicle.json"
if chronicle_file.exists():
    try:
        data = {"version": "1.0", "memories": []}
        with open(chronicle_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info("Cleared chronicle.json")
    except Exception as e:
        logger.error(f"Error clearing chronicle: {e}")

# 5. Reset Character States (PCs and NPCs)
for npc_dir in CHARACTERS_DIR.iterdir():
    if not npc_dir.is_dir():
        continue
    state_file = npc_dir / "state.json"
    if not state_file.exists():
        continue

    try:
        data = json.loads(state_file.read_text(encoding='utf-8'))
        
        # Is PC? Look for level/experience
        if "level" in data and "experience_points" in data:
            data["level"] = 1
            data["experience_points"] = 0
            if "status" in data and isinstance(data["status"], dict):
                if "inventory" in data["status"]:
                    data["status"]["inventory"] = []
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Reset PC state: {npc_dir.name}")
            
        # Is NPC? Look for influence/loyalty
        elif "loyalty" in data and "influence" in data:
            data["influence"] = 0
            # Keep loyalty as it might have a default, or set to 50
            data["loyalty"] = 50 
            if "fear" in data: data["fear"] = 0
            if "corruption_exposure" in data: data["corruption_exposure"] = 0
            if "cult_allegiance" in data: data["cult_allegiance"] = 0
            if "latent_symptom_flag" in data: data["latent_symptom_flag"] = False
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Reset NPC state: {npc_dir.name}")
            
    except Exception as e:
        logger.error(f"Error resetting {npc_dir.name}: {e}")

logger.info("Wipe complete.")
