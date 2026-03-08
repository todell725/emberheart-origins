# Changelog

All notable changes to the EmberHeart: Origins project will be documented in this file.

## [Unreleased] - Initial Retheme & Separation

### Added
- **Project Scaffold**: Created standalone directory for `EmberHeart-Origins`, separated from `Claudes-EmberHeart`.
- **Game DBs**: Rethemed all 9 idle skill databases (`MINING_DB`, `WOODCUTTING_DB`, etc.) to feature Origins-specific materials (Ashiron, Orichalcum, Flamewood, etc.) and lore locations.
- **Quest DB**: Created `SIDE_QUESTS_DB.json` containing 40 custom Origins quests across 7 categories (Council, District, Academy, Military, Bloodline, Trade Route, Espionage, Festival).
- **Relationships**: Populated `PARTY_RELATIONSHIPS.json` with Kaelrath's 4 wives, 9 children, 7 council members, and 5 noble houses.
- **Documentation**: Created full documentation suite (README, ARCHITECTURE, CHANGELOG).

### Changed
- **Bot Tone & Prompts**: Changed the main narrator to *The Flame Chronicler*. Prompts restructured to support golden-age kingdom governance rather than underground survival.
- **Channel Mapping**: Rethemed channels (e.g., Party Chat -> Council Chambers).

### Removed
- **Legacy Lore**: Stripped all references to the Scourge, Weaver, underground bunkers, and specific old-campaign character remnants from game databases.
