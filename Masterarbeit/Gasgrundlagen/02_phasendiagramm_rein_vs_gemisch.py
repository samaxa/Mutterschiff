# -*- coding: utf-8 -*-
"""
G02 - Phasendiagramm des Worst-Case-Gemischs (reines CO2 als gestrichelte Siedelinie)
============================================================================
Für das Grundlagenkapitel: nur das Gemisch, reines CO2 nur noch als
gestrichelte Siedelinie (das reine Phasendiagramm zeigt G01). Man sieht, was
5 mol-% Begleitstoffe ändern: aus der Siedelinie wird ein Zweiphasengebiet zwischen
Tau- und Blasenlinie, der kritische Punkt verschiebt sich, und der
höchste Druck des Zweiphasengebiets (Cricondenbar) liegt über dem
kritischen Druck von reinem CO2.
Die Anhebung des Blasendrucks bei 15 °C (+21 bar gegenüber reinem CO2)
steht nur im Text, nicht in der Grafik.

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
print(f"Cricondentherm Gemisch:   {pg['cricondentherm'][0]:5.1f} °C / {pg['cricondentherm'][1]:5.1f} bar")
print(f"bei 15 °C: Siededruck rein {p_s15:.1f} bar | Gemisch Tau {p_tau15:.1f} bar, "
      f"Blase {p_bl15:.1f} bar -> Zweiphasengebiet {p_bl15 - p_tau15:.1f} bar breit, "
      f"Blasenlinie {p_bl15 - p_s15:+.1f} bar gegenüber rein")

Tmin, Tmax, Pmin, Pmax = -55.0, 60.0, 0.0, 120.0
C_GAS, C_FLUE, C_SUP = "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_GAS, COL_FLUE, COL_SUP, COL_REIN, COL_GEM = "#164a73", "#007335", "#a3480b", "#00304F", "#CA220E"
box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8)


def hintergrund(ax):
    """Phasengebiete des Gemischs: flüssig oberhalb der Blasenlinie, gasförmig unterhalb
    der Taulinie, überkritisch oberhalb von kritischer Temperatur und kritischem Druck
    des Gemischs. Das Zweiphasengebiet dazwischen wird separat schraffiert."""
    i = np.argsort(pg["p_tau"])                      # Taulinie: Druck steigt bis zum krit. Punkt
    T_tau, p_tau = pg["T_tau"][i], pg["p_tau"][i]
    j = np.argsort(pg["T_blase"])                    # Blasenlinie: Temperatur steigt bis zum krit. Punkt
    T_bl, p_bl = pg["T_blase"][j], pg["p_blase"][j]
    T0 = min(Tmin, T_tau[0], T_bl[0]) - 1.0
    gas = [(T0, Pmin), (Tmax, Pmin), (Tmax, p_krit_G), (T_krit_G, p_krit_G)]
    gas += list(zip(T_tau[::-1], p_tau[::-1])) + [(T0, p_tau[0])]
    ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))
    flue = [(T0, p_bl[0])] + list(zip(T_bl, p_bl)) + [(T_krit_G, p_krit_G), (T_krit_G, Pmax), (T0, Pmax)]
    ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))
    ax.add_patch(plt.Rectangle((T_krit_G, p_krit_G), Tmax - T_krit_G, Pmax - p_krit_G,
                               fc=C_SUP, ec="none", zorder=0))
    ax.text(-30, 95, "flüssig", fontsize=12, color=COL_FLUE, weight="bold", ha="center", bbox=box)
    ax.text(45, 45, "gasförmig", fontsize=12, color=COL_GAS, weight="bold", ha="center", bbox=box)
    ax.text(45, 108, "überkritisch", fontsize=11, color=COL_SUP, weight="bold", ha="center", bbox=box)


# Nur das Gemisch: reines CO2 steht schon in abb_G01_phasendiagramm_co2.png und ist hier
# nur noch als gestrichelte Siedelinie angedeutet. Die Flächen gehören zum Gemisch. Markiert wird nur der kritische Punkt
# des Gemischs; Cricondenbar und Cricondentherm liegen knapp daneben und werden im Text
# beschrieben.
fig, ax2 = plt.subplots(figsize=(7.4, 5.6))
hintergrund(ax2)
huelle = list(zip(pg["T_tau"], pg["p_tau"])) + list(zip(pg["T_blase"], pg["p_blase"]))
ax2.add_patch(plt.Polygon(huelle, closed=True, fc=COL_GEM, alpha=0.12, ec="none", zorder=1))
ax2.add_patch(plt.Polygon(huelle, closed=True, fc="none", ec=COL_GEM, hatch="///", lw=0,
                          alpha=0.35, zorder=1))
ax2.plot(T_s, p_s, color=COL_REIN, lw=1.2, ls="--", zorder=3, label="Siedelinie reines CO₂")
ax2.plot(pg["T_blase"], pg["p_blase"], color=COL_GEM, lw=2.0, zorder=4, label="Blasenlinie Gemisch")
ax2.plot(pg["T_tau"], pg["p_tau"], color=COL_GEM, lw=2.0, ls="-.", zorder=4, label="Taulinie Gemisch")
ax2.plot(T_krit_G, p_krit_G, "o", color=COL_GEM, ms=8, zorder=5, mec="white", mew=1.5)
ax2.annotate("kritischer Punkt Gemisch\n" + f"{T_krit_G:.1f} °C / {p_krit_G:.1f} bar".replace(".", ","),
             (T_krit_G, p_krit_G), textcoords="data", xytext=(-8, 106), ha="left", va="center",
             fontsize=9, color=COL_GEM, bbox=box, arrowprops=dict(arrowstyle="-", color=COL_GEM, lw=0.7))
ax2.text(-20, 30, "zweiphasig", fontsize=11, color=COL_GEM, weight="bold", ha="center", bbox=box)
ax2.set_xlim(Tmin, Tmax)
ax2.set_ylim(Pmin, Pmax)
ax2.set_xlabel("Temperatur [°C]", fontsize=11)
ax2.set_ylabel("Druck [bar]", fontsize=11)
ax2.tick_params(labelsize=10)
ax2.grid(alpha=0.25, zorder=1)
ax2.legend(loc="lower right", fontsize=9, framealpha=0.95)

fig.tight_layout()
fig.savefig(gb.ABB / "abb_G02_phasendiagramm_rein_vs_gemisch.png", dpi=175)
plt.close(fig)
print("gespeichert: abb_G02_phasendiagramm_rein_vs_gemisch.png")

json.dump({
    "krit_rein": {"T": T_krit, "p": p_krit},
    "krit_gemisch": {"T": float(T_krit_G), "p": float(p_krit_G)},
    "cricondenbar": {"T": float(T_cb), "p": float(p_cb)},
    "cricondentherm": {"T": float(pg["cricondentherm"][0]), "p": float(pg["cricondentherm"][1])},
    "15C": {"siededruck_rein": p_s15, "taudruck_gemisch": float(p_tau15),
            "blasendruck_gemisch": float(p_bl15)},
}, open(gb.ABB / "G02_rein_vs_gemisch.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
