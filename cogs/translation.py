"""
Arcane Translation Minigame
Players find encrypted texts and use resources to decode them via AI translators
"""
import discord
from discord.ext import commands
import logging
import random
import base64

logger = logging.getLogger("Cog_Translation")


class TranslationCog(commands.Cog):
    """
    Arcane translation puzzle system
    """

    def __init__(self, bot):
        self.bot = bot
        self.active_puzzles = {}  # puzzle_id -> puzzle_data
        self._create_sample_puzzles()

    def _create_sample_puzzles(self):
        """Create sample encrypted puzzles"""
        puzzles = [
            {
                "id": "VAULT_001",
                "title": "The Sealed Vault",
                "encrypted_text": "VGhlIHZhdWx0IG9wZW5zIG9ubHkgd2hlbiB0aGUgbW9vbiBpcyBmdWxsIGFuZCB0aGUgYmxvb2Qgb2YgYSBwaG9lbml4IGlzIHNwcmVhZCB1cG9uIHRoZSBkb29yLiBXaXRoaW46IHRoZSBDcm93biBvZiBFdGVybmFsIE5pZ2h0Lg==",
                "solution": "The vault opens only when the moon is full and the blood of a phoenix is spread upon the door. Within: the Crown of Eternal Night.",
                "language": "Ancient Elvish",
                "cost_per_fragment": 50  # Lore Points or Gold
            },
            {
                "id": "PROPHECY_002",
                "title": "The Dark Prophecy",
                "encrypted_text": "V2hlbiB0aHJlZSBzdGFycyBhbGlnbiwgdGhlIERlYWQgS2luZyByaXNlcy4gT25seSB0aGUgQmxhZGUgRm9yZ2VkIGluIERyYWdvbmZpcmUgY2FuIHN0cmlrZSBoaXMgaGVhcnQu",
                "solution": "When three stars align, the Dead King rises. Only the Blade Forged in Dragonfire can strike his heart.",
                "language": "Necromantic Runes",
                "cost_per_fragment": 100
            }
        ]

        for puzzle in puzzles:
            self.active_puzzles[puzzle["id"]] = puzzle
            # Track progress
            puzzle["revealed_words"] = set()
            puzzle["full_revealed"] = False

    @commands.command(name="find_cipher", hidden=True)
    async def find_cipher(self, ctx):
        """
        (DM/Admin only) Spawn a random encrypted message puzzle.
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ This command is for DMs only.")
            return

        puzzle_id = random.choice(list(self.active_puzzles.keys()))
        puzzle = self.active_puzzles[puzzle_id]

        msg = f"""
╔═══════════════════════════════════════╗
║  📜 **ANCIENT TEXT DISCOVERED** 📜    ║
╚═══════════════════════════════════════╝

*During your quest, you discover a sealed scroll covered in strange symbols...*

**{puzzle['title']}**

```
{puzzle['encrypted_text']}
```

**Language:** {puzzle['language']} (Encrypted)

*This text is written in an ancient tongue. You'll need a translator to decode it.*

Use `!translate {puzzle_id} [fragment]` to decode pieces of it.
Cost: {puzzle['cost_per_fragment']} Gold per fragment
"""

        await ctx.send(msg)

    @commands.command(name="translate")
    async def translate(self, ctx, puzzle_id: str = None, *, fragment: str = None):
        """
        Translate a fragment of an encrypted puzzle.
        Costs gold/resources. The AI translator may struggle!
        Usage: !translate VAULT_001 "first three words"
        """
        if not puzzle_id:
            await ctx.send(
                "❌ Usage: `!translate <puzzle_id> <fragment>`\n"
                "Example: `!translate VAULT_001 beginning`"
            )
            return

        puzzle_id = puzzle_id.upper()

        if puzzle_id not in self.active_puzzles:
            await ctx.send(f"❌ Puzzle **{puzzle_id}** not found. Check available puzzles with `!puzzles`.")
            return

        puzzle = self.active_puzzles[puzzle_id]

        # Check if player has enough gold
        cost = puzzle["cost_per_fragment"]

        try:
            from core.storage import load_character_state

            character_id = "PC-01"
            char_state = load_character_state(character_id)

            if not char_state:
                await ctx.send("❌ Character state not found.")
                return

            # For now, just assume player has gold
            # TODO: Implement actual gold deduction from SETTLEMENT_STATE.json

            # Generate partial translation via AI
            translation_result = await self._translate_fragment(puzzle, fragment or "beginning")

            # Update revealed words
            # (Simplified - in production, track which words are revealed)

            msg = f"""
╔═══════════════════════════════════════╗
║  🔮 **TRANSLATION ATTEMPT** 🔮         ║
╚═══════════════════════════════════════╝

*The translator squints at the ancient script, struggling with the archaic symbols...*

{translation_result['dialogue']}

**Partial Translation:**
> {translation_result['partial_text']}

**Cost:** {cost} Gold (deducted from Kingdom Treasury)

{'✨ **Translation complete!** You now understand the full message!' if translation_result['complete'] else '*The translator needs more time and resources to decode the rest...*'}
"""

            await ctx.send(msg)

            if translation_result['complete']:
                # Mark as fully revealed
                puzzle["full_revealed"] = True

        except Exception as e:
            logger.error(f"Failed to translate: {e}", exc_info=True)
            await ctx.send("❌ Translation failed. Please try again.")

    async def _translate_fragment(self, puzzle: dict, fragment_request: str) -> dict:
        """
        Translate a fragment using AI

        Args:
            puzzle: Puzzle data
            fragment_request: What part the player wants translated

        Returns:
            Translation result with partial text
        """
        try:
            # Decode the base64 solution
            solution = puzzle["solution"]

            # Simulate progressive translation
            if "beginning" in fragment_request.lower() or "start" in fragment_request.lower():
                # Reveal first 30%
                words = solution.split()
                revealed = " ".join(words[:len(words)//3]) + " [...?]"
                complete = False
            elif "middle" in fragment_request.lower():
                words = solution.split()
                start = len(words)//3
                end = 2*len(words)//3
                revealed = "[...] " + " ".join(words[start:end]) + " [...?]"
                complete = False
            elif "end" in fragment_request.lower():
                words = solution.split()
                revealed = "[...] " + " ".join(words[2*len(words)//3:])
                complete = False
            elif "all" in fragment_request.lower() or "full" in fragment_request.lower():
                revealed = solution
                complete = True
            else:
                # Default: reveal a random chunk
                words = solution.split()
                chunk_size = max(3, len(words)//4)
                start = random.randint(0, max(0, len(words) - chunk_size))
                revealed = "[...] " + " ".join(words[start:start+chunk_size]) + " [...]"
                complete = False

            # Generate translator dialogue via AI
            if self.bot.llm and self.bot.llm.is_available():
                prompt = f"""You are an ancient translator struggling to decode cryptic text. Generate 1-2 sentences of dialogue.

The text is in {puzzle['language']} and you're attempting to translate: "{fragment_request}"

You should sound like you're piecing together fragments, uncertain, consulting old texts.

Example: "Hmm, this symbol here... yes, I've seen it before in the Codex of Shadows. It speaks of a vault, I think. But the grammar is archaic - give me a moment..."

Your dialogue:"""

                dialogue = await self.bot.llm.async_generate(prompt=prompt, temperature=0.8, max_tokens=80)
                dialogue = dialogue.strip() if dialogue else "I'm working on the translation..."
            else:
                dialogue = "I'm deciphering the ancient script... this may take time."

            return {
                "dialogue": dialogue,
                "partial_text": revealed,
                "complete": complete
            }

        except Exception as e:
            logger.error(f"Failed to translate fragment: {e}")
            return {
                "dialogue": "The symbols are too faded to read clearly...",
                "partial_text": "[Illegible]",
                "complete": False
            }

    @commands.command(name="puzzles")
    async def list_puzzles(self, ctx):
        """List all available encrypted puzzles"""
        if not self.active_puzzles:
            await ctx.send("📜 No encrypted texts have been discovered yet.")
            return

        embed = discord.Embed(
            title="📜 Encrypted Texts",
            description="*Ancient mysteries waiting to be decoded...*",
            color=0x9B59B6
        )

        for puzzle_id, puzzle in self.active_puzzles.items():
            status = "✅ Fully Translated" if puzzle.get("full_revealed") else "🔒 Partially Encrypted"
            embed.add_field(
                name=f"{puzzle_id}: {puzzle['title']}",
                value=f"Language: {puzzle['language']}\nCost: {puzzle['cost_per_fragment']} Gold/fragment\nStatus: {status}",
                inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TranslationCog(bot))
