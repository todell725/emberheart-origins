"""
State coordination for EmberHeart: Origins
SQLite read model + async write coordinator
Ported from Claudes-EmberHeart
"""
import sqlite3
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.storage import (
    load_all_character_profiles,
    load_all_character_states,
    save_character_state,
    save_character_profile,
    load_json,
    save_json
)
from core.models import CharacterProfile, CharacterState


class SQLiteReadModel:
    """In-memory SQLite database built from canonical JSON state. Fast reads, dropped on exit."""
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        self._bootstrap_from_json()

    def _init_schema(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE characters (
                id TEXT PRIMARY KEY,
                name TEXT,
                race TEXT,
                role TEXT,
                avatar_url TEXT,
                description TEXT,
                bio TEXT,
                motivation TEXT,
                secret TEXT,
                hp INTEGER,
                max_hp INTEGER,
                gold INTEGER,
                inventory TEXT,
                equipped_weapon TEXT,
                equipped_armor TEXT,
                status_effects TEXT,
                location TEXT
            )
        ''')
        self.conn.commit()

    def _bootstrap_from_json(self):
        """Loads all data from characters/ into the SQLite DB at startup."""
        profiles = list(load_all_character_profiles())
        states = list(load_all_character_states())

        char_map = {}
        for p in profiles:
            char_map[p.get("id")] = p

        for s in states:
            cid = s.get("id")
            if cid in char_map:
                char_map[cid].update(s)
            else:
                char_map[cid] = s

        c = self.conn.cursor()
        for char_id, data in char_map.items():
            if not char_id:
                continue
            c.execute('''
                INSERT OR REPLACE INTO characters (
                    id, name, race, role, avatar_url, description, bio, motivation, secret,
                    hp, max_hp, gold, inventory, equipped_weapon, equipped_armor, status_effects, location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get("id"),
                data.get("name"),
                data.get("race"),
                data.get("role"),
                data.get("avatar_url"),
                data.get("description"),
                data.get("bio"),
                data.get("motivation"),
                data.get("secret"),
                data.get("hp"),
                data.get("max_hp"),
                data.get("gold", 0),
                json.dumps(data.get("inventory", {})),
                data.get("equipped_weapon"),
                data.get("equipped_armor"),
                json.dumps(data.get("status_effects", [])),
                data.get("location")
            ))
        self.conn.commit()

    def get_character(self, char_id: str) -> Optional[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
        row = c.fetchone()
        if not row:
            return None
        res = dict(row)
        res["inventory"] = json.loads(res["inventory"]) if res["inventory"] else {}
        res["status_effects"] = json.loads(res["status_effects"]) if res["status_effects"] else []
        return res

    def find_characters_by_name(self, name_part: str) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM characters WHERE name LIKE ?", (f"%{name_part}%",))
        result = []
        for row in c.fetchall():
            res = dict(row)
            res["inventory"] = json.loads(res["inventory"]) if res["inventory"] else {}
            res["status_effects"] = json.loads(res["status_effects"]) if res["status_effects"] else []
            result.append(res)
        return result

    def update_character(self, data: Dict[str, Any]):
        c = self.conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO characters (
                id, name, race, role, avatar_url, description, bio, motivation, secret,
                hp, max_hp, gold, inventory, equipped_weapon, equipped_armor, status_effects, location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get("id"),
            data.get("name"),
            data.get("race"),
            data.get("role"),
            data.get("avatar_url"),
            data.get("description"),
            data.get("bio"),
            data.get("motivation"),
            data.get("secret"),
            data.get("hp"),
            data.get("max_hp"),
            data.get("gold", 0),
            json.dumps(data.get("inventory", {})),
            data.get("equipped_weapon"),
            data.get("equipped_armor"),
            json.dumps(data.get("status_effects", [])),
            data.get("location")
        ))
        self.conn.commit()


class StateCoordinator:
    """Serializes all canonical JSON writes and synchronizes the SQLite read model."""
    def __init__(self, read_model: SQLiteReadModel):
        self.read_model = read_model
        self.file_locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, file_id: str) -> asyncio.Lock:
        if file_id not in self.file_locks:
            self.file_locks[file_id] = asyncio.Lock()
        return self.file_locks[file_id]

    async def update_character_state_async(self, char_id: str, updates: Dict[str, Any]):
        """Async atomic write to character state, preventing races."""
        lock = self._get_lock(f"char_state_{char_id}")
        async with lock:
            state = await asyncio.to_thread(self._sync_load_state, char_id)
            state.update(updates)
            await asyncio.to_thread(save_character_state, char_id, state)

            profile = await asyncio.to_thread(self._sync_load_profile, char_id)
            merged = {**profile, **state}
            self.read_model.update_character(merged)

    async def update_global_json_async(self, filename: str, modify_callback):
        """Async atomic global JSON update."""
        lock = self._get_lock(f"global_{filename}")
        async with lock:
            try:
                data = await asyncio.to_thread(load_json, filename)
            except FileNotFoundError:
                data = {}

            new_data = modify_callback(data)
            if new_data is None:
                new_data = data

            await asyncio.to_thread(save_json, filename, new_data)

    def _sync_load_state(self, char_id: str) -> dict:
        from core.storage import load_character_state
        return load_character_state(char_id)

    def _sync_load_profile(self, char_id: str) -> dict:
        from core.storage import load_character_profile
        return load_character_profile(char_id)


# Singleton Instance
read_model = SQLiteReadModel()
coordinator = StateCoordinator(read_model)
