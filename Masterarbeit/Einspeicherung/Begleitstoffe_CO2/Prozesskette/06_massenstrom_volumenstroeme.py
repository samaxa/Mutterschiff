# -*- coding: utf-8 -*-
"""
Schritt 6 (rein und Gemisch) - ein Massenstrom, viele Volumenströme
============================================================================
Besprechung K. Vosbeck 15.10.2026, Pkt. 4: "Volumenströme der unterschiedlichen Phasen
nicht direkt gleichsetzen; stattdessen über einen konsistenten Massenstrom verknüpfen."

Der Massenstrom ist entlang der ganzen Kette gleich (keine Abzweigung, kein Speicher):
    ṁ = V_n · ρ_n / 3600            (Normvolumenstrom, 0 °C / 1,01325 bar, DIN 1343)
Der tatsächliche Volumenstrom an jedem Zustandspunkt folgt aus der Dichte dort:
    V̇ = ṁ / ρ(p, T) · 3600  [m³/h]
Ein Verdichter muss also ein Vielfaches des Volumenstroms einer Pumpe fördern - bei
gleichem ṁ. Das ist der Grund, warum Maschinenauswahl und Rohrdimensionen am Zustand
festgemacht werden, nicht am Normvolumenstrom (Grundsatz Nm³/h ≠ m³/h).

Liest: Abbildungen/s1_ergebnisse.json, s2_ergebnisse.json (03_S1, 03_S2 vorher ausführen)
Ausgabe: Konsole, Abbildungen/abb_volumenstroeme.png, Abbildungen/massenstrom_ergebnisse.json
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ORDNER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORDNER / "Grundlagen"))
sys.path.insert(0, str(ORDNER.parents[1] / "Kaverne" / "Grundlagen"))
ABB = ORDNER / "Abbildungen"

import einspeicherung_bausteine as eb   # noqa: E402
import kaverne_bausteine as kb          # noqa: E402

RATE_A = "100.000 Nm³/h"


def lade(name, von):
    f = ABB / name
    if not f.exists():
        raise FileNotFoundError(f"{name} fehlt - zuerst {von} ausführen.")
    with open(f, encoding="utf-8") as d:
        return json.load(d)


S1J, S2J = lade("s1_ergebnisse.json", "03_S1"), lade("s2_ergebnisse.json", "03_S2")

erg = {}
for med in (kb.REIN, kb.gemisch()):
    k = med.stoff.kurz
    s1, s2 = S1J[k], S2J[k]
    b1, b2 = s1["betrieb"][RATE_A], s2["betrieb"][RATE_A]
    K = s2["S2"]
    punkte = {
        "S1": [("Netzübergabe S1", eb.p_S1, eb.T_S1),
               ("Pumpe aus = Bohrlochkopf", b1["p_kopf"], b1["T_kopf"]),
               ("LCCS (Kaverne voll)", b1["p_lccs"], b1["T_lccs"])],
        "S2": [("Netzübergabe S2 = Verdichter 1 ein", eb.p_S2, eb.T_S2),
               ("Verdichter 1 aus", K["p_zw"], K["V1"]["T2"]),
               ("Zwischenkühler aus = Verdichter 2 ein", K["p_zw"], eb.T_ZK),
               ("Verdichter 2 aus", eb.P_UEK, K["V2"]["T2"]),
               ("Kühler aus = Pumpe ein", eb.P_UEK, eb.T_K),
               ("Pumpe aus = Bohrlochkopf", b2["p_kopf"], b2["T_kopf"]),
               ("LCCS (Kaverne voll)", b2["p_lccs"], b2["T_lccs"])],
    }
    rr = kb.raten(med)
    tab = {}
    for szen, pts in punkte.items():
        zeilen = []
        for name, p, T in pts:
            rho = med.rho(p, T)
            zeilen.append(dict(punkt=name, p=p, T=T, rho=rho, phase=med.phase(p, T),
                               **{f"V_{r[:3].replace('.', '')}k": m / rho * 3600 for r, m in rr.items()}))
        tab[szen] = zeilen
    erg[k] = dict(name=med.name, rho_norm=med.rho_norm(), m_dot={r: m for r, m in rr.items()}, punkte=tab)
    print(f"\n==== {med.name}: ṁ = {rr['50.000 Nm³/h']:.2f} / {rr[RATE_A]:.2f} kg/s (ρ_n = {med.rho_norm():.4f} kg/Nm³) ====")
    for szen, zeilen in tab.items():
        for z in zeilen:
            print(f"  {szen} {z['punkt']:<38} {z['p']:6.1f} bar {z['T']:5.1f} °C  ρ {z['rho']:6.1f} kg/m³  "
                  f"V̇ {z['V_50k']:7.0f} / {z['V_100k']:7.0f} m³/h")

# ---- Abbildung: tatsächlicher Volumenstrom je Zustandspunkt (100.000 Nm³/h) ----------------------
fig, ax = plt.subplots(figsize=(11, 5.6))
FARBE = {"rein": "#00304F", "gem": "#CA220E"}
namen = [f"S2: {z['punkt']}" for z in erg["rein"]["punkte"]["S2"]] + [f"S1: {z['punkt']}" for z in erg["rein"]["punkte"]["S1"]]
y = np.arange(len(namen))
for j, k in enumerate(("rein", "gem")):
    werte = [z["V_100k"] for z in erg[k]["punkte"]["S2"]] + [z["V_100k"] for z in erg[k]["punkte"]["S1"]]
    ax.barh(y + (j - 0.5) * 0.38, werte, 0.38, color=FARBE[k], label=erg[k]["name"])
    for yi, w in zip(y, werte):
        ax.text(w * 1.05, yi + (j - 0.5) * 0.38, f"{w:,.0f}".replace(",", "."), va="center", fontsize=7)
ax.set_xscale("log")
ax.set_yticks(y)
ax.set_yticklabels(namen, fontsize=8)
ax.invert_yaxis()
ax.set(xlabel="tatsächlicher Volumenstrom bei 100.000 Nm³/h [m³/h] (logarithmisch)",
       title="Gleicher Massenstrom, sehr unterschiedliche Volumenströme: Verdichter fördern ~10× mehr Volumen als die Pumpe")
ax.grid(alpha=0.3, axis="x")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(ABB / "abb_volumenstroeme.png", dpi=170)
plt.close(fig)
print("\ngespeichert: abb_volumenstroeme.png")

with open(ABB / "massenstrom_ergebnisse.json", "w", encoding="utf-8") as f:
    json.dump(kb._rein_json(erg), f, ensure_ascii=False, indent=1)
print("gespeichert: massenstrom_ergebnisse.json")
