"""Pré-dimensionnement des deux ventilateurs de la PAC de fenêtre (sans dépendance).

Points de fonctionnement repris du cahier des charges des échangeurs (pac_9000btu.html) :
intérieur 800 m³/h, extérieur 2 500 m³/h, 25 Pa de perte de charge par batterie.

Ce que calcule le script :
1. le poids des ventilateurs dans le COP visé (pourquoi chaque watt compte) ;
2. la perte de sortie ½ρc² d'un axial sans diffuseur, qui s'ajoute aux 25 Pa ;
3. pour plusieurs diamètres : vitesse de bout de pale et tr/min pour un coefficient de pression
   ψ typique, coefficient de débit φ, puissance électrique selon le rendement global ;
4. le rendement réel d'un ventilateur EC du commerce (ventilateurs/W1G200-EC87-20.json).

Définitions (Carolus, « Ventilatoren ») : u = π D n ; φ = Q / (π D²/4 · u) ; ψ = 2 Δp_t / (ρ u²).
Plages usuelles : axial basse pression ψ ≈ 0,1–0,3 et φ ≈ 0,15–0,35 ;
centrifuge à aubes arrière ψ ≈ 0,8–1,1 (u et D à la sortie de roue).

Lancer : python3 conception_ventilateur/outils/predimensionnement.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

RHO = 1.2          # kg/m³ (air ≈ 20 °C ; 1,33 à −8 °C : +11 % de pression à même vitesse)
Q_UTILE = 2638.0   # W, 9 000 BTU/h
POINTS = {"intérieur": 800.0, "extérieur": 2500.0}   # m³/h
DP_BATTERIE = 25.0  # Pa
COP_CIBLES = (4.0, 6.0)


def fmt(x, n=1):
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",")


def poids_dans_cop():
    print("## 1. Poids des ventilateurs dans le COP\n")
    print("| COP visé | Puissance élec. totale W | Ventilateurs 76 W (η 0,30) | Ventilateurs 40 W (η ≈ 0,55) | COP si 76 → 40 W |")
    print("|---|---|---|---|---|")
    for cop in COP_CIBLES:
        p = Q_UTILE / cop
        print(f"| {fmt(cop)} | {fmt(p, 0)} | {fmt(76 / p * 100, 0)} % | {fmt(40 / p * 100, 0)} % "
              f"| {fmt(Q_UTILE / (p - 36), 2)} |")
    print()


def perte_sortie():
    print("## 2. Perte de sortie d'un axial libre (énergie cinétique perdue)\n")
    print("| Échangeur | D mm | moyeu/D | c sortie m/s | ½ρc² Pa | Δp_total Pa | part perdue |")
    print("|---|---|---|---|---|---|---|")
    for nom, q in POINTS.items():
        for D in ((0.20, 0.25, 0.30) if nom == "intérieur" else (0.30, 0.40, 0.50)):
            nu = 0.35
            a = math.pi / 4 * D**2 * (1 - nu**2)
            c = q / 3600 / a
            pd = 0.5 * RHO * c**2
            print(f"| {nom} | {D*1000:.0f} | {fmt(nu, 2)} | {fmt(c)} | {fmt(pd)} | {fmt(DP_BATTERIE + pd)} "
                  f"| {fmt(pd / (DP_BATTERIE + pd) * 100, 0)} % |")
    print("\nLa composante tangentielle (giration) s'ajoute si rien ne la redresse (stator, aubes directrices).\n")


def balayage(psi=0.20, rend=(0.30, 0.45, 0.60)):
    print(f"## 3. Axial, ψ = {fmt(psi, 2)}, perte de sortie récupérée à 50 % (diffuseur court)\n")
    print("| Échangeur | D mm | Δp_t Pa | u bout m/s | tr/min | φ | P élec. W à η = " +
          " / ".join(fmt(r, 2) for r in rend) + " |")
    print("|---|---|---|---|---|---|---|")
    for nom, q_h in POINTS.items():
        q = q_h / 3600
        for D in ((0.20, 0.25, 0.30) if nom == "intérieur" else (0.30, 0.40, 0.50)):
            a = math.pi / 4 * D**2 * (1 - 0.35**2)
            dpt = DP_BATTERIE + 0.5 * 0.5 * RHO * (q / a) ** 2
            u = math.sqrt(2 * dpt / (RHO * psi))
            n = u / (math.pi * D) * 60
            phi = q / (math.pi * D**2 / 4 * u)
            p = " / ".join(fmt(q * dpt / r, 0) for r in rend)
            print(f"| {nom} | {D*1000:.0f} | {fmt(dpt)} | {fmt(u)} | {n:.0f} | {fmt(phi, 2)} | {p} |")
    print("\nφ hors de 0,15–0,35 : diamètre mal adapté au débit. Le bruit croît comme u⁵ à u⁶ :"
          " à débit égal, le grand diamètre lent gagne.\n")


def ventilateur_reel():
    f = Path(__file__).resolve().parents[2] / "ventilateurs" / "W1G200-EC87-20.json"
    if not f.exists():
        return
    d = json.loads(f.read_text(encoding="utf-8"))
    print(f"## 4. Rendement statique mesuré : {d['nom']}\n")
    print("| tr/min | m³/h | Δp Pa | P élec. W | η statique global |")
    print("|---|---|---|---|---|")
    for c in d["courbes"]:
        for q, dp, p in zip(c["q_m3h"], c["dp_Pa"], c["P_W"]):
            if dp > 0:
                print(f"| {c['n_tr_min']} | {q:.0f} | {dp:.0f} | {fmt(p)} | {fmt(q / 3600 * dp / p, 2)} |")
    print("\nUn bon ventilateur EC de 200 mm du commerce : η ≈ 0,2–0,3 au point utile. L'hypothèse 0,30"
          " du cahier des charges est donc « bon produit standard » ; la cible du dossier est 0,50–0,60.\n")


if __name__ == "__main__":
    poids_dans_cop()
    perte_sortie()
    balayage()
    ventilateur_reel()
