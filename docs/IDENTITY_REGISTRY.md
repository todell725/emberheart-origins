# EmberHeart: Origins — Identity Registry

The Identity Registry is a core component of `core/config.py`. It is responsible for mapping internal AI roles and text-aliases to the Discord output identity (Name + Avatar).

## AI System Identities

These identities are hardcoded into the system and do not use the dynamic Discord Webhook trick. They are primarily for the LLM's internal representation.

- **`_DM_IDENTITY`**: "The Flame Chronicler". Represents the omniscient narrator, the event generator, and the rumor engine.
- **`_SYSTEM_IDENTITY`**: "EmberHeart System". Used for error messages, boot sequences, and out-of-character administration.

## The Webhook Aliases

When an NPC responds or starts a quest, the bot looks up their name in the registry to apply the correct avatar URL and Display Name to the Discord Webhook.

**Data Source:** `characters/npcs/*/profile.json`

The system automatically parses all 43 folders on boot to build the master Identity Registry. Example:

```json
{
  "id": "EH-17",
  "name": "Sybelle",
  "avatar_url": "portrait.webp"
}
```

The bot takes that input and registers multiple valid aliases. If the LLM generates output starting with `"Archivist Sybelle:"` or `"Sybelle:"` or `"EH-17:"`, the Regex parser in `agents/parser.py` resolves it all to the same Webhook profile.
