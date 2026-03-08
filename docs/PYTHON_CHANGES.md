# EmberHeart: Origins — Python Changes (Fork Log)

This document tracks the surgical modifications required to adapt the underlying `Claudes-EmberHeart` Python architecture into the `EmberHeart: Origins` standalone kingdom simulation.

*Note: The goal was a 100% data-driven retheme. Python changes were strictly limited to aesthetic, naming, and prompt modifications.*

## 1. `core/config.py`
- **Identity Registry:** Changed `_DM_IDENTITY` name from `"The Chronicle Weaver"` to `"The Flame Chronicler"`. Updated identity alias dictionaries.
- **Narrative Prompts:** Rewrote `DM_SYSTEM_PROMPT` completely. Old text emphasizing "dark visceral underground survival" and "Scourge/Weaver" threats replaced with instructions for a "golden-age high fantasy kingdom", "divine providence", and "royal council governance."

## 2. `main_unified.py`
- **Environment Variables:** 
  - `PARTY_CHAT` ➡️ `COUNCIL_CHAMBERS`
  - `CAMPFIRE` ➡️ `HEARTH`
  - `RUMORS` ➡️ `WHISPERS`
  - `DM_NARRATION` ➡️ `KINGDOM_HERALD`
- **Aesthetic:** Updated startup banner from `EMBERHEART UNIFIED` to `EMBERHEART: ORIGINS`.

## 3. `bot/client_unified.py`
- **Channel Routing:** Updated the keys in the channel map to reflect the new env vars.
- **Webhook Identity:** Updated the fallback webhook names from `EmberHeart-NPCs` to `Origins-NPCs`.

## 4. `engines/event_generator.py`
- **LLM Prompt (`_build_event_prompt`):** Changed focus from bunker disasters, starvation, and Scourge attacks to noble house proposals, district festivals, trade disputes, golem incidents, and divine omens matching the golden-age aesthetic.

## 5. `engines/rumor_engine.py`
- **LLM Prompt (`_build_rumor_prompt`):** Changed from tavern whispers about monsters/survival to court gossip regarding the royal children, academy accidents, and trade consortium deals.

## 6. `cogs/` Modifications
- **`cogs/campfire.py` ➡️ `cogs/hearth.py`:** Renamed file and class to `HearthCog`.
- **Decorators:** All `@require_channel` decorators were updated to match the new `COUNCIL_CHAMBERS`, `HEARTH`, and `WHISPERS` variables.
- **Idle Cogs:** Left functionally identical. Output text flavor changes were handled entirely via JSON Database modifications (e.g., `MINING_DB.json`), not Python string updates.

## Summary
Less than 2% of the total Python codebase was modified. Because the bot relies heavily on runtime JSON loading (`docs/*.json` and `characters/npcs/*/profile.json`), changing the data completely changed the game mechanics and character roster without requiring an engine rewrite.
