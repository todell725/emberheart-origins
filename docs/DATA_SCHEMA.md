# EmberHeart: Origins — Data Schemas

This document outlines the JSON schemas used across the EmberHeart: Origins data-driven architecture.

## 1. Character Profiles
**Location:** `characters/npcs/*/profile.json`
**Purpose:** Defines the static lore and traits of an NPC.

```json
{
  "id": "EH-01",
  "name": "Talmarr",
  "race": "Elf",
  "role": "First Wife, Royal Paladin",
  "domains": ["protection", "law"],
  "avatar_url": "portrait.webp",
  "bio": "The First Wife of Kaelrath, matron of the Citadel Guard.",
  "motivation": "Maintain order and protect the Emberhide bloodline."
}
```

## 2. Character State
**Location:** `characters/npcs/*/state.json`
**Purpose:** Defines the mutable, session-to-session state of an NPC.

```json
{
  "current_location": "Citadel Core",
  "mood": "Vigilant",
  "recent_memory": "Reviewed the Citadel Guard rotation.",
  "influence": 8,
  "loyalty": 95
}
```

## 3. Idle Skill Databases (e.g., MINING_DB, FISHING_DB)
**Location:** `docs/<SKILL>_DB.json`
**Purpose:** Lists the available resources the player can gather.

```json
[
  {
    "id": "ore_orichalcum",
    "level_req": 20,
    "name": "Orichalcum",
    "base_time": 60,
    "xp_reward": 50,
    "environment": ["Industrial Mines"],
    "description": "A heavy, warm metal used in golem chassis."
  }
]
```

## 4. Crafting/Smithing Databases
**Location:** `docs/IDLE_SMITHING_DB.json`, `docs/IDLE_CRAFTING_DB.json`
**Purpose:** Lists recipes for processing gathered resources.

```json
[
  {
    "id": "ingot_orichalcum",
    "name": "Orichalcum Ingot",
    "level_req": 25,
    "materials": {"ore_orichalcum": 3, "coal": 1},
    "base_time": 120,
    "xp_reward": 75,
    "facility_req": "Embersteel Quarter Forge"
  }
]
```

## 5. Side Quests Database
**Location:** `docs/SIDE_QUESTS_DB.json`
**Purpose:** Defines narrative encounters.

```json
[
  {
    "quest_id": "SQ-C01",
    "title": "The Zevrix Tariff Dispute",
    "category": "Council",
    "difficulty": "Easy",
    "description": "House Zevrix proposes raising tariffs...",
    "objectives": ["Hear both sides", "Issue a ruling"],
    "rewards": {"gold": 500, "reputation": {"House_Zevrix": 5}},
    "npcs_involved": ["House Zevrix", "Oran Velthyr"],
    "district": "Obsidian Gate"
  }
]
```

## 6. Settlement State
**Location:** `state/SETTLEMENT_STATE.json`
**Purpose:** Tracks kingdom-level statistics.

```json
{
  "population": 24000,
  "treasury_gp": 10200000,
  "morale": "Exalted",
  "active_events": [],
  "military": {
    "wyrmwing_riders": 50,
    "citadel_guard": 500
  }
}
```

## 7. Party Relationships
**Location:** `state/PARTY_RELATIONSHIPS.json`
**Purpose:** Defines connections between Kaelrath and the world.

```json
{
  "wives": [
    {
      "id": "EH-01",
      "name": "Talmarr",
      "bond_type": "Political/Martial Alliance"
    }
  ],
  "children": [],
  "council": [],
  "houses": []
}
```
