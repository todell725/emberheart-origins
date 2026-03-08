# EmberHeart: Origins — Council Format

The "Council Format" is the defining signature mechanic of PemberHeart: Origins, separating it fundamentally from its predecessor's "party chat" mechanic.

Instead of generic companions following the player through a dungeon, Kaelrath sits at the seat of power and the world comes to him.

## The Interaction Flow

1. **Player (Kaelrath) speaks in `#council-chambers`.**
   *Example: "@Council, House Zevrix is requesting a tariff increase at the Obsidian Gate. What are our alternatives?"*

2. **The `CognitiveRouter` Analyzes.**
   The router parses the player's message and extracts themes (e.g., `trade`, `finance`, `obsidian gate`). It compares these themes against the `domains` tags defined in every NPC's `profile.json`.

3. **NPC Selection.**
   The router picks the 2-5 most relevant NPCs. For a trade dispute, it might select:
   - `EH-21: Velra Zevrix` (Finance & Trade)
   - `EH-31: Oran Velthyr` (Guildmaster)
   - `EH-17: Archivist Sybelle` (Law/Lorekeeper)

4. **Multi-NPC LLM Generation.**
   The `CharacterAgent` feeds the player prompt, the state of the kingdom, and the profiles of the selected NPCs into a single LLM call. The LLM is instructed to output a JSON array of responses, simulating a sequential debate between those specific characters.

5. **Discord Output via Webhooks.**
   The bot parses the JSON array and sequentially triggers Discord Webhooks to post each message under the respective NPC's name and avatar. 

6. **The Final Ruling.**
   The NPCs are instructed *never* to execute a major action autonomously. They may debate, argue, and propose solutions, but they must end by deferring to Kaelrath for the final decree. The player provides the final ruling, which is saved to the `memory/chronicle.json`.

## Enforcing the Format

This behavior is enforced in two places:
1. `core/config.py` — The unified system prompts explicitly instruct characters to respect Kaelrath's ultimate authority.
2. `agents/router.py` — High-priority clamping ensuring that only NPCs with relevant domain tags are summoned to a specific issue.
