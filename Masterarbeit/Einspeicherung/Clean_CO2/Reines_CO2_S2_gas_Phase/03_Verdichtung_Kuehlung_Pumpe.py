# -*- coding: utf-8 -*-
"""
Schritt 2 - Verdichtung, Kühlung, Pumpe: Netzübergabe -> Bohrlochkopf (Szenario 2, gasförmig, reines CO₂)
============================================================================
Eingangszustand: 30 bar / 15 °C, unverändert aus Schritt 01_02 (gasförmig).
Gas lässt sich nicht pumpen, deshalb die Kette - seit 15.10.2026 DERSELBE Weg wie beim
Gemisch (Pfad B), damit rein und Gemisch nur im Stoff verschieden sind:

  Verdichter 1 (30 -> 55 bar) -> Zwischenkühler (40 °C) -> Verdichter 2 (55 -> 91 bar)
  -> Kühler (91 bar, 26 °C) -> Pumpe (91 bar -> Zieldruck im Betrieb)

Warum zwei verschiedene Kühltemperaturen (Besprechung K. Vosbeck 15.10.2026, Pkt. 1):
  Zwischenkühler  40 °C   Zweck: Verdichterarbeit und Austrittstemperatur (≤ 95 °C, Q-016 S. 4).
                          Q-017 S. 37: Soll-Kühltemperatur CO₂ 40 °C; Q-063 Kap. 5.1: ≤ 40 °C.
                          Kälter senkt Z am Eintritt Stufe 2 unter 0,7 (Q-017 S. 44) bzw.
                          0,65 (Siemens Energy) - Zahlen: 05_kuehlung_begruendung.py.
  Kühler          26 °C   Zweck: Pumpe. Kühlwasser 20 °C + 6 K (Q-120 Folie 24); Pumpen auf
                          27-32 °C kühlen (Q-120 Folie 32). Bei 91 bar liegt die pseudo-
                          kritische Linie von reinem CO₂ bei ~40 °C - 40 °C wäre also genau
                          dort, wo die Dichte am stärksten schwankt.
Die frühere Annahme (20 °C nach jeder Stufe, Verflüssigen bei 60 bar; nach Q-016) ist
ersetzt: In Q-016 dient die Kühlung auf 20 °C der Wasserabscheidung vor der TEG-Trocknung
(nasses CO₂ aus der Abscheidung) - das CO₂ aus dem Netz ist bereits trocken. Verflüssigen
bei 60 bar bräuchte Kühlwasser ≤ 14 °C (Vergleich A unten).

Zieldruck: Kopfdruck im Betrieb (strömende Säule beim Einspeisen, 100.000 Nm³/h), nicht
mehr die ruhende Säule - Kaverne/Grundlagen/kaverne_bausteine.zieldruck_einspeisen().

Vergleich (wie 04_phasenpfade_vergleich.py für das Gemisch):
  A  verflüssigen bei 60 bar und 20 °C (Kühlwasser 14 °C bzw. Kältemaschine), Pumpe
  C  durchverdichten in 2 Stufen bis zum Kopfdruck, Zwischenkühlung 26 °C, keine Pumpe

Alle Bausteine: Begleitstoffe_CO2/Grundlagen/einspeicherung_bausteine.py (kette_S2).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

MASTER = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(MASTER / "Einspeicherung" / "Begleitstoffe_CO2" / "Grundlagen"))
sys.path.insert(0, str(MASTER / "Kaverne" / "Grundlagen"))
import einspeicherung_bausteine as eb   # noqa: E402
import kaverne_bausteine as kb          # noqa: E402

REIN = eb.ReinCO2()
ok = kb.ok

# ---- 1) Zieldruck ---------------------------------------------------------------
p_still = eb.kopfdruck(REIN)
betrieb = kb.zieldruck_einspeisen(kb.REIN, kb.TIEF, "S2", kb.raten(kb.REIN)["100.000 Nm³/h"])
p_kopf = betrieb["p_kopf"]
print(f"Zieldruck am Bohrlochkopf: Stillstand {p_still:.2f} bar, im Betrieb (S2, 100.000 Nm³/h) {p_kopf:.2f} bar "
      f"({p_kopf - p_still:+.2f} bar: wärmere, leichtere Säule; an der LCCS {betrieb['T_lccs']:.1f} °C)")

# ---- 2) Kette S2 (Pfad B) --------------------------------------------------------
S2 = eb.kette_S2(REIN, p_kopf)
V1, ZK, V2, K, P, e = S2["V1"], S2["ZK"], S2["V2"], S2["K"], S2["P"], S2["ein"]
m_min, m_max = eb.massenstrom(REIN)
print("\nSzenario 2 - reines CO₂, Pfad B:")
print(f"  Verdichter 1:    {eb.p_S2:.0f} -> {S2['p_zw']:.0f} bar, {eb.T_S2:.0f} -> {V1['T2']:.1f} °C "
      f"{ok(V1['T2'] <= eb.T_MAX_STUFE)} (≤ 95 °C), Z_ein {V1['Z1']:.3f}, w = {V1['w']:.2f} kJ/kg")
print(f"  Zwischenkühler:  {V1['T2']:.1f} -> {eb.T_ZK:.0f} °C bei {S2['p_zw']:.0f} bar, q = {ZK['q']:.2f} kJ/kg "
      f"({ZK['phase']}; {eb.T_ZK - kb.T_KRIT:.1f} K über T_krit -> kein Kondensat)")
print(f"  Verdichter 2:    {S2['p_zw']:.0f} -> {eb.P_UEK:.0f} bar, -> {V2['T2']:.1f} °C {ok(V2['T2'] <= eb.T_MAX_STUFE)}, "
      f"Z_ein {V2['Z1']:.3f} {ok(V2['Z1'] >= eb.Z_Q017)} (≥ 0,7 Q-017), w = {V2['w']:.2f} kJ/kg")
print(f"  Kühler:          {V2['T2']:.1f} -> {eb.T_K:.0f} °C bei {eb.P_UEK:.0f} bar, q = {K['q']:.2f} kJ/kg, "
      f"ρ = {e['rho']:.0f} kg/m³ {ok(e['rho'] >= eb.RHO_MIN)} (≥ 500 kg/m³)")
print(f"  Pumpe:           {eb.P_UEK:.0f} -> {p_kopf:.2f} bar, {eb.T_K:.0f} -> {P['T2']:.2f} °C, w = {P['w']:.2f} kJ/kg")
print(f"  Summe:           w = {S2['w']:.2f} kJ/kg, q = {S2['q']:.1f} kJ/kg; "
      f"Antrieb {m_min * S2['w']:.0f}-{m_max * S2['w']:.0f} kW, Kühlung {m_min * S2['q']:.0f}-{m_max * S2['q']:.0f} kW")

# ---- 3) Vergleich A (verflüssigen 60 bar / 20 °C) und C (durchverdichten) -----------
p_V, T_A = 60.0, 20.0
pzA, A1, AZK, A2 = eb.zweistufig(REIN, p_V, T_zk=T_A)
AV = eb.kuehler(REIN, p_V, A2["h2"], T_A)
AP = eb.stufe(REIN, p_V, T_A, p_kopf, eb.eta_P)
w_A = A1["w"] + A2["w"] + AP["w"]
C1 = eb.stufe(REIN, eb.p_S2, eb.T_S2, eb.P_ZW_DV, eb.eta_V1)
C2 = eb.stufe(REIN, eb.P_ZW_DV, eb.T_K, p_kopf, eb.eta_V2)
w_C = C1["w"] + C2["w"]
S1 = eb.stufe(REIN, eb.p_S1, eb.T_S1, kb.zieldruck_einspeisen(kb.REIN, kb.TIEF, "S1",
                                                             kb.raten(kb.REIN)["100.000 Nm³/h"])["p_kopf"], eb.eta_P)
print(f"\nVergleich: A verflüssigen 60 bar / 20 °C: w = {w_A:.2f} kJ/kg ({w_A / S2['w'] - 1:+.0%}), "
      f"braucht Kühlwasser ≤ 14 °C (Q-120 Folie 24: + 6 K)")
print(f"           C durchverdichten bis {p_kopf:.1f} bar: w = {w_C:.2f} kJ/kg ({w_C / S2['w'] - 1:+.0%}), "
      f"Stufe 2 {C2['T2']:.1f} °C {ok(C2['T2'] <= eb.T_MAX_STUFE)}")
print(f"           S1 (nur Pumpe): {S1['w']:.2f} kJ/kg")

# ---- 4) Diagramm 1: p-T mit den Pfaden -------------------------------------------
T_krit, p_krit = PropsSI("Tcrit", "CO2"), PropsSI("Pcrit", "CO2")
T_tripel, p_tripel = PropsSI("Ttriple", "CO2"), PropsSI("ptriple", "CO2")
T_krit_C, T_tripel_C = T_krit - 273.15, T_tripel - 273.15
p_krit_bar, p_tripel_bar = p_krit / 1e5, p_tripel / 1e5
T_saett = np.linspace(T_tripel, T_krit, 200)
p_saett_bar = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_saett]) / 1e5
T_saett_C = T_saett - 273.15


def sublimation_bar(T_K_):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K_ / T_tripel
    return p_tripel_bar * np.exp((T_tripel / T_K_) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K_):
    x = T_K_ / T_tripel - 1.0
    return p_tripel_bar * (1.0 + 1955.5390 * x + 2055.4593 * x**2)


Tmin, Tmax, Pmin, Pmax = -80.0, 110.0, 0.0, 130.0
T_sub = np.linspace(Tmin + 273.15, T_tripel, 150)
p_sub_bar, T_sub_C = sublimation_bar(T_sub), T_sub - 273.15
T_melt = np.linspace(T_tripel, T_tripel * 1.02, 100)
p_melt_bar, T_melt_C = schmelz_bar(T_melt), T_melt - 273.15
C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, ROT = "#5F2176", "#CA220E"
GRUEN, BLAU, HELLBLAU, VIOLETT = "#007335", "#0476D9", "#68AFE1", "#7030A0"

fig, ax = plt.subplots(figsize=(10, 6.5))
gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, p_krit_bar), (T_krit_C, p_krit_bar)]
gas += list(zip(T_saett_C[::-1], p_saett_bar[::-1])) + list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))
fest = [(Tmin, Pmax), (T_melt_C[-1], p_melt_bar[-1])] + list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
fest += list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(fest, closed=True, fc=C_FEST, ec="none", zorder=0))
flue = list(zip(T_saett_C, p_saett_bar)) + [(T_krit_C, Pmax), (T_melt_C[-1], Pmax)]
flue += list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))
ax.add_patch(plt.Rectangle((T_krit_C, p_krit_bar), Tmax - T_krit_C, Pmax - p_krit_bar, fc=C_SUP, ec="none", zorder=0))
ax.plot(T_sub_C, p_sub_bar, color="#333333", lw=1.5, zorder=3, label="Sublimationslinie")
ax.plot(T_saett_C, p_saett_bar, color="#00304F", lw=1.8, zorder=3, label="Sättigungslinie")
ax.plot(T_melt_C, p_melt_bar, color=COL_FEST, lw=1.5, zorder=3, label="Schmelzlinie")
ax.plot(T_tripel_C, p_tripel_bar, "o", color="black", ms=5, zorder=5)
ax.plot(T_krit_C, p_krit_bar, "o", color=ROT, ms=8, zorder=5)

pfad_S1 = [(eb.T_S1, eb.p_S1), (S1["T2"], S1["p2"])]
pfad_A = [(eb.T_S2, eb.p_S2), (A1["T2"], pzA), (T_A, pzA), (A2["T2"], p_V), (T_A, p_V), (AP["T2"], p_kopf)]
pfad_C = [(eb.T_S2, eb.p_S2), (C1["T2"], eb.P_ZW_DV), (eb.T_K, eb.P_ZW_DV), (C2["T2"], p_kopf)]
ax.plot(*zip(*pfad_S1), "-D", color=GRUEN, lw=2.5, ms=6, zorder=6, label="S1: Pumpe")
ax.plot(*zip(*S2["pfad"]), "-o", color=BLAU, lw=2.4, ms=6, zorder=7,
        label="S2 (B): 2 Stufen, ZK 40 °C → Kühler 91 bar / 26 °C → Pumpe")
ax.plot(*zip(*pfad_A), ":o", color=HELLBLAU, lw=2.0, ms=4, zorder=7, label="Vergleich A: verflüssigen 60 bar / 20 °C")
ax.plot(*zip(*pfad_C), "--o", color=VIOLETT, lw=1.5, ms=4, zorder=6, label="Vergleich C: durchverdichten")
txt = dict(fontsize=8, weight="bold", color="#404040", ha="center", va="center", zorder=8)
ax.text(eb.T_S2, eb.p_S2 - 5, "S2 Netzübergabe", **txt)
ax.text(eb.T_ZK - 15, S2["p_zw"] + 2, "Zwischenkühler", **txt)
ax.text(eb.T_K - 13, eb.P_UEK - 4, "Kühler 91 bar", **txt)
ax.text(-3, 91, "S1 Netzübergabe", **txt)
ax.text(20, p_kopf + 5, f"Zieldruck im Betrieb {kb.de(p_kopf)} bar", **txt)
big = dict(fontsize=12, weight="bold", color="#404040", ha="center", va="center", zorder=2)
ax.text(-71, 70, "fest", **big)
ax.text(-30, 105, "flüssig", **big)
ax.text(72, 12, "gasförmig", **big)
ax.text(85, 125, "überkritisch", **big)
ax.set(xlabel="Temperatur [°C]", ylabel="Druck [bar]", xlim=(Tmin, Tmax), ylim=(Pmin, Pmax),
       title="Einspeicherung reines CO₂: S1, S2 (Pfad B) und Vergleich A / C")
ax.set_xticks(np.arange(Tmin, Tmax + 1, 20))
ax.set_yticks(np.arange(Pmin, Pmax + 1, 10))
ax.grid(color="white", lw=0.5, zorder=1)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(Path(__file__).resolve().parent / "abb_verdichtung_S2.png", dpi=160)
print("\ngespeichert: abb_verdichtung_S2.png")

# ---- 5) Diagramm 2: spezifische Arbeit -------------------------------------------
wege = ["S1 dichte Phase", "S2 (B): 2 Stufen +\nKühler 91 bar + Pumpe", "Vergleich A:\nverflüssigen 60 bar",
        "Vergleich C:\ndurchverdichten"]
anteile = [("Verdichter 1. Stufe", [0.0, V1["w"], A1["w"], C1["w"]], "#EE7203"),
           ("Verdichter 2. Stufe", [0.0, V2["w"], A2["w"], C2["w"]], "#F4B183"),
           ("Pumpe", [S1["w"], P["w"], AP["w"], 0.0], GRUEN)]
fig2, ax2 = plt.subplots(figsize=(8.5, 4.6))
links = np.zeros(len(wege))
for name, werte, farbe in anteile:
    werte = np.array(werte)
    bars = ax2.barh(wege, werte, left=links, color=farbe, label=name, height=0.55)
    for b, v in zip(bars, werte):
        if v > 3:
            ax2.text(b.get_x() + b.get_width() / 2, b.get_y() + b.get_height() / 2, f"{v:.1f}".replace(".", ","),
                     ha="center", va="center", fontsize=8)
    links += werte
for y, summe in enumerate(links):
    ax2.text(summe + 1, y, f"{summe:.2f} kJ/kg".replace(".", ","), va="center", fontsize=9, weight="bold")
ax2.invert_yaxis()
ax2.set_xlim(0, max(links) * 1.2)
ax2.set_xlabel("spezifische Arbeit bis zum Bohrlochkopf (Zieldruck im Betrieb) [kJ/kg]")
ax2.set_title("Spezifische Arbeit bis zum Bohrlochkopf (reines CO₂)", fontsize=11)
ax2.grid(axis="x", alpha=0.3)
ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=8, frameon=False)
fig2.tight_layout()
fig2.savefig(Path(__file__).resolve().parent / "abb_vergleich_arbeit_S2.png", dpi=160)
print("gespeichert: abb_vergleich_arbeit_S2.png")
