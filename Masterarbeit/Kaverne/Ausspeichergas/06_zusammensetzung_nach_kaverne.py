# -*- coding: utf-8 -*-
"""
Kaverne Schritt 06 - Zusammensetzung des Ausspeichergases (Min- und Max-Fall)
============================================================================
Was nimmt das CO₂ in der Kaverne auf, und mit welcher Zusammensetzung startet der
Ausspeicherpfad? Grundlage ist die H₂-Studie Q-089 (UGS für DGMK 2024, Uniper-
Musterkaverne: frühere Erdgaskaverne, Diesel-Blanket, ölgeschmierter Kolbenverdichter),
übertragen auf CO₂. Statt eines einzigen Worst Case jetzt eine Bandbreite (Besprechung
K. Vosbeck 15.10.2026): Min- und Max-Fall nach den Bandbreiten in Q-089, jeweils für
reines CO₂ und das Worst-Case-Gemisch der Anlieferung. Werte und Fundstellen:
ausspeichergas.py (Kopf der Datei).

Zustände aus den vorigen Schritten (Auslegungsrate 100.000 Nm³/h, Einspeisung S2,
Stillstand 21,67 d; die erste Ausspeicherung ist für S1 und S2 gleich):
  Kaverne voll / leer   ../Reines_CO2/kavernenzyklus.json bzw. ../Begleitstoffe_CO2/...
  Bohrlochkopf          .../bohrlochkopf.json -> fällt am Kopf freies Wasser aus?

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
RATE, ST = "100.000 Nm³/h", "Stillstand 21,67 d (Q-028)"
V_REF_Q089 = 500000.0            # m³, Musterkaverne Q-089 (Tab. 16)
FAELLE = {
    "min": dict(name="Min-Fall (untere Werte Q-089)", a_w_voll=ag.A_W_SOLE, a_w_leer=1.0,
                finger_m3=1000.0, blanket_m3=0.084, oel_kg=0.135),
    "max": dict(name="Max-Fall (obere Werte Q-089, gesättigt)", a_w_voll=ag.A_W_AUSLEGUNG, a_w_leer=ag.A_W_AUSLEGUNG,
                finger_m3=2000.0, blanket_m3=1.76, oel_kg=0.260),
}
RHO_DIESEL, M_DIESEL = 827.7, 230.0     # kg/m³ (Q-089 Tab. 12, 50 °C / 210 bar), g/mol (Tab. 11: 121-315, Mitte)
M_OEL = 300.0                           # g/mol (Q-089 Tab. 5: 270-320)
H2S_PPM, CH4_MIKRO_PPM = 10.0, 50.0     # Q-089 Abschn. 6.4.2 / 6.4.3, Tab. 20 (S. 40)
RESTSOLE_ANTEIL = 0.01                  # eigene Annahme: 1 % von V Restsole (nur Größenordnung; Q-003 Kap. 9.3.2.4: ≤ 1 %)
OGE = dict(H2O_ppm=30.0, H2S_ppm=0.5, p_min=91.0)   # Rückgabe ins Netz (OGE-Austausch 16.09.2026)

ORDNER_STOFF = {"rein": kb.ORDNER_REIN, "gem": kb.ORDNER_GEM}
BASIS = {"rein": {"CO2": 1.0}, "gem": {name: x / 100 for _, name, x, _ in kb.gw.ZUSAMMENSETZUNG}}
M_MISCH = {"rein": PropsSI("M", "CO2") * 1000, "gem": kb.gw.gemisch().molar_mass() * 1000}   # g/mol


def zustaende(stoff):
    """Kaverne voll/leer (erste Ausspeicherung) und Kopfzustände beim Ausspeichern."""
    zyk = kb.lade_json(ORDNER_STOFF[stoff], "kavernenzyklus.json", "03 im Stoffordner")
    kopf = kb.lade_json(ORDNER_STOFF[stoff], "bohrlochkopf.json", "04 im Stoffordner")
    vl = [x for x in zyk["zyklen"][f"S2|{RATE}|{ST}"]["verlauf"] if x["art"] == "aus"]
    koepfe = [z["kopf"] for z in kopf["ausspeisen"][RATE]["punkte"] if z["kopf"]]
    return (vl[0]["p_mitte"], vl[0]["T"]), (vl[-1]["p_mitte"], vl[-1]["T"]), koepfe


faelle, details = {}, {}
for stoff in ("rein", "gem"):
    med = kb.medium(stoff)
    voll, leer, koepfe = zustaende(stoff)
    TGV = kb.inventar(med, KAV, KAV.p_max)                       # t
    n_tot = TGV * 1e6 / M_MISCH[stoff]                           # mol
    for fk, F in FAELLE.items():
        # Wasser: Austrittsstrom gesättigt, der wasserreichere Zustand zählt
        y_voll = ag.wasser_im_co2(*voll, a_w=F["a_w_voll"])
        y_leer = ag.wasser_im_co2(*leer, a_w=F["a_w_leer"])
        y_h2o = max(y_voll, y_leer)
        # Resterdgas im Finger (100 % CH₄ bei Kavernenzustand voll), homogen vermischt (Q-089 Tab. 16)
        finger = F["finger_m3"] / V_REF_Q089 * KAV.volumen
        n_ch4_rest = finger * PropsSI("D", "P", voll[0] * 1e5, "T", voll[1] + 273.15, "Methane") / PropsSI("M", "Methane")
        n_diesel = F["blanket_m3"] * RHO_DIESEL * 1000 / M_DIESEL
        y_oel = F["oel_kg"] * 1e3 / 1e5 / M_OEL / ag.N_NORM      # g/Nm³ -> mol/mol
        n_co2_sole = RESTSOLE_ANTEIL * KAV.volumen * 1000 * ag.co2_molalitaet(*voll)

        zus = {k: v * n_tot for k, v in BASIS[stoff].items()}
        zus["Methane"] = zus.get("Methane", 0.0) + n_ch4_rest
        zus["HydrogenSulfide"] = H2S_PPM * 1e-6 * n_tot
        if stoff == "gem":
            zus["Methane"] += CH4_MIKRO_PPM * 1e-6 * n_tot
            zus["Hydrogen"] -= 4 * CH4_MIKRO_PPM * 1e-6 * n_tot      # 4 H₂ + CO₂ -> CH₄ + 2 H₂O
        zus["Diesel (C10-C20)"] = n_diesel
        zus["Verdichteroel"] = y_oel * n_tot
        n_trocken = sum(zus.values())
        feucht = {k: v / n_trocken * (1 - y_h2o) for k, v in zus.items()}
        feucht["Water"] = y_h2o
        coolprop = {k: v for k, v in zus.items() if k not in ("Diesel (C10-C20)", "Verdichteroel")}
        s = sum(coolprop.values())
        trocken_cp = {k: v / s for k, v in coolprop.items()}
        zus2 = dict(zus, Methane=zus["Methane"] - n_ch4_rest)     # ab dem 2. Zyklus: kein Resterdgas mehr
        s2 = sum(v for k, v in zus2.items() if k in coolprop)
        trocken_cp2 = {k: v / s2 for k, v in zus2.items() if k in coolprop}

        kopf_pruef = []
        for k in koepfe:
            y_sat = ag.wasser_im_co2(k["p"], k["T"])
            frei = y_h2o > y_sat
            kopf_pruef.append(dict(p=k["p"], T=k["T"], y_sat=y_sat, freies_wasser=frei,
                                   hydrat=frei and k["T"] < ag.T_hydrat(k["p"]), spycher_gueltig=k["T"] >= 12.0))
        fall = f"{stoff}_{fk}"
        faelle[fall] = dict(feucht=feucht, trocken_coolprop=trocken_cp)
        faelle[fall + "_ab_2_zyklus"] = dict(feucht=None, trocken_coolprop=trocken_cp2)
        details[fall] = dict(stoff=med.name, fall=F["name"], voll=voll, leer=leer, TGV=TGV, n_tot=n_tot,
                             y_voll=y_voll, y_leer=y_leer, y_h2o=y_h2o, g_Nm3=ag.g_pro_Nm3(y_h2o),
                             ppm=dict(Wasser=1e6 * y_h2o, Resterdgas_CH4=1e6 * n_ch4_rest / n_tot,
                                      H2S=H2S_PPM, CH4_mikrobiell=CH4_MIKRO_PPM if stoff == "gem" else 0.0,
                                      Diesel=1e6 * n_diesel / n_tot, Verdichteroel=1e6 * y_oel),
                             annahmen=F, co2_sole_t=n_co2_sole * 44.01e-6, kopf=kopf_pruef,
                             rueckgabe=dict(H2O_entfernen_ppm=1e6 * y_h2o - OGE["H2O_ppm"],
                                            H2O_entfernen_kg_h=(y_h2o - OGE["H2O_ppm"] * 1e-6) / (1 - y_h2o)
                                            * kb.V_NORM_MAX * ag.N_NORM * ag.M_H2O / 1000,
                                            H2S_entfernen_ppm=H2S_PPM - OGE["H2S_ppm"]))

# ---- Konsole -------------------------------------------------------------------------------------
for fall, d in details.items():
    print(f"\n==== {d['stoff']}, {d['fall']} ====")
    print(f"  Wasser: voll {d['voll'][0]:.0f} bar / {d['voll'][1]:.1f} °C {1e6*d['y_voll']:.0f} ppm, leer "
          f"{d['leer'][0]:.0f} bar / {d['leer'][1]:.1f} °C {1e6*d['y_leer']:.0f} ppm -> {d['g_Nm3']:.2f} g/Nm³"
          "  (Q-089, H₂: 0,47-1,38 g/Nm³)")
    for k, v in d["ppm"].items():
        print(f"  {k:<16} {v:10.2f} ppm")
    fw = [k for k in d["kopf"] if k["freies_wasser"]]
    print(f"  Kopf: freies Wasser in {len(fw)} von {len(d['kopf'])} Kopfzuständen; "
          f"Rückgabe (OGE): {d['rueckgabe']['H2O_entfernen_ppm']:.0f} ppm Wasser "
          f"({d['rueckgabe']['H2O_entfernen_kg_h']:.0f} kg/h bei 100.000 Nm³/h) und "
          f"{d['rueckgabe']['H2S_entfernen_ppm']:.1f} ppm H₂S entfernen")

# ---- Abbildung 1: Wassersättigung --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6.2))
pp = np.linspace(15, 230, 200)
for T, c in ((12, "#9DC3E6"), (20, "#5B9BD5"), (31, "#2E75B6"), (40, "#1F4E79"), (52, "#0B2A4A")):
    ax.plot(pp, [1e6 * ag.wasser_im_co2(p, T) for p in pp], color=c, lw=1.6, label=f"{T} °C, reines Wasser")
FARBE = {"rein": "#00304F", "gem": "#CA220E"}
for stoff in ("rein", "gem"):
    d = details[f"{stoff}_max"]
    ax.plot(d["voll"][0], 1e6 * d["y_voll"], "o", color=FARBE[stoff], ms=8, label=f"{d['stoff']}: voll (gesättigt)")
    ax.plot(d["leer"][0], 1e6 * d["y_leer"], "s", color=FARBE[stoff], ms=8, label=f"{d['stoff']}: leer (gesättigt)")
    ax.plot([k["p"] for k in d["kopf"]], [1e6 * k["y_sat"] for k in d["kopf"]], "x", color=FARBE[stoff], ms=5,
            label=f"{d['stoff']}: Sättigung am Kopf")
ax.axhline(OGE["H2O_ppm"], color="#7030A0", ls="--", lw=1)
ax.text(20, OGE["H2O_ppm"] + 80, "Rückgabe OGE: 30 ppm", color="#7030A0", fontsize=8)
ax.set(xlabel="Druck [bar]", ylabel="Wasser in der CO₂-Phase [mol-ppm]", ylim=(0, 9000),
       title="Wassersättigung von CO₂ (Spycher et al. 2003): Kaverne voll/leer und Kopf beim Ausspeichern")
ax.grid(alpha=0.3)
ax.legend(fontsize=7.5, ncol=2)
fig.tight_layout()
fig.savefig(ORDNER / "abb_K06_wasser.png", dpi=160)
plt.close(fig)

# ---- Abbildung 2: Einträge je Quelle, Min/Max ----------------------------------------------------
fig, ax = plt.subplots(figsize=(10.5, 5))
quellen = list(details["gem_max"]["ppm"].keys())
x = np.arange(len(quellen))
for j, (fall, c) in enumerate((("rein_min", "#9DC3E6"), ("rein_max", "#00304F"),
                                ("gem_min", "#F4B183"), ("gem_max", "#CA220E"))):
    ax.bar(x + (j - 1.5) * 0.2, [max(details[fall]["ppm"][q], 1e-3) for q in quellen], 0.2, color=c,
           label=fall.replace("rein", "rein").replace("gem", "Gemisch").replace("_", " "))
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels([q.replace("_", "\n") for q in quellen])
ax.set(ylabel="Eintrag [mol-ppm]", ylim=(0.01, 2e4),
       title="Was das CO₂ in der Kaverne aufnimmt – Bandbreite nach Q-089 (1. Zyklus)")
ax.grid(alpha=0.3, axis="y")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(ORDNER / "abb_K06_eintraege.png", dpi=160)
plt.close(fig)

kb.speichere_json(ORDNER, "zusammensetzung_nach_kaverne.json", dict(
    auslegungsfall="gem_max", rate=RATE, betriebsweise=ST, oge_rueckgabe=OGE,
    annahmen=dict(faelle=FAELLE, H2S_ppm=H2S_PPM, CH4_mikrobiell_ppm=CH4_MIKRO_PPM, V_ref_q089=V_REF_Q089,
                  rho_diesel=RHO_DIESEL, M_diesel=M_DIESEL, M_oel=M_OEL, restsole_anteil=RESTSOLE_ANTEIL),
    faelle=faelle, details=details))
