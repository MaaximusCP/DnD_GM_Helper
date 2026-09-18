"""Local adventure runner. Every transition and its effects share one transaction."""
import json
import secrets
from uuid import uuid4

from app.domain.models import AdventureCreate, AdventureEnemyGroup, CampaignRecord, CombatantCreate, utc_now
from app.infrastructure.database import Database
from app.infrastructure.homebrew_catalog import HomebrewCatalog
from app.infrastructure.reference_catalog import ReferenceCatalog

# Basic Rules 2014 encounter thresholds; see docs/adventures.md for attribution.
THRESHOLDS = [(25,50,75,100),(50,100,150,200),(75,150,225,400),(125,250,375,500),
    (250,500,750,1100),(300,600,900,1400),(350,750,1100,1700),(450,900,1400,2100),
    (550,1100,1600,2400),(600,1200,1900,2800),(800,1600,2400,3600),(1000,2000,3000,4500),
    (1100,2200,3400,5100),(1250,2500,3800,5700),(1400,2800,4300,6400),(1600,3200,4800,7200),
    (2000,3900,5900,8800),(2100,4200,6300,9500),(2400,4900,7300,10900),(2800,5700,8500,12700)]


class AdventureConflict(ValueError):
    pass


class AdventureService:
    def __init__(self, database: Database, catalog: HomebrewCatalog):
        self.database, self.catalog = database, catalog

    def resources(self):
        return self.catalog.search(limit=10000)["items"] + ReferenceCatalog().search(category="monsters", limit=10000)["items"]

    def resource(self, item_id, category):
        item = self.catalog.get(item_id) or ReferenceCatalog().get(item_id)
        if not item or item["category"] not in ({"enemy", "monsters"} if category == "enemy" else {category}):
            raise ValueError(f"Recurs inexistent o incompatible: {item_id}")
        return item

    def groups(self, groups: list[AdventureEnemyGroup]):
        if sum(group.quantity for group in groups) > 60:
            raise ValueError("Màxim 60 enemics per aventura")
        result = []
        for group in groups:
            resource = self.resource(group.resource_id, "enemy")
            xp = resource["data"].get("xp", 0)
            if type(xp) not in (int, float) or not 0 <= xp <= 1000000:
                raise ValueError(f"PX no vàlids al recurs {resource['name']}")
            self.enemy_payload(resource, resource["name"][:160])
            result.append({**group.model_dump(), "resource": resource})
        return result

    @staticmethod
    def enemy_payload(resource, name):
        stats = resource["data"]
        ac = stats.get("armor_class", 10)
        if isinstance(ac, list):
            if ac and not isinstance(ac[0], dict):
                raise ValueError("Format de classe d'armadura no vàlid")
            ac = ac[0].get("value", 10) if ac else 10
        raw_actions = stats.get("actions", [])
        if not isinstance(raw_actions, list) or not all(isinstance(a, dict) for a in raw_actions):
            raise ValueError("Les accions de l'enemic han de ser una llista d'objectes")
        actions = [{"name": str(a.get("name", "Acció")), "description": str(a.get("description", a.get("desc", "")))} for a in raw_actions[:30]]
        traits = stats.get("traits", [])
        if not isinstance(traits, list):
            raise ValueError("Els trets han de ser una llista")
        notes = "\n".join([str(stats.get("tactics", "")), *map(str, traits)])[:3000]
        dexterity = stats.get("dexterity", 10)
        if not isinstance(dexterity, int):
            raise ValueError("Destresa de l'enemic no vàlida")
        return CombatantCreate(name=name, armor_class=ac, max_hp=stats.get("hit_points", 1),
            initiative_bonus=stats.get("initiative_bonus", (dexterity-10)//2), actions=actions, notes=notes,
            reference_id=resource["id"] if resource["category"] == "monsters" else None)

    @staticmethod
    def budget(db, campaign_id, groups):
        if not db.execute("SELECT 1 FROM campaigns WHERE id=?", (campaign_id,)).fetchone():
            raise ValueError("Campanya no trobada")
        levels = [row[0] for row in db.execute("SELECT level FROM characters WHERE campaign_id=? AND active=1", (campaign_id,))]
        source = "characters"
        if not levels:
            party = db.execute("SELECT level,size FROM party_settings WHERE campaign_id=?", (campaign_id,)).fetchone()
            levels = [party[0]] * party[1] if party else [3] * 4
            source = "party_settings"
        thresholds = [sum(THRESHOLDS[max(1, min(20, level))-1][i] for level in levels) for i in range(4)]
        waves = []
        for wave in sorted({g["wave"] for g in groups}):
            members = [g for g in groups if g["wave"] == wave]
            count = sum(g["quantity"] for g in members)
            xp = sum(max(0, int(g["resource"]["data"].get("xp", 0))) * g["quantity"] for g in members)
            index = 1 if count == 1 else 2 if count == 2 else 3 if count <= 6 else 4 if count <= 10 else 5 if count <= 14 else 6
            index += 1 if len(levels) < 3 else -1 if len(levels) >= 6 else 0
            multiplier = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5][index]
            adjusted = int(xp * multiplier)
            difficulty = ["trivial", "easy", "medium", "hard", "deadly"][sum(adjusted >= t for t in thresholds)]
            waves.append({"wave": wave, "count": count, "xp": xp, "adjusted_xp": adjusted,
                          "multiplier": multiplier, "difficulty": difficulty})
        return {"rules": "dnd5e-2014", "levels": levels, "party_source": source, "thresholds": thresholds,
                "waves": waves, "total_xp": sum(w["xp"] for w in waves),
                "warnings": ["Estimació, no garantia: terreny, recursos i habilitats poden canviar el risc.",
                             "Les onades es valoren separadament. Si se solapen, el risc augmenta.",
                             "Els PX ajustats no són PX de recompensa; tots els enemics compten al multiplicador."]}

    def preview(self, payload):
        groups = self.groups(payload.enemy_groups)
        with self.database.connect() as db:
            return self.budget(db, payload.campaign_id, groups)

    @staticmethod
    def read(db, item_id):
        row = db.execute("SELECT * FROM campaign_records WHERE id=? AND kind='adventure'", (item_id,)).fetchone()
        if not row:
            raise LookupError("Aventura no trobada")
        return CampaignRecord(**{**dict(row), "data": json.loads(row["data"])})

    @staticmethod
    def write(db, item):
        item.updated_at = utc_now()
        db.execute("UPDATE campaign_records SET status=?,data=?,updated_at=? WHERE id=?",
                   (item.status, json.dumps(item.data, ensure_ascii=False), item.updated_at, item.id))
        return item

    @staticmethod
    def activity(db, item, message):
        session = db.execute("SELECT id FROM sessions WHERE campaign_id=? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1", (item.campaign_id,)).fetchone()
        db.execute("INSERT INTO campaign_activities VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"activity_{uuid4().hex}", item.campaign_id, session[0] if session else None,
                    "adventure", item.title, message, "dm", item.id, utc_now()))

    def create(self, payload: AdventureCreate):
        groups = self.groups(payload.enemy_groups)
        steps = [{"kind": "briefing", "title": "Punt de partida", "description": payload.description}]
        for category, item_id in [("situation", payload.situation_id), ("temple", payload.temple_id)]:
            if item_id:
                resource = self.resource(item_id, category)
                steps.append({"kind": category, "title": resource["name"], "description": resource["summary"], "resource": resource})
        if groups:
            steps.append({"kind": "combat", "title": "Trobada i reforços", "description": "Negociar, fugir o combatre: el DM decideix quan tancar la trobada."})
        if payload.minigame_id:
            resource = self.resource(payload.minigame_id, "minigame")
            steps.append({"kind": "minigame", "title": resource["name"], "description": resource["summary"], "resource": resource})
        steps.append({"kind": "resolution", "title": "Conseqüències i botí", "description": "Anota pactes, pistes i conseqüències. Reparteix el botí i els PX des de les eines existents, només amb aprovació del DM."})
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            budget = self.budget(db, payload.campaign_id, groups)
            for table, item_id in [("hex_cells", payload.hex_id), ("locations", payload.location_id)]:
                if item_id and not db.execute(f"SELECT 1 FROM {table} WHERE id=? AND campaign_id=?", (item_id, payload.campaign_id)).fetchone():
                    raise ValueError("L'hexàgon o ubicació no pertany a aquesta campanya")
            item = CampaignRecord(id=f"adventure_{uuid4().hex}", campaign_id=payload.campaign_id,
                kind="adventure", title=payload.title, status="draft", visibility="dm",
                data={"schema_version": 1, "revision": 0, "current_step": 0, "steps": steps,
                      "enemy_groups": groups, "budget": budget, "hex_id": payload.hex_id,
                      "location_id": payload.location_id, "alert_delta": payload.alert_delta,
                      "include_characters": payload.include_characters, "released_waves": [], "notes": []})
            db.execute("INSERT INTO campaign_records VALUES (?,?,?,?,?,?,?,?,?,?,?)", (item.id, item.campaign_id,
                item.kind, item.title, item.status, item.visibility, None, None, json.dumps(item.data), item.created_at, item.updated_at))
            self.activity(db, item, "Aventura preparada; cap efecte sobre el món encara.")
            return item

    @staticmethod
    def add_combatant(db, combat_id, payload):
        values = payload.model_dump()
        values["current_hp"] = payload.current_hp if payload.current_hp is not None else payload.max_hp
        values.update(id=f"combatant_{uuid4().hex}", combat_id=combat_id, legendary_actions_max=payload.legendary_actions)
        for key in ("conditions", "actions"):
            values[key] = json.dumps(values[key])
        db.execute(f"INSERT INTO combatants ({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))

    def release(self, db, item):
        state = item.data
        remaining = sorted({g["wave"] for g in state["enemy_groups"]} - set(state["released_waves"]))
        if not remaining:
            raise AdventureConflict("Ja han entrat totes les onades")
        combat_id = state["combat_id"]
        combat = db.execute("SELECT * FROM combats WHERE id=? AND campaign_id=?", (combat_id, item.campaign_id)).fetchone()
        if not combat or combat["status"] != "active":
            raise AdventureConflict("El combat no està actiu")
        # Preserve whose turn it is when the initiative list grows.
        before = db.execute("SELECT id FROM combatants WHERE combat_id=? ORDER BY initiative DESC,name", (combat_id,)).fetchall()
        current = before[min(combat["turn_index"], len(before)-1)][0] if before else None
        wave = remaining[0]
        for index, group in enumerate(state["enemy_groups"]):
            if group["wave"] != wave:
                continue
            resource = group["resource"]
            for number in range(group["quantity"]):
                self.add_combatant(db, combat_id, self.enemy_payload(resource,
                    f"{resource['name'][:130]} · O{wave}.{index+1}/{number+1}"))
        state["released_waves"].append(wave)
        if current:
            after = [r[0] for r in db.execute("SELECT id FROM combatants WHERE combat_id=? ORDER BY initiative DESC,name", (combat_id,))]
            db.execute("UPDATE combats SET turn_index=? WHERE id=?", (after.index(current), combat_id))
        db.execute("INSERT INTO combat_logs VALUES (?,?,?,?,?)", (f"combatlog_{uuid4().hex}", combat_id, f"Entra l'onada {wave}", "system", utc_now()))
        self.activity(db, item, f"Onada {wave} activada")

    def enter_step(self, db, item):
        state = item.data
        step = state["steps"][state["current_step"]]
        if step["kind"] == "combat":
            combat_id = f"combat_{uuid4().hex}"
            state["combat_id"] = combat_id
            db.execute("INSERT INTO combats VALUES (?,?,?,?,?,?,?,?,?)", (combat_id, item.campaign_id,
                item.title[:160], "active", 1, 0, None, "Aventura: " + item.id, utc_now()))
            if state["include_characters"]:
                for pc in db.execute("SELECT * FROM characters WHERE campaign_id=? AND active=1", (item.campaign_id,)).fetchall():
                    self.add_combatant(db, combat_id, CombatantCreate(name=pc["name"], kind="player",
                        armor_class=pc["armor_class"], max_hp=pc["max_hp"], current_hp=pc["current_hp"],
                        temp_hp=pc["temp_hp"], conditions=json.loads(pc["conditions"]), character_id=pc["id"],
                        initiative_bonus=(json.loads(pc["ability_scores"]).get("dex", 10)-10)//2))
            self.release(db, item)
        self.activity(db, item, f"Escena: {step['title']}")

    def activate(self, item_id, force=False):
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            item = self.read(db, item_id)
            if item.status == "active":
                return item
            if item.status != "draft":
                raise AdventureConflict("Aquesta aventura ja ha finalitzat")
            if db.execute("SELECT 1 FROM campaign_records WHERE campaign_id=? AND kind='adventure' AND status='active'", (item.campaign_id,)).fetchone():
                raise AdventureConflict("Finalitza l'aventura activa abans de començar-ne una altra")
            hex_id = item.data.get("hex_id")
            if hex_id:
                if not db.execute("SELECT 1 FROM hex_cells WHERE id=? AND campaign_id=?", (hex_id, item.campaign_id)).fetchone():
                    raise AdventureConflict("L'hexàgon vinculat ja no existeix")
                position = db.execute("SELECT current_hex_id FROM expedition_state WHERE campaign_id=?", (item.campaign_id,)).fetchone()
                if not force and (not position or position[0] != hex_id):
                    raise AdventureConflict("El grup no és a l'hexàgon vinculat. Viatja-hi o confirma l'activació remota.")
                db.execute("UPDATE hex_cells SET alert_level=MIN(5,alert_level+?) WHERE id=? AND campaign_id=?",
                           (item.data["alert_delta"], hex_id, item.campaign_id))
            item.status = "active"
            item.data["revision"] += 1
            self.enter_step(db, item)
            return self.write(db, item)

    def transition(self, item_id, payload, action="advance"):
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            item = self.read(db, item_id)
            state = item.data
            if item.status != "active" or state["revision"] != payload.expected_revision:
                raise AdventureConflict("L'estat ha canviat. Recarrega l'aventura abans de continuar.")
            step = state["steps"][state["current_step"]]
            if action == "wave":
                if step["kind"] != "combat":
                    raise AdventureConflict("Aquesta escena no és un combat")
                self.release(db, item)
            elif action == "note":
                if not payload.note.strip():
                    raise ValueError("Escriu una nota")
            elif action == "check":
                checks = step.get("resource", {}).get("data", {}).get("checks", [])
                if step["kind"] != "minigame" or payload.check_index >= len(checks):
                    raise ValueError("Prova no disponible en aquesta escena")
                check = checks[payload.check_index]
                dc = check.get("dc")
                if not isinstance(dc, int) or not 1 <= dc <= 40:
                    raise ValueError("La prova no té una CD vàlida")
                roll = payload.d20 if payload.d20 is not None else secrets.randbelow(20) + 1
                result = {"name": check.get("name", "Prova"), "d20": roll, "modifier": payload.modifier,
                          "total": roll + payload.modifier, "dc": dc,
                          "success": roll + payload.modifier >= dc, "manual": payload.d20 is not None,
                          "created_at": utc_now()}
                step.setdefault("check_results", []).append(result)
                self.activity(db, item, f"{result['name']}: {result['total']} vs CD {dc} ({'manual' if result['manual'] else 'automàtica'})")
            else:
                if step["kind"] == "combat":
                    combat = db.execute("SELECT status FROM combats WHERE id=? AND campaign_id=?", (state["combat_id"], item.campaign_id)).fetchone()
                    if not payload.force and (not combat or combat[0] != "completed" or len(state["released_waves"]) < len(state["budget"]["waves"])):
                        raise AdventureConflict("Finalitza el combat i les onades, o confirma saltar la trobada")
                    if payload.force:
                        db.execute("UPDATE combats SET status='completed' WHERE id=? AND campaign_id=?", (state["combat_id"], item.campaign_id))
                step["completed_at"] = utc_now()
                if state["current_step"] + 1 == len(state["steps"]):
                    item.status = "completed"
                    self.activity(db, item, "Aventura finalitzada. Botí i PX pendents de decisió del DM.")
                else:
                    state["current_step"] += 1
                    self.enter_step(db, item)
            if payload.note.strip():
                state["notes"].append({"text": payload.note.strip(), "step": step["title"], "created_at": utc_now()})
                self.activity(db, item, payload.note.strip())
            state["revision"] += 1
            return self.write(db, item)
