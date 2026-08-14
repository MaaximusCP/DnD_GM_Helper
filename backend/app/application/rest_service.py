from uuid import uuid4

from app.domain.models import (
    CampaignUpdate, ExpeditionRestRequest, ExpeditionRestResult,
    ExpeditionStateUpdate, TravelLog,
)
from app.infrastructure.campaign_tools_repository import CampaignToolsRepository
from app.infrastructure.repository import SQLiteRepository


class RestService:
    """Aplica descansos a l'expedició respectant els subsistemes activats."""

    def __init__(self, tools: CampaignToolsRepository, world: SQLiteRepository):
        self.tools = tools
        self.world = world

    def rest(self, campaign_id: str, request: ExpeditionRestRequest) -> ExpeditionRestResult:
        campaign = self.world.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campanya no trobada")
        state = self.tools.get_expedition_state(campaign_id)
        if not state.current_hex_id or not self.tools.get_hex(state.current_hex_id):
            raise ValueError("Cal situar l'expedició en un hex abans de descansar")

        settings = self.tools.get_hexcrawl_settings(campaign_id)
        party = self.world.get_party_settings(campaign_id)
        is_long = request.rest_type == "long"
        day_advanced = 1 if is_long else 0
        notes = ["Descans llarg" if is_long else "Descans curt"]

        required_food = float(party.size) if is_long and request.consume_resources and settings.track_food else 0
        required_water = float(party.size * 2) if is_long and request.consume_resources and settings.track_water else 0
        required_supplies = 1.0 if is_long and request.consume_resources and request.safe_camp else 0
        food_used = min(state.food, required_food)
        water_used = min(state.water, required_water)
        supplies_used = min(state.supplies, required_supplies)
        shortage = food_used < required_food or water_used < required_water

        if not request.consume_resources:
            notes.append("Consum de provisions ignorat pel DM")
        elif is_long:
            notes.append(f"Consum: {food_used:g} menjar, {water_used:g} aigua i {supplies_used:g} subministraments")
        if shortage:
            notes.append("Les provisions no han estat suficients per a tot el grup")
        if not request.safe_camp:
            notes.append("El campament no és segur: no es recupera esgotament")

        exhaustion_delta = 0
        if is_long and settings.track_fatigue:
            if shortage:
                exhaustion_delta = 1
                notes.append("La manca de provisions augmenta l'esgotament")
            elif request.safe_camp and state.exhaustion > 0:
                exhaustion_delta = -1
                notes.append("El descans segur redueix l'esgotament")

        updated = self.tools.update_expedition_state(campaign_id, ExpeditionStateUpdate(
            food=max(0, state.food - food_used), water=max(0, state.water - water_used),
            supplies=max(0, state.supplies - supplies_used),
            exhaustion=max(0, min(6, state.exhaustion + exhaustion_delta)),
            lost=False if request.safe_camp else state.lost,
        ))
        if day_advanced:
            self.world.update_campaign(campaign_id, CampaignUpdate(current_day=campaign.current_day + day_advanced))

        log = self.tools.save_travel_log(TravelLog(
            id=f"rest_{uuid4().hex[:12]}", campaign_id=campaign_id,
            origin_hex_id=state.current_hex_id, destination_hex_id=state.current_hex_id,
            route=[state.current_hex_id], pace=f"rest_{request.rest_type}", days=day_advanced,
            distance=0, distance_unit=settings.distance_unit, weather=state.weather,
            food_used=food_used, water_used=water_used, exhaustion_delta=exhaustion_delta,
            reached_destination=True, notes=notes,
        ))
        return ExpeditionRestResult(
            state=updated, log=log, food_used=food_used, water_used=water_used,
            supplies_used=supplies_used, exhaustion_delta=exhaustion_delta,
            day_advanced=day_advanced, notes=notes,
        )
