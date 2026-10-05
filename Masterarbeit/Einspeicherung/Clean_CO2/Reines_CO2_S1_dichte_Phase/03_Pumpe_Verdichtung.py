# -*- coding: utf-8 -*-
"""
Schritt 2 - Pumpe: Netzübergabe -> Bohrlochkopf (Szenario 1, dichte Phase)
============================================================================
Eingangszustand: 91 bar / 15 °C, unverändert aus Schritt 01_02

Der Zieldruck der Pumpe ergibt sich aus der Kaverne: der Bohrlochkopfdruck, bei dem die Gassäule (1200 m) am
Kavernenboden genau den zulässigen Maximaldruck erreicht. Deshalb wird die
Gassäule hier zuerst gerechnet, bevor die Pumpe gerechnet werden kann - auch
wenn die Gassäule im Blockfließbild erst danach kommt.

Gerechnet wird von unten nach oben: unten ist der Druck bekannt (210 bar),
das Ergebnis oben ist direkt der Kopfdruck - kein Sekantenverfahren nötig.
Gleicher Rechenweg wie in Stillstand_gassaeule_Kaverne_Version1.py und in der
Excel-Rechenübersicht, deshalb überall 107,60 bar. (Früher wurde von oben
nach unten mit Sekante gerechnet -> 107,58 bar. Der Unterschied kommt nur
von der Schrittweite 2 m; mit 0,2 m liefern beide Richtungen 107,59 bar.)

Kaverne Version 1 - Randbedingungen (siehe Handbuch_Einspeicherung.docx, Kap. 5):
Teufe 1200 m, p_max (LCCS) 210 bar, Gebirge 10 °C + 0,03 K/m.
Grob abgeleitet aus Q-028 (Buzogany & Kruck 2022), Q-029/Q-030 (DBI-Studien
für Uniper) als plausible Zwischengröße für eine mitteleuropäische
Salzkaverne, abgestimmt mit Martina. Keine exakte Übernahme einer einzelnen Studien-Option.

Eine flachere Kaverne (Version 2) ist ein mögliches weiteres Szenario

Rechenweg Pumpe: isentrope Zustandsänderung (h2s bei gleicher Entropie),
mit Wirkungsgrad eta auf die reale Enthalpieerhöhung skaliert - identisch
zum Ansatz in Kavernenrechner/1_auslegung/co2_kaverne3.py.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI, PhaseSI

# ---- 1) Kaverne Version 1 - Randbedingungen --------------------------------
TEUFE = 1200.0  # m
P_MAX_LCCS = 210.0  # bar, Zieldruck am Kavernenboden
T_OBERFLAECHE = 10.0  # °C, Gebirge an der Oberfläche
GRADIENT = 0.03  # K/m, geothermischer Gradient
G = 9.81  # m/s2


# ---- 2) Zieldruck am Bohrlochkopf: Gassäule von unten nach oben -----------
T_KRIT_C = PropsSI("Tcrit", "CO2") - 273.15


def T_gebirge(z):
    return T_OBERFLAECHE + GRADIENT * z


def dichte(p_bar, T_c):
    """Dichte wie in 04: nahe der Siedelinie wird der Gasast gewählt."""
    T = T_c + 273.15
    p = p_bar * 1e5
    if T_c >= T_KRIT_C:
        return PropsSI("D", "P", p, "T", T, "CO2")
    psat = PropsSI("P", "T", T, "Q", 0, "CO2")
    if abs(p - psat) / psat < 5e-4:
        return PropsSI("D", "T", T, "Q", 1, "CO2")
    return PropsSI("D", "P", p, "T", T, "CO2")


def kopfdruck(p_lccs_bar, n=600):
    """Integriert dp/dz = rho(p,T)*g von der Teufe (LCCS) nach oben zum Kopf."""
    dz = TEUFE / n
    p = p_lccs_bar
    for i in range(n):
        z = TEUFE - i * dz
        p -= dichte(p, T_gebirge(z)) * G * dz / 1e5
    return p


p_kopf_ein = kopfdruck(P_MAX_LCCS)

print("Zieldruck am Bohrlochkopf (aus Gassäule, Kaverne Version 1):")
print(f"  unten: {P_MAX_LCCS:.0f} bar am Kavernenboden in {TEUFE:.0f} m")
print(f"  oben:  {p_kopf_ein:.2f} bar am Bohrlochkopf")

# ---- 3) Pumpe: Netzübergabe -> Bohrlochkopf --------------------------------
p1_bar, T1_C = 91.0, 15.0  # Eingangszustand aus Schritt 01_02
eta = 0.80  # Wirkungsgrad - eigene Annahme, Vergleichswerte in Q-016 (S. 4, Kap. 2.3), herstellerseitig zu bestätigen

h1 = PropsSI("H", "P", p1_bar * 1e5, "T", T1_C + 273.15, "CO2")
s1 = PropsSI("S", "P", p1_bar * 1e5, "T", T1_C + 273.15, "CO2")
h2s = PropsSI("H", "P", p_kopf_ein * 1e5, "S", s1, "CO2")  # isentrop: gleiche Entropie
h2 = h1 + (h2s - h1) / eta  # mit Wirkungsgradverlust
T2_C = PropsSI("T", "P", p_kopf_ein * 1e5, "H", h2, "CO2") - 273.15
phase2 = PhaseSI("P", p_kopf_ein * 1e5, "H", h2, "CO2")
w_spez = (h2 - h1) / 1000.0  # kJ/kg

print("\nPumpe:")
print(f"  ein:  {p1_bar:.1f} bar / {T1_C:.1f} °C")
print(f"  aus:  {p_kopf_ein:.2f} bar / {T2_C:.2f} °C  ({phase2})")
print(f"  spezifische Arbeit: {w_spez:.2f} kJ/kg")

# ---- Durchsatz und Pumpenleistung ------------------------------------------
# Bandbreite mit Martina abgestimmt: 50.000-100.000 Nm3/h (Normzustand
# 0 degC, 1,01325 bar) - identisch zu V_norm_min/max in co2_kaverne3.py.
V_NORM_MIN, V_NORM_MAX = 50000.0, 100000.0  # Nm3/h


def massenstrom(V_norm_h):
    rho_n = PropsSI("D", "P", 101325, "T", 273.15, "CO2")
    return V_norm_h * rho_n / 3600.0  # kg/s


m_min, m_max = massenstrom(V_NORM_MIN), massenstrom(V_NORM_MAX)
P_min, P_max = m_min * w_spez, m_max * w_spez  # kW

print(f"  Durchsatz: {V_NORM_MIN:.0f}-{V_NORM_MAX:.0f} Nm3/h -> {m_min:.1f}-{m_max:.1f} kg/s")
print(f"  Pumpenleistung: {P_min:.1f}-{P_max:.1f} kW")

# ---- 4) Diagramm: Startpunkt -> Pumpenaustritt -----------------------------
T_krit = PropsSI("Tcrit", "CO2")
p_krit = PropsSI("Pcrit", "CO2")
T_tripel = PropsSI("Ttriple", "CO2")
p_tripel = PropsSI("ptriple", "CO2")
T_krit_C, T_tripel_C = T_krit - 273.15, T_tripel - 273.15
p_krit_bar, p_tripel_bar = p_krit / 1e5, p_tripel / 1e5

T_saett = np.linspace(T_tripel, T_krit, 200)
p_saett_bar = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_saett]) / 1e5
T_saett_C = T_saett - 273.15


# Sublimations- und Schmelzlinie wie in 01_02 (Span & Wagner 1996)
def sublimation_bar(T_K):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / T_tripel
    return p_tripel_bar * np.exp((T_tripel / T_K) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K):
    x = T_K / T_tripel - 1.0
    return p_tripel_bar * (1.0 + 1955.5390 * x + 2055.4593 * x**2)


# Achsen und Farben wie Diagramm 1 im Blatt "Phasendiagramm" der Excel
Tmin, Tmax = -80.0, 100.0
Pmin, Pmax = 0.0, 130.0

T_sub = np.linspace(Tmin + 273.15, T_tripel, 150)
p_sub_bar, T_sub_C = sublimation_bar(T_sub), T_sub - 273.15
T_melt = np.linspace(T_tripel, T_tripel * 1.02, 100)
p_melt_bar, T_melt_C = schmelz_bar(T_melt), T_melt - 273.15

C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, COL_GAS, COL_FLUE, COL_SUP, ROT = "#5F2176", "#164a73", "#007335", "#a3480b", "#CA220E"

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
ax.plot(T_tripel_C, p_tripel_bar, "o", color="black", ms=7, zorder=5)
ax.plot(T_krit_C, p_krit_bar, "o", color=ROT, ms=8, zorder=5)

box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75)
ax.text(-67, 100, "fest\n(Trockeneis)", fontsize=9.5, color=COL_FEST, weight="bold", ha="center", bbox=box)
ax.text(65, 15, "gasförmig", fontsize=12, color=COL_GAS, weight="bold", ha="center", bbox=box)
ax.text(-5, 105, "flüssig", fontsize=12, color=COL_FLUE, weight="bold", ha="center", bbox=box)
ax.text(65, 118, "überkritisch", fontsize=12, color=COL_SUP, weight="bold", ha="center", bbox=box)

# Start- und Endpunkt der Pumpe, mit Pfeil dazwischen
ax.annotate("", xy=(T2_C, p_kopf_ein), xytext=(T1_C, p1_bar),
            arrowprops=dict(arrowstyle="->", color="black", lw=2), zorder=6)
ax.plot(T1_C, p1_bar, "s", color=COL_FLUE, ms=10, zorder=7, mec="black", mew=0.8)
ax.annotate(f"Netzübergabe\n{T1_C:.0f} °C / {p1_bar:.0f} bar",
            (T1_C, p1_bar), textcoords="offset points", xytext=(-95, -10), fontsize=9, weight="bold")
ax.plot(T2_C, p_kopf_ein, "^", color=COL_FLUE, ms=11, zorder=7, mec="black", mew=0.8)
ax.annotate(f"Bohrlochkopf (nach Pumpe)\n{T2_C:.1f} °C / {p_kopf_ein:.1f} bar",
            (T2_C, p_kopf_ein), textcoords="offset points", xytext=(10, 10), fontsize=9, weight="bold")

ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("CO2 p-T-Diagramm - Schritt 2: Pumpe (Szenario 1)")
ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
ax.grid(alpha=0.25, zorder=1)

fig.tight_layout()
fig.savefig("abb_pumpe.png", dpi=175)
print("\ngespeichert: abb_pumpe.png")