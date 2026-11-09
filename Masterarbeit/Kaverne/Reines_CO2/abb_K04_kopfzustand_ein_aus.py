# -*- coding: utf-8 -*-
"""
Abbildung für die Masterarbeit: Zustände am Bohrlochkopf, links Einspeichern, rechts Ausspeichern
(reines CO₂, Strang adiabat). Ersetzt in der Arbeit abb_K04_kopfzustand_pT.png, ohne die
Bezugslinien 91 bar und 30 bar.

Liest bohrlochkopf.json aus diesem Ordner (Schritt 04, je Rate 14 Stützstellen) und rechnet nur
noch die Sättigungslinie, eine Drossellinie zur Erklärung und die Hydratgrenze dazu:
  links:  Kopf nach Pumpe bzw. Drossel für S1 und S2; dazu die isenthalpe Drosselung des
          S1-Lieferzustands (91 bar / 15 °C) auf den Kopfdruck bei leerer Kaverne. Sie zeigt,
          warum der Kopf beim Einspeichern auf der Sättigungslinie liegt.
  rechts: Kopf beim Ausspeichern; Hydratgrenze nach ausspeichergas.T_hydrat (Näherung zwischen
          den Quadrupelpunkten, oberhalb fast senkrecht, Q-099 Folie 20).

Ausgabe: abb_K04_kopfzustand_ein_aus.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Ausspeichergas"))
import ausspeichergas as ag   # noqa: E402  (T_hydrat)

NAVY, GRUEN, BLAU, ROT, GRAU = "#0B2A4A", "#1B7A3A", "#1F6FD1", "#CA220E", "#8C8C8C"
R50, R100 = "50.000 Nm³/h", "100.000 Nm³/h"
B = json.load(open(ORDNER / "bohrlochkopf.json", encoding="utf-8"))
de = lambda x, n=1: f"{x:.{n}f}".replace(".", ",")

# Sättigungslinie und kritischer Punkt
T_K, P_K = PropsSI("Tcrit", "CO2") - 273.15, PropsSI("pcrit", "CO2") / 1e5
Ts = np.linspace(-25, T_K - 0.01, 300)
ps = np.array([PropsSI("P", "T", t + 273.15, "Q", 0, "CO2") / 1e5 for t in Ts])

# Isenthalpe Drosselung des S1-Lieferzustands auf den Kopfdruck bei leerer Kaverne (50.000 Nm³/h)
S1 = B["einspeisen"][f"S1|{R50}"]["punkte"]
p_leer = S1[0]["kopf"]["p"]
h_S1 = PropsSI("H", "P", 91e5, "T", 15 + 273.15, "CO2")
p_dr = np.linspace(91, p_leer, 200)
T_dr = [PropsSI("T", "P", p * 1e5, "H", h_S1, "CO2") - 273.15 for p in p_dr]
q_leer = PropsSI("Q", "P", p_leer * 1e5, "H", h_S1, "CO2")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
fig, (axE, axA) = plt.subplots(1, 2, figsize=(8.2, 4.3), dpi=250, sharey=True)
for ax in (axE, axA):
    lab = ax is axA
    ax.plot(Ts, ps, color=GRAU, lw=1.6, label="Sättigungslinie reines CO₂" if lab else None)
    ax.plot(T_K, P_K, "o", color=GRAU, mfc="white", ms=5, zorder=5, label="kritischer Punkt" if lab else None)
    ax.set(xlim=(-25, 45), ylim=(0, 140), xlabel="Temperatur am Kopf [°C]")
    ax.grid(alpha=0.3)
axE.set_ylabel("Druck am Kopf [bar]")

# ---- links: Einspeichern -----------------------------------------------------------------------
for sz, farbe in (("S1", GRUEN), ("S2", BLAU)):
    for r, ls in ((R50, ":"), (R100, "-")):
        P = B["einspeisen"][f"{sz}|{r}"]["punkte"]
        axE.plot([x["kopf"]["T"] for x in P], [x["kopf"]["p"] for x in P], ls=ls, marker="s", ms=3.2,
                 color=farbe, lw=1.3, label=f"{sz}, {r}")
axE.plot(15, 91, "s", ms=6, mfc="white", mec=GRUEN, mew=1.4, zorder=6)
axE.annotate("S1 Übergabe\n91 bar / 15 °C", (15, 91), (-23, 96), fontsize=6.5, color=GRUEN,
             arrowprops=dict(arrowstyle="-", color=GRUEN, lw=0.7))
axE.plot(26, 91, "s", ms=6, mfc="white", mec=BLAU, mew=1.4, zorder=6)
axE.annotate("S2 nach Kühler\n91 bar / 26 °C", (26, 91), (30, 96), fontsize=6.5, color=BLAU,
             arrowprops=dict(arrowstyle="-", color=BLAU, lw=0.7))
axE.plot(T_dr, p_dr, ls="--", color=ROT, lw=1.0, label="Drosseln S1 (Isenthalpe)")
k0 = S1[0]["kopf"]
axE.annotate(f"Kaverne leer: Kopf braucht nur {de(k0['p'])} bar\n"
             f"→ gedrosselt auf {de(k0['T'])} °C, {100*q_leer:.0f} % Dampf",
             (k0["T"], k0["p"]), (-23, 4), fontsize=6.5, color=ROT,
             arrowprops=dict(arrowstyle="-", color=ROT, lw=0.7))
k1 = S1[-1]["kopf"]
axE.annotate(f"Kaverne voll: Pumpe\nauf {de(k1['p'])} bar", (k1["T"], k1["p"]), (-12, 124), fontsize=6.5,
             color=GRUEN, arrowprops=dict(arrowstyle="-", color=GRUEN, lw=0.7))
axE.set_title("Einspeichern: Kopf nach Pumpe bzw. Drossel", loc="left", fontsize=8.5, weight="bold",
              color=NAVY)
axE.legend(loc="lower right", fontsize=5.8, framealpha=0.95)

# ---- rechts: Ausspeichern ----------------------------------------------------------------------
pH = np.linspace(15, 140, 300)
axA.plot([ag.T_hydrat(p) for p in pH], pH, ls="--", color=ROT, lw=1.2,
         label="Hydratgrenze mit freiem Wasser (genähert)")
for r, ls in ((R50, ":"), (R100, "-")):
    P = B["ausspeisen"][r]["punkte"]
    axA.plot([x["kopf"]["T"] for x in P], [x["kopf"]["p"] for x in P], ls=ls, marker="o", ms=3.4,
             color=NAVY, lw=1.3, label=f"Ausspeichern, {r}")
    unter = [x for x in P if x["kopf"]["T"] < ag.T_hydrat(x["kopf"]["p"])]
    if unter:
        axA.plot([x["kopf"]["T"] for x in unter], [x["kopf"]["p"] for x in unter], "o", ms=4.5,
                 color=ROT, zorder=6)
axA.plot([], [], "o", color=ROT, ms=4.5, label="Kopf unter der Hydratgrenze")
s = B["ausspeisen"][R50]["punkte"][0]["kopf"]
axA.annotate(f"Kaverne voll:\n{de(s['p'])} bar / {de(s['T'])} °C", (s["T"], s["p"]), (24, 126),
             fontsize=6.5, color=NAVY, arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.7))
for r, xy in ((R100, (-23, 5)), (R50, (17, 18))):
    P = B["ausspeisen"][r]["punkte"]
    k = min(P, key=lambda x: x["kopf"]["T"])["kopf"]
    axA.annotate(f"{r}: kältester Punkt\n{de(k['T'])} °C bei {de(k['p'])} bar", (k["T"], k["p"]), xy,
                 fontsize=6.5, color=NAVY, arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.7))
axA.set_title("Ausspeichern: Kopf vor der Aufbereitung", loc="left", fontsize=8.5, weight="bold",
              color=NAVY)
axA.legend(loc="upper left", fontsize=5.8, framealpha=0.95)

fig.tight_layout()
fig.savefig(ORDNER / "abb_K04_kopfzustand_ein_aus.png", bbox_inches="tight")
print(f"Drosselung S1 leer: 91 bar / 15 °C -> {de(p_leer)} bar / {de(T_dr[-1])} °C, Dampfanteil {de(q_leer, 2)}")
print("gespeichert: abb_K04_kopfzustand_ein_aus.png")
