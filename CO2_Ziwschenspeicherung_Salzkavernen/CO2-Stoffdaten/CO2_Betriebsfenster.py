"""
Erzeugt zwei Abbildungen fuer die Praesentation:

  abbA_phasendiagramm_rein.png       reines p-T-Phasendiagramm, OHNE Prozesspfad
  abbB_betriebsfenster_kaverne.png   dasselbe Diagramm mit Kavernen-Betriebsfenster
                                     und den beiden OGE-Anlieferfenstern

Betriebsdaten uebernommen aus CO2_Gassaeule_Kaverne2.xlsx
(Blaetter 'Anlagenkonzept', 'Annahmen', 'Berechnung', 'Phasendiagramm').

Ausfuehren:
    py -3.10 CO2_Betriebsfenster.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from CoolProp.CoolProp import PropsSI

SAVE = True
OUT = "Abbildungen"

# ---- Referenzpunkte -------------------------------------------------------
T_TRIPLE_K, P_TRIPLE_BAR = 216.592, 5.1795
T_TRIPLE_C = T_TRIPLE_K - 273.15
T_CRIT_C = PropsSI("Tcrit", "CO2") - 273.15
P_CRIT_BAR = PropsSI("Pcrit", "CO2") / 1e5

# ---- Betriebsdaten aus der Excel -----------------------------------------
KAVERNE = dict(T=(30.0, 60.0), p=(70.0, 210.0))        # Blatt 'Phasendiagramm', Reihe Kaverne
OGE_DICHT = dict(T=(5.0, 25.0), p=(74.0, 200.0))       # Anlagenkonzept: Spec dichte Phase
OGE_GAS = dict(T=(5.0, 25.0), p=(25.0, 35.0))          # Anlagenkonzept: Spec gasfoermig
PKT_DICHT = (15.0, 85.0)                               # Auslegungspunkt Szenario D
PKT_GAS = (15.0, 30.0)                                 # Auslegungspunkt Szenario G
KOPF = (15.0, 110.8)                                   # Bohrlochkopf, Blatt 'Annahmen'
KAV_PKT = (51.0, 210.0)                                # Kaverne unten, Blatt 'Anlagenkonzept'

# Farben (Uniper-nah)
C_FEST, C_FLUE, C_GAS, C_SUP = "#D9D2E9", "#D9EAD3", "#CFE2F3", "#FCE5CD"
NAVY, ORNG, GREEN, RED = "#00304F", "#EE7203", "#007335", "#CA220E"


# ---- Phasengrenzen --------------------------------------------------------
def saettigung(n=400):
    T = np.linspace(T_TRIPLE_K, PropsSI("Tcrit", "CO2") - 1e-6, n)
    p = PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5
    return T - 273.15, p


def sublimation(n=200):
    """Sublimationsdruck nach Span & Wagner (1996)."""
    T = np.linspace(180.0, T_TRIPLE_K, n)
    t = 1 - T / T_TRIPLE_K
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    lnp = (T_TRIPLE_K / T) * (a1 * t + a2 * t ** 1.9 + a3 * t ** 2.9)
    return T - 273.15, P_TRIPLE_BAR * np.exp(lnp)


def schmelz(pmax=260, n=200):
    """Schmelzdruck nach Span & Wagner (1996)."""
    p = np.linspace(P_TRIPLE_BAR, pmax, n)
    a1, a2 = 1955.5390, 2055.4593
    # p/p_t = 1 + a1*(T/T_t - 1) + a2*(T/T_t - 1)^2  -> nach T aufloesen
    y = p / P_TRIPLE_BAR - 1.0
    disc = a1 ** 2 + 4 * a2 * y
    x = (-a1 + np.sqrt(disc)) / (2 * a2)
    return (1 + x) * T_TRIPLE_K - 273.15, p


def grundgeruest(ax, tlim, plim, legende=True, dichte_beschriftung=True):
    """zeichnet Phasengebiete, Grenzlinien, Trippel- und kritischen Punkt"""
    Ts, ps = saettigung()
    Tsub, psub = sublimation()
    Tm, pm = schmelz(pmax=plim[1] * 1.15)
    t0, t1 = tlim
    p0, p1 = plim

    # Flaechen
    ax.add_patch(Rectangle((t0, p0), t1 - t0, p1 - p0, fc=C_GAS, ec="none", zorder=0))
    # fluessig: links der Saettigung, oberhalb, links der Schmelzlinie
    Tf = np.concatenate([Tsub[Tsub >= t0], Ts])
    pf = np.concatenate([psub[Tsub >= t0], ps])
    Tm_i = np.interp(np.linspace(p0, p1, 200), pm, Tm)
    poly = list(zip(Tf, pf)) + [(T_CRIT_C, P_CRIT_BAR), (T_CRIT_C, p1)] + \
           list(zip(Tm_i[::-1], np.linspace(p0, p1, 200)[::-1]))
    ax.add_patch(Polygon(poly, closed=True, fc=C_FLUE, ec="none", zorder=0))
    # fest
    ax.add_patch(Polygon(list(zip(Tm_i, np.linspace(p0, p1, 200))) +
                         [(t0, p1), (t0, p0)],
                         closed=True, fc=C_FEST, ec="none", zorder=0))
    # ueberkritisch
    ax.add_patch(Rectangle((T_CRIT_C, P_CRIT_BAR), t1 - T_CRIT_C, p1 - P_CRIT_BAR,
                           fc=C_SUP, ec="none", zorder=0))

    # Linien
    ax.plot(Tsub, psub, color="#333333", lw=2, label="Sublimationslinie", zorder=3)
    ax.plot(Ts, ps, color="#1F4E79", lw=2.4, label="Sättigungslinie", zorder=3)
    ax.plot(Tm, pm, color="#5F2176", lw=2, label="Schmelzlinie", zorder=3)

    # Punkte
    ax.plot(*[T_CRIT_C], [P_CRIT_BAR], "o", ms=9, color=RED, zorder=6)
    ax.annotate(f"kritischer Punkt\n{T_CRIT_C:.1f} °C  |  {P_CRIT_BAR:.1f} bar",
                (T_CRIT_C, P_CRIT_BAR), textcoords="offset points", xytext=(16, -34),
                fontsize=11, color=RED, weight="bold", zorder=10,
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.85),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.4))
    if t0 <= T_TRIPLE_C <= t1:
        ax.plot([T_TRIPLE_C], [P_TRIPLE_BAR], "o", ms=8, color="black", zorder=6)
        ax.annotate(f"Tripelpunkt\n{T_TRIPLE_C:.1f} °C  |  {P_TRIPLE_BAR:.2f} bar",
                    (T_TRIPLE_C, P_TRIPLE_BAR), textcoords="offset points", xytext=(18, 34),
                    fontsize=10.5, arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

    # Gebietsbeschriftung
    if dichte_beschriftung:
        box = dict(boxstyle="round,pad=0.28", fc="white", ec="none", alpha=0.72)
        ax.text(t0 + (T_TRIPLE_C - t0) * 0.35, p1 * 0.62, "fest\n(Trockeneis)",
                fontsize=13, color="#4A3B6B", ha="center", weight="bold", bbox=box)
        ax.text((T_TRIPLE_C + T_CRIT_C) / 2, p1 * 0.60, "flüssig",
                fontsize=14, color=GREEN, ha="center", weight="bold", bbox=box)
        ax.text(t0 + (t1 - t0) * 0.72, p1 * 0.07, "gasförmig",
                fontsize=14, color="#1F4E79", ha="center", weight="bold", bbox=box)
        ax.text(T_CRIT_C + (t1 - T_CRIT_C) * 0.55, p1 * 0.86, "überkritisch",
                fontsize=14, color=ORNG, ha="center", weight="bold", bbox=box)

    ax.set_xlim(*tlim); ax.set_ylim(*plim)
    ax.set_xlabel("Temperatur  [°C]", fontsize=13)
    ax.set_ylabel("Druck  [bar]", fontsize=13)
    ax.grid(alpha=0.25, zorder=1)
    ax.tick_params(labelsize=11.5)
    if legende:
        ax.legend(loc="upper left", fontsize=11, framealpha=0.92)


# =========================================================== Abbildung A
fig, ax = plt.subplots(figsize=(11.0, 7.2))
grundgeruest(ax, (-100, 60), (0, 250))
fig.suptitle("Phasendiagramm von CO$_2$", fontsize=18, weight="bold", y=0.975)
fig.text(0.5, 0.925, "reine Stoffdaten, lineare Druckachse · CoolProp (Span-Wagner)",
         ha="center", fontsize=11.5, color="#555555")
fig.tight_layout(rect=[0, 0, 1, 0.90])
if SAVE:
    fig.savefig(f"{OUT}/abbA_phasendiagramm_rein.png", dpi=200)
    print("geschrieben:", f"{OUT}/abbA_phasendiagramm_rein.png")


# =========================================================== Abbildung B
fig, ax = plt.subplots(figsize=(11.6, 7.2))
grundgeruest(ax, (-10, 70), (0, 240), legende=False, dichte_beschriftung=False)

box = dict(boxstyle="round,pad=0.26", fc="white", ec="none", alpha=0.78)
ax.text(-7.5, 158, "flüssig", fontsize=13, color=GREEN, weight="bold", bbox=box)
ax.text(65, 228, "überkritisch", fontsize=13, color=ORNG, weight="bold", ha="right", bbox=box)
ax.text(66, 8, "gasförmig", fontsize=13, color="#1F4E79", weight="bold", ha="right", bbox=box)

def fenster(d, color, label, hatch=None, lw=2.4):
    t0, t1 = d["T"]; p0, p1 = d["p"]
    ax.add_patch(Rectangle((t0, p0), t1 - t0, p1 - p0, fc=color, ec=color,
                           alpha=0.22, zorder=4))
    ax.add_patch(Rectangle((t0, p0), t1 - t0, p1 - p0, fc="none", ec=color,
                           lw=lw, zorder=5, hatch=hatch))
    return label

# Kavernen-Betriebsfenster
fenster(KAVERNE, ORNG, "")
ax.annotate("KAVERNE\n70 – 210 bar\n30 – 60 °C",
            xy=(45, 140), fontsize=12.5, color=ORNG, weight="bold",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=ORNG, lw=1.6, alpha=0.95),
            zorder=8)

# OGE-Fenster
fenster(OGE_DICHT, NAVY, "")
ax.annotate("OGE-ANLIEFERUNG\ndichte Phase\n74 – 200 bar · 5 – 25 °C",
            xy=(15, 200), xytext=(-8.0, 226), fontsize=11.5, color=NAVY, weight="bold",
            ha="left", va="top",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=NAVY, lw=1.5, alpha=0.95),
            arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.5), zorder=8)

fenster(OGE_GAS, GREEN, "")
ax.annotate("OGE-ANLIEFERUNG\ngasförmig\n25 – 35 bar · 5 – 25 °C",
            xy=(5, 28), xytext=(-8.2, 3), fontsize=11.5, color=GREEN, weight="bold",
            ha="left", va="bottom",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=GREEN, lw=1.5, alpha=0.95),
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5), zorder=8)

# Gassaeule im Bohrloch: Kopf -> Kaverne
ax.annotate("", xy=KAV_PKT[::-1][::-1], xytext=KOPF,
            arrowprops=dict(arrowstyle="-", color="#777777", lw=0))
ax.plot([KOPF[0], KAV_PKT[0]], [KOPF[1], KAV_PKT[1]],
        ls="--", lw=2.0, color="#666666", zorder=6)
ax.plot(*KOPF, "o", ms=8, mfc="white", mec="#444444", mew=1.8, zorder=7)
ax.plot(*KAV_PKT, "o", ms=8, color="#444444", zorder=7)
ax.annotate("Gassäule im Bohrloch\n1200 m", xy=(33, 165), fontsize=10.5,
            color="#444444", ha="center", style="italic", zorder=8,
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.8))
ax.annotate("Bohrlochkopf\n110,8 bar · 15 °C", xy=KOPF, xytext=(-8.0, 96),
            fontsize=10.5, color="#333333", ha="left", va="center",
            arrowprops=dict(arrowstyle="->", color="#666666", lw=1.2), zorder=8)

# Auslegungspunkte
for (t, p), col, txt in [(PKT_DICHT, NAVY, "85 bar · 15 °C"), (PKT_GAS, GREEN, "30 bar · 15 °C")]:
    ax.plot(t, p, "D", ms=8, color=col, zorder=9)
    ax.annotate(txt, (t, p), textcoords="offset points", xytext=(11, 9),
                fontsize=10.5, color=col, weight="bold", ha="left", zorder=9,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

fig.suptitle("Wo die Kaverne arbeitet – und wo das CO$_2$ ankommt",
             fontsize=18, weight="bold", y=0.975)
fig.text(0.5, 0.925,
         "Betriebsfenster der Salzkaverne (1200 m) und Anlieferfenster der OGE-Leitung · "
         "Daten aus CO2_Gassaeule_Kaverne2.xlsx",
         ha="center", fontsize=11, color="#555555")
fig.tight_layout(rect=[0, 0, 1, 0.90])
if SAVE:
    fig.savefig(f"{OUT}/abbB_betriebsfenster_kaverne.png", dpi=200)
    print("geschrieben:", f"{OUT}/abbB_betriebsfenster_kaverne.png")
