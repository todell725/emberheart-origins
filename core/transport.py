"""
Transport API for EmberHeart: Origins
Unified webhook-based message delivery
Ported from Claudes-EmberHeart
"""
import aiohttp
import asyncio
import json
import logging
import re
from pathlib import Path

import discord
from discord import Webhook

from core.config import IDENTITIES, resolve_identity

logger = logging.getLogger("EH_Transport")

# Webhook cache persisted to disk so we survive bot restarts
_CACHE_PATH = Path(__file__).resolve().parent.parent / "state" / "WEBHOOK_CACHE.json"


def sanitize_text(text: str) -> str:
    """Clean up smart characters and common encoding artifacts for logs and Discord."""
    if not text: return ""
    replacements = {
        "\u201c": '"', "\u201d": '"',
        "\u2018": "'", "\u2019": "'",
        "\u2014": "--", "\u2013": "-",
        "\u2026": "..."
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


class TransportAPI:
    """Unified API for sending messages to Discord via webhooks or fallback sends."""

    def __init__(self):
        self._cache = {}
        self._npc_cache = {}
        self._load_npc_cache()

    def _npc_slug(self, npc_name: str) -> str:
        """Normalize NPC name to a safe webhook slug."""
        _identity, canonical_name, char_id = resolve_identity(speaker=npc_name, speaker_id="")

        prefix = "EH"
        if char_id.upper().startswith("PC-"):
            prefix = "PC"
        elif char_id.upper().startswith("DM-"):
            prefix = "DM"

        display_name = canonical_name or str(npc_name)
        name_slug = re.sub(r"[^a-zA-Z0-9 ]", "", display_name).strip()

        if char_id:
            id_slug = re.sub(r"[^A-Za-z0-9-]", "", char_id).upper().replace("-", "")
            return f"{prefix}-{name_slug[:18]} {id_slug}"[:80]

        return f"{prefix}-{name_slug[:24]}"

    def _is_valid_webhook_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        if not url.startswith("https://discord.com/api/webhooks/"):
            return False
        return not url.endswith("/None")

    def _load_npc_cache(self):
        try:
            if _CACHE_PATH.exists():
                data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
                cleaned = {}
                for raw_key, raw_url in data.items():
                    key = tuple(raw_key.split("|"))
                    if self._is_valid_webhook_url(raw_url):
                        cleaned[key] = raw_url
                self._npc_cache = cleaned
                logger.info(f"Loaded {len(self._npc_cache)} cached NPC webhooks.")

                if len(cleaned) != len(data):
                    self._save_npc_cache()
        except Exception as e:
            logger.warning(f"Could not load webhook cache: {e}")

    def _save_npc_cache(self):
        try:
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            serializable = {
                "|".join(k): v
                for k, v in self._npc_cache.items()
                if self._is_valid_webhook_url(v)
            }
            from core.storage import save_json
            save_json(_CACHE_PATH.name, serializable)
        except Exception as e:
            logger.warning(f"Could not save webhook cache: {e}")

    async def _get_npc_webhook(self, channel, npc_name: str, session):
        """Get or create a dedicated webhook for a specific NPC in a channel."""
        npc_slug = self._npc_slug(npc_name)
        key = (str(channel.id), npc_slug)

        cached_url = self._npc_cache.get(key)
        if cached_url and self._is_valid_webhook_url(cached_url):
            try:
                return Webhook.from_url(cached_url, session=session)
            except Exception:
                self._npc_cache.pop(key, None)
                self._save_npc_cache()
        elif key in self._npc_cache:
            self._npc_cache.pop(key, None)
            self._save_npc_cache()

        try:
            existing_hooks = await channel.webhooks()
            wh = next((w for w in existing_hooks if w.name == npc_slug), None)
            if wh and getattr(wh, "token", None):
                if self._is_valid_webhook_url(wh.url):
                    self._npc_cache[key] = wh.url
                    self._save_npc_cache()
                return wh

            if wh and not getattr(wh, "token", None):
                try:
                    await wh.delete(reason=f"Rebuilding tokenless webhook for {npc_name}")
                except Exception:
                    pass

            eh_hooks = [w for w in existing_hooks if w.name and w.name.startswith("EH-")]
            if len(existing_hooks) >= 8 and eh_hooks:
                oldest = sorted(eh_hooks, key=lambda w: w.id)[0]
                await oldest.edit(name=npc_slug, reason=f"NPC slot reused for {npc_name}")
                if getattr(oldest, "token", None):
                    wh = oldest
                else:
                    try:
                        await oldest.delete(reason=f"Rebuilding tokenless webhook for {npc_name}")
                    except Exception:
                        pass
                    wh = await channel.create_webhook(name=npc_slug, reason=f"NPC webhook for {npc_name}")
            else:
                wh = await channel.create_webhook(name=npc_slug, reason=f"NPC webhook for {npc_name}")

            if wh and getattr(wh, "token", None) and self._is_valid_webhook_url(wh.url):
                self._npc_cache[key] = wh.url
                self._save_npc_cache()

            logger.info(f"Created NPC webhook '{npc_slug}' in #{channel.name}")
            return wh

        except discord.Forbidden:
            logger.warning(f"No Manage Webhooks permission in #{channel.name}.")
            return None
        except Exception as e:
            logger.warning(f"Could not get NPC webhook for '{npc_name}' in #{channel.name}: {e}")
            return None

    async def send_as_npc(self, channel, npc_name: str, content: str, avatar_url: str = None, wait: bool = False):
        """Send a message impersonating a specific NPC via dedicated webhook."""
        content = sanitize_text(content)
        if not content:
            return

        identity, canonical_name, _canonical_id = resolve_identity(speaker=npc_name, speaker_id="")
        if canonical_name:
            npc_name = canonical_name
        if not avatar_url and identity:
            avatar_url = identity.get("avatar")

        async with aiohttp.ClientSession() as session:
            wh = await self._get_npc_webhook(channel, npc_name, session)
            if wh:
                try:
                    await self._send_chunked_webhook(wh, content, npc_name, avatar_url, wait=wait)
                    return
                except discord.errors.NotFound:
                    key = (str(channel.id), self._npc_slug(npc_name))
                    if key in self._npc_cache:
                        del self._npc_cache[key]
                        self._save_npc_cache()

                    wh = await self._get_npc_webhook(channel, npc_name, session)
                    if wh:
                        try:
                            await self._send_chunked_webhook(wh, content, npc_name, avatar_url, wait=wait)
                            return
                        except Exception as e:
                            logger.warning(f"NPC webhook retry failed for '{npc_name}': {e}")
                except Exception as e:
                    logger.warning(f"NPC webhook send failed for '{npc_name}': {e}")

            await self._send_chunked_standard(channel, content, username=npc_name)

    async def send(self, channel, content: str, identity_key: str = "DM", wait: bool = False,
                   username: str = None, avatar_url: str = None):
        """Send a message via general webhook, with standard-send fallback."""
        content = sanitize_text(content)

        async with aiohttp.ClientSession() as session:
            webhook = await self._get_webhook(channel, session)

            identity = IDENTITIES.get(identity_key, IDENTITIES["DM"])
            final_name = username or identity["name"]
            final_avatar = avatar_url or identity["avatar"]

            dm_avatar_base = IDENTITIES["DM"]["avatar"].split("?")[0]
            current_avatar_base = (final_avatar or "").split("?")[0]

            if final_name and identity_key != "DM" and (not final_avatar or current_avatar_base == dm_avatar_base):
                match = next((k for k in IDENTITIES if isinstance(k, str) and k.lower() == final_name.lower()), None)
                if match and IDENTITIES[match].get("avatar"):
                    final_avatar = IDENTITIES[match]["avatar"]

            if not webhook:
                return await self._send_chunked_standard(channel, content, final_name)

            try:
                return await self._send_chunked_webhook(webhook, content, final_name, final_avatar, wait)
            except discord.errors.NotFound:
                if channel.id in self._cache:
                    del self._cache[channel.id]
                webhook = await self._get_webhook(channel, session)
                if webhook:
                    try:
                        return await self._send_chunked_webhook(webhook, content, final_name, final_avatar, wait)
                    except Exception:
                        pass
                return await self._send_chunked_standard(channel, content, final_name)
            except Exception:
                return await self._send_chunked_standard(channel, content, final_name)

    async def _get_webhook(self, channel, session):
        if channel.id in self._cache:
            return self._cache[channel.id]

        try:
            whs = await channel.webhooks()
            wh = next((w for w in whs if w.name == "EmberHeart DM"), None)
            if not wh:
                wh = await channel.create_webhook(name="EmberHeart DM", reason="Dynamic NPC Impersonation")

            self._cache[channel.id] = wh
            return wh
        except Exception as e:
            logger.warning(f"Failed to manage webhook for {channel.name}: {e}")
            return None

    async def _send_chunked_webhook(self, webhook, content, username, avatar_url, wait):
        max_length = 1900
        if len(content) <= max_length:
            return await webhook.send(content=content, username=username, avatar_url=avatar_url, wait=wait)

        chunks = self._chunk_text(content, max_length)
        last_msg = None
        for chunk in chunks:
            if chunk:
                last_msg = await webhook.send(content=chunk, username=username, avatar_url=avatar_url, wait=True)
                await asyncio.sleep(0.5)
        return last_msg

    async def _send_chunked_standard(self, channel, content, username=None):
        if isinstance(channel, discord.DMChannel) and username and username != "DM":
            content = f"**{username}:**\n{content}"

        max_length = 1900
        if len(content) <= max_length:
            return await channel.send(content)

        chunks = self._chunk_text(content, max_length)
        last_msg = None
        for chunk in chunks:
            if chunk:
                last_msg = await channel.send(chunk)
                await asyncio.sleep(0.5)
        return last_msg

    def _chunk_text(self, text, max_len):
        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break
            split_idx = text.rfind("\n", 0, max_len)
            if split_idx == -1:
                split_idx = max_len
            chunks.append(text[:split_idx].strip())
            text = text[split_idx:].strip()
        return chunks


# Singleton instance
transport = TransportAPI()
