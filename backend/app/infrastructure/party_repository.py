import json
from uuid import uuid4

from app.domain.models import (
    Character, CharacterCreate, CharacterUpdate, InventoryConsume, InventoryItem,
    InventoryItemCreate, InventoryItemUpdate, InventoryTransaction, Treasury,
    TreasuryAdjustment, TreasuryUpdate, utc_now,
)
from app.infrastructure.database import Database


JSON_CHARACTER_FIELDS = {"ability_scores", "saving_throws", "skills", "conditions", "spell_slots", "spell_slots_max", "resources"}


class PartyRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _character(row) -> Character:
        data = dict(row)
        for key in JSON_CHARACTER_FIELDS:
            data[key] = json.loads(data[key])
        return Character(**data)

    def list_characters(self, campaign_id: str, active_only: bool = False) -> list[Character]:
        sql = "SELECT * FROM characters WHERE campaign_id=?"
        if active_only:
            sql += " AND active=1"
        with self.database.connect() as db:
            rows = db.execute(sql + " ORDER BY active DESC,name", (campaign_id,)).fetchall()
        return [self._character(row) for row in rows]

    def get_character(self, item_id: str) -> Character | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM characters WHERE id=?", (item_id,)).fetchone()
        return self._character(row) if row else None

    def create_character(self, payload: CharacterCreate) -> Character:
        data = payload.model_dump()
        data["current_hp"] = payload.max_hp if payload.current_hp is None else min(payload.current_hp, payload.max_hp)
        item = Character(id=f"char_{uuid4().hex[:12]}", **data)
        values = item.model_dump()
        for key in JSON_CHARACTER_FIELDS:
            values[key] = json.dumps(values[key])
        columns = ",".join(values)
        with self.database.connect() as db:
            db.execute(f"INSERT INTO characters({columns}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))
            self._log(db, item.campaign_id, "character", f"Personatge creat: {item.name}", character_id=item.id)
        return item

    def update_character(self, item_id: str, payload: CharacterUpdate) -> Character | None:
        values = payload.model_dump(exclude_none=True)
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM characters WHERE id=?", (item_id,)).fetchone()
            if not row:
                return None
            if "current_hp" in values:
                values["current_hp"] = min(values["current_hp"], values.get("max_hp", row["max_hp"]))
            for key in JSON_CHARACTER_FIELDS & values.keys():
                values[key] = json.dumps(values[key])
            if values:
                db.execute(f"UPDATE characters SET {','.join(f'{key}=?' for key in values)} WHERE id=?", (*values.values(), item_id))
                combat_fields = {"name", "armor_class", "max_hp", "current_hp", "temp_hp", "conditions"}
                sync = {key: value for key, value in values.items() if key in combat_fields}
                if sync:
                    db.execute(f"UPDATE combatants SET {','.join(f'{key}=?' for key in sync)} WHERE character_id=?", (*sync.values(), item_id))
            updated = db.execute("SELECT * FROM characters WHERE id=?", (item_id,)).fetchone()
        return self._character(updated)

    def delete_character(self, item_id: str) -> bool:
        with self.database.connect() as db:
            row = db.execute("SELECT campaign_id,name FROM characters WHERE id=?", (item_id,)).fetchone()
            if not row:
                return False
            db.execute("UPDATE inventory_items SET owner_type='party',owner_id=NULL,equipped=0 WHERE owner_type='character' AND owner_id=?", (item_id,))
            db.execute("UPDATE combatants SET character_id=NULL WHERE character_id=?", (item_id,))
            db.execute("DELETE FROM characters WHERE id=?", (item_id,))
            self._log(db, row["campaign_id"], "character", f"Personatge eliminat: {row['name']}")
        return True

    def apply_rest(self, campaign_id: str, rest_type: str, recover: bool) -> list[str]:
        if not recover:
            return []
        recovered = []
        for character in self.list_characters(campaign_id, active_only=True):
            resources = [resource.model_dump() for resource in character.resources]
            for resource in resources:
                if rest_type == "long" or resource["reset"] == "short":
                    resource["current"] = resource["maximum"]
            update = {"resources": resources}
            if rest_type == "long":
                update.update(current_hp=character.max_hp, temp_hp=0, spell_slots=dict(character.spell_slots_max), exhaustion=max(0, character.exhaustion - 1))
            self.update_character(character.id, CharacterUpdate(**update))
            recovered.append(character.name)
        return recovered

    @staticmethod
    def _inventory(row) -> InventoryItem:
        return InventoryItem(**dict(row))

    def list_inventory(self, campaign_id: str, owner_type: str | None = None, owner_id: str | None = None) -> list[InventoryItem]:
        sql, params = "SELECT * FROM inventory_items WHERE campaign_id=?", [campaign_id]
        if owner_type:
            sql += " AND owner_type=?"; params.append(owner_type)
        if owner_id:
            sql += " AND owner_id=?"; params.append(owner_id)
        with self.database.connect() as db:
            rows = db.execute(sql + " ORDER BY category,name", params).fetchall()
        return [self._inventory(row) for row in rows]

    def get_inventory_item(self, item_id: str) -> InventoryItem | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM inventory_items WHERE id=?", (item_id,)).fetchone()
        return self._inventory(row) if row else None

    def create_inventory_item(self, payload: InventoryItemCreate) -> InventoryItem:
        self._validate_owner(payload.campaign_id, payload.owner_type, payload.owner_id)
        item = InventoryItem(id=f"item_{uuid4().hex[:12]}", **payload.model_dump())
        values = item.model_dump()
        with self.database.connect() as db:
            db.execute(f"INSERT INTO inventory_items({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))
            self._log(db, item.campaign_id, "item_add", f"Afegit: {item.name}", item.id, item.owner_id, quantity_delta=item.quantity)
        return item

    def update_inventory_item(self, item_id: str, payload: InventoryItemUpdate) -> InventoryItem | None:
        current = self.get_inventory_item(item_id)
        if not current:
            return None
        values = payload.model_dump(exclude_none=True)
        owner_type = values.get("owner_type", current.owner_type)
        owner_id = values.get("owner_id", current.owner_id)
        self._validate_owner(current.campaign_id, owner_type, owner_id)
        with self.database.connect() as db:
            if values:
                db.execute(f"UPDATE inventory_items SET {','.join(f'{key}=?' for key in values)} WHERE id=?", (*values.values(), item_id))
                if "owner_type" in values or "owner_id" in values:
                    self._log(db, current.campaign_id, "transfer", f"Transferit: {current.name}", item_id, owner_id)
            row = db.execute("SELECT * FROM inventory_items WHERE id=?", (item_id,)).fetchone()
        return self._inventory(row)

    def consume_inventory_item(self, item_id: str, payload: InventoryConsume) -> InventoryItem | None:
        item = self.get_inventory_item(item_id)
        if not item:
            return None
        if payload.quantity > item.quantity:
            raise ValueError("No hi ha prou quantitat disponible")
        remaining = item.quantity - payload.quantity
        with self.database.connect() as db:
            if remaining <= 0:
                db.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))
            else:
                db.execute("UPDATE inventory_items SET quantity=? WHERE id=?", (remaining, item_id))
            self._log(db, item.campaign_id, "consume", f"{payload.description}: {item.name}", item_id, item.owner_id, quantity_delta=-payload.quantity)
        return self.get_inventory_item(item_id)

    def delete_inventory_item(self, item_id: str) -> bool:
        item = self.get_inventory_item(item_id)
        if not item:
            return False
        with self.database.connect() as db:
            db.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))
            self._log(db, item.campaign_id, "item_remove", f"Eliminat: {item.name}", item.id, item.owner_id, quantity_delta=-item.quantity)
        return True

    def get_treasury(self, campaign_id: str) -> Treasury:
        with self.database.connect() as db:
            db.execute("INSERT OR IGNORE INTO treasury(campaign_id,updated_at) VALUES (?,?)", (campaign_id, utc_now()))
            row = db.execute("SELECT * FROM treasury WHERE campaign_id=?", (campaign_id,)).fetchone()
        return Treasury(**dict(row))

    def update_treasury(self, campaign_id: str, payload: TreasuryUpdate) -> Treasury:
        self.get_treasury(campaign_id)
        values = payload.model_dump(exclude_none=True); values["updated_at"] = utc_now()
        with self.database.connect() as db:
            db.execute(f"UPDATE treasury SET {','.join(f'{key}=?' for key in values)} WHERE campaign_id=?", (*values.values(), campaign_id))
            self._log(db, campaign_id, "treasury", "Tresoreria actualitzada")
        return self.get_treasury(campaign_id)

    def adjust_treasury(self, campaign_id: str, payload: TreasuryAdjustment) -> Treasury:
        treasury = self.get_treasury(campaign_id)
        current = getattr(treasury, payload.currency)
        if current + payload.amount < 0:
            raise ValueError("La tresoreria no pot quedar en negatiu")
        with self.database.connect() as db:
            db.execute(f"UPDATE treasury SET {payload.currency}=?,updated_at=? WHERE campaign_id=?", (current + payload.amount, utc_now(), campaign_id))
            self._log(db, campaign_id, "currency", payload.description, currency=payload.currency, currency_delta=payload.amount)
        return self.get_treasury(campaign_id)

    def list_transactions(self, campaign_id: str, limit: int = 200) -> list[InventoryTransaction]:
        with self.database.connect() as db:
            rows = db.execute("SELECT * FROM inventory_transactions WHERE campaign_id=? ORDER BY created_at DESC LIMIT ?", (campaign_id, limit)).fetchall()
        return [InventoryTransaction(**dict(row)) for row in rows]

    def _validate_owner(self, campaign_id: str, owner_type: str, owner_id: str | None) -> None:
        if owner_type == "party":
            return
        if not owner_id:
            raise ValueError("Aquest propietari requereix un identificador")
        table = "characters" if owner_type == "character" else "locations"
        with self.database.connect() as db:
            if not db.execute(f"SELECT 1 FROM {table} WHERE id=? AND campaign_id=?", (owner_id, campaign_id)).fetchone():
                raise ValueError("El propietari no pertany a la campanya")

    @staticmethod
    def _log(db, campaign_id: str, kind: str, description: str, item_id: str | None = None,
             character_id: str | None = None, currency: str | None = None,
             currency_delta: float = 0, quantity_delta: float = 0) -> None:
        db.execute("INSERT INTO inventory_transactions VALUES (?,?,?,?,?,?,?,?,?,?)", (
            f"tx_{uuid4().hex[:12]}", campaign_id, kind, description, item_id, character_id,
            currency, currency_delta, quantity_delta, utc_now(),
        ))
