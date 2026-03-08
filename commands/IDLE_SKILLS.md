# Idle Skills Command Reference

Complete reference for all idle/passive skill systems in EmberHeart.

---

## 📋 Idle Skills Overview

EmberHeart features 5 idle skill systems that accumulate progress over time:

| Skill | Channel ID | Focus | Primary Rewards |
|-------|-----------|-------|-----------------|
| **Slayer** | TBD | Combat/XP | XP, Combat Loot, Boss Drops |
| **Hunting** | TBD | Resources | Pelts, Meat, Crafting Materials |
| **Mining** | #idle-mining | Ores/Gems | Ores, Gemstones, Forge Materials |
| **Fishing** | #idle-fishing | Food/Treasure | Fish, Pearls, Underwater Loot |
| **Woodcutting** | #idle-woodcutting | Lumber | Wood, Sap, Seeds, Crafting Materials |

---

## ⚔️ Slayer Commands

### Channel: #idle-slayer

**Commands:**
```
!slayer list                    # View all slayer tasks
!slayer task <task_id>         # Start a slayer task
!slayer claim                   # Claim rewards
!slayer stop                    # Stop current task
!slayer info <task_id>         # View task details
```

**Example Usage:**
```
!slayer list                    # Browse available monsters
!slayer task slayer_001        # Start killing Goblins
# ... wait for time to pass ...
!slayer claim                   # Collect your kills, XP, and loot
```

**Slayer Tasks (8 tiers):**
1. **SLAYER_001** - Goblin Extermination (Very Easy)
2. **SLAYER_002** - Wolf Pack (Easy)
3. **SLAYER_003** - Bandit Camp (Medium)
4. **SLAYER_004** - Undead Crypt (Medium-Hard)
5. **SLAYER_005** - Drake Nest (Hard)
6. **SLAYER_006** - Demon Portal (Very Hard)
7. **SLAYER_007** - Ancient Dragon (Extreme)
8. **SLAYER_008** - Void Titan (Legendary)

**Rewards:** XP, Gold, Weapons, Armor, Boss Materials

**Romance Bonding:** ✅ Yes - Combat bonding scales with kill count

---

## 🏹 Hunting Commands

### Channel: #idle-hunting

**Commands:**
```
!hunt list                      # View all hunting grounds
!hunt start <hunt_id>          # Start hunting
!hunt claim                     # Claim rewards
!hunt stop                      # Stop hunting
!hunt info <hunt_id>           # View ground details
```

**Example Usage:**
```
!hunt list                      # Browse hunting grounds
!hunt start HUNT_001           # Hunt rabbits in Meadow
# ... wait for time to pass ...
!hunt claim                     # Collect pelts and meat
```

**Hunting Grounds (8 tiers):**
1. **HUNT_001** - Meadow Rabbits (Very Easy)
2. **HUNT_002** - Forest Deer (Easy)
3. **HUNT_003** - Mountain Boar (Medium)
4. **HUNT_004** - Plains Elk (Medium-Hard)
5. **HUNT_005** - Tundra Wolves (Hard)
6. **HUNT_006** - Dire Bears (Very Hard)
7. **HUNT_007** - Wyverns (Extreme)
8. **HUNT_008** - Phoenix (Legendary)

**Rewards:** Pelts, Meat, Bones, Feathers, Rare Hides

**Romance Bonding:** ✅ Yes - Combat bonding scales with kill count

---

## ⛏️ Mining Commands

### Channel: #idle-mining

**Commands:**
```
!mine list                      # View all ore veins
!mine node <node_id>           # Start mining
!mine claim                     # Claim rewards
!mine stop                      # Stop mining
!mine info <node_id>           # View vein details
```

**Example Usage:**
```
!mine list                      # Browse ore veins
!mine node MINE_001            # Mine copper
# ... wait for time to pass ...
!mine claim                     # Collect ores and gems
```

**Ore Veins (8 tiers):**
1. **MINE_001** - Copper Vein (Very Easy)
2. **MINE_002** - Iron Deposit (Easy)
3. **MINE_003** - Silver Vein (Medium)
4. **MINE_004** - Gold Vein (Medium-Hard)
5. **MINE_005** - Mithril Deposit (Hard)
6. **MINE_006** - Adamantine Vein (Very Hard)
7. **MINE_007** - Orichalcum Deposit (Extreme)
8. **MINE_008** - Starstone Vein (Legendary)

**Rewards:** Ores, Gemstones, Crystals, Fossils

**Romance Bonding:** ❌ No - Resource gathering activity

---

## 🎣 Fishing Commands

### Channel: #idle-fishing

**Commands:**
```
!fish list                      # View all fishing spots
!fish spot <spot_id>           # Start fishing
!fish claim                     # Claim rewards
!fish stop                      # Stop fishing
!fish info <spot_id>           # View spot details
```

**Example Usage:**
```
!fish list                      # Browse fishing spots
!fish spot FISH_001            # Fish at village pond
# ... wait for time to pass ...
!fish claim                     # Collect fish and treasures
```

**Fishing Spots (8 tiers):**
1. **FISH_001** - Village Pond (Very Easy)
2. **FISH_002** - Forest Stream (Easy)
3. **FISH_003** - Mountain Lake (Medium)
4. **FISH_004** - Coastal Waters (Medium-Hard)
5. **FISH_005** - Deep Sea (Hard)
6. **FISH_006** - Sunken Ruins (Very Hard)
7. **FISH_007** - Maelstrom Waters (Extreme)
8. **FISH_008** - Abyssal Trench (Legendary)

**Rewards:** Fish, Pearls, Kelp, Shells, Underwater Treasures

**Romance Bonding:** ❌ No - Resource gathering activity

---

## 🪓 Woodcutting Commands

### Channel: #idle-woodcutting

**Commands:**
```
!chop list                      # View all tree types
!chop tree <tree_id>           # Start chopping
!chop claim                     # Claim rewards
!chop stop                      # Stop chopping
!chop info <tree_id>           # View tree details
```

**Example Usage:**
```
!chop list                      # Browse tree types
!chop tree WOOD_001            # Chop pine trees
# ... wait for time to pass ...
!chop claim                     # Collect lumber
```

**Tree Types (8 tiers):**
1. **WOOD_001** - Pine Grove (Very Easy)
2. **WOOD_002** - Oak Forest (Easy)
3. **WOOD_003** - Maple Stand (Medium)
4. **WOOD_004** - Ash Grove (Medium-Hard)
5. **WOOD_005** - Ironwood Forest (Hard)
6. **WOOD_006** - Ancient Oak (Very Hard)
7. **WOOD_007** - Elderwood Grove (Extreme)
8. **WOOD_008** - World Tree Sapling (Legendary)

**Rewards:** Lumber, Sap, Seeds, Bark, Rare Woods

**Romance Bonding:** ❌ No - Resource gathering activity

---

## 🍳 Cooking Commands

### Channel: #idle-cooking

**Commands:**
```
!cook list                      # View all recipes
!cook recipe <recipe_id>        # Start preparing a meal
!cook claim                     # Serve finished dishes
!cook stop                      # Put out the fire
```

**Example Usage:**
```
!cook list                      # Look at the menu
!cook recipe COOK_001           # Start campfire roasting
# ... wait for time to pass ...
!cook claim                     # Collect cooked meat and XP
```

**Recipe Progression (8 tiers):**
1. **COOK_001** - Campfire Roasting (Lv 1)
2. **COOK_002** - Forager's Stew (Lv 5)
3. **COOK_003** - Pan-Fried River Fish (Lv 10)
4. **COOK_004** - Spiced Desert Skewers (Lv 15)
5. **COOK_005** - Elvish Wafer Baking (Lv 20)
6. **COOK_006** - Abyssal Seafood Boil (Lv 25)
7. **COOK_007** - Mithril-Seared Steak (Lv 35)
8. **COOK_008** - Dragon's Breath Banquet (Lv 50)

**Rewards:** Experience (Chef), Cooked Foods, Rare Spices

**Romance Bonding:** ✅ Yes - Shared cooking duties build rapport.

---

## ⏱️ Time Mechanics

### How Time Works
- Each activity has a "time_to_kill" (or time per action) in seconds
- Activities accumulate progress in real-time
- Maximum 24 hours of progress can accumulate (prevents infinite stacking)

### Time Skip (Owner Only)
```
!owner skip <hours>
```

- Advances time for ALL active idle activities in the channel
- Processes daily passive romance bonding (for combat skills)
- Automatically triggers claim commands when complete
- No limit on hours (owner authority)

**Example:**
```
!owner skip 24                  # Skip 24 hours in this channel
```

---

## 🎯 Skill Strategy Guide

### Combat vs. Resource Skills

**Combat Skills (Slayer, Hunting):**
- Grant XP and levels
- Trigger romance bonding with NPCs
- Drop weapons, armor, and combat materials
- Scale rewards with kill count

**Resource Skills (Mining, Fishing, Woodcutting):**
- No XP or romance bonding
- Focus on gathering materials for crafting
- Essential for forge projects and alchemy
- Steady, reliable income

### Optimal Workflow

1. **Start Multiple Activities**
   - Start a combat activity (slayer/hunting) in one channel
   - Start resource gathering in another channel
   - Both accumulate simultaneously!

2. **Time Skip Strategy** (Owner)
   - Navigate to channel with active task
   - Use `!owner skip <hours>` to fast-forward
   - Bot auto-claims when tasks complete
   - Repeat for other channels

3. **Resource Priorities**
   - **Early Game:** Mining (copper/iron for forge)
   - **Mid Game:** Fishing (food for buffs), Woodcutting (fuel)
   - **Late Game:** All resources for legendary crafting

---

## 🍳 Cooking Commands

### Channel: #idle-cooking

**Commands:**
```
!cook list                      # View all recipes
!cook recipe <id> [solo]        # Start cooking
!cook claim                     # Claim meals and stop
!cook stop                      # Stop cooking
```

**Mechanics:**
- **Consumes RAW INGREDIENTS** from the Party Inventory (e.g., Raw Meat, River Salmon).
- Produces Cooked Meals which heal HP or provide buffs.
- If the party runs out of required ingredients, the fire goes out and no more meals are produced.

---

## 🧵 Crafting Commands

### Channel: #idle-crafting

**Commands:**
```
!craft list                     # View all crafting projects
!craft recipe <id> [solo]       # Start crafting gear
!craft claim                    # Claim finished items
!craft stop                     # Stop crafting
```

**Mechanics:**
- Converts gathered resources (Wood, Pelts, Gems) into usable gear (Arrows, Leather Armor, Cut Gems).
- At high tiers, produces Legendary Artifacts like the *Amulet of the Eclipse*.
- **Consumes RESOURCES** directly from the Party Inventory.

---

## ⚒️ Smithing Commands

### Channel: #idle-smithing

**Commands:**
```
!smith list                     # View all forging blueprints
!smith recipe <id> [solo]       # Start striking the anvil
!smith claim                    # Claim finished ingots/weapons
!smith stop                     # Empty the forge
```

**Mechanics:**
- Smelts raw ores from Mining (Copper, Iron, Mithril, Adamantine) into Ingots.
- Forges Ingots into Armaments (Longswords, Vanguard Plate).
- **Consumes ORE & COAL** directly from the Party Inventory.

4. **Combat Priorities**
   - **Early Game:** Slayer (XP grinding)
   - **Mid Game:** Hunting (pelts for armor, meat for cooking)
   - **Late Game:** High-tier slayer tasks (legendary drops)

---

## 📊 Reward Tables

### Drop Mechanics
- Each kill/action rolls against a drop table
- Multiple items can drop per action (max_drops_per_kill)
- Rarity affects drop chance (0.01 = 1%, 0.95 = 95%)
- Higher-tier activities have better loot tables

### Shared Loot (Party System)
When claiming with a party:
- XP is divided equally among party members
- Loot is distributed to random party members
- Romance bonding applies to each character individually

**Example Claim Output:**
```
⚔️ SLAYER TASK COMPLETE! ⚔️
Task: Goblin Extermination
Kills: 72

📊 XP Breakdown:
  • Kaelrath: 288 XP
  • Silvy: 288 XP
  • Thalindra: 288 XP

🎁 Loot Breakdown:
  • Kaelrath: Goblin Dagger, Leather Scraps (x2)
  • Silvy: Goblin Ear, Copper Coin (x5)
  • Thalindra: Rusty Sword

💕 Romance Bonding:
  • Kaelrath ↔ Thalindra: +1 from 72 kills
```

---

## 🔍 Debug & Admin

### Owner Debug Command
```
!owner debug
```

**Shows:**
- All active slayer tasks across channels
- All active hunting sessions
- All active mining operations
- All active fishing sessions
- All active woodcutting operations
- Active forge projects

---

## 💡 Tips & Tricks

1. **Parallel Processing:** Run multiple idle skills simultaneously in different channels
2. **Overnight Progress:** Start a task before logging off - it accumulates while you're away (max 24hrs)
3. **Romance Optimization:** Use slayer/hunting for relationship building
4. **Material Farming:** Use mining/fishing/woodcutting for forge projects
5. **Task Difficulty:** Higher-tier tasks are slower but give better rewards
6. **Hot Reload:** Owner can use `!owner reload <cog>` to update skill configs without restarting

---

**Last Updated:** March 1, 2026
