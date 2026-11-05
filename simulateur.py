"""
Lance le simulateur temps réel de la pompe à chaleur de fenêtre R290.

    python simulateur.py                      # interface web (ouvre le navigateur)
    python simulateur.py --port 9000 --sans-navigateur
    python simulateur.py --tk                 # ancienne interface matplotlib
    python simulateur.py --capture vue.png    # capture d'écran sans affichage
    python simulateur.py --capture vue.png --mode clim
"""

import argparse

import matplotlib


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", metavar="PNG", help="génère une image au lieu d'ouvrir la fenêtre")
    ap.add_argument("--mode", choices=["chauffage", "clim"], default="chauffage")
    ap.add_argument("--tk", action="store_true", help="ancienne interface matplotlib")
    ap.add_argument("--port", type=int, default=8765, help="port de l'interface web")
    ap.add_argument("--sans-navigateur", action="store_true", help="ne pas ouvrir le navigateur")
    args = ap.parse_args()

    if not (args.tk or args.capture):
        from pac_fenetre.serveur import lancer
        lancer(args.port, ouvrir=not args.sans_navigateur)
        return

    if args.capture:
        matplotlib.use("Agg")

    from pac_fenetre.interface import Simulateur

    sim = Simulateur()
    if args.mode == "clim":
        sim.rb_mode.set_active(1)
        sim.delai = 0.0
    if args.capture:
        sim.capture(args.capture)
        print(f"Capture enregistrée : {args.capture}")
    else:
        sim.lancer()


if __name__ == "__main__":
    main()
