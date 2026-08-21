import json
from uuid import uuid4

from app.domain.models import (
    Combat, CombatCreate, CombatLog, CombatUpdate, Combatant, CombatantCreate, CombatantUpdate,
    DiceRoll, DiceRollRequest,
    ExpeditionState, ExpeditionStateUpdate, HexCell, HexCellCreate, HexCellUpdate, HexRevealRequest,
    HexcrawlSettings, HexcrawlSettingsUpdate, LoreEntry, LoreEntryCreate, LoreEntryUpdate,
    PlayerViewSettings, PlayerViewSettingsUpdate, TravelLog, utc_now,
)
from app.infrastructure.database import Database


class CampaignToolsRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _dice_roll(row) -> DiceRoll:
        data = dict(row)
        data["dice"] = json.loads(data["dice"])
        data["kept"] = json.loads(data["kept"])
        data["success"] = None if data["success"] is None else bool(data["success"])
        return DiceRoll(**data)

    def list_dice_rolls(self, campaign_id: str, limit: int = 50) -> list[DiceRoll]:
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT * FROM dice_rolls WHERE campaign_id=? ORDER BY created_at DESC LIMIT ?",
                (campaign_id, limit),
            )
            return [self._dice_roll(row) for row in rows]

    def add_dice_roll(self, campaign_id: str, payload: DiceRollRequest, result: dict) -> DiceRoll:
        item = DiceRoll(id=f"roll_{uuid4().hex[:12]}", campaign_id=campaign_id,
                        **{**payload.model_dump(), **result})
        with self.database.connect() as db:
            db.execute(
                """INSERT INTO dice_rolls(id,campaign_id,notation,label,actor,mode,dice,kept,modifier,total,dc,success,critical,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item.id, item.campaign_id, item.notation, item.label, item.actor, item.mode,
                 json.dumps(item.dice), json.dumps(item.kept), item.modifier, item.total, item.dc,
                 None if item.success is None else int(item.success), item.critical, item.created_at),
            )
        return item

    def clear_dice_rolls(self, campaign_id: str) -> int:
        with self.database.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM dice_rolls WHERE campaign_id=?", (campaign_id,)).fetchone()[0]
            db.execute("DELETE FROM dice_rolls WHERE campaign_id=?", (campaign_id,))
        return int(count)

    def list_lore(self, campaign_id: str, layer: str | None = None) -> list[LoreEntry]:
        with self.database.connect() as db:
            if layer:
                rows = db.execute("SELECT * FROM lore_entries WHERE campaign_id=? AND layer=? ORDER BY created_at DESC", (campaign_id, layer))
            else:
                rows = db.execute("SELECT * FROM lore_entries WHERE campaign_id=? ORDER BY layer,title", (campaign_id,))
            return [LoreEntry(**dict(row)) for row in rows]

    def create_lore(self, payload: LoreEntryCreate) -> LoreEntry:
        item = LoreEntry(id=f"lore_{uuid4().hex[:12]}", **payload.model_dump())
        with self.database.connect() as db:
            db.execute("""INSERT INTO lore_entries(id,campaign_id,layer,category,title,content,source_id,source_page,location_id,created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                item.id, item.campaign_id, item.layer, item.category, item.title, item.content,
                item.source_id, item.source_page, item.location_id, item.created_at,
            ))
        return item

    def update_lore(self, item_id: str, payload: LoreEntryUpdate) -> LoreEntry | None:
        values = payload.model_dump(exclude_none=True)
        with self.database.connect() as db:
            if not db.execute("SELECT 1 FROM lore_entries WHERE id=?", (item_id,)).fetchone():
                return None
            if values:
                assignments = ", ".join(f"{key}=?" for key in values)
                db.execute(f"UPDATE lore_entries SET {assignments} WHERE id=?", (*values.values(), item_id))
            row = db.execute("SELECT * FROM lore_entries WHERE id=?", (item_id,)).fetchone()
        return LoreEntry(**dict(row))

    def delete_lore(self, item_id: str) -> bool:
        with self.database.connect() as db:
            exists = bool(db.execute("SELECT 1 FROM lore_entries WHERE id=?", (item_id,)).fetchone())
            if exists:
                db.execute("DELETE FROM lore_entries WHERE id=?", (item_id,))
            return exists

    def list_hexes(self, campaign_id: str) -> list[HexCell]:
        with self.database.connect() as db:
            return [self._hex(row) for row in db.execute("SELECT * FROM hex_cells WHERE campaign_id=? ORDER BY r,q", (campaign_id,))]

    @staticmethod
    def _hex(row) -> HexCell:
        data = dict(row); data["risk_tags"] = json.loads(data.get("risk_tags") or "[]")
        return HexCell(**data)

    def get_hex(self, item_id: str) -> HexCell | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM hex_cells WHERE id=?", (item_id,)).fetchone()
        return self._hex(row) if row else None

    def create_hex(self, payload: HexCellCreate) -> HexCell:
        item = HexCell(id=f"hex_{uuid4().hex[:12]}", **payload.model_dump())
        try:
            with self.database.connect() as db:
                db.execute("""INSERT INTO hex_cells(id,campaign_id,q,r,terrain,title,discovery,travel_cost,encounter_chance,
                           player_notes,dm_notes,location_id,source_id,risk_level,alert_level,risk_tags)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    item.id, item.campaign_id, item.q, item.r, item.terrain, item.title, item.discovery,
                    item.travel_cost, item.encounter_chance, item.player_notes, item.dm_notes,
                    item.location_id, item.source_id, item.risk_level, item.alert_level, json.dumps(item.risk_tags),
                ))
        except Exception as exc:
            raise ValueError("Ja existeix un hex amb aquestes coordenades") from exc
        return item

    def update_hex(self, item_id: str, payload: HexCellUpdate) -> HexCell | None:
        values = payload.model_dump(exclude_none=True)
        if "risk_tags" in values:
            values["risk_tags"] = json.dumps(values["risk_tags"])
        with self.database.connect() as db:
            if not db.execute("SELECT 1 FROM hex_cells WHERE id=?", (item_id,)).fetchone():
                return None
            if values:
                assignments = ", ".join(f"{key}=?" for key in values)
                db.execute(f"UPDATE hex_cells SET {assignments} WHERE id=?", (*values.values(), item_id))
            row = db.execute("SELECT * FROM hex_cells WHERE id=?", (item_id,)).fetchone()
        return self._hex(row)

    def reveal_hexes(self, campaign_id: str, payload: HexRevealRequest) -> list[HexCell]:
        center = self.get_hex(payload.center_hex_id)
        if not center or center.campaign_id != campaign_id:
            raise ValueError("L'hex central no pertany a la campanya")
        changed: list[HexCell] = []
        for item in self.list_hexes(campaign_id):
            dq, dr = item.q - center.q, item.r - center.r
            distance = max(abs(dq), abs(dr), abs(dq + dr))
            if distance > payload.radius:
                continue
            target = payload.discovery
            if item.discovery == "explored" or (item.discovery == "discovered" and target == "discovered"):
                changed.append(item)
                continue
            updated = self.update_hex(item.id, HexCellUpdate(discovery=target))
            if updated:
                changed.append(updated)
        return changed

    def delete_hex(self, item_id: str) -> bool:
        item = self.get_hex(item_id)
        if not item:
            return False
        state = self.get_expedition_state(item.campaign_id)
        if state.current_hex_id == item_id:
            raise ValueError("No es pot eliminar l'hex on es troba l'expedició")
        with self.database.connect() as db:
            db.execute("DELETE FROM hex_cells WHERE id=?", (item_id,))
        return True

    def get_hexcrawl_settings(self, campaign_id: str) -> HexcrawlSettings:
        with self.database.connect() as db:
            db.execute("INSERT OR IGNORE INTO hexcrawl_settings(campaign_id) VALUES (?)", (campaign_id,))
            row = db.execute("SELECT * FROM hexcrawl_settings WHERE campaign_id=?", (campaign_id,)).fetchone()
        return HexcrawlSettings(**dict(row))

    def update_hexcrawl_settings(self, campaign_id: str, payload: HexcrawlSettingsUpdate) -> HexcrawlSettings:
        self.get_hexcrawl_settings(campaign_id)
        values = payload.model_dump(exclude_none=True)
        with self.database.connect() as db:
            if values:
                assignments = ", ".join(f"{key}=?" for key in values)
                db.execute(f"UPDATE hexcrawl_settings SET {assignments} WHERE campaign_id=?", (*values.values(), campaign_id))
        return self.get_hexcrawl_settings(campaign_id)

    def get_expedition_state(self, campaign_id: str) -> ExpeditionState:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM expedition_state WHERE campaign_id=?", (campaign_id,)).fetchone()
            if not row:
                first = db.execute("SELECT id FROM hex_cells WHERE campaign_id=? ORDER BY r,q LIMIT 1", (campaign_id,)).fetchone()
                db.execute("INSERT INTO expedition_state VALUES (?, ?, 40, 80, 10, 0, 0, 'clear', ?)", (campaign_id, first["id"] if first else None, utc_now()))
                row = db.execute("SELECT * FROM expedition_state WHERE campaign_id=?", (campaign_id,)).fetchone()
        return ExpeditionState(**dict(row))

    def update_expedition_state(self, campaign_id: str, payload: ExpeditionStateUpdate) -> ExpeditionState:
        self.get_expedition_state(campaign_id)
        values = payload.model_dump(exclude_none=True)
        values["updated_at"] = utc_now()
        with self.database.connect() as db:
            assignments = ", ".join(f"{key}=?" for key in values)
            db.execute(f"UPDATE expedition_state SET {assignments} WHERE campaign_id=?", (*values.values(), campaign_id))
        return self.get_expedition_state(campaign_id)

    def save_travel_log(self, item: TravelLog) -> TravelLog:
        with self.database.connect() as db:
            db.execute("""INSERT INTO travel_logs(id,campaign_id,origin_hex_id,destination_hex_id,route,pace,days,
                       distance,distance_unit,weather,navigation_roll,encounter_roll,food_used,water_used,exhaustion_delta,
                       encounter_triggered,encounter_id,reached_destination,notes,created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                item.id, item.campaign_id, item.origin_hex_id, item.destination_hex_id, json.dumps(item.route),
                item.pace, item.days, item.distance, item.distance_unit, item.weather, item.navigation_roll, item.encounter_roll,
                item.food_used, item.water_used, item.exhaustion_delta, int(item.encounter_triggered),
                item.encounter_id, int(item.reached_destination), json.dumps(item.notes), item.created_at,
            ))
        return item

    def list_travel_logs(self, campaign_id: str, limit: int = 100) -> list[TravelLog]:
        with self.database.connect() as db:
            rows = db.execute("SELECT * FROM travel_logs WHERE campaign_id=? ORDER BY created_at DESC LIMIT ?", (campaign_id, limit))
            return [TravelLog(**{**dict(row), "route": json.loads(row["route"]), "notes": json.loads(row["notes"])}) for row in rows]

    def get_player_view_settings(self, campaign_id: str) -> PlayerViewSettings:
        with self.database.connect() as db:
            db.execute("INSERT OR IGNORE INTO player_view_settings(campaign_id) VALUES (?)", (campaign_id,))
            row = db.execute("SELECT * FROM player_view_settings WHERE campaign_id=?", (campaign_id,)).fetchone()
        return PlayerViewSettings(**dict(row))

    def update_player_view_settings(self, campaign_id: str, payload: PlayerViewSettingsUpdate) -> PlayerViewSettings:
        self.get_player_view_settings(campaign_id)
        values = payload.model_dump(exclude_none=True)
        with self.database.connect() as db:
            if values:
                assignments = ", ".join(f"{key}=?" for key in values)
                db.execute(f"UPDATE player_view_settings SET {assignments} WHERE campaign_id=?", (*values.values(), campaign_id))
        return self.get_player_view_settings(campaign_id)

    def create_combat(self, payload: CombatCreate) -> Combat:
        item = Combat(id=f"combat_{uuid4().hex[:12]}", **payload.model_dump())
        with self.database.connect() as db:
            db.execute("""INSERT INTO combats(id,campaign_id,name,status,round,turn_index,encounter_id,summary,created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                item.id, item.campaign_id, item.name, item.status, item.round, item.turn_index,
                item.encounter_id, item.summary, item.created_at,
            ))
        self.add_combat_log(item.id, f"Combat iniciat: {item.name}")
        return item

    @staticmethod
    def _combatant(row) -> Combatant:
        return Combatant(**{**dict(row), "conditions": json.loads(row["conditions"]), "actions": json.loads(row["actions"])})

    def get_combat(self, combat_id: str) -> Combat | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM combats WHERE id=?", (combat_id,)).fetchone()
            if not row:
                return None
            combatants = [self._combatant(item) for item in db.execute(
                "SELECT * FROM combatants WHERE combat_id=? ORDER BY initiative DESC, name", (combat_id,)
            )]
        turn_index = min(row["turn_index"], max(0, len(combatants) - 1))
        return Combat(**{**dict(row), "turn_index": turn_index}, combatants=combatants)

    def list_combats(self, campaign_id: str) -> list[Combat]:
        with self.database.connect() as db:
            ids = [row["id"] for row in db.execute("SELECT id FROM combats WHERE campaign_id=? ORDER BY created_at DESC", (campaign_id,))]
        return [item for combat_id in ids if (item := self.get_combat(combat_id))]

    def update_combat(self, combat_id: str, payload: CombatUpdate) -> Combat | None:
        values = payload.model_dump(exclude_none=True)
        with self.database.connect() as db:
            if not db.execute("SELECT 1 FROM combats WHERE id=?", (combat_id,)).fetchone():
                return None
            if values:
                assignments = ", ".join(f"{key}=?" for key in values)
                db.execute(f"UPDATE combats SET {assignments} WHERE id=?", (*values.values(), combat_id))
        if values.get("status") == "completed":
            self.add_combat_log(combat_id, "Combat finalitzat")
        return self.get_combat(combat_id)

    def add_combatant(self, combat_id: str, payload: CombatantCreate) -> Combatant:
        if not self.get_combat(combat_id):
            raise ValueError("Combat no trobat")
        values = payload.model_dump()
        values["current_hp"] = payload.current_hp if payload.current_hp is not None else payload.max_hp
        item = Combatant(id=f"combatant_{uuid4().hex[:12]}", combat_id=combat_id, **values)
        with self.database.connect() as db:
            db.execute("""INSERT INTO combatants(id,combat_id,name,kind,initiative,armor_class,max_hp,current_hp,temp_hp,
                       initiative_bonus,concentration,reaction_available,legendary_actions,legendary_actions_max,notes,
                       conditions,actions,source_id,reference_id,character_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                item.id, item.combat_id, item.name, item.kind, item.initiative, item.armor_class,
                item.max_hp, item.current_hp, item.temp_hp, item.initiative_bonus, int(item.concentration),
                int(item.reaction_available), item.legendary_actions, item.legendary_actions_max, item.notes,
                json.dumps(item.conditions), json.dumps(item.actions), item.source_id, item.reference_id, item.character_id,
            ))
        self.add_combat_log(combat_id, f"{item.name} entra al combat")
        return item

    def update_combatant(self, item_id: str, payload: CombatantUpdate) -> Combatant | None:
        values = payload.model_dump(exclude_none=True)
        if "conditions" in values:
            values["conditions"] = json.dumps(values["conditions"])
        if "actions" in values:
            values["actions"] = json.dumps(values["actions"])
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM combatants WHERE id=?", (item_id,)).fetchone()
            if row["character_id"]:
                sync = {key: values[key] for key in ("current_hp", "max_hp", "temp_hp", "conditions") if key in values}
                if "conditions" in sync and isinstance(sync["conditions"], list):
                    sync["conditions"] = json.dumps(sync["conditions"])
                if sync:
                    db.execute(f"UPDATE characters SET {','.join(f'{key}=?' for key in sync)} WHERE id=?", (*sync.values(), row["character_id"]))
            if not row:
                return None
            previous_hp = row["current_hp"]
            if "current_hp" in values:
                maximum = values.get("max_hp", row["max_hp"])
                values["current_hp"] = min(values["current_hp"], maximum)
            if values:
                assignments = ", ".join(f"{key}=?" for key in values)
                db.execute(f"UPDATE combatants SET {assignments} WHERE id=?", (*values.values(), item_id))
            row = db.execute("SELECT * FROM combatants WHERE id=?", (item_id,)).fetchone()
        item = self._combatant(row)
        if "current_hp" in values and values["current_hp"] != previous_hp:
            delta = values["current_hp"] - previous_hp
            kind = "healing" if delta > 0 else "damage"
            self.add_combat_log(item.combat_id, f"{item.name}: {delta:+d} PG ({item.current_hp}/{item.max_hp})", kind)
        return item

    def delete_combatant(self, item_id: str) -> bool:
        with self.database.connect() as db:
            row = db.execute("SELECT combat_id,name FROM combatants WHERE id=?", (item_id,)).fetchone()
            if row:
                db.execute("DELETE FROM combatants WHERE id=?", (item_id,))
        if row:
            self.add_combat_log(row["combat_id"], f"{row['name']} surt del combat")
        return bool(row)

    def duplicate_combatant(self, item_id: str, quantity: int) -> list[Combatant]:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM combatants WHERE id=?", (item_id,)).fetchone()
        if not row:
            raise ValueError("Combatent no trobat")
        original = self._combatant(row)
        created = []
        for index in range(1, quantity + 1):
            created.append(self.add_combatant(original.combat_id, CombatantCreate(
                name=f"{original.name} {index + 1}", kind=original.kind,
                initiative=original.initiative - index, initiative_bonus=original.initiative_bonus,
                armor_class=original.armor_class, max_hp=original.max_hp, temp_hp=original.temp_hp,
                legendary_actions_max=original.legendary_actions_max, notes=original.notes,
                conditions=list(original.conditions), actions=list(original.actions),
                source_id=original.source_id, reference_id=original.reference_id,
            )))
        return created

    def next_turn(self, combat_id: str) -> Combat | None:
        combat = self.get_combat(combat_id)
        if not combat:
            return None
        count = len(combat.combatants)
        if not count:
            return combat
        next_index = (combat.turn_index + 1) % count
        next_round = combat.round + 1 if next_index == 0 else combat.round
        with self.database.connect() as db:
            db.execute("UPDATE combats SET turn_index=?, round=? WHERE id=?", (next_index, next_round, combat_id))
            if next_index == 0:
                db.execute("UPDATE combatants SET reaction_available=1, legendary_actions=legendary_actions_max WHERE combat_id=?", (combat_id,))
        updated = self.get_combat(combat_id)
        if updated and updated.combatants:
            self.add_combat_log(combat_id, f"Ronda {updated.round}: torn de {updated.combatants[updated.turn_index].name}", "turn")
        return updated

    def roll_initiative(self, combat_id: str, rolls: dict[str, int]) -> Combat | None:
        if not self.get_combat(combat_id):
            return None
        with self.database.connect() as db:
            for item_id, roll in rolls.items():
                db.execute("UPDATE combatants SET initiative=? + initiative_bonus WHERE id=? AND combat_id=?", (roll, item_id, combat_id))
            db.execute("UPDATE combats SET round=1,turn_index=0 WHERE id=?", (combat_id,))
        self.add_combat_log(combat_id, "Iniciatives recalculades", "roll")
        return self.get_combat(combat_id)

    def add_combat_log(self, combat_id: str, message: str, kind: str = "system") -> CombatLog:
        item = CombatLog(id=f"combatlog_{uuid4().hex[:12]}", combat_id=combat_id, message=message, kind=kind)
        with self.database.connect() as db:
            db.execute("INSERT INTO combat_logs VALUES (?, ?, ?, ?, ?)", (item.id, item.combat_id, item.message, item.kind, item.created_at))
        return item

    def list_combat_logs(self, combat_id: str, limit: int = 200) -> list[CombatLog]:
        with self.database.connect() as db:
            return [CombatLog(**dict(row)) for row in db.execute(
                "SELECT * FROM combat_logs WHERE combat_id=? ORDER BY created_at DESC LIMIT ?", (combat_id, limit)
            )]
