import re
from uuid import uuid4

from app.domain.models import Consequence, EventAnalyzeRequest, EventProposal
from app.infrastructure.repository import SQLiteRepository


class EventService:
    """Conservative local analyzer: it only proposes changes; the DM applies them."""

    def __init__(self, repository: SQLiteRepository):
        self.repository = repository

    def analyze(self, request: EventAnalyzeRequest) -> EventProposal:
        text = request.description.lower()
        event_type, title, severity = "narrative", "Nou fet de la campanya", 3
        consequences: list[Consequence] = []

        if re.search(r"rob|furt|saque", text):
            event_type, title, severity = "crime", "Robatori", 6
            consequences.append(Consequence(kind="wanted", target_id=request.campaign_id, field="wanted_level", delta=1))
        elif re.search(r"atac|baralla|ferit|agred", text):
            event_type, title, severity = "conflict", "Conflicte violent", 7
            consequences.append(Consequence(kind="wanted", target_id=request.campaign_id, field="wanted_level", delta=1))
        elif re.search(r"ajud|salv|resc", text):
            event_type, title, severity = "aid", "Ajuda significativa", 4
            if request.npc_id:
                consequences.append(Consequence(kind="relationship", target_id=request.npc_id, field="trust", delta=10))
        elif re.search(r"suborn", text):
            event_type, title, severity = "social", "Intent de suborn", 5
            if request.npc_id:
                consequences.append(Consequence(kind="relationship", target_id=request.npc_id, field="trust", delta=-10))

        if request.npc_id:
            consequences.append(
                Consequence(kind="memory", target_id=request.npc_id, field="memory", text=request.description)
            )

        proposal = EventProposal(
            id=f"event_{uuid4().hex[:12]}", campaign_id=request.campaign_id,
            title=title, description=request.description, event_type=event_type,
            severity=severity, consequences=consequences,
            location_id=request.location_id or (self.repository.get_campaign(request.campaign_id).current_location_id if self.repository.get_campaign(request.campaign_id) else None),
            visibility=request.visibility,
        )
        self.repository.save_event(proposal)
        return proposal
