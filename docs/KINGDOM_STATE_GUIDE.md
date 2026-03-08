# EmberHeart: Origins — Kingdom State Guide

The core persistence file for the kingdom's health and trajectory is located at:
`state/SETTLEMENT_STATE.json`

This file is heavily referenced by the `EventGenerator` and `RumorEngine` to determine the tone and severity of ambient world generation. 

## The Schema

```json
{
  "population": 24000,
  "treasury_gp": 10200000,
  "morale": "Exalted",
  "active_events": [],
  "military": {
    "wyrmwing_riders": 50,
    "citadel_guard": 500,
    "golem_auxilia": 200,
    "naval_fleet": 15
  },
  "districts": [
    "Citadel Core",
    "Embersteel Quarter",
    "Wyrmshadow Commons",
    "Prismspire Heights",
    "Outer Groves",
    "Emberlake Port",
    "Flamepier Docks",
    "Vault of Seven Perimeter",
    "Fae-Craft Borderlands",
    "Silkspire Trail",
    "Obsidian Gate",
    "Bloomshade",
    "Iron March",
    "Ashwake Caravan Spine",
    "Verdant Cross"
  ]
}
```

## Field Explanations

- **`population`**: The total number of citizens. Events (plagues, shard-storms) can reduce this; festivals and trade deals can increase it. If it drops too low, idle resource gathering takes a severe penalty.
- **`treasury_gp`**: The royal coffers. Used to pay for kingdom-scale upgrades, massive resource buyouts, or diplomatic bribes. If it hits 0, morale craters.
- **`morale`**: A string enum (`Exalted`, `Secure`, `Anxious`, `Rebellious`). Affects the tone of the `RumorEngine` and the likelihood of negative `EventGenerator` outputs.
- **`active_events`**: An array of string IDs representing ongoing kingdom-wide effects (e.g., `["trade_embargo", "festival_of_flame"]`). These persist across reboots until a counter-event or Kaelrath's decree resolves them.
- **`military`**: A dictionary tracking troop counts. Specific quests (e.g., Naval Expansion) modify these values. Military strength deters bandit/monster events.
- **`districts`**: A static list of the 15 primary locations in the lore. Used by the LLM as valid anchor points for local rumors and encounters.
