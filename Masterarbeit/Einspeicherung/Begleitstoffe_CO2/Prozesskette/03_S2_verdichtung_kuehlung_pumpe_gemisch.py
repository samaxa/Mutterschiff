# -*- coding: utf-8 -*-
"""
Schritt 3 S2 (Gemisch und reines CO₂) - gasförmige Anlieferung: verdichten, überkritisch kühlen, pumpen
============================================================================
Dieselbe Rechnung wie die Excel-Mappen (Blatt "Einspeicherung S2"). Alle Annahmen und
Bausteine stehen in Grundlagen/einspeicherung_bausteine.py (kette_S2), der Zieldruck im
Betrieb kommt aus Kaverne/Grundlagen/kaverne_bausteine.py (zieldruck_einspeisen).

  S2 gasförmig:  Verdichter 1 (30 -> 55 bar) -> Zwischenkühler (40 °C)
                 -> Verdichter 2 (55 -> 91 bar) -> Kühler (91 bar, 26 °C)
                 -> Pumpe (91 bar -> Zieldruck im Betrieb)
Gleicher Weg und gleiche Kühllogik für reines CO₂ und Gemisch (Stand 15.10.2026).

Warum zwei verschiedene Kühltemperaturen (Besprechung K. Vosbeck 15.10.2026, Pkt. 1):
  Zwischenkühler 40 °C  Zweck: Verdichterarbeit und Austrittstemperatur. Q-017 S. 37
                        (Soll-Kühltemperatur 40 °C), Q-063 Kap. 5.1 (≤ 40 °C). Kälter
                        bringt wenig und senkt Z (Q-017 S. 19, S. 44).
  Kühler 26 °C          Zweck: Pumpe. Bei 91 bar liegt die pseudokritische Linie bei
                        ~40 °C (rein) bzw. ~33 °C (Gemisch); dort ist CO₂ extrem
                        kompressibel. Q-120 Folie 32: Pumpen auf 27-32 °C kühlen;
                        Q-120 Folie 24: Kühlwasser + 6 K -> 26 °C. Begründung mit
                        Zahlen: 05_kuehlung_begruendung.py.

Prüfungen (wie in der Excel-Mappe):
  - höchstens 95 °C je Verdichterstufe (Q-016 S. 4)
  - Realgasfaktor am Eintritt jeder Verdichterstufe Z > 0,65 (Siemens Energy,
    E-Mail-Auskunft 08/2026); Literaturrichtwert Z ≥ 0,7 (Q-017 S. 44) zum Vergleich
  - Zwischenkühler über T_krit (rein) bzw. Cricondentherm (Gemisch): kein Kondensat
  - Kühldruck mindestens 3 bar über der Cricondenbar (keine Phasengrenze)
  - Dichte am Pumpeneintritt ≥ 500 kg/m³ (Q-121 S. 2, Q-001 Kap. 5.2)

Ausgabe: Konsole, Abbildungen/abb_einspeicherpfad_gemisch.png, abb_arbeit_rein_vs_gemisch.png,
Abbildungen/s2_ergebnisse.json (-> Excel-Mappen, Blatt "Einspeicherung S2")
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

ORDNER = Path(__file__).resolve().parents[1]          # Begleitstoffe_CO2
sys.path.insert(0, str(ORDNER / "Grundlagen"))
sys.path.insert(0, str(ORDNER.parents[1] / "Kaverne" / "Grundlagen"))
ABB = ORDNER / "Abbildungen"
ABB.mkdir(exist_ok=True)

import einspeicherung_bausteine as eb   # noqa: E402
import gemisch_worstcase as gw          # noqa: E402
import kaverne_bausteine as kb          # noqa: E402

RATE_A = "100.000 Nm³/h"

# Werte der Excel-Mappe Gemisch (Stand 15.10.2026) zur Kontrolle
EXCEL = dict(S2=71.1302, T_V1=65.899, T_V2=84.713, T_P=34.406)


def ok(bedingung):
    return "✔" if bedingung else "✘"


def z_text(Z):
    return f"Z_ein {Z:.3f} {ok(Z > eb.Z_MIN)} (Siemens > {eb.Z_MIN}; Q-017 ≥ {eb.Z_Q017}: {ok(Z >= eb.Z_Q017)})"


erg = {}
for med in (kb.gemisch(), kb.REIN):
    stoff = med.stoff
    p_still = eb.kopfdruck(stoff, eb.P_MAX_LCCS)
    betrieb = {rate: kb.zieldruck_einspeisen(med, kb.TIEF, "S2", m) for rate, m in kb.raten(med).items()}
    p_kopf = betrieb[RATE_A]["p_kopf"]
    S2 = eb.kette_S2(stoff, p_kopf)
    s1 = kb.zieldruck_einspeisen(med, kb.TIEF, "S1", kb.raten(med)[RATE_A])     # nur fürs Diagramm
    S1 = eb.stufe(stoff, eb.p_S1, eb.T_S1, s1["p_kopf"], eb.eta_P)
    m_min, m_max = eb.massenstrom(stoff)
    T_grenze_zk = med.T_ct                       # T_krit bzw. Cricondentherm: darüber kein Kondensat
    erg[stoff.kurz] = dict(name=stoff.name, p_kopf_still=p_still, p_kopf=p_kopf,
                           betrieb={r: {k: v for k, v in b.items() if k not in ("profil", "pumpe")}
                                    for r, b in betrieb.items()},
                           S2={k: v for k, v in S2.items()}, S1=S1, p_kopf_S1=s1["p_kopf"], m=(m_min, m_max),
                           s_ZK=stoff.s(S2["p_zw"], eb.T_ZK), s_K=stoff.s(eb.P_UEK, eb.T_K),
                           s_ein=stoff.s(eb.p_S2, eb.T_S2), T_grenze_zk=T_grenze_zk, p_grenze=stoff.P_GRENZE)

    V1, ZK, V2, K, P, e = S2["V1"], S2["ZK"], S2["V2"], S2["K"], S2["P"], S2["ein"]
    print(f"\n==== {stoff.name} ====")
    print(f"Zieldruck: Stillstand {p_still:.2f} bar, Betrieb S2 " +
          ", ".join(f"{r} {b['p_kopf']:.2f} bar" for r, b in betrieb.items()) + f" -> Auslegung {p_kopf:.2f} bar")
    print(f"   Verdichter 1 {eb.p_S2:.0f} -> {S2['p_zw']:.0f} bar: T_aus {V1['T2']:.1f} °C {ok(V1['T2'] <= eb.T_MAX_STUFE)}, "
          f"{z_text(V1['Z1'])}, w = {V1['w']:.2f} kJ/kg")
    print(f"   Zwischenkühler {S2['p_zw']:.0f} bar -> {eb.T_ZK:.0f} °C: q = {ZK['q']:.2f} kJ/kg, "
          f"{eb.T_ZK - T_grenze_zk:.1f} K über {'T_krit' if not med.ist_gemisch else 'der Cricondentherm'} "
          f"{ok(eb.T_ZK > T_grenze_zk)} (kein Kondensat)")
    print(f"   Verdichter 2 {S2['p_zw']:.0f} -> {eb.P_UEK:.0f} bar: T_aus {V2['T2']:.1f} °C {ok(V2['T2'] <= eb.T_MAX_STUFE)}, "
          f"{z_text(V2['Z1'])}, w = {V2['w']:.2f} kJ/kg")
    print(f"   Kühler {eb.P_UEK:.0f} bar -> {eb.T_K:.0f} °C: q = {K['q']:.2f} kJ/kg, "
          f"{eb.P_UEK - stoff.P_GRENZE:.1f} bar über der Phasengrenze {ok(eb.P_UEK - stoff.P_GRENZE >= eb.U_PG)}, "
          f"ρ = {e['rho']:.0f} kg/m³ {ok(e['rho'] >= eb.RHO_MIN)}")
    print(f"   Pumpe {eb.P_UEK:.0f} -> {p_kopf:.2f} bar: T_aus {P['T2']:.2f} °C, w = {P['w']:.2f} kJ/kg")
    print(f"   Summe w = {S2['w']:.2f} kJ/kg, q = {S2['q']:.1f} kJ/kg, "
          f"Leistung {m_min * S2['w']:.0f}-{m_max * S2['w']:.0f} kW, Kühlleistung {m_min * S2['q']:.0f}-{m_max * S2['q']:.0f} kW")

M, R = erg["gem"], erg["rein"]
w_CO2 = gw.MOLANTEILE[0] * PropsSI("M", "CO2") / gw.gemisch().molar_mass()
print("\n==== Gemisch gegenüber reinem CO₂ (gleiche Kette) ====")
print(f"CO₂-Massenanteil im Gemisch: {100 * w_CO2:.1f} %")
print(f"S2 gesamt  rein {R['S2']['w']:6.2f} | Gemisch {M['S2']['w']:6.2f} kJ/kg ({100 * (M['S2']['w'] / R['S2']['w'] - 1):+.0f} %)")

werte = dict(S2=M["S2"]["w"], T_V1=M["S2"]["V1"]["T2"], T_V2=M["S2"]["V2"]["T2"], T_P=M["S2"]["P"]["T2"])
abw = max(abs(werte[k] - EXCEL[k]) for k in EXCEL)
print(f"\nKontrolle gegen die Excel-Mappe: größte Abweichung {abw:.3f} {ok(abw < 0.01)}  "
      + ", ".join(f"{k} {werte[k]:.3f}" for k in EXCEL))

# ---- Diagramm 1: Einspeicherpfade im Phasendiagramm des Gemischs ------------------------------
ROT, GRUEN, TUERKIS, ORANGE = "#CA220E", "#007335", "#00B0B0", "#EE7203"
pg = kb.gemisch().stoff.pg
T_s = np.linspace(PropsSI("Ttriple", "CO2"), PropsSI("Tcrit", "CO2"), 150)
p_s = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_s]) / 1e5
fig, ax = plt.subplots(figsize=(11, 7))
ax.plot(T_s - 273.15, p_s, color="#8C8C8C", lw=1.2, zorder=3, label="Sättigungslinie reines CO₂ (Vergleich)")
huelle_T = np.concatenate([pg["T_tau"], pg["T_blase"]])
huelle_p = np.concatenate([pg["p_tau"], pg["p_blase"]])
ax.fill(huelle_T, huelle_p, fc=ROT, alpha=0.15, lw=0, zorder=1)
ax.plot(huelle_T, huelle_p, color=ROT, lw=2.0, zorder=4, label="Zweiphasengebiet Gemisch")
ax.axhline(pg["cricondenbar"][1], color=ROT, lw=0.8, ls=":", zorder=2)
ax.text(-18, pg["cricondenbar"][1] + 1.5, "Cricondenbar 82,2 bar", color=ROT, fontsize=8)
ax.plot([eb.T_S1, M["S1"]["T2"]], [eb.p_S1, M["p_kopf_S1"]], "-D", color=GRUEN, lw=2.5, ms=6, zorder=7,
        label="S1: Pumpe")
ax.plot(*zip(*M["S2"]["pfad"]), "-o", color=TUERKIS, lw=2.5, ms=6, zorder=6,
        label="S2: verdichten (ZK 40 °C) → Kühler 91 bar / 26 °C → Pumpe")
txt = dict(fontsize=8.5, color="#303030", zorder=8)
ax.text(eb.T_S2 + 2, eb.p_S2 - 5, "S2 Netzübergabe", **txt)
ax.text(M["S2"]["V1"]["T2"] + 2, eb.P_ZW - 4, "Verdichter 1", **txt)
ax.text(eb.T_ZK - 22, eb.P_ZW + 1, "Zwischenkühler", **txt)
ax.text(M["S2"]["V2"]["T2"] + 2, eb.P_UEK - 4, "Verdichter 2", **txt)
ax.text(eb.T_K - 30, eb.P_UEK - 4, "Kühler 91 bar → Pumpe", **txt)
ax.text(eb.T_S1 - 19, eb.p_S1 + 2, "S1 Netzübergabe", **txt)
ax.text(2, M["p_kopf"] + 3, f"Zieldruck S2 im Betrieb {kb.de(M['p_kopf'])} bar", **txt)
ax.axhline(M["p_kopf"], color=TUERKIS, lw=0.8, ls=":", zorder=2)
bereich = dict(fontsize=11, weight="bold", color="#9A9A9A", ha="center", zorder=2)
ax.text(-5, 120, "flüssig / dicht", **bereich)
ax.text(80, 20, "gasförmig", **bereich)
ax.text(80, 120, "überkritisch", **bereich)
ax.set(xlim=(-20, 110), ylim=(0, 140), xlabel="Temperatur [°C]", ylabel="Druck [bar]",
       title="Einspeicherpfade S1 und S2 im p-T-Diagramm des Worst-Case-Gemischs")
ax.grid(alpha=0.3, zorder=1)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(ABB / "abb_einspeicherpfad_gemisch.png", dpi=170)
print("\ngespeichert: abb_einspeicherpfad_gemisch.png")

# ---- Diagramm 2: spezifische Arbeit rein vs. Gemisch ----------------------------------------
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
ax2.set_xlabel("spezifische Arbeit bis Bohrlochkopf (Zieldruck im Betrieb) [kJ/kg]")
ax2.set_title("Spezifische Arbeit: reines CO₂ vs. Worst-Case-Gemisch (gleiche Kette)", fontsize=11)
ax2.grid(axis="x", alpha=0.3)
ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=8, frameon=False)
fig2.tight_layout()
fig2.savefig(ABB / "abb_arbeit_rein_vs_gemisch.png", dpi=170)
print("gespeichert: abb_arbeit_rein_vs_gemisch.png")

with open(ABB / "s2_ergebnisse.json", "w", encoding="utf-8") as f:
    json.dump(kb._rein_json(erg), f, ensure_ascii=False, indent=1)
print("gespeichert: s2_ergebnisse.json")
