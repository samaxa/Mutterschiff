# -*- coding: utf-8 -*-
"""
G06 - Gewicht der Säule im Förderstrang: CO2 im Vergleich zu Erdgas und Wasserstoff
============================================================================
Frage: Warum braucht ein CO2-Speicher am Bohrlochkopf so viel weniger Druck
als ein Erdgas- oder Wasserstoffspeicher, obwohl die Kaverne denselben Druck
hat?

Idee: Im Förderstrang steht eine Säule des gespeicherten Mediums. Je dichter
sie ist, desto mehr Druck liefert sie selbst, und desto weniger muss die
Anlage am Kopf aufbringen. CO2 ist unter Kavernenbedingungen dicht
(800 bis 930 kg/m³), Erdgas und Wasserstoff bleiben Gase.

Rechnung (dieselbe wie in der Kavernenrechnung, Fall Stillstand):
  dp/dz = ρ(p, T(z)) · g, von der LCCS nach oben, 600 Schritte
  T(z) = 10 °C + 0,03 K/m · z (Q-028)
  Stoffwerte CoolProp: CO2 Span & Wagner, Methan als Erdgas-Ersatz,
  Normal-Wasserstoff (siehe gasgrundlagen_bausteine.py).
  Gassäule, Gebirgstemperatur und Referenzkaverne kommen unverändert aus
  Kaverne/Grundlagen/kaverne_bausteine.py (gassaeule, T_gebirge, TIEF).

Annahmen
  p an der LCCS 210 bar (voll) und 70 bar (leer) wie Referenzkaverne.
  Teufenreihe 600 bis 1600 m: der Druck an der LCCS bleibt bewusst in jeder
  Teufe bei 210 bar, damit nur der Einfluss der Säule sichtbar wird. Real
  steigt der zulässige Höchstdruck mit der Teufe (Gebirgsdruck).
  Ruhende Säule, ohne Reibung. Beim Strömen kommt die Reibung hinzu
  (Kaverne/Reines_CO2/01).

Gleiche Werte wie Blatt „Medienvergleich“ in
Einspeicherung/Clean_CO2/CO2_Einspeicherpfad_Rechenuebersicht.xlsx.

Abbildung: Abbildungen/abb_G06_gassaeule_medienvergleich.png
  links  Druck über der Teufe in der Referenzkaverne (210 bar an der LCCS)
  rechts Kopfdruck über der Teufe der LCCS (210 bar an der LCCS)
Ergebnisse: Abbildungen/G06_gassaeule_medienvergleich.json

Braucht Kaverne/Grundlagen/kaverne_bausteine.py (Ordner Kaverne/ neben
Gasgrundlagen/, wie Einspeicherung/ für 02).
"""
import json
import sys
from dataclasses import replace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import gasgrundlagen_bausteine as gb

sys.path.insert(0, str(gb.ORDNER.parent / "Kaverne" / "Grundlagen"))
import kaverne_bausteine as kb  # noqa: E402

P_VOLL, P_LEER = kb.TIEF.p_max, kb.TIEF.p_min      # 210 / 70 bar an der LCCS
TEUFEN = np.arange(600.0, 1601.0, 50.0)            # m, LCCS-Teufe
TEUFEN_TAB = (600.0, 800.0, 1000.0, 1200.0, 1400.0, 1600.0)


class Gas:
    """Erdgas (Methan) und Wasserstoff mit derselben Schnittstelle wie kb.Medium."""

    def __init__(self, kurz):
        self.cp_name, self.name, self.farbe = gb.STOFFE[kurz]

    def rho(self, p, T):
        return PropsSI("D", "P", p * 1e5, "T", T + 273.15, self.cp_name)


MEDIEN = {"CO2": kb.REIN, "CH4": Gas("CH4"), "H2": Gas("H2")}
NAMEN = {k: gb.STOFFE[k][1] for k in MEDIEN}
FARBEN = {k: gb.STOFFE[k][2] for k in MEDIEN}


def de(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


# ---- 1) Referenzkaverne: Profile voll und leer ------------------------------------
ergebnis = {"annahmen": {
    "p_LCCS_voll_bar": P_VOLL, "p_LCCS_leer_bar": P_LEER, "z_LCCS_m": kb.TIEF.z_lccs,
    "Gebirge": "10 °C + 0,03 K/m (Q-028)", "Schritte": 600,
    "Teufenreihe": "p an der LCCS in jeder Teufe 210 bar"}}
profile = {}
print(f"Referenzkaverne, LCCS {kb.TIEF.z_lccs:.0f} m, ruhende Säule")
print(f"{'':18s} {'Kopf voll':>10s} {'Gewinn':>8s} {'ρ Kopf':>8s} {'ρ LCCS':>8s} {'Kopf leer':>10s}")
for k, med in MEDIEN.items():
    p_kopf, prof = kb.gassaeule(med, kb.TIEF, P_VOLL)
    p_kopf_leer, _ = kb.gassaeule(med, kb.TIEF, P_LEER)
    profile[k] = prof
    r = {"p_Kopf_voll_bar": p_kopf, "Saeulengewinn_voll_bar": P_VOLL - p_kopf,
         "rho_Kopf_kg_m3": prof[0, 3], "rho_LCCS_kg_m3": prof[-1, 3],
         "p_Kopf_leer_bar": p_kopf_leer, "Saeulengewinn_leer_bar": P_LEER - p_kopf_leer}
    ergebnis[k] = r
    print(f"{NAMEN[k]:18s} {p_kopf:10.1f} {P_VOLL - p_kopf:8.1f} {prof[0, 3]:8.1f} "
          f"{prof[-1, 3]:8.1f} {p_kopf_leer:10.1f}")

# ---- 2) Kopfdruck über der Teufe der LCCS ------------------------------------------
kopf_teufe = {k: [] for k in MEDIEN}
for z in TEUFEN:
    kav = replace(kb.TIEF, z_lccs=z, z_mitte=z + kb.DZ_BEZUG)
    for k, med in MEDIEN.items():
        kopf_teufe[k].append(kb.gassaeule(med, kav, P_VOLL)[0])
kopf_teufe = {k: np.array(v) for k, v in kopf_teufe.items()}

print("\nKopfdruck über der LCCS-Teufe (210 bar an der LCCS)")
print(f"{'Teufe':>6s}" + "".join(f"{NAMEN[k]:>20s}" for k in MEDIEN))
tabelle = []
for z in TEUFEN_TAB:
    i = int(np.argmin(abs(TEUFEN - z)))
    tabelle.append({"z_LCCS_m": z, **{k: float(kopf_teufe[k][i]) for k in MEDIEN}})
    print(f"{z:6.0f}" + "".join(f"{kopf_teufe[k][i]:20.1f}" for k in MEDIEN))
d_co2 = kopf_teufe["CO2"][0] - kopf_teufe["CO2"][-1]
print(f"CO2 zwischen 600 und 1600 m: {d_co2:.1f} bar weniger Kopfdruck, "
      f"CH4 {kopf_teufe['CH4'][0] - kopf_teufe['CH4'][-1]:.1f} bar, "
      f"H2 {kopf_teufe['H2'][0] - kopf_teufe['H2'][-1]:.1f} bar")
ergebnis["kopfdruck_ueber_teufe"] = tabelle
ergebnis["CO2_Abnahme_600_1600_bar"] = float(d_co2)

# ---- 3) Abbildung ----------------------------------------------------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 4.4))

for k in MEDIEN:
    prof = profile[k]
    a1.plot(prof[:, 1], prof[:, 0], color=FARBEN[k], lw=2.0, label=NAMEN[k])
    p_k = ergebnis[k]["p_Kopf_voll_bar"]
    a1.plot(p_k, 0, "o", color=FARBEN[k], ms=5, zorder=5, clip_on=False)
a1.plot(P_VOLL, kb.TIEF.z_lccs, "ko", ms=5, zorder=6)
a1.annotate(f"{de(P_VOLL, 0)} bar an der LCCS", (P_VOLL, kb.TIEF.z_lccs),
            xytext=(-8, 0), textcoords="offset points", ha="right", va="center", fontsize=8.5)
for k, (dx, dy) in {"CO2": (-6, -5), "CH4": (-6, -5), "H2": (6, -5)}.items():
    p_k = ergebnis[k]["p_Kopf_voll_bar"]
    a1.annotate(f"{de(p_k)} bar", (p_k, 0), xytext=(dx, dy), textcoords="offset points",
                ha="left" if dx > 0 else "right", va="top", fontsize=8.5, color=FARBEN[k])
a1.set_xlim(0, 250)
a1.set_ylim(kb.TIEF.z_lccs + 20, 0)
a1.set_xlabel("Druck in bar")
a1.set_ylabel("Teufe in m")
a1.set_title("Druck im Förderstrang,\nReferenzkaverne (LCCS 1200 m)", fontsize=10)
a1.grid(alpha=0.3)
a1.legend(loc="center left", fontsize=8.5, framealpha=0.95)

for k in MEDIEN:
    a2.plot(TEUFEN, kopf_teufe[k], color=FARBEN[k], lw=2.0, label=NAMEN[k])
    sel = np.isin(TEUFEN, TEUFEN_TAB)
    a2.plot(TEUFEN[sel], kopf_teufe[k][sel], "o", color=FARBEN[k], ms=4)
a2.axhline(P_VOLL, color="0.35", ls="--", lw=1.0)
a2.text(1590, P_VOLL + 3, f"{de(P_VOLL, 0)} bar an der LCCS", ha="right", va="bottom",
        fontsize=8.5, color="0.25")
a2.axvline(kb.TIEF.z_lccs, color="0.35", ls=":", lw=1.0)
a2.text(kb.TIEF.z_lccs + 15, 20, "Referenz-\nkaverne", fontsize=8.5, color="0.25", va="bottom")
a2.set_xlim(600, 1600)
a2.set_ylim(0, 250)
a2.set_xlabel("Teufe der LCCS in m")
a2.set_ylabel("Kopfdruck in bar")
a2.set_title("Kopfdruck über der Teufe\nder LCCS (ruhende Säule)", fontsize=10)
a2.grid(alpha=0.3)

fig.tight_layout()
fig.savefig(gb.ABB / "abb_G06_gassaeule_medienvergleich.png", dpi=175)
print("\nAbbildung gespeichert:", gb.ABB / "abb_G06_gassaeule_medienvergleich.png")

json.dump(ergebnis, open(gb.ABB / "G06_gassaeule_medienvergleich.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=float)
