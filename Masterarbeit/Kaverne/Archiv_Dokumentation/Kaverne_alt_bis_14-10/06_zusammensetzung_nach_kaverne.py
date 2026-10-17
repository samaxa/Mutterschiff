# -*- coding: utf-8 -*-
"""
Kaverne Schritt 06 - Zusammensetzung des Ausspeichergases
============================================================================
Was nimmt das CO₂ in der Kaverne auf, und mit welcher Zusammensetzung startet
der Ausspeicherpfad? Grundlage ist die H₂-Studie Q-089 (UGS für DGMK 2024,
Musterkaverne Uniper: frühere Erdgaskaverne, Diesel-Blanket, ölgeschmierter
Kolbenverdichter) - übertragen auf CO₂, Begründung je Quelle in ausspeichergas.py.

Kavernenhistorie (wie Q-089, Worst Case): umgewidmete Erdgaskaverne, mit Diesel
als Blanket gesolt, Einspeicherung über ölgeschmierte Kolbenverdichter (S2-Pfad;
DBI empfiehlt Kolbenverdichter, Q-031). Neu gesolte Kaverne mit N₂-Blanket oder
dichte Anlieferung über die Pumpe (S1) wären günstiger.

Eintrag                       Ansatz (Quelle)                                   gilt für
  Wasser                      gesättigt (Spycher et al. 2003) über reinem       immer
                              Wasser, wasserreichster Kavernenzustand - kon-
                              servative Auslegung. Vergleich: Q-089 Abschn. 6.5
                              setzt voll nur 75 % an (Wasseraktivität Sole)
  Resterdgas (als CH₄)        Fingervolumen 0,4 % von V, 100 % CH₄ bei p_max    1. Zyklus
                              (Q-089 Abschn. 6.3: 2000 m³ in 500.000 m³)
  Diesel-Blanket              Restblanket Fall 4c: 1,76 m³ (Q-089 Tab. 10/12),  bis ausgetragen
                              vollständig gelöst (dichtes CO₂ = Lösungsmittel)
  Verdichteröl                0,26 kg je 100.000 Nm³ (Q-089 Tab. 20)            S2-Pfad
  H₂S (mikrobiell)            10 ppm (Q-089 Abschn. 6.4.2; Q-030: zulässig 10)  immer (Annahme)
  CH₄ (mikrobiell)            + 50 ppm, verbraucht 200 ppm H₂ (Q-089 6.4.3,     nur Gemisch
                              4 H₂ + CO₂ -> CH₄ + 2 H₂O)

Zustände aus den vorigen Schritten (Auslegungsrate 100.000 Nm³/h):
  Kaverne voll / leer   03 (rein) und 05 (Gemisch)
  Bohrlochkopf          04 (rein) und 05 (Gemisch) -> fällt am Kopf freies Wasser aus?

Ausgabe: Konsole, abb_K06_wasser.png, abb_K06_eintraege.png,
zusammensetzung_nach_kaverne.json (-> ausspeichergas.py -> Ausspeicherpfad)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import ausspeichergas as ag
import kaverne_bausteine as kb

RATE = "100.000 Nm³/h"
FINGER_ANTEIL = 2000.0 / 500000.0          # Q-089 Abschn. 6.3 (ungünstiger Fall)
BLANKET_M3, RHO_DIESEL, M_DIESEL = 1.76, 827.7, 230.0   # m³, kg/m³ (Q-089 Tab. 12), g/mol (Tab. 11, Mitte)
OEL_KG_JE_1E5_NM3, M_OEL = 0.26, 300.0     # Q-089 Tab. 20 (oberer Wert), g/mol (Tab. 5)
H2S_PPM, CH4_MIKRO_PPM = 10.0, 50.0        # Q-089 Abschn. 6.4
RESTSOLE_ANTEIL = 0.01                     # eigene Annahme: 1 % von V Restsole (nur Größenordnung)

zyklus = kb.lade_json("kavernenzyklus.json", "03_ein_ausspeicherrate.py")
koepfe_rein = kb.lade_json("bohrlochkopf_ausspeicherung.json", "04_bohrlochkopf_ausspeicherung.py")
gem_json = kb.lade_json("gemisch_vs_rein.json", "05_gemisch_vs_rein.py")

BASIS = {"rein": {"CO2": 1.0},
         "gem": {name: x / 100 for _, name, x, _ in kb.gw.ZUSAMMENSETZUNG}}
M_MISCH = {"rein": PropsSI("M", "CO2") * 1000, "gem": kb.gw.gemisch().molar_mass() * 1000}   # g/mol


def zustaende(kav, stoff):
    """Kaverne voll/leer und Kopfzustände (p, T) beim Ausspeichern mit RATE."""
    if stoff == "rein":
        aus = [x for x in zyklus[kav.kurz]["raten"][RATE]["verlauf"] if x["art"] == "aus"]
        koepfe = [z[m] for z in koepfe_rein[kav.kurz][RATE] for m in ("adiabat", "gebirge") if z[m]]
    else:
        aus = gem_json[kav.kurz]["gem"]["raten"][RATE]["verlauf"]
        koepfe = [k["kopf"] for k in gem_json[kav.kurz]["gem"]["raten"][RATE]["koepfe"] if k["kopf"]]
    return (aus[0]["p_mitte"], aus[0]["T"]), (aus[-1]["p_mitte"], aus[-1]["T"]), koepfe


faelle, details = {}, {}
for kav in kb.KAVERNEN:
    for stoff in ("rein", "gem"):
        med = kb.REIN if stoff == "rein" else kb.gemisch()
        voll, leer, koepfe = zustaende(kav, stoff)
        TGV = kb.inventar(med, kav, kav.p_max)                       # t
        n_tot = TGV * 1e6 / M_MISCH[stoff]                           # mol
        # Wasser: Austrittsstrom gesättigt (über reinem Wasser), der wasserreichere Zustand zählt.
        # Vergleich nach Q-089: voll nur 75 % (gesättigte Sole), leer 100 %.
        y_voll = ag.wasser_im_co2(*voll, a_w=ag.A_W_AUSLEGUNG)
        y_leer = ag.wasser_im_co2(*leer, a_w=ag.A_W_AUSLEGUNG)
        y_h2o = max(y_voll, y_leer)
        y_q089 = max(ag.wasser_im_co2(*voll, a_w=ag.A_W_SOLE), y_leer)
        # Resterdgas im Finger, homogen vermischt
        n_ch4_rest = FINGER_ANTEIL * kav.volumen * PropsSI("D", "P", voll[0] * 1e5, "T", voll[1] + 273.15, "Methane") \
            / PropsSI("M", "Methane")
        # Diesel und Verdichteröl
        n_diesel = BLANKET_M3 * RHO_DIESEL * 1000 / M_DIESEL
        y_oel = OEL_KG_JE_1E5_NM3 * 1e3 / 1e5 / M_OEL / ag.N_NORM    # g/Nm³ -> mol/mol
        # CO₂ in Restsole (Größenordnung)
        n_co2_sole = RESTSOLE_ANTEIL * kav.volumen * 1000 * ag.co2_molalitaet(*voll)   # ~1000 kg Wasser je m³

        zus = {k: v * n_tot for k, v in BASIS[stoff].items()}           # mol
        zus["Methane"] = zus.get("Methane", 0.0) + n_ch4_rest
        zus["HydrogenSulfide"] = H2S_PPM * 1e-6 * n_tot
        if stoff == "gem":
            zus["Methane"] += CH4_MIKRO_PPM * 1e-6 * n_tot
            zus["Hydrogen"] -= 4 * CH4_MIKRO_PPM * 1e-6 * n_tot
        zus["Diesel (C10-C20)"] = n_diesel
        zus["Verdichteroel"] = y_oel * n_tot
        n_trocken = sum(zus.values())
        feucht = {k: v / n_trocken * (1 - y_h2o) for k, v in zus.items()}
        feucht["Water"] = y_h2o
        coolprop = {k: v for k, v in zus.items() if k not in ("Diesel (C10-C20)", "Verdichteroel")}
        s = sum(coolprop.values())
        trocken_cp = {k: v / s for k, v in coolprop.items()}
        # ohne Resterdgas = ab dem 2. Zyklus
        zus2 = dict(zus, Methane=zus["Methane"] - n_ch4_rest)
        s2 = sum(v for k, v in zus2.items() if k in coolprop)
        trocken_cp2 = {k: v / s2 for k, v in zus2.items() if k in coolprop}

        # Freies Wasser am Kopf und Hydrat
        kopf_pruef = []
        for k in koepfe:
            y_sat_kopf = ag.wasser_im_co2(k["p"], k["T"])
            frei = y_h2o > y_sat_kopf
            kopf_pruef.append(dict(p=k["p"], T=k["T"], y_sat=y_sat_kopf, freies_wasser=frei,
                                   hydrat=frei and k["T"] < ag.T_hydrat(k["p"]),
                                   spycher_gueltig=k["T"] >= 12.0))
        fall = f"{kav.kurz}_{stoff}"
        faelle[fall] = dict(feucht=feucht, trocken_coolprop=trocken_cp)
        faelle[fall + "_ab_2_zyklus"] = dict(feucht=None, trocken_coolprop=trocken_cp2)
        details[fall] = dict(kav=kav, med=med, voll=voll, leer=leer, TGV=TGV, y_voll=y_voll, y_leer=y_leer, y_q089=y_q089,
                             y_h2o=y_h2o, ppm=dict(Resterdgas_CH4=1e6 * n_ch4_rest / n_tot, H2S=H2S_PPM,
                                                   CH4_mikrobiell=CH4_MIKRO_PPM if stoff == "gem" else 0.0,
                                                   Diesel=1e6 * n_diesel / n_tot, Verdichteroel=1e6 * y_oel,
                                                   Wasser=1e6 * y_h2o),
                             co2_sole_t=n_co2_sole * 44.01e-6, kopf=kopf_pruef, n_tot=n_tot)

# ---- Konsole ------------------------------------------------------------------------------------
for fall, d in details.items():
    kav = d["kav"]
    print(f"\n==== {kav.name}, {d['med'].name} (Inhalt voll {d['TGV']/1e3:.0f} kt) ====")
    print(f"  Wasser voll  {d['voll'][0]:.0f} bar / {d['voll'][1]:.1f} °C, gesättigt: {1e6*d['y_voll']:6.0f} ppm = "
          f"{ag.g_pro_Nm3(d['y_voll']):.2f} g/Nm³")
    print(f"  (Vergleich Q-089-Ansatz mit 75 % bei voll: {1e6*d['y_q089']:6.0f} ppm = {ag.g_pro_Nm3(d['y_q089']):.2f} g/Nm³)")
    print(f"  Wasser leer  {d['leer'][0]:.0f} bar / {d['leer'][1]:.1f} °C, gesättigt: {1e6*d['y_leer']:6.0f} ppm = "
          f"{ag.g_pro_Nm3(d['y_leer']):.2f} g/Nm³   (Q-089, H₂: 0,47-1,38 g/Nm³)"
          + ("  [unter 12 °C: Spycher extrapoliert]" if d["leer"][1] < 12 else ""))
    for k, v in d["ppm"].items():
        print(f"  {k:<16} {v:10.2f} ppm")
    print(f"  CO₂ in Restsole (1 % von V, obere Schranke): {d['co2_sole_t']:.0f} t = "
          f"{100*d['co2_sole_t']/d['TGV']:.2f} % des Inhalts -> Zusammensetzung praktisch unverändert")
    fw = [k for k in d["kopf"] if k["freies_wasser"]]
    hy = [k for k in d["kopf"] if k["hydrat"]]
    print(f"  Bohrlochkopf: freies Wasser in {len(fw)} von {len(d['kopf'])} Kopfzuständen, "
          f"Hydratgefahr in {len(hy)}" + (" (Spycher unter 12 °C extrapoliert)" if any(not k['spycher_gueltig'] for k in fw) else ""))
y30 = ag.wasser_im_co2(30.0, 12.0)
print(f"\nNach Drossel auf 30 bar (04: -5,6 °C, zweiphasig): CO₂-Hydrat ab T < {ag.T_hydrat(30.0):.1f} °C, "
      f"Wassersättigung schon bei 12 °C nur {1e6*y30:.0f} ppm -> Abscheider + Trocknung + Vorwärmung vor der Drossel")

# ---- Abbildung 1: Wassersättigung -----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6.2))
pp = np.linspace(15, 230, 200)
for T, c in ((12, "#9DC3E6"), (20, "#5B9BD5"), (31, "#2E75B6"), (40, "#1F4E79"), (50, "#0B2A4A")):
    ax.plot(pp, [1e6 * ag.wasser_im_co2(p, T) for p in pp], color=c, lw=1.6, label=f"{T} °C, reines Wasser")
FARBE = {"tief": "#00304F", "flach": "#EE7203"}
for fall, d in details.items():
    if not fall.endswith("rein"):
        continue
    kurz = d["kav"].kurz
    ax.plot(d["voll"][0], 1e6 * d["y_voll"], "o", color=FARBE[kurz], ms=8, label=f"{kurz} voll (gesättigt)")
    ax.plot(d["leer"][0], 1e6 * d["y_leer"], "s", color=FARBE[kurz], ms=8, label=f"{kurz} leer (gesättigt)")
    ax.plot([k["p"] for k in d["kopf"]], [1e6 * k["y_sat"] for k in d["kopf"]], "x", color=FARBE[kurz], ms=5,
            label=f"{kurz}: Sättigung am Kopf")
ax.set(xlabel="Druck [bar]", ylabel="Wasser in der CO₂-Phase [mol-ppm]", ylim=(0, 9000),
       title="Wassersättigung von CO₂ (Spycher et al. 2003): im dichten CO₂ mehr Wasser als im Gas\n"
             "-> Kaverne liefert Wasser, das am Kopf bzw. nach der Drossel ausfällt (x unter den Punkten)")
ax.grid(alpha=0.3)
ax.legend(fontsize=7.5, ncol=2)
fig.tight_layout()
fig.savefig(kb.ORDNER / "abb_K06_wasser.png", dpi=160)
print("\ngespeichert: abb_K06_wasser.png")

# ---- Abbildung 2: Einträge je Quelle -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))
quellen = list(details["tief_gem"]["ppm"].keys())
x = np.arange(len(quellen))
for j, (fall, c) in enumerate((("tief_rein", "#00304F"), ("tief_gem", "#CA220E"),
                                ("flach_rein", "#EE7203"), ("flach_gem", "#F4B183"))):
    ax.bar(x + (j - 1.5) * 0.2, [max(details[fall]["ppm"][q], 1e-3) for q in quellen], 0.2, color=c, label=fall)
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels([q.replace("_", "\n") for q in quellen])
ax.set(ylabel="Eintrag [mol-ppm]", ylim=(0.1, 2e4),
       title="Was das CO₂ in der Kaverne aufnimmt (Worst Case nach Q-089, 1. Zyklus)")
ax.grid(alpha=0.3, axis="y")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(kb.ORDNER / "abb_K06_eintraege.png", dpi=160)
print("gespeichert: abb_K06_eintraege.png")

kb.speichere_json("zusammensetzung_nach_kaverne.json", dict(
    auslegungsfall="tief_gem",
    annahmen=dict(rate=RATE, finger_anteil=FINGER_ANTEIL, blanket_m3=BLANKET_M3, oel_kg_je_1e5_Nm3=OEL_KG_JE_1E5_NM3,
                  H2S_ppm=H2S_PPM, CH4_mikrobiell_ppm=CH4_MIKRO_PPM, a_w_auslegung=ag.A_W_AUSLEGUNG,
                  a_w_vergleich_q089=ag.A_W_SOLE),
    faelle=faelle,
    details={f: {k: v for k, v in d.items() if k not in ("kav", "med")} for f, d in details.items()}))
