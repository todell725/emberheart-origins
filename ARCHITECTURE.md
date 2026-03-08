# EmberHeart: Origins Architecture

This document describes the technical architecture of the EmberHeart: Origins Python application.

## Core Philosophy: Data-Driven Narrative

EmberHeart: Origins runs on a rigid separation of logic and content. The Python code (`bot/`, `engines/`, `cogs/`) knows **nothing** about the game's lore. It doesn't know what "Ashiron" is or who "General Varka" is. 

Instead, the logic purely facilitates the reading, writing, and LLM-synthesis of the static JSON databases (`docs/`) and mutable state files (`state/`).

**If you want to change the game, change the JSON files, not the code.**

## System Components

### 1. The Discord Client (`bot/client_unified.py`)
Intercepts all Discord messages, applies basic routing (is this a council channel? an idle channel? a whisper channel?), and delegates to the appropriate engine or LLM router.

### 2. The Cognitive Router (`agents/router.py`)
When a message requires an NPC response (like in `#council-chambers`), the router uses BM25 and domain-tag matching (from `profile.json`) to select the 2-5 most relevant NPCs to respond to the prompt.

### 3. The LLM Agents (`agents/character.py`)
Extracts the selected NPCs, compiles their `profile.json`, current `state.json`, and relationship vectors into an LLM prompt. The output is parsed into a structured JSON array representing sequential NPC dialogue via the `NPCResponseParser`.

### 4. The Idle Engines (`engines/idle_engine.py`)
A generalized, data-driven engine that runs periodic background tasks (Mining, Fishing, etc.). 
- Reads possible actions from `docs/<SKILL>_DB.json`.
- Tracks ongoing player tasks in `state/<SKILL>_ACTIVE.json`.
- Yield depends entirely on the JSON definitions.

### 5. The Dynamic Engines (`engines/event_generator.py` & `rumor_engine.py`)
Scheduled tasks that occasionally trigger the LLM to generate ambient world content.
- **Event Generator**: Looks at `SETTLEMENT_STATE.json` and creates kingdom-level events (festivals, trade disputes).
- **Rumor Engine**: Looks at recent events and NPC locations to generate local gossip.

### 6. The Memory Chronicle (`memory/chronicle.py`)
Stores major events, council decisions, and kingdom milestones using BM25 indexing in `state/chronicle.json`. This provides long-term context to the LLMs so they remember past rulings.

## The Data Layer

The entire narrative is driven by three directories:

1. **`docs/` (Read-only Databases)**
   Lists of materials, monsters, quests, and forged items. The engine randomly selects from these lists based on player level.
2. **`characters/npcs/` (Read/Write NPC Profiles)**
   Contains a folder for each NPC with `profile.json` (static lore, traits, domains) and `state.json` (mutable location, mood).
3. **`state/` (Mutable Kingdom State)**
   Tracks active player timers, settlement statistics (`SETTLEMENT_STATE.json`), relationship networks (`PARTY_RELATIONSHIPS.json`), and the event chronicle.
