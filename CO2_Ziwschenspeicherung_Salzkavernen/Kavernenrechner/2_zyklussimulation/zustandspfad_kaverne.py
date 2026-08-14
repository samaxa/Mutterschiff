"""
Zustandspfad der Kaverne im p-T-Diagramm - und warum ein Rechteck zu wenig ist.

Zeigt:
  * den tatsaechlich durchlaufenen Zustandspfad der Kaverne ueber einen Zyklus,
    fuer die langsame (55 kg/s) und die schnelle (234 kg/s) Ausspeicherung
  * den zweiphasigen Abschnitt der schnellen Variante
  * zum Vergleich das vereinfachte Rechteck 70-210 bar / 30-60 grad C
  * die Modellkaverne aus Q-002 (CO2START, Abb. 28), die flacher liegt und
    deshalb legitim durch Gas-, Fluessig- und ueberkritisches Gebiet laeuft

Erzeugt: abb9_kaverne_zustandspfad.png

Ausfuehren (im Ordner 2_zyklussimulation):
    py -3.10 zustandspfad_kaverne.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from matplotlib.lines import Line2D
from CoolProp.CoolProp import PropsSI

import zyklus as Z

OUT = "abb9_kaverne_zustandspfad.png"

TC, PC = Z.TC, Z.PC
C_FLUE, C_GAS, C_SUP = "#D9EAD3", "#CFE2F3", "#FCE5CD"
NAVY, ORNG, GREEN, RED = "#00304F", "#EE7203", "#007335", "#CA220E"
MAG, GREY = "#8E44AD", "#777777"

# vereinfachtes Fenster, wie bisher in den Praesentationsbildern verwendet
RECHTECK = dict(T=(30.0, 60.0), p=(70.0, 210.0))
# Modellkaverne aus Q-002 (CO2START), Abb. 28 - Werte aus der Abbildung abgelesen
Q002 = dict(T_inj=(15.0, 85.0), T_prod=(15.0, 40.0), p=(20.0, 140.0), T_init=40.0)

TLIM, PLIM = (8, 92), (0, 235)


def saettigung(n=500):
    T = np.linspace(216.592, PropsSI("Tcrit", "CO2") - 1e-6, n)
    return T - 273.15, PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5


fig, ax = plt.subplots(figsize=(12.6, 7.4))
Ts, ps = saettigung()
t0, t1 = TLIM; p0, p1 = PLIM

ax.add_patch(Rectangle((t0, p0), t1 - t0, p1 - p0, fc=C_GAS, ec="none", zorder=0))
m = Ts >= t0
poly = [(t0, p1), (t0, np.interp(t0, Ts, ps))] + list(zip(Ts[m], ps[m])) + \
       [(TC, PC), (TC, p1)]
ax.add_patch(Polygon(poly, closed=True, fc=C_FLUE, ec="none", zorder=0))
ax.add_patch(Rectangle((TC, PC), t1 - TC, p1 - PC, fc=C_SUP, ec="none", zorder=0))
ax.plot(Ts, ps, color="#1F4E79", lw=2.6, zorder=4)
ax.plot([TC], [PC], "o", ms=9, color=RED, zorder=8)
ax.annotate(f"krit. Punkt\n{TC:.1f} °C | {PC:.1f} bar", (TC, PC),
            textcoords="offset points", xytext=(44, -58), fontsize=10,
            color=RED, weight="bold", zorder=12,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.88),
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))

box = dict(boxstyle="round,pad=0.24", fc="white", ec="none", alpha=0.78)
ax.text(10, 218, "flüssig", fontsize=12, color=GREEN, weight="bold", bbox=box, zorder=6)
ax.text(46, 226, "überkritisch", fontsize=12, color=ORNG, weight="bold",
        ha="center", bbox=box, zorder=6)
ax.text(20, 8, "gasförmig", fontsize=12, color="#1F4E79", weight="bold",
        ha="center", bbox=box, zorder=6)

# ---- Vergleichsfenster ----------------------------------------------------
t0q, t1q = Q002["T_inj"]; p0q, p1q = Q002["p"]
ax.add_patch(Rectangle((t0q, p0q), t1q - t0q, p1q - p0q, fc=GREY, ec=GREY,
                       alpha=0.10, lw=2.0, ls=(0, (6, 4)), zorder=2))
ax.annotate("Modellkaverne Q-002 (CO₂START, Abb. 28)\n20 – 140 bar · ca. 15 – 85 °C\n"
            "flacher gelegen → quert Gas, flüssig und überkritisch",
            xy=(t1q, p1q - 8), xytext=(63, 208), fontsize=10, color="#444444",
            ha="left", va="center", zorder=12,
            bbox=dict(boxstyle="round,pad=0.32", fc="white", ec=GREY, lw=1.3, alpha=0.95),
            arrowprops=dict(arrowstyle="->", color=GREY, lw=1.3))

t0r, t1r = RECHTECK["T"]; p0r, p1r = RECHTECK["p"]
ax.add_patch(Rectangle((t0r, p0r), t1r - t0r, p1r - p0r, fc="none", ec=ORNG,
                       lw=2.0, ls=(0, (5, 3)), zorder=3))
ax.annotate("bisher gezeichnetes Fenster\n70 – 210 bar · 30 – 60 °C",
            xy=(t0r, 150), xytext=(9.5, 118), fontsize=10, color=ORNG,
            weight="bold", ha="left", va="center", zorder=12,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=ORNG, lw=1.3, alpha=0.95),
            arrowprops=dict(arrowstyle="->", color=ORNG, lw=1.3))

# ---- tatsaechliche Zustandspfade ------------------------------------------
handles = []
for rate, farbe, lab in [(55.0, NAVY, "Zyklus bei 55 kg/s  (langsam)"),
                         (234.0, RED, "Zyklus bei 234 kg/s  (Nennrate)")]:
    r = Z.simuliere(Z.phasen, m_dot=rate)
    T = np.array([x["T"] for x in r]); P = np.array([x["p"] for x in r])
    q = np.array([x["q"] for x in r], dtype=float)
    ax.plot(T, P, "-", color=farbe, lw=2.4, zorder=7, alpha=0.95)
    handles.append(Line2D([0], [0], color=farbe, lw=2.4, label=lab))
    zwei = (q > 0) & (q < 1)
    if zwei.any():
        ax.plot(T[zwei], P[zwei], "-", color=MAG, lw=6, zorder=9, alpha=0.85,
                solid_capstyle="round")
        i = int(np.argmin(T))
        ax.annotate(f"ZWEIPHASIG\n{T[i]:.1f} °C · {P[i]:.0f} bar · Dampfanteil q = {q[i]:.2f}",
                    xy=(T[i], P[i]), xytext=(9.5, 40), fontsize=10.5, color=MAG,
                    weight="bold", ha="left", va="center", zorder=13,
                    bbox=dict(boxstyle="round,pad=0.32", fc="white", ec=MAG, lw=1.6, alpha=0.97),
                    arrowprops=dict(arrowstyle="->", color=MAG, lw=1.6))
        handles.append(Line2D([0], [0], color=MAG, lw=6,
                              label="davon zweiphasig (auf der Sättigungslinie)"))

ax.plot([Z.T_rock], [135.0], "s", ms=11, color=GREEN, mec="white", mew=1.5, zorder=11)
ax.annotate(f"Startzustand\n135 bar · {Z.T_rock:.0f} °C", (Z.T_rock, 135.0),
            textcoords="offset points", xytext=(14, 12), fontsize=10,
            color=GREEN, weight="bold", zorder=12,
            bbox=dict(boxstyle="round,pad=0.24", fc="white", ec=GREEN, lw=1.2, alpha=0.95))

ax.set_xlim(*TLIM); ax.set_ylim(*PLIM)
ax.set_xlabel("Temperatur  [°C]", fontsize=13)
ax.set_ylabel("Druck  [bar]", fontsize=13)
ax.grid(alpha=0.25, zorder=1); ax.tick_params(labelsize=11.5)
fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=10.5,
           framealpha=0.96, bbox_to_anchor=(0.5, 0.115))

fig.suptitle("Was die Kaverne wirklich durchläuft", fontsize=18, weight="bold", y=0.975)
fig.text(0.5, 0.925, "Zustandspfad über einen kompletten Speicherzyklus · "
                     f"Teufe {Z.TEUFE:.0f} m · Gebirge {Z.T_OBERFL:.0f} °C + "
                     f"{Z.GEO_GRAD*100:.0f} °C/100 m · CoolProp",
         ha="center", fontsize=11, color="#555555")
fig.text(0.5, 0.016,
         "Ein Rechteck zeigt nur die Hüllkurve der erlaubten Drücke und Temperaturen, "
         "nicht den Weg.\n"
         "Bei hoher Ausspeicherrate kühlt die Kaverne unter T_krit und wird zweiphasig.",
         ha="center", va="bottom", fontsize=11.5, color=NAVY, weight="bold", linespacing=1.4)
fig.tight_layout(rect=[0, 0.21, 1, 0.90])
fig.savefig(OUT, dpi=200)
print("geschrieben:", OUT)
