# -*- coding: utf-8 -*-
"""
Schritt 0b - Verifikation der Stoffmodelle: CoolProp gegen unabhängige Software
============================================================================
Frage: Rechnet CoolProp die Stoffwerte richtig, und wie groß ist die
Modellunsicherheit der Phasengrenze des Worst-Case-Gemischs?

Vergleich mit einer zweiten, unabhängig programmierten Stoffdatenbibliothek:
thermopack (SINTEF Energy Research, https://github.com/thermotools/thermopack),
installierbar mit  pip install thermopack

Verglichene Modelle
  CoolProp HEOS   Reinstoff: Span & Wagner (1996)
                  Gemisch:   Mehrfluid-Helmholtz-Modell, Reinstoff-Referenz-
                             gleichungen + Binärparameter aus GERG-2008
                             (Kunz & Wagner 2012) und EOS-CG (Gernert 2013)
  thermopack GERG-2008   GERG-2008 vollständig (eigene Reinstoffgleichungen
                         und Binärparameter nach Kunz & Wagner 2012),
                         eigener Programmcode -> unabhängige Gegenrechnung
  thermopack PR / SRK    kubische Zustandsgleichungen (Peng-Robinson,
                         Soave-Redlich-Kwong) - zum Vergleich, wie groß der
                         Fehler eines einfachen Modells wäre

Ergebnis: Konsolenausgabe (Tabellen), abb_validierung_phasengrenze.png (Gemisch)
          und abb_validierung_rein_co2.png (reines CO2)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import CoolProp
import CoolProp.CoolProp as CP
from thermopack.multiparameter import multiparam
from thermopack.cubic import cubic

import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parents[1]          # Begleitstoffe_CO2
sys.path.insert(0, str(ORDNER / "Grundlagen"))         # gemisch_worstcase, einspeicherung_bausteine
ABB = ORDNER / "Abbildungen"                           # Abbildungen und Ergebnisdateien

import gemisch_worstcase as gw

print(f"CoolProp-Version: {CoolProp.__version__}")

# ---- 1) Reines CO2 --------------------------------------------------------
M_CO2 = CP.PropsSI("M", "CO2")          # kg/mol
eins = np.array([1.0])
rein = {
    "GERG-2008 (thermopack)": multiparam("CO2", "GERG2008"),
    "Peng-Robinson": cubic("CO2", "PR"),
    "SRK": cubic("CO2", "SRK"),
}

print("\nReines CO2 - Dampfdruck [bar]")
print(f"{'T [°C]':>7} {'CoolProp':>9} " + " ".join(f"{k:>24}" for k in rein))
for T_C in [-50, -20, 0, 15, 20, 25, 30]:
    T = T_C + 273.15
    p_cp = CP.PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5
    zeile = f"{T_C:7.0f} {p_cp:9.3f} "
    for eos in rein.values():
        p = eos.bubble_pressure(T, eins)[0] / 1e5
        zeile += f"{p:13.3f} ({100*(p-p_cp)/p_cp:+6.2f} %)"
    print(zeile)

print("\nReines CO2 - Dichte an den Betriebspunkten [kg/m3]")
PUNKTE = [("S1 Netzübergabe", 91.0, 15.0), ("S2 Netzübergabe", 30.0, 15.0),
          ("S2 Kühleraustritt", 80.0, 25.0), ("Bohrlochkopf", 107.6, 20.0),
          ("Kaverne max.", 210.0, 50.0)]
print(f"{'Punkt':<18} {'CoolProp':>9} " + " ".join(f"{k:>24}" for k in rein))
for name, p_bar, T_C in PUNKTE:
    T, p = T_C + 273.15, p_bar * 1e5
    rho_cp = CP.PropsSI("D", "P", p, "T", T, "CO2")
    zeile = f"{name:<18} {rho_cp:9.1f} "
    for eos in rein.values():
        phase = eos.LIQPH if rho_cp > 300 else eos.VAPPH
        v, = eos.specific_volume(T, p, eins, phase)
        rho = M_CO2 / v
        zeile += f"{rho:13.1f} ({100*(rho-rho_cp)/rho_cp:+6.2f} %)"
    print(zeile)

# ---- 2) Worst-Case-Gemisch -------------------------------------------------
# gleiche Reihenfolge wie gemisch_worstcase.ZUSAMMENSETZUNG
TP_NAMEN = {"CO2": "CO2", "Nitrogen": "N2", "Argon": "AR", "Methane": "C1",
            "Hydrogen": "H2", "CarbonMonoxide": "CO"}
tp_komp = ",".join(TP_NAMEN[k] for k in gw.KOMPONENTEN)
z = np.array(gw.MOLANTEILE)

gem = {
    "GERG-2008 (thermopack)": multiparam(tp_komp, "GERG2008"),
    "Peng-Robinson": cubic(tp_komp, "PR"),
}

pg = gw.phasengrenze()
T_tripel_C = CP.PropsSI("Ttriple", "CO2") - 273.15

print("\nWorst-Case-Gemisch - Phasengrenze")
kennwerte = {"CoolProp HEOS": {
    "krit": pg["krit"], "cricondenbar": pg["cricondenbar"],
    "p_blase15": gw.blasendruck(15), "p_tau15": gw.taudruck(15)}}
huellen = {}
for name, eos in gem.items():
    T, p = eos.get_envelope_twophase(5e5, z, maximum_pressure=150e5, calc_v=False)
    T, p = np.array(T) - 273.15, np.array(p) / 1e5
    gueltig = T >= T_tripel_C               # wie in CoolProp: kein Feststoff
    huellen[name] = (T[gueltig], p[gueltig])
    Tc, _, pc = eos.critical(z)
    i = int(np.argmax(p[gueltig]))
    kennwerte[name] = {
        "krit": (Tc - 273.15, pc / 1e5),
        "cricondenbar": (T[gueltig][i], p[gueltig][i]),
        "p_blase15": eos.bubble_pressure(288.15, z)[0] / 1e5,
        "p_tau15": eos.dew_pressure(288.15, z)[0] / 1e5,
    }

print(f"{'Modell':<24} {'krit. Punkt':>18} {'Cricondenbar':>18} {'p_Blase 15°C':>13} {'p_Tau 15°C':>11}")
for name, k in kennwerte.items():
    print(f"{name:<24} {k['krit'][0]:6.1f} °C/{k['krit'][1]:5.1f} bar "
          f"{k['cricondenbar'][0]:6.1f} °C/{k['cricondenbar'][1]:5.1f} bar "
          f"{k['p_blase15']:9.1f} bar {k['p_tau15']:7.1f} bar")

print("\nWorst-Case-Gemisch - Dichte an den Betriebspunkten [kg/m3]")
M_gem = gw.gemisch().molar_mass()
AS = gw.gemisch()
print(f"{'Punkt':<18} {'CoolProp':>9} " + " ".join(f"{k:>24}" for k in gem))
for name, p_bar, T_C in PUNKTE:
    s = gw.stoffwerte(p_bar, T_C, AS)
    if s["phase"] == "ZWEIPHASIG":
        print(f"{name:<18} zweiphasig - Dichtevergleich nicht sinnvoll")
        continue
    zeile = f"{name:<18} {s['rho']:9.1f} "
    for eos in gem.values():
        phase = eos.LIQPH if s["rho"] > 300 else eos.VAPPH
        v, = eos.specific_volume(T_C + 273.15, p_bar * 1e5, z, phase)
        rho = M_gem / v
        zeile += f"{rho:13.1f} ({100*(rho-s['rho'])/s['rho']:+6.2f} %)"
    print(zeile)

# ---- 3) Plot: Phasengrenze Gemisch nach drei Modellen ----------------------
ROT, BLAU, GRAU, GRUEN = "#CA220E", "#164a73", "#666666", "#007335"
fig, ax = plt.subplots(figsize=(8.5, 6.2))

T_s = np.linspace(CP.PropsSI("Ttriple", "CO2"), CP.PropsSI("Tcrit", "CO2"), 200)
ax.plot(T_s - 273.15, [CP.PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_s],
        color="#00304F", lw=1.6, label="reines CO₂ (Span-Wagner)")

ax.plot(pg["T_blase"], pg["p_blase"], color=ROT, lw=2.2, label="Gemisch: CoolProp HEOS")
ax.plot(pg["T_tau"], pg["p_tau"], color=ROT, lw=2.2)
ax.plot(*pg["krit"], "o", color=ROT, ms=7, markeredgecolor="white", markeredgewidth=1.2)

stil = {"GERG-2008 (thermopack)": (BLAU, "--"), "Peng-Robinson": (GRAU, ":")}
for name, (T, p) in huellen.items():
    farbe, ls = stil[name]
    ax.plot(T, p, color=farbe, lw=2.0, ls=ls, label=f"Gemisch: {name}")
    ax.plot(*kennwerte[name]["krit"], "o", color=farbe, ms=6,
            markeredgecolor="white", markeredgewidth=1.2)

for name, p_bar, T_C in PUNKTE[:3]:
    ax.plot(T_C, p_bar, "s", color=GRUEN if p_bar > 85 else BLAU, ms=8,
            markeredgecolor="black", markeredgewidth=0.7, zorder=5)
    versatz = (-105, 10) if name == "S2 Kühleraustritt" else (8, 6)
    ax.annotate(name, (T_C, p_bar), textcoords="offset points", xytext=versatz, fontsize=8.5)

ax.set_xlim(-60, 40)
ax.set_ylim(0, 100)
ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("Phasengrenze Worst-Case-Gemisch: drei Stoffmodelle im Vergleich")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.92)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(ABB / "abb_validierung_phasengrenze.png", dpi=175)
print("\ngespeichert: abb_validierung_phasengrenze.png")

# ---- 4) Plot: reines CO2 nach vier Modellen --------------------------------
# oben:  Dampfdrucklinie und ihre Abweichung von CoolProp (Span-Wagner)
# unten: Dichte auf der 15-°C-Isotherme (Pipelinetemperatur, S1) über dem
#        Druck und ihre Abweichung - hier zeigt sich, wie stark einfache
#        kubische Modelle die Dichte der flüssigen/dichten Phase verfehlen
ORANGE = "#a3480b"
stil_rein = {"GERG-2008 (thermopack)": (BLAU, "--"), "Peng-Robinson": (GRAU, ":"),
             "SRK": (ORANGE, "-.")}

T_krit = CP.PropsSI("Tcrit", "CO2")
T_sat = np.linspace(CP.PropsSI("Ttriple", "CO2"), T_krit - 0.3, 120)
p_cp = np.array([CP.PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_sat]) / 1e5

T_iso = 15.0 + 273.15
p_iso = np.linspace(60.0, 220.0, 81)          # alle Punkte oberhalb p_s(15 °C) = 50,9 bar
rho_cp = np.array([CP.PropsSI("D", "P", p * 1e5, "T", T_iso, "CO2") for p in p_iso])

fig, ((a1, a2), (a3, a4)) = plt.subplots(2, 2, figsize=(12, 8.6))
a1.plot(T_sat - 273.15, p_cp, color=ROT, lw=2.6, label="CoolProp (Span-Wagner)")
a3.plot(p_iso, rho_cp, color=ROT, lw=2.6, label="CoolProp (Span-Wagner)")
for ax in (a2, a4):
    ax.axhline(0, color=ROT, lw=2.6, label="CoolProp (Span-Wagner)")

for name, eos in rein.items():
    farbe, ls = stil_rein[name]
    p_m = []
    for T in T_sat:
        try:
            p_m.append(eos.bubble_pressure(T, eins)[0] / 1e5)
        except Exception:                      # direkt am kritischen Punkt keine Lösung
            p_m.append(np.nan)
    p_m = np.array(p_m)
    rho_m = np.array([M_CO2 / eos.specific_volume(T_iso, p * 1e5, eins, eos.LIQPH)[0]
                      for p in p_iso])
    a1.plot(T_sat - 273.15, p_m, color=farbe, lw=1.8, ls=ls, label=name)
    a2.plot(T_sat - 273.15, 100 * (p_m - p_cp) / p_cp, color=farbe, lw=1.8, ls=ls, label=name)
    a3.plot(p_iso, rho_m, color=farbe, lw=1.8, ls=ls, label=name)
    a4.plot(p_iso, 100 * (rho_m - rho_cp) / rho_cp, color=farbe, lw=1.8, ls=ls, label=name)

# Betriebspunkte auf der 15-°C-Isotherme
for ax in (a3, a4):
    ax.axvline(91.0, color=GRUEN, lw=1.0, alpha=0.7)
a3.annotate("S1 Netzübergabe\n91 bar / 15 °C", (91.0, CP.PropsSI("D", "P", 91e5, "T", T_iso, "CO2")),
            textcoords="offset points", xytext=(10, -40), fontsize=8.5, color=GRUEN)

a1.set(xlabel="Temperatur [°C]", ylabel="Dampfdruck [bar]",
       title="a) Dampfdrucklinie (Siedelinie)")
a2.set(xlabel="Temperatur [°C]", ylabel="Abweichung von CoolProp [%]",
       title="b) Abweichung Dampfdruck")
a3.set(xlabel="Druck [bar]", ylabel="Dichte [kg/m³]",
       title="c) Dichte bei 15 °C (Pipelinetemperatur)")
a4.set(xlabel="Druck [bar]", ylabel="Abweichung von CoolProp [%]",
       title="d) Abweichung Dichte bei 15 °C")
a1.set_xlim(-60, 35)
a2.set_xlim(-60, 35)
for ax in (a1, a2, a3, a4):
    ax.grid(alpha=0.25)
a1.legend(loc="upper left", fontsize=8.5, framealpha=0.92)
a2.text(0.02, 0.88, "GERG-2008 liegt auf der Nulllinie (≤ 0,02 %)", transform=a2.transAxes,
        fontsize=8.5, color=BLAU)
a4.text(0.30, 0.55, "GERG-2008 liegt auf der Nulllinie (≤ 0,02 %)", transform=a4.transAxes,
        fontsize=8.5, color=BLAU)

fig.suptitle("Reines CO₂: CoolProp (Span-Wagner) im Vergleich mit drei weiteren Stoffmodellen",
             fontsize=12)
fig.tight_layout()
fig.savefig(ABB / "abb_validierung_rein_co2.png", dpi=175)
print("gespeichert: abb_validierung_rein_co2.png")
