import logging
import json
import re
import difflib
from pathlib import Path
from collections import Counter

from discord.ext import commands

from core.config import ROOT_DIR, DB_DIR
from core.routing import require_channel

logger = logging.getLogger("Cog_Rules")
DND_INDEX_PATH = ROOT_DIR / "docs" / "DND_REFERENCE_INDEX.json"


def _build_reference_candidates(raw_path: str) -> list[Path]:
    raw = str(raw_path or "").strip().replace("\\", "/")
    if not raw:
        return []

    raw = raw.lstrip("./")
    candidates: list[Path] = []

    def add(path: Path):
        if path not in candidates:
            candidates.append(path)

    add(ROOT_DIR / Path(raw))

    trimmed = raw
    for prefix in ("EmberHeart: Origins/", "EmberHeart/"):
        if trimmed.lower().startswith(prefix.lower()):
            trimmed = trimmed[len(prefix):]
            break

    add(ROOT_DIR / Path(trimmed))

    low = trimmed.lower()
    docs_marker = "/docs/"
    if docs_marker in low:
        idx = low.find(docs_marker)
        docs_rel = trimmed[idx + len(docs_marker):]
        add(ROOT_DIR / "docs" / Path(docs_rel))

    if low.startswith("docs/"):
        add(ROOT_DIR / Path(trimmed))

    add(ROOT_DIR / "docs" / Path(trimmed).name)
    return candidates


def _resolve_reference_path(raw_path: str) -> Path | None:
    for candidate in _build_reference_candidates(raw_path):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


class RulesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from core.transport import transport
        self.transport = transport

    @commands.command()
    @require_channel("resources")
    async def rule(self, ctx, *, query: str):
        """AI-powered 5e rules/spell reference. Searches local D&D index first."""
        channel = getattr(ctx, "target_channel", ctx.channel)
        normalized_query = re.sub(r"[^a-zA-Z0-9\s]", "", query.lower()).strip()

        if DND_INDEX_PATH.exists():
            index = json.loads(DND_INDEX_PATH.read_text(encoding="utf-8"))

            if normalized_query in index:
                entry = index[normalized_query]
                file_path = _resolve_reference_path(entry.get("path", ""))
                if file_path:
                    content = file_path.read_text(encoding="utf-8")
                    await self.transport.send(channel, f"📚 **Reference Found: {entry['title']}**\n{content}", "DM")
                    return

            matches = [k for k in index.keys() if normalized_query in k]
            if not matches:
                matches = difflib.get_close_matches(normalized_query, index.keys(), n=5, cutoff=0.6)

            if matches:
                if len(matches) == 1:
                    entry = index[matches[0]]
                    file_path = _resolve_reference_path(entry.get("path", ""))
                    if file_path:
                        content = file_path.read_text(encoding="utf-8")
                        await self.transport.send(channel, f"📚 **Reference Found ({matches[0]}): {entry['title']}**\n{content}", "DM")
                        return
                else:
                    suggestions = ", ".join([f"`{index[m]['title']}`" for m in matches])
                    await self.transport.send(channel, f"🔍 **Multiple matches found for '{query}':**\n{suggestions}\n\n*Try being more specific!*")
                    return

        await self.transport.send(channel, "🔍 Concept not found in static rules. Ask the DM AI directly in the main channel.", "DM")




async def setup(bot):
    await bot.add_cog(RulesCog(bot))
