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
    current_location_id TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS party_settings (
    campaign_id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Grup d''aventurers',
    level INTEGER NOT NULL DEFAULT 3, size INTEGER NOT NULL DEFAULT 4,
    notes TEXT NOT NULL DEFAULT '', FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
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
CREATE TABLE IF NOT EXISTS lore_entries (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, layer TEXT NOT NULL,
    category TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL,
    source_id TEXT, location_id TEXT, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS hex_cells (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, q INTEGER NOT NULL, r INTEGER NOT NULL,
    terrain TEXT NOT NULL, title TEXT NOT NULL, discovery TEXT NOT NULL,
    travel_cost INTEGER NOT NULL, encounter_chance INTEGER NOT NULL,
    player_notes TEXT NOT NULL, dm_notes TEXT NOT NULL, location_id TEXT, source_id TEXT,
    UNIQUE(campaign_id, q, r), FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS combats (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL,
    round INTEGER NOT NULL, turn_index INTEGER NOT NULL, encounter_id TEXT, summary TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS combatants (
    id TEXT PRIMARY KEY, combat_id TEXT NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL,
    initiative INTEGER NOT NULL, armor_class INTEGER NOT NULL, max_hp INTEGER NOT NULL,
    current_hp INTEGER NOT NULL, temp_hp INTEGER NOT NULL DEFAULT 0, initiative_bonus INTEGER NOT NULL DEFAULT 0,
    concentration INTEGER NOT NULL DEFAULT 0, reaction_available INTEGER NOT NULL DEFAULT 1,
    legendary_actions INTEGER NOT NULL DEFAULT 0, legendary_actions_max INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '', conditions TEXT NOT NULL, actions TEXT NOT NULL,
    source_id TEXT, reference_id TEXT, character_id TEXT, FOREIGN KEY(combat_id) REFERENCES combats(id)
);
CREATE TABLE IF NOT EXISTS hexcrawl_settings (
    campaign_id TEXT PRIMARY KEY, track_weather INTEGER NOT NULL DEFAULT 1,
    track_navigation INTEGER NOT NULL DEFAULT 1, track_food INTEGER NOT NULL DEFAULT 1,
    track_water INTEGER NOT NULL DEFAULT 1, track_fatigue INTEGER NOT NULL DEFAULT 1,
    track_encounters INTEGER NOT NULL DEFAULT 1, track_foraging INTEGER NOT NULL DEFAULT 1,
    auto_discover INTEGER NOT NULL DEFAULT 1, default_pace TEXT NOT NULL DEFAULT 'normal',
    hex_distance REAL NOT NULL DEFAULT 10, distance_unit TEXT NOT NULL DEFAULT 'km',
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS expedition_state (
    campaign_id TEXT PRIMARY KEY, current_hex_id TEXT, food REAL NOT NULL DEFAULT 40,
    water REAL NOT NULL DEFAULT 80, supplies REAL NOT NULL DEFAULT 10,
    exhaustion INTEGER NOT NULL DEFAULT 0, lost INTEGER NOT NULL DEFAULT 0,
    weather TEXT NOT NULL DEFAULT 'clear', updated_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS travel_logs (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, origin_hex_id TEXT, destination_hex_id TEXT NOT NULL,
    route TEXT NOT NULL, pace TEXT NOT NULL, days INTEGER NOT NULL, distance REAL NOT NULL, distance_unit TEXT NOT NULL DEFAULT 'km',
    weather TEXT NOT NULL, navigation_roll INTEGER, encounter_roll INTEGER,
    food_used REAL NOT NULL, water_used REAL NOT NULL, exhaustion_delta INTEGER NOT NULL,
    encounter_triggered INTEGER NOT NULL, encounter_id TEXT, reached_destination INTEGER NOT NULL,
    notes TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS player_view_settings (
    campaign_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1, show_map INTEGER NOT NULL DEFAULT 1,
    show_rumors INTEGER NOT NULL DEFAULT 1, show_resources INTEGER NOT NULL DEFAULT 1,
    show_weather INTEGER NOT NULL DEFAULT 1, show_combat INTEGER NOT NULL DEFAULT 1,
    show_enemy_hp INTEGER NOT NULL DEFAULT 0, show_characters INTEGER NOT NULL DEFAULT 1,
    show_inventory INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS combat_logs (
    id TEXT PRIMARY KEY, combat_id TEXT NOT NULL, message TEXT NOT NULL, kind TEXT NOT NULL,
    created_at TEXT NOT NULL, FOREIGN KEY(combat_id) REFERENCES combats(id)
);
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, name TEXT NOT NULL, player_name TEXT NOT NULL DEFAULT '',
    class_name TEXT NOT NULL DEFAULT 'Aventurer', ancestry TEXT NOT NULL DEFAULT '', level INTEGER NOT NULL DEFAULT 1,
    armor_class INTEGER NOT NULL DEFAULT 10, max_hp INTEGER NOT NULL DEFAULT 1, current_hp INTEGER NOT NULL DEFAULT 1,
    temp_hp INTEGER NOT NULL DEFAULT 0, speed INTEGER NOT NULL DEFAULT 30, ability_scores TEXT NOT NULL DEFAULT '{}',
    saving_throws TEXT NOT NULL DEFAULT '[]', skills TEXT NOT NULL DEFAULT '[]', passive_perception INTEGER NOT NULL DEFAULT 10,
    exhaustion INTEGER NOT NULL DEFAULT 0, conditions TEXT NOT NULL DEFAULT '[]', spell_slots TEXT NOT NULL DEFAULT '{}',
    spell_slots_max TEXT NOT NULL DEFAULT '{}', resources TEXT NOT NULL DEFAULT '[]', notes TEXT NOT NULL DEFAULT '',
    share_with_players INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS treasury (
    campaign_id TEXT PRIMARY KEY, cp REAL NOT NULL DEFAULT 0, sp REAL NOT NULL DEFAULT 0,
    ep REAL NOT NULL DEFAULT 0, gp REAL NOT NULL DEFAULT 0, pp REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL, FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS inventory_items (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, owner_type TEXT NOT NULL DEFAULT 'party', owner_id TEXT,
    name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'gear', quantity REAL NOT NULL DEFAULT 1,
    weight REAL NOT NULL DEFAULT 0, value REAL NOT NULL DEFAULT 0, currency_unit TEXT NOT NULL DEFAULT 'gp',
    description TEXT NOT NULL DEFAULT '', equipped INTEGER NOT NULL DEFAULT 0, attuned INTEGER NOT NULL DEFAULT 0,
    consumable INTEGER NOT NULL DEFAULT 0, reference_id TEXT, source_id TEXT, reward_id TEXT, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
CREATE TABLE IF NOT EXISTS inventory_transactions (
    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, kind TEXT NOT NULL, description TEXT NOT NULL,
    item_id TEXT, character_id TEXT, currency TEXT, currency_delta REAL NOT NULL DEFAULT 0,
    quantity_delta REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
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
            campaign_columns = {row["name"] for row in connection.execute("PRAGMA table_info(campaigns)")}
            if "archived" not in campaign_columns:
                connection.execute("ALTER TABLE campaigns ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
            combat_columns = {row["name"] for row in connection.execute("PRAGMA table_info(combats)")}
            if "encounter_id" not in combat_columns:
                connection.execute("ALTER TABLE combats ADD COLUMN encounter_id TEXT")
            if "summary" not in combat_columns:
                connection.execute("ALTER TABLE combats ADD COLUMN summary TEXT NOT NULL DEFAULT ''")
            combatant_columns = {row["name"] for row in connection.execute("PRAGMA table_info(combatants)")}
            combatant_migrations = {
                "temp_hp": "INTEGER NOT NULL DEFAULT 0", "initiative_bonus": "INTEGER NOT NULL DEFAULT 0",
                "concentration": "INTEGER NOT NULL DEFAULT 0", "reaction_available": "INTEGER NOT NULL DEFAULT 1",
                "legendary_actions": "INTEGER NOT NULL DEFAULT 0", "legendary_actions_max": "INTEGER NOT NULL DEFAULT 0",
                "notes": "TEXT NOT NULL DEFAULT ''",
            }
            for name, definition in combatant_migrations.items():
                if name not in combatant_columns:
                    connection.execute(f"ALTER TABLE combatants ADD COLUMN {name} {definition}")
            if "character_id" not in combatant_columns:
                connection.execute("ALTER TABLE combatants ADD COLUMN character_id TEXT")
            reward_columns = {row["name"] for row in connection.execute("PRAGMA table_info(rewards)")}
            if "claimed" not in reward_columns:
                connection.execute("ALTER TABLE rewards ADD COLUMN claimed INTEGER NOT NULL DEFAULT 0")
            if "claimed_at" not in reward_columns:
                connection.execute("ALTER TABLE rewards ADD COLUMN claimed_at TEXT")
            player_columns = {row["name"] for row in connection.execute("PRAGMA table_info(player_view_settings)")}
            if "show_characters" not in player_columns:
                connection.execute("ALTER TABLE player_view_settings ADD COLUMN show_characters INTEGER NOT NULL DEFAULT 1")
            if "show_inventory" not in player_columns:
                connection.execute("ALTER TABLE player_view_settings ADD COLUMN show_inventory INTEGER NOT NULL DEFAULT 1")
            travel_columns = {row["name"] for row in connection.execute("PRAGMA table_info(travel_logs)")}
            if "encounter_id" not in travel_columns:
                connection.execute("ALTER TABLE travel_logs ADD COLUMN encounter_id TEXT")
            if "distance_unit" not in travel_columns:
                connection.execute("ALTER TABLE travel_logs ADD COLUMN distance_unit TEXT NOT NULL DEFAULT 'km'")
            connection.execute("""CREATE TABLE IF NOT EXISTS party_settings (
                campaign_id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Grup d''aventurers',
                level INTEGER NOT NULL DEFAULT 3, size INTEGER NOT NULL DEFAULT 4,
                notes TEXT NOT NULL DEFAULT '', FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
            )""")
            connection.execute("""INSERT OR IGNORE INTO party_settings(campaign_id)
                                  SELECT id FROM campaigns""")
            connection.execute("""INSERT OR IGNORE INTO hexcrawl_settings(campaign_id)
                                  SELECT id FROM campaigns""")
            connection.execute("""INSERT OR IGNORE INTO player_view_settings(campaign_id)
                                  SELECT id FROM campaigns""")
            self._seed(connection)
            self._seed_generation(connection)
            self._seed_campaign_tools(connection)
            self._seed_party(connection)

    def _seed_party(self, db: sqlite3.Connection) -> None:
        if not db.execute("SELECT 1 FROM campaigns WHERE id='demo'").fetchone():
            return
        db.execute("INSERT OR IGNORE INTO treasury(campaign_id,updated_at,gp) VALUES ('demo',datetime('now'),125)")
        if db.execute("SELECT 1 FROM characters WHERE campaign_id='demo' LIMIT 1").fetchone():
            return
        samples = [
            ("char_aria", "Aria Ventclar", "Marta", "Exploradora", "Humana", 4, 15, 34, 29, 35, 15, 1),
            ("char_borin", "Borin Rocafort", "Pau", "Guerrer", "Nan", 4, 18, 44, 44, 25, 12, 0),
            ("char_nim", "Nim de la Boira", "Laia", "Druida", "Elfa", 4, 14, 31, 24, 30, 16, 0),
        ]
        for item in samples:
            values = (item[0], "demo", *item[1:], json.dumps({"str":10,"dex":14,"con":12,"int":10,"wis":14,"cha":10}),
                      "[]", "[]", "[]", json.dumps({"1":2,"2":1}), json.dumps({"1":4,"2":3}),
                      json.dumps([{"name":"Inspiració","current":1,"maximum":1,"reset":"long"}]))
            db.execute("""INSERT INTO characters(id,campaign_id,name,player_name,class_name,ancestry,level,armor_class,max_hp,
                current_hp,speed,passive_perception,exhaustion,ability_scores,saving_throws,skills,conditions,spell_slots,
                spell_slots_max,resources,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", values)
        db.execute("""INSERT OR IGNORE INTO inventory_items(id,campaign_id,owner_type,name,category,quantity,weight,value,
            currency_unit,description,consumable,created_at) VALUES ('item_rations','demo','party','Racions','supplies',8,2,0.5,'gp',
            'Menjar per a una jornada',1,datetime('now'))""")

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
            "INSERT INTO campaigns(id, name, system, rules_profile, current_day, current_location_id) VALUES (?, ?, ?, ?, ?, ?)",
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

    def _seed_campaign_tools(self, db: sqlite3.Connection) -> None:
        if not db.execute("SELECT 1 FROM campaigns WHERE id='demo'").fetchone():
            return
        if not db.execute("SELECT 1 FROM lore_entries WHERE campaign_id='demo' LIMIT 1").fetchone():
            lore = [
                ("lore_dm_demo", "dm", "quest", "El sabotatge de l'expedició", "Nyra sospita que algú del gremi ven les rutes segures a una facció rival."),
                ("lore_players_demo", "players", "lore", "Rumors del port", "Diversos mariners afirmen que la selva canvia els camins després de les tempestes."),
                ("lore_world_demo", "world", "location", "Estació de pluges", "Les pluges han crescut els rius i han alentit totes les expedicions cap a l'interior."),
            ]
            for item_id, layer, category, title, content in lore:
                db.execute("INSERT INTO lore_entries VALUES (?, 'demo', ?, ?, ?, ?, NULL, 'port_verd', datetime('now'))", (item_id, layer, category, title, content))
        if not db.execute("SELECT 1 FROM hex_cells WHERE campaign_id='demo' LIMIT 1").fetchone():
            hexes = [
                ("hex_demo_0_0", 0, 0, "urban", "Port Verd", "explored", 1, 5, "Punt de sortida i lloc segur.", "Els contactes del gremi poden proporcionar guies.", "port_verd"),
                ("hex_demo_1_0", 1, 0, "jungle", "Sender de les falgueres", "discovered", 2, 25, "Un sender parcialment cartografiat.", "Hi ha rastres recents de depredadors.", None),
                ("hex_demo_0_1", 0, 1, "river", "Gual de pedra", "discovered", 2, 20, "Un pas possible si el riu no creix.", "Les pluges poden duplicar el cost de viatge.", None),
                ("hex_demo_1_1", 1, 1, "ruins", "Ruïnes cobertes", "hidden", 3, 40, "", "Una cambra inferior conserva una inscripció i una reserva oblidada.", None),
                ("hex_demo_-1_1", -1, 1, "swamp", "Aiguamolls silenciosos", "hidden", 3, 35, "", "Boira densa i terreny difícil; possible refugi d'una criatura territorial.", None),
            ]
            for row in hexes:
                db.execute("INSERT INTO hex_cells VALUES (?, 'demo', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)", row)
        if not db.execute("SELECT 1 FROM combats WHERE campaign_id='demo' LIMIT 1").fetchone():
            db.execute("""INSERT INTO combats(id,campaign_id,name,status,round,turn_index,encounter_id,summary,created_at)
                          VALUES ('combat_demo', 'demo', 'Emboscada al sender', 'active', 1, 0, NULL, '', datetime('now'))""")
            combatants = [
                ("combatant_demo_kara", "Kara", "ally", 16, 14, 24, 24, [], [{"name":"Ballesta lleugera","description":"Atac a distància; 1d8+2 perforant.","source":"manual"}], None, None),
                ("combatant_demo_goblin", "Explorador goblin", "enemy", 14, 15, 12, 12, [], [{"name":"Cimitarra","description":"Atac cos a cos; 1d6+2 tallant.","source":"SRD"},{"name":"Amagar-se","description":"Intenta ocultar-se com a acció addicional.","source":"SRD"}], None, "srd51:monsters:goblin"),
                ("combatant_demo_raptor", "Raptor de la jungla", "enemy", 11, 13, 18, 18, [], [{"name":"Mossegada","description":"Atac cos a cos; dany perforant.","source":"manual"}], None, None),
            ]
            for item_id, name, kind, initiative, armor_class, max_hp, current_hp, conditions, actions, source_id, reference_id in combatants:
                db.execute("""INSERT INTO combatants(id,combat_id,name,kind,initiative,armor_class,max_hp,current_hp,
                           conditions,actions,source_id,reference_id) VALUES (?, 'combat_demo', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           (item_id, name, kind, initiative, armor_class, max_hp, current_hp, json.dumps(conditions), json.dumps(actions), source_id, reference_id))
        db.execute("""INSERT OR IGNORE INTO expedition_state(campaign_id,current_hex_id,food,water,supplies,exhaustion,lost,weather,updated_at)
                      VALUES ('demo','hex_demo_0_0',40,80,10,0,0,'clear',datetime('now'))""")
