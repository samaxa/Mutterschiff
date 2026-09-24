# -*- coding: utf-8 -*-
"""
Schritt 0 - Startpunkt der Kette: Netzuebergabe, Szenario 1 (dichte Phase)
============================================================================
in welchem Zustand kommt das CO2 an, und wo liegt es im p-T-Phasendiagramm?

Herkunft der beiden Zahlen
  Druck:       91 bar   - OGE-Notizen 16.09.2026, Punkt 6: Übergabedruck auf
               mindestens 91 bar angehoben (bisher 85 bar), Worst-Case mit
               Verunreinigungen (N2/Ar).

  Temperatur:  15 degC  - Medientemperatur an der Pipeline (Fernleitung),
               keine Gebirgstemperatur.

CoolProp arbeitet intern in SI-Basiseinheiten: Pa statt bar, Kelvin statt
Grad Celsius. Deshalb rechnen in SI.

Schritt 1 (Messtechnik und Filtration): kein Druckverlust, keine
Zustandsänderung angesetzt - der Zustand bleibt 91 bar / 15 °C.

Diagramm: gleiche Farben und Achsen wie Diagramm 1 im Blatt "Phasendiagramm"
der Excel-Rechenübersicht (-80 bis 100 °C, 0 bis 130 bar).
"""
import matplotlib                                   #legt Bild ausgabe in png. fest
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI, PhaseSI      # Importiert Funktionen aus CoolProp. PropsSI: Abfragefunktion für Stoffwerte in SI und PhaseSI liefert Phasenzustand "liquid", "gas" usw.

# ---- 1) Startpunkt ---------------------------------------------------------
p_uebergabe_bar = 91.0
T_uebergabe_C = 15.0

# CoolProp arbeitet in SI-Einheiten: Pa, K, J/kg, Kg/m3.
p_uebergabe = p_uebergabe_bar * 1e5           # bar -> Pa
T_uebergabe = T_uebergabe_C + 273.15          # degC -> K

# ---- 2) Phase und Kennwerte -------------------------------------------------
# Grundform jeder CoolProp-Abfrage:
# PropsSI("gesuchte Groesse", "Zustandsgroesse1", Wert1, "Zustandsgroesse2", Wert2, "Fluid")
phase = PhaseSI("P", p_uebergabe, "T", T_uebergabe, "CO2")
rho = PropsSI("D", "P", p_uebergabe, "T", T_uebergabe, "CO2")   # kg/m3
h = PropsSI("H", "P", p_uebergabe, "T", T_uebergabe, "CO2")     # J/kg

T_krit = PropsSI("Tcrit", "CO2")
p_krit = PropsSI("Pcrit", "CO2")
T_tripel = PropsSI("Ttriple", "CO2")
p_tripel = PropsSI("ptriple", "CO2")

print("Zustand an der Netzuebergabe (Szenario 1):")
print(f"  p = {p_uebergabe_bar:.1f} bar, T = {T_uebergabe_C:.1f} degC")
print(f"  Phase laut CoolProp: {phase}")
print(f"  Dichte:    {rho:.1f} kg/m3")
print(f"  Enthalpie: {h/1000:.1f} kJ/kg")
print(f"  (zum Vergleich: kritischer Punkt {T_krit-273.15:.1f} degC / {p_krit/1e5:.1f} bar)")

# ---- 3) Saettigungslinie (fuer das Diagramm) --------------------------------
# Q=0: Siedelinie, Grenze zur fluessigen Phase.
T_saett = np.linspace(T_tripel, T_krit, 200)
p_saett_bar = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_saett]) / 1e5
T_saett_C = T_saett - 273.15
T_krit_C, T_tripel_C = T_krit - 273.15, T_tripel - 273.15
p_krit_bar, p_tripel_bar = p_krit / 1e5, p_tripel / 1e5

# Sublimationslinie (fest <-> gasförmig, unterhalb des Tripelpunkts) und
# Schmelzlinie (fest <-> flüssig, oberhalb des Tripelpunkts) sind in CoolProp
# für CO2 nicht direkt abfragbar - Korrelationen für Schmelz- und
# Sublimationsdruck nach Span & Wagner (1996). Dieselben Formeln stecken auch
# in der Excel-Rechenübersicht.

def sublimation_bar(T_K):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / T_tripel
    lnp = (T_tripel / T_K) * (a1 * th + a2 * th**1.9 + a3 * th**2.9)
    return p_tripel_bar * np.exp(lnp)


def schmelz_bar(T_K):
    a1, a2 = 1955.5390, 2055.4593
    x = T_K / T_tripel - 1.0
    return p_tripel_bar * (1.0 + a1 * x + a2 * x**2)


Tmin, Tmax = -80.0, 100.0
Pmin, Pmax = 0.0, 130.0

T_sub = np.linspace(Tmin + 273.15, T_tripel, 150)
p_sub_bar = sublimation_bar(T_sub)
T_sub_C = T_sub - 273.15

# Schmelzlinie nach Temperatur, nicht nach Druck, parametrisiert (steil!)
T_melt = np.linspace(T_tripel, T_tripel * 1.02, 100)
p_melt_bar = schmelz_bar(T_melt)
T_melt_C = T_melt - 273.15

# ---- 4) Plot ---------------------------------------------------------------
# Farben aus CO2-Stoffdaten/CO2_Betriebsfenster.py übernommen, damit alle
# Phasendiagramme der Arbeit gleich aussehen.
C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, COL_GAS, COL_FLUE, COL_SUP, ROT = "#5F2176", "#164a73", "#007335", "#a3480b", "#CA220E"

fig, ax = plt.subplots(figsize=(8.5, 6.5))

# Gasfläche: unterhalb Sublimations-/Sättigungslinie, oberhalb T_krit unterhalb p_krit
gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, p_krit_bar), (T_krit_C, p_krit_bar)]
gas += list(zip(T_saett_C[::-1], p_saett_bar[::-1]))
gas += list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))

# Festfläche: unterhalb Sublimations-/Schmelzlinie, links des Tripelpunkts
fest = [(Tmin, Pmax), (T_melt_C[-1], p_melt_bar[-1])]
fest += list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
fest += list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(fest, closed=True, fc=C_FEST, ec="none", zorder=0))

# Flüssigfläche: zwischen Sättigungslinie und Schmelzlinie, unterhalb Pmax
flue = list(zip(T_saett_C, p_saett_bar)) + [(T_krit_C, Pmax)]
flue += [(T_melt_C[-1], Pmax)] + list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))

# Überkritische Fläche: rechts von T_krit, oberhalb p_krit
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
            (T_tripel_C, p_tripel_bar), textcoords="offset points", xytext=(8, 12),
            fontsize=9)

box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75)
ax.text(-67, 100, "fest\n(Trockeneis)", fontsize=9.5, color=COL_FEST, weight="bold", ha="center", bbox=box)
ax.text(65, 15, "gasförmig", fontsize=12, color=COL_GAS, weight="bold", ha="center", bbox=box)
ax.text(-5, 105, "flüssig", fontsize=12, color=COL_FLUE, weight="bold", ha="center", bbox=box)
ax.text(65, 118, "überkritisch", fontsize=12, color=COL_SUP, weight="bold", ha="center", bbox=box)

ax.plot(T_uebergabe_C, p_uebergabe_bar, "s", color=COL_FLUE, ms=10, zorder=6,
        markeredgecolor="black", markeredgewidth=0.8)
ax.annotate(f"Netzübergabe\n{T_uebergabe_C:.0f} °C / {p_uebergabe_bar:.0f} bar\n({phase})",
            (T_uebergabe_C, p_uebergabe_bar),
            textcoords="offset points", xytext=(10, 10), fontsize=9, weight="bold")

ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("CO2 p-T-Diagramm - Startpunkt der Prozesskette (Szenario 1)")
ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25, zorder=1)

fig.tight_layout()
fig.savefig("abb_startpunkt_netzuebergabe.png", dpi=175)
print("\ngespeichert: abb_startpunkt_netzuebergabe.png")