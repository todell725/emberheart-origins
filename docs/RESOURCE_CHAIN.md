# EmberHeart: Origins — Resource Chain

This document illustrates how resources flow from raw gathering (Mining, Fishing, Woodcutting, Hunting) to processing (Smithing, Cooking) to final products (Crafting, Forge Catalog).

Because EmberHeart: Origins is data-driven, a material must exist in a gathering DB before it can be used as an ingredient in a processing DB.

---

## 1. The Metallurgical Chain (Mining → Smithing → Forge)

**Raw Ores (MINING_DB)**
- Surface Clay
- Ashiron Vein
- Flame-Hardened Metal
- Orichalcum
- Memory Ore
- Voidsteel
- God-Touched Stone

**Processed Ingots (IDLE_SMITHING_DB)**
- *Requires: Raw Ores + Coal*
- Ashiron Bar
- Flame-Hardened Plate
- Orichalcum Ingot
- Voidsteel Bar
- Godsteel Ingot

**Finished Armaments (FORGE_CATALOG & IDLE_CRAFTING_DB)**
- *Requires: Processed Ingots + Wood/Leather*
- Ashiron Shortsword / Armor
- Orichalcum War Axe / Golem Chassis
- Voidsteel Greataxe
- Memory-Forged Blade
- Godsteel Greatsword (Flamekeeper's Regalia)

---

## 2. The Agrarian Chain (Hunting/Fishing/Farming → Cooking)

**Raw Ingredients (HUNTING_DB & FISHING_DB & Base Farming)**
- Emberfield Hare Meat
- Flame Stag Venison
- Wild Wyrmling Meat
- Sacred Salmon / Fae-Touched Pike (Fishing)
- Flamewheat / Ashbarley (Farming abstraction)
- Emberroot / Dreamfruit (Gathering abstraction)

**Prepared Meals (IDLE_COOKING_DB)**
- *Requires: Raw Ingredients + Fire/Time*
- Flamewheat Bread
- Ashbarley Stew
- Shimmerplum Tart
- Emberroot Roast
- Flame-Seared Venison
- Dreamfruit Elixir
- Divine Feast (Requires Wyrmling + Fae Fish + Dreamfruit)

---

## 3. The Arcane/Woodcraft Chain (Woodcutting/Slayer → Crafting)

**Raw Materials (WOODCUTTING_DB & IDLE_SLAYER_DB)**
- Firesapling / Ashbark / Flamewood / Dreamwood (Woodcutting)
- Shards / Memory Coils / Void Dust / Fae Silk (Slayer monster drops)

**Finished Goods (IDLE_CRAFTING_DB)**
- *Requires: Wood + Monster Hooks + Metals*
- Ashbark Bow
- Flamewood Staff
- Shard-Bark Shield (Requires Void Dust)
- Dreamforged Amulet (Requires Memory Coils + Dreamwood)
- Golem Core Assembly (Requires Orichalcum + Shards)

---

## Modding the Chain

If you want to add a new Tier 8 weapon (e.g., "Star-Iron Halberd"):
1. Add `ore_star_iron` to `MINING_DB.json`.
2. Add a recipe for `ingot_star_iron` (requires `ore_star_iron`) to `IDLE_SMITHING_DB.json`.
3. Add the `Star-Iron Halberd` (requires `ingot_star_iron` and `Flamewood`) to `FORGE_CATALOG.json`.
