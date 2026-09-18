"""Real-browser smoke test and optional README captures, using disposable data only.

Install playwright in the backend venv. Uses installed Edge; no browser download.
Run: backend/.venv/Scripts/python.exe scripts/check_adventure_ui.py --screenshots
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", action="store_true", help="Refresh docs/assets/adventure-*.png")
    parser.add_argument("--browser", default=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    args = parser.parse_args()
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise SystemExit("Build frontend/dist first")
    with tempfile.TemporaryDirectory(prefix="gm-ai-ui-") as temp:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = {**os.environ, "GM_AI_DATABASE_PATH": str(Path(temp) / "test.db"),
               "GM_AI_LIBRARY_PATH": str(Path(temp) / "library"),
               "GM_AI_HOMEBREW_PATH": str(Path(temp) / "packs"), "GM_AI_LLM_PROVIDER": "mock"}
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                                  cwd=ROOT / "backend", env=env, stdout=subprocess.DEVNULL,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

        def request(path, payload=None, method=None):
            raw = json.dumps(payload).encode() if payload is not None else None
            with urlopen(Request(base + "/api" + path, data=raw, method=method, headers={"Content-Type":"application/json"}), timeout=30) as response:
                return json.load(response)

        try:
            for _ in range(60):
                try:
                    request("/health")
                    break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError("Temporary server exited during startup")
                    time.sleep(0.25)
            else:
                raise RuntimeError("Temporary server did not become ready")
            for character in request("/campaigns/demo")["characters"]:
                request(f"/characters/{character['id']}", {"active":False}, method="PATCH")
            for name, role in [("Arlet", "Exploradora"),("Biel", "Guerrer"),("Nura", "Druida"),("Tarek", "Mag")]:
                request("/characters", {"campaign_id":"demo","name":name,"class_name":role,"level":3,"max_hp":24,"armor_class":14})
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=args.browser, headless=True)
                context = browser.new_context(viewport={"width":1440,"height":1150}, locale="ca-ES", reduced_motion="reduce")
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: errors.append(f"HTTP {response.status}: {response.url}") if response.status >= 500 else None)
                page.goto(base + "/?view=adventures")
                expect(page.get_by_role("heading", name="De la idea a la partida")).to_be_visible()
                page.get_by_role("button", name="El deute de la pluja", exact=False).click()
                page.get_by_label("Cerca d'enemics").fill("Goblin")
                goblin = next(item for item in request("/adventures/resources") if item["category"] == "monsters" and item["name"] == "Goblin")
                page.get_by_label("Enemic", exact=True).select_option(goblin["id"])
                page.get_by_role("button", name="Afegir", exact=True).click()
                expect(page.locator(".adv-enemy")).to_have_count(3)
                expect(page.locator(".adv-wave")).to_have_count(2)
                page.get_by_label("Cerca d'enemics").fill("")
                page.locator("summary").filter(has_text="Vincle amb el món").click()
                page.get_by_label("Hexàgon", exact=True).select_option("hex_demo_1_0")
                page.get_by_label("Alerta en activar").fill("1")
                page.locator("summary").filter(has_text="Vincle amb el món").click()

                def shot(name):
                    if args.screenshots:
                        page.evaluate("window.scrollTo(0,0)")
                        page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                        page.screenshot(path=str(ROOT / "docs/assets" / name), full_page=True)

                shot("adventure-builder.png")
                page.get_by_role("button", name="Desar aventura preparada").click()
                expect(page.get_by_role("button", name="Començar aventura")).to_be_visible()
                # Explicitly confirm remote activation; test the real dialog.
                page.locator("summary").filter(has_text="Activació fora").click()
                page.once("dialog", lambda dialog: dialog.accept())
                page.get_by_role("button", name="Confirmar activació remota").click()
                expect(page.get_by_role("heading", name="Punt de partida")).to_be_visible()
                page.get_by_label("Decisions i notes").fill("La guia ajudarà el grup si respecten el santuari. SECRET-ONLY-DM")
                page.get_by_role("button", name="Desar nota", exact=True).click()
                expect(page.get_by_label("Decisions i notes")).to_have_value("")
                for title in ["Floració fora de lluna", "Temple de les Set Gotes", "Trobada i reforços"]:
                    page.get_by_role("button", name="Següent escena").click()
                    expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
                page.get_by_label("Decisions i notes").fill("Els reforços arriben des de la galeria nord.")
                page.get_by_role("button", name="Fer entrar la següent onada").click()
                expect(page.locator(".adv-combat-controls p")).to_contain_text("activades: 1, 2")
                expect(page.get_by_role("button", name="Següent escena")).to_be_enabled()
                expect(page.get_by_label("Decisions i notes")).to_have_value("Els reforços arriben des de la galeria nord.")
                page.get_by_role("button", name="Desar nota", exact=True).click()
                expect(page.get_by_label("Decisions i notes")).to_have_value("")
                expect(page.get_by_role("button", name="Fer entrar la següent onada")).to_be_disabled()
                shot("adventure-session.png")
                adventure = request("/campaign-records?campaign_id=demo&kind=adventure")[0]
                page.get_by_role("link", name="Obrir iniciativa").click()
                expect(page.get_by_role("heading", name="Assistent de combat")).to_be_visible()
                dashboard = request("/campaigns/demo")
                combat = next(c for c in dashboard["combats"] if c["id"] == adventure["data"]["combat_id"])
                assert len(combat["combatants"]) == 8, "Four PCs, three plants, one goblin"
                page.get_by_role("link", name="Tornar a l'aventura").click()
                page.locator("summary").filter(has_text="Resoldre sense completar").click()
                page.once("dialog", lambda dialog: dialog.accept())
                page.get_by_role("button", name="Confirmar resolució narrativa").click()
                expect(page.get_by_role("heading", name="Fugida del temple inundat", exact=True)).to_be_visible()
                page.get_by_label("Els jugadors tiren els daus físics").check()
                page.get_by_label("Resultat natural del d20").fill("17")
                page.get_by_label("Modificador", exact=True).fill("3")
                page.get_by_role("button", name="Registrar tirada").click()
                expect(page.locator(".adv-roll-result b")).to_have_text("20")
                page.locator("summary").filter(has_text="Guia de l'escena").click()
                shot("adventure-checks.png")
                page.reload()
                expect(page.locator(".adv-roll-result b")).to_have_text("20")
                public = json.dumps(request("/player-view/demo"))
                assert "SECRET-ONLY-DM" not in public and "Floraci" not in public
                page.get_by_role("button", name="Següent escena").click()
                page.get_by_role("button", name="Finalitzar aventura", exact=True).click()
                expect(page.get_by_role("heading", name="Aventura finalitzada")).to_be_visible()
                page.set_viewport_size({"width":390,"height":844})
                page.get_by_role("button", name="Preparar", exact=True).click()
                if page.locator(".adv-templates").get_attribute("open") is None:
                    page.locator("summary").filter(has_text="Sis punts de partida").click()
                page.get_by_role("button", name="El riu és testimoni", exact=False).click()
                expect(page.locator(".adv-wave")).to_have_count(1)
                expect(page.locator(".adv-xp")).to_contain_text("150 PX base")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow on mobile"
                shot("adventure-mobile.png")
                assert not errors, errors
                browser.close()
                print("PASS: template, mixed encounter, hex confirmation, scene flow, waves, combat link, manual d20, reload, player privacy, completion, 390px layout; no browser errors.")
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == "__main__":
    main()
