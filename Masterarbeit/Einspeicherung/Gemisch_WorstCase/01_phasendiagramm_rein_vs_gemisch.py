# -*- coding: utf-8 -*-
"""
Schritt 0 (Gemisch) - Phasendiagramm: reines CO2 vs. Worst-Case-Gemisch
============================================================================
Was ändern 5 mol-% Begleitstoffe (N2, Ar, CH4, H2, CO) am p-T-Diagramm,
und liegen die Betriebspunkte der Einspeicherung noch sicher einphasig?

Reines CO2 hat eine Dampfdrucklinie: bei gegebener Temperatur genau EIN
Druck, bei dem Flüssigkeit und Gas nebeneinander vorliegen. Beim Gemisch
wird daraus ein Zweiphasengebiet zwischen Taulinie und Blasenlinie. Die
leichtsiedenden Begleitstoffe (vor allem H2 und N2) schieben die
Blasenlinie deutlich zu höheren Drücken - man muss also mehr Druck
halten, damit das Gemisch sicher einphasig (flüssig/dicht) bleibt.

Betriebspunkte (aus den Skripten für reines CO2, Szenario 1 und 2):
  S1 Netzübergabe      91 bar / 15 °C   (dichte Phase)
  S2 Netzübergabe      30 bar / 15 °C   (gasförmig)
  S2 Zwischenkühler    49 bar / 40 °C
  S2 Kühleraustritt    80 bar / 25 °C   ("Verflüssiger", vor der Pumpe)

Stoffdaten des Gemischs: gemisch_worstcase.py (gleicher Ordner).

Diagramm links: gleiche Achsen und Farben wie abb_startpunkt_netzuebergabe.png
(-80 bis 100 °C, 0 bis 130 bar). Rechts: Ausschnitt um den kritischen Bereich.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI, PhaseSI

import gemisch_worstcase as gw

# ---- 1) Reines CO2: Sättigungslinie, kritischer Punkt, Tripelpunkt ---------
T_krit = PropsSI("Tcrit", "CO2")
p_krit = PropsSI("Pcrit", "CO2")
T_tripel = PropsSI("Ttriple", "CO2")
p_tripel = PropsSI("ptriple", "CO2")

T_saett = np.linspace(T_tripel, T_krit, 200)
p_saett_bar = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_saett]) / 1e5
T_saett_C = T_saett - 273.15
T_krit_C, T_tripel_C = T_krit - 273.15, T_tripel - 273.15
p_krit_bar, p_tripel_bar = p_krit / 1e5, p_tripel / 1e5


# Sublimations- und Schmelzlinie von reinem CO2 nach Span & Wagner (1996),
# wie in 01_02_start_netzuebergabe_filter_messungen.py (Szenario 1)
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
T_melt = np.linspace(T_tripel, T_tripel * 1.02, 100)
p_melt_bar = schmelz_bar(T_melt)
T_melt_C = T_melt - 273.15

# ---- 2) Gemisch: Zweiphasengebiet -------------------------------------------
pg = gw.phasengrenze()
T_krit_G, p_krit_G = pg["krit"]
T_cb, p_cb = pg["cricondenbar"]
T_ct, p_ct = pg["cricondentherm"]

print("Kritischer Punkt:")
print(f"  reines CO2: {T_krit_C:6.1f} °C / {p_krit_bar:6.1f} bar")
print(f"  Gemisch:    {T_krit_G:6.1f} °C / {p_krit_G:6.1f} bar")
print(f"  Cricondenbar (Gemisch):   {T_cb:.1f} °C / {p_cb:.1f} bar  "
      "-> oberhalb dieses Drucks ist das Gemisch bei jeder Temperatur einphasig")
print(f"  Cricondentherm (Gemisch): {T_ct:.1f} °C / {p_ct:.1f} bar")

print("\nPhasengrenze bei 15 °C (Pipelinetemperatur):")
p_s15 = PropsSI("P", "T", 15 + 273.15, "Q", 0, "CO2") / 1e5
print(f"  reines CO2 Dampfdruck:  {p_s15:5.1f} bar")
print(f"  Gemisch Taudruck:       {gw.taudruck(15):5.1f} bar  (darunter einphasig gasförmig)")
print(f"  Gemisch Blasendruck:    {gw.blasendruck(15):5.1f} bar  (darüber einphasig flüssig)")

# ---- 3) Betriebspunkte: rein vs. Gemisch -----------------------------------
PUNKTE = [
    # (Name, p [bar], T [°C], Markerfarbe, Marker)
    ("S1 Netzübergabe",   91.0, 15.0, "#007335", "s"),
    ("S2 Netzübergabe",   30.0, 15.0, "#164a73", "o"),
    ("S2 Zwischenkühler", 49.0, 40.0, "#164a73", "D"),
    ("S2 Kühleraustritt", 80.0, 25.0, "#164a73", "^"),
]

print(f"\n{'Betriebspunkt':<19} {'p':>6} {'T':>5} | {'Phase rein':<21} {'rho rein':>8} | "
      f"{'Phase Gemisch':<14} {'rho Gem.':>8}")
AS = gw.gemisch()
ergebnisse = {}
for name, p, T, _, _ in PUNKTE:
    ph_rein = PhaseSI("P", p * 1e5, "T", T + 273.15, "CO2")
    rho_rein = PropsSI("D", "P", p * 1e5, "T", T + 273.15, "CO2")
    g = gw.stoffwerte(p, T, AS)
    ergebnisse[name] = g
    zusatz = f"  (Dampfanteil Q = {g['Q']:.2f})" if "Q" in g else ""
    print(f"{name:<19} {p:6.1f} {T:5.1f} | {ph_rein:<21} {rho_rein:8.1f} | "
          f"{g['phase']:<14} {g['rho']:8.1f}{zusatz}")

# Abstand S1 zum Zweiphasengebiet
print(f"\nS1: 91 bar liegen {91 - gw.blasendruck(15):.1f} bar über dem Blasendruck bei 15 °C "
      f"und {91 - p_cb:.1f} bar über dem Cricondenbar.")

# ---- 4) Plot ---------------------------------------------------------------
# Flächenfarben wie in den Diagrammen für reines CO2 (CO2_Betriebsfenster.py)
C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, COL_GAS, COL_FLUE, COL_SUP, ROT = "#5F2176", "#164a73", "#007335", "#a3480b", "#CA220E"
COL_REIN = "#00304F"      # Sättigungslinie reines CO2
COL_GEM = ROT             # Phasengrenze Gemisch


def phasenflaechen_rein(ax):
    """Phasengebiete von reinem CO2 als Hintergrund (wie Szenario 1)."""
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


def linien(ax, beschriften=True):
    # reines CO2
    ax.plot(T_sub_C, p_sub_bar, color="#333333", lw=1.4, zorder=3,
            label="Sublimationslinie (rein)" if beschriften else None)
    ax.plot(T_melt_C, p_melt_bar, color=COL_FEST, lw=1.4, zorder=3,
            label="Schmelzlinie (rein)" if beschriften else None)
    ax.plot(T_saett_C, p_saett_bar, color=COL_REIN, lw=2.0, zorder=3,
            label="Sättigungslinie reines CO₂" if beschriften else None)
    ax.plot(T_krit_C, p_krit_bar, "o", color=COL_REIN, ms=8, zorder=5,
            markeredgecolor="white", markeredgewidth=1.5)

    # Gemisch: Zweiphasengebiet schraffiert, Blasen- und Taulinie
    huelle = list(zip(pg["T_tau"], pg["p_tau"])) + list(zip(pg["T_blase"], pg["p_blase"]))
    ax.add_patch(plt.Polygon(huelle, closed=True, fc=COL_GEM, alpha=0.12, ec="none", zorder=1))
    ax.add_patch(plt.Polygon(huelle, closed=True, fc="none", ec=COL_GEM, hatch="///",
                             lw=0, alpha=0.35, zorder=1))
    ax.plot(pg["T_blase"], pg["p_blase"], color=COL_GEM, lw=2.0, zorder=4,
            label="Blasenlinie Gemisch (Q = 0)" if beschriften else None)
    ax.plot(pg["T_tau"], pg["p_tau"], color=COL_GEM, lw=2.0, ls="--", zorder=4,
            label="Taulinie Gemisch (Q = 1)" if beschriften else None)
    ax.plot(T_krit_G, p_krit_G, "o", color=COL_GEM, ms=8, zorder=5,
            markeredgecolor="white", markeredgewidth=1.5)
    ax.axhline(p_cb, color=COL_GEM, lw=0.9, ls=":", zorder=2,
               label=f"Cricondenbar Gemisch ({p_cb:.1f} bar)" if beschriften else None)


def betriebspunkte(ax, texte):
    for name, p, T, farbe, marker in PUNKTE:
        ax.plot(T, p, marker, color=farbe, ms=10, zorder=6,
                markeredgecolor="black", markeredgewidth=0.8)
        if name in texte:
            dx, dy = texte[name]
            g = ergebnisse[name]
            ax.annotate(f"{name}\n{p:.0f} bar / {T:.0f} °C\nGemisch: {g['phase']}",
                        (T, p), textcoords="offset points", xytext=(dx, dy), fontsize=8.5,
                        weight="bold" if g["phase"] == "ZWEIPHASIG" else "normal",
                        color=COL_GEM if g["phase"] == "ZWEIPHASIG" else "black",
                        arrowprops=dict(arrowstyle="-", color="#555555", lw=0.7))


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.8), gridspec_kw={"width_ratios": [1.15, 1]})

# -- links: Übersicht (gleiche Achsen wie Szenario 1) --
phasenflaechen_rein(ax1)
linien(ax1)
box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75)
ax1.text(-67, 100, "fest\n(Trockeneis)", fontsize=9.5, color=COL_FEST, weight="bold", ha="center", bbox=box)
ax1.text(72, 55, "gasförmig", fontsize=12, color=COL_GAS, weight="bold", ha="center", bbox=box)
ax1.text(-5, 105, "flüssig", fontsize=12, color=COL_FLUE, weight="bold", ha="center", bbox=box)
ax1.text(65, 118, "überkritisch", fontsize=12, color=COL_SUP, weight="bold", ha="center", bbox=box)
ax1.text(-35, 32, "Zweiphasen-\ngebiet Gemisch", fontsize=9, color=COL_GEM, weight="bold", ha="center", bbox=box)
betriebspunkte(ax1, {"S1 Netzübergabe": (12, 12), "S2 Netzübergabe": (-60, -52)})
# Ausschnitt rechts markieren
Z_T, Z_P = (0.0, 45.0), (40.0, 100.0)
ax1.add_patch(plt.Rectangle((Z_T[0], Z_P[0]), Z_T[1] - Z_T[0], Z_P[1] - Z_P[0],
                            fc="none", ec="#555555", lw=1.0, ls="-", zorder=7))
ax1.set_xlim(Tmin, Tmax)
ax1.set_ylim(Pmin, Pmax)
ax1.set_xlabel("Temperatur [°C]")
ax1.set_ylabel("Druck [bar]")
ax1.set_title("Übersicht")
ax1.legend(loc="lower right", fontsize=8, framealpha=0.92)
ax1.grid(alpha=0.25, zorder=1)

# -- rechts: Ausschnitt kritischer Bereich --
phasenflaechen_rein(ax2)
linien(ax2, beschriften=False)
betriebspunkte(ax2, {"S1 Netzübergabe": (10, 8), "S2 Zwischenkühler": (-40, -48),
                     "S2 Kühleraustritt": (10, 45)})
ax2.annotate(f"krit. Punkt rein\n{T_krit_C:.1f} °C / {p_krit_bar:.1f} bar", (T_krit_C, p_krit_bar),
             textcoords="offset points", xytext=(12, -30), fontsize=8.5, color=COL_REIN)
ax2.annotate(f"krit. Punkt Gemisch\n{T_krit_G:.1f} °C / {p_krit_G:.1f} bar", (T_krit_G, p_krit_G),
             textcoords="offset points", xytext=(14, -24), fontsize=8.5, color=COL_GEM)

# Verschiebung der Phasengrenze bei 15 °C als Pfeil
p_bl15 = gw.blasendruck(15)
ax2.annotate("", xy=(15, p_bl15), xytext=(15, p_s15),
             arrowprops=dict(arrowstyle="->", color="#333333", lw=1.4))
ax2.text(15.8, 44.0,
         f"+{p_bl15 - p_s15:.0f} bar\n(Dampfdruck rein {p_s15:.1f} bar\n→ Blasendruck Gemisch {p_bl15:.1f} bar)",
         fontsize=8.5, va="bottom", bbox=box)

ax2.set_xlim(*Z_T)
ax2.set_ylim(*Z_P)
ax2.set_xlabel("Temperatur [°C]")
ax2.set_title("Ausschnitt: kritischer Bereich und Betriebspunkte")
ax2.grid(alpha=0.25, zorder=1)

fig.suptitle("p-T-Diagramm: reines CO₂ vs. Worst-Case-Gemisch "
             "(95 % CO₂, 2,4 % N₂, 1 % Ar, 1 % CH₄, 0,5 % H₂, 0,1 % CO)", fontsize=12)
fig.tight_layout()
fig.savefig("abb_phasendiagramm_rein_vs_gemisch.png", dpi=175)
print("\ngespeichert: abb_phasendiagramm_rein_vs_gemisch.png")
