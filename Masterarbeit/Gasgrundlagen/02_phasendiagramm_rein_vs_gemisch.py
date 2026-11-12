# -*- coding: utf-8 -*-
"""
G02 - Phasendiagramm reines CO2 (links) und Worst-Case-Gemisch (rechts)
============================================================================
Für das Grundlagenkapitel: gleiche Achsen, gleiche Farben, links reines CO2,
rechts das Gemisch. Von links nach rechts sieht man, was 5 mol-%
Begleitstoffe ändern: aus der Siedelinie wird ein Zweiphasengebiet zwischen
Tau- und Blasenlinie, der kritische Punkt verschiebt sich, und der
höchste Druck des Zweiphasengebiets (Cricondenbar) liegt über dem
kritischen Druck von reinem CO2.

Keine Betriebspunkte: die stehen in
Einspeicherung/Begleitstoffe_CO2/Stoffmodell/01_phasendiagramm_rein_vs_gemisch.py
(Abbildung abb_phasendiagramm_rein_vs_gemisch.png, Methodik/Prozesskette).
Zusammensetzung und Herleitung des Gemischs: gemisch_worstcase.py und
Masterarbeit Kap. 4 (Zusammensetzung des Worst-Case-Gemischs).

Ergebnisse: Abbildungen/G02_rein_vs_gemisch.json
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import gasgrundlagen_bausteine as gb

sys.path.insert(0, str(gb.ORDNER.parent / "Einspeicherung" / "Begleitstoffe_CO2" / "Grundlagen"))
import gemisch_worstcase as gw                       # noqa: E402

kw = gb.kennwerte("CO2")
T_krit, p_krit = kw["T_krit"], kw["p_krit"]
T_s, p_s = gb.saettigungslinie_co2()
pg = gw.phasengrenze()
T_krit_G, p_krit_G = pg["krit"]
T_cb, p_cb = pg["cricondenbar"]
p_bl15, p_tau15 = gw.blasendruck(15.0), gw.taudruck(15.0)
p_s15 = PropsSI("P", "T", gb.K(15.0), "Q", 0, "CO2") / 1e5

print(f"kritischer Punkt rein:    {T_krit:5.1f} °C / {p_krit:5.1f} bar")
print(f"kritischer Punkt Gemisch: {T_krit_G:5.1f} °C / {p_krit_G:5.1f} bar")
print(f"Cricondenbar Gemisch:     {T_cb:5.1f} °C / {p_cb:5.1f} bar")
print(f"bei 15 °C: Siededruck rein {p_s15:.1f} bar | Gemisch Tau {p_tau15:.1f} bar, "
      f"Blase {p_bl15:.1f} bar -> Zweiphasengebiet {p_bl15 - p_tau15:.1f} bar breit, "
      f"Blasenlinie {p_bl15 - p_s15:+.1f} bar gegenüber rein")

Tmin, Tmax, Pmin, Pmax = -55.0, 60.0, 0.0, 120.0
C_GAS, C_FLUE, C_SUP = "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_GAS, COL_FLUE, COL_SUP, COL_REIN, COL_GEM = "#164a73", "#007335", "#a3480b", "#00304F", "#CA220E"
box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8)


def hintergrund(ax):
    gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, p_krit), (T_krit, p_krit)]
    gas += list(zip(T_s[::-1], p_s[::-1])) + [(T_s[0], Pmin)]
    gas = [(max(t, Tmin), p) for t, p in gas]
    ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))
    flue = [(Tmin, p_s[0]), (Tmin, Pmax), (T_krit, Pmax)] + list(zip(T_s[::-1], p_s[::-1]))
    ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))
    ax.add_patch(plt.Rectangle((T_krit, p_krit), Tmax - T_krit, Pmax - p_krit,
                               fc=C_SUP, ec="none", zorder=0))
    ax.text(-30, 95, "flüssig", fontsize=12, color=COL_FLUE, weight="bold", ha="center", bbox=box)
    ax.text(45, 45, "gasförmig", fontsize=12, color=COL_GAS, weight="bold", ha="center", bbox=box)
    ax.text(46, 108, "überkritisch", fontsize=11, color=COL_SUP, weight="bold", ha="center", bbox=box)


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.0), sharey=True)

# -- links: reines CO2 --
hintergrund(ax1)
ax1.plot(T_s, p_s, color=COL_REIN, lw=2.0, zorder=3, label="Siedelinie reines CO₂")
ax1.plot(T_krit, p_krit, "o", color=COL_REIN, ms=8, zorder=5, mec="white", mew=1.5)
ax1.annotate(f"kritischer Punkt\n{T_krit:.1f} °C / {p_krit:.1f} bar", (T_krit, p_krit),
             textcoords="offset points", xytext=(-130, 18), fontsize=8.5, color=COL_REIN, bbox=box,
             arrowprops=dict(arrowstyle="-", color=COL_REIN, lw=0.7))
ax1.set_title("Reines CO₂")
ax1.set_ylabel("Druck [bar]")

# -- rechts: Gemisch --
hintergrund(ax2)
huelle = list(zip(pg["T_tau"], pg["p_tau"])) + list(zip(pg["T_blase"], pg["p_blase"]))
ax2.add_patch(plt.Polygon(huelle, closed=True, fc=COL_GEM, alpha=0.12, ec="none", zorder=1))
ax2.add_patch(plt.Polygon(huelle, closed=True, fc="none", ec=COL_GEM, hatch="///", lw=0,
                          alpha=0.35, zorder=1))
ax2.plot(T_s, p_s, color=COL_REIN, lw=1.2, ls="--", zorder=3, label="Siedelinie reines CO₂")
ax2.plot(pg["T_blase"], pg["p_blase"], color=COL_GEM, lw=2.0, zorder=4, label="Blasenlinie Gemisch")
ax2.plot(pg["T_tau"], pg["p_tau"], color=COL_GEM, lw=2.0, ls="-.", zorder=4, label="Taulinie Gemisch")
ax2.axhline(p_cb, color=COL_GEM, lw=0.9, ls=":", zorder=2, label=f"Cricondenbar ({p_cb:.1f} bar)")
ax2.plot(T_krit_G, p_krit_G, "o", color=COL_GEM, ms=8, zorder=5, mec="white", mew=1.5)
ax2.annotate(f"krit. Punkt Gemisch\n{T_krit_G:.1f} °C / {p_krit_G:.1f} bar", (T_krit_G, p_krit_G),
             textcoords="offset points", xytext=(-140, 24), fontsize=8.5, color=COL_GEM, bbox=box,
             arrowprops=dict(arrowstyle="-", color=COL_GEM, lw=0.7))
ax2.text(-20, 30, "zweiphasig", fontsize=10, color=COL_GEM, weight="bold", ha="center", bbox=box)
ax2.annotate("", xy=(15, p_bl15), xytext=(15, p_s15),
             arrowprops=dict(arrowstyle="->", color="#333333", lw=1.4))
ax2.text(16.5, 0.5 * (p_s15 + p_bl15), f"+{p_bl15 - p_s15:.0f} bar", fontsize=9, va="center", bbox=box)
ax2.set_title("Worst-Case-Gemisch (95 mol-% CO₂)")

for ax in (ax1, ax2):
    ax.set_xlim(Tmin, Tmax)
    ax.set_ylim(Pmin, Pmax)
    ax.set_xlabel("Temperatur [°C]")
    ax.grid(alpha=0.25, zorder=1)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.92)

fig.tight_layout()
fig.savefig(gb.ABB / "abb_G02_phasendiagramm_rein_vs_gemisch.png", dpi=175)
plt.close(fig)
print("gespeichert: abb_G02_phasendiagramm_rein_vs_gemisch.png")

json.dump({
    "krit_rein": {"T": T_krit, "p": p_krit},
    "krit_gemisch": {"T": float(T_krit_G), "p": float(p_krit_G)},
    "cricondenbar": {"T": float(T_cb), "p": float(p_cb)},
    "15C": {"siededruck_rein": p_s15, "taudruck_gemisch": float(p_tau15),
            "blasendruck_gemisch": float(p_bl15)},
}, open(gb.ABB / "G02_rein_vs_gemisch.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
