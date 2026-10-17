# -*- coding: utf-8 -*-
"""
Kaverne Schritt 05 - Worst-Case-Gemisch gegenüber reinem CO₂: welcher Fall ist ungünstiger?
============================================================================
Besprechung K. Vosbeck 15.10.2026, Pkt. 7: "Prüfen, ob die Kavernenrechnung konservativ
mit reinem CO₂ durchgeführt werden sollte ... alternativ eine Vergleichsrechnung."

Antwort: Es gibt keinen pauschal konservativen Stoff - welcher Fall ungünstiger ist, hängt
an der Auslegungsgröße. Deshalb werden beide gerechnet (Schritte 01-04 in Reines_CO2/ und
Begleitstoffe_CO2/), und je Auslegungsgröße wird der ungünstigere Wert für die Auslegung
der Obertageanlage genommen.

Liest: ../Reines_CO2/*.json und ./*.json (Schritte 01-04 müssen in beiden Ordnern gelaufen sein)
Ausgabe: Konsole, abb_K05_rein_vs_gemisch.png, vergleich_rein_gemisch.json (-> Excel)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402

R, S = "100.000 Nm³/h", "Stillstand 21,67 d (Q-028)"


def lade(ordner):
    return dict(still=kb.lade_json(ordner, "kaverne_stillstand.json", "01"),
                ag=kb.lade_json(ordner, "arbeitsgas.json", "02"),
                zyk=kb.lade_json(ordner, "kavernenzyklus.json", "03"),
                kopf=kb.lade_json(ordner, "bohrlochkopf.json", "04"))


D = {"rein": lade(kb.ORDNER_REIN), "gem": lade(kb.ORDNER_GEM)}

# (Auslegungsgröße, Einheit, Funktion -> Wert, ungünstig wenn 'höher'/'niedriger', betrifft)
GROESSEN = [
    ("Zieldruck Pumpe S1 (Kaverne voll, strömend)", "bar", lambda d: d["still"]["betrieb"]["S1"][R]["p_kopf"],
     "höher", "Pumpe S1: Förderhöhe, Auslegungsdruck"),
    ("Zieldruck Pumpe S2 (Kaverne voll, strömend)", "bar", lambda d: d["still"]["betrieb"]["S2"][R]["p_kopf"],
     "höher", "Pumpe S2: Förderhöhe, Auslegungsdruck"),
    ("Pumpenarbeit S2", "kJ/kg", lambda d: d["still"]["betrieb"]["S2"][R]["w_pumpe"], "höher", "Antriebsleistung"),
    ("Kopfdruck Stillstand voll", "bar", lambda d: d["still"]["saeulen"]["voll"]["p_kopf"], "höher",
     "Druckstufe der Kopfarmaturen"),
    ("Kaverneninhalt voll (TGV)", "t", lambda d: d["ag"]["TGV"], "niedriger", "Speicherkapazität"),
    ("Arbeitsgas im Zyklus (S2)", "t", lambda d: d["zyk"]["zyklen"][f"S2|{R}|{S}"]["arbeitsgas_t"], "niedriger",
     "Speicherkapazität, Kavernenzahl"),
    ("Arbeitsgasanteil im Zyklus (S2)", "–", lambda d: d["zyk"]["zyklen"][f"S2|{R}|{S}"]["anteil_arbeitsgas"],
     "niedriger", "Kissengasbedarf"),
    ("Ratengrenze 10 bar/d bei voller Kaverne", "kg/s", lambda d: d["zyk"]["ratengrenze"]["isotherm_10"][-1],
     "niedriger", "Ein-/Ausspeicherrate am Anfang"),
    ("Kaverneninhalt T_min beim Ausspeichern", "°C",
     lambda d: d["zyk"]["zyklen"][f"S2|{R}|{S}"]["kennwerte"][0]["T_min"], "niedriger", "Abstand zur Phasengrenze"),
    ("Kopfdruck min beim Ausspeichern", "bar", lambda d: d["kopf"]["kopfdruckfenster"][f"ausspeisen_{R}_min"],
     "niedriger", "Rückverdichtung auf 91 bar"),
    ("Kopftemperatur min beim Ausspeichern", "°C", lambda d: d["kopf"]["kopfdruckfenster"][f"ausspeisen_{R}_T_min"],
     "niedriger", "Vorwärmung, Hydrat"),
    ("T nach Drossel auf 30 bar (min)", "°C",
     lambda d: d["kopf"]["kopfdruckfenster"][f"ausspeisen_{R}_T_drossel_min"], "niedriger", "Vorwärmung vor der Drossel"),
    ("Strang zweiphasig ab p_LCCS (Ausspeisen)", "bar",
     lambda d: (d["kopf"]["ausspeisen"][R]["strang_zweiphasig"] or {}).get("p_lccs_oben", np.nan), "höher",
     "Mindestdruck der Kaverne (vgl. Q-030: 160 bar)"),
    ("Einspeisen einphasig erst ab p_LCCS (S2)", "bar",
     lambda d: d["kopf"]["einspeisen"][f"S2|{R}"]["p_lccs_einphasig_ab"] or np.nan, "höher",
     "Drosselung am Kopf, Zweiphasenströmung im Strang"),
    ("Strömungsgeschwindigkeit max im Strang", "m/s",
     lambda d: d["kopf"]["kopfdruckfenster"][f"ausspeisen_{R}_v_max"], "höher", "Grenze 20 m/s (Q-030)"),
]

zeilen = []
print(f"{'Auslegungsgröße':<46}{'rein':>12}{'Gemisch':>12}  ungünstiger")
for name, einheit, f, schlecht, betrifft in GROESSEN:
    r, g = float(f(D["rein"])), float(f(D["gem"]))
    if np.isnan(r) or np.isnan(g):
        ung = "–"
    else:
        ung = ("Gemisch" if g > r else "rein") if schlecht == "höher" else ("Gemisch" if g < r else "rein")
        if abs(g - r) < 1e-9:
            ung = "gleich"
    zeilen.append(dict(groesse=name, einheit=einheit, rein=r, gemisch=g, ungünstig_wenn=schlecht,
                       ungünstiger_fall=ung, betrifft=betrifft))
    print(f"{name:<46}{r:12.2f}{g:12.2f}  {ung:<8} ({schlecht} = schlechter; {betrifft})")
n_gem = sum(z["ungünstiger_fall"] == "Gemisch" for z in zeilen)
print(f"\nGemisch ungünstiger in {n_gem} von {len(zeilen)} Größen, reines CO₂ in "
      f"{sum(z['ungünstiger_fall'] == 'rein' for z in zeilen)} -> beide Fälle rechnen, je Größe den ungünstigeren nehmen.")

# ---- Abbildung: relative Abweichung Gemisch gegenüber rein, eingefärbt nach ungünstigerem Fall
fig, ax = plt.subplots(figsize=(11, 6.5))
y = np.arange(len(zeilen))
rel = [100 * (z["gemisch"] / z["rein"] - 1) if z["rein"] not in (0, None) and not np.isnan(z["gemisch"]) else 0
       for z in zeilen]
farben = ["#CA220E" if z["ungünstiger_fall"] == "Gemisch" else "#00304F" if z["ungünstiger_fall"] == "rein" else "#999"
          for z in zeilen]
ax.barh(y, rel, color=farben)
for yi, z, r in zip(y, zeilen, rel):
    ax.text(r + (0.5 if r >= 0 else -0.5), yi, f"rein {kb.de(z['rein'], 1)} | Gemisch {kb.de(z['gemisch'], 1)} {z['einheit']}",
            va="center", ha="left" if r >= 0 else "right", fontsize=7.5)
ax.set_yticks(y)
ax.set_yticklabels([z["groesse"] for z in zeilen], fontsize=8)
ax.invert_yaxis()
ax.axvline(0, color="#333", lw=0.8)
ax.set(xlabel="Gemisch gegenüber reinem CO₂ [%]",
       title="Welcher Fall ist ungünstiger? rot = Gemisch, blau = reines CO₂ (Auslegungsrate 100.000 Nm³/h)")
ax.set_xlim(min(rel) - 35, max(rel) + 45)
ax.grid(alpha=0.3, axis="x")
fig.tight_layout()
fig.savefig(ORDNER / "abb_K05_rein_vs_gemisch.png", dpi=160)
plt.close(fig)

kb.speichere_json(ORDNER, "vergleich_rein_gemisch.json", dict(rate=R, betriebsweise=S, groessen=zeilen))
