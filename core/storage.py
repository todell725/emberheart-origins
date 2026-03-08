"""
Storage utilities for EmberHeart: Origins
Ported from Claudes-EmberHeart
"""
import json
import os
import shutil
import time
import logging
from pathlib import Path
from datetime import datetime

from .config import DB_DIR, ROOT_DIR, NPC_DIR, CHARACTERS_DIR

BACKUP_DIR = ROOT_DIR / "backups"
logger = logging.getLogger("EH_Storage")


def _read_json_with_retry(path: Path, retries: int = 3, delay: float = 0.05) -> dict | list:
    """Read JSON with short retries for transient Windows/network-share file locks."""
    last_error = None
    for attempt in range(retries):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except PermissionError as e:
            last_error = e
            if attempt == retries - 1:
                raise
            time.sleep(delay * (attempt + 1))
    if last_error:
        raise last_error
    raise FileNotFoundError(path)


def get_character_dir(char_id: str) -> Path | None:
    """Finds the character directory based on ID prefix (EH-XXX or PC-XXX)."""
    # Check npcs/ subdirectory first
    for search_dir in [NPC_DIR, CHARACTERS_DIR]:
        if not search_dir.exists():
            continue
        for d in search_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{char_id}_"):
                return d
    return None


def load_character_profile(char_id: str) -> dict:
    """Loads lore/static data for a specific character."""
    char_dir = get_character_dir(char_id)
    if not char_dir: return {}
    path = char_dir / "profile.json"
    if not path.exists(): return {}
    return _read_json_with_retry(path)


def load_character_state(char_id: str) -> dict:
    """Loads runtime/dynamic state for a specific character."""
    char_dir = get_character_dir(char_id)
    if not char_dir: return {}
    path = char_dir / "state.json"
    if not path.exists(): return {}
    return _read_json_with_retry(path)


def save_character_state(char_id: str, state: dict):
    """Atomically saves dynamic state for a specific character."""
    char_dir = get_character_dir(char_id)
    if not char_dir:
        raise FileNotFoundError(f"Character directory for {char_id} not found.")

    path = char_dir / "state.json"

    import uuid
    temp_path = path.with_suffix(f'.{uuid.uuid4()}.tmp')

    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)

        max_retries = 5
        for i in range(max_retries):
            try:
                if path.exists():
                    os.replace(temp_path, path)
                else:
                    os.rename(temp_path, path)
                break
            except PermissionError:
                if i == max_retries - 1: raise
                time.sleep(0.5 * (i + 1))
    finally:
        if temp_path.exists():
            try: os.remove(temp_path)
            except Exception: pass


def save_character_profile(char_id: str, profile: dict):
    """Atomically saves static profile data for a specific character."""
    char_dir = get_character_dir(char_id)
    if not char_dir:
        raise FileNotFoundError(f"Character directory for {char_id} not found.")

    path = char_dir / "profile.json"

    import uuid
    temp_path = path.with_suffix(f'.{uuid.uuid4()}.tmp')

    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=4)

        max_retries = 5
        for i in range(max_retries):
            try:
                if path.exists():
                    os.replace(temp_path, path)
                else:
                    os.rename(temp_path, path)
                break
            except PermissionError:
                if i == max_retries - 1: raise
                time.sleep(0.5 * (i + 1))
    finally:
        if temp_path.exists():
            try: os.remove(temp_path)
            except Exception: pass


def load_all_character_profiles() -> list:
    """Utility to load all character profiles from the characters/npcs/ directory."""
    profiles = []
    for search_dir in [NPC_DIR, CHARACTERS_DIR]:
        if not search_dir.exists():
            continue
        for char_dir in search_dir.iterdir():
            if not char_dir.is_dir(): continue
            profile_path = char_dir / "profile.json"
            if profile_path.exists():
                try:
                    data = _read_json_with_retry(profile_path)
                    if isinstance(data, dict):
                        profiles.append(data)
                    else:
                        logger.warning("Skipping profile with non-object JSON: %s", profile_path)
                except Exception as e:
                    logger.warning("Skipping unreadable profile: %s (%s)", profile_path, e)
    return profiles


def resolve_character(query: str) -> dict | None:
    """Finds a character (NPC or PC) by ID, Name, or Partial Name match."""
    query = query.lower()
    all_chars = load_all_character_profiles()

    match = next((c for c in all_chars if query == c.get('id', '').lower() or query == c.get('name', '').lower()), None)
    if match: return match

    match = next((c for c in all_chars if query in c.get('name', '').lower()), None)
    return match


def load_all_character_states() -> list:
    """Utility to load all character profiles + states merged."""
    entities = []
    for search_dir in [NPC_DIR, CHARACTERS_DIR]:
        if not search_dir.exists():
            continue
        for char_dir in search_dir.iterdir():
            if not char_dir.is_dir(): continue
            profile_path = char_dir / "profile.json"
            state_path = char_dir / "state.json"

            try:
                data = _read_json_with_retry(profile_path)
                if not isinstance(data, dict):
                    continue
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning("Skipping character; failed to read profile %s (%s)", profile_path, e)
                continue

            if state_path.exists():
                try:
                    state_data = _read_json_with_retry(state_path)
                    if isinstance(state_data, dict):
                        data.update(state_data)
                except Exception as e:
                    logger.warning("Ignoring unreadable state %s (%s)", state_path, e)

            entities.append(data)
    return entities


def load_json(filename: str):
    """Safely loads a JSON file from the state directory."""
    path = DB_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filename: str, data: dict | list):
    """Atomically saves data to a JSON file in the state directory."""
    try:
        DB_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        if not DB_DIR.exists():
            print(f"Warning: Failed to create DB_DIR {DB_DIR}: {e}")

    path = DB_DIR / filename
    import uuid
    temp_path = path.with_suffix(f'.{uuid.uuid4()}.tmp')

    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        max_retries = 3
        retry_delay = 0.02

        for i in range(max_retries):
            try:
                if path.exists():
                    os.replace(temp_path, path)
                else:
                    os.rename(temp_path, path)
                break
            except PermissionError as e:
                if i == max_retries - 1:
                    raise
                time.sleep(retry_delay)
    finally:
        if temp_path.exists():
            try: os.remove(temp_path)
            except Exception: pass


def load_conversations() -> dict:
    """Loads all active conversation histories with corruption protection."""
    path = DB_DIR / "CONVERSATIONS.json"
    if not path.exists():
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Corruption detected in CONVERSATIONS.json: {e}")
        backup_path = path.with_suffix('.corrupt.bak')
        try:
            os.replace(path, backup_path)
        except Exception as e2:
            print(f"Failed to move corrupted file: {e2}")
        return {}


def save_conversations(data: dict):
    """Saves conversation histories."""
    save_json("CONVERSATIONS.json", data)


def log_narrative_event(event_text: str):
    """Appends a concise narrative event to the global NARRATIVE_LOG.md with pruning."""
    log_path = DB_DIR / "NARRATIVE_LOG.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"- [{timestamp}] {event_text}\n"

    lines = []
    if log_path.exists():
        lines = log_path.read_text(encoding='utf-8').splitlines(keepends=True)

    if len(lines) >= 50:
        lines = lines[-49:]

    lines.append(new_entry)

    import uuid
    temp_path = log_path.with_suffix(f'.{uuid.uuid4()}.tmp')

    try:
        temp_path.write_text("".join(lines), encoding='utf-8')
        max_retries = 5
        for i in range(max_retries):
            try:
                if log_path.exists():
                    os.replace(temp_path, log_path)
                else:
                    os.rename(temp_path, log_path)
                break
            except PermissionError:
                if i == max_retries - 1:
                    raise
                time.sleep(0.5 * (i + 1))
    finally:
        if temp_path.exists():
            try: os.remove(temp_path)
            except Exception: pass
