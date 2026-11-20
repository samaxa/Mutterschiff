# -*- coding: utf-8 -*-
"""
Kaverne Schritt 06 - Zusammensetzung des Ausspeichergases (Min- und Max-Fall)
============================================================================
Was nimmt das CO₂ in der Kaverne auf, und mit welcher Zusammensetzung startet der
Ausspeicherpfad? Grundlage ist die H₂-Studie Q-089 (UGS für DGMK 2024, Uniper-
Musterkaverne: frühere Erdgaskaverne, Diesel-Blanket, ölgeschmierter Kolbenverdichter),
übertragen auf CO₂, ergänzt um die Begleitstoffe der Anlieferung. Statt eines einzigen
Worst Case eine Bandbreite (Besprechung K. Vosbeck 15.10.2026). Werte und Fundstellen:
ausspeichergas.py (Kopf der Datei) und die Mappe CO2_Ausspeichergas_Zusammensetzung.xlsx
(dieser Ordner, ein Blatt je Begleitstoff).

Stand 18.11.2026 (gleiche Rechnung wie die Mappe, Blatt 12):
  - Auslegungsrate 50.000 Nm³/h (Entscheidung 16.11.2026), Zustände aus dem Zyklus
    S2 | 50.000 Nm³/h | Stillstand 21,67 d
  - Resterdgas als Erdgas H nach OGE 2022 (Q-140): Min Russland, Max Nordsee; Methan,
    C₂ bis C6+, N₂ und CO₂ getrennt statt reinem Methan
  - aus der Anlieferung (nur Gemisch, Max-Fall, Porthos Q-096): H₂S 5 ppm, COS 15 ppm,
    O₂ 40 ppm, NOx 5 ppm
  - neuer Fall gem_max_ohne_stillstand: Wasser aus dem wärmsten Zustand am Ende des
    Einspeicherns (a_w = 1), wenn ohne Stillstand ausgespeichert wird
  - Verdichteröl nur mit Verdichter (S2): Min 0,135, Max 0,260 kg je 10⁵ Nm³ (Q-089 Tab. 20)
  - Aromaten im Diesel als Information (Q-141, Q-142), CO₂ in der Restsole als Information

Zustände aus den vorigen Schritten:
  Kaverne voll / leer / Ende Einspeichern   ../Reines_CO2/kavernenzyklus.json bzw. ../Begleitstoffe_CO2/...
  Bohrlochkopf                              .../bohrlochkopf.json -> fällt am Kopf freies Wasser aus?

Randbedingung Rückgabe (OGE 16.09.2026): H₂O ≤ 30 ppm, H₂S < 0,5 ppm -> was die
Aufbereitung entfernen muss.

Ausgabe: Konsole, abb_K06_wasser.png, abb_K06_eintraege.png,
zusammensetzung_nach_kaverne.json (-> ausspeichergas.py -> Ausspeicherpfad / HYSYS)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import ausspeichergas as ag      # noqa: E402
import kaverne_bausteine as kb   # noqa: E402

KAV = kb.TIEF
RATE_TXT, RATE = "50.000 Nm³/h", 50000.0        # Auslegungsrate (Entscheidung 16.11.2026)
ST = "Stillstand 21,67 d (Q-028)"
ZYKLUS = f"S2|{RATE_TXT}|{ST}"                    # erste Ausspeicherung ist für S1 und S2 gleich
V_REF_Q089 = 500000.0                             # m³, Musterkaverne Q-089 (Tab. 16)

# Erdgas H, Jahresmittel 2022 in mol-% (Q-140, OGE-Orientierungswerte; C4/C5 als Summe der Isomere)
ERDGAS_H = {
    "Nordsee":  dict(Methane=88.05, Nitrogen=0.94, CO2=2.08, Ethane=7.06, Propane=1.48,
                     **{"n-Butane": 0.34, "n-Pentane": 0.05, "n-Hexane": 0.01}),
    "Russland": dict(Methane=96.01, Nitrogen=0.33, CO2=0.44, Ethane=3.00, Propane=0.12,
                     **{"n-Butane": 0.07, "n-Pentane": 0.01, "n-Hexane": 0.01}),
}

# Bandbreite je Eintrag (Spalten Min/Max der Blätter 04 bis 11)
BANDBREITE = {
    "min": dict(a_w_voll=ag.A_W_SOLE, a_w_leer=1.0,            # Q-089 Abschn. 6.5, Q-137 Abschn. 3
                finger_m3=1000.0, erdgas="Russland",           # Q-089 Abschn. 6.3, Q-140
                blanket_m3=0.084, aromaten=0.07,               # Q-089 Tab. 10 Fall 4a; Q-142
                oel_kg=0.135,                                  # Q-089 Tab. 20, nur mit Verdichter (S2)
                h2s_mikro_ppm=0.0, ch4_mikro_ppm=0.0,          # Mikroben gehemmt
                h2s_feed_ppm=0.0, cos_feed_ppm=0.0, o2_feed_ppm=0.0, nox_feed_ppm=0.0),
    "max": dict(a_w_voll=ag.A_W_AUSLEGUNG, a_w_leer=ag.A_W_AUSLEGUNG,
                finger_m3=2000.0, erdgas="Nordsee",
                blanket_m3=1.76, aromaten=0.38,                # Q-089 Tab. 10 Fall 4c; 30 % Mono + 8 % PAK (Q-141)
                oel_kg=0.260,
                h2s_mikro_ppm=10.0, ch4_mikro_ppm=50.0,        # Q-089 Abschn. 6.4.2/6.4.3, Tab. 20
                h2s_feed_ppm=5.0, cos_feed_ppm=15.0,           # Porthos Q-096: H₂S 5, Schwefel gesamt 20 ppm
                o2_feed_ppm=40.0, nox_feed_ppm=5.0),           # Porthos Q-096
}
RHO_DIESEL, M_DIESEL = 827.7, 230.0     # kg/m³ (Q-089 Tab. 12, 50 °C / 210 bar), g/mol (Tab. 11: 121-315, Mitte)
DIESEL_LEICHT = 0.004                   # Massenanteil unter 200 °C (C6 bis etwa C10), Q-089 Siedeanalyse
M_OEL = 300.0                           # g/mol (Q-089 Tab. 5: 270-320)
RESTSOLE_ANTEIL = 0.01                  # 1 % von V (Q-003 Kap. 9.3.2.4: ≤ 1 %); nur Information
AUSSALZFAKTOR = 0.345                   # Henry-Faktor Wasser/Sole 100/290 MPa (Q-136 Anhang A)
OGE = dict(H2O_ppm=30.0, H2S_ppm=0.5, p_min=91.0)   # Rückgabe ins Netz (OGE-Austausch 16.09.2026)

# Fälle wie die Spalten D bis I der Mappe (02_Kaverne Abschn. 6)
FAELLE = {
    "rein_min": dict(stoff="rein", band="min", verdichter=False, stillstand=True, zyklus=1,
                     name="reines CO₂, Min-Fall (S1, ohne Mikroben)"),
    "rein_max": dict(stoff="rein", band="max", verdichter=True, stillstand=True, zyklus=1,
                     name="reines CO₂, Max-Fall (S2)"),
    "gem_min": dict(stoff="gem", band="min", verdichter=False, stillstand=True, zyklus=1,
                    name="Gemisch, Min-Fall (S1, ohne Mikroben)"),
    "gem_max": dict(stoff="gem", band="max", verdichter=True, stillstand=True, zyklus=1,
                    name="Gemisch, Max-Fall (S2) - Auslegung"),
    "gem_max_ohne_stillstand": dict(stoff="gem", band="max", verdichter=True, stillstand=False, zyklus=1,
                                    name="Gemisch, Max-Fall, ohne Stillstand"),
    "gem_max_ab_2_zyklus": dict(stoff="gem", band="max", verdichter=True, stillstand=True, zyklus=2,
                                name="Gemisch, Max-Fall, ab 2. Zyklus (ohne Resterdgas)"),
}
for _f in ("rein_min", "rein_max", "gem_min"):       # zusätzlich, nicht in der Mappe
    FAELLE[f"{_f}_ab_2_zyklus"] = dict(FAELLE[_f], zyklus=2, name=FAELLE[_f]["name"] + ", ab 2. Zyklus")

ORDNER_STOFF = {"rein": kb.ORDNER_REIN, "gem": kb.ORDNER_GEM}
BASIS = {"rein": {"CO2": 1.0}, "gem": {name: x / 100 for _, name, x, _ in kb.gw.ZUSAMMENSETZUNG}}
M_MISCH = {"rein": PropsSI("M", "CO2") * 1000, "gem": kb.gw.gemisch().molar_mass() * 1000}   # g/mol
NICHT_COOLPROP = ("NOx", "Diesel (C10-C20)", "Verdichteroel")
REIHENFOLGE = ["CO2", "Nitrogen", "Argon", "Methane", "Ethane", "Propane", "n-Butane", "n-Pentane", "n-Hexane",
               "Hydrogen", "CarbonMonoxide", "HydrogenSulfide", "CarbonylSulfide", "Oxygen", *NICHT_COOLPROP]


def zustaende(stoff):
    """Kaverne voll/leer (erste Ausspeicherung), Ende Einspeichern S2 und Kopfzustände beim Ausspeichern."""
    zyk = kb.lade_json(ORDNER_STOFF[stoff], "kavernenzyklus.json", "03 im Stoffordner")
    kopf = kb.lade_json(ORDNER_STOFF[stoff], "bohrlochkopf.json", "04 im Stoffordner")
    vl = zyk["zyklen"][ZYKLUS]["verlauf"]
    aus = [x for x in vl if x["art"] == "aus"]
    ein = [x for x in vl if x["art"] == "ein"]
    koepfe = [z["kopf"] for z in kopf["ausspeisen"][RATE_TXT]["punkte"] if z["kopf"]]
    # Ende Einspeichern aus demselben Zyklus wie in der Mappe (02_Kaverne Z. 48/49); der Zyklus
    # "kontinuierlich (0 d)" liegt nur 0,1 bis 0,3 bar darunter, der Wassergehalt ändert sich < 0,1 %.
    return ((aus[0]["p_mitte"], aus[0]["T"]), (aus[-1]["p_mitte"], aus[-1]["T"]),
            (ein[-1]["p_mitte"], ein[-1]["T"]), koepfe)


def normiert(d):
    s = sum(d.values())
    return {k: v / s for k, v in d.items()}


def sortiert(d):
    return {k: d[k] for k in REIHENFOLGE if k in d}


stoffe = {}
for stoff in ("rein", "gem"):
    med = kb.medium(stoff)
    voll, leer, ende_ein, koepfe = zustaende(stoff)
    TGV = kb.inventar(med, KAV, KAV.p_max)                       # t
    stoffe[stoff] = dict(med=med, voll=voll, leer=leer, ende_ein=ende_ein, koepfe=koepfe, TGV=TGV,
                         n_tot=TGV * 1e6 / M_MISCH[stoff],    # mol
                         rho_ch4=PropsSI("Dmolar", "P", voll[0] * 1e5, "T", voll[1] + 273.15, "Methane"))

faelle, details = {}, {}
for fall, C in FAELLE.items():
    S, B = stoffe[C["stoff"]], BANDBREITE[C["band"]]
    gem = C["stoff"] == "gem"
    n_tot, voll, leer, ende_ein = S["n_tot"], S["voll"], S["leer"], S["ende_ein"]

    # Wasser (Blatt 04): Austrittsstrom gesättigt, der wasserreichere Zustand zählt
    y_voll = ag.wasser_im_co2(*voll, a_w=B["a_w_voll"])
    y_leer = ag.wasser_im_co2(*leer, a_w=B["a_w_leer"])
    y_ein = ag.wasser_im_co2(*ende_ein, a_w=ag.A_W_AUSLEGUNG)
    y_h2o = max(y_voll, y_leer) if C["stillstand"] else y_ein

    # Grundgas (02_Kaverne Abschn. 4)
    zus = {k: x * n_tot for k, x in BASIS[C["stoff"]].items()}

    def dazu(k, n):
        zus[k] = zus.get(k, 0.0) + n

    # Resterdgas im Finger (Blatt 05): Molzahl wie reines Methan bei Kavernenzustand voll, aufgeteilt
    # nach Erdgas H; homogen vermischt, nur im 1. Zyklus (Q-089 Tab. 16)
    finger = B["finger_m3"] * KAV.volumen / V_REF_Q089                     # m³
    n_rest = finger * S["rho_ch4"] if C["zyklus"] == 1 else 0.0
    rest = {k: n_rest * x for k, x in normiert(ERDGAS_H[B["erdgas"]]).items()}
    for k, n in rest.items():
        dazu(k, n)

    # Mikroorganismen (Blätter 08, 09): H₂S in beiden Grundgasen, CH₄ nur im Gemisch (braucht H₂)
    n_h2s_mik = B["h2s_mikro_ppm"] * 1e-6 * n_tot
    n_ch4_mik = B["ch4_mikro_ppm"] * 1e-6 * n_tot if gem else 0.0
    dazu("HydrogenSulfide", n_h2s_mik)
    dazu("Methane", n_ch4_mik)
    if gem:
        dazu("Hydrogen", -4 * n_ch4_mik)                                     # 4 H₂ + CO₂ -> CH₄ + 2 H₂O

    # Anlieferung (Blätter 08, 11): nur Gemisch
    feed = {k: (B[p] if gem else 0.0) * 1e-6 * n_tot for k, p in
            (("HydrogenSulfide", "h2s_feed_ppm"), ("CarbonylSulfide", "cos_feed_ppm"),
             ("Oxygen", "o2_feed_ppm"), ("NOx", "nox_feed_ppm"))}
    for k, n in feed.items():
        dazu(k, n)

    # Diesel-Blanket (Blatt 06) und Verdichteröl (Blatt 07, nur mit Verdichter)
    n_diesel = B["blanket_m3"] * RHO_DIESEL * 1000 / M_DIESEL
    y_oel = (B["oel_kg"] if C["verdichter"] else 0.0) * 1e3 / 1e5 / M_OEL / ag.N_NORM   # g/Nm³ -> mol/mol
    dazu("Diesel (C10-C20)", n_diesel)
    dazu("Verdichteroel", y_oel * n_tot)

    zus = sortiert(zus)
    n_tr = sum(zus.values())
    trocken = {k: n / n_tr for k, n in zus.items()}
    feucht = {k: x * (1 - y_h2o) for k, x in trocken.items()}
    feucht["Water"] = y_h2o
    trocken_cp = normiert({k: n for k, n in zus.items() if k not in NICHT_COOLPROP})
    faelle[fall] = dict(feucht=feucht, trocken=trocken, trocken_coolprop=trocken_cp)

    # Einträge bezogen auf den Inhalt (Blatt 12 Abschn. 5) und Prüfungen
    ppm = lambda n: 1e6 * n / n_tot                                                   # noqa: E731
    c2plus = sum(v for k, v in rest.items() if k in ("Ethane", "Propane", "n-Butane", "n-Pentane", "n-Hexane"))
    diesel_ppm = ppm(n_diesel)
    kopf_pruef = []
    for k in S["koepfe"]:
        y_sat = ag.wasser_im_co2(k["p"], k["T"])
        frei = y_h2o > y_sat
        kopf_pruef.append(dict(p=k["p"], T=k["T"], y_sat=y_sat, freies_wasser=frei,
                               hydrat=frei and k["T"] < ag.T_hydrat(k["p"]), spycher_gueltig=k["T"] >= 12.0))
    n_co2_sole = RESTSOLE_ANTEIL * KAV.volumen * 1000 * ag.co2_molalitaet(*voll)     # mol, über reinem Wasser
    h2s_ges = 1e6 * feucht["HydrogenSulfide"]
    details[fall] = dict(
        stoff=S["med"].name, fall=C["name"], annahmen=dict(C, **B), voll=voll, leer=leer, ende_einspeichern=ende_ein,
        TGV=S["TGV"], n_tot=n_tot, y_voll=y_voll, y_leer=y_leer, y_ende_einspeichern=y_ein, y_h2o=y_h2o,
        g_Nm3=ag.g_pro_Nm3(y_h2o),
        ppm=dict(Wasser=1e6 * y_h2o, Resterdgas_CH4=ppm(rest.get("Methane", 0.0)), Resterdgas_C2plus=ppm(c2plus),
                 Resterdgas_N2_CO2=ppm(rest.get("Nitrogen", 0.0) + rest.get("CO2", 0.0)),
                 CH4_mikrobiell=ppm(n_ch4_mik), H2S_mikrobiell=ppm(n_h2s_mik),
                 H2S_Anlieferung=ppm(feed["HydrogenSulfide"]), COS_Anlieferung=ppm(feed["CarbonylSulfide"]),
                 O2_Anlieferung=ppm(feed["Oxygen"]), NOx_Anlieferung=ppm(feed["NOx"]),
                 Diesel=diesel_ppm, Verdichteroel=1e6 * y_oel),
        aromaten_ppm=dict(Diesel_gesamt_Aramis=diesel_ppm * B["aromaten"],
                          Diesel_C6_C10_Porthos=diesel_ppm * DIESEL_LEICHT,
                          Resterdgas_C6plus_obere_Schranke=ppm(rest.get("n-Hexane", 0.0))),
        nicht_kondensierbar_mol_prozent=100 * sum(trocken.get(k, 0.0) for k in
                                                  ("Nitrogen", "Argon", "Methane", "Hydrogen", "CarbonMonoxide",
                                                   "Oxygen")),
        co2_restsole=dict(anteil_sole=RESTSOLE_ANTEIL, t_reines_wasser=n_co2_sole * 44.0098e-6,
                          t_mit_aussalzfaktor=n_co2_sole * 44.0098e-6 * AUSSALZFAKTOR,
                          anteil_am_inhalt=n_co2_sole * 44.0098e-6 / S["TGV"]),
        kopf=kopf_pruef,
        rueckgabe=dict(H2O_entfernen_ppm=1e6 * y_h2o - OGE["H2O_ppm"],
                       H2O_entfernen_kg_h=(y_h2o - OGE["H2O_ppm"] * 1e-6) / (1 - y_h2o) * RATE * ag.N_NORM
                       * ag.M_H2O / 1000,
                       H2S_entfernen_ppm=max(h2s_ges - OGE["H2S_ppm"], 0.0),
                       Schwefel_gesamt_ppm=h2s_ges + 1e6 * feucht["CarbonylSulfide"]))

# ---- Konsole -------------------------------------------------------------------------------------
for fall, d in details.items():
    if fall.endswith("_ab_2_zyklus") and fall != "gem_max_ab_2_zyklus":
        continue
    print(f"\n==== {fall}: {d['fall']} ====")
    print(f"  Wasser: voll {d['voll'][0]:.1f} bar / {d['voll'][1]:.1f} °C {1e6*d['y_voll']:.0f} ppm, leer "
          f"{d['leer'][0]:.1f} bar / {d['leer'][1]:.1f} °C {1e6*d['y_leer']:.0f} ppm, Ende Einspeichern "
          f"{1e6*d['y_ende_einspeichern']:.0f} ppm -> {1e6*d['y_h2o']:.0f} ppm = {d['g_Nm3']:.2f} g/Nm³")
    for k, v in d["ppm"].items():
        if v:
            print(f"  {k:<18} {v:10.3f} ppm")
    fw = [k for k in d["kopf"] if k["freies_wasser"]]
    r = d["rueckgabe"]
    print(f"  Kopf: freies Wasser in {len(fw)} von {len(d['kopf'])} Kopfzuständen; Rückgabe (OGE): "
          f"{r['H2O_entfernen_ppm']:.0f} ppm Wasser ({r['H2O_entfernen_kg_h']:.0f} kg/h bei {RATE_TXT}) und "
          f"{r['H2S_entfernen_ppm']:.1f} ppm H₂S entfernen; Schwefel gesamt {r['Schwefel_gesamt_ppm']:.1f} ppm")

print("\nTrockenes Gas (mol-%) für HYSYS - wie Mappe Blatt 12, Abschnitt 7:")
HAUPT = ("rein_min", "rein_max", "gem_min", "gem_max", "gem_max_ohne_stillstand", "gem_max_ab_2_zyklus")
print(f"  {'':<16}" + "".join(f"{f:>14}" for f in ("rein min", "rein max", "gem min", "gem max", "ohne Still.",
                                                    "ab 2. Zykl.")))
for k in REIHENFOLGE:
    if k in NICHT_COOLPROP:
        continue
    print(f"  {k:<16}" + "".join(f"{100 * faelle[f]['trocken_coolprop'].get(k, 0.0):14.6f}" for f in HAUPT))

# ---- Abbildung 1: Wassersättigung --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6.2))
pp = np.linspace(15, 230, 200)
for T, c in ((12, "#9DC3E6"), (20, "#5B9BD5"), (31, "#2E75B6"), (40, "#1F4E79"), (52, "#0B2A4A"), (59, "#000814")):
    ax.plot(pp, [1e6 * ag.wasser_im_co2(p, T) for p in pp], color=c, lw=1.6, label=f"{T} °C, reines Wasser")
FARBE = {"rein": "#00304F", "gem": "#CA220E"}
for stoff in ("rein", "gem"):
    d = details[f"{stoff}_max"]
    ax.plot(d["voll"][0], 1e6 * d["y_voll"], "o", color=FARBE[stoff], ms=8, label=f"{d['stoff']}: voll (gesättigt)")
    ax.plot(d["leer"][0], 1e6 * d["y_leer"], "s", color=FARBE[stoff], ms=8, label=f"{d['stoff']}: leer (gesättigt)")
    ax.plot(d["ende_einspeichern"][0], 1e6 * d["y_ende_einspeichern"], "^", color=FARBE[stoff], ms=8,
            label=f"{d['stoff']}: Ende Einspeichern (ohne Stillstand)")
    dmin = details[f"{stoff}_min"]
    ax.plot(dmin["voll"][0], 1e6 * dmin["y_voll"], "o", mfc="none", color=FARBE[stoff], ms=8,
            label=f"{d['stoff']}: voll, Min-Fall (Sole, a_w = 0,75)")
    ax.plot([k["p"] for k in d["kopf"]], [1e6 * k["y_sat"] for k in d["kopf"]], "x", color=FARBE[stoff], ms=5,
            label=f"{d['stoff']}: Sättigung am Kopf ({RATE_TXT})")
ax.axhline(OGE["H2O_ppm"], color="#7030A0", ls="--", lw=1)
ax.text(20, OGE["H2O_ppm"] + 80, "Rückgabe OGE: 30 ppm", color="#7030A0", fontsize=8)
ax.set(xlabel="Druck [bar]", ylabel="Wasser in der CO₂-Phase [mol-ppm]", ylim=(0, 10000),
       title="Wassersättigung von CO₂ (Spycher et al. 2003): Kaverne voll/leer/Ende Einspeichern und Kopf")
ax.grid(alpha=0.3)
ax.legend(fontsize=7, ncol=2)
fig.tight_layout()
fig.savefig(ORDNER / "abb_K06_wasser.png", dpi=160)
plt.close(fig)

# ---- Abbildung 2: Einträge je Quelle, alle Fälle der Mappe ---------------------------------------
fig, ax = plt.subplots(figsize=(12.5, 5.4))
quellen = list(details["gem_max"]["ppm"].keys())
x = np.arange(len(quellen))
STIL = (("rein_min", "#9DC3E6", "rein Min"), ("rein_max", "#00304F", "rein Max"),
        ("gem_min", "#F4B183", "Gemisch Min"), ("gem_max", "#CA220E", "Gemisch Max (Auslegung)"),
        ("gem_max_ohne_stillstand", "#7F0F05", "Gemisch Max ohne Stillstand"),
        ("gem_max_ab_2_zyklus", "#A5A5A5", "Gemisch Max ab 2. Zyklus"))
bw = 0.8 / len(STIL)
for j, (fall, c, lab) in enumerate(STIL):
    ax.bar(x + (j - (len(STIL) - 1) / 2) * bw, [max(details[fall]["ppm"][q], 1e-3) for q in quellen], bw,
           color=c, label=lab)
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels([q.replace("_", "\n") for q in quellen], fontsize=8)
ax.set(ylabel="Eintrag [mol-ppm, bezogen auf den Inhalt]", ylim=(0.01, 2e4),
       title=f"Was das CO₂ in der Kaverne aufnimmt - Bandbreite (Q-089, Q-096, Q-140), {RATE_TXT}")
ax.grid(alpha=0.3, axis="y")
ax.legend(fontsize=8, ncol=3)
fig.tight_layout()
fig.savefig(ORDNER / "abb_K06_eintraege.png", dpi=160)
plt.close(fig)

kb.speichere_json(ORDNER, "zusammensetzung_nach_kaverne.json", dict(
    stand="18.11.2026", auslegungsfall="gem_max", rate=RATE_TXT, zyklus=ZYKLUS, oge_rueckgabe=OGE,
    annahmen=dict(faelle=FAELLE, bandbreite=BANDBREITE, erdgas_h_mol_prozent=ERDGAS_H, V_ref_q089=V_REF_Q089,
                  rho_diesel=RHO_DIESEL, M_diesel=M_DIESEL, diesel_leicht=DIESEL_LEICHT, M_oel=M_OEL,
                  restsole_anteil=RESTSOLE_ANTEIL, aussalzfaktor=AUSSALZFAKTOR,
                  hinweis="Molanteile = Mappe CO2_Ausspeichergas_Zusammensetzung.xlsx, Blatt 12"),
    faelle=faelle, details=details))
