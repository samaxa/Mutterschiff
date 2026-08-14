"""
Prozesspfade der beiden Anlieferszenarien im p-T-Phasendiagramm.

  abbC_prozesspfad_szenarioD.png   Szenario D - Anlieferung in dichter Phase
  abbD_prozesspfad_szenarioG.png   Szenario G - gasfoermige Anlieferung

Die Punktbezeichnungen E1...E7 und A1...A6 sind identisch mit denen der
Blockfliessbilder, damit beide Darstellungen nebeneinander lesbar sind.

Zustandspunkte aus CO2_Gassaeule_Kaverne2.xlsx, Blatt 'Anlagenkonzept';
Bohrlochsaeule aus Blatt 'Berechnung'.

Ausfuehren:
    py -3.10 CO2_Prozesspfade.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from matplotlib.lines import Line2D
from CoolProp.CoolProp import PropsSI

OUT = "Abbildungen"

T_TRIPLE_K, P_TRIPLE_BAR = 216.592, 5.1795
T_CRIT_C = PropsSI("Tcrit", "CO2") - 273.15
P_CRIT_BAR = PropsSI("Pcrit", "CO2") / 1e5

C_FLUE, C_GAS, C_SUP = "#D9EAD3", "#CFE2F3", "#FCE5CD"
NAVY, ORNG, GREEN, RED, GREY = "#00304F", "#EE7203", "#007335", "#CA220E", "#666666"

# ---- Bohrlochsaeule (Blatt 'Berechnung') ---------------------------------
SAEULE_T = [15.0, 16.5, 18.0, 19.5, 21.0, 22.5, 24.0, 25.5, 27.0, 28.5, 30.0, 31.5,
            33.0, 34.5, 36.0, 37.5, 39.0, 40.5, 42.0, 43.5, 45.0, 46.5, 48.0, 49.5, 51.0]
SAEULE_P = [110.79, 115.2, 119.59, 123.95, 128.3, 132.61, 136.9, 141.17, 145.42,
            149.64, 153.83, 158.01, 162.16, 166.29, 170.39, 174.48, 178.54, 182.58,
            186.6, 190.6, 194.58, 198.53, 202.47, 206.39, 210.28]

KAVERNE = dict(T=(30.0, 60.0), p=(70.0, 210.0))


def saettigung(n=400):
    T = np.linspace(T_TRIPLE_K, PropsSI("Tcrit", "CO2") - 1e-6, n)
    return T - 273.15, PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5


def hintergrund(ax, tlim, plim, krit_off=(-96, -46), krit_label=True,
                kavernenfenster=True, regionen=True):
    Ts, ps = saettigung()
    t0, t1 = tlim; p0, p1 = plim
    ax.add_patch(Rectangle((t0, p0), t1 - t0, p1 - p0, fc=C_GAS, ec="none", zorder=0))
    m = (Ts >= t0)
    poly = [(t0, p1), (t0, np.interp(t0, Ts, ps))] + list(zip(Ts[m], ps[m])) + \
           [(T_CRIT_C, P_CRIT_BAR), (T_CRIT_C, p1)]
    ax.add_patch(Polygon(poly, closed=True, fc=C_FLUE, ec="none", zorder=0))
    ax.add_patch(Rectangle((T_CRIT_C, P_CRIT_BAR), t1 - T_CRIT_C, p1 - P_CRIT_BAR,
                           fc=C_SUP, ec="none", zorder=0))
    ax.plot(Ts, ps, color="#1F4E79", lw=2.4, zorder=3)
    ax.plot([T_CRIT_C], [P_CRIT_BAR], "o", ms=9, color=RED, zorder=6)
    if krit_label:
        ax.annotate("krit. Punkt\n31,0 °C | 73,8 bar", (T_CRIT_C, P_CRIT_BAR),
                    textcoords="offset points", xytext=krit_off, fontsize=9.5,
                    color=RED, weight="bold", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85),
                    arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
    # Kavernenfenster
    t0k, t1k = KAVERNE["T"]; p0k, p1k = KAVERNE["p"]
    if not kavernenfenster:
        t0k = t1k = p0k = p1k = None
    if kavernenfenster:
        ax.add_patch(Rectangle((t0k, p0k), t1k - t0k, p1k - p0k, fc=ORNG, ec=ORNG,
                               alpha=0.13, lw=1.6, ls=(0, (5, 3)), zorder=2))
        ax.text(t1k - 0.6, p1k - 5, "Betriebsfenster Kaverne", fontsize=9,
                color=ORNG, ha="right", va="top", style="italic", zorder=6)

    box = dict(boxstyle="round,pad=0.24", fc="white", ec="none", alpha=0.75)
    if regionen:
        ax.text(t0 + (t1 - t0) * 0.04, p1 * 0.93, "flüssig", fontsize=11.5,
                color=GREEN, weight="bold", bbox=box, zorder=5)
        ax.text(t1 - (t1 - t0) * 0.03, p1 * 0.93, "überkritisch", fontsize=11.5,
                color=ORNG, weight="bold", ha="right", bbox=box, zorder=5)
        ax.text(t1 - (t1 - t0) * 0.03, p1 * 0.045, "gasförmig", fontsize=11.5,
                color="#1F4E79", weight="bold", ha="right", bbox=box, zorder=5)

    ax.set_xlim(*tlim); ax.set_ylim(*plim)
    ax.set_xlabel("Temperatur  [°C]", fontsize=12.5)
    ax.set_ylabel("Druck  [bar]", fontsize=12.5)
    ax.grid(alpha=0.25, zorder=1); ax.tick_params(labelsize=11)


def pfad(ax, punkte, color, label, off=None, ms=9, skip=(), rename=None):
    """punkte: Liste (name, T, p); zeichnet Linie, Marker und Beschriftung"""
    T = [p[1] for p in punkte]; P = [p[2] for p in punkte]
    ax.plot(T, P, "-", color=color, lw=2.6, zorder=7, solid_capstyle="round")
    ax.plot(T, P, "o", color="white", ms=ms + 5, zorder=8)
    ax.plot(T, P, "o", color=color, ms=ms, zorder=9)
    for i, (nm, t, p) in enumerate(punkte):
        if nm in skip: continue
        dx, dy = (off or {}).get(nm, (12, 10))
        txt = (rename or {}).get(nm, nm)
        ax.annotate(txt, (t, p), textcoords="offset points", xytext=(dx, dy),
                    fontsize=10.5, weight="bold", color=color, zorder=11,
                    bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=color,
                              lw=0.9, alpha=0.95))
    return Line2D([0], [0], color=color, lw=2.6, marker="o", ms=7, label=label)


def pfeile(ax, punkte, color):
    for a, b in zip(punkte[:-1], punkte[1:]):
        ax.annotate("", xy=((a[1] + b[1]) / 2 + (b[1] - a[1]) * 0.06,
                            (a[2] + b[2]) / 2 + (b[2] - a[2]) * 0.06),
                    xytext=((a[1] + b[1]) / 2, (a[2] + b[2]) / 2),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=0, mutation_scale=18,
                                    fc=color, ec=color), zorder=10)


# =========================================================== Szenario D
fig, ax = plt.subplots(figsize=(11.4, 7.0))
hintergrund(ax, (0, 62), (0, 240), krit_off=(-104, -54))

EIN_D = [("E1/E2", 15.0, 85.0), ("E3", 17.9, 110.8)]
AUS_D = [("A1/A2", 37.9, 120.0), ("A3", 32.0, 85.0), ("A4/A5", 25.0, 85.0)]

ax.plot(SAEULE_T, SAEULE_P, "-", color=GREEN, lw=2.6, zorder=7)
ax.annotate("E4  Bohrloch abwärts\n1200 m, homogen –\nkeine Phasengrenze",
            xy=(33, 162), xytext=(3.0, 178), fontsize=10, color=GREEN, weight="bold",
            ha="left", va="center", zorder=11,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=GREEN, lw=1.2, alpha=0.95),
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.4))

h1 = pfad(ax, EIN_D, GREEN, "① Einspeicherung", off={"E1/E2": (-16, -26), "E3": (-58, 6)})
pfeile(ax, EIN_D, GREEN)
h2 = pfad(ax, AUS_D, RED, "② Ausspeicherung", off={"A1/A2": (14, 8), "A3": (14, -6), "A4/A5": (-20, -26)})
pfeile(ax, AUS_D, RED)

ax.plot([SAEULE_T[-1]], [SAEULE_P[-1]], "s", color=ORNG, ms=13, zorder=10,
        mec="white", mew=1.6)
ax.annotate("KAVERNE\n210 bar · 51 °C", (SAEULE_T[-1], SAEULE_P[-1]),
            textcoords="offset points", xytext=(-40, 16), fontsize=10.5,
            weight="bold", color=ORNG, ha="center", zorder=11,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=ORNG, lw=1.3, alpha=0.95))
ax.plot([AUS_D[0][1]], [AUS_D[0][2]], "-", color=RED)
ax.plot([SAEULE_T[-1], AUS_D[0][1]], [SAEULE_P[-1], AUS_D[0][2]], "-",
        color=RED, lw=2.6, zorder=7)

ax.legend(handles=[h1, h2], loc="lower right", fontsize=11, framealpha=0.95)
fig.suptitle("Szenario D – Anlieferung in dichter Phase", fontsize=17.5, weight="bold", y=0.975)
fig.text(0.5, 0.925, "Prozesspfad im p-T-Diagramm · Punktbezeichnungen wie im Blockfließbild",
         ha="center", fontsize=11, color="#555555")
fig.text(0.5, 0.018, "Der Strom bleibt über die gesamte Kette einphasig – die Phasengrenze wird nie gequert.",
         ha="center", fontsize=11.5, color=NAVY, weight="bold")
fig.tight_layout(rect=[0, 0.035, 1, 0.90])
fig.savefig(f"{OUT}/abbC_prozesspfad_szenarioD.png", dpi=200)
print("geschrieben:", f"{OUT}/abbC_prozesspfad_szenarioD.png")

# =========================================================== Szenario G
fig, ax = plt.subplots(figsize=(12.6, 7.0))
hintergrund(ax, (-12, 95), (0, 240), krit_label=False,
            kavernenfenster=False, regionen=False)
box_ = dict(boxstyle="round,pad=0.24", fc="white", ec="none", alpha=0.75)
ax.text(-10.5, 224, "flüssig", fontsize=11.5, color=GREEN, weight="bold", bbox=box_, zorder=5)
ax.text(93, 224, "überkritisch", fontsize=11.5, color=ORNG, weight="bold",
        ha="right", bbox=box_, zorder=5)
ax.text(34, 9, "gasförmig", fontsize=11.5, color="#1F4E79", weight="bold",
        ha="center", bbox=box_, zorder=5)

EIN_G = [("E1/E2", 15.0, 30.0), ("E3", 56.4, 49.0), ("E4", 40.0, 49.0),
         ("E5", 83.8, 80.0), ("E6", 25.0, 80.0), ("E7", 30.0, 111.0)]
AUS_G = [("A1/A2", 41.0, 120.0), ("A3", 75.0, 120.0), ("A4", 32.0, 60.0),
         ("A5", 46.0, 60.0), ("A6", 15.0, 30.0)]

ax.plot(SAEULE_T, SAEULE_P, "-", color=GREEN, lw=2.2, alpha=0.55, zorder=6)
ax.annotate("Bohrloch abwärts", xy=(37, 168), fontsize=9.5, color=GREEN,
            style="italic", ha="center", zorder=7,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))

h1 = pfad(ax, EIN_G, GREEN, "① Einspeicherung  Gas → Verdichtung → Verflüssigung → Pumpe",
          off={"E1/E2": (-18, -30), "E3": (10, -24), "E4": (-8, -28),
               "E5": (12, 6), "E6": (-36, 12), "E7": (-34, 14)}, ms=8,
          rename={"E1/E2": "E1/E2  ·  A6"})
pfeile(ax, EIN_G, GREEN)
h2 = pfad(ax, AUS_G, RED, "② Ausspeicherung  vorwärmen und drosseln",
          off={"A1/A2": (-50, 12), "A3": (12, 8), "A4": (-16, 14),
               "A5": (12, 10)}, ms=8, skip=("A6",))
pfeile(ax, AUS_G, RED)
ax.plot([SAEULE_T[-1], AUS_G[0][1]], [SAEULE_P[-1], AUS_G[0][2]], "-",
        color=RED, lw=2.6, zorder=7)
ax.plot([EIN_G[-1][1], SAEULE_T[0]], [EIN_G[-1][2], SAEULE_P[0]], "-",
        color=GREEN, lw=2.6, zorder=7)

# Vergleich ohne Vorwaermung
ax.plot([41.0, -5.6], [120.0, 30.0], ls=(0, (4, 3)), lw=2.2, color="#8E44AD", zorder=7)
ax.plot([-5.6], [30.0], "X", ms=13, color="#8E44AD", zorder=10, mec="white", mew=1.4)
ax.annotate("ohne Vorwärmung:\n−5,6 °C, zweiphasig (q = 0,21)\naußerhalb Spezifikation",
            xy=(-5.6, 30.0), xytext=(-11.0, 62), fontsize=10, color="#8E44AD",
            weight="bold", ha="left", va="bottom", zorder=11,
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#8E44AD", lw=1.2, alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#8E44AD", lw=1.3))

ax.plot([SAEULE_T[-1]], [SAEULE_P[-1]], "s", color=ORNG, ms=13, zorder=10,
        mec="white", mew=1.6)
ax.annotate("KAVERNE\n210 bar · 51 °C", (SAEULE_T[-1], SAEULE_P[-1]),
            textcoords="offset points", xytext=(4, 16), fontsize=10.5,
            weight="bold", color=ORNG, ha="center", zorder=11,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=ORNG, lw=1.3, alpha=0.95))

ax.legend(handles=[h1, h2], loc="lower right", fontsize=10, framealpha=0.96)
fig.suptitle("Szenario G – gasförmige Anlieferung", fontsize=17.5, weight="bold", y=0.975)
fig.text(0.5, 0.925, "Prozesspfad im p-T-Diagramm · Punktbezeichnungen wie im Blockfließbild",
         ha="center", fontsize=11, color="#555555")
fig.text(0.5, 0.018, "Hier wird die Phasengrenze zweimal gequert: bei der Verflüssigung (E6) "
                     "und bei der Drosselung (A4).",
         ha="center", fontsize=11.5, color=NAVY, weight="bold")
fig.tight_layout(rect=[0, 0.035, 1, 0.90])
fig.savefig(f"{OUT}/abbD_prozesspfad_szenarioG.png", dpi=200)
print("geschrieben:", f"{OUT}/abbD_prozesspfad_szenarioG.png")
