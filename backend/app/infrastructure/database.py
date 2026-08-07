import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, system TEXT NOT NULL,
    rules_profile TEXT NOT NULL, current_day INTEGER NOT NULL,
    current_location_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS locations (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '', terrain TEXT NOT NULL DEFAULT 'urban',
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS factions (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS npcs (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, name TEXT NOT NULL,
    location_id TEXT NOT NULL, faction_id TEXT, traits TEXT NOT NULL,
    goals TEXT NOT NULL, values_json TEXT NOT NULL, secrets TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS relationships (
    npc_id TEXT PRIMARY KEY, trust INTEGER NOT NULL DEFAULT 0,
    respect INTEGER NOT NULL DEFAULT 0, fear INTEGER NOT NULL DEFAULT 0,
    affection INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(npc_id) REFERENCES npcs(id)
);
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY, npc_id TEXT NOT NULL, text TEXT NOT NULL,
    importance TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(npc_id) REFERENCES npcs(id)
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, started_at TEXT NOT NULL,
    ended_at TEXT, summary TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, title TEXT NOT NULL,
    description TEXT NOT NULL, event_type TEXT NOT NULL, severity INTEGER NOT NULL,
    consequences TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
    location_id TEXT, visibility TEXT NOT NULL DEFAULT 'public',
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS world_state (
    campaign_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
    PRIMARY KEY(campaign_id, key),
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE,
    changes TEXT NOT NULL, undone_at TEXT, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY(event_id) REFERENCES events(id)
);
CREATE TABLE IF NOT EXISTS content_sources (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, title TEXT NOT NULL,
    source_type TEXT NOT NULL, file_name TEXT NOT NULL, file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL, checksum TEXT NOT NULL, visibility TEXT NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 0, chunk_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL, created_at TEXT NOT NULL, asset_kind TEXT NOT NULL DEFAULT 'document',
    UNIQUE(campaign_id, checksum), FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY, source_id TEXT NOT NULL, page INTEGER, section TEXT NOT NULL,
    text TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES content_sources(id)
);
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY, npc_id TEXT NOT NULL, subject TEXT NOT NULL, content TEXT NOT NULL,
    confidence REAL NOT NULL, truth_status TEXT NOT NULL, source_type TEXT NOT NULL,
    source_id TEXT, created_at TEXT NOT NULL, FOREIGN KEY(npc_id) REFERENCES npcs(id)
);
CREATE TABLE IF NOT EXISTS rumors (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, origin_location_id TEXT,
    subject TEXT NOT NULL, content TEXT NOT NULL, credibility REAL NOT NULL,
    spread REAL NOT NULL, status TEXT NOT NULL, source_event_id TEXT, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS generation_tables (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL,
    description TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS generation_entries (
    id TEXT PRIMARY KEY, table_id TEXT NOT NULL, terrains TEXT NOT NULL,
    min_level INTEGER NOT NULL, max_level INTEGER NOT NULL,
    min_difficulty INTEGER NOT NULL, max_difficulty INTEGER NOT NULL,
    weight INTEGER NOT NULL, title TEXT NOT NULL, payload TEXT NOT NULL, tags TEXT NOT NULL,
    FOREIGN KEY(table_id) REFERENCES generation_tables(id)
);
CREATE TABLE IF NOT EXISTS encounters (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, location_id TEXT, terrain TEXT NOT NULL,
    party_level INTEGER NOT NULL, party_size INTEGER NOT NULL, difficulty INTEGER NOT NULL,
    encounter_type TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
    objectives TEXT NOT NULL, complications TEXT NOT NULL, context_reasons TEXT NOT NULL,
    status TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS rewards (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, encounter_id TEXT, location_id TEXT,
    terrain TEXT NOT NULL, party_level INTEGER NOT NULL, difficulty INTEGER NOT NULL,
    mode TEXT NOT NULL, fortune_roll INTEGER, tier TEXT NOT NULL, title TEXT NOT NULL,
    items TEXT NOT NULL, narrative_rewards TEXT NOT NULL, context_reasons TEXT NOT NULL,
    created_at TEXT NOT NULL, FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(locations)")}
            if "terrain" not in columns:
                connection.execute("ALTER TABLE locations ADD COLUMN terrain TEXT NOT NULL DEFAULT 'urban'")
            event_columns = {row["name"] for row in connection.execute("PRAGMA table_info(events)")}
            if "location_id" not in event_columns:
                connection.execute("ALTER TABLE events ADD COLUMN location_id TEXT")
            if "visibility" not in event_columns:
                connection.execute("ALTER TABLE events ADD COLUMN visibility TEXT NOT NULL DEFAULT 'public'")
            source_columns = {row["name"] for row in connection.execute("PRAGMA table_info(content_sources)")}
            if "asset_kind" not in source_columns:
                connection.execute("ALTER TABLE content_sources ADD COLUMN asset_kind TEXT NOT NULL DEFAULT 'document'")
            self._seed(connection)
            self._seed_generation(connection)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _seed(self, db: sqlite3.Connection) -> None:
        if db.execute("SELECT 1 FROM campaigns LIMIT 1").fetchone():
            return
        db.execute(
            "INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, ?)",
            ("demo", "Expedició de la Jungla", "dnd5e", "campaign_default", 1, "port_verd"),
        )
        db.execute(
            "INSERT INTO locations(id, campaign_id, name, description, terrain) VALUES (?, ?, ?, ?, ?)",
            ("port_verd", "demo", "Port Verd", "Un port tropical, punt de partida de l'expedició.", "urban"),
        )
        db.execute(
            "INSERT INTO factions VALUES (?, ?, ?, ?)",
            ("gremi_exploradors", "demo", "Gremi d'Exploradors", "Cartògrafs, guies i aventurers locals."),
        )
        npcs = [
            ("kara", "Kara", ["pragmàtica", "observadora", "ambiciosa"], ["protegir el seu negoci"], ["lleialtat", "prudència"], 25, 35, 5, 10),
            ("batu", "Batu", ["jovial", "curiós", "lleial"], ["cartografiar una ruta segura"], ["coneixement", "amistat"], 45, 30, 0, 25),
            ("nyra", "Nyra", ["reservada", "directa", "valenta"], ["descobrir qui saboteja l'expedició"], ["justícia", "deure"], 5, 40, 5, 0),
        ]
        for npc_id, name, traits, goals, values, trust, respect, fear, affection in npcs:
            db.execute(
                "INSERT INTO npcs VALUES (?, 'demo', ?, 'port_verd', 'gremi_exploradors', ?, ?, ?, '[]')",
                (npc_id, name, json.dumps(traits), json.dumps(goals), json.dumps(values)),
            )
            db.execute("INSERT INTO relationships VALUES (?, ?, ?, ?, ?)", (npc_id, trust, respect, fear, affection))
        db.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?, datetime('now'))",
            ("memory_kara_1", "kara", "El grup va ajudar un aprenent del seu negoci.", "important"),
        )
        db.execute("INSERT INTO world_state VALUES ('demo', 'wanted_level', '0')")
        db.execute("INSERT INTO world_state VALUES ('demo', 'reputation:gremi_exploradors', '10')")

    def _seed_generation(self, db: sqlite3.Connection) -> None:
        if not db.execute("SELECT 1 FROM campaigns WHERE id='demo'").fetchone():
            return
        if db.execute("SELECT 1 FROM generation_tables WHERE campaign_id='demo' LIMIT 1").fetchone():
            return
        db.execute("INSERT INTO generation_tables VALUES ('table_encounter_demo','demo','encounter','Encounters bàsics','Opcions inicials ampliables',datetime('now'))")
        db.execute("INSERT INTO generation_tables VALUES ('table_reward_demo','demo','reward','Recompenses contextuals','Opcions inicials ampliables',datetime('now'))")
        encounter_entries = [
            ("enc_jungle_scouts", ["jungle", "forest"], 1, 10, 1, 4, 4, "Exploradors desconfiats", {"type":"social","description":"Un grup local ha sentit versions contradictòries sobre els aventurers.","objectives":["Aconseguir informació o pas segur"],"complications":["El rumor pot empitjorar si fallen les negociacions"]}, ["faction","rumor"]),
            ("enc_jungle_predator", ["jungle", "forest", "swamp"], 1, 20, 2, 5, 5, "Depredador territorial", {"type":"combat","description":"Una criatura defensa el territori i una possible via de retirada.","objectives":["Travessar la zona o fer retrocedir la criatura"],"complications":["Terreny dens i visibilitat limitada"]}, ["wildlife"]),
            ("enc_urban_dispute", ["urban"], 1, 20, 1, 4, 6, "Disputa al mercat", {"type":"social","description":"Una discussió pública involucra dues faccions locals.","objectives":["Evitar l'escalada o escollir una posició"],"complications":["Testimonis i reputació en joc"]}, ["social","faction"]),
            ("enc_dungeon_hazard", ["dungeon", "ruins"], 1, 20, 2, 5, 5, "Cambra inestable", {"type":"hazard","description":"L'estructura cedeix mentre el grup identifica una ruta segura.","objectives":["Creuar sense perdre recursos"],"complications":["Soroll que pot atraure enemics"]}, ["hazard"]),
            ("enc_coast_wreck", ["coast", "river"], 1, 20, 1, 5, 3, "Restes arrossegades per l'aigua", {"type":"exploration","description":"Unes restes recents contenen pistes i perills ambientals.","objectives":["Investigar l'origen de les restes"],"complications":["Marea o corrent canviant"]}, ["exploration"]),
        ]
        reward_entries = [
            ("rew_jungle_supplies", ["jungle", "forest", "swamp"], 1, 20, 1, 5, 6, "Subministraments de supervivència", {"items":[{"name":"Herbes medicinals","quantity":2,"category":"consumable"},{"name":"Racions protegides","quantity":3,"category":"supply"}],"narrative":["Una pista sobre una ruta menys perillosa"]}, ["survival"]),
            ("rew_urban_contact", ["urban"], 1, 20, 1, 5, 6, "Contacte i moneda local", {"items":[{"name":"Moneda local","quantity":40,"category":"currency"}],"narrative":["Un contacte ofereix informació o un descompte"]}, ["social","currency"]),
            ("rew_dungeon_cache", ["dungeon", "ruins"], 1, 20, 2, 5, 5, "Reserva oblidada", {"items":[{"name":"Consumible apropiat al nivell","quantity":1,"category":"consumable"},{"name":"Monedes antigues","quantity":60,"category":"currency"}],"narrative":["Inscripció que apunta a una zona encara no explorada"]}, ["treasure","lore"]),
            ("rew_coast_salvage", ["coast", "river"], 1, 20, 1, 5, 4, "Materials recuperats", {"items":[{"name":"Materials aprofitables","quantity":2,"category":"trade"}],"narrative":["Marca d'un comerciant o vaixell conegut"]}, ["trade"]),
        ]
        for table_id, entries in (("table_encounter_demo", encounter_entries), ("table_reward_demo", reward_entries)):
            for entry_id, terrains, min_level, max_level, min_diff, max_diff, weight, title, payload, tags in entries:
                db.execute("INSERT INTO generation_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (entry_id, table_id, json.dumps(terrains), min_level, max_level, min_diff, max_diff, weight, title, json.dumps(payload), json.dumps(tags)))
