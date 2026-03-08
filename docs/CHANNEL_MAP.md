# EmberHeart: Origins — Channel Map

This document maps the Discord channels to their mechanical and narrative functions in the EmberHeart: Origins simulation.

The bot uses the `.env` file to identify these channels by their exact Discord text-channel names.

## Primary Narrative Channels

| env Variable | Default Value | Purpose / Mechanics |
|--------------|---------------|---------------------|
| `COUNCIL_CHAMBERS` | `council-chambers` | The main interaction hub. Mentions here trigger the `CognitiveRouter` to summon 2-5 relevant NPCs (Council, Nobles, Family) to debate the player's decrees. Representing the official court of Kaelrath. |
| `HEARTH` | `hearth` | A quieter, more intimate channel for 1-on-1 conversations with wives or children. High chance of triggering romance or family-bonding events. |
| `WHISPERS` | `whispers` | The domain of the `RumorEngine`. The Flame Chronicler periodically posts gossip, plots, and news from the lower districts here. Players cannot directly command NPCs here. |
| `KINGDOM_HERALD` | `kingdom-herald` | The domain of the `EventGenerator`. The Flame Chronicler posts major, kingdom-wide events (festivals, shard-storms, trade embargoes) here. |

## Idle Skill Channels

*Note: These channels are managed by their respective `IdleTaskEngine` instances. Typing `!start` in these channels initiates background gathering.*

| Channel Name | Engine | Linked JSON Database |
|--------------|--------|----------------------|
| `mining-ops` | Mining Engine | `docs/MINING_DB.json` |
| `woodcutting` | Woodcutting Engine | `docs/WOODCUTTING_DB.json` |
| `fishing-docks`| Fishing Engine | `docs/FISHING_DB.json` |
| `hunting-grounds`| Hunting Engine | `docs/HUNTING_DB.json` |
| `royal-kitchens`| Cooking Engine | `docs/IDLE_COOKING_DB.json` |
| `forge-academy` | Smithing/Crafting/Forge | `docs/IDLE_SMITHING_DB.json` / `IDLE_CRAFTING_DB` / `FORGE_CATALOG` |

## Combat & Quest Channels

| Channel Name | Engine | Linked JSON Database |
|--------------|--------|----------------------|
| `slayer-bounties` | Slayer Engine | `docs/IDLE_SLAYER_DB.json` |
| `quest-board` | Quest Engine | `docs/SIDE_QUESTS_DB.json` |
| `combat-arena` | Combat Engine | (Uses dynamically generated or Quest-specific foes) |

## System Channels

| Channel Name | Purpose |
|--------------|---------|
| `system-logs` | Tracks bot boot status, engine ticks, and error tracebacks. |
| `trade-bazaar` | Domain of the Shop Engine. Players can buy/sell raw materials and finished goods here. |
