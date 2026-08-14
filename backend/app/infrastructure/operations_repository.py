import json
from uuid import uuid4

from app.domain.models import (
    CampaignActivity, CampaignActivityCreate, CampaignRecord, CampaignRecordCreate,
    CampaignRecordUpdate, utc_now,
)
from app.infrastructure.database import Database


class OperationsRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _record(row) -> CampaignRecord:
        return CampaignRecord(**{**dict(row), "data": json.loads(row["data"] or "{}")})

    def list_records(self, campaign_id: str, kind: str | None = None) -> list[CampaignRecord]:
        with self.database.connect() as db:
            if kind:
                rows = db.execute("SELECT * FROM campaign_records WHERE campaign_id=? AND kind=? ORDER BY due_day IS NULL,due_day,updated_at DESC", (campaign_id, kind)).fetchall()
            else:
                rows = db.execute("SELECT * FROM campaign_records WHERE campaign_id=? ORDER BY kind,due_day IS NULL,due_day,updated_at DESC", (campaign_id,)).fetchall()
        return [self._record(row) for row in rows]

    def get_record(self, item_id: str) -> CampaignRecord | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM campaign_records WHERE id=?", (item_id,)).fetchone()
        return self._record(row) if row else None

    def create_record(self, payload: CampaignRecordCreate) -> CampaignRecord:
        item = CampaignRecord(id=f"{payload.kind}_{uuid4().hex[:12]}", **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO campaign_records VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                item.id, item.campaign_id, item.kind, item.title, item.status, item.visibility,
                item.due_day, item.linked_id, json.dumps(item.data), item.created_at, item.updated_at,
            ))
        self.add_activity(CampaignActivityCreate(campaign_id=item.campaign_id, kind=item.kind,
            title=f"Creat: {item.title}", linked_id=item.id))
        return item

    def update_record(self, item_id: str, payload: CampaignRecordUpdate) -> CampaignRecord | None:
        current = self.get_record(item_id)
        if not current:
            return None
        values = payload.model_dump(exclude_none=True)
        if "data" in values:
            values["data"] = json.dumps(values["data"])
        values["updated_at"] = utc_now()
        with self.database.connect() as db:
            db.execute(f"UPDATE campaign_records SET {','.join(f'{key}=?' for key in values)} WHERE id=?", (*values.values(), item_id))
        updated = self.get_record(item_id)
        if payload.status and payload.status != current.status:
            self.add_activity(CampaignActivityCreate(campaign_id=current.campaign_id, kind=current.kind,
                title=f"{current.title}: {payload.status}", linked_id=item_id,
                visibility="players" if current.visibility == "players" else "dm"))
        return updated

    def delete_record(self, item_id: str) -> bool:
        with self.database.connect() as db:
            row = db.execute("SELECT campaign_id,title FROM campaign_records WHERE id=?", (item_id,)).fetchone()
            if row:
                db.execute("DELETE FROM campaign_records WHERE id=? OR linked_id=?", (item_id, item_id))
        if row:
            self.add_activity(CampaignActivityCreate(campaign_id=row["campaign_id"], kind="delete", title=f"Eliminat: {row['title']}"))
        return bool(row)

    def add_activity(self, payload: CampaignActivityCreate) -> CampaignActivity:
        item = CampaignActivity(id=f"activity_{uuid4().hex[:12]}", **payload.model_dump())
        with self.database.connect() as db:
            db.execute("INSERT INTO campaign_activities VALUES (?,?,?,?,?,?,?,?,?)", (
                item.id, item.campaign_id, item.session_id, item.kind, item.title, item.details,
                item.visibility, item.linked_id, item.created_at,
            ))
        return item

    def list_activities(self, campaign_id: str, limit: int = 500) -> list[CampaignActivity]:
        with self.database.connect() as db:
            rows = db.execute("SELECT * FROM campaign_activities WHERE campaign_id=? ORDER BY created_at DESC LIMIT ?", (campaign_id, limit)).fetchall()
        return [CampaignActivity(**dict(row)) for row in rows]

    def active_session_id(self, campaign_id: str) -> str | None:
        with self.database.connect() as db:
            row = db.execute("SELECT id FROM sessions WHERE campaign_id=? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1", (campaign_id,)).fetchone()
        return row["id"] if row else None

    def advance_clock(self, clock_id: str, steps: int) -> CampaignRecord | None:
        clock = self.get_record(clock_id)
        if not clock or clock.kind != "clock":
            return None
        data = dict(clock.data); maximum = max(1, int(data.get("maximum", 4)))
        data["current"] = min(maximum, max(0, int(data.get("current", 0)) + steps))
        status = "completed" if data["current"] >= maximum else clock.status
        return self.update_record(clock_id, CampaignRecordUpdate(data=data, status=status))
