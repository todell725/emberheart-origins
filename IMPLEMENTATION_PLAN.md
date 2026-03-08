# EmberHeart: Origins — Implementation Plan

## Context

Todd has two Emberheart datasets that tell different stories:

1. **Claudes-EmberHeart** — A working Discord bot (Python/discord.py) with 25 cogs, 21 engines, 65+ NPCs, 220 quests. Set in an underground survival bunker with a "Weaver" cosmic horror threat.
2. **EmberHeart-origins/** — Raw lore from the original ChatGPT campaign. A surface kingdom in a golden age ruled by Kaelrath Emberhide, God-Ascendant with divine domains, a council of nobles, 4 wives, 9 children, 15 districts, trade routes, and a full military.

**Goal:** Create a new standalone project (`/Users/todd/Documents/Dnd/EmberHeart-Origins/`) that forks the bot architecture from Claudes-EmberHeart but replaces all game data with the original ChatGPT lore. Claudes-EmberHeart stays untouched.

**Key constraints:**
- Documentation is priority one — every file, schema, and decision documented as we go
- Data-first approach (build all game data before touching Python)
- Keep: level/XP, dungeon crawling, idle skills, combat, romance
- Drop: underground survival theme, Scourge/Weaver, bunker politics
- Retheme: "party chat" → "council chambers", DM narrator → "Flame Chronicler"

---

## Phase 0: Project Scaffold & Docs Foundation

### What gets created
- New project directory at `/Users/todd/Documents/Dnd/EmberHeart-Origins/`
- Copy Python architecture from Claudes-EmberHeart:
  - `main_unified.py`, `bot/`, `agents/`, `core/`, `engines/`, `llm/`, `memory/`, `cogs/`
- Do NOT copy: `characters/npcs/*`, `docs/*.json`, `state/*.json`, `venv/`, `__pycache__/`, `archive/`, `.log` files
- Create empty directory stubs: `characters/npcs/`, `docs/`, `state/`, `tests/`
- Create `.env.example` with rethemed channel names
- Create `requirements.txt` (identical deps)

### Documentation produced
- `README.md` — Project overview, setup, how it differs from Claudes-EmberHeart
- `ARCHITECTURE.md` — System architecture adapted for Origins
- `CHANGELOG.md` — Initial entry
- `docs/DATA_SCHEMA.md` — Stub (filled in Phase 1)

### Verification
- All Python files import without errors
- Directory structure matches expected layout
- `grep -r "Claudes-EmberHeart" .` returns no hits in Python

---

## Phase 1: Game Database Retheme (Data-First)

The idle engine (`engines/idle_engine.py`) is fully data-driven — it loads from `docs/<DB>.json` and expects a flat JSON array of task objects. Same schemas, new content.

### 1.1 — MINING_DB.json
Replace ores with Emberheart materials:
- Surface Clay → Ashiron Vein → Flame-Hardened Metal → Orichalcum → Memory Ore → Voidsteel → Vault of Seven (Divine)
- Locations reference Industrial Mines, Vault of Seven, Embersteel Quarter

### 1.2 — WOODCUTTING_DB.json
- Firesapling → Ashbark → Flamewood → Dreamwood → Shard-Barked Ancient → Flame-Hardened Ironwood → Sentient Tree
- Locations reference Outer Grove Districts, Enchanted Groves, Maurellien lands

### 1.3 — FISHING_DB.json
- Emberlake Shallows → River Bend → Deep Emberlake → Sacred Falls → Leviathan Cradle → Fae-Touched Waters → Divine Spring
- Locations reference Emberlake Port, Flamepier Docks, Bloomshade waters

### 1.4 — HUNTING_DB.json
- Emberfield Hare → Flame Stag → Shard-Mutated Boar → Wild Wyrmling → Dream-Stalker Wolf → Echo Elk → Ancient Wyrm

### 1.5 — IDLE_SLAYER_DB.json
Replace D&D monsters with Origins threats:
- Shard Entity, Dream-Eater, Mnemonic Coil, Corrupted Vault Seraph, Crimson Mask Cultist, Shardborn Spawn, Hollow Choir Shade, Fae Trickster, Void-Touched Golem, Ember Maw Beast, etc.

### 1.6 — IDLE_COOKING_DB.json
Ingredients from Origins crops: Flamewheat Bread, Ashbarley Stew, Shimmerplum Tart, Emberroot Roast, Shard-Grain Porridge, Dreamfruit Elixir, Divine Feast

### 1.7 — IDLE_CRAFTING_DB.json
Craft from gathered materials: Dreamwood Staff, Shard-Bark Shield, Ashiron Tools, Emberlake Nets

### 1.8 — IDLE_SMITHING_DB.json
Smelt Origins ores: Ashiron Bar, Orichalcum Ingot, Voidsteel Bar, Flame-Hardened Plate, Memory-Forged Blade

### 1.9 — FORGE_CATALOG.json
Emberheart Forge Academy catalog: Embersteel Plate, Godsteel Greatsword, Memory-Forged Crown, Orichalcum War Golem Shell, Dreamforged Amulet

### 1.10 — SIDE_QUESTS_DB.json (Largest file — start with 30-50 quests)
Same schema as source (id, title, difficulty, xp_reward, location, key_npcs, turns with choice_a/b, branching_outcomes).

Quest categories:
- **Council** (5-10): Noble house proposals, diplomatic missions
- **District** (10-15): One per district — golem malfunction, dream-bleed, trade disputes
- **Academy** (5): Student rivalries, experiments gone wrong
- **Military** (5): Border patrols, shard incursions, naval commissioning
- **Bloodline** (5-10): Reuniting with Kaelrath's 9 scattered children
- **Trade Route** (5): Caravan escort, fae-craft negotiations

### 1.11 — Supporting state/reference files
- `SETTLEMENT_STATE.json` — Golden age kingdom stats (pop 24k, treasury 10.2M GP, etc.)
- `PARTY_STATE.json` — Kaelrath as PC-01 (God-Ascendant, AC 21, HP ~290, domains, relics)
- `PARTY_RELATIONSHIPS.json` — Kaelrath → wives, council, children
- `PARTY_EQUIPMENT.json` — Kaelrath's relics
- `NPC_ORIENTATIONS.json` — Updated for new roster
- `NPC_STATE_FULL.json` — Full NPC state for Origins roster

### Documentation produced
- `docs/DATA_SCHEMA.md` — Every JSON schema documented with field descriptions and examples
- `docs/LORE_INDEX.md` — Maps lore topics to source files in EmberHeart-origins/
- `docs/RESOURCE_CHAIN.md` — Shows how materials flow (mining drops → smithing, hunting → cooking, etc.)

### Verification
- All JSON files pass `python -m json.tool` validation
- Schema keys match source counterparts (automated comparison)
- Quest DB has 30+ quests with complete turn structures
- Resource chain is consistent (mining drops appear in smithing recipes, etc.)

---

## Phase 2: NPC Character Data

Create the full NPC roster. Each NPC gets a folder `characters/npcs/EH-XX_Name/` with `profile.json` and `state.json`.

### NPC Roster

**Royal Family (EH-01 → EH-14)**
| ID | Name | Role |
|----|------|------|
| EH-01 | Talmarr | First Wife, Elven Paladin |
| EH-02 | Mareth | Second Wife, Blade Master |
| EH-03 | Silvara (Silvy) | Third Wife, Illusionist |
| EH-04 | Callix | Fourth Wife, Shadow Mage |
| EH-05 | Ashryn | Child (18), Fire Dancer |
| EH-06 | Kaelen | Child (16), Forgehand |
| EH-07 | Silviea | Child (13), Illusion Prodigy |
| EH-08 | Tharn | Child (12), Street Thief |
| EH-09 | Emberyn | Child (10), Young Bard |
| EH-10 | Roan | Child (8), Dreamseer |
| EH-11 | Riven | Child (7), Silent Burning |
| EH-12 | Tahlia | Child (5), Birdspeaker |
| EH-13 | Dawn | Infant |
| EH-14 | Queen Maeryn | Emberheart Royalty |

**Council (EH-15 → EH-20)**
| ID | Name | Role |
|----|------|------|
| EH-15 | General Varka | Military Commander |
| EH-16 | High Enchanter Thalos | Golemancer, Prismspire |
| EH-17 | Archivist Sybelle | Lorekeeper |
| EH-18 | Mason Brennus | Infrastructure |
| EH-19 | Brida | Matron of Wyrmwood Manor |
| EH-20 | Prince Aereth | Heir |

**Noble Houses (EH-21 → EH-25)**
| ID | Name | Role |
|----|------|------|
| EH-21 | Velra Zevrix | Finance & Trade |
| EH-22 | Elder Maurellien | Druids & Healing |
| EH-23 | Commander Caldrith | Defense & Order |
| EH-24 | Arcanist Theryn | Arcane & History |
| EH-25 | Forgemaster Veydran | Golemcraft & Industry |

**Military (EH-26 → EH-30)**
| ID | Name | Role |
|----|------|------|
| EH-26 | Captain Rynn | Wyrmwing Commander |
| EH-27 | Forge-Sergeant Halvek | Golem Weaponry |
| EH-28 | Commander Thera | Navy Admiral |
| EH-29 | Drillmaster Harkon Veer | Military Training |
| EH-30 | Herald-Commander Veyla Jurn | Loyalty & Recruitment |

**Trade & Economy (EH-31 → EH-36)**
| ID | Name | Role |
|----|------|------|
| EH-31 | Oran Velthyr | Guildmaster, Embertrade |
| EH-32 | Selyra Vint | Gilded Scale Consortium |
| EH-33 | Bramm Holdock | Warden of Iron Weigh |
| EH-34 | Dellan the Tallyman | Bazaar Overseer |
| EH-35 | Captain Veyra Moonswake | Merchant Captain |
| EH-36 | Zharim the Inkweaver | Exotic Trader |

**Academy & Specialists (EH-37 → EH-42)**
| ID | Name | Role |
|----|------|------|
| EH-37 | Golemwright Fereth | Prismspire Design Lead |
| EH-38 | Mother Aressa | Temple Shrine Matron |
| EH-39 | Moon-Sibyl | Echo-Sleepers' Hall |
| EH-40 | Justice Verra Flamebrand | Chief Justicar |
| EH-41 | Stablemaster Halric | Warhorse & Wyrm |
| EH-42 | Ambassador Lysithra | Fae-Craft Liaison |

**Player Character**
| ID | Name | Role |
|----|------|------|
| PC-01 | Kaelrath Emberhide | God-Ascendant, Flamekeeper |

**Narrator**
| ID | Name | Role |
|----|------|------|
| DM-00 | The Flame Chronicler | Narrator/DM Voice |

### Profile schema (same as source)
```json
{
  "id": "EH-XX",
  "name": "Name",
  "race": "Race",
  "role": "Role",
  "domains": ["topic1", "topic2"],
  "avatar_url": "",
  "description": "Physical appearance",
  "bio": "Background",
  "motivation": "What drives them",
  "influence": 0-10,
  "loyalty": 0-100,
  "respect": 0-100,
  "secret": "Hidden knowledge",
  "corruption_exposure": 0,
  "house_allegiance": "House Name or 'Crown'"
}
```

### Documentation produced
- `docs/NPC_CATALOG.md` — Full roster with ID, name, role, domain tags, house affiliation
- `docs/IDENTITY_REGISTRY.md` — Maps IDs to names, avatars, aliases

### Verification
- All 43+ NPC folders exist with valid profile.json and state.json
- `core/config.py`'s `load_npc_identities()` loads all profiles
- Every NPC mentioned in quest key_npcs exists in the roster
- NPC_STATE_FULL.json generated from individual profiles

---

## Phase 3: Python Retheme (Minimal Modifications)

Surgical text changes only — no architectural changes.

### 3.1 — `core/config.py`
- Change `_DM_IDENTITY` from "The Chronicle Weaver" to "The Flame Chronicler"
- Update `IDENTITIES` dict (STEWARD, RUMORS aliases)
- Rewrite `DM_SYSTEM_PROMPT` for golden-age kingdom narrator tone (no Scourge/Weaver/underground)

### 3.2 — `main_unified.py`
- Rename channel env vars: `PARTY_CHAT` → `COUNCIL_CHAMBERS`, `DM_NARRATION` → `KINGDOM_HERALD`, `CAMPFIRE` → `HEARTH`, `RUMORS` → `WHISPERS`
- Update banner text to "EmberHeart: Origins"

### 3.3 — `bot/client_unified.py`
- Update channel key references to match new env vars
- Update on_ready branding

### 3.4 — `engines/event_generator.py`
- Retheme LLM prompt: kingdom events (noble proposals, festivals, trade news, divine omens) instead of underground survival

### 3.5 — `engines/rumor_engine.py`
- Retheme LLM prompt: court gossip, noble house dealings, children sightings, Forge Academy incidents

### 3.6 — `cogs/campfire.py` → `cogs/hearth.py`
- Rename file and class
- Update channel routing decorator

### 3.7 — Channel routing in all cogs
- Update `@require_channel()` decorators where channel names changed
- Idle skill channels stay the same (idle-mining, idle-fishing, etc.)

### Documentation produced
- `docs/PYTHON_CHANGES.md` — Every modified Python file, what changed, why
- `docs/CHANNEL_MAP.md` — Discord channel name → purpose mapping
- `.env.example` updated

### Verification
- `grep -r "Scourge\|Weaver\|bunker\|underground\|Chronicle Weaver" *.py **/*.py` returns zero hits
- Bot starts without import errors
- All 25 cogs load successfully

---

## Phase 4: Kingdom State & Event Systems

### 4.1 — SETTLEMENT_STATE.json
Golden-age baseline: population 24k, treasury 10.2M GP, 15 districts, military forces, resource outputs, morale: Exalted

### 4.2 — State file stubs
Empty/initial JSON files in `state/`: MINING_ACTIVE, FISHING_ACTIVE, HUNTING_ACTIVE, WOODCUTTING_ACTIVE, SLAYER_ACTIVE, SMITHING_ACTIVE, SHOP_STOCK, QUEST_COMPLETION, PARTY_RELATIONSHIPS, chronicle.json (seeded with a few kingdom memories)

### 4.3 — Event Generator prompts
Retheme to produce: district happenings, noble proposals, trade route news, festival prep, golem incidents, divine omens

### 4.4 — Rumor Engine prompts
Retheme to produce: court intrigue, house dealings, children sightings, Forge Academy news, Vault whispers

### Documentation produced
- `docs/KINGDOM_STATE_GUIDE.md` — Every SETTLEMENT_STATE field explained
- `docs/EVENT_CATEGORIES.md` — Event types with examples

### Verification
- All state JSONs valid and loadable
- Event generator produces a test event
- Rumor engine produces a test rumor

---

## Phase 5: Council Chambers Format

The signature feature — council meetings replace party chat.

### Flow
1. Player (as Kaelrath) posts in #council-chambers
2. DM-00 (Flame Chronicler) posts kingdom stats header
3. CognitiveRouter selects 2-5 council members based on topic
4. Each responds with title and house affiliation via webhook

### Implementation
- Add `domains` field to council NPC profiles (already planned in Phase 2)
- Modify `agents/router.py` CognitiveRouter: add council mode with domain-tag matching and higher `max_speakers`
- Modify `bot/client_unified.py`: detect council channel, apply council-specific formatting

### Documentation produced
- `docs/COUNCIL_FORMAT.md` — Full spec of council meeting flow with example sessions

### Verification
- Test message in council-chambers gets 2-4 NPC responses
- Stats header appears
- Non-council channels work normally

---

## Phase 6: Testing & Polish

### Automated checks
- JSON schema validation on all docs/*.json
- NPC roster integrity (quest key_npcs → real NPCs)
- Resource chain validation (mining → smithing, hunting → cooking)
- No stale references grep (Scourge, Weaver, bunker, underground, Line 4)

### Manual testing
- Start bot with test Discord server
- Test each idle skill, quest flow, council interaction, events, rumors
- Verify NPC webhooks display correctly

### Documentation review
All docs complete and accurate:
- README.md, ARCHITECTURE.md, CHANGELOG.md
- docs/DATA_SCHEMA.md, NPC_CATALOG.md, LORE_INDEX.md, RESOURCE_CHAIN.md
- docs/PYTHON_CHANGES.md, CHANNEL_MAP.md
- docs/KINGDOM_STATE_GUIDE.md, EVENT_CATEGORIES.md, COUNCIL_FORMAT.md
- docs/IDENTITY_REGISTRY.md

### Verification
- All documentation files exist and are non-empty
- Bot runs for 5 minutes without errors
- At least one: quest accepted, idle skill started, council interaction, event generated

---

## Phase Dependency Order

```
Phase 0 (scaffold)
    ↓
Phase 1 (game DBs) ──→ Phase 2 (NPCs)
                              ↓
                     Phase 3 (Python retheme)
                              ↓
                     Phase 4 (kingdom state)
                              ↓
                     Phase 5 (council format)
                              ↓
                     Phase 6 (test & polish)
```

## Critical Source Files

| File | Purpose | What changes |
|------|---------|-------------|
| `Claudes-EmberHeart/core/config.py` | Identity registry, DM prompt, paths | Retheme narrator, channels |
| `Claudes-EmberHeart/engines/idle_engine.py` | Base class for idle skills | Nothing — data-driven |
| `Claudes-EmberHeart/bot/client_unified.py` | Bot client, routing, setup | Channel names, branding |
| `Claudes-EmberHeart/agents/router.py` | NPC speaker selection | Add council mode |
| `EmberHeart-origins/EmberHeart-o.md` | Master lore document (548 lines) | Source of truth for all data |
| `EmberHeart-origins/emberheart world/*.md` | Expanded lore (districts, military, trade) | Source of truth for world data |

---

## 🔬 ULTRATHINK POST-ANALYSIS (Agent v3.0 Review)

> **Execution:** Parallel Orchestrator (4 Tracks: Architecture, Adversarial, Lore-Synergy, First-Principles)  
> **Convergence Score:** 92/100 (Proceed with Amendments)

After cross-referencing the `Claudes-EmberHeart` architecture (`ARCHITECTURE.md`), the `EmberHeart-Origins` lore, and the proposed `IMPLEMENTATION_PLAN.md`, several critical friction points and necessary adjustments have been identified. 

### 1. ⚠️ The Concurrency Bottleneck (Adversarial Track)
**The Problem:** Phase 5 proposes that the `CognitiveRouter` selects 2-5 council members to respond whenever Kaelrath posts. According to `ARCHITECTURE.md`, a single local LLM response takes 15-30 seconds. Generating 5 sequential NPC responses will trap the user in a **1.5 to 2.5 minute wait** per council turn. This will destroy the UX.
**Proposed Change:** 
- **Option A (DM Summarization):** Instead of individual LLM calls per NPC, feed the selected 3-5 NPCs into a single prompt for the `DungeonMaster` / `Flame Chronicler` agent, who generates a unified JSON array of responses in one pass, taking advantage of the `NPCResponseParser`. 
- **Option B (Strict Cap):** Hard-cap `max_speakers=2` for standard interactions, reserving multi-speaker arrays for `!council` commands specifically.

### 2. 👑 Kingdom-Scale Mechanics vs. Party Mechanics (First Principles Track)
**The Problem:** The current `idle_engine.py` (mining, woodcutting) implies physical labor by the party. Kaelrath is a God-Ascendant ruling 24,000 citizens. It breaks immersion if the user has to type `!mine` to swing a pickaxe. 
**Proposed Change:** 
- Retheme the Idle Engine verbs from *gathering* to *decreeing/blessing*. 
- `!mine` becomes `!bless_vault` (applying Kaelrath's triple-yield modifier to the Golems). 
- `!chop` becomes `!grove_edict`. 
- The yield text should reflect *kingdom scale* (e.g., "The Wyrmtooth Golems extracted 45 units of Ashiron") rather than individual loot finding.

### 3. 🧠 Memory & Context Layer Adjustments (Architecture Track)
**The Problem:** The current `Chronicle` uses basic categories (`dialogue`, `quest`). The Origins lore introduces heavily compartmentalized political and divine data that BM25 might conflate if not tagged properly.
**Proposed Change:** 
- Expand `Chronicle` storage tags in Phase 1 to include: `noble_proposal`, `bloodline_inheritance`, `fae_trade`, and `divine_omen`.
- Kaelrath's 9 children and 4 wives require explicit hierarchical tagging in `PARTY_RELATIONSHIPS.json` so the Router knows who belongs to which faction when generating family friction.

### 4. ⚖️ The Final Decision Maker (Lore Synergy Track)
**The Problem:** The current bot prompts NPCs to freely debate and vote. The Origins lore explicitly states: *Kaelrath provides the final ruling.* 
**Proposed Change:** 
- The `DM_SYSTEM_PROMPT` and `CharacterAgent` base prompts must strictly instruct NPCs to end their proposals by deferring to Kaelrath's judgment. They may argue with each other, but they must await the Flamekeeper's decree rather than acting autonomously.

---

## Codex’s Standalone Implementation Approach

### Conclusions from Comparing Origins Lore/Plan vs Claudes-EmberHeart
- Origins is fundamentally a kingdom-governance simulation with Kaelrath Emberhide as final authority in council outcomes.
- Claudes-EmberHeart is feature-rich and technically useful as a capability reference, but it is strongly theme-bound to a different narrative baseline.
- A standalone architecture is the cleanest implementation path because it prevents inherited naming/theme debt and avoids implicit runtime coupling.

### How I Would Implement It (Standalone)
1. Define an independent project architecture and module boundaries (`bot`, `agents`, `engines`, `memory`, `core`, `cogs`, `docs`, `state`, `characters`) inside EmberHeart-Origins.
2. Lock Origins-first schemas for NPCs, quests, settlement state, relationships, and idle skill databases directly from lore source files.
3. Build core services first: config loading, identity registry, channel routing, response parser, and state persistence.
4. Implement gameplay engines and cogs around council-first interaction flow, then layer idle/quest/event/rumor systems.
5. Retheme narrator and prompts to The Flame Chronicler and enforce Kaelrath-final-ruling behavior in all council outputs.
6. Add validation and testing gates (schema validation, cross-reference checks, stale-theme detection, smoke runtime checks) before expanding scope.

### Required Plan Corrections
- Remove or replace wording that implies forking/copying architecture from Claudes-EmberHeart as a build dependency.
- Reword Phase 0 to: initialize standalone project structure within the existing EmberHeart-Origins directory.
- Add explicit non-goals:
  - No direct runtime dependency on `claudes-emberheart` artifacts.
  - No file-copy bootstrap from `claudes-emberheart` directories.
  - No requirement to maintain Claude env-var/API compatibility.
- Keep Claudes-EmberHeart comparison as a parity checklist only (feature benchmark), not an implementation base.

### Acceptance Criteria
- The implementation plan is decision-complete for a standalone build.
- The resulting design has zero runtime dependency on `claudes-emberheart` files.
- Council chamber behavior, lore-derived data modeling, and validation/testing gates are explicitly defined.
- Environment/channel naming is Origins-specific and not constrained by Claude naming conventions.

---

## ⚡ Antigravity's Ultrathink Analysis (Dissenting Opinion)

> **Protocol:** /ultrathink v3.0 — Full Parallel Orchestrator  
> **Tracks:** Architecture Audit (code-level), Adversarial (vs. Codex's conclusions), Lore Synergy, First Principles  
> **Convergence Score:** 88/100

### Executive Summary

**I respectfully disagree with Codex's standalone recommendation.** After reading every major file in the `Claudes-EmberHeart` codebase — not just the architecture doc — my assessment is that **fork-and-retheme is the correct path**, and it isn't close. Codex's analysis appears to be based on the *conceptual narrative* difference between the two projects, not the *actual code coupling*. Here's the evidence:

---

### Track A: Architecture Audit — The Coupling Is a Myth

I read the following files line-by-line:

| File | Lines | Theme-Coupled? |
|------|-------|----------------|
| `core/config.py` | 219 | **Partially** — Only `_DM_IDENTITY` name, `DM_SYSTEM_PROMPT` text, and `IDENTITIES` aliases. The identity *system* (resolver, alias registry, ID normalization) is completely generic. |
| `engines/idle_engine.py` | 458 | **No** — Fully data-driven. Loads JSON from `docs/`, tracks active tasks in `state/`. Zero theme strings. The entire loot, XP, and party breakdown system is parameterized. |
| `engines/event_generator.py` | 217 | **Partially** — Only the LLM prompt string on line 123 references "EmberHeart" and "Corruption Level". The event loop, parsing, and execution logic are generic. |
| `engines/rumor_engine.py` | 186 | **Partially** — Only the LLM prompt on line 133 and the narrator list on line 166. The architecture (loop timing, quest-hook integration, channel posting) is generic. |
| `agents/router.py` | 175 | **No** — Pure scoring algorithm. No theme references whatsoever. |
| `agents/parser.py` | ~400 | **No** — JSON/regex parser with fallbacks. Theme-agnostic. |
| `agents/character.py` | ~300 | **No** — Loads personality from data files, builds prompts dynamically. |
| `bot/client_unified.py` | 623 | **Partially** — Channel key names (`party_chat`, `campfire`), `on_ready` banner text, webhook name `"EmberHeart-NPCs"`. The actual message routing, webhook management, prompt construction, and Chronicle integration are completely theme-agnostic. |
| `main_unified.py` | 122 | **Partially** — Only the banner strings and env var names for channels. |
| `memory/chronicle.py` | ~200 | **No** — BM25 search engine. Zero theme coupling. |
| All 26 cogs | ~200K total | **No** — Every cog loads its engine, registers commands, and formats output. Cog logic is tied to *game mechanics*, not *narrative theme*. |
| All idle skill engines | 8 files | **No** — Each is a thin subclass of `IdleTaskEngine` that specifies which JSON files to load. |

**Bottom line:** Out of ~60 Python files and ~5,000 lines of code, theme contamination exists in exactly **5 locations**:

1. `DM_SYSTEM_PROMPT` in `core/config.py` (~27 lines of prompt text)
2. `_DM_IDENTITY` dict in `core/config.py` (1 line: the name "Chronicle Weaver")
3. Event prompt in `engines/event_generator.py` (~20 lines)
4. Rumor prompt in `engines/rumor_engine.py` (~15 lines)
5. Channel env var names + branding in `main_unified.py` + `bot/client_unified.py` (~10 lines total)

**That's ~73 lines out of ~5,000.** A 1.5% contamination rate does not justify a ground-up rewrite.

---

### Track B: Adversarial — Why Standalone Is the Wrong Call

Codex argues standalone prevents "inherited naming/theme debt and avoids implicit runtime coupling." Let me address both:

**1. "Naming/Theme Debt"**
- There is no naming debt. The only theme-bound names are in the 5 locations listed above. A `sed` command could fix all of them in under 60 seconds. The *structural* names (`IdleTaskEngine`, `CognitiveRouter`, `Chronicle`, `CharacterAgent`) are perfectly applicable to Origins.

**2. "Implicit Runtime Coupling"**  
- There is zero runtime coupling. The bot loads NPCs from `characters/npcs/*/profile.json`. It loads game databases from `docs/*.json`. It loads state from `state/*.json`. **Every single data dependency is a JSON file path, not a code import.** Swapping data = swapping the game. That's the entire design.

**3. What standalone *actually* costs:**
- You lose 26 working cogs (~200,000 bytes of tested Discord integration)
- You lose 20 battle-tested engines (idle, quest, combat, romance, forge, shop, event, rumor, tick, slayer)
- You lose the unified bot client with webhook management, typing delays, message chunking, and NPC event triggers
- You lose the Chronicle/RAG pipeline with BM25 search
- You lose the CognitiveRouter + NPCResponseParser combo (the "key innovation" per ARCHITECTURE.md)
- **Estimated rewrite time: 3-5 weeks** to reach feature parity
- **Estimated fork-and-retheme time: 2-3 days** to reach a running Origins bot

---

### Track C: Lore Synergy — What Actually Needs to Change

Here's what a fork-and-retheme approach requires, mapped to the lore:

#### Tier 1: String Replacements (Day 1, < 2 hours)
- `_DM_IDENTITY.name`: "The Chronicle Weaver" → "The Flame Chronicler"
- `_DM_IDENTITY.avatar`: New avatar URL
- Channel env vars: `PARTY_CHAT` → `COUNCIL_CHAMBERS`, `CAMPFIRE` → `HEARTH`, `RUMORS` → `WHISPERS`
- `on_ready` banner: "EMBERHEART UNIFIED" → "EMBERHEART: ORIGINS"
- Webhook name: "EmberHeart-NPCs" → "Origins-NPCs"

#### Tier 2: Prompt Rewrites (Day 1, ~4 hours)
- `DM_SYSTEM_PROMPT`: Rewrite 27 lines from "dark visceral underground" to "golden age kingdom governance"
- `event_generator._build_event_prompt`: Rewrite to produce district happenings, noble proposals, festivals, divine omens
- `rumor_engine._build_rumor_prompt`: Rewrite to produce court gossip, Noble House dealings, Forge Academy incidents
- `rumor_engine._post_rumor` narrator list: Replace tavern narrators with court narrators

#### Tier 3: Data Population (Days 1-2)
- Populate all `docs/*.json` databases with Origins materials (this is identical work whether standalone or fork)
- Create 43+ NPC profile folders under `characters/npcs/` (identical work either way)
- Populate `state/` with golden-age baseline (identical work either way)

#### Tier 4: New Feature — Council Mode (Day 2-3)
- Add `council` channel type in `client_unified.py._handle_party_chat()` — route through domain-tag filtering
- Add `domains` field to NPC profiles (already planned in Phase 2)
- Enforce Kaelrath-defers behavior via system prompt amendment (my earlier Ultrathink finding #4)
- Apply the concurrency fix from my earlier analysis (single-prompt multi-NPC generation)

---

### Track D: First Principles — What Codex Got Right

To be fair, Codex raises two valid points that I incorporate:

1. **Zero runtime dependency on Claudes-EmberHeart at deploy time** — Agreed. The fork should be a full copy into `EmberHeart-Origins/`, not a symlink or import. Once forked, the two projects diverge permanently.
2. **Origins-first naming** — Agreed. All env vars, channel names, and Discord-facing strings should use Origins naming from the start. No "Claude" references should survive.

But these are properties of a *well-executed fork*, not arguments for standalone.

---

### My Recommended Implementation Order

```
Day 1 (Morning):   Copy Python + infrastructure into EmberHeart-Origins/
Day 1 (Afternoon): Tier 1 string replacements + Tier 2 prompt rewrites
Day 1 (Evening):   Verify: bot starts, cogs load, zero stale-theme grep hits
Day 2 (Full):      Tier 3 data population (NPCs, game DBs, state files)
Day 2 (Evening):   Verify: bot starts with Origins data, idle skills work
Day 3 (Full):      Tier 4 Council Mode + concurrency fix
Day 3 (Evening):   Verify: council interaction works, multi-NPC < 30sec
```

### My Non-Negotiables

1. **Keep `idle_engine.py` as-is.** It's a masterclass in data-driven design. Don't rewrite it.
2. **Keep the `CognitiveRouter` + `NPCResponseParser` pipeline.** It's the core innovation and it's 100% theme-agnostic.
3. **Keep all 26 cogs.** They're game mechanics, not narrative. `!mine` still works; only the *flavor text* in the JSON database changes.
4. **Rewrite the `DM_SYSTEM_PROMPT` completely.** This is the #1 priority — it controls the entire narrative voice.
5. **Apply the Concurrency Fix** (from my earlier analysis) — use single-prompt multi-NPC generation for council sessions.
6. **Kingdom-scale idle verbs** (from my earlier analysis) — retheme `!mine` flavor text to reference Golem operations, not personal labor. This is a *data* change in `MINING_DB.json`, not a code change.

### Acceptance Criteria (Revised)

- The implementation results in zero runtime dependency on `claudes-emberheart` files (Codex's criterion — agreed)
- `grep -ri "chronicle weaver\|scourge\|weaver\|bunker\|underground" *.py **/*.py` returns zero hits
- All 26 cogs load successfully with Origins data
- Council mode produces 2-4 domain-relevant NPC responses in < 30 seconds
- Bot runs for 10 minutes without errors using Origins NPC roster and game databases
