"""
Serveur HTTP local de l'interface web du simulateur (bibliothèque standard).

    GET  /              page web (pac_fenetre/web/index.html)
    GET  /api/statique  données fixes (cloche P-h, réglages, technologies)
    POST /api/pas       {"dt": s réels, "regler": {...}} -> état courant
    GET  /api/optim/hypotheses   familles, matériaux, contraintes par défaut
    GET  /api/optim     avancement et résultats du dimensionnement des échangeurs
    POST /api/optim     {contraintes} -> lance le dimensionnement en tâche de fond

Le calcul physique reste en Python (CoolProp) ; le navigateur ne fait que
l'affichage. Un seul thread : les requêtes sont traitées dans l'ordre.
"""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .dimensionnement import Optimiseur, hypotheses
from .moteur import Moteur, _json

PAGE = Path(__file__).with_name("web") / "index.html"


def creer_serveur(port: int = 8765, hote: str = "127.0.0.1") -> HTTPServer:
    moteur = Moteur()
    optimiseur = Optimiseur()
    statique = json.dumps(moteur.statique()).encode()
    hyp_optim = json.dumps(_json(hypotheses())).encode()

    class Handler(BaseHTTPRequestHandler):
        def _repondre(self, corps: bytes, type_="application/json; charset=utf-8", code=200):
            self.send_response(code)
            self.send_header("Content-Type", type_)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._repondre(PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/statique":
                self._repondre(statique)
            elif self.path == "/api/optim/hypotheses":
                self._repondre(hyp_optim)
            elif self.path == "/api/optim":
                self._repondre(json.dumps(_json(optimiseur.instantane())).encode())
            else:
                self._repondre(b'{"erreur": "introuvable"}', code=404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/optim":
                lance = optimiseur.lancer(req)
                self._repondre(json.dumps({"lance": lance}).encode())
                return
            if self.path != "/api/pas":
                self._repondre(b'{"erreur": "introuvable"}', code=404)
                return
            if req.get("regler"):
                moteur.regler(req["regler"])
            dt = min(max(float(req.get("dt", 0.1)), 0.0), 0.5)
            self._repondre(json.dumps(moteur.pas(dt)).encode())

        def log_message(self, *_):  # pas de log à chaque requête
            pass

    return HTTPServer((hote, port), Handler)


def lancer(port: int = 8765, ouvrir: bool = True):
    srv = creer_serveur(port)
    url = f"http://127.0.0.1:{port}/"
    print(f"Simulateur disponible sur {url}  (Ctrl+C pour arrêter)")
    if ouvrir:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
