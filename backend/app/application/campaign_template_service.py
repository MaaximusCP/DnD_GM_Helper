from app.domain.models import (
    Campaign, CampaignCreate, CampaignRecordCreate, CampaignTemplateCreate, FactionCreate,
    HexCellCreate, LocationCreate, LocationUpdate, LoreEntryCreate, NPCCreate, Relationship,
)
from app.infrastructure.campaign_tools_repository import CampaignToolsRepository
from app.infrastructure.operations_repository import OperationsRepository
from app.infrastructure.repository import SQLiteRepository


TEMPLATES = {
    "blank": {"name": "Campanya en blanc", "description": "Només crea el punt de partida i el nucli persistent.", "terrain": "urban"},
    "jungle_expedition": {"name": "Expedició selvàtica", "description": "Exploració, supervivència, ruïnes i una facció rival.", "terrain": "jungle"},
    "urban_intrigue": {"name": "Intriga urbana", "description": "Contactes, reputació, rumors i clocks polítics.", "terrain": "urban"},
    "dungeon_delve": {"name": "Expedició a la dungeon", "description": "Sales, riscos, botí contextual i retirada segura.", "terrain": "dungeon"},
}


class CampaignTemplateService:
    def __init__(self, world: SQLiteRepository, tools: CampaignToolsRepository, operations: OperationsRepository):
        self.world, self.tools, self.operations = world, tools, operations

    @staticmethod
    def list_templates() -> list[dict[str, str]]:
        return [{"id": key, **value} for key, value in TEMPLATES.items()]

    def create(self, request: CampaignTemplateCreate) -> Campaign:
        spec = TEMPLATES[request.template_id]
        campaign = self.world.create_campaign(CampaignCreate(
            name=request.name, location_name="Punt de partida",
        ))
        start = self.world.get_location(campaign.current_location_id)
        if start:
            self.world.update_location(start.id, LocationUpdate(
                name={"jungle_expedition":"Camp base", "urban_intrigue":"Barri central", "dungeon_delve":"Vestíbul segur"}.get(request.template_id, "Punt de partida"),
                description=spec["description"], terrain=spec["terrain"],
            ))
        if request.template_id == "blank":
            return campaign

        variants = {
            "jungle_expedition": {
                "places":[("Riu de les boires","Un pas navegable però exposat.","river"),("Ruïnes cobertes","Pedra antiga sota la vegetació.","ruins")],
                "faction":("Companyia rival","Una expedició competidora amb més recursos que escrúpols."),
                "npcs":[("Iria la guia",["prudent","observadora"],["trobar una ruta segura"]),("Varek",["ambiciós","persuasiu"],["arribar primer a les ruïnes"])],
                "quest":"Cartografiar una ruta segura", "clock":"La selva tanca els camins", "risk":["fauna","malaltia","patrulles"],
            },
            "urban_intrigue": {
                "places":[("Mercat vell","Informació, favors i mirades indiscretes.","urban"),("Molls nocturns","Contraban i reunions fora de registre.","coast")],
                "faction":("Consell de mercaders","Cases comercials que competeixen pel control polític."),
                "npcs":[("Mara Vell",["diplomàtica","calculadora"],["controlar una votació decisiva"]),("Toren",["discret","lleial"],["descobrir qui compra els guàrdies"])],
                "quest":"Identificar la xarxa de suborns", "clock":"El rival consolida el consell", "risk":["espies","guàrdies","rumors"],
            },
            "dungeon_delve": {
                "places":[("Galeria inundada","Un tram lent amb mecanismes ocults.","dungeon"),("Santuari interior","El centre ritual del complex.","ruins")],
                "faction":("Custodis del llindar","Una confraria que protegeix els secrets del complex."),
                "npcs":[("Elda la cartògrafa",["metòdica","valenta"],["completar el mapa del nivell"]),("Custodi Orun",["sever","pacient"],["impedir que obrin el santuari"])],
                "quest":"Trobar el santuari interior", "clock":"Les defenses antigues desperten", "risk":["trampes","foscor","soroll"],
            },
        }[request.template_id]

        locations = [self.world.create_location(campaign.id, LocationCreate(name=name, description=description, terrain=terrain))
                     for name, description, terrain in variants["places"]]
        faction = self.world.create_faction(campaign.id, FactionCreate(name=variants["faction"][0], description=variants["faction"][1]))
        for index, (name, traits, goals) in enumerate(variants["npcs"]):
            self.world.create_npc(campaign.id, NPCCreate(
                name=name, location_id=(locations[index % len(locations)]).id, faction_id=faction.id,
                traits=traits, goals=goals, values=["protegir els seus interessos"], active=True,
                autonomy=1 + index, relationship=Relationship(trust=5 if index == 0 else -5),
            ))
        self.tools.create_lore(LoreEntryCreate(campaign_id=campaign.id, layer="players", category="lore",
            title="Punt de partida", content=spec["description"], location_id=campaign.current_location_id))
        self.tools.create_lore(LoreEntryCreate(campaign_id=campaign.id, layer="dm", category="lore",
            title="Tensió inicial", content=f"{variants['faction'][0]} actuarà quan el clock avanci.", location_id=locations[-1].id))
        self.operations.create_record(CampaignRecordCreate(campaign_id=campaign.id, kind="quest", title=variants["quest"],
            visibility="players", data={"description":spec["description"], "objectives":["Investigar el primer indici","Decidir la ruta"]}))
        self.operations.create_record(CampaignRecordCreate(campaign_id=campaign.id, kind="clock", title=variants["clock"],
            visibility="dm", data={"current":0,"maximum":4,"consequence":"El context canvia i apareix una nova complicació."}))
        for index, (q, r) in enumerate(((0,0),(1,0),(0,1),(1,1),(-1,1))):
            self.tools.create_hex(HexCellCreate(
                campaign_id=campaign.id, q=q, r=r, terrain=spec["terrain"] if index < 2 else variants["places"][index % 2][2],
                title="Punt conegut" if index == 0 else f"Sector {index}", discovery="explored" if index == 0 else "discovered" if index == 1 else "hidden",
                location_id=campaign.current_location_id if index == 0 else None, risk_level=min(5, 1 + index),
                encounter_chance=15 + index * 5, risk_tags=[variants["risk"][index % len(variants["risk"])]],
                player_notes="Zona inicial assegurada." if index == 0 else "",
            ))
        self.tools.get_expedition_state(campaign.id)
        return self.world.get_campaign(campaign.id) or campaign
