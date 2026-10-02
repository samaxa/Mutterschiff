# -*- coding: utf-8 -*-
"""
Schritt 3 S1 (Gemisch) - Gassäule und dichte Anlieferung: Pumpe
============================================================================
Dieselbe Rechnung wie die Excel-Mappe "CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx"
(Blätter Kaverne & Gassäule, Einspeicherung S1). Alle Annahmen und Bausteine stehen
in Grundlagen/einspeicherung_bausteine.py.

  1) Gassäule Kaverne V1 -> Zieldruck am Bohrlochkopf (voll 210 bar, leer 70 bar unten)
  2) S1 dicht:  Pumpe 91 bar / 15 °C -> Bohrlochkopf
Bei 91 bar liegt das Gemisch 8,8 bar über der Cricondenbar (82,2 bar): die Pumpe
saugt einphasig dichtes CO₂ an.

Die gasförmige Anlieferung S2 rechnet 03_S2_verdichtung_kuehlung_pumpe_gemisch.py.
Dieselbe Rechnung wird zum Vergleich auch für reines CO₂ gemacht. Zum Schluss
werden die Ergebnisse mit den Werten der Excel-Mappe verglichen.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parents[1]          # Begleitstoffe_CO2
sys.path.insert(0, str(ORDNER / "Grundlagen"))         # gemisch_worstcase, einspeicherung_bausteine
ABB = ORDNER / "Abbildungen"                           # Abbildungen und Ergebnisdateien

import einspeicherung_bausteine as eb

REIN, GEM = eb.ReinCO2(), eb.Gemisch()

# Werte der Excel-Mappe (Gemisch, Stand 01.10.2026) zur Kontrolle
EXCEL = dict(kopf=114.931, kopf_leer=50.705, S1=3.7235)


def ok(bedingung):
    return "✔" if bedingung else "✘"


# ---- 1) Rechnen: Gemisch (Excel) und reines CO2 (Vergleich) ------------------
erg = {}
for stoff in (GEM, REIN):
    p_kopf, profil = eb.gassaeule(stoff, eb.P_MAX_LCCS)
    p_kopf_leer, profil_leer = eb.gassaeule(stoff, eb.P_MIN_LCCS)
    S1 = eb.stufe(stoff, eb.p_S1, eb.T_S1, p_kopf, eb.eta_P)
    m_min, m_max = eb.massenstrom(stoff)
    erg[stoff.name] = dict(p_kopf=p_kopf, p_kopf_leer=p_kopf_leer, profil=profil, profil_leer=profil_leer,
                           S1=S1, m=(m_min, m_max))

    print(f"\n==== {stoff.name} ====")
    print(f"Gassäule: 210 bar unten -> {p_kopf:.2f} bar am Kopf (leer: 70 bar -> {p_kopf_leer:.2f} bar)")
    print(f"S1 Pumpe {eb.p_S1:.0f} -> {p_kopf:.2f} bar: {eb.T_S1:.0f} -> {S1['T2']:.2f} °C, w = {S1['w']:.2f} kJ/kg, "
          f"Leistung {m_min * S1['w']:.0f}-{m_max * S1['w']:.0f} kW")

M, R = erg[GEM.name], erg[REIN.name]

# ---- 2) Auswirkungen des Gemischs --------------------------------------------
print("\n==== Gemisch gegenüber reinem CO₂ ====")
print(f"Kopfdruck voll:  rein {R['p_kopf']:7.2f} | Gemisch {M['p_kopf']:7.2f} bar ({M['p_kopf'] - R['p_kopf']:+.2f})")
wr, wg = R["S1"]["w"], M["S1"]["w"]
print(f"S1 Pumpe   rein {wr:6.2f} | Gemisch {wg:6.2f} kJ/kg ({100 * (wg / wr - 1):+.0f} %)")

# ---- 3) Kontrolle gegen die Excel-Mappe -------------------------------------
werte = dict(kopf=M["p_kopf"], kopf_leer=M["p_kopf_leer"], S1=M["S1"]["w"])
abw = max(abs(werte[k] - EXCEL[k]) for k in EXCEL)
print(f"\nKontrolle gegen die Excel-Mappe: größte Abweichung {abw:.3f} {ok(abw < 0.01)}  "
      + ", ".join(f"{k} {werte[k]:.3f}" for k in EXCEL))

# ---- 4) Diagramm: Gassäule rein vs. Gemisch (voll und leer) -----------------
ROT = "#CA220E"
fig3, (b1, b2) = plt.subplots(1, 2, figsize=(10, 5.5), sharey=True)
for e, farbe, name in ((R, "#00304F", "reines CO₂"), (M, ROT, "Gemisch")):
    for prof, ls, fall, kopf in ((e["profil"], "-", "voll", e["p_kopf"]),
                                 (e["profil_leer"], "--", "leer", e["p_kopf_leer"])):
        z, p, T, rho = prof.T
        b1.plot(rho, z, color=farbe, lw=2, ls=ls, label=f"{name} {fall}")
        b2.plot(p, z, color=farbe, lw=2, ls=ls, label=f"{name} {fall}: Kopf {kopf:.1f} bar".replace(".", ","))
b1.set(xlabel="Dichte [kg/m³]", ylabel="Teufe [m]", title="Dichte in der Gassäule")
b2.set(xlabel="Druck [bar]", title="Druck in der Gassäule")
b1.invert_yaxis()
for b in (b1, b2):
    b.grid(alpha=0.3)
    b.legend(fontsize=8)
fig3.suptitle("Gassäule Kaverne V1 (1200 m; voll 210 bar, leer 70 bar unten): reines CO₂ vs. Gemisch",
              fontsize=11)
fig3.tight_layout()
fig3.savefig(ABB / "abb_gassaeule_rein_vs_gemisch.png", dpi=170)
print("\ngespeichert: abb_gassaeule_rein_vs_gemisch.png")
