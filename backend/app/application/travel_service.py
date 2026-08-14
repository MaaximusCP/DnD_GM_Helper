import math
import secrets
from collections import deque
from uuid import uuid4

from app.application.generation_service import GenerationService
from app.domain.models import (
    CampaignUpdate, EncounterRequest, ExpeditionStateUpdate, HexCellUpdate, TravelLog, TravelRequest,
)
from app.infrastructure.campaign_tools_repository import CampaignToolsRepository
from app.infrastructure.repository import SQLiteRepository
from app.infrastructure.simulation_repository import SimulationRepository


WEATHER_BY_TERRAIN = {
    "jungle": ["clear", "humid", "heavy_rain", "storm", "mist"],
    "swamp": ["humid", "heavy_rain", "mist", "storm"],
    "mountain": ["clear", "wind", "heavy_rain", "storm"],
    "desert": ["clear", "heat", "heat", "wind"],
    "coast": ["clear", "wind", "heavy_rain", "storm"],
}
NEIGHBORS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


class TravelService:
    def __init__(self, tools: CampaignToolsRepository, world: SQLiteRepository, simulation: SimulationRepository):
        self.tools = tools
        self.world = world
        self.simulation = simulation

    @staticmethod
    def _roll(sides: int) -> int:
        return secrets.randbelow(sides) + 1

    def _route(self, campaign_id: str, origin_id: str | None, destination_id: str) -> list[str]:
        cells = self.tools.list_hexes(campaign_id)
        by_id = {cell.id: cell for cell in cells}
        if destination_id not in by_id:
            raise ValueError("L'hex de destí no pertany a la campanya")
        if not origin_id or origin_id not in by_id:
            return [destination_id]
        if origin_id == destination_id:
            return [origin_id]
        by_coord = {(cell.q, cell.r): cell for cell in cells}
        queue = deque([origin_id])
        previous: dict[str, str | None] = {origin_id: None}
        while queue:
            current_id = queue.popleft()
            current = by_id[current_id]
            for dq, dr in NEIGHBORS:
                neighbor = by_coord.get((current.q + dq, current.r + dr))
                if not neighbor or neighbor.id in previous:
                    continue
                previous[neighbor.id] = current_id
                if neighbor.id == destination_id:
                    queue.clear()
                    break
                queue.append(neighbor.id)
        if destination_id not in previous:
            raise ValueError("No hi ha una ruta contínua d'hexàgons fins al destí")
        route = []
        cursor: str | None = destination_id
        while cursor:
            route.append(cursor)
            cursor = previous[cursor]
        return list(reversed(route))

    def travel(self, campaign_id: str, request: TravelRequest) -> TravelLog:
        settings = self.tools.get_hexcrawl_settings(campaign_id)
        state = self.tools.get_expedition_state(campaign_id)
        party = self.world.get_party_settings(campaign_id)
        campaign = self.world.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campanya no trobada")
        route = self._route(campaign_id, state.current_hex_id, request.destination_hex_id)
        destination = self.tools.get_hex(request.destination_hex_id)
        if not destination:
            raise ValueError("Hex de destí no trobat")
        travel_cells = route[1:] if len(route) > 1 else route
        all_cells = {cell.id: cell for cell in self.tools.list_hexes(campaign_id)}
        pace = request.pace or settings.default_pace
        pace_factor = {"slow": 0.75, "normal": 1.0, "fast": 1.35}[pace]
        cost = sum(all_cells[item].travel_cost for item in travel_cells)
        days = max(1, math.ceil(cost / (2 * pace_factor)))
        distance = max(1, len(travel_cells)) * settings.hex_distance
        weather_options = WEATHER_BY_TERRAIN.get(destination.terrain, ["clear", "rain", "wind", "mist"])
        weather = request.manual_weather or (weather_options[secrets.randbelow(len(weather_options))] if settings.track_weather else "ignored")

        notes = [f"Ruta de {len(travel_cells)} hexàgons a ritme {pace}", f"Durada estimada: {days} dia/dies"]
        risk_level = destination.risk_level if settings.track_risk else 0
        alert_level = destination.alert_level if settings.track_alert else 0
        if settings.track_risk:
            notes.append(f"Risc {risk_level}/5" + (f" ({', '.join(destination.risk_tags)})" if destination.risk_tags else ""))
        if settings.track_alert:
            notes.append(f"Alerta inicial {alert_level}/5")
        navigation_roll = None
        reached = True
        if settings.track_navigation:
            navigation_roll = request.navigation_roll or self._roll(20)
            dc = 9 + destination.travel_cost + risk_level + (2 if weather in {"heavy_rain", "storm", "mist"} else 0) + (2 if pace == "fast" else 0) - (2 if pace == "slow" else 0)
            reached = navigation_roll >= dc
            notes.append(f"Navegació {navigation_roll} contra DC {dc}: {'èxit' if reached else 'el grup s’ha perdut'}")

        food_used = float(party.size * days) if settings.track_food else 0
        water_multiplier = 2 if weather in {"heat", "humid"} else 1
        water_used = float(party.size * days * water_multiplier) if settings.track_water else 0
        if settings.track_foraging:
            foraging_roll = request.foraging_roll or self._roll(20)
            forage_dc = 10 + destination.travel_cost
            if foraging_roll >= forage_dc:
                food_used = max(0, food_used - party.size * days * 0.5)
                water_used = max(0, water_used - party.size * days * 0.5)
                notes.append(f"Foratge {foraging_roll}: recursos recuperats")
            else:
                notes.append(f"Foratge {foraging_roll}: sense recursos útils")

        exhaustion_delta = 0
        if settings.track_fatigue:
            if pace == "fast" and days > 1:
                exhaustion_delta += 1
                notes.append("El ritme ràpid afegeix fatiga")
            if (settings.track_food and state.food < food_used) or (settings.track_water and state.water < water_used):
                exhaustion_delta += 1
                notes.append("La manca de provisions afegeix fatiga")
            if weather == "storm":
                exhaustion_delta += 1
                notes.append("La tempesta força una marxa esgotadora")

        encounter_roll = None
        encounter_triggered = False
        encounter_id = None
        if settings.track_encounters:
            encounter_roll = request.encounter_roll or self._roll(100)
            chance = max((all_cells[item].encounter_chance for item in travel_cells), default=destination.encounter_chance)
            chance += 10 if pace == "fast" else -5 if pace == "slow" else 0
            chance += risk_level * 6 + alert_level * 5
            encounter_triggered = encounter_roll <= max(0, min(100, chance))
            notes.append(f"Encounter {encounter_roll} contra {chance}%: {'activat' if encounter_triggered else 'cap'}")
            if encounter_triggered:
                encounter = GenerationService(self.simulation, self.world).generate_encounter(EncounterRequest(
                    campaign_id=campaign_id, location_id=destination.location_id, terrain=destination.terrain,
                    party_level=party.level, party_size=party.size,
                    difficulty=max(1, min(5, destination.travel_cost + risk_level // 2 + alert_level // 2)), encounter_type="auto",
                ))
                encounter_id = encounter.id

        new_food = max(0, state.food - food_used) if settings.track_food else state.food
        new_water = max(0, state.water - water_used) if settings.track_water else state.water
        new_exhaustion = min(6, state.exhaustion + exhaustion_delta) if settings.track_fatigue else state.exhaustion
        self.tools.update_expedition_state(campaign_id, ExpeditionStateUpdate(
            current_hex_id=destination.id if reached else state.current_hex_id,
            food=new_food, water=new_water, exhaustion=new_exhaustion,
            lost=not reached if settings.track_navigation else False, weather=weather,
        ))
        if settings.track_alert:
            alert_delta = (1 if pace == "fast" else 0) + (1 if not reached else 0) + (1 if encounter_triggered else 0)
            if settings.alert_decay and pace == "slow" and reached and not encounter_triggered:
                alert_delta -= 1
            new_alert = max(0, min(5, alert_level + alert_delta))
            self.tools.update_hex(destination.id, HexCellUpdate(alert_level=new_alert))
            notes.append(f"Alerta {'+' if alert_delta > 0 else ''}{alert_delta}: nivell final {new_alert}/5")
        if reached and settings.auto_discover:
            for item_id in route:
                cell = all_cells[item_id]
                if cell.discovery != "explored":
                    self.tools.update_hex(item_id, HexCellUpdate(discovery="explored" if item_id == destination.id else "discovered"))
        self.world.update_campaign(campaign_id, CampaignUpdate(current_day=campaign.current_day + days))
        log = TravelLog(
            id=f"travel_{uuid4().hex[:12]}", campaign_id=campaign_id,
            origin_hex_id=state.current_hex_id, destination_hex_id=destination.id, route=route,
            pace=pace, days=days, distance=distance, distance_unit=settings.distance_unit, weather=weather,
            navigation_roll=navigation_roll, encounter_roll=encounter_roll,
            food_used=food_used, water_used=water_used, exhaustion_delta=exhaustion_delta,
            encounter_triggered=encounter_triggered, encounter_id=encounter_id,
            reached_destination=reached, notes=notes,
        )
        return self.tools.save_travel_log(log)
