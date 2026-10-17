# -*- coding: utf-8 -*-
"""
Schritt 3 S1 (Gemisch und reines CO₂) - Zieldruck und dichte Anlieferung: Pumpe
============================================================================
Dieselbe Rechnung wie die Excel-Mappen (Blätter "Kaverne & Gassäule", "Einspeicherung S1").
Annahmen und Bausteine: Grundlagen/einspeicherung_bausteine.py; Förderstrang und Kopplung
an die Kaverne: Kaverne/Grundlagen/kaverne_bausteine.py.

  1) Zieldruck am Bohrlochkopf, zwei Betrachtungen:
     Stillstand  ruhende Säule mit Gebirgstemperatur (Q-028 Fig. 3) - wie bisher
     Betrieb     strömende Säule beim Einspeisen: Kopftemperatur = Pumpenaustritt, adiabat
                 nach unten (h + g·z = konst.), Reibung im 8 5/8"-Strang (Q-030 Kap. 1.2.1,
                 f = 0,016 nach Q-003 Kap. 6.2). Der kältere Strang ist schwerer als die
                 ruhende Säule -> S1 braucht oben etwas WENIGER als im Stillstand.
     NEU: Auslegungsdruck der Pumpe = Betrieb bei 100.000 Nm³/h (Besprechung K. Vosbeck
     15.10.2026, Pkt. 6: Regelung über den Kopfdruck, Staudruck bei hohen Raten).
  2) S1 dicht: Pumpe 91 bar / 15 °C -> Zieldruck im Betrieb
Bei 91 bar liegt das Gemisch 8,8 bar über der Cricondenbar (82,2 bar): die Pumpe
saugt einphasig dichtes CO₂ an.

Ausgabe: Konsole, Abbildungen/abb_gassaeule_rein_vs_gemisch.png,
Abbildungen/s1_ergebnisse.json (-> Excel-Mappen, Blatt "Einspeicherung S1")
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDNER = Path(__file__).resolve().parents[1]          # Begleitstoffe_CO2
sys.path.insert(0, str(ORDNER / "Grundlagen"))         # gemisch_worstcase, einspeicherung_bausteine
sys.path.insert(0, str(ORDNER.parents[1] / "Kaverne" / "Grundlagen"))   # kaverne_bausteine (Förderstrang)
ABB = ORDNER / "Abbildungen"
ABB.mkdir(exist_ok=True)

import einspeicherung_bausteine as eb   # noqa: E402
import kaverne_bausteine as kb          # noqa: E402

RATE_A = "100.000 Nm³/h"                # Auslegungsrate

# Werte der Excel-Mappe Gemisch (Stand 15.10.2026) zur Kontrolle
EXCEL = dict(kopf=114.931, kopf_leer=50.705, kopf_betrieb=114.274, S1=3.6220)


def ok(bedingung):
    return "✔" if bedingung else "✘"


def kurz(z):
    return {k: v for k, v in z.items() if k not in ("profil", "pumpe")}


erg = {}
for med in (kb.gemisch(), kb.REIN):
    stoff = med.stoff
    p_kopf, profil = eb.gassaeule(stoff, eb.P_MAX_LCCS)
    p_kopf_leer, profil_leer = eb.gassaeule(stoff, eb.P_MIN_LCCS)
    betrieb = {rate: kb.zieldruck_einspeisen(med, kb.TIEF, "S1", m) for rate, m in kb.raten(med).items()}
    z = betrieb[RATE_A]
    S1 = eb.stufe(stoff, eb.p_S1, eb.T_S1, z["p_kopf"], eb.eta_P)
    m_min, m_max = eb.massenstrom(stoff)
    erg[stoff.kurz] = dict(name=stoff.name, p_kopf_still=p_kopf, p_kopf_leer=p_kopf_leer,
                           betrieb={r: kurz(b) for r, b in betrieb.items()},
                           S1=dict(S1, s1=stoff.s(eb.p_S1, eb.T_S1)), m=(m_min, m_max),
                           profil_still=profil.tolist(), profil_leer=profil_leer.tolist(),
                           profil_betrieb=[[float(r[0]), float(r[1]), float(r[2]), float(r[3])] for r in z["profil"]])
    print(f"\n==== {stoff.name} ====")
    print(f"Stillstand: 210 bar unten -> {p_kopf:.2f} bar am Kopf (leer: 70 bar -> {p_kopf_leer:.2f} bar)")
    for rate, b in betrieb.items():
        print(f"Betrieb S1 {rate:<14}: Kopf {b['p_kopf']:.2f} bar / {b['T_kopf']:.2f} °C, an der LCCS {b['T_lccs']:.1f} °C, "
              f"v {b['v_kopf']:.2f} m/s")
    print(f"S1 Pumpe {eb.p_S1:.0f} -> {z['p_kopf']:.2f} bar (Auslegung {RATE_A}): {eb.T_S1:.0f} -> {S1['T2']:.2f} °C, "
          f"w = {S1['w']:.3f} kJ/kg, Leistung {m_min * S1['w']:.0f}-{m_max * S1['w']:.0f} kW")

M, R = erg["gem"], erg["rein"]
print("\n==== Gemisch gegenüber reinem CO₂ ====")
print(f"Zieldruck Betrieb S1: rein {R['betrieb'][RATE_A]['p_kopf']:.2f} | Gemisch {M['betrieb'][RATE_A]['p_kopf']:.2f} bar")
print(f"S1 Pumpe: rein {R['S1']['w']:.3f} | Gemisch {M['S1']['w']:.3f} kJ/kg")

werte = dict(kopf=M["p_kopf_still"], kopf_leer=M["p_kopf_leer"], kopf_betrieb=M["betrieb"][RATE_A]["p_kopf"],
             S1=M["S1"]["w"])
abw = max(abs(werte[k] - EXCEL[k]) for k in EXCEL)
print(f"\nKontrolle gegen die Excel-Mappe: größte Abweichung {abw:.3f} {ok(abw < 0.01)}  "
      + ", ".join(f"{k} {werte[k]:.3f}" for k in EXCEL))

# ---- Abbildung: Säule rein vs. Gemisch, Stillstand und Betrieb ------------------------------
ROT = "#CA220E"
fig, (b1, b2) = plt.subplots(1, 2, figsize=(10.5, 5.8), sharey=True)
for e, farbe, name in ((R, "#00304F", "reines CO₂"), (M, ROT, "Gemisch")):
    for prof, ls, fall in ((e["profil_still"], "-", "Stillstand voll"), (e["profil_leer"], ":", "Stillstand leer"),
                           (e["profil_betrieb"], "--", f"Einspeisen S1 ({RATE_A})")):
        z_, p_, T_, rho_ = zip(*prof)
        kopf = p_[z_.index(min(z_))]
        b1.plot(rho_, z_, color=farbe, lw=2, ls=ls, label=f"{name}, {fall}")
        b2.plot(p_, z_, color=farbe, lw=2, ls=ls, label=f"{name}, {fall}: Kopf {kb.de(kopf)} bar")
b1.set(xlabel="Dichte [kg/m³]", ylabel="Teufe [m]", title="Dichte im Bohrloch")
b2.set(xlabel="Druck [bar]", title="Druck im Bohrloch")
b1.invert_yaxis()
for b in (b1, b2):
    b.grid(alpha=0.3)
    b.legend(fontsize=7)
fig.suptitle("Bohrloch Referenzkaverne (1200 m, 210 bar unten): Stillstand und Einspeisen S1, rein vs. Gemisch",
             fontsize=11)
fig.tight_layout()
fig.savefig(ABB / "abb_gassaeule_rein_vs_gemisch.png", dpi=170)
print("\ngespeichert: abb_gassaeule_rein_vs_gemisch.png")

with open(ABB / "s1_ergebnisse.json", "w", encoding="utf-8") as f:
    json.dump(kb._rein_json(erg), f, ensure_ascii=False, indent=1)
print("gespeichert: s1_ergebnisse.json")
