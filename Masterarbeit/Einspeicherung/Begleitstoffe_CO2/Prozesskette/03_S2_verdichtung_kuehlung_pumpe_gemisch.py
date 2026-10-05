# -*- coding: utf-8 -*-
"""
Schritt 3 S2 (Gemisch) - gasförmige Anlieferung: verdichten, überkritisch kühlen, pumpen
============================================================================
Dieselbe Rechnung wie die Excel-Mappe "CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx"
(Blatt Einspeicherung S2). Alle Annahmen und Bausteine stehen in
Grundlagen/einspeicherung_bausteine.py.

  S2 gasförmig:  Verdichter 1 (30 -> 50 bar) -> Zwischenkühler (26 °C)
                 -> Verdichter 2 (50 -> 91 bar) -> Kühler (91 bar, 26 °C)
                 -> Pumpe (91 bar -> Bohrlochkopf)
Bei 91 bar liegt das Gemisch über der Cricondenbar (82,2 bar): der Kühler
kreuzt kein Zweiphasengebiet, die Pumpe saugt einphasig dichtes CO₂ an. Warum
dieser Weg (Pfad B) und nicht verflüssigen bei 80 bar (A), durchverdichten (C)
oder tiefkalt verflüssigen (D): 04_phasenpfade_vergleich.py und
Handbuch_Einspeicherung.docx (Kap. 8.6).

Prüfungen wie in der Excel-Mappe:
  - höchstens 95 °C je Verdichterstufe (Q-016)
  - Realgasfaktor am Eintritt jeder Verdichterstufe Z > 0,65 (Siemens Energy,
    E-Mail-Auskunft 08/2026); Literaturrichtwert Z ≥ 0,7 (Q-017 S. 43) zum Vergleich.
    Für die Pumpe gilt stattdessen die Mindestdichte.
  - Zwischendruck mindestens 3 bar unter der Taulinie bei 26 °C (kein Kondensat)
  - Kühldruck mindestens 3 bar über der Cricondenbar (keine Phasengrenze)
  - Dichte am Pumpeneintritt ≥ 500 kg/m³ (Q-121 S. 2, Q-001 Kap. 5.2)
Der Kopfdruck kommt aus der Gassäule (Rechnung und Kontrolle: 03_S1_pumpe_gemisch.py).
S1 wird hier nur für die beiden Diagramme mitgezeichnet. Dieselbe Kette wird zum
Vergleich auch für reines CO₂ gerechnet. Zum Schluss werden die Ergebnisse mit den
Werten der Excel-Mappe verglichen.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parents[1]          # Begleitstoffe_CO2
sys.path.insert(0, str(ORDNER / "Grundlagen"))         # gemisch_worstcase, einspeicherung_bausteine
ABB = ORDNER / "Abbildungen"                           # Abbildungen und Ergebnisdateien

import einspeicherung_bausteine as eb
import gemisch_worstcase as gw

REIN, GEM = eb.ReinCO2(), eb.Gemisch()

# Werte der Excel-Mappe (Gemisch, Stand 01.10.2026) zur Kontrolle
EXCEL = dict(S2=66.1669, T_V1=57.500, T_V2=77.377, T_P=31.750)


def ok(bedingung):
    return "✔" if bedingung else "✘"


def z_text(Z):
    """Realgasfaktor am Verdichtereintritt: Siemens-Grenze (maßgebend) und Q-017 zum Vergleich."""
    return f"Z_ein {Z:.3f} {ok(Z > eb.Z_MIN)} (Siemens > {eb.Z_MIN}; Q-017 ≥ {eb.Z_Q017}: {ok(Z >= eb.Z_Q017)})"


def kette_S2(stoff, p_kopf):
    """S2: 2 Stufen bis P_UEK, Kühler bei P_UEK auf T_K, Pumpe auf den Kopfdruck."""
    p_zw, V1, ZK, V2 = eb.zweistufig(stoff, eb.P_UEK, p_zw=eb.P_ZW)
    K = eb.kuehler(stoff, eb.P_UEK, V2["h2"], eb.T_K)
    P = eb.stufe(stoff, eb.P_UEK, eb.T_K, p_kopf, eb.eta_P)
    return dict(p_zw=p_zw, V1=V1, ZK=ZK, V2=V2, K=K, P=P, ein=eb.pumpeneintritt(stoff, eb.P_UEK, eb.T_K),
                w=V1["w"] + V2["w"] + P["w"], q=ZK["q"] + K["q"],
                pfad=[(eb.T_S2, eb.p_S2), (V1["T2"], p_zw), (eb.T_K, p_zw), (V2["T2"], eb.P_UEK),
                      (eb.T_K, eb.P_UEK), (P["T2"], p_kopf)])


# ---- 1) Rechnen: Gemisch (Excel) und reines CO2 (Vergleich) ------------------
erg = {}
for stoff in (GEM, REIN):
    p_kopf, _ = eb.gassaeule(stoff, eb.P_MAX_LCCS)
    S1 = eb.stufe(stoff, eb.p_S1, eb.T_S1, p_kopf, eb.eta_P)          # nur für die Diagramme
    S2 = kette_S2(stoff, p_kopf)
    m_min, m_max = eb.massenstrom(stoff)
    p_tau_ZK = stoff.taudruck(eb.T_K)
    erg[stoff.name] = dict(p_kopf=p_kopf, S1=S1, S2=S2, m=(m_min, m_max))

    V1, ZK, V2, K, P, e = S2["V1"], S2["ZK"], S2["V2"], S2["K"], S2["P"], S2["ein"]
    print(f"\n==== {stoff.name} ====")
    print(f"Kopfdruck (Gassäule, 210 bar unten): {p_kopf:.2f} bar")
    print(f"S2 (verdichten -> überkritisch kühlen -> pumpen, Kühlung auf {eb.T_K:.0f} °C):")
    print(f"   Verdichter 1 {eb.p_S2:.0f} -> {S2['p_zw']:.0f} bar: T_aus {V1['T2']:.1f} °C {ok(V1['T2'] <= eb.T_MAX_STUFE)}, "
          f"{z_text(V1['Z1'])}, w = {V1['w']:.2f} kJ/kg")
    abst = (p_tau_ZK - S2["p_zw"]) if not np.isnan(p_tau_ZK) else float("inf")
    print(f"   Zwischenkühler {S2['p_zw']:.0f} bar -> {eb.T_K:.0f} °C: q = {ZK['q']:.2f} kJ/kg, "
          f"{abst:.1f} bar unter der Taulinie {ok(abst >= eb.U_PG)}")
    print(f"   Verdichter 2 {S2['p_zw']:.0f} -> {eb.P_UEK:.0f} bar: T_aus {V2['T2']:.1f} °C {ok(V2['T2'] <= eb.T_MAX_STUFE)}, "
          f"{z_text(V2['Z1'])}, w = {V2['w']:.2f} kJ/kg")
    print(f"   Kühler {eb.P_UEK:.0f} bar -> {eb.T_K:.0f} °C: q = {K['q']:.2f} kJ/kg, "
          f"{eb.P_UEK - stoff.P_GRENZE:.1f} bar über der Phasengrenze {ok(eb.P_UEK - stoff.P_GRENZE >= eb.U_PG)}, "
          f"ρ = {e['rho']:.0f} kg/m³ {ok(e['rho'] >= eb.RHO_MIN)}")
    print(f"   Pumpe {eb.P_UEK:.0f} -> {p_kopf:.2f} bar: T_aus {P['T2']:.2f} °C, w = {P['w']:.2f} kJ/kg")
    print(f"   Summe w = {S2['w']:.2f} kJ/kg, q = {S2['q']:.1f} kJ/kg, "
          f"Leistung {m_min * S2['w']:.0f}-{m_max * S2['w']:.0f} kW, Kühlleistung {m_min * S2['q']:.0f}-{m_max * S2['q']:.0f} kW")

M, R = erg[GEM.name], erg[REIN.name]

# ---- 2) Auswirkungen des Gemischs --------------------------------------------
w_CO2 = gw.MOLANTEILE[0] * PropsSI("M", "CO2") / gw.gemisch().molar_mass()   # Massenanteil CO2
print("\n==== Gemisch gegenüber reinem CO₂ (gleiche Kette) ====")
print(f"CO₂-Massenanteil im Gemisch: {100 * w_CO2:.1f} %")
wr, wg = R["S2"]["w"], M["S2"]["w"]
print(f"S2 gesamt  rein {wr:6.2f} | Gemisch {wg:6.2f} kJ/kg ({100 * (wg / wr - 1):+.0f} %)")

# ---- 3) Kontrolle gegen die Excel-Mappe -------------------------------------
werte = dict(S2=M["S2"]["w"], T_V1=M["S2"]["V1"]["T2"], T_V2=M["S2"]["V2"]["T2"], T_P=M["S2"]["P"]["T2"])
abw = max(abs(werte[k] - EXCEL[k]) for k in EXCEL)
print(f"\nKontrolle gegen die Excel-Mappe: größte Abweichung {abw:.3f} {ok(abw < 0.01)}  "
      + ", ".join(f"{k} {werte[k]:.3f}" for k in EXCEL))

# ---- 4) Diagramm 1: Einspeicherpfade im Phasendiagramm des Gemischs ---------
ROT, GRUEN, TUERKIS, ORANGE = "#CA220E", "#007335", "#00B0B0", "#EE7203"
pg = GEM.pg
T_s = np.linspace(PropsSI("Ttriple", "CO2"), PropsSI("Tcrit", "CO2"), 150)
p_s = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_s]) / 1e5

fig, ax = plt.subplots(figsize=(11, 7))
ax.plot(T_s - 273.15, p_s, color="#8C8C8C", lw=1.2, zorder=3, label="Sättigungslinie reines CO₂ (Vergleich)")
huelle_T = np.concatenate([pg["T_tau"], pg["T_blase"]])
huelle_p = np.concatenate([pg["p_tau"], pg["p_blase"]])
ax.fill(huelle_T, huelle_p, fc=ROT, alpha=0.15, lw=0, zorder=1)
ax.plot(huelle_T, huelle_p, color=ROT, lw=2.0, zorder=4, label="Zweiphasengebiet Gemisch")
ax.plot(*pg["krit"], "o", color=ROT, ms=7, markeredgecolor="white", zorder=5)
ax.axhline(GEM.P_GRENZE, color=ROT, lw=0.8, ls=":", zorder=2)
ax.text(-18, GEM.P_GRENZE + 1.5, "Cricondenbar 82,2 bar", color=ROT, fontsize=8)

ax.plot([eb.T_S1, M["S1"]["T2"]], [eb.p_S1, M["p_kopf"]], "-D", color=GRUEN, lw=2.5, ms=6, zorder=7,
        label="S1: Pumpe")
ax.plot(*zip(*M["S2"]["pfad"]), "-o", color=TUERKIS, lw=2.5, ms=6, zorder=6,
        label="S2: verdichten → überkritisch kühlen → pumpen")

txt = dict(fontsize=8.5, color="#303030", zorder=8)
ax.text(eb.T_S2 + 2, eb.p_S2 - 5, "S2 Netzübergabe", **txt)
ax.text(M["S2"]["V1"]["T2"] + 2, eb.P_ZW - 4, "Verdichter 1", **txt)
ax.text(eb.T_K - 21, eb.P_ZW + 1, "Zwischenkühler", **txt)
ax.text(M["S2"]["V2"]["T2"] + 2, eb.P_UEK - 4, "Verdichter 2", **txt)
ax.text(eb.T_K - 30, eb.P_UEK - 4, "Kühler 91 bar → Pumpe", **txt)
ax.text(eb.T_S1 - 19, eb.p_S1 + 2, "S1 Netzübergabe", **txt)
ax.text(5, M["p_kopf"] + 4, f"Bohrlochkopf {M['p_kopf']:.1f} bar".replace(".", ","), **txt)
ax.axhline(M["p_kopf"], color=GRUEN, lw=0.8, ls=":", zorder=2)
bereich = dict(fontsize=11, weight="bold", color="#9A9A9A", ha="center", zorder=2)
ax.text(-5, 110, "flüssig / dicht", **bereich)
ax.text(80, 20, "gasförmig", **bereich)
ax.text(80, 110, "überkritisch", **bereich)
ax.set_xlim(-20, 110)
ax.set_ylim(0, 130)
ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("Einspeicherpfade S1 und S2 im p-T-Diagramm des Worst-Case-Gemischs", fontsize=11)
ax.grid(alpha=0.3, zorder=1)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(ABB / "abb_einspeicherpfad_gemisch.png", dpi=170)
print("\ngespeichert: abb_einspeicherpfad_gemisch.png")

# ---- 5) Diagramm 2: spezifische Arbeit rein vs. Gemisch --------------------
zeilen = []
for e, name in ((R, "reines CO₂"), (M, "Gemisch")):
    zeilen += [(f"S1 {name}", [0, 0, e["S1"]["w"]]),
               (f"S2 {name}", [e["S2"]["V1"]["w"], e["S2"]["V2"]["w"], e["S2"]["P"]["w"]])]
teile = [("Verdichter 1. Stufe", ORANGE), ("Verdichter 2. Stufe", "#F4B183"), ("Pumpe", GRUEN)]
fig2, ax2 = plt.subplots(figsize=(9, 3.8))
namen = [z[0] for z in zeilen]
werte_w = np.array([z[1] for z in zeilen], dtype=float)
links = np.zeros(len(zeilen))
for j, (tname, farbe) in enumerate(teile):
    ax2.barh(namen, werte_w[:, j], left=links, color=farbe, label=tname, height=0.6)
    links += werte_w[:, j]
for y, summe in enumerate(links):
    ax2.text(summe + 1, y, f"{summe:.1f} kJ/kg".replace(".", ","), va="center", fontsize=8.5, weight="bold")
ax2.invert_yaxis()
ax2.set_xlim(0, links.max() * 1.18)
ax2.set_xlabel("spezifische Arbeit bis Bohrlochkopf [kJ/kg]")
ax2.set_title("Spezifische Arbeit: reines CO₂ vs. Worst-Case-Gemisch (gleiche Kette)", fontsize=11)
ax2.grid(axis="x", alpha=0.3)
ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=8, frameon=False)
fig2.tight_layout()
fig2.savefig(ABB / "abb_arbeit_rein_vs_gemisch.png", dpi=170)
print("gespeichert: abb_arbeit_rein_vs_gemisch.png")
