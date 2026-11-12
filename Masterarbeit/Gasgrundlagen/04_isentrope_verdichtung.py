# -*- coding: utf-8 -*-
"""
G04 - Isentrope Verdichtung und Pumpen: wie viel Arbeit braucht CO2?
============================================================================
Frage aus der Präsentation: Braucht CO2 mehr oder weniger Energie als
Erdgas oder Wasserstoff, und was passiert beim Verdichten?

Idealer Verdichter (isentrop, s = konst.), einstufig, ohne Kühlung, von
10 bar / 15 °C auf 210 bar. Das ist ein Vergleichsprozess, keine Auslegung:
die reale Verdichtung mit zwei Stufen, Zwischenkühlung und Wirkungsgrad
steht in Einspeicherung/. Die spezifische Arbeit ist die Enthalpiedifferenz
    w_s = h(p, s0) - h(p0, T0)          [kJ/kg]
und je Normkubikmeter
    w_s,N = w_s · ρ_N                   [kJ/Nm³]

Pumpe: CO2 in dichter Phase (91 bar / 15 °C, Anlieferung S1) auf 210 bar.
Weil die Dichte hoch ist und sich kaum ändert, gilt w ≈ Δp / ρ.

Warum wird es beim Verdichten so heiß, beim Drosseln aber nur mäßig kalt?
Beim Verdichten zählt µ_S = (∂T/∂p)_s, beim Drosseln µ_JT = (∂T/∂p)_h.
Bei 10 bar / 15 °C ist µ_S für CO2 mehr als fünfmal so groß wie µ_JT.

Annahmen: gasgrundlagen_bausteine.py · Ergebnisse: Abbildungen/G04_verdichtung.json
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import gasgrundlagen_bausteine as gb

erg = {}
print(f"Isentrope Verdichtung {gb.P_START_V:.0f} bar / {gb.T_START_V:.0f} °C -> {gb.P_ENDE_V:.0f} bar\n")
print(f"{'Stoff':<18}{'T_end °C':>9}{'w kJ/kg':>9}{'w kJ/Nm³':>10}{'w(91 bar) kJ/kg':>17}")
for k, (f, name, _) in gb.STOFFE.items():
    s0, h0, zeilen = gb.isentrope_verdichtung(k)
    z91 = gb.isentrope_verdichtung(k, p_liste=[gb.P_PUMPE_EIN])[2][0]
    erg[k] = {"s0": s0, "h0": h0, "zeilen": zeilen, "bis_91bar": z91,
              "kennwerte": gb.kennwerte(k)}
    e = zeilen[-1]
    print(f"{name:<18}{e['T']:9.1f}{e['w_kg']:9.1f}{e['w_Nm3']:10.1f}{z91['w_kg']:17.1f}")

pumpe = gb.pumpe_isentrop()
erg["pumpe_CO2"] = pumpe
w_gas_91_210 = erg["CO2"]["zeilen"][-1]["w_kg"] - erg["CO2"]["bis_91bar"]["w_kg"]
erg["CO2_gas_91_bis_210"] = w_gas_91_210
print(f"\nCO2 91 -> 210 bar: Pumpe (dicht, 15 °C) {pumpe['w_kg']:.1f} kJ/kg "
      f"(Näherung Δp/ρ: {pumpe['w_kg_naeherung']:.1f} kJ/kg), "
      f"Weiterverdichten des Gases {w_gas_91_210:.1f} kJ/kg")

# µ_S und µ_JT entlang der CO2-Verdichtung (wie Tabelle in der alten Mappe)
print("\nCO2 entlang der Verdichtung:   µ_S      µ_JT")
koeff = []
for r in erg["CO2"]["zeilen"]:
    if r["p"] in (10, 50, 100, 150, 210):
        z = gb.zustand("CO2", r["p"], r["T"])
        koeff.append({"p": r["p"], "T": r["T"], "mu_S": z["mu_S"], "mu_JT": z["mu_JT"]})
        print(f"  {r['p']:5.0f} bar / {r['T']:6.1f} °C  {z['mu_S']:6.2f}  {z['mu_JT']:6.2f}  K/bar")
erg["koeffizienten_CO2"] = koeff

# ---- Abbildung: T, w je kg (Balken), w je Nm³ ---------------------------------------
w_pumpweg = erg["CO2"]["bis_91bar"]["w_kg"] + pumpe["w_kg"]
erg["CO2_verdichten_kuehlen_pumpen"] = w_pumpweg
print(f"CO2 bis 91 bar verdichten, kühlen, pumpen: {w_pumpweg:.1f} kJ/kg "
      f"(statt {erg['CO2']['zeilen'][-1]['w_kg']:.1f} kJ/kg durchverdichten)")

fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1, 1.15, 1]})
for k, (f, name, farbe) in gb.STOFFE.items():
    z = [r for r in erg[k]["zeilen"] if r["p"] > gb.P_START_V]
    p = [gb.P_START_V] + [r["p"] for r in z]
    axs[0].plot(p, [gb.T_START_V] + [r["T"] for r in z], "-o", color=farbe, lw=1.8, ms=3.5, label=name)
    axs[2].plot(p, [0.0] + [r["w_Nm3"] for r in z], "-o", color=farbe, lw=1.8, ms=3.5, label=name)

balken = [("H₂ verdichten", erg["H2"]["zeilen"][-1]["w_kg"], "#164a73"),
          ("CH₄ verdichten", erg["CH4"]["zeilen"][-1]["w_kg"], "#E36C09"),
          ("CO₂ verdichten", erg["CO2"]["zeilen"][-1]["w_kg"], "#007335"),
          ("CO₂ bis 91 bar verdichten,\nkühlen, dann pumpen", w_pumpweg, "#7FB89A")]
y = range(len(balken))
axs[1].barh(list(y), [b[1] for b in balken], color=[b[2] for b in balken])
for i, b in enumerate(balken):
    axs[1].text(b[1] * 1.08, i, f"{b[1]:,.0f}".replace(",", "."), va="center", fontsize=9)
axs[1].set_yticks(list(y))
axs[1].set_yticklabels([b[0] for b in balken], fontsize=8.5)
axs[1].set_xscale("log")
axs[1].set_xlim(50, 2e4)
axs[1].set_xlabel("spez. Arbeit bis 210 bar [kJ/kg] (log.)")
axs[1].set_title("Arbeit je kg")

axs[0].set_ylabel("Temperatur am Austritt [°C]")
axs[0].set_title("Temperatur")
axs[2].set_ylabel("Arbeit je Normkubikmeter [kJ/Nm³]")
axs[2].set_title("Arbeit je Nm³")
for ax in (axs[0], axs[2]):
    ax.set_xlabel("Enddruck [bar]")
    ax.set_xlim(0, 220)
for ax in axs:
    ax.grid(alpha=0.25)
axs[0].legend(loc="upper left", fontsize=8.5)
fig.suptitle(f"Isentrope Verdichtung ab {gb.P_START_V:.0f} bar / {gb.T_START_V:.0f} °C "
             "(einstufig, ideal, ohne Kühlung)", fontsize=11)
fig.tight_layout()
fig.savefig(gb.ABB / "abb_G04_verdichtung_vergleich.png", dpi=175)
plt.close(fig)
print("\ngespeichert: abb_G04_verdichtung_vergleich.png")

json.dump(erg, open(gb.ABB / "G04_verdichtung.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
