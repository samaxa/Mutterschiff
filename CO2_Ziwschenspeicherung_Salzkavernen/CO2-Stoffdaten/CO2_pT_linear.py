"""
Extra: CO2-p-T-Phasendiagramm mit LINEARER Druckachse (statt logarithmisch).

Gleicher Inhalt wie das CO2-Diagramm im Hauptskript, nur die y-Achse ist
linear (0 - 250 bar). Dadurch sieht man die Drucksprünge "echt" - allerdings
wird der Bereich unter ~10 bar (Sublimation, Tripelpunkt) stark gestaucht.

Ausfuehren mit Python 3.10:
    py -3.10 CO2_pT_linear.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from CoolProp.CoolProp import PropsSI


SAVE_PNG = True

# ---- Referenzpunkte ----
T_triple_K = 216.592
T_triple_C = T_triple_K - 273.15
P_triple_bar = 5.1795
T_crit_K = PropsSI("Tcrit", "CO2")
T_crit_C = T_crit_K - 273.15
P_crit_bar = PropsSI("Pcrit", "CO2") / 1e5

# ---- Plotgrenzen ----
Tmin, Tmax = -100.0, 60.0
Pmin, Pmax = 0.0, 250.0          # LINEAR: Start bei 0 bar


# ---- Phasengrenzen ----
def sublimation_pressure_bar(T_K):
    T_K = np.asarray(T_K, dtype=float)
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / T_triple_K
    ex = T_triple_K / T_K * (a1 * th + a2 * th**1.9 + a3 * th**2.9)
    return P_triple_bar * np.exp(ex)


def melting_pressure_bar(T_K):
    T_K = np.asarray(T_K, dtype=float)
    a1, a2 = 1955.5390, 2055.4593
    x = T_K / T_triple_K - 1.0
    return P_triple_bar * (1.0 + a1 * x + a2 * x**2)


T_sub_K = np.linspace(173.15, T_triple_K, 500)
T_sub_C = T_sub_K - 273.15
P_sub = sublimation_pressure_bar(T_sub_K)

T_sat_in = np.linspace(T_triple_K + 0.01, T_crit_K - 0.01, 500)
P_sat_in = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_sat_in])
T_sat_C = np.concatenate(([T_triple_K], T_sat_in, [T_crit_K])) - 273.15
P_sat = np.concatenate(([P_triple_bar], P_sat_in, [P_crit_bar]))

a1, a2 = 1955.5390, 2055.4593
tgt = Pmax / P_triple_bar - 1.0
x_top = (-a1 + np.sqrt(a1**2 + 4.0 * a2 * tgt)) / (2.0 * a2)
T_melt_K = np.linspace(T_triple_K, T_triple_K * (1.0 + x_top), 400)
T_melt_C = T_melt_K - 273.15
P_melt = melting_pressure_bar(T_melt_K)


# ---- Entspannungspfad (deine Excel-Werte) ----
P_path = np.array([210, 200, 190, 180, 170, 160, 150, 140, 130, 120,
                   110, 100, 90, 80, 70, 60, 50, 40, 30], dtype=float)
T_path = np.array([50.0, 49.299, 48.537, 47.707, 46.801, 45.809, 44.72,
                   43.518, 42.185, 40.697, 39.021, 37.113, 34.9, 32.26,
                   28.683, 21.978, 14.284, 5.3, -5.552], dtype=float)
h0 = PropsSI("H", "T", 50 + 273.15, "P", 210e5, "CO2")
Q_path = np.array([PropsSI("Q", "P", p * 1e5, "H", h0, "CO2") for p in P_path])
twp = (Q_path >= 0) & (Q_path <= 1)


# ---- Plot ----
fig, ax = plt.subplots(figsize=(13, 9))

COL_GAS, COL_LIQ, COL_SUP, COL_SOL = "#b9d7f0", "#b8d8a8", "#f4c7a1", "#a8a8c8"

gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, P_crit_bar), (T_crit_C, P_crit_bar)]
gas += list(zip(T_sat_C[::-1], P_sat[::-1]))
gas += list(zip(T_sub_C[::-1], P_sub[::-1]))
ax.add_patch(Polygon(gas, closed=True, facecolor=COL_GAS, edgecolor="none", alpha=0.55))

sol = [(Tmin, Pmax), (T_melt_C[-1], P_melt[-1])]
sol += list(zip(T_melt_C[::-1], P_melt[::-1]))
sol += list(zip(T_sub_C[::-1], P_sub[::-1]))
ax.add_patch(Polygon(sol, closed=True, facecolor=COL_SOL, edgecolor="none", alpha=0.55))

liq = [(T_melt_C[-1], Pmax), (T_crit_C, Pmax)]
liq += list(zip(T_sat_C[::-1], P_sat[::-1]))
liq += list(zip(T_melt_C, P_melt))
ax.add_patch(Polygon(liq, closed=True, facecolor=COL_LIQ, edgecolor="none", alpha=0.55))

sup = [(T_crit_C, P_crit_bar), (Tmax, P_crit_bar), (Tmax, Pmax), (T_crit_C, Pmax)]
ax.add_patch(Polygon(sup, closed=True, facecolor=COL_SUP, edgecolor="none", alpha=0.55))

# Grenzlinien
ax.plot(T_sub_C, P_sub, color="#303030", linewidth=2.0, label="Sublimationslinie")
ax.plot(T_sat_C, P_sat, color="#0b4f8a", linewidth=2.4, label="Sättigungslinie")
ax.plot(T_melt_C, P_melt, color="#5d3a7e", linewidth=2.0, label="Schmelzlinie")

# Punkte
ax.scatter(T_triple_C, P_triple_bar, color="black", s=55, zorder=10)
ax.annotate(f"Tripelpunkt\n{T_triple_C:.1f} °C | {P_triple_bar:.2f} bar",
            xy=(T_triple_C, P_triple_bar), xytext=(-55, 30),
            arrowprops=dict(arrowstyle="->", color="black"), fontsize=9)
ax.scatter(T_crit_C, P_crit_bar, color="#c00000", s=55, zorder=10)
ax.annotate(f"krit. Punkt\n{T_crit_C:.1f} °C | {P_crit_bar:.1f} bar",
            xy=(T_crit_C, P_crit_bar), xytext=(34, 92),
            arrowprops=dict(arrowstyle="->", color="#c00000"),
            fontsize=9, color="#c00000")

# Entspannungspfad
ax.plot(T_path, P_path, "-", color="#c43c39", linewidth=3, zorder=12,
        label="Entspannung CO2 (isenthalp)")
ax.scatter(T_path[~twp], P_path[~twp], color="#c43c39", s=42, zorder=13)
ax.scatter(T_path[twp], P_path[twp], facecolor="white", edgecolor="#c43c39",
           s=52, linewidth=1.6, zorder=13, label="zweiphasig (auf Sättigungslinie)")
for i in range(0, len(T_path) - 1, 2):
    ax.annotate("", xy=(T_path[i + 1], P_path[i + 1]),
                xytext=(T_path[i], P_path[i]),
                arrowprops=dict(arrowstyle="->", color="#8b1a1a", linewidth=1.4),
                zorder=14)

# Beschriftungen
for x, y, txt, col in [(-86, 150, "fest\nTrockeneis", "#35355f"),
                       (-20, 20, "gasförmig", "#164a73"),
                       (-8, 120, "flüssig", "#3f702d"),
                       (48, 200, "superkritisch", "#a3480b")]:
    ax.text(x, y, txt, fontsize=13, ha="center", color=col,
            bbox=dict(facecolor="white", alpha=0.6, edgecolor="none"))

ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.set_xlabel("Temperatur (°C)", fontsize=13)
ax.set_ylabel("Druck (bar, lineare Skala)", fontsize=13)
ax.set_title("CO2 p-T-Phasendiagramm der isenthalpen Entspannung\n"
             "(lineare Druckachse)", fontsize=15)
ax.set_yticks(np.arange(0, 251, 25))
ax.grid(True, alpha=0.25)
ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
fig.tight_layout()

if SAVE_PNG:
    fig.savefig("CO2_pT_Phasendiagramm_linear.png", dpi=200, bbox_inches="tight")
    print("gespeichert: CO2_pT_Phasendiagramm_linear.png")

plt.show()
