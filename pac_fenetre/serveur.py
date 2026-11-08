"""
Serveur HTTP local de l'interface web du simulateur (bibliothèque standard).

    GET  /              page web (pac_fenetre/web/index.html)
    GET  /api/statique  données fixes (cloche P-h, réglages, technologies)
    POST /api/pas       {"dt": s réels, "regler": {...}} -> état courant
    GET  /api/optim/hypotheses   familles, matériaux, contraintes par défaut
    GET  /api/optim     avancement et résultats du dimensionnement des échangeurs
    POST /api/optim     {contraintes} -> lance le dimensionnement en tâche de fond
    GET  /api/gyroide/hypotheses  paramètres réglables de l'échangeur gyroïde
    POST /api/gyroide   {paramètres} -> simulation PAC avec deux batteries gyroïdes
    GET  /api/comparer/hypotheses ; POST /api/comparer {paramètres} ; GET /api/comparer (avancement)
    GET  /vendor/...    bibliothèques JavaScript locales (three.js)

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
from .simu_gyroide import hypotheses_ui, simuler
from .comparateur import Comparateur, hypotheses_ui as hypotheses_comparateur

PAGE = Path(__file__).with_name("web") / "index.html"
VENDOR = Path(__file__).with_name("web") / "vendor"

# Connexion fermée par le navigateur avant la fin de la réponse (rechargement,
# préchargement de page, onglet fermé…) : sans conséquence, on l'ignore.
CONNEXION_COUPEE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


class _Serveur(HTTPServer):
    def handle_error(self, request, client_address):
        import sys
        if isinstance(sys.exc_info()[1], CONNEXION_COUPEE):
            return
        super().handle_error(request, client_address)


def creer_serveur(port: int = 8765, hote: str = "127.0.0.1") -> HTTPServer:
    moteur = Moteur()
    optimiseur = Optimiseur()
    statique = json.dumps(moteur.statique()).encode()
    hyp_optim = json.dumps(_json(hypotheses())).encode()
    hyp_gyro = json.dumps(_json(hypotheses_ui())).encode()
    comparateur = Comparateur()

    class Handler(BaseHTTPRequestHandler):
        def _repondre(self, corps: bytes, type_="application/json; charset=utf-8", code=200):
            try:
                self.send_response(code)
                self.send_header("Content-Type", type_)
                self.send_header("Content-Length", str(len(corps)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(corps)
            except CONNEXION_COUPEE:
                self.close_connection = True

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._repondre(PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/statique":
                self._repondre(statique)
            elif self.path == "/api/optim/hypotheses":
                self._repondre(hyp_optim)
            elif self.path == "/api/optim":
                self._repondre(json.dumps(_json(optimiseur.instantane())).encode())
            elif self.path == "/api/gyroide/hypotheses":
                self._repondre(hyp_gyro)
            elif self.path == "/api/comparer/hypotheses":
                self._repondre(json.dumps(_json(hypotheses_comparateur())).encode())
            elif self.path == "/api/comparer":
                self._repondre(json.dumps(_json(comparateur.instantane())).encode())
            elif self.path.startswith("/vendor/"):
                nom = self.path[len("/vendor/"):]
                f = VENDOR / nom
                if "/" in nom or ".." in nom or not f.is_file():
                    self._repondre(b'{"erreur": "introuvable"}', code=404)
                else:
                    self._repondre(f.read_bytes(), "text/javascript; charset=utf-8")
            else:
                self._repondre(b'{"erreur": "introuvable"}', code=404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/optim":
                lance = optimiseur.lancer(req)
                self._repondre(json.dumps({"lance": lance}).encode())
                return
            if self.path == "/api/comparer":
                self._repondre(json.dumps({"lance": comparateur.lancer(req)}).encode())
                return
            if self.path == "/api/gyroide":
                try:
                    res = simuler(req)
                except Exception as exc:  # paramètres hors domaine du modèle
                    res = {"ok": False, "message": f"Échec de la simulation : {exc}"}
                self._repondre(json.dumps(_json(res)).encode())
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

    return _Serveur((hote, port), Handler)


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
