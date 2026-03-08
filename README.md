# EmberHeart: Origins

EmberHeart: Origins is a Discord-based RPG and kingdom-management simulation. It puts the players in the role of **Kaelrath Emberhide**, a God-Ascendant ruling a golden-age fantasy kingdom alongside his council, his wives, and his nine children.

This project is a standalone fork of the original `EmberHeartReborn` architecture, fundamentally re-themed from a dark, visceral underground survival game into a high-fantasy golden-age governance simulation. 

## Key Features

- **Council Meetings:** The core gameplay loop. Players interact in the `#council-chambers` channel, where Kaelrath's decisions are debated by relevant members of the royal council or noble houses before Kaelrath passes his final decree.
- **Kingdom-Scale Idle Skills:** Mining, Woodcutting, Fishing, and more managed at a kingdom scale. Players command golems and guilds to gather and process resources (e.g., Ashiron to Godsteel).
- **Dynamic Events & Rumors:** An LLM-driven event generator and rumor engine that creates living, breathing politics, trade disputes, festival preparations, and family drama.
- **Data-Driven Architecture:** All lore, NPCs, quests, and idle progression elements are controlled by simple JSON files in the `docs/` and `characters/` directories.

## Difference from EmberHeart-Reborn

While this project shares a Python/Discord architecture with `EmberHeartReborn`, they are entirely separate games:

| Feature | EmberHeart-Reborn | EmberHeart: Origins |
|---------|--------------------|---------------------|
| **Theme** | Underground survival, horror, Scourge | Golden-age kingdom, divine magic, prosperity |
| **Main Channel** | Party Chat | Council Chambers |
| **DM Agent** | The Chronicle Weaver | The Flame Chronicler |
| **Mechanics Focus** | Personal survival, dungeon crawling | Kingdom decree, resource logistics, diplomacy |
| **Data dependency** | Hard-coupled to original campaign | Fully rethemed JSON databases (Lore-First) |

## Quick Start
1. Create a virtual environment and `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and fill in your Discord token and LLM API keys.
3. Ensure the `docs/`, `characters/`, and `state/` directories are fully populated.
4. Run `python main_unified.py` to start the bot.

## Directory Structure
- `bot/` - Discord client and event routing.
- `cogs/` - Discord command modules (idle skills, quests, council interactions).
- `engines/` - Core simulation logic (event, rumor, combat, idle tasks).
- `core/` - Configuration, identity management, and unified prompts.
- `agents/` - LLM interaction logic (character generation, routing, parsing).
- `memory/` - BM25 chronological indexing of events.
- `characters/npcs/` - All 40+ NPC profile and state files.
- `docs/` - Read-only game databases (Quests, Forging, Slayer, etc.).
- `state/` - Mutable game state (Settlement stats, relationships, shop stock).

For detailed technical design, see [ARCHITECTURE.md](ARCHITECTURE.md).
