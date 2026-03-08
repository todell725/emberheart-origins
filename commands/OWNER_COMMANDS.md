# Owner Commands Reference

Sovereign Authority Commands for EmberHeart Bot Administration

---

## 👑 Overview

Owner commands provide administrative control over the bot and game systems. These commands bypass normal restrictions and limitations, giving the server owner complete control over time manipulation, system initialization, and debugging.

**Permission Required:** Bot Owner (configured in bot settings)

---

## ⏱️ Time Manipulation

### `!owner skip <hours>`

Skip forward in time for all active idle activities in the current channel.

**Usage:**
```
!owner skip <hours>
```

**Parameters:**
- `hours` - Number of hours to skip (float, no limit)

**What It Does:**
- Advances time for slayer tasks
- Advances time for hunting sessions
- Advances time for mining operations
- Advances time for fishing sessions
- Advances time for woodcutting operations
- Advances time for forge projects
- Processes daily passive romance bonding
- Automatically invokes claim commands when tasks complete

**Examples:**
```
!owner skip 24                  # Skip 24 hours
!owner skip 1.5                 # Skip 1.5 hours (90 minutes)
!owner skip 168                 # Skip 1 week
!owner skip 0.5                 # Skip 30 minutes
```

**Output Examples:**

**When Slayer Task Active:**
```
⏳ Time Warped: Advanced the hunt by 24 hours.
💕 Relationships evolved over 1 day(s) of passive bonding.

⚔️ SLAYER TASK COMPLETE! ⚔️
[Task completion details...]
```

**When Mining Active:**
```
⏳ Time Warped: Advanced mining by 48 hours.

⛏️ MINING OPERATION COMPLETE! ⛏️
[Mining rewards...]
```

**When Nothing Active:**
```
🎮 Nothing to skip in this channel.
```

**Notes:**
- **Local Mode:** Runs per-channel (only affects tasks in the specific channel)
- **Global Mode:** If run in the authorized Owner Channel, it skips time for *all* active tasks across *all* channels simultaneously.
- Processes romance bonding for each full day skipped
- Auto-claims are sequential (slayer → hunting → mining → fishing → woodcutting → forge)
- No cooldown or limit

---

### `!owner wipe_idle`

Globally clears all active idle tasks and forge projects across the entire server.

**Usage:**
```
!owner wipe_idle
```

**What It Does:**
- Instantly deletes all active slayer, hunting, mining, fishing, and woodcutting tasks.
- Instantly deletes all active forge projects.
- Saves the empty state to the database to prevent ghost tasks.
- Does *not* affect inventory, gold, or completed progression.

**Output:**
```
🧹 Sovereign Decree: Globally wiped 12 active idle operations.
```

**Use Cases:**
- Resetting the sandbox after a massive testing session
- Fixing corrupted active states
- Wiping the slate clean for a new campaign season
- Processes romance bonding for each full day skipped
- Auto-claims are sequential (slayer → hunting → mining → fishing → woodcutting → forge)

---

## 🔨 Forge Override

### `!owner start forge <blueprint_id>`

Force-start a forge project without checking material requirements.

**Usage:**
```
!owner start forge <blueprint_id>
```

**Parameters:**
- `blueprint_id` - The blueprint to craft (e.g., `sword_001`)

**What It Does:**
- Bypasses material requirement checks
- Bypasses level requirement checks
- Starts crafting immediately
- Still respects time requirements (use `!owner skip` to fast-forward)

**Examples:**
```
!owner start forge sword_legendary
!owner start forge armor_mythic
```

**Output:**
```
⚡ Sovereign Override: Forge project started (materials bypassed).
```

**Use Cases:**
- Testing new blueprints
- Granting legendary items to players
- Story rewards that bypass normal progression

---

## 🔄 System Management

### `!owner reload <cog_name>`

Hot-reload a cog without restarting the entire bot.

**Usage:**
```
!owner reload <cog_name>
```

**Parameters:**
- `cog_name` - Name of the cog to reload (with or without "cogs." prefix)

**What It Does:**
- Reloads the specified cog module
- Preserves bot state and active tasks
- Applies code changes without downtime
- Loads cog if not already loaded

**Examples:**
```
!owner reload slayer            # Reloads cogs.slayer
!owner reload cogs.mining       # Also works with full module path
!owner reload relationships     # Hot-swap relationship configs
```

**Output:**
```
✅ Reloaded: cogs.slayer
```

**If Not Loaded:**
```
✅ Loaded: cogs.fishing (was not previously loaded)
```

**On Error:**
```
❌ Failed to reload cogs.invalid: No module named 'cogs.invalid'
```

**Available Cogs:**
- `slayer` - Slayer system
- `hunting` - Hunting system
- `mining` - Mining system
- `fishing` - Fishing system
- `woodcutting` - Woodcutting system
- `forge` - Forge/crafting system
- `quests` - Quest system
- `economy` - Shop and trading
- `relationships` - Romance and friendship
- `combat` - Combat encounters
- `characters` - Character management
- `world` - World events
- `owner` - Owner commands (this cog)
- `campfire` - Campfire activities
- `dreams` - Dream sequences
- `alchemy` - Potion brewing
- `gathering` - Resource gathering
- `translation` - Language translation
- `appraisal` - Item identification
- `meta` - Meta commands
- `rules` - Rules reference

**Notes:**
- Changes to Python files take effect immediately after reload
- JSON database changes are loaded automatically (no reload needed)
- Active tasks are preserved during reload

---

## 🔍 Debugging

### `!owner debug`

Display comprehensive debug information about all active systems.

**Usage:**
```
!owner debug
```

**What It Shows:**
- Active slayer tasks across all channels
- Active hunting sessions
- Active mining operations
- Active fishing sessions
- Active woodcutting operations
- Active forge projects
- Current channel information

**Example Output:**
```
🔍 Debug Info:

**Active Slayer Tasks:**
  • #idle-slayer: slayer_003 (started 2026-03-01 10:30:00)

**Active Hunting Tasks:**
  • #idle-hunting: HUNT_005 (started 2026-03-01 12:00:00)

**Active Mining Tasks:**
  • #idle-mining: MINE_001 (started 2026-03-01 09:00:00)

**Active Fishing Tasks:** None

**Active Woodcutting Tasks:** None

**Active Forge Projects:**
  • #the-forge: sword_legendary (started 2026-03-01 08:00:00)

**Current Channel:** #idle-slayer (ID: 1234567890)
```

**Use Cases:**
- Troubleshooting stuck tasks
- Verifying time skip worked correctly
- Checking which channels have active operations
- Monitoring cross-channel activity

---

## 🌍 System Initialization

### `!owner setup`

Automatically create all necessary Discord channels and filesystem directories.

**Usage:**
```
!owner setup
```

**What It Does:**

**Discord Channels Created:**
- `campaign-chat` - Main story channel
- `rumors-chat` - World rumors and hooks
- `off-topic` - Casual RP and tavern banter
- `party-chat` - Party coordination
- `npc-gallery` - NPC dossiers
- `the-forge` - Crafting channel
- `world-events` - Weekly proclamations
- `royal-treasury` - Inventory tracking
- `side-quests` - Quest log
- `images` - Generated images
- `resources` - Rules and reference
- `combat` - Combat encounters
- `idle-slayer` - Slayer grinding
- `weaver-archives` - Owner-only meta channel (private)

**Filesystem Created:**
- `state/` - Active task tracking
- `characters/` - Character JSON files
- `assets/` - Generated images
- `docs/quests/Hard/` - Hard quest files
- `docs/reference/` - Reference documents
- `session_logs/` - Session history

**Example Output:**
```
🛠️ Initializing Sovereignty Infrastructure...
✅ Created Category: 🏰 EMBERHEART
✅ Created Channel: #campaign-chat
✅ Created Channel: #rumors-chat
...
✅ Created Channel: #weaver-archives (PRIVATE)
✨ Setup Complete. 14 Discord channels and 6 filesystem directories established. Glory to the World-Spark.
```

**Notes:**
- Safe to run multiple times (skips existing channels)
- Moves existing channels to the EMBERHEART category
- `#weaver-archives` is private to bot owner only
- Creates `.gitkeep` files in empty directories

---

## 📊 Tick System

### `!owner tick`

Manually trigger the weekly Sovereignty Heartbeat (world state update).

**Usage:**
```
!owner tick
```

**What It Does:**
- Processes weekly world state changes
- Updates kingdom statistics
- Generates proclamation events
- Logs the tick in quest history

**Example Output:**
```
⚡ Invoking the Sovereign Heartbeat...

📊 [THE SOVEREIGN PROCLAMATION]
***The stars have shifted. The kingdom breathes.***

🌍 Week 12 has dawned.
- The treasury swells with 12,450 gold.
- 7 quests have been completed this cycle.
- Relationship bonds have deepened across the realm.
- The Goblin threat diminishes (47% completion).

*Glory to the World-Spark.*
```

**Notes:**
- Normally runs automatically every 7 days
- Manual trigger useful for testing or story beats
- Logged to quest engine as a "SYSTEM" deed

---

## 🔧 Utility Commands

### `!purge`

Clear channel message history (requires manage_messages permission).

**Usage:**
```
!purge
```

**What It Does:**
- Deletes last 100 messages in channel
- Shows confirmation message
- Auto-deletes confirmation after 3 seconds

**Output:**
```
🧹 Channel Purged.
```

**Notes:**
- Not strictly an owner command (requires manage_messages permission)
- Useful for cleaning up test spam
- Cannot purge messages older than 14 days (Discord limitation)

---

## 💰 Economy Commands

### `!owner give <char_id> <amount> <item_name>`

Directly inject items into a character's inventory.

**Usage:**
```
!owner give <char_id> <amount> <item_name>
```

**Parameters:**
- `char_id` - Character ID (e.g., `PC-01`, `PC-02`)
- `amount` - Number of items to give (integer)
- `item_name` - Full name of the item (supports spaces)

**Examples:**
```
!owner give PC-01 10 Iron Ore
!owner give PC-02 1 Hammer of the Forge-Bane
!owner give PC-01 3 Elder Brain Fragment
!owner give PC-03 5 Potion of Acid Resistance
```

**Output:**
```
✅ Sovereign Grant: Gave 10x Iron Ore to Kaelrath (PC-01).
```

**Notes:**
- Uses the same storage path as `sync_loot` for full consistency
- Items appear immediately in `!stats` inventory
- Item names are case-sensitive and stored exactly as typed

---

### `!owner gold <char_id> <amount>`

Add gold to a character's balance.

**Usage:**
```
!owner gold <char_id> <amount>
```

**Parameters:**
- `char_id` - Character ID (e.g., `PC-01`)
- `amount` - Amount of gold to add (integer, can be negative to remove)

**Examples:**
```
!owner gold PC-01 5000
!owner gold PC-02 100000
!owner gold PC-01 -500              # Remove gold
```

**Output:**
```
✅ Sovereign Grant: Added 5,000 gold to Kaelrath (PC-01). New balance: 12,450 gold.
```

**Notes:**
- Can use negative values to deduct gold
- Shows updated balance after the transaction
- Persisted immediately to character state

---

## 💡 Tips & Best Practices

### Time Skip Strategy

**Per-Channel Workflow:**
```
# In #idle-slayer
!slayer task slayer_005
!owner skip 24

# In #idle-mining
!mine node MINE_003
!owner skip 24

# In #the-forge
!forge start sword_legendary
!owner skip 12
```

**Multi-Task Skip:**
```
# Start tasks in multiple channels
# Navigate to each channel and skip time
# Tasks accumulate independently
```

### Hot Reload Workflow

When editing code:
```
1. Edit cog Python file (e.g., cogs/slayer.py)
2. Save changes
3. Run: !owner reload slayer
4. Test immediately - no restart needed!
```

### Debugging Stuck Tasks

```
!owner debug                    # Check what's active
# Navigate to the problem channel
!owner skip 0.1                # Tiny skip to test
!slayer claim                   # Manual claim if needed
```

### Setup Best Practices

```
!owner setup                    # Run once on new server
# Customize channel topics/permissions as needed
# Bot will respect existing channels
```

---

## 🚨 Important Notes

### Safety & Permissions

- **Owner-only:** These commands only work for the configured bot owner
- **No cooldowns:** Commands have no rate limits or cooldowns
- **Irreversible:** Time skips cannot be undone
- **State persistence:** All changes are saved to disk immediately

### Known Limitations

- `!owner skip` works per-channel only (must navigate to each channel)
- Cannot skip backwards in time
- Active tasks cap at 24 hours of accumulated progress
- Forge projects still require time even with override start

### Error Handling

**If a command fails:**
```
❌ Failed to reload cogs.example: [error message]
```

**Common Errors:**
- **Syntax errors in code:** Fix the Python file, then retry reload
- **Missing engine:** Check that the target cog is properly initialized
- **Permission errors:** Ensure bot has proper Discord permissions

---

## 📋 Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `!owner skip <hours>` | Time travel | `!owner skip 24` |
| `!owner start forge <id>` | Force craft | `!owner start forge sword_legendary` |
| `!owner reload <cog>` | Hot reload | `!owner reload slayer` |
| `!owner debug` | System info | `!owner debug` |
| `!owner setup` | Initialize server | `!owner setup` |
| `!owner wipe_idle` | Global reset | `!owner wipe_idle` |
| `!owner tick` | Manual heartbeat | `!owner tick` |
| `!owner give <id> <n> <item>` | Give items | `!owner give PC-01 5 Iron Ore` |
| `!owner gold <id> <amount>` | Add gold | `!owner gold PC-01 5000` |

---

**Last Updated:** March 1, 2026
**Permission Level:** Bot Owner Only
