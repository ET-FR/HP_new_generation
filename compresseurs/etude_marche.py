#!/usr/bin/env python3
"""Génère compresseurs/etude_compresseurs.html : étude de marché des compresseurs R290 pour la PAC de fenêtre.

Les chiffres viennent des fiches enregistrées dans compresseurs/sources/<famille>/ (voir SOURCES.md de chaque
dossier). η_is global = ṁ · Δh_isentropique / P_électrique, recalculé avec CoolProp (même définition que
fiche_pac_9000.py, qui compte toute la puissance du compresseur dans ṁ·Δh_is/η_is).

Usage : .venv/bin/python compresseurs/etude_marche.py
"""
import html
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(RACINE / "conception_echangeur" / "outils" / "analytique"))

import CoolProp.CoolProp as CP  # noqa: E402

FL = "Propane"
SRC = ICI / "sources"
FAMILLES = [("chine_taiwan", "Chine et Taïwan (GMCC, Highly, Landa, Rechi)"),
            ("japon_coree", "Japon, Corée, Thaïlande (Panasonic, LG, Mitsubishi, Samsung…)"),
            ("europe_usa", "Europe et États-Unis (Danfoss, Secop, Embraco, Tecumseh, Aspen, Copeland)"),
            ("concurrents_marche", "Concurrents, marché, réglementation, rendements publiés")]

# ------------------------------------------------------------------ besoin (fiche_pac_9000, étape 1)
POINTS = [("Clim 35 °C", 14, 40, 8.69, 2.09), ("Chauffage 8,3 °C", 3.5, 32, 7.26, 2.34),
          ("Chauffage −8,3 °C", -12, 32, 7.00, 3.61), ("Chauffage −15 °C", -19, 32, 6.87, 4.45)]
ETA_V = 0.90


def psat(T, q):
    return CP.PropsSI("P", "T", T + 273.15, "Q", q, FL)


def taux(Te, Tc):
    return psat(Tc, 0) / psat(Te, 1)


def eta_ashrae(froid_W, P_W, Te=7.2, Tc=54.4, Ts=35.0, Tl=46.1):
    """η_is global au point ASHRAE à partir de la puissance froid et de la puissance électrique."""
    pe, pc = psat(Te, 1), psat(Tc, 0)
    h1 = CP.PropsSI("H", "T", Ts + 273.15, "P", pe, FL)
    s1 = CP.PropsSI("S", "T", Ts + 273.15, "P", pe, FL)
    h3 = CP.PropsSI("H", "T", Tl + 273.15, "P", pc, FL)
    h2s = CP.PropsSI("H", "P", pc, "S", s1, FL)
    m = froid_W / (h1 - h3)
    return m * (h2s - h1) / P_W


def vitesse(V_asp_m3h, cyl_cm3):
    return V_asp_m3h / 3600 / (ETA_V * cyl_cm3 * 1e-6)


# ------------------------------------------------------------------ candidats (rotatifs R290 à variateur)
# (fabricant, modèle, type, cm³, vmax rps ou None, η_is global, statut η, condition, huile, encombrement, dossier, fichier, url, note)
# statut : "cat" chiffre catalogue vérifiable ; "conf" dépend d'une condition non définie ; "proto" prototype
PANA = ("japon_coree", "panasonic_HVACR_catalogue_2026.pdf",
        "https://industry.panasonic.eu/storage/custom-upload/Devices/Panasonic_HVAC_R_Catalogue_2026.pdf")
LG = ("japon_coree", "lg_rotary_catalog_2022.pdf",
      "https://cdn.shopify.com/s/files/1/0605/9560/1544/files/LG_Rotary_Compressor_Catalog_2022_20230420_143824.pdf")
GMCC_HP = ("chine_taiwan", "GMCC_Welling_brochure_pompes_a_chaleur_2024_nuernbergmesse.pdf",
           "https://images.nuernbergmesse.de/files/6fbf8406-3844-f991-6fb0-8720e3179dbe.pdf")
GMCC_CAT = ("chine_taiwan", "GMCC_catalogue_rotatif_2024_hvacrcompressor.pdf",
            "https://www.hvacrcompressor.com/downloadpdf/GMCC-rotary-compressor-catalogue.pdf")
GMCC_210 = ("chine_taiwan", "GMCC_EDTN210D32EFZ_R290_21cc_akkudoktor.pdf",
            "https://akkudoktor.net/uploads/short-url/td8QM6XccsT73eRC9jk7BlpOhMP.pdf")
LANDA = ("chine_taiwan", "Landa_catalogue_2023_climatisation_domestique_commercial.pdf",
         "http://www.landa.com.cn/uploads/file/20230627/8f921d6b1ec4d888e9ff3a2bd7180895.pdf")
RECHI = ("chine_taiwan", "Rechi_catalogue_2026_climatisation_deshumidification.pdf",
         "https://www.rechi.com/folder/2026%E5%B9%B4%E7%A9%BA%E8%AA%BF%E9%99%A4%E6%BA%BC%E5%9E%8B%E9%8C%84.pdf")
HIGHLY = ("chine_taiwan", "Highly_catalogue_rotatif_hubhvacr_2023.pdf",
          "https://hubhvacr.com/wp-content/uploads/2023/06/Highly-Rotary-Compressor-Catalog-PDF.pdf")
DANF = ("europe_usa", "danfoss_VRN_guide_application_AB463930637612.pdf",
        "https://assets.danfoss.com/documents/455089/AB463930637612en-000202.pdf")
ORNL = ("japon_coree", "ornl_window_AC_propane_limited_charge_Pub119670.pdf",
        "https://info.ornl.gov/sites/publications/Files/Pub119670.pdf")
ASPEN = ("europe_usa", "aspen_H-Series_7.6cc_perf_R290.pdf",
         "https://www.aspencompressor.com/_files/ugd/87858f_be1fede5ef2348ee9bdc211d484e605f.pdf")

C = []


def cand(fab, mod, typ, cyl, vmax, eta, statut, cond, huile, dim, src, note=""):
    C.append(dict(fab=fab, mod=mod, typ=typ, cyl=cyl, vmax=vmax, eta=eta, statut=statut, cond=cond,
                  huile=huile, dim=dim, src=src, note=note))


cand("Panasonic", "7WD138Z", "bicylindre", 13.9, None, eta_ashrae(3365 - 725, 725), "cat",
     "ASHRAE ; chaud 3 365 W / 725 W, froid pris = chaud − P", "?", "Ø104 × 267 mm", PANA,
     "meilleur η publié ; vitesse max à demander")
cand("Panasonic", "7SD110Z", "bicylindre", 11.2, None, eta_ashrae(1990, 570), "cat",
     "ASHRAE ; froid 1 990 W / 570 W", "?", "Ø95 × 225 mm", PANA, "cylindrée la plus proche de 10,8 cm³")
cand("Panasonic", "7TD075Z", "bicylindre", 7.5, None, eta_ashrae(1340, 380), "cat",
     "ASHRAE ; froid 1 340 W / 380 W", "?", "Ø84 × 203 mm", PANA, "trop petit pour −15 °C")
cand("LG", "PST102MA", "2 pistons", 10.2, 90, eta_ashrae(1890, 531), "cat",
     "ASHRAE 60 Hz ; 1 890 W / 531 W", "?", "H 218,6 mm", LG, "90 rps max : −15 °C hors portée")
cand("LG", "PAT134MA", "2 pistons", 13.4, 90, eta_ashrae(2419, 697), "cat",
     "ASHRAE 60 Hz ; 2 419 W / 697 W", "?", "H 249 mm", LG, "102 rps requis > 90")
cand("LG", "PST092MA", "2 pistons", 9.2, 90, eta_ashrae(1664, 481), "cat",
     "ASHRAE 60 Hz ; 1 664 W / 481 W", "?", "H 220,6 mm", LG, "")
cand("GMCC", "RDTN150D54TEZ3", "bicylindre", 14.9, 120, 0.67, "cat",
     "SEER60 (Te 2,8 / Tc 42,3, variateur inclus) ; 3 244 W ch / 645 W", "?", "?", GMCC_HP,
     "meilleur COP GMCC publié")
cand("GMCC", "EDTN150D32EFZ", "bicylindre", 15.0, 120, 0.65, "cat",
     "SEER60 ; 3 210 W ch / 652 W", "PAG (famille EDTN : 300 ml pour 21 cm³)", "?", GMCC_HP,
     "en stock en Europe (AREA Cooling)")
cand("GMCC", "DSN180D54UEZ3", "monocylindre", 18.0, None, 0.71, "cat",
     "SEER60 ; 3 120 W / 735 W", "?", "H 250 mm", GMCC_CAT, "« en développement »")
cand("GMCC", "EDTN210D32EFZ", "bicylindre", 21.0, 120, 0.65, "cat",
     "SEER60, 60 rps ; 4 415 W ch / 900 W", "300 ml PAG", "8,45 kg", GMCC_210,
     "seule fiche complète (enveloppe, bruit 67+4 dB(A)) ; 108–148 USD")
cand("Landa (Gree)", "QXDS-N150zX170", "?", 15.0, 120, 0.70, "cat",
     "GB chinoise (Te 7,2 / Tc 46) ; 3 050 W / 701 W", "?", "H 275 mm", LANDA, "")
cand("Rechi", "QP180SJ70", "monocylindre", 18.0, None, 0.68, "cat",
     "GB chinoise ; 3 580 W / 845 W (0,735 hors variateur)", "?", "?", RECHI, "")
cand("Rechi", "39P22LA", "monocylindre", 14.0, None, 0.685, "cat",
     "ASHRAE/T ; 2 675 W / 795 W (0,74 hors variateur)", "?", "?", RECHI, "")
cand("Highly", "PSD140RKQ-6B", "monocylindre", 14.0, None, 0.77, "conf",
     "« New GB » non définie ; 2 810 W, COP 4,75", "?", "H 235 mm", HIGHLY,
     "0,77 seulement si « New GB » = GB chinoise")
cand("Highly", "PTD175RKQ-6B", "bicylindre", 17.5, None, 0.80, "conf",
     "« New GB » non définie ; 3 650 W, COP 4,93", "?", "H 240,9 mm", HIGHLY, "idem")
cand("Danfoss (fab. Highly)", "VRN150WSQASE", "monocylindre", 15.0, 120, None, "cat",
     "aucune performance publiée (Coolselector)", "POE 0,48 L", "Ø113 × 308 mm, 8,9 kg", DANF,
     "échantillon MOQ 1 (126X2025) avec variateur CDS203 ; Lw 74 dB(A)")
cand("Highly pour ORNL", "prototype R290", "rotatif", 16.0, None, 0.785, "proto",
     "mesuré, Tsat asp. 46–54 °F, taux ≈ 2,3–2,9 : 0,77 à 0,80", "270 ml (série)", "?", ORNL,
     "le compresseur de série PSD162XW : 0,67")
cand("Aspen (USA)", "H76", "rotatif horizontal 24/48 V", 7.6, 108, 0.48, "cat",
     "fiche R290, zone utile 0,45–0,52 (0,37–0,40 à Te −20 °C)", "130 cm³", "≈ 3,2 kg", ASPEN,
     "trop petit : 1,4 kW à Te −20 °C")


# ------------------------------------------------------------------ outils HTML
def e(x):
    return html.escape(str(x))


def f(x, n=2):
    return "?" if x is None else f"{x:.{n}f}".replace(".", ",")


def lien_src(src, texte=None):
    dossier, fichier, url = src
    return (f'<a href="sources/{dossier}/{e(fichier)}">{e(texte or fichier)}</a> · '
            f'<a href="{e(url)}">en ligne</a>')


def md_inline(t, dossier):
    t = e(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"(https?://[^\s<|)]+)", r'<a href="\1">\1</a>', t)

    def fichier(m):
        nom = m.group(0)
        return f'<a href="sources/{dossier}/{nom}">{nom}</a>' if (SRC / dossier / html.unescape(nom)).exists() else nom
    t = re.sub(r"(?<![/\w.-])[\w.\-]+\.(?:pdf|html)(?![\w/])", fichier, t)
    return t


def md_vers_html(texte, dossier):
    """Convertisseur minimal pour les SOURCES.md (titres, paragraphes, tableaux, listes)."""
    out, tab = [], None
    for ligne in texte.splitlines():
        s = ligne.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            if tab is None:
                tab = ["<div class='carte'><table><tr>" + "".join(f"<th>{md_inline(c, dossier)}</th>" for c in cells) + "</tr>"]
            else:
                tab.append("<tr>" + "".join(f"<td>{md_inline(c, dossier)}</td>" for c in cells) + "</tr>")
            continue
        if tab is not None:
            out.append("".join(tab) + "</table></div>")
            tab = None
        if not s:
            continue
        if s.startswith("# "):
            continue  # le titre de famille est donné par le rapport
        if s.startswith("#"):
            out.append(f"<h4>{md_inline(s.lstrip('#').strip(), dossier)}</h4>")
        elif s.startswith(("- ", "* ")):
            out.append(f"<p class='note'>• {md_inline(s[2:], dossier)}</p>")
        else:
            out.append(f"<p class='note'>{md_inline(s, dossier)}</p>")
    if tab is not None:
        out.append("".join(tab) + "</table></div>")
    return "\n".join(out)


# ------------------------------------------------------------------ graphique η_is global / cylindrée
def graphique():
    W, H, ml, mr, mt, mb = 760, 380, 56, 20, 16, 46
    x0, x1, y0, y1 = 6, 22, 0.40, 0.85
    X = lambda v: ml + (v - x0) / (x1 - x0) * (W - ml - mr)  # noqa: E731
    Y = lambda v: mt + (y1 - v) / (y1 - y0) * (H - mt - mb)  # noqa: E731
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Rendement isentropique global en fonction de la cylindrée">']
    for v in [0.40, 0.50, 0.60, 0.70, 0.80]:
        o.append(f'<line x1="{ml}" x2="{W-mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grille"/>'
                 f'<text x="{ml-8}" y="{Y(v)+4:.1f}" text-anchor="end" class="axe">{f(v)}</text>')
    for v in range(6, 23, 2):
        o.append(f'<text x="{X(v):.1f}" y="{H-mb+18}" text-anchor="middle" class="axe">{v}</text>')
    o.append(f'<text x="{(ml+W-mr)/2}" y="{H-6}" text-anchor="middle" class="axe">cylindrée (cm³/tr)</text>')
    o.append(f'<text x="14" y="{(mt+H-mb)/2}" text-anchor="middle" class="axe" transform="rotate(-90 14 {(mt+H-mb)/2})">η_is global</text>')
    # bande « vitesse requise ≤ 120 rps à −15 °C » : cylindrée ≥ 4,45/3600/(0,9·120) → 11,4 cm³
    cmin = 4.45 / 3600 / (ETA_V * 120) * 1e6
    o.append(f'<rect x="{X(cmin):.1f}" y="{mt}" width="{X(x1)-X(cmin):.1f}" height="{H-mt-mb}" class="zone"/>'
             f'<text x="{X(cmin)+6:.1f}" y="{H-mb-8}" class="axe">≥ {f(cmin,1)} cm³ : −15 °C tenu sous 120 rps</text>')
    o.append(f'<line x1="{ml}" x2="{W-mr}" y1="{Y(0.75):.1f}" y2="{Y(0.75):.1f}" class="cible"/>'
             f'<text x="{W-mr-4}" y="{Y(0.75)-6:.1f}" text-anchor="end" class="axe">hypothèse de la fiche : 0,75</text>')
    o.append(f'<line x1="{X(10.8):.1f}" x2="{X(10.8):.1f}" y1="{mt}" y2="{H-mb}" class="cible"/>'
             f'<text x="{X(10.8)+4:.1f}" y="{mt+12}" class="axe">10,8 cm³ (fiche)</text>')
    etiq = {"7WD138Z": (8, 4, "start"), "PST102MA": (-8, -8, "end"), "7SD110Z": (8, 18, "start"),
            "PSD140RKQ-6B": (-9, -5, "end"), "PTD175RKQ-6B": (8, -8, "start"), "prototype R290": (8, 16, "start"),
            "RDTN150D54TEZ3": (8, 4, "start"), "H76": (8, 4, "start"), "QXDS-N150zX170": (8, -6, "start")}
    for c in C:
        if c["eta"] is None:
            continue
        cls = {"cat": "s1", "conf": "s2", "proto": "s3"}[c["statut"]]
        x, y = X(c["cyl"]), Y(c["eta"])
        tip = f'{c["fab"]} {c["mod"]} · {f(c["cyl"],1)} cm³ · η {f(c["eta"])} · {c["cond"]}'
        o.append(f'<g class="pt"><circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="transparent"/>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="{cls}"/><title>{e(tip)}</title></g>')
        if c["mod"] in etiq:
            dx, dy, ancre = etiq[c["mod"]]
            o.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" text-anchor="{ancre}" class="lab">{e(c["mod"])}</text>')
    o.append("</svg>")
    return "".join(o)


# ------------------------------------------------------------------ page
def page():
    import fiche_pac_9000 as FP  # sensibilité du COP de l'unité au rendement du compresseur
    sens = []
    for k, ch in FP.CHOIX.items():
        cib, _ = FP.cible(k)
        cops = [FP.cop_unite(k, ch["Te"], ch["Tc"], ch["Vi"], ch["Ve"], eta=x)[0] for x in (0.67, 0.70, 0.72, 0.74, 0.75, 0.80)]
        sens.append((k, cib, cops))
    noms = {"clim": "Clim 35 °C", "ch47": "Chauffage 8,3 °C", "ch17": "Chauffage −8,3 °C", "ch5": "Chauffage −15 °C"}

    lignes_besoin = "".join(
        f"<tr><td>{n}</td><td class='n'>{f(Te,1)} / {f(Tc,0)}</td><td class='n'>{f(taux(Te,Tc))}</td>"
        f"<td class='n'>{f(psat(Te,1)/1e5,1)} / {f(psat(Tc,0)/1e5,1)}</td><td class='n'>{f(m)}</td><td class='n'>{f(V)}</td>"
        f"<td class='n'>{vitesse(V,10.8):.0f}</td><td class='n'>{vitesse(V,15):.0f}</td></tr>"
        for n, Te, Tc, m, V in POINTS)

    def ligne_cand(c):
        req = [vitesse(p[4], c["cyl"]) for p in POINTS]
        vmax = c["vmax"]
        r15 = req[3]
        ok = "" if vmax is None else ("ok" if r15 <= vmax else "alerte")
        r15s = f"<span class='{ok}'>{r15:.0f}</span>" if ok else f"{r15:.0f}"
        st = {"cat": "", "conf": " <span class='alerte'>(à confirmer)</span>", "proto": " <i>(prototype)</i>"}[c["statut"]]
        return (f"<tr><td><b>{e(c['fab'])}</b><br>{e(c['mod'])}</td><td>{e(c['typ'])}</td><td class='n'>{f(c['cyl'],1)}</td>"
                f"<td class='n'>{'?' if vmax is None else vmax}</td><td class='n'>{req[0]:.0f}</td><td class='n'>{r15s}</td>"
                f"<td class='n'><b>{f(c['eta'])}</b>{st}</td><td>{e(c['cond'])}</td><td>{e(c['huile'])}</td><td>{e(c['dim'])}</td>"
                f"<td>{e(c['note'])}</td><td class='src'>{lien_src(c['src'], 'fiche')}</td></tr>")

    tab_cand = "".join(ligne_cand(c) for c in sorted(C, key=lambda c: -(c["eta"] or 0)))

    def cel(x, cib):
        return f"<td class='n {'ok' if x >= cib else 'alerte'}'>{f(x)}</td>"
    tab_sens = "".join(f"<tr><td>{noms[k]}</td><td class='n'><b>{f(cib)}</b></td>{''.join(cel(x, cib) for x in cops)}</tr>"
                       for k, cib, cops in sens)

    sources = []
    for d, titre in FAMILLES:
        md = (SRC / d / "SOURCES.md").read_text(encoding="utf-8")
        fichiers = sorted(p.name for p in (SRC / d).iterdir() if p.name != "SOURCES.md")
        sources.append(f"<h3>{e(titre)}</h3><p class='note'>Liste d'origine : <a href='sources/{d}/SOURCES.md'>sources/{d}/SOURCES.md</a> · "
                       f"{len(fichiers)} fichiers enregistrés dans <code>sources/{d}/</code></p>" + md_vers_html(md, d))
    n_fichiers = sum(1 for p in SRC.rglob("*") if p.is_file() and p.name != "SOURCES.md")

    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Compresseurs R290 du marché</title>
<style>
:root {{ --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; --accent:#1c7ed6;
  --ok:#2b8a3e; --alerte:#c92a2a; --cle:#fff9db; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --zone:#e7f5ff; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --fond:#141517; --carte:#1f2023;
  --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; --ok:#69db7c; --alerte:#ff8787; --cle:#2b2a1d;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --zone:#1b3550; }} }}
:root[data-theme="dark"] {{ --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40;
  --accent:#4dabf7; --ok:#69db7c; --alerte:#ff8787; --cle:#2b2a1d; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --zone:#1b3550; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--fond); color:var(--texte); font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; }} h2 {{ font-size:19px; margin:36px 0 8px; border-bottom:2px solid var(--trait); padding-bottom:4px; }}
h3 {{ font-size:16px; margin:20px 0 6px; }} h4 {{ font-size:14.5px; margin:14px 0 4px; }}
a {{ color:var(--accent); overflow-wrap:anywhere; }}
.sous {{ color:var(--doux); margin:0 0 18px; }}
.carte {{ background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:14px 16px; margin:10px 0; overflow-x:auto; }}
.cle {{ background:var(--cle); }} .cle ol, .cle ul {{ margin:4px 0; padding-left:22px; }} .cle li {{ margin:6px 0; }}
table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--trait); vertical-align:top; }}
th {{ color:var(--doux); font-weight:600; }}
td.n, th.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td.src {{ white-space:nowrap; font-size:12.5px; }}
code {{ font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:12.5px; }}
.note {{ color:var(--doux); font-size:13.5px; margin:6px 0; }}
.alerte {{ color:var(--alerte); font-weight:600; }} .ok {{ color:var(--ok); font-weight:600; }}
svg {{ width:100%; height:auto; display:block; }}
svg .grille {{ stroke:var(--trait); stroke-width:1; }} svg .axe {{ fill:var(--doux); font-size:12px; }}
svg .lab {{ fill:var(--texte); font-size:11.5px; }} svg .cible {{ stroke:var(--doux); stroke-width:1.5; stroke-dasharray:5 4; }}
svg .zone {{ fill:var(--zone); opacity:.7; }}
svg .s1 {{ fill:var(--s1); }} svg .s2 {{ fill:var(--s2); }} svg .s3 {{ fill:var(--s3); }}
svg circle.s1, svg circle.s2, svg circle.s3 {{ stroke:var(--carte); stroke-width:2; }}
svg .pt:hover circle:last-of-type {{ r:7; }}
.leg span {{ display:inline-flex; align-items:center; gap:6px; margin-right:16px; font-size:13px; color:var(--doux); }}
.leg i {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
nav ol {{ margin:0; padding-left:20px; columns:2; font-size:14px; }}
@media (max-width:640px) {{ nav ol {{ columns:1; }} }}
</style></head><body><main>
<h1>Compresseurs R290 du marché pour la PAC de fenêtre 9 000 BTU/h</h1>
<p class="sous">Étude de marché, 11/11/2026 · généré par <code>compresseurs/etude_marche.py</code> ·
{n_fichiers} documents enregistrés dans <code>compresseurs/sources/</code> · besoin tiré de <a href="../pac_9000btu.html">pac_9000btu.html</a></p>

<nav class="carte"><ol>
<li><a href="#bref">En bref</a></li><li><a href="#besoin">Le besoin</a></li><li><a href="#methode">Comment on compare</a></li>
<li><a href="#tableau">Les candidats</a></li><li><a href="#graphe">Rendement et cylindrée</a></li><li><a href="#cop">Effet sur le COP de la machine</a></li>
<li><a href="#choix">Recommandation</a></li><li><a href="#ecartes">Écartés</a></li><li><a href="#concurrents">Concurrents</a></li>
<li><a href="#regle">Réglementation</a></li><li><a href="#technique">Points techniques</a></li><li><a href="#demandes">Demandes à envoyer</a></li>
<li><a href="#sources">Toutes les sources</a></li></ol></nav>

<h2 id="bref">En bref</h2>
<div class="carte cle"><ol>
<li><b>Aucun compresseur R290 de catalogue ne tient vérifiablement η_is = 0,75</b> (rendement global : puissance isentropique ÷ puissance électrique, comme dans la fiche).
Les meilleurs chiffres publiés, recalculés au point ASHRAE (taux de compression 3,2), sont : <b>Panasonic 7WD138Z 0,74</b>, LG PST102MA 0,725,
Panasonic 7SD110Z 0,71, GMCC DSN180D54UEZ3 0,71, Landa QXDS-N150zX170 0,70. Le seul 0,77–0,80 mesuré est un <b>prototype Highly optimisé pour ORNL</b>
(le modèle de série du même essai : 0,67). Highly annonce peut-être 0,77–0,80 en catalogue (PSD140RKQ-6B, PTD175RKQ-6B), mais la condition d'essai n'est pas définie.</li>
<li><b>La cylindrée de 10,8 cm³ à 128 tr/s n'existe pas</b> : la vitesse maximale des rotatifs R290 à variateur est de 90 tr/s (LG) à 120 tr/s (GMCC, Danfoss, Landa).
<b>Il faut viser 14–15 cm³</b> : le point −15 °C passe alors à ≈ 92–99 tr/s et la clim à ≈ 43–46 tr/s, dans toutes les plages publiées.</li>
<li><b>Courte liste</b> : Panasonic 7WD138Z (13,9 cm³), GMCC RDTN150D54TEZ3 / EDTN150D32EFZ (15 cm³, en stock en Europe), Highly PSD140RKQ-6B (14 cm³) et son
équivalent Danfoss VRN150WSQASE (15 cm³, échantillon à l'unité avec variateur). Tous bicylindres ou à faible vibration, sauf Highly/Danfoss (monocylindre).</li>
<li>Avec le meilleur rendement de catalogue (≈ 0,72), la machine rate de peu trois cibles sur quatre (−2 % en clim, −2 % à 8,3 °C, −1,5 % à −15 °C).
Il manque ≈ 0,03 de rendement. <b>C'est le premier point à négocier avec un fabricant</b> (version optimisée R290, comme ORNL/Highly).</li>
<li>Les deux concurrents visés (Midea PWHP, Gradient) sont <b>en R32</b> et ne publient pas leur compresseur. Les machines R290 du marché (Olimpia Unico, Innova 2.0)
restent sous 152 g en se limitant à ≈ 1,6–2,1 kW ; Innova utilise un <b>rotatif bicylindre LG R290</b>. Dans l'UE, les monoblocs ≤ 12 kW en GWP ≥ 150 sont
interdits au 1/1/2027 : le R290 devient obligatoire en Europe.</li>
</ol></div>

<h2 id="besoin">Le besoin (fiche de conception, étapes 1 et 2)</h2>
<div class="carte"><table>
<tr><th>Point</th><th class="n">Te / Tc °C</th><th class="n">Taux de compression</th><th class="n">P asp. / P ref. bar</th><th class="n">ṁ g/s</th>
<th class="n">Débit aspiré m³/h</th><th class="n">tr/s à 10,8 cm³</th><th class="n">tr/s à 15 cm³</th></tr>
{lignes_besoin}</table>
<p class="note">Vitesse = débit aspiré / (η_v = 0,90 × cylindrée). Points catalogue : ASHRAE Te 7,2 / Tc 54,4 °C, taux 3,2 ; nos points vont de 1,9 (clim) à 4,5 (−15 °C).
Exigences de la fiche : η_is ≥ 0,75, faible bruit (chambre), peu d'huile (la charge totale reste ≤ 152 g, le R290 se dissout dans l'huile), compact.</p></div>

<h2 id="methode">Comment on compare</h2>
<div class="carte">
<p>Les fabricants ne publient pas de rendement isentropique. Il est recalculé (CoolProp, propane) à partir du point catalogue :
débit ṁ = puissance froid / (h aspiration − h liquide), puis <b>η_is global = ṁ · (h₂s − h₁) / P électrique</b>. C'est exactement la définition de la fiche
(la puissance du compresseur y vaut ṁ·Δh_is/η_is, sans perte de moteur ou de variateur ajoutée). Vérification : la méthode redonne 0,67 pour le Highly PSD162XW, valeur publiée par ORNL.</p>
<p class="note">Limites : (1) les conditions diffèrent selon les fabricants (ASHRAE, SEER60 de GMCC, GB chinoise) et le variateur est inclus ou non ;
(2) un seul point par modèle, au taux 3,2 ou moins : rien ne dit le rendement à 1,9 et à 4,5, ni à 100–120 tr/s ;
(3) quand seule la puissance de chauffage est donnée, le froid est pris égal à chauffage − puissance électrique.</p></div>

<h2 id="tableau">Les candidats : rotatifs R290 à variateur, 7 à 21 cm³</h2>
<div class="carte"><table>
<tr><th>Fabricant / modèle</th><th>Type</th><th class="n">cm³</th><th class="n">tr/s max</th><th class="n">tr/s clim</th><th class="n">tr/s −15 °C</th>
<th class="n">η_is global</th><th>Point d'origine</th><th>Huile</th><th>Encombrement</th><th>Remarque</th><th>Source</th></tr>
{tab_cand}</table>
<p class="note">tr/s clim et −15 °C : vitesse nécessaire avec ce compresseur pour tenir 9 000 BTU/h (η_v = 0,90). En vert / rouge : sous / au-dessus de la vitesse maximale publiée.
« ? » : non publié. Les rendements GMCC, Landa, Rechi et Highly viennent du recalcul des sous-points par l'étude (voir sources) ; Panasonic et LG ont été recalculés pour ce rapport.</p></div>

<h2 id="graphe">Rendement et cylindrée</h2>
<div class="carte">
<p class="leg"><span><i style="background:var(--s1)"></i>catalogue, condition connue</span><span><i style="background:var(--s2)"></i>catalogue, condition à confirmer</span>
<span><i style="background:var(--s3)"></i>prototype mesuré</span></p>
{graphique()}
<p class="note">Survoler un point pour le détail. Les modèles à vitesse fixe et les alternatifs de réfrigération (Secop, Embraco, Tecumseh : 0,54–0,66) ne sont pas tracés.
La zone bleue indique les cylindrées qui tiennent le point −15 °C sous 120 tr/s.</p></div>

<h2 id="cop">Effet du rendement réel sur le COP de la machine</h2>
<div class="carte"><table>
<tr><th>Point</th><th class="n">Cible</th><th class="n">η 0,67</th><th class="n">η 0,70</th><th class="n">η 0,72</th><th class="n">η 0,74</th><th class="n">η 0,75</th><th class="n">η 0,80</th></tr>
{tab_sens}</table>
<p class="note">COP de l'unité (ventilateurs inclus) recalculé avec <code>fiche_pac_9000.cop_unite</code>, à Te, Tc et débits d'air inchangés. Vert : cible tenue.
0,67 = rotatif R290 de série courant ; 0,72 = meilleurs catalogues ; 0,80 = prototype ORNL/Highly. Le rendement à taux 1,9 et 4,5 sera probablement plus bas qu'au taux 3,2 :
une étude Midea sur rotatif R32 (taux 4,2) trouve 0,66–0,70 entre 80 et 160 Hz, puis une chute à 200 Hz.</p></div>

<h2 id="choix">Recommandation</h2>
<div class="carte cle"><ol>
<li><b>Changer l'hypothèse de cylindrée de la fiche : 14–15 cm³ au lieu de 10,8.</b> On reste sous 100 tr/s à −15 °C, là où les rotatifs gardent leur rendement,
et on garde de la marge pour le dégivrage et les jours plus froids. En contrepartie, la vitesse minimale (12–20 tr/s) limite la modulation par temps doux : à vérifier avec la charge partielle.</li>
<li><b>Panasonic 7WD138Z</b> (13,9 cm³, bicylindre, Ø104 × 267 mm) : meilleur rendement publié (0,74 au point ASHRAE). Demander la plage de vitesse, la carte complète et la charge d'huile.</li>
<li><b>GMCC RDTN150D54TEZ3 / EDTN150D32EFZ</b> (15 cm³, bicylindre, 12–120 tr/s) : fournisseur de Midea, disponible en Europe chez AREA Cooling qui annonce un logiciel de sélection ;
prix de l'ordre de 110–150 USD (EDTN210). Rendement publié plus modeste (0,65–0,67), mais variateur inclus.</li>
<li><b>Highly PSD140RKQ-6B / Danfoss VRN150WSQASE</b> : Highly a fait le prototype ORNL à 0,80 ; Danfoss vend le VRN150 (fabriqué par Highly) à l'unité avec son variateur CDS203,
la voie la plus simple pour un premier banc d'essai. Faire préciser la condition « New GB » et obtenir la carte Coolselector.</li>
<li><b>LG PAT134MA / PST102MA</b> : bon rendement (0,71–0,725) et référence du marché (Innova), mais 90 tr/s maximum. Utilisable seulement si LG étend la plage ou si l'on accepte une capacité réduite à −15 °C.</li>
<li><b>Panasonic 7SD110Z</b> (11,2 cm³) : la cylindrée de la fiche, mais 123 tr/s requis à −15 °C. À garder si Panasonic confirme ≥ 125 tr/s.</li>
</ol>
<p class="note">Une fois une fiche EN 12900 obtenue, la saisir dans <code>compresseurs/MODELE_carte.json</code> (ou <code>ajuster_carte.py</code> pour un tableau de points) : le simulateur l'utilisera à la place du modèle synthétique.</p></div>

<h2 id="ecartes">Écartés, et pourquoi</h2>
<div class="carte"><table>
<tr><th>Famille</th><th>Raison</th><th>Source</th></tr>
<tr><td>Alternatifs à vitesse variable Secop NLV / SLVE, Embraco FMF / VNE, Tecumseh VTC</td><td>Conçus pour la réfrigération : 4 500 tr/min max (75 tr/s), 10–14 kg, 430–550 cm³ d'huile ; SLVE limité à Te ≤ 10 °C ; η global 0,54–0,66.</td>
<td class="src"><a href="sources/europe_usa/secop_quickref_vitesse_variable_R290_06-2026.pdf">Secop</a> · <a href="sources/europe_usa/embraco_vitesse_variable_hawco.pdf">Embraco</a> · <a href="sources/europe_usa/tecumseh_catalogue_R290.pdf">Tecumseh</a></td></tr>
<tr><td>Aspen H76 (7,6 cm³, 24/48 V)</td><td>Trop petit (≈ 1,4 kW à Te −20 °C, 181 tr/s nécessaires), η 0,45–0,52 ; intéressant seulement en bi-compresseur ou en secours.</td>
<td class="src"><a href="sources/europe_usa/aspen_H-Series_7.6cc_perf_R290.pdf">fiche R290</a></td></tr>
<tr><td>Rotatifs 5–9 cm³ (sèche-linge, petites PAC : GMCC RDSK, Rechi 39Q, Landa G088, Highly PSD0088RK)</td><td>≈ 155 tr/s à −15 °C, au-delà des 120 tr/s ; η 0,61–0,68.</td>
<td class="src"><a href="sources/chine_taiwan/SOURCES.md">sources Chine/Taïwan</a></td></tr>
<tr><td>Scroll R290 (Copeland YHV, Samsung, Daikin)</td><td>Plus petit modèle ≈ 6 kW : trop gros.</td><td class="src"><a href="sources/europe_usa/SOURCES.md">sources Europe/USA</a></td></tr>
<tr><td>Compresseurs linéaires sans huile (Embraco Wisemotion, LG)</td><td>Réfrigérateurs en R600a / R134a, pas de version PAC R290.</td><td class="src"><a href="sources/europe_usa/SOURCES.md">sources Europe/USA</a></td></tr>
<tr><td>Mitsubishi Electric / Siam, Samsung rotatif, Fujitsu</td><td>Pas de données publiques R290. Mitsubishi a un rotatif R290 maison (split MSZ-RZ) : contact marketing@siamcompressor.com.</td>
<td class="src"><a href="sources/japon_coree/SOURCES.md">sources Japon/Corée</a></td></tr>
</table></div>

<h2 id="concurrents">Ce qu'utilisent les concurrents</h2>
<div class="carte"><table>
<tr><th>Produit</th><th>Fluide / charge</th><th>Compresseur</th><th>Source</th></tr>
<tr><td>Midea PWHP 9k (MAH09H1AGR)</td><td>R32 ; COP 4,0 / 2,42 / 2,0 à 47 / 17 / 5 °F</td><td>Variateur, garantie 12 ans ; modèle non publié (Midea possède GMCC)</td>
<td class="src"><a href="sources/concurrents_marche/midea_pwhp_product_specs_2024.pdf">fiche 2024</a></td></tr>
<tr><td>Gradient All-Weather 120V</td><td>R32 ; COP 4,00 / 2,60 / 2,35</td><td>« Variable speed », modèle non publié</td>
<td class="src"><a href="sources/concurrents_marche/gradient_allweather120v_spec_sheet.pdf">fiche</a></td></tr>
<tr><td>Innova 2.0 MINI 9 HP</td><td><b>R290, 140 g</b>, ≈ 1,7 kW (les modèles plus gros : R32)</td><td><b>LG rotatif bicylindre R290 inverter</b> (référence non publiée)</td>
<td class="src"><a href="sources/concurrents_marche/lg_case_study_innova_2.0_mini_R290_twin_rotary.html">LG</a> · <a href="sources/concurrents_marche/innova_2.0_brochure_en_2025.pdf">brochure</a></td></tr>
<tr><td>Olimpia Splendid Unico</td><td><b>R290, 145 g</b> pour 1,6–2,1 kW ; 2,6 kW en R32 (280 g)</td><td>« Twin rotary » à faibles vibrations, fabricant non indiqué</td>
<td class="src"><a href="sources/concurrents_marche/olimpia_unico_EN24_steelsoft.pdf">catalogue</a></td></tr>
<tr><td>Fenêtre R290 ORNL / Highly (12 000 BTU/h, 2018)</td><td>R290 &lt; 260 g (150 g visé en microcanaux), EER 14,0</td><td>Highly PSD162XW (16,2 cm³, 0,67) puis prototype ≈ 0,80</td>
<td class="src"><a href="sources/japon_coree/ornl_window_AC_propane_limited_charge_Pub119670.pdf">rapport ORNL</a></td></tr>
<tr><td>Programme NYCHA / Clean Heat for All</td><td>Moyenne Midea + Gradient : COP 3,92 / 2,44 / 2,03 ; 47–51 dB(A) max mesurés</td><td>—</td>
<td class="src"><a href="sources/concurrents_marche/be_exchange_window_hp_expo_2026-06.pdf">BE-Exchange 2026</a></td></tr>
</table>
<p class="note">Enseignements : les monoblocs silencieux (Innova, Olimpia, Ephoca) prennent tous un rotatif bicylindre ; à 2,6 kW, aucun produit R290 du marché ne reste sous 152 g.
Midea ne publie son rotatif bi-étagé à injection de vapeur que pour ses PAC gainables.</p></div>

<h2 id="regle">Réglementation</h2>
<div class="carte"><table>
<tr><th>Texte</th><th>Ce qu'il impose</th><th>Source</th></tr>
<tr><td>UE 2024/573 (F-gas), annexe IV point 8</td><td>Monoblocs et autonomes ≤ 12 kW : GWP ≥ 150 interdit au 1/1/2027, tout gaz fluoré au 1/1/2032. Le R32 sort du marché européen des PAC de fenêtre.</td>
<td class="src"><a href="sources/concurrents_marche/eurlex_reglement_UE_2024_573_fgas.pdf">EUR-Lex</a></td></tr>
<tr><td>IEC 60335-2-40 éd. 7</td><td>R290 : 152 g sans condition (4 × LFL) ; jusqu'à 988 g avec surface de pièce minimale et mesures de sécurité ; 304 g pour un appareil non fixe.</td>
<td class="src"><a href="sources/concurrents_marche/eia_us_enabling_ultralow_gwp_safety_standards_2026.pdf">EIA 2026</a> · <a href="sources/concurrents_marche/iec_60335-2-40_ed7_preview_vde.pdf">extrait VDE</a></td></tr>
<tr><td>États-Unis : EPA SNAP (2015), UL 60335-2-40 éd. 4</td><td>Climatiseur de fenêtre 9 000 BTU/h : 240 g max (SNAP) ; UL 114 g. La révision SNAP 27 n'est pas finalisée (avril 2026).</td>
<td class="src"><a href="sources/concurrents_marche/federal_register_2015-07895_snap_hydrocarbons_room_ac.html">Federal Register</a> · <a href="sources/concurrents_marche/epa_snap_rule27_snprm_factsheet_2026-04.pdf">SNAP 27</a></td></tr>
</table>
<p class="note">Pour le compresseur, cela pèse sur l'huile : ≈ 40 g de R290 dissous dans les 270 ml du PSD162XW (ORNL). Un 15 cm³ avec 300–480 ml d'huile prend une part notable des 152 g.</p></div>

<h2 id="technique">Points techniques à retenir</h2>
<div class="carte"><ul>
<li><b>Rendement hors du point catalogue.</b> Nos points sont à taux 1,9 et 4,5. À bas taux, les pertes de clapet pèsent plus ; à haut taux et haute vitesse, fuites et pertes moteur.
Seule une carte EN 12900 à plusieurs vitesses (30 / 60 / 90 / 120 tr/s) permet de conclure.</li>
<li><b>Haute vitesse plutôt que grosse cylindrée</b> : piste GMCC/Meizhi (Purdue 2024, résumé seulement), avec un double orifice de refoulement au-delà de 90 Hz. C'est l'inverse de notre recommandation de cylindrée : à arbitrer avec les cartes.</li>
<li><b>Injection de vapeur (EVI)</b> sur rotatif : +5 à +18 % de capacité à basse température, COP +0 à +3,5 %. Aucune donnée publique en R290 à −15 °C. Option à demander si le point −15 °C coince.</li>
<li><b>Démarrage à froid en R290</b> : aspiration sous la pression atmosphérique possible, et fluide qui migre dans le carter. GMCC impose ≥ 26 tr/s sous 0 °C extérieur et des paliers de démarrage ; prévoir le chauffage du carter.</li>
<li><b>Bruit</b> : Danfoss VRN150 Lw 74 dB(A) ; GMCC EDTN210 67 + 4 dB(A). Un capotage acoustique est à prévoir dans tous les cas.</li>
</ul></div>

<h2 id="demandes">Demandes à envoyer</h2>
<div class="carte"><table>
<tr><th>À qui</th><th>Quoi</th></tr>
<tr><td>Panasonic Industry Europe</td><td>7WD138Z et 7SD110Z : plage de vitesse, carte EN 12900 / AHRI 540, huile, bruit, prix d'échantillon.</td></tr>
<tr><td>GMCC via AREA Cooling (Espagne)</td><td>RDTN150D54TEZ3, EDTN150D32EFZ : polynômes du logiciel AREA, enveloppe, vitesse max autorisée, huile, échantillon + variateur de référence.</td></tr>
<tr><td>Danfoss (Coolselector) / Highly</td><td>VRN150WSQASE (code échantillon 126X2025) : données Coolselector ; PSD140RKQ-6B : définition de « New GB » ; possibilité d'une version optimisée R290 (cf. ORNL).</td></tr>
<tr><td>LG</td><td>PAT134MA / PST102MA : vitesse au-delà de 90 tr/s, cartes R290.</td></tr>
<tr><td>Siam Compressor (Mitsubishi Electric)</td><td>Catalogue des rotatifs R290 de 10 à 15 cm³.</td></tr>
</table>
<p class="note">Questions communes : carte à 30 / 60 / 90 / 120 tr/s, taux 1,9 à 4,5 ; volume d'huile et solubilité du R290 ; vitesse minimale ; bruit ; démarrage à froid ; injection de vapeur.</p></div>

<h2 id="sources">Toutes les sources</h2>
<p class="note">Toutes les sources ont été consultées le 11/11/2026. Les copies locales sont dans <code>compresseurs/sources/</code> (non suivies par git pour les PDF : voir <code>.gitignore</code>).
« non sauvegardé » ou « — » : page bloquée (anti-robot, 403), seule l'URL est gardée.</p>
{''.join(sources)}
</main></body></html>
"""


def main():
    out = ICI / "etude_compresseurs.html"
    out.write_text(page(), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
