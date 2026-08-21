import hashlib
from uuid import uuid4

from app.domain.models import CampaignUpdate, Consequence, EventProposal, NPCActionRequest, NPCActionResult
from app.infrastructure.repository import SQLiteRepository


class NPCActionService:
    """Rules-first downtime engine. It creates reviewable proposals and never applies them."""

    ACTIONS = (
        "mou contactes i recursos per avançar",
        "investiga discretament pistes relacionades amb",
        "pressiona els seus aliats per protegir",
        "prepara el següent pas per aconseguir",
        "busca una oportunitat vinculada a",
    )

    def __init__(self, repository: SQLiteRepository):
        self.repository = repository

    def generate(self, campaign_id: str, request: NPCActionRequest) -> NPCActionResult:
        campaign = self.repository.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campanya no trobada")
        selected = set(request.npc_ids)
        npcs = [npc for npc in self.repository.list_npcs(campaign_id) if not selected or npc.id in selected]
        proposals: list[EventProposal] = []
        skipped: list[str] = []
        locations = {item.id: item for item in self.repository.list_locations(campaign_id)}
        factions = {item.id: item for item in self.repository.list_factions(campaign_id)}

        for npc in npcs:
            if not npc.active or npc.autonomy <= 0:
                skipped.append(f"{npc.name}: NPC passiu")
                continue
            if not npc.goals:
                skipped.append(f"{npc.name}: sense objectius")
                continue
            goal_index = (campaign.current_day + request.days + npc.autonomy) % len(npc.goals)
            goal = npc.goals[goal_index]
            digest = hashlib.sha256(f"{npc.id}:{campaign.current_day}:{request.days}:{goal}".encode()).digest()
            action = self.ACTIONS[digest[0] % len(self.ACTIONS)]
            location = locations.get(npc.location_id)
            faction = factions.get(npc.faction_id or "")
            scope = f" a {location.name}" if location else ""
            affiliation = f"Amb el suport de {faction.name}, " if faction else ""
            description = (
                f"Durant els pròxims {request.days} dies, {npc.name} {action} «{goal}»{scope}."
                f" {affiliation}L'acció pot alterar el context de la campanya si el DM l'aprova."
            )
            proposal = EventProposal(
                id=f"event_{uuid4().hex[:12]}", campaign_id=campaign_id,
                title=f"Agenda de {npc.name}: {goal[:90]}", description=description,
                event_type="npc_action", severity=min(8, 2 + npc.autonomy + request.days // 7),
                consequences=[Consequence(
                    kind="memory", target_id=npc.id, field="memory",
                    text=f"Va dedicar {request.days} dies a avançar l'objectiu: {goal}.",
                )],
                location_id=npc.location_id, visibility="private",
            )
            self.repository.save_event(proposal)
            proposals.append(proposal)

        previous_day = campaign.current_day
        current_day = previous_day
        if request.advance_calendar:
            current_day = previous_day + request.days
            self.repository.update_campaign(campaign_id, CampaignUpdate(current_day=current_day))
        return NPCActionResult(previous_day=previous_day, current_day=current_day,
                               proposals=proposals, skipped=skipped)
