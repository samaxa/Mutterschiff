# -*- coding: utf-8 -*-
"""
G03 - Isenthalpe Entspannung (Drosselung): CO2, Erdgas und Wasserstoff
============================================================================
Was passiert, wenn das Gas in einem Ventil von 210 bar / 50 °C auf 10 bar
gedrosselt wird? In der Drossel wird keine Arbeit geleistet und (fast) keine
Wärme getauscht, also bleibt die Enthalpie gleich: h = konst.

Die Temperaturänderung pro bar ist der Joule-Thomson-Koeffizient
µ_JT = (∂T/∂p)_h (Schritt G05). Mit der Mappe vergleichbar wird hier die
mittlere Steigung zwischen zwei Druckstufen ausgegeben:
    µ_JT,mittel ≈ ΔT / Δp

Ergebnis in Worten
  CO2   kühlt stark ab und erreicht bei ~71 bar die Siedelinie. Danach
        verdampft ein Teil, bei 10 bar sind es knapp 58 % Dampf bei -40 °C.
  CH4   kühlt deutlich ab, bleibt aber einphasig gasförmig.
  H2    wird bei Raumtemperatur beim Drosseln sogar wärmer (µ_JT < 0,
        Inversionstemperatur von H2 liegt weit unter Raumtemperatur).

Fall wie in der alten Mappe, Blatt „Isenthalpe_Entspannung_Gase“
(dort CoolProp Online, hier CoolProp direkt). Annahmen: gasgrundlagen_bausteine.py
Ergebnisse: Abbildungen/G03_entspannung.json
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import gasgrundlagen_bausteine as gb

erg = {}
print(f"Drosselung {gb.P_SPEICHER:.0f} bar / {gb.T_SPEICHER:.0f} °C -> {gb.P_ENDE_DROSSEL:.0f} bar\n")
for k, (f, name, _) in gb.STOFFE.items():
    h0, zeilen = gb.isenthalpe_entspannung(k)
    ein = gb.eintritt_zweiphasig(k)
    T_end = zeilen[-1]["T"]
    erg[k] = {"h0": h0, "zeilen": zeilen, "dT": T_end - gb.T_SPEICHER,
              "eintritt_zweiphasig": ein}
    zusatz = (f", ab {ein[0]:.1f} bar / {ein[1]:.1f} °C zweiphasig, Dampfanteil am Ende "
              f"{zeilen[-1]['q']:.2f}" if ein else ", bleibt einphasig")
    print(f"{name:<18} h = {h0:7.1f} kJ/kg  T_end = {T_end:6.1f} °C  ΔT = {T_end - gb.T_SPEICHER:+6.1f} K{zusatz}")

# mittlere Steigung je 10-bar-Schritt für CO2 (zeigt: Abkühlung vor allem unter ~100 bar)
print("\nCO2: mittlere Abkühlung je bar zwischen zwei Stufen")
z = erg["CO2"]["zeilen"]
for a, b in zip(z[:-1], z[1:]):
    if a["p"] in (210, 150, 110, 90, 80, 70, 60, 30):
        print(f"  {a['p']:5.0f} -> {b['p']:5.0f} bar: {(a['T'] - b['T']) / (a['p'] - b['p']):5.2f} K/bar  ({b['phase']})")

# ---- Abbildung: links T(p) aller Gase, rechts Weg von CO2 im p-T-Diagramm ----------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.6))
for k, (f, name, farbe) in gb.STOFFE.items():
    z = erg[k]["zeilen"]
    p = [r["p"] for r in z]
    T = [r["T"] for r in z]
    ax1.plot(p, T, "-", color=farbe, lw=2.0, label=f"{name}: ΔT = {erg[k]['dT']:+.0f} K")
    ein_ = [r for r in z if r["q"] is not None]
    aus_ = [r for r in z if r["q"] is None]
    ax1.plot([r["p"] for r in aus_], [r["T"] for r in aus_], "s", color=farbe, ms=5)
    if ein_:
        ax1.plot([r["p"] for r in ein_], [r["T"] for r in ein_], "o", mfc="white", mec=farbe,
                 mew=1.5, ms=6, label="zweiphasig")
ax1.axhline(gb.T_SPEICHER, color="#999999", lw=0.8, ls=":")
ax1.invert_xaxis()
ax1.set_xlabel("Druck [bar] (Drosselung von links nach rechts)")
ax1.set_ylabel("Temperatur [°C]")
ax1.set_title(f"Isenthalpe Drosselung ab {gb.P_SPEICHER:.0f} bar / {gb.T_SPEICHER:.0f} °C")
ax1.grid(alpha=0.25)
ax1.legend(loc="lower left", fontsize=8.5, framealpha=0.92)

# rechts: CO2 im Phasendiagramm
T_s, p_s = gb.saettigungslinie_co2()
kw = gb.kennwerte("CO2")
Tmin, Tmax, Pmin, Pmax = -50.0, 60.0, 0.0, 230.0
C_GAS, C_FLUE, C_SUP = "#CFE2F3", "#D9EAD3", "#FCE5CD"
gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, kw["p_krit"]), (kw["T_krit"], kw["p_krit"])]
gas += [(t, p) for t, p in zip(T_s[::-1], p_s[::-1]) if t >= Tmin] + [(Tmin, PropsSI("P", "T", gb.K(Tmin), "Q", 0, "CO2") / 1e5)]
ax2.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))
flue = [(Tmin, PropsSI("P", "T", gb.K(Tmin), "Q", 0, "CO2") / 1e5), (Tmin, Pmax), (kw["T_krit"], Pmax)]
flue += [(t, p) for t, p in zip(T_s[::-1], p_s[::-1]) if t >= Tmin]
ax2.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))
ax2.add_patch(plt.Rectangle((kw["T_krit"], kw["p_krit"]), Tmax - kw["T_krit"], Pmax - kw["p_krit"],
                            fc=C_SUP, ec="none", zorder=0))
ax2.plot(T_s, p_s, color="#00304F", lw=2.0, label="Siedelinie")
ax2.plot(kw["T_krit"], kw["p_krit"], "o", color="#00304F", ms=7, mec="white", mew=1.4)
z = erg["CO2"]["zeilen"]
ax2.plot([r["T"] for r in z], [r["p"] for r in z], "-", color="#CA220E", lw=2.0, label="Drosselung (h = konst.)")
ax2.plot([r["T"] for r in z if r["q"] is None], [r["p"] for r in z if r["q"] is None], "s",
         color="#CA220E", ms=4.5)
ax2.plot([r["T"] for r in z if r["q"] is not None], [r["p"] for r in z if r["q"] is not None], "o",
         mfc="white", mec="#CA220E", mew=1.4, ms=6, label="zweiphasig (auf der Siedelinie)")
ein = erg["CO2"]["eintritt_zweiphasig"]
box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8)
ax2.annotate(f"Siedelinie erreicht\n{ein[0]:.0f} bar / {ein[1]:.0f} °C", (ein[1], ein[0]),
             textcoords="offset points", xytext=(-120, 40), fontsize=8.5, bbox=box,
             arrowprops=dict(arrowstyle="-", color="#555555", lw=0.7))
ax2.text(-35, 150, "flüssig", fontsize=11, color="#007335", weight="bold", bbox=box)
ax2.text(-35, 20, "gasförmig", fontsize=11, color="#164a73", weight="bold", bbox=box)
ax2.text(38, 200, "überkritisch", fontsize=11, color="#a3480b", weight="bold", bbox=box)
ax2.set_xlim(Tmin, Tmax)
ax2.set_ylim(Pmin, Pmax)
ax2.set_xlabel("Temperatur [°C]")
ax2.set_ylabel("Druck [bar]")
ax2.set_title("CO₂: Weg der Drosselung im p-T-Diagramm")
ax2.grid(alpha=0.25)
ax2.legend(loc="lower right", fontsize=8.5, framealpha=0.92)

fig.tight_layout()
fig.savefig(gb.ABB / "abb_G03_drosselung_vergleich.png", dpi=175)
plt.close(fig)
print("\ngespeichert: abb_G03_drosselung_vergleich.png")

json.dump(erg, open(gb.ABB / "G03_entspannung.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
