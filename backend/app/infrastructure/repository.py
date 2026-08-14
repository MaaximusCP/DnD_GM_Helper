import json
import re
from uuid import uuid4

from app.domain.models import (
    Campaign, CampaignBundle, CampaignCreate, CampaignImport, CampaignUpdate, EventProposal, EventUpdate,
    Faction, FactionCreate, FactionUpdate, Location, LocationCreate, LocationUpdate,
    Memory, MemoryCreate, NPC, NPCCreate, NPCUpdate, PartySettings,
    PartySettingsUpdate, Relationship, SearchResult, Session, utc_now,
)
from app.infrastructure.database import Database


class SQLiteRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_campaigns(self) -> list[Campaign]:
        with self.database.connect() as db:
            return [Campaign(**dict(row)) for row in db.execute("SELECT * FROM campaigns ORDER BY name")]

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
            return Campaign(**dict(row)) if row else None

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return cleaned[:40] or uuid4().hex[:12]

    def create_campaign(self, payload: CampaignCreate) -> Campaign:
        campaign_id = f"campaign_{self._slug(payload.name)}_{uuid4().hex[:6]}"
        location_id = f"location_{self._slug(payload.location_name)}_{uuid4().hex[:6]}"
        with self.database.connect() as db:
            db.execute("""INSERT INTO campaigns(id, name, system, rules_profile, current_day, current_location_id)
                          VALUES (?, ?, ?, ?, 1, ?)""", (campaign_id, payload.name, payload.system, payload.rules_profile, location_id))
            db.execute("INSERT INTO locations(id, campaign_id, name, description, terrain) VALUES (?, ?, ?, '', 'urban')", (location_id, campaign_id, payload.location_name))
            db.execute("INSERT INTO world_state VALUES (?, 'wanted_level', '0')", (campaign_id,))
            db.execute("INSERT INTO party_settings(campaign_id) VALUES (?)", (campaign_id,))
        return self.get_campaign(campaign_id)  # type: ignore[return-value]

    def update_campaign(self, campaign_id: str, payload: CampaignUpdate) -> Campaign | None:
        current = self.get_campaign(campaign_id)
        if not current:
            return None
        values = payload.model_dump(exclude_none=True)
        if payload.current_location_id:
            location = self.get_location(payload.current_location_id)
            if not location or location.campaign_id != campaign_id:
                raise ValueError("La localització no pertany a aquesta campanya")
        if values:
            allowed = {"name", "current_day", "current_location_id", "rules_profile", "archived"}
            assignments = ", ".join(f"{key} = ?" for key in values if key in allowed)
            parameters = [values[key] for key in values if key in allowed]
            with self.database.connect() as db:
                db.execute(f"UPDATE campaigns SET {assignments} WHERE id = ?", (*parameters, campaign_id))
        return self.get_campaign(campaign_id)

    def get_location(self, location_id: str) -> Location | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
            return Location(**dict(row)) if row else None

    def list_locations(self, campaign_id: str) -> list[Location]:
        with self.database.connect() as db:
            return [Location(**dict(row)) for row in db.execute("SELECT * FROM locations WHERE campaign_id = ? ORDER BY name", (campaign_id,))]

    def create_location(self, campaign_id: str, payload: LocationCreate) -> Location:
        item = Location(id=f"location_{self._slug(payload.name)}_{uuid4().hex[:6]}", campaign_id=campaign_id, **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO locations(id, campaign_id, name, description, terrain) VALUES (?, ?, ?, ?, ?)", (item.id, item.campaign_id, item.name, item.description, item.terrain))
        return item

    def update_location(self, location_id: str, payload: LocationUpdate) -> Location | None:
        current = self.get_location(location_id)
        if not current:
            return None
        values = payload.model_dump(exclude_none=True)
        if values:
            assignments = ", ".join(f"{key} = ?" for key in values)
            with self.database.connect() as db:
                db.execute(f"UPDATE locations SET {assignments} WHERE id = ?", (*values.values(), location_id))
        return self.get_location(location_id)

    def delete_location(self, location_id: str) -> bool:
        location = self.get_location(location_id)
        if not location:
            return False
        campaign = self.get_campaign(location.campaign_id)
        if campaign and campaign.current_location_id == location_id:
            raise ValueError("No es pot eliminar la localització activa")
        with self.database.connect() as db:
            if db.execute("SELECT 1 FROM npcs WHERE location_id=? LIMIT 1", (location_id,)).fetchone():
                raise ValueError("Mou els NPC a una altra localització abans d'eliminar-la")
            db.execute("DELETE FROM locations WHERE id=?", (location_id,))
        return True

    def list_factions(self, campaign_id: str) -> list[Faction]:
        with self.database.connect() as db:
            rows = db.execute("SELECT * FROM factions WHERE campaign_id = ? ORDER BY name", (campaign_id,))
            return [Faction(**dict(row)) for row in rows]

    def get_faction(self, faction_id: str) -> Faction | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM factions WHERE id = ?", (faction_id,)).fetchone()
            return Faction(**dict(row)) if row else None

    def create_faction(self, campaign_id: str, payload: FactionCreate) -> Faction:
        item = Faction(id=f"faction_{self._slug(payload.name)}_{uuid4().hex[:6]}", campaign_id=campaign_id, **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO factions VALUES (?, ?, ?, ?)", (item.id, item.campaign_id, item.name, item.description))
            db.execute("INSERT INTO world_state VALUES (?, ?, '0')", (campaign_id, f"reputation:{item.id}"))
        return item

    def update_faction(self, faction_id: str, payload: FactionUpdate) -> Faction | None:
        current = self.get_faction(faction_id)
        if not current:
            return None
        values = payload.model_dump(exclude_none=True)
        if values:
            assignments = ", ".join(f"{key} = ?" for key in values)
            with self.database.connect() as db:
                db.execute(f"UPDATE factions SET {assignments} WHERE id = ?", (*values.values(), faction_id))
        return self.get_faction(faction_id)

    def delete_faction(self, faction_id: str) -> bool:
        faction = self.get_faction(faction_id)
        if not faction:
            return False
        with self.database.connect() as db:
            db.execute("UPDATE npcs SET faction_id=NULL WHERE faction_id=?", (faction_id,))
            db.execute("DELETE FROM world_state WHERE campaign_id=? AND key=?", (faction.campaign_id, f"reputation:{faction_id}"))
            db.execute("DELETE FROM factions WHERE id=?", (faction_id,))
        return True

    def list_npcs(self, campaign_id: str) -> list[NPC]:
        with self.database.connect() as db:
            ids = [row["id"] for row in db.execute("SELECT id FROM npcs WHERE campaign_id = ? ORDER BY name", (campaign_id,))]
        return [npc for npc_id in ids if (npc := self.get_npc(npc_id))]

    def get_npc(self, npc_id: str) -> NPC | None:
        with self.database.connect() as db:
            row = db.execute(
                """SELECT n.*, r.trust, r.respect, r.fear, r.affection
                   FROM npcs n JOIN relationships r ON r.npc_id = n.id WHERE n.id = ?""",
                (npc_id,),
            ).fetchone()
            if not row:
                return None
            memories = [Memory(**dict(item)) for item in db.execute(
                "SELECT * FROM memories WHERE npc_id = ? ORDER BY created_at DESC LIMIT 10", (npc_id,)
            )]
            return NPC(
                id=row["id"], campaign_id=row["campaign_id"], name=row["name"],
                location_id=row["location_id"], faction_id=row["faction_id"],
                traits=json.loads(row["traits"]), goals=json.loads(row["goals"]),
                values=json.loads(row["values_json"]), secrets=json.loads(row["secrets"]),
                relationship=Relationship(trust=row["trust"], respect=row["respect"], fear=row["fear"], affection=row["affection"]),
                memories=memories,
            )

    def create_npc(self, campaign_id: str, payload: NPCCreate) -> NPC:
        npc_id = f"npc_{self._slug(payload.name)}_{uuid4().hex[:6]}"
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO npcs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (npc_id, campaign_id, payload.name, payload.location_id, payload.faction_id,
                 json.dumps(payload.traits), json.dumps(payload.goals), json.dumps(payload.values), json.dumps(payload.secrets)),
            )
            relation = payload.relationship
            db.execute("INSERT INTO relationships VALUES (?, ?, ?, ?, ?)", (npc_id, relation.trust, relation.respect, relation.fear, relation.affection))
        return self.get_npc(npc_id)  # type: ignore[return-value]

    def update_npc(self, npc_id: str, payload: NPCUpdate) -> NPC | None:
        if not self.get_npc(npc_id):
            return None
        values = payload.model_dump(exclude_none=True, exclude={"relationship"})
        mapping = {"values": "values_json"}
        json_fields = {"traits", "goals", "values", "secrets"}
        if values:
            assignments = ", ".join(f"{mapping.get(key, key)} = ?" for key in values)
            parameters = [json.dumps(value) if key in json_fields else value for key, value in values.items()]
            with self.database.connect() as db:
                db.execute(f"UPDATE npcs SET {assignments} WHERE id = ?", (*parameters, npc_id))
        if payload.relationship:
            relation = payload.relationship
            with self.database.connect() as db:
                db.execute("UPDATE relationships SET trust=?, respect=?, fear=?, affection=? WHERE npc_id=?", (relation.trust, relation.respect, relation.fear, relation.affection, npc_id))
        return self.get_npc(npc_id)

    def delete_npc(self, npc_id: str) -> bool:
        with self.database.connect() as db:
            if not db.execute("SELECT 1 FROM npcs WHERE id = ?", (npc_id,)).fetchone():
                return False
            db.execute("DELETE FROM memories WHERE npc_id = ?", (npc_id,))
            db.execute("DELETE FROM relationships WHERE npc_id = ?", (npc_id,))
            db.execute("DELETE FROM npcs WHERE id = ?", (npc_id,))
            return True

    def add_memory(self, npc_id: str, payload: MemoryCreate) -> Memory:
        memory = Memory(id=f"memory_{uuid4().hex[:12]}", npc_id=npc_id, **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?)", (memory.id, memory.npc_id, memory.text, memory.importance, memory.created_at))
        return memory

    def save_event(self, event: EventProposal) -> None:
        with self.database.connect() as db:
            db.execute(
                """INSERT INTO events(id, campaign_id, title, description, event_type, severity,
                   consequences, status, created_at, location_id, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event.id, event.campaign_id, event.title, event.description, event.event_type,
                 event.severity, event.model_dump_json(include={"consequences"}), event.status, event.created_at,
                 event.location_id, event.visibility),
            )

    def get_event(self, event_id: str) -> EventProposal | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            if not row:
                return None
            consequences = json.loads(row["consequences"])["consequences"]
            return EventProposal(**{**dict(row), "consequences": consequences})

    def list_events(self, campaign_id: str, limit: int = 25) -> list[EventProposal]:
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE campaign_id = ? ORDER BY created_at DESC LIMIT ?", (campaign_id, limit)
            ).fetchall()
        return [EventProposal(**{**dict(row), "consequences": json.loads(row["consequences"])["consequences"]}) for row in rows]

    def update_event(self, event_id: str, payload: EventUpdate) -> EventProposal | None:
        event = self.get_event(event_id)
        if not event:
            return None
        if event.status != "pending":
            raise ValueError("Només es poden editar propostes pendents")
        values = payload.model_dump(exclude_none=True)
        if "consequences" in values:
            values["consequences"] = json.dumps({"consequences": values["consequences"]}, ensure_ascii=False)
        if values:
            assignments = ", ".join(f"{key} = ?" for key in values)
            with self.database.connect() as db:
                db.execute(f"UPDATE events SET {assignments} WHERE id = ?", (*values.values(), event_id))
        return self.get_event(event_id)

    def apply_event(self, event: EventProposal) -> EventProposal:
        if event.status != "pending":
            raise ValueError("Només es poden aplicar esdeveniments pendents")
        with self.database.connect() as db:
            audit_changes: list[dict[str, object]] = []
            for item in event.consequences:
                if item.kind == "relationship":
                    allowed = {"trust", "respect", "fear", "affection"}
                    if item.field not in allowed:
                        raise ValueError("Dimensió de relació no vàlida")
                    previous = db.execute(f"SELECT {item.field} FROM relationships WHERE npc_id = ?", (item.target_id,)).fetchone()
                    if not previous:
                        raise ValueError(f"L'NPC {item.target_id} no existeix")
                    audit_changes.append({"kind": "relationship", "target_id": item.target_id, "field": item.field, "before": previous[item.field]})
                    db.execute(
                        f"UPDATE relationships SET {item.field} = MAX(-100, MIN(100, {item.field} + ?)) WHERE npc_id = ?",
                        (item.delta, item.target_id),
                    )
                elif item.kind in {"wanted", "reputation"}:
                    key = "wanted_level" if item.kind == "wanted" else f"reputation:{item.target_id}"
                    previous = db.execute("SELECT value FROM world_state WHERE campaign_id = ? AND key = ?", (event.campaign_id, key)).fetchone()
                    audit_changes.append({"kind": "world_state", "key": key, "existed": bool(previous), "before": previous["value"] if previous else None})
                    db.execute(
                        """INSERT INTO world_state(campaign_id, key, value) VALUES (?, ?, ?)
                           ON CONFLICT(campaign_id, key) DO UPDATE SET value = CAST(value AS INTEGER) + excluded.value""",
                        (event.campaign_id, key, str(item.delta)),
                    )
                elif item.kind == "memory" and item.text:
                    memory_id = f"memory_{uuid4().hex[:12]}"
                    audit_changes.append({"kind": "memory", "id": memory_id})
                    db.execute(
                        "INSERT INTO memories VALUES (?, ?, ?, 'important', ?)",
                        (memory_id, item.target_id, item.text, utc_now()),
                    )
            db.execute("UPDATE events SET status = 'applied' WHERE id = ?", (event.id,))
            db.execute("INSERT INTO audit_log VALUES (?, ?, ?, ?, NULL, ?)", (f"audit_{uuid4().hex[:12]}", event.campaign_id, event.id, json.dumps(audit_changes), utc_now()))
        return self.get_event(event.id)  # type: ignore[return-value]

    def undo_event(self, event_id: str) -> EventProposal:
        event = self.get_event(event_id)
        if not event or event.status != "applied":
            raise ValueError("L'esdeveniment no està aplicat")
        with self.database.connect() as db:
            audit = db.execute("SELECT * FROM audit_log WHERE event_id = ? AND undone_at IS NULL", (event_id,)).fetchone()
            if not audit:
                raise ValueError("No hi ha informació per desfer aquest esdeveniment")
            for change in reversed(json.loads(audit["changes"])):
                if change["kind"] == "relationship":
                    field = change["field"]
                    if field not in {"trust", "respect", "fear", "affection"}:
                        raise ValueError("Registre d'auditoria no vàlid")
                    db.execute(f"UPDATE relationships SET {field} = ? WHERE npc_id = ?", (change["before"], change["target_id"]))
                elif change["kind"] == "world_state":
                    if change["existed"]:
                        db.execute("UPDATE world_state SET value = ? WHERE campaign_id = ? AND key = ?", (change["before"], event.campaign_id, change["key"]))
                    else:
                        db.execute("DELETE FROM world_state WHERE campaign_id = ? AND key = ?", (event.campaign_id, change["key"]))
                elif change["kind"] == "memory":
                    db.execute("DELETE FROM memories WHERE id = ?", (change["id"],))
            db.execute("UPDATE audit_log SET undone_at = ? WHERE event_id = ?", (utc_now(), event_id))
            db.execute("UPDATE events SET status = 'pending' WHERE id = ?", (event_id,))
        return self.get_event(event_id)  # type: ignore[return-value]

    def ignore_event(self, event_id: str) -> EventProposal | None:
        with self.database.connect() as db:
            current = db.execute("SELECT status FROM events WHERE id = ?", (event_id,)).fetchone()
            if current and current["status"] != "pending":
                raise ValueError("Només es poden ignorar propostes pendents")
            db.execute("UPDATE events SET status = 'ignored' WHERE id = ? AND status = 'pending'", (event_id,))
        return self.get_event(event_id)

    def get_world_state(self, campaign_id: str) -> dict[str, int | str]:
        with self.database.connect() as db:
            rows = db.execute("SELECT key, value FROM world_state WHERE campaign_id = ?", (campaign_id,))
            result: dict[str, int | str] = {}
            for row in rows:
                try:
                    result[row["key"]] = int(row["value"])
                except ValueError:
                    result[row["key"]] = row["value"]
            return result

    def set_world_state(self, campaign_id: str, key: str, value: int | str) -> dict[str, int | str]:
        normalized = key.strip()
        if len(normalized) < 2:
            raise ValueError("La clau ha de tenir almenys dos caràcters")
        if len(str(value)) > 1000:
            raise ValueError("El valor no pot superar els 1.000 caràcters")
        with self.database.connect() as db:
            db.execute("""INSERT INTO world_state(campaign_id, key, value) VALUES (?, ?, ?)
                          ON CONFLICT(campaign_id, key) DO UPDATE SET value=excluded.value""",
                       (campaign_id, normalized, str(value)))
        return self.get_world_state(campaign_id)

    def delete_world_state(self, campaign_id: str, key: str) -> bool:
        if key == "wanted_level" or key.startswith("reputation:"):
            raise ValueError("Aquesta variable és gestionada pel motor")
        with self.database.connect() as db:
            cursor = db.execute("DELETE FROM world_state WHERE campaign_id=? AND key=?", (campaign_id, key))
            return cursor.rowcount > 0

    def get_party_settings(self, campaign_id: str) -> PartySettings:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM party_settings WHERE campaign_id=?", (campaign_id,)).fetchone()
            if not row:
                db.execute("INSERT INTO party_settings(campaign_id) VALUES (?)", (campaign_id,))
                row = db.execute("SELECT * FROM party_settings WHERE campaign_id=?", (campaign_id,)).fetchone()
            return PartySettings(**dict(row))

    def update_party_settings(self, campaign_id: str, payload: PartySettingsUpdate) -> PartySettings:
        with self.database.connect() as db:
            db.execute("""INSERT INTO party_settings(campaign_id, name, level, size, notes)
                          VALUES (?, ?, ?, ?, ?)
                          ON CONFLICT(campaign_id) DO UPDATE SET name=excluded.name,
                          level=excluded.level, size=excluded.size, notes=excluded.notes""",
                       (campaign_id, payload.name, payload.level, payload.size, payload.notes))
        return self.get_party_settings(campaign_id)

    def start_session(self, campaign_id: str) -> Session:
        session = Session(id=f"session_{uuid4().hex[:12]}", campaign_id=campaign_id)
        with self.database.connect() as db:
            if db.execute("SELECT 1 FROM sessions WHERE campaign_id = ? AND ended_at IS NULL", (campaign_id,)).fetchone():
                raise ValueError("Ja hi ha una sessió activa")
            db.execute(
                "INSERT INTO sessions(id, campaign_id, started_at, summary) VALUES (?, ?, ?, '')",
                (session.id, session.campaign_id, session.started_at),
            )
        return session

    def list_sessions(self, campaign_id: str) -> list[Session]:
        with self.database.connect() as db:
            return [Session(**dict(row)) for row in db.execute("SELECT * FROM sessions WHERE campaign_id = ? ORDER BY started_at DESC", (campaign_id,))]

    def end_session(self, session_id: str, summary: str) -> Session | None:
        with self.database.connect() as db:
            db.execute("UPDATE sessions SET ended_at = ?, summary = ? WHERE id = ? AND ended_at IS NULL", (utc_now(), summary, session_id))
            row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return Session(**dict(row)) if row else None

    def search(self, campaign_id: str, query: str) -> list[SearchResult]:
        like = f"%{query.strip()}%"
        results: list[SearchResult] = []
        with self.database.connect() as db:
            specs = [
                ("npc", "SELECT id, name title, traits excerpt FROM npcs WHERE campaign_id=? AND (name LIKE ? OR traits LIKE ? OR goals LIKE ?) LIMIT 10"),
                ("event", "SELECT id, title, description excerpt FROM events WHERE campaign_id=? AND (title LIKE ? OR description LIKE ? OR event_type LIKE ?) LIMIT 10"),
                ("location", "SELECT id, name title, description excerpt FROM locations WHERE campaign_id=? AND (name LIKE ? OR description LIKE ? OR id LIKE ?) LIMIT 10"),
                ("faction", "SELECT id, name title, description excerpt FROM factions WHERE campaign_id=? AND (name LIKE ? OR description LIKE ? OR id LIKE ?) LIMIT 10"),
            ]
            for kind, sql in specs:
                for row in db.execute(sql, (campaign_id, like, like, like)):
                    results.append(SearchResult(kind=kind, **dict(row)))
            for row in db.execute("""SELECT m.id, n.name title, m.text excerpt FROM memories m JOIN npcs n ON n.id=m.npc_id
                                     WHERE n.campaign_id=? AND m.text LIKE ? LIMIT 10""", (campaign_id, like)):
                results.append(SearchResult(kind="memory", **dict(row)))
        return results[:30]

    def export_campaign(self, campaign_id: str) -> CampaignBundle | None:
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None
        from app.infrastructure.simulation_repository import SimulationRepository
        from app.infrastructure.campaign_tools_repository import CampaignToolsRepository
        from app.infrastructure.party_repository import PartyRepository
        simulation = SimulationRepository(self.database)
        tools = CampaignToolsRepository(self.database)
        party_repo = PartyRepository(self.database)
        return CampaignBundle(
            campaign=campaign, locations=self.list_locations(campaign_id), factions=self.list_factions(campaign_id),
            npcs=self.list_npcs(campaign_id), events=self.list_events(campaign_id, 10000),
            world_state=self.get_world_state(campaign_id), party=self.get_party_settings(campaign_id),
            knowledge=simulation.list_campaign_knowledge(campaign_id),
            rumors=simulation.list_rumors(campaign_id), generation_tables=simulation.list_tables(campaign_id),
            generation_entries=simulation.list_campaign_entries(campaign_id), encounters=simulation.list_encounters(campaign_id),
            rewards=simulation.list_rewards(campaign_id),
            lore_entries=tools.list_lore(campaign_id), hex_cells=tools.list_hexes(campaign_id),
            combats=tools.list_combats(campaign_id),
            hexcrawl_settings=tools.get_hexcrawl_settings(campaign_id),
            expedition_state=tools.get_expedition_state(campaign_id),
            travel_logs=tools.list_travel_logs(campaign_id, 10000),
            player_view_settings=tools.get_player_view_settings(campaign_id),
            characters=party_repo.list_characters(campaign_id), inventory=party_repo.list_inventory(campaign_id),
            treasury=party_repo.get_treasury(campaign_id),
            inventory_transactions=party_repo.list_transactions(campaign_id, 10000),
        )

    def import_campaign(self, package: CampaignBundle) -> Campaign:
        if self.get_campaign(package.campaign.id):
            raise ValueError("Ja existeix una campanya amb aquest identificador")
        location_ids = {item.id for item in package.locations}
        faction_ids = {item.id for item in package.factions}
        if package.campaign.current_location_id not in location_ids:
            raise ValueError("La localització actual no existeix dins del paquet")
        if len(location_ids) != len(package.locations) or len(faction_ids) != len(package.factions):
            raise ValueError("El paquet conté identificadors duplicats")
        for npc in package.npcs:
            if npc.location_id not in location_ids:
                raise ValueError(f"La localització de l'NPC {npc.name} no existeix")
            if npc.faction_id and npc.faction_id not in faction_ids:
                raise ValueError(f"La facció de l'NPC {npc.name} no existeix")
        with self.database.connect() as db:
            c = package.campaign
            db.execute("""INSERT INTO campaigns(id, name, system, rules_profile, current_day, current_location_id, archived)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""", (c.id, c.name, c.system, c.rules_profile, c.current_day, c.current_location_id, int(c.archived)))
            if package.party:
                db.execute("INSERT INTO party_settings VALUES (?, ?, ?, ?, ?)",
                           (c.id, package.party.name, package.party.level, package.party.size, package.party.notes))
            else:
                db.execute("INSERT INTO party_settings(campaign_id) VALUES (?)", (c.id,))
            for item in package.locations:
                db.execute("INSERT INTO locations(id, campaign_id, name, description, terrain) VALUES (?, ?, ?, ?, ?)", (item.id, c.id, item.name, item.description, item.terrain))
            for item in package.factions:
                db.execute("INSERT INTO factions VALUES (?, ?, ?, ?)", (item.id, c.id, item.name, item.description))
            for npc in package.npcs:
                db.execute("INSERT INTO npcs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (npc.id, c.id, npc.name, npc.location_id, npc.faction_id, json.dumps(npc.traits), json.dumps(npc.goals), json.dumps(npc.values), json.dumps(npc.secrets)))
                r = npc.relationship
                db.execute("INSERT INTO relationships VALUES (?, ?, ?, ?, ?)", (npc.id, r.trust, r.respect, r.fear, r.affection))
                for memory in npc.memories:
                    db.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?)", (memory.id, npc.id, memory.text, memory.importance, memory.created_at))
            for event in package.events:
                db.execute("""INSERT INTO events(id, campaign_id, title, description, event_type, severity,
                           consequences, status, created_at, location_id, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           (event.id, c.id, event.title, event.description, event.event_type, event.severity,
                            json.dumps({"consequences": [x.model_dump() for x in event.consequences]}), event.status,
                            event.created_at, event.location_id, event.visibility))
            for key, value in package.world_state.items():
                db.execute("INSERT INTO world_state VALUES (?, ?, ?)", (c.id, key, str(value)))
            for item in package.knowledge:
                db.execute("INSERT INTO knowledge VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.id, item.npc_id, item.subject, item.content, item.confidence, item.truth_status, item.source_type, item.source_id, item.created_at))
            for item in package.rumors:
                db.execute("INSERT INTO rumors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.id, c.id, item.origin_location_id, item.subject, item.content, item.credibility, item.spread, item.status, item.source_event_id, item.created_at))
            for item in package.generation_tables:
                db.execute("INSERT INTO generation_tables VALUES (?, ?, ?, ?, ?, ?)", (item.id, c.id, item.kind, item.name, item.description, item.created_at))
            for item in package.generation_entries:
                db.execute("INSERT INTO generation_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.id, item.table_id, json.dumps(item.terrains), item.min_level, item.max_level, item.min_difficulty, item.max_difficulty, item.weight, item.title, json.dumps(item.payload), json.dumps(item.tags)))
            for item in package.encounters:
                db.execute("INSERT INTO encounters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.id, c.id, item.location_id, item.terrain, item.party_level, item.party_size, item.difficulty, item.encounter_type, item.title, item.description, json.dumps(item.objectives), json.dumps(item.complications), json.dumps(item.context_reasons), item.status, item.created_at))
            for item in package.rewards:
                db.execute("""INSERT INTO rewards(id,campaign_id,encounter_id,location_id,terrain,party_level,difficulty,mode,
                           fortune_roll,tier,title,items,narrative_rewards,context_reasons,created_at,claimed,claimed_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (item.id, c.id, item.encounter_id, item.location_id,
                           item.terrain, item.party_level, item.difficulty, item.mode, item.fortune_roll, item.tier, item.title,
                           json.dumps(item.items), json.dumps(item.narrative_rewards), json.dumps(item.context_reasons),
                           item.created_at, int(item.claimed), item.claimed_at))
            for item in package.lore_entries:
                db.execute("INSERT INTO lore_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.id, c.id, item.layer, item.category, item.title, item.content, item.source_id, item.location_id, item.created_at))
            for item in package.hex_cells:
                db.execute("INSERT INTO hex_cells VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.id, c.id, item.q, item.r, item.terrain, item.title, item.discovery, item.travel_cost, item.encounter_chance, item.player_notes, item.dm_notes, item.location_id, item.source_id))
            for combat in package.combats:
                db.execute("""INSERT INTO combats(id,campaign_id,name,status,round,turn_index,encounter_id,summary,created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (combat.id, c.id, combat.name, combat.status, combat.round, combat.turn_index, combat.encounter_id, combat.summary, combat.created_at))
                for item in combat.combatants:
                    db.execute("""INSERT INTO combatants(id,combat_id,name,kind,initiative,armor_class,max_hp,current_hp,temp_hp,
                               initiative_bonus,concentration,reaction_available,legendary_actions,legendary_actions_max,notes,
                               conditions,actions,source_id,reference_id,character_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                               (item.id, combat.id, item.name, item.kind, item.initiative, item.armor_class, item.max_hp,
                                item.current_hp, item.temp_hp, item.initiative_bonus, int(item.concentration),
                                int(item.reaction_available), item.legendary_actions, item.legendary_actions_max, item.notes,
                                json.dumps(item.conditions), json.dumps(item.actions), item.source_id, item.reference_id, item.character_id))
            if package.hexcrawl_settings:
                item = package.hexcrawl_settings
                db.execute("INSERT INTO hexcrawl_settings VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (c.id, int(item.track_weather), int(item.track_navigation), int(item.track_food), int(item.track_water), int(item.track_fatigue), int(item.track_encounters), int(item.track_foraging), int(item.auto_discover), item.default_pace, item.hex_distance, item.distance_unit))
            else:
                db.execute("INSERT INTO hexcrawl_settings(campaign_id) VALUES (?)", (c.id,))
            if package.player_view_settings:
                item = package.player_view_settings
                db.execute("INSERT INTO player_view_settings VALUES (?,?,?,?,?,?,?,?,?,?)", (c.id, int(item.enabled), int(item.show_map), int(item.show_rumors), int(item.show_resources), int(item.show_weather), int(item.show_combat), int(item.show_enemy_hp), int(item.show_characters), int(item.show_inventory)))
            else:
                db.execute("INSERT INTO player_view_settings(campaign_id) VALUES (?)", (c.id,))
            if package.expedition_state:
                item = package.expedition_state
                db.execute("INSERT INTO expedition_state VALUES (?,?,?,?,?,?,?,?,?)", (c.id, item.current_hex_id, item.food, item.water, item.supplies, item.exhaustion, int(item.lost), item.weather, item.updated_at))
            for item in package.travel_logs:
                db.execute("""INSERT INTO travel_logs(id,campaign_id,origin_hex_id,destination_hex_id,route,pace,days,
                           distance,distance_unit,weather,navigation_roll,encounter_roll,food_used,water_used,exhaustion_delta,
                           encounter_triggered,encounter_id,reached_destination,notes,created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (item.id, c.id, item.origin_hex_id,
                           item.destination_hex_id, json.dumps(item.route), item.pace, item.days, item.distance,
                           item.distance_unit, item.weather, item.navigation_roll, item.encounter_roll, item.food_used, item.water_used,
                           item.exhaustion_delta, int(item.encounter_triggered), item.encounter_id,
                           int(item.reached_destination), json.dumps(item.notes), item.created_at))
            for item in package.characters:
                values = item.model_dump()
                for key in ("ability_scores", "saving_throws", "skills", "conditions", "spell_slots", "spell_slots_max", "resources"):
                    values[key] = json.dumps(values[key])
                values["campaign_id"] = c.id
                db.execute(f"INSERT INTO characters({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))
            for item in package.inventory:
                values = item.model_dump(); values["campaign_id"] = c.id
                db.execute(f"INSERT INTO inventory_items({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))
            treasury = package.treasury
            if treasury:
                db.execute("INSERT INTO treasury VALUES (?,?,?,?,?,?,?)", (c.id, treasury.cp, treasury.sp, treasury.ep, treasury.gp, treasury.pp, treasury.updated_at))
            else:
                db.execute("INSERT INTO treasury(campaign_id,updated_at) VALUES (?,datetime('now'))", (c.id,))
            for item in package.inventory_transactions:
                db.execute("INSERT INTO inventory_transactions VALUES (?,?,?,?,?,?,?,?,?,?)", (item.id, c.id, item.kind,
                           item.description, item.item_id, item.character_id, item.currency, item.currency_delta,
                           item.quantity_delta, item.created_at))
        return self.get_campaign(c.id)  # type: ignore[return-value]
