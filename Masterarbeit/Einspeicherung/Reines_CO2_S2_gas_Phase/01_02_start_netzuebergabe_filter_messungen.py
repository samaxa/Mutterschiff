# -*- coding: utf-8 -*-
"""
Schritt 0 - Startpunkt der Kette: Netzübergabe, Szenario 2 (gasförmig)
============================================================================
in welchem Zustand kommt das CO2 an, und wo liegt es im p-T-Phasendiagramm?

Herkunft der beiden Zahlen
  Druck:       30 bar   - Annahme aus der Vorarbeit (ObertageAnlageRechner).
               Die alte Tabelle nennt dazu Q-040 (ISO 27913), dort noch
               nicht ausgewertet - zu prüfen.
  Temperatur:  15 °C    - Medientemperatur an der Pipeline, wie in Szenario 1.

Schritt 1 (Messtechnik und Filtration): kein Druckverlust, keine
Zustandsänderung angesetzt - der Zustand bleibt 30 bar / 15 °C.

Unterschied zu Szenario 1: bei 30 bar liegt das CO2 unterhalb der
Sättigungslinie, also gasförmig. Gas lässt sich nicht pumpen - deshalb
braucht Szenario 2 Verdichter (siehe 03_Verdichtung_Kuehlung_Pumpe.py).

Diagramm: gleiche Farben und Achsen wie Diagramm 1 im Blatt "Phasendiagramm"
der Excel-Rechenübersicht (-80 bis 100 °C, 0 bis 130 bar).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI, PhaseSI

# ---- 1) Startpunkt ---------------------------------------------------------
p_uebergabe_bar = 30.0
T_uebergabe_C = 15.0

p_uebergabe = p_uebergabe_bar * 1e5           # bar -> Pa
T_uebergabe = T_uebergabe_C + 273.15          # °C -> K

# ---- 2) Phase und Kennwerte -------------------------------------------------
phase = PhaseSI("P", p_uebergabe, "T", T_uebergabe, "CO2")
rho = PropsSI("D", "P", p_uebergabe, "T", T_uebergabe, "CO2")   # kg/m3
h = PropsSI("H", "P", p_uebergabe, "T", T_uebergabe, "CO2")     # J/kg

T_krit = PropsSI("Tcrit", "CO2")
p_krit = PropsSI("Pcrit", "CO2")
T_tripel = PropsSI("Ttriple", "CO2")
p_tripel = PropsSI("ptriple", "CO2")

# Abstand zur Sättigungslinie: bei welchem Druck würde das CO2 bei 15 °C
# kondensieren, und bei welcher Temperatur bei 30 bar (Taupunkt)?
p_sat_15 = PropsSI("P", "T", T_uebergabe, "Q", 1, "CO2") / 1e5
T_tau_30 = PropsSI("T", "P", p_uebergabe, "Q", 1, "CO2") - 273.15

print("Zustand an der Netzübergabe (Szenario 2):")
print(f"  p = {p_uebergabe_bar:.1f} bar, T = {T_uebergabe_C:.1f} °C")
print(f"  Phase laut CoolProp: {phase}")
print(f"  Dichte:    {rho:.1f} kg/m3")
print(f"  Enthalpie: {h/1000:.1f} kJ/kg")
print(f"  Sättigungsdruck bei {T_uebergabe_C:.0f} °C: {p_sat_15:.1f} bar"
      f" -> {p_sat_15 - p_uebergabe_bar:.1f} bar Abstand bis zur Kondensation")
print(f"  Taupunkt bei {p_uebergabe_bar:.0f} bar: {T_tau_30:.1f} °C"
      f" -> {T_uebergabe_C - T_tau_30:.1f} K überhitzt")

# ---- 3) Phasengrenzen (für das Diagramm) ------------------------------------
T_saett = np.linspace(T_tripel, T_krit, 200)
p_saett_bar = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_saett]) / 1e5
T_saett_C = T_saett - 273.15
T_krit_C, T_tripel_C = T_krit - 273.15, T_tripel - 273.15
p_krit_bar, p_tripel_bar = p_krit / 1e5, p_tripel / 1e5


# Sublimations- und Schmelzlinie wie in Szenario 1 (Span & Wagner 1996)
def sublimation_bar(T_K):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / T_tripel
    return p_tripel_bar * np.exp((T_tripel / T_K) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K):
    x = T_K / T_tripel - 1.0
    return p_tripel_bar * (1.0 + 1955.5390 * x + 2055.4593 * x**2)


Tmin, Tmax = -80.0, 100.0
Pmin, Pmax = 0.0, 130.0

T_sub = np.linspace(Tmin + 273.15, T_tripel, 150)
p_sub_bar, T_sub_C = sublimation_bar(T_sub), T_sub - 273.15
T_melt = np.linspace(T_tripel, T_tripel * 1.02, 100)
p_melt_bar, T_melt_C = schmelz_bar(T_melt), T_melt - 273.15

# ---- 4) Plot ---------------------------------------------------------------
C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, COL_GAS, COL_FLUE, COL_SUP, ROT = "#5F2176", "#164a73", "#007335", "#a3480b", "#CA220E"
BLAU = "#0476D9"   # Farbe von Szenario 2 in der Excel

fig, ax = plt.subplots(figsize=(8.5, 6.5))

gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, p_krit_bar), (T_krit_C, p_krit_bar)]
gas += list(zip(T_saett_C[::-1], p_saett_bar[::-1]))
gas += list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))

fest = [(Tmin, Pmax), (T_melt_C[-1], p_melt_bar[-1])]
fest += list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
fest += list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(fest, closed=True, fc=C_FEST, ec="none", zorder=0))

flue = list(zip(T_saett_C, p_saett_bar)) + [(T_krit_C, Pmax)]
flue += [(T_melt_C[-1], Pmax)] + list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))

ax.add_patch(plt.Rectangle((T_krit_C, p_krit_bar), Tmax - T_krit_C, Pmax - p_krit_bar,
                           fc=C_SUP, ec="none", zorder=0))

ax.plot(T_sub_C, p_sub_bar, color="#333333", lw=1.8, zorder=3, label="Sublimationslinie")
ax.plot(T_saett_C, p_saett_bar, color="#00304F", lw=1.8, zorder=3, label="Sättigungslinie")
ax.plot(T_melt_C, p_melt_bar, color=COL_FEST, lw=1.8, zorder=3, label="Schmelzlinie")

ax.plot(T_krit_C, p_krit_bar, "o", color=ROT, ms=8, zorder=5)
ax.annotate(f"kritischer Punkt\n{T_krit_C:.1f} °C / {p_krit_bar:.1f} bar",
            (T_krit_C, p_krit_bar), textcoords="offset points", xytext=(10, -28),
            fontsize=9, color=ROT)
ax.plot(T_tripel_C, p_tripel_bar, "o", color="black", ms=7, zorder=5)
ax.annotate(f"Tripelpunkt\n{T_tripel_C:.1f} °C / {p_tripel_bar:.2f} bar",
            (T_tripel_C, p_tripel_bar), textcoords="offset points", xytext=(8, 12), fontsize=9)

box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75)
ax.text(-67, 100, "fest\n(Trockeneis)", fontsize=9.5, color=COL_FEST, weight="bold", ha="center", bbox=box)
ax.text(65, 15, "gasförmig", fontsize=12, color=COL_GAS, weight="bold", ha="center", bbox=box)
ax.text(-5, 105, "flüssig", fontsize=12, color=COL_FLUE, weight="bold", ha="center", bbox=box)
ax.text(65, 118, "überkritisch", fontsize=12, color=COL_SUP, weight="bold", ha="center", bbox=box)

# Abstand zur Sättigungslinie bei 15 °C als gestrichelte Hilfslinie
ax.plot([T_uebergabe_C, T_uebergabe_C], [p_uebergabe_bar, p_sat_15], ls=":", color="#555555", lw=1.2, zorder=4)
ax.plot(T_uebergabe_C, p_uebergabe_bar, "s", color=BLAU, ms=10, zorder=6,
        markeredgecolor="black", markeredgewidth=0.8)
ax.annotate(f"Netzübergabe S2\n{T_uebergabe_C:.0f} °C / {p_uebergabe_bar:.0f} bar\n({phase})",
            (T_uebergabe_C, p_uebergabe_bar),
            textcoords="offset points", xytext=(12, -38), fontsize=9, weight="bold")
ax.annotate(f"p_sat({T_uebergabe_C:.0f} °C) = {p_sat_15:.1f} bar",
            (T_uebergabe_C, p_sat_15), textcoords="offset points", xytext=(-150, 4), fontsize=8.5, color="#555555")

ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("CO2 p-T-Diagramm - Startpunkt der Prozesskette (Szenario 2)")
ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25, zorder=1)

fig.tight_layout()
fig.savefig("abb_startpunkt_netzuebergabe_S2.png", dpi=175)
print("\ngespeichert: abb_startpunkt_netzuebergabe_S2.png")
