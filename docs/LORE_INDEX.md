# EmberHeart: Origins — Lore Index

This index maps key Emberheart lore concepts to their source origin and their implementation in the architecture.

## 1. Characters & Bloodlines

| Concept | Description | Implementation |
|---------|-------------|----------------|
| **Kaelrath Emberhide** | The God-Ascendant Flamekeeper. The Player Character. | Implicit in prompts; `PC-01` in states. |
| **The 4 Wives** | Talmarr, Mareth, Silvy, Callix. Matriarchs of different domains. | Profiles `EH-01` to `EH-04` |
| **The 9 Children** | Ashryn, Kaelen, Silviea, Tharn, Emberyn, Roan, Riven, Tahlia, Dawn. | Profiles `EH-05` to `EH-13` |
| **The 5 Noble Houses** | Zevrix, Maurellien, Caldrith, Theryn, Veydran. | Profiles `EH-21` to `EH-25`, Quests in Council/Trade. |

## 2. Geography & Districts

| District | Primary Function | Implementation |
|----------|------------------|----------------|
| **Citadel Core** | Governance, Royal family residence. | `SETTLEMENT_STATE`, Events, Quests. |
| **Embersteel Quarter** | Heavy industry, golem manufacturing. | `MINING_DB`, `SMITHING_DB`, NPCs `EH-16`, `EH-27`. |
| **Wyrmshadow Commons** | Public living, community kitchens. | `COOKING_DB`, Quests. |
| **Prismspire Heights** | Arcane/divine research, Library of Echoes. | `CRAFTING_DB`, NPCs `EH-17`, `EH-37`. |
| **Outer Groves** | Agriculture, Druidic conclaves. | `WOODCUTTING_DB`, Quests. |
| **Emberlake/Flamepier** | Trade, Naval docks, Fishing. | `FISHING_DB`, Naval Quests. |

## 3. Materials & Crafting

| Material | Significance | Source Database |
|----------|--------------|-----------------|
| **Ashiron** | Standard military metal, fire-resistant. | `MINING_DB`, `SMITHING_DB`, `FORGE_CATALOG`. |
| **Orichalcum** | Divine-conductive, used in golems. | `MINING_DB`, `SMITHING_DB`. |
| **Voidsteel** | Rare, requires celestial/abyssal tempering. | `MINING_DB`, `FORGE_CATALOG`. |
| **Godsteel** | Near-mythical, used in Kaelrath's relics. | `MINING_DB`, `SMITHING_DB`, `FORGE_CATALOG`. |
| **Flamewood** | Never stops burning, used in staves/handles. | `WOODCUTTING_DB`, `CRAFTING_DB`. |
| **Dreamwood** | Softly glowing, used in mnemonic items. | `WOODCUTTING_DB`, `CRAFTING_DB`. |

## 4. The Cosmos & Threats

| Concept | Description | Implementation |
|---------|-------------|----------------|
| **The Flame/Divine Providence** | Source of Kaelrath's power, provides stability. | `EVENT_GENERATOR`, DM Narrator aesthetic. |
| **The Shard-Storm/Corruption** | Lingering pre-Ascension chaotic magic. | `HUNTING_DB`, `SLAYER_DB` (Mutated beasts). |
| **The Vault of Seven** | Ancient deep-earth anomaly, whispers memories. | `MINING_DB` (Deepest drops), Espionage Quests. |
