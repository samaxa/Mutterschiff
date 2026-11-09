# -*- coding: utf-8 -*-
"""
Folienabbildung: Zustand am Bohrlochkopf beim Ausspeichern (reines CO₂, Strang adiabat)
und Zielkonflikt Mindestdruck.

Liest kavernenzyklus.json und arbeitsgas.json aus diesem Ordner und rechnet für jeden
gespeicherten Zeitschritt des Ausspeicherns (alle 0,2 d) den Kopfzustand mit
kaverne_bausteine.strang_aufwaerts, also feiner als die 14 Stützstellen in bohrlochkopf.json.
Jeder Punkt der Linie ist ein Zeitpunkt: Start oben rechts (Kaverne voll), dann entlang der
Siedelinie nach unten.

Ausgabe: abb_folie_kopf_ausspeichern.png
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
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402

MED, KAV = kb.REIN, kb.TIEF
ST = "Stillstand 21,67 d (Q-028)"
NAVY, BLAU, ORANGE, ROT, GRAU = "#0B2A4A", "#1F6FD1", "#E8A33D", "#CA220E", "#7F7F7F"

Z = json.load(open(ORDNER / "kavernenzyklus.json", encoding="utf-8"))
A = json.load(open(ORDNER / "arbeitsgas.json", encoding="utf-8"))


def kopfpfad(rate):
    vl = [x for x in Z["zyklen"][f"S2|{rate}|{ST}"]["verlauf"] if x["art"] == "aus" and x["m_dot"] < 0]
    out = []
    for x in vl:
        h_u = kb.h_dampf(MED, x["p_lccs"]) if x["q"] is not None else None
        _, k = kb.strang_aufwaerts(MED, KAV, x["p_lccs"], x["T"], -x["m_dot"], n=300, h_unten=h_u)
        if k is not None:
            out.append(dict(t=x["t"], p=k["p"], T=k["T"], q=k["q"]))
    return out


pfad = {r: kopfpfad(r) for r in ("100.000 Nm³/h", "50.000 Nm³/h")}
for r, P in pfad.items():
    i = int(np.argmin([k["T"] for k in P]))
    print(f"{r}: Start {P[0]['p']:.1f} bar / {P[0]['T']:.1f} °C, kältester Punkt Tag {P[i]['t']:.1f}: "
          f"{P[i]['p']:.1f} bar / {P[i]['T']:.1f} °C, Dampf {P[i]['q']}, Ende {P[-1]['p']:.1f} bar / {P[-1]['T']:.1f} °C, "
          f"p {min(k['p'] for k in P):.1f}-{max(k['p'] for k in P):.1f} bar, "
          f"T {min(k['T'] for k in P):.1f}-{max(k['T'] for k in P):.1f} °C")

# ---- Abbildung ---------------------------------------------------------------------------------
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(8.3, 4.4), dpi=300, gridspec_kw=dict(width_ratios=[1.75, 1]))

T_K, P_K = PropsSI("Tcrit", "CO2") - 273.15, PropsSI("pcrit", "CO2") / 1e5
Ts = np.linspace(-5, T_K - 0.01, 200)
ps = [PropsSI("P", "T", t + 273.15, "Q", 0, "CO2") / 1e5 for t in Ts]
xmin, xmax, ymin, ymax = 0, 45, 20, 130
ax.fill_between([xmin, T_K], P_K, ymax, color="#DCEBDD", lw=0)
ax.fill_between(np.r_[Ts, T_K], np.r_[ps, P_K], ymax, where=None, color="#DCEBDD", lw=0)
ax.fill_between([T_K, xmax], P_K, ymax, color="#FBE5D3", lw=0)
ax.plot(Ts, ps, color=NAVY, lw=2.2, alpha=0.85)
ax.text(8.5, 35.2, "Siedelinie = zweiphasig", rotation=13, color=NAVY, fontsize=7, weight="bold")
ax.text(1, 126, "flüssig / dicht", color="#4E7A55", weight="bold", va="top")
ax.text(36.5, 126, "überkritisch", color="#B3651B", weight="bold", va="top")
ax.text(33, 28, "gasförmig", color=GRAU, weight="bold")
ax.plot(T_K, P_K, "o", color=ROT, ms=5, zorder=5)

for r, ls in (("100.000 Nm³/h", "-"), ("50.000 Nm³/h", ":")):
    P = pfad[r]
    ax.plot([k["T"] for k in P], [k["p"] for k in P], color=NAVY, lw=1.6, ls=ls, label=f"Kopf beim Ausspeichern, {r}")
    sel = P[::max(1, len(P) // 14)] + [P[-1]]
    for k in sel:
        ax.plot(k["T"], k["p"], "o", ms=4.5, mec="white", mew=0.6,
                color=ORANGE if k["q"] is not None else NAVY, zorder=4)
ax.plot([], [], "o", color=ORANGE, ms=4.5, label="zweiphasig am Kopf")
ax.plot([], [], "o", color=NAVY, ms=4.5, label="einphasig am Kopf")

P = pfad["100.000 Nm³/h"]
s = P[0]
ax.annotate(f"Start (voll):\n{s['p']:.0f} bar / {s['T']:.0f} °C,\ndicht", (s["T"], s["p"]), (35.0, 86),
            fontsize=6.8, color=NAVY, weight="bold", arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.7))
i = int(np.argmin([k["T"] for k in P]))
k = P[i]
ax.plot(k["T"], k["p"], "o", ms=5, color=ORANGE, mec=NAVY, mew=0.9, zorder=6)
de = lambda x: f"{x:.1f}".replace(".", ",")
ax.annotate(f"100.000 Nm³/h: kältester Punkt\n{de(k['p'])} bar / {de(k['T'])} °C, {100*k['q']:.0f} % Dampf",
            (k["T"], k["p"]), (1, 24), fontsize=6.8, color=NAVY, arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.7))
e = pfad["50.000 Nm³/h"][-1]
ax.annotate("Ende (70 bar unten):\nwieder fast nur Gas", (e["T"], e["p"]), (25, 37), fontsize=6.8, color=NAVY,
            arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.7))

ax.set(xlim=(xmin, xmax), ylim=(ymin, ymax), xlabel="Temperatur am Kopf [°C]", ylabel="Druck am Kopf [bar]")
ax.set_title("Zustand am Kopf beim Ausspeichern\n(reines CO₂, Strang adiabat)", loc="left", fontsize=8.5,
             weight="bold", color=NAVY)
ax.legend(loc="upper left", fontsize=6.2, bbox_to_anchor=(0.0, 0.94), framealpha=0.95)

# ---- Zielkonflikt Mindestdruck ------------------------------------------------------------------
v = {round(x["p_min"]): x for x in A["varianten"]}
v70, v172 = v[70], min(A["varianten"], key=lambda x: abs(x["p_min"] - 172))
werte = [v70["WGV_iso"] / 1e3, v172["WGV_iso"] / 1e3]
ax2.bar([0, 1], werte, color=[BLAU, ORANGE], width=0.55)
for x, w, a in zip([0, 1], werte, [v70["anteil_iso"], v172["anteil_iso"]]):
    ax2.text(x, w + 8, f"rund {round(w, -1 if w > 100 else 0):.0f} kt\n{100*a:.0f} % vom Inhalt",
             ha="center", fontsize=7, weight="bold", color=NAVY)
ax2.text(1.33, 490, f"Inhalt voll {A['TGV']/1e3:.0f} kt\nim Zyklus: 380 kt", ha="right", va="top", fontsize=6.5, color=GRAU)
ax2.set_xticks([0, 1])
ax2.set_xticklabels(["Mindestdruck\n70 bar", "Mindestdruck\n172 bar"], fontsize=7)
ax2.set(xlim=(-0.6, 1.4), ylim=(0, 500), ylabel="Arbeitsgas je Zyklus [kt]")
ax2.set_title("Zielkonflikt\nMindestdruck", loc="left", fontsize=8.5, weight="bold", color=NAVY)
ax2.text(0, -95, "Kopf meist\nzweiphasig", ha="center", color=ROT, fontsize=7)
ax2.text(1, -95, "dicht, aber\nkaum nutzbar", ha="center", color=ROT, fontsize=7)
for a in (ax, ax2):
    a.grid(alpha=0.25)

fig.tight_layout()
fig.savefig(ORDNER / "abb_folie_kopf_ausspeichern.png", bbox_inches="tight")
print("gespeichert: abb_folie_kopf_ausspeichern.png")
