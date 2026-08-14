import json
from uuid import uuid4

from app.domain.models import (
    Encounter, GenerationEntry, GenerationEntryCreate, GenerationTable,
    GenerationTableCreate, GenerationTableUpdate, Knowledge, KnowledgeCreate,
    Reward, Rumor, RumorCreate, utc_now,
)
from app.infrastructure.database import Database


class SimulationRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_knowledge(self, npc_id: str) -> list[Knowledge]:
        with self.database.connect() as db:
            return [Knowledge(**dict(row)) for row in db.execute("SELECT * FROM knowledge WHERE npc_id=? ORDER BY created_at DESC", (npc_id,))]

    def list_campaign_knowledge(self, campaign_id: str) -> list[Knowledge]:
        with self.database.connect() as db:
            return [Knowledge(**dict(row)) for row in db.execute(
                "SELECT k.* FROM knowledge k JOIN npcs n ON n.id=k.npc_id WHERE n.campaign_id=? ORDER BY k.created_at", (campaign_id,)
            )]

    def add_knowledge(self, npc_id: str, payload: KnowledgeCreate) -> Knowledge:
        item = Knowledge(id=f"knowledge_{uuid4().hex[:12]}", npc_id=npc_id, **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO knowledge VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                item.id, item.npc_id, item.subject, item.content, item.confidence,
                item.truth_status, item.source_type, item.source_id, item.created_at,
            ))
        return item

    def has_knowledge_source(self, npc_id: str, source_id: str) -> bool:
        with self.database.connect() as db:
            return bool(db.execute("SELECT 1 FROM knowledge WHERE npc_id=? AND source_id=?", (npc_id, source_id)).fetchone())

    def create_rumor(self, payload: RumorCreate) -> Rumor:
        item = Rumor(id=f"rumor_{uuid4().hex[:12]}", **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO rumors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                item.id, item.campaign_id, item.origin_location_id, item.subject, item.content,
                item.credibility, item.spread, item.status, item.source_event_id, item.created_at,
            ))
        return item

    def get_rumor_by_event(self, event_id: str) -> Rumor | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM rumors WHERE source_event_id=?", (event_id,)).fetchone()
            return Rumor(**dict(row)) if row else None

    def get_rumor(self, rumor_id: str) -> Rumor | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM rumors WHERE id=?", (rumor_id,)).fetchone()
            return Rumor(**dict(row)) if row else None

    def list_rumors(self, campaign_id: str) -> list[Rumor]:
        with self.database.connect() as db:
            return [Rumor(**dict(row)) for row in db.execute("SELECT * FROM rumors WHERE campaign_id=? ORDER BY created_at DESC", (campaign_id,))]

    def remove_rumors_for_event(self, event_id: str) -> int:
        with self.database.connect() as db:
            rumor_ids = [row["id"] for row in db.execute("SELECT id FROM rumors WHERE source_event_id=?", (event_id,))]
            for rumor_id in rumor_ids:
                db.execute("DELETE FROM knowledge WHERE source_type='rumor' AND source_id=?", (rumor_id,))
                db.execute("DELETE FROM rumors WHERE id=?", (rumor_id,))
            return len(rumor_ids)

    def create_table(self, payload: GenerationTableCreate) -> GenerationTable:
        item = GenerationTable(id=f"table_{uuid4().hex[:12]}", **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO generation_tables VALUES (?, ?, ?, ?, ?, ?)", (item.id, item.campaign_id, item.kind, item.name, item.description, item.created_at))
        return item

    def get_table(self, table_id: str) -> GenerationTable | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM generation_tables WHERE id=?", (table_id,)).fetchone()
            return GenerationTable(**dict(row)) if row else None

    def update_table(self, table_id: str, payload: GenerationTableUpdate) -> GenerationTable | None:
        if not self.get_table(table_id):
            return None
        values = payload.model_dump(exclude_none=True)
        if values:
            assignments = ", ".join(f"{key}=?" for key in values)
            with self.database.connect() as db:
                db.execute(f"UPDATE generation_tables SET {assignments} WHERE id=?", (*values.values(), table_id))
        return self.get_table(table_id)

    def delete_table(self, table_id: str) -> bool:
        if not self.get_table(table_id):
            return False
        with self.database.connect() as db:
            db.execute("DELETE FROM generation_entries WHERE table_id=?", (table_id,))
            db.execute("DELETE FROM generation_tables WHERE id=?", (table_id,))
        return True

    def list_tables(self, campaign_id: str, kind: str | None = None) -> list[GenerationTable]:
        with self.database.connect() as db:
            if kind:
                rows = db.execute("SELECT * FROM generation_tables WHERE campaign_id=? AND kind=? ORDER BY name", (campaign_id, kind))
            else:
                rows = db.execute("SELECT * FROM generation_tables WHERE campaign_id=? ORDER BY kind,name", (campaign_id,))
            return [GenerationTable(**dict(row)) for row in rows]

    def add_entry(self, table_id: str, payload: GenerationEntryCreate) -> GenerationEntry:
        if not self.get_table(table_id):
            raise ValueError("Taula no trobada")
        if payload.min_level > payload.max_level or payload.min_difficulty > payload.max_difficulty:
            raise ValueError("Els rangs mínims no poden superar els màxims")
        item = GenerationEntry(id=f"entry_{uuid4().hex[:12]}", table_id=table_id, **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO generation_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                item.id, item.table_id, json.dumps(item.terrains), item.min_level, item.max_level,
                item.min_difficulty, item.max_difficulty, item.weight, item.title,
                json.dumps(item.payload), json.dumps(item.tags),
            ))
        return item

    def update_entry(self, entry_id: str, payload: GenerationEntryCreate) -> GenerationEntry | None:
        if payload.min_level > payload.max_level or payload.min_difficulty > payload.max_difficulty:
            raise ValueError("Els rangs mínims no poden superar els màxims")
        with self.database.connect() as db:
            if not db.execute("SELECT 1 FROM generation_entries WHERE id=?", (entry_id,)).fetchone():
                return None
            db.execute("""UPDATE generation_entries SET terrains=?, min_level=?, max_level=?,
                       min_difficulty=?, max_difficulty=?, weight=?, title=?, payload=?, tags=? WHERE id=?""", (
                json.dumps(payload.terrains), payload.min_level, payload.max_level,
                payload.min_difficulty, payload.max_difficulty, payload.weight, payload.title,
                json.dumps(payload.payload), json.dumps(payload.tags), entry_id,
            ))
            row = db.execute("SELECT * FROM generation_entries WHERE id=?", (entry_id,)).fetchone()
        return GenerationEntry(**{**dict(row), "terrains": json.loads(row["terrains"]), "payload": json.loads(row["payload"]), "tags": json.loads(row["tags"])})

    def delete_entry(self, entry_id: str) -> bool:
        with self.database.connect() as db:
            exists = bool(db.execute("SELECT 1 FROM generation_entries WHERE id=?", (entry_id,)).fetchone())
            if exists:
                db.execute("DELETE FROM generation_entries WHERE id=?", (entry_id,))
            return exists

    def list_entries(self, campaign_id: str, kind: str, terrain: str, level: int, difficulty: int) -> list[GenerationEntry]:
        with self.database.connect() as db:
            rows = db.execute("""SELECT e.* FROM generation_entries e JOIN generation_tables t ON t.id=e.table_id
                                 WHERE t.campaign_id=? AND t.kind=? AND e.min_level<=? AND e.max_level>=?
                                 AND e.min_difficulty<=? AND e.max_difficulty>=?""",
                              (campaign_id, kind, level, level, difficulty, difficulty)).fetchall()
        entries = [GenerationEntry(**{**dict(row), "terrains": json.loads(row["terrains"]), "payload": json.loads(row["payload"]), "tags": json.loads(row["tags"])}) for row in rows]
        return [entry for entry in entries if not entry.terrains or terrain in entry.terrains or "any" in entry.terrains]

    def list_table_entries(self, table_id: str) -> list[GenerationEntry]:
        with self.database.connect() as db:
            rows = db.execute("SELECT * FROM generation_entries WHERE table_id=? ORDER BY title", (table_id,)).fetchall()
        return [GenerationEntry(**{**dict(row), "terrains": json.loads(row["terrains"]), "payload": json.loads(row["payload"]), "tags": json.loads(row["tags"])}) for row in rows]

    def list_campaign_entries(self, campaign_id: str) -> list[GenerationEntry]:
        entries: list[GenerationEntry] = []
        for table in self.list_tables(campaign_id):
            entries.extend(self.list_table_entries(table.id))
        return entries

    def save_encounter(self, item: Encounter) -> Encounter:
        with self.database.connect() as db:
            db.execute("INSERT INTO encounters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                item.id, item.campaign_id, item.location_id, item.terrain, item.party_level,
                item.party_size, item.difficulty, item.encounter_type, item.title, item.description,
                json.dumps(item.objectives), json.dumps(item.complications), json.dumps(item.context_reasons),
                item.status, item.created_at,
            ))
        return item

    def list_encounters(self, campaign_id: str) -> list[Encounter]:
        with self.database.connect() as db:
            rows = db.execute("SELECT * FROM encounters WHERE campaign_id=? ORDER BY created_at DESC", (campaign_id,))
            return [Encounter(**{**dict(row), "objectives": json.loads(row["objectives"]), "complications": json.loads(row["complications"]), "context_reasons": json.loads(row["context_reasons"])}) for row in rows]

    def get_encounter(self, encounter_id: str) -> Encounter | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM encounters WHERE id=?", (encounter_id,)).fetchone()
            return Encounter(**{**dict(row), "objectives": json.loads(row["objectives"]), "complications": json.loads(row["complications"]), "context_reasons": json.loads(row["context_reasons"])}) if row else None

    def update_encounter_status(self, encounter_id: str, status: str) -> Encounter | None:
        with self.database.connect() as db:
            if not db.execute("SELECT 1 FROM encounters WHERE id=?", (encounter_id,)).fetchone():
                return None
            db.execute("UPDATE encounters SET status=? WHERE id=?", (status, encounter_id))
        return self.get_encounter(encounter_id)

    def save_reward(self, item: Reward) -> Reward:
        with self.database.connect() as db:
            db.execute("""INSERT INTO rewards(id,campaign_id,encounter_id,location_id,terrain,party_level,difficulty,
                mode,fortune_roll,tier,title,items,narrative_rewards,context_reasons,created_at,claimed,claimed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                item.id, item.campaign_id, item.encounter_id, item.location_id, item.terrain,
                item.party_level, item.difficulty, item.mode, item.fortune_roll, item.tier, item.title,
                json.dumps(item.items), json.dumps(item.narrative_rewards), json.dumps(item.context_reasons), item.created_at,
                int(item.claimed), item.claimed_at,
            ))
        return item

    def get_reward(self, reward_id: str) -> Reward | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM rewards WHERE id=?", (reward_id,)).fetchone()
        return self._reward(row) if row else None

    @staticmethod
    def _reward(row) -> Reward:
        return Reward(**{**dict(row), "items": json.loads(row["items"]),
                         "narrative_rewards": json.loads(row["narrative_rewards"]),
                         "context_reasons": json.loads(row["context_reasons"])})

    def mark_reward_claimed(self, reward_id: str) -> Reward | None:
        with self.database.connect() as db:
            if not db.execute("SELECT 1 FROM rewards WHERE id=? AND claimed=0", (reward_id,)).fetchone():
                return None
            db.execute("UPDATE rewards SET claimed=1,claimed_at=? WHERE id=?", (utc_now(), reward_id))
        return self.get_reward(reward_id)

    def list_rewards(self, campaign_id: str) -> list[Reward]:
        with self.database.connect() as db:
            rows = db.execute("SELECT * FROM rewards WHERE campaign_id=? ORDER BY created_at DESC", (campaign_id,))
            return [self._reward(row) for row in rows]
