"""Page HTML des résultats d'un cas CFD de l'échangeur Ø 150 (après resultats_d150.py).

Lit <cas>/resultat.json, cas.json, l'historique postProcessing/ et les coupes PNG, compare au cahier des charges
du module (docs/criteres_module.md : hA ≥ 1 104 W/K et Δp ≤ 25 Pa à 2 500 m³/h) et écrit
docs/formes/cylindre_d150_helice/resultats_<cas>.html (images intégrées).

    .venv/bin/python conception_echangeur/outils/cfd_3d/page_resultats_d150.py conception_echangeur/cfd_campagne/d150_helice/U2_5
"""
import base64
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs/formes/cylindre_d150_helice"
HA_REQUIS, DP_MAX, Q_REQUIS = 1104.0, 25.0, 2500.0          # criteres_module.md
PR23 = 0.71 ** (2 / 3)


def f(x, n=1):
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",")


def img(p):
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def main(cas: Path):
    r = json.loads((cas / "resultat.json").read_text())
    meta = json.loads((cas / "cas.json").read_text())
    dim = json.loads((SORTIE / "dimensions.json").read_text())
    zones = json.loads((SORTIE / "cfd/zones.json").read_text())
    rho = meta["air"]["rho"]
    U, Q = r["U_conduit"], r["debit_m3h"]
    dp, C = r["perte_charge_Pa"], r["mCp_W_K"]
    tf, tp = r["Tf"], r["Tp"]
    A_ech = zones["tubes"]["aire_m2"] + zones["ailette"]["aire_m2"]
    h = tf["hA_W_K"] / A_ech
    fj = dp / (tf["NTU"] * PR23 * rho * U ** 2 / 2)
    p = dim["parametres"]
    vol_L = math.pi * (p["d_ext_principal"] / 2e3) ** 2 * p["longueur_principal"] / 1e3 * 1e3
    n_mod = Q_REQUIS / Q
    ha_tot_f, ha_tot_p = n_mod * tf["hA_W_K"], n_mod * tp["hA_W_K"]
    p_vent = Q_REQUIS / 3600 * dp / 0.3

    # historique de convergence
    def hist(nom):
        return np.loadtxt(next((cas / "postProcessing" / nom).glob("*/surfaceFieldValue.dat")), comments="#")
    T, P = hist("TSortie"), hist("pEntree")
    pas = 300
    lignes = "".join(
        f"<tr><td class=n>{int(t[0])}</td><td class=n>{f(t[1], 3)}</td><td class=n>{f(t[2], 3)}</td>"
        f"<td class=n>{f(pp[1] * rho, 1)}</td></tr>"
        for t, pp in zip(T, P) if int(t[0]) % pas == 0)
    log = (cas / "log.simpleFoam").read_text(errors="ignore")
    duree = float(re.findall(r"ExecutionTime = ([\d.]+)", log)[-1])
    cellules = re.search(r"cells:\s+(\d+)", (cas / "log.checkMesh").read_text()).group(1)
    yp = r.get("yPlus", {})

    def fig(nom, legende):
        fp = cas / nom
        return (f"<figure style=margin:0><img src='{img(fp)}' alt='{legende}'><figcaption class=aide>{legende}</figcaption></figure>"
                if fp.exists() else "")

    ok = lambda c: "<span class=ok>oui</span>" if c else "<span class=ko>non</span>"
    html = f"""<!doctype html><html lang=fr><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>CFD Ø150 · {f(U)} m/s</title><style>
:root{{--fond:#f8f9fa;--carte:#fff;--texte:#212529;--doux:#5c636a;--trait:#dee2e6;--ok:#2b8a3e;--ko:#c92a2a}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--fond:#141517;--carte:#1f2023;--texte:#e9ecef;--doux:#adb5bd;--trait:#373a40;--ok:#69db7c;--ko:#ff8787}}}}
:root[data-theme=dark]{{--fond:#141517;--carte:#1f2023;--texte:#e9ecef;--doux:#adb5bd;--trait:#373a40;--ok:#69db7c;--ko:#ff8787}}
body{{margin:0;background:var(--fond);color:var(--texte);font:15px/1.5 system-ui,sans-serif}} main{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:24px;margin:0 0 6px}} h2{{font-size:18px;margin:26px 0 8px}} .carte{{background:var(--carte);border:1px solid var(--trait);border-radius:10px;padding:12px 16px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:14px}} td,th{{padding:5px 9px;border-bottom:1px solid var(--trait);text-align:left}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums}} .grille{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}}
img{{width:100%;border-radius:8px;border:1px solid var(--trait);background:#fff}} .aide{{color:var(--doux);font-size:13px}}
.ok{{color:var(--ok);font-weight:600}} .ko{{color:var(--ko);font-weight:600}} .chiffres{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}
.chiffres div{{background:var(--carte);border:1px solid var(--trait);border-radius:10px;padding:10px 14px}} .chiffres b{{display:block;font-size:24px}}</style></head><body><main>
<h1>CFD 3D de l'échangeur Ø 150 · {f(U)} m/s dans le conduit</h1>
<p class=aide>simpleFoam k-ω SST, {int(cellules) / 1e6:.2f} M mailles, 3 000 itérations sur AWS (64 cœurs, {duree / 60:.0f} min).
Moyennes sur les {r['fenetre_iterations']} dernières itérations. Air entrant à 0, tubes à 1 : ε est directement la température moyenne de sortie.</p>

<div class=chiffres>
<div>Débit d'air<b>{f(Q, 0)} m³/h</b><span class=aide>{f(r['debit_kg_s'] * 1e3, 1)} g/s</span></div>
<div>Perte de charge<b>{f(dp, 1)} Pa</b><span class=aide>entrée → sortie</span></div>
<div>Efficacité ε<b>{f(tf['epsilon'], 2)}</b><span class=aide>{f(tp['epsilon'], 2)} si l'ailette ne conduit pas</span></div>
<div>hA côté air<b>{f(tf['hA_W_K'], 1)} W/K</b><span class=aide>{f(tp['hA_W_K'], 1)} W/K si l'ailette ne conduit pas</span></div>
<div>Ventilateur (η = 0,3)<b>{f(r['puissance_ventilateur_W_eta03'], 2)} W</b><span class=aide>pour ce module seul</span></div>
</div>

<h2>Résultats détaillés</h2>
<div class=grille><div class=carte><table>
<tr><th>Grandeur</th><th class=n>Ailette froide</th><th class=n>Ailette passive</th></tr>
<tr><td>ε (T sortie moyenne pondérée par le débit)</td><td class=n>{f(tf['epsilon'], 3)}</td><td class=n>{f(tp['epsilon'], 3)}</td></tr>
<tr><td>NTU = −ln(1 − ε)</td><td class=n>{f(tf['NTU'], 2)}</td><td class=n>{f(tp['NTU'], 2)}</td></tr>
<tr><td>hA = NTU · ṁ·cp (ṁ·cp = {f(C, 1)} W/K)</td><td class=n><b>{f(tf['hA_W_K'], 1)} W/K</b></td><td class=n><b>{f(tp['hA_W_K'], 1)} W/K</b></td></tr>
<tr><td>Puissance pour 1 K d'écart air / propane</td><td class=n>{f(tf['W_par_K_d_ecart'], 1)} W</td><td class=n>{f(tp['W_par_K_d_ecart'], 1)} W</td></tr>
</table>
<p class=aide><b>Ailette froide</b> : ailette à la température des tubes (rendement d'ailette 100 %). <b>Ailette passive</b> : ailette
qui ne conduit pas, seuls les tubes échangent. La réalité est entre les deux, très près de l'ailette froide : aucun point de l'ailette n'est à plus d'environ
12 mm d'un tube, et avec 1 mm d'aluminium et h ≈ 73 W/m²·K le rendement d'ailette est d'environ 0,95.</p></div>
<div class=carte><table>
<tr><th>Grandeur</th><th class=n>Valeur</th></tr>
<tr><td>Surface d'échange (tubes + ailette)</td><td class=n>{f(A_ech, 3)} m²</td></tr>
<tr><td>h moyen (ailette froide)</td><td class=n>{f(h, 0)} W/m²·K</td></tr>
<tr><td>f/j apparent = Δp / (NTU · Pr<sup>2/3</sup> · ρu²/2)</td><td class=n>{f(fj, 1)}</td></tr>
<tr><td>Écart de Δp sur la fenêtre de moyenne</td><td class=n>{f(r['ecart_perte_charge_Pa'], 2)} Pa</td></tr>
<tr><td>Écart de ε sur la fenêtre de moyenne</td><td class=n>{f(tf['ecart_epsilon'], 4)}</td></tr>
<tr><td>y⁺ moyen tubes / ailette / parois</td><td class=n>{' / '.join(f(yp[k]['moyenne'], 1) for k in ('tubes', 'ailette', 'parois') if k in yp)}</td></tr>
</table>
<p class=aide>f/j inclut les pertes des conduits d'entrée et de sortie. Limite théorique (plaque lisse) ≈ 2.
y⁺ de quelques unités : la paroi est résolue presque jusqu'à la sous-couche visqueuse (lois de paroi de Spalding valables partout).</p></div></div>

<h2>Comparaison au cahier des charges du module</h2>
<div class=carte><table>
<tr><th>Exigence (criteres_module.md)</th><th class=n>Ce module</th><th class=n>Respectée ?</th></tr>
<tr><td>Débit d'air : {f(Q_REQUIS, 0)} m³/h</td><td class=n>{f(Q, 0)} m³/h, soit {f(Q / Q_REQUIS * 100, 1)} % du besoin</td><td class=n>{ok(Q >= Q_REQUIS)}</td></tr>
<tr><td>hA ≥ {f(HA_REQUIS, 0)} W/K</td><td class=n>{f(tf['hA_W_K'], 1)} W/K, soit {f(HA_REQUIS / tf['hA_W_K'], 0)} fois trop peu</td><td class=n>{ok(tf['hA_W_K'] >= HA_REQUIS)}</td></tr>
<tr><td>Δp ≤ {f(DP_MAX, 0)} Pa</td><td class=n>{f(dp, 1)} Pa</td><td class=n>{ok(dp <= DP_MAX)}</td></tr>
<tr><td colspan=3><b>Si on mettait {math.ceil(n_mod)} modules identiques en parallèle</b> (même vitesse, donc même ε et même Δp) :</td></tr>
<tr><td>hA total</td><td class=n>{f(ha_tot_f, 0)} W/K (ailette froide) · {f(ha_tot_p, 0)} W/K (passive)</td><td class=n>{ok(ha_tot_f >= HA_REQUIS)}</td></tr>
<tr><td>Perte de charge, ventilateur (η = 0,3)</td><td class=n>{f(dp, 1)} Pa · {f(p_vent, 0)} W</td><td class=n>{ok(dp <= DP_MAX)}</td></tr>
<tr><td>Volume occupé (cylindres seuls)</td><td class=n>{f(math.ceil(n_mod) * vol_L, 0)} L</td><td class=n>—</td></tr>
</table>
<p class=aide>Le canal en hélice échange correctement (h ≈ {f(h, 0)} W/m²·K, ε = {f(tf['epsilon'], 2)} en un seul passage), mais il ne laisse passer
que {f(Q, 0)} m³/h : tout l'air passe par une section de 100 × 50 mm = 0,005 m², alors que le cahier des charges demande une section libre
de 0,15 à 0,34 m² (30 à 70 fois plus). Le défaut n'est pas la forme des tubes ou de l'ailette mais le débit traversant.</p></div>

<h2>Convergence</h2>
<div class=carte><table><tr><th class=n>Itération</th><th class=n>ε froide</th><th class=n>ε passive</th><th class=n>p entrée (Pa)</th></tr>{lignes}</table>
<p class=aide>Δp stable dès l'itération 300 ; ε stable dès ≈ 1 200 (variation &lt; 0,2 % ensuite).</p></div>

<h2>Pression</h2>
<div class=grille>
{fig('coupe_meridienne_p.png', "Coupe verticale par l'axe : la pression baisse régulièrement d'un tour à l'autre (≈ 10 Pa par tour), sans obstacle localisé.")}
{fig('coupe_horizontale_mil_p.png', 'Coupe à mi-hauteur.')}
{fig('coupe_horizontale_bas_p.png', "Coupe au niveau du conduit d'entrée.")}
</div>
<h2>Vitesse</h2>
<div class=grille>
{fig('coupe_horizontale_mil_U.png', "Mi-hauteur : l'air va plus vite près du noyau (chemin plus court) ; chaque tube laisse un sillage lent derrière lui.")}
{fig('coupe_meridienne_U.png', "Coupe verticale par l'axe.")}
{fig('coupe_horizontale_bas_U.png', "Au niveau du conduit d'entrée : le jet entrant.")}
</div>
<h2>Température, ailette froide (Tf)</h2>
<div class=grille>
{fig('coupe_meridienne_Tf.png', "Coupe verticale : l'air (0, noir) se réchauffe en montant le long de l'hélice vers 1 (température des tubes). Il chauffe d'abord contre l'ailette.")}
{fig('coupe_horizontale_mil_Tf.png', 'Coupe à mi-hauteur.')}
{fig('coupe_horizontale_bas_Tf.png', "Au niveau du conduit d'entrée.")}
</div>
<h2>Température, ailette passive (Tp)</h2>
<div class=grille>
{fig('coupe_meridienne_Tp.png', "Coupe verticale : seuls les tubes chauffent l'air.")}
{fig('coupe_horizontale_mil_Tp.png', 'Coupe à mi-hauteur.')}
{fig('coupe_horizontale_bas_Tp.png', "Au niveau du conduit d'entrée.")}
</div>
<p class=aide>Données : {cas.relative_to(RACINE.parent)} · les champs complets restent sur le disque de la machine AWS (arrêtée).</p>
</main></body></html>"""
    out = SORTIE / f"resultats_{cas.name}.html"
    out.write_text(html)
    print(out, len(html) // 1024, "ko")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
