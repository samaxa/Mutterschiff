# -*- coding: utf-8 -*-
"""
Schritt 5 (rein und Gemisch) - Begründung der Kühltemperaturen und des Zwischendrucks
============================================================================
Besprechung K. Vosbeck 15.10.2026, Pkt. 1: "Warum wird auf etwa 20 °C gekühlt und nicht
nur auf etwa 40 °C wie bei der Erdgaseinspeicherung? ... Für jede Kühlstufe festhalten:
Zieltemperatur, technischer Zweck, zugrunde liegende Annahme und Quelle."

Antwort in Zahlen - die zwei Kühler haben verschiedene Aufgaben:

  1  Kühler vor der Pumpe (91 bar): Die Pumpe braucht dichtes, einphasiges CO₂. Bei 91 bar
     liegt die pseudokritische Linie (Maximum von c_p) bei ~40 °C (rein) bzw. ~33 °C
     (Gemisch). Dort ändert sich die Dichte je Kelvin am stärksten - eine Pumpe würde
     dort instabil fördern. 26 °C (Kühlwasser 20 °C + 6 K, Q-120 Folie 24) liegt mit
     Abstand darunter. Q-120 Folie 32: "cool to 80 to 90 °F (27 to 32 °C)"; über 38 °C
     braucht die Pumpe deutlich mehr Förderhöhe. Q-121 S. 2: Mindestdichte 400-500 kg/m³.
     Außerdem: je wärmer das CO₂ in den Strang geht, desto leichter die Säule und desto
     höher der nötige Kopfdruck (Zieldruck im Betrieb) -> Sensitivität Kühlwasser.
  2  Zwischenkühler (55 bar): Zweck ist nur die Verdichterarbeit und die 95-°C-Grenze
     (Q-016 S. 4). 40 °C wie in der Erdgas-/CCS-Verdichtung (Q-017 S. 37, Q-063 Kap. 5.1).
     Kälter senkt den Realgasfaktor am Eintritt von Stufe 2 unter die Herstellergrenzen
     (Siemens Energy Z > 0,65; Q-017 S. 44: Z ≥ 0,7).
  3  Zwischendruck: höchster runder Druck mit Z ≥ 0,7 am Eintritt Stufe 2 (40 °C) für beide
     Gasqualitäten -> 55 bar; beide Stufen bleiben mit Abstand unter 95 °C.

Ausgabe: Konsole, Abbildungen/abb_kuehlung_pseudokritisch.png, abb_zwischenkuehler.png,
Abbildungen/kuehlung_ergebnisse.json (-> Excel-Blatt "Kühlung")
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
ABB.mkdir(exist_ok=True)

import einspeicherung_bausteine as eb   # noqa: E402
import kaverne_bausteine as kb          # noqa: E402

RATE_A = "100.000 Nm³/h"
T_ISOBARE = np.arange(10.0, 50.01, 1.0)
P_ZW_LISTE = (45.0, 50.0, 55.0, 60.0)
T_ZK_LISTE = (20.0, 26.0, 30.0, 35.0, 40.0, 45.0)
T_KW_LISTE = (15.0, 20.0, 25.0)            # Kühlwasser: kühler Tag / Auslegung / warmer Sommertag

erg = {}
for med in (kb.REIN, kb.gemisch()):
    stoff, k = med.stoff, med.stoff.kurz
    # 1) Isobare 91 bar: Dichte und c_p -> pseudokritische Linie
    rho, cp = [], []
    for T in T_ISOBARE:
        if med.ist_gemisch:
            AS = med._pt(eb.P_UEK, T)
            rho.append(AS.rhomass()); cp.append(AS.cpmass() / 1000)
        else:
            med._AS.update(kb.CP.PT_INPUTS, eb.P_UEK * 1e5, T + 273.15)
            rho.append(med._AS.rhomass()); cp.append(med._AS.cpmass() / 1000)
    T_fein = np.arange(25.0, 45.0, 0.1)
    cp_fein = []
    for T in T_fein:
        AS = med._pt(eb.P_UEK, T) if med.ist_gemisch else med._AS
        if not med.ist_gemisch:
            AS.update(kb.CP.PT_INPUTS, eb.P_UEK * 1e5, T + 273.15)
        cp_fein.append(AS.cpmass())
    T_pc = float(T_fein[int(np.argmax(cp_fein))])
    T_rho500 = float(np.interp(-500.0, -np.array(rho), T_ISOBARE))   # rho fällt mit T
    # 2) Zwischendruck bei 40 °C Zwischenkühlung
    pzw = []
    for p in P_ZW_LISTE:
        _, V1, ZK, V2 = eb.zweistufig(stoff, eb.P_UEK, p_zw=p, T_zk=eb.T_ZK)
        pzw.append(dict(p_zw=p, T1=V1["T2"], T2=V2["T2"], Z2=V2["Z1"], w=V1["w"] + V2["w"]))
    # 3) Zwischenkühler-Temperatur bei 55 bar
    zk = []
    for T in T_ZK_LISTE:
        _, V1, ZK, V2 = eb.zweistufig(stoff, eb.P_UEK, p_zw=eb.P_ZW, T_zk=T)
        zk.append(dict(T_ZK=T, Z2=V2["Z1"], T2=V2["T2"], w=V1["w"] + V2["w"], q_ZK=ZK["q"]))
    # 4) Kühlwasser-Sensitivität: Kühler vor der Pumpe = Kühlwasser + 6 K (Q-120 Folie 24)
    kw = []
    m = kb.raten(med)[RATE_A]
    for T_kw in T_KW_LISTE:
        T_k = T_kw + eb.DT_KUEHLER
        z = kb.zieldruck_einspeisen(med, kb.TIEF, "S2", m, T_ein=T_k)
        kw.append(dict(T_KW=T_kw, T_K=T_k, rho_pumpe=med.rho(eb.P_UEK, T_k), p_kopf=z["p_kopf"],
                       T_kopf=z["T_kopf"], w_pumpe=z["w_pumpe"]))
    erg[k] = dict(name=stoff.name, isobare=dict(T=T_ISOBARE.tolist(), rho=rho, cp=cp), T_pc_91=T_pc,
                  T_rho500_91=T_rho500, p_zw=pzw, zwischenkuehler=zk, kuehlwasser=kw)
    print(f"\n==== {stoff.name} ====")
    print(f"91 bar: pseudokritische Temperatur (c_p-Maximum) {T_pc:.1f} °C, ρ = 500 kg/m³ bei {T_rho500:.1f} °C")
    for T in (20, 26, 30, 35, 40):
        i = int(np.argmin(abs(T_ISOBARE - T)))
        print(f"   {T} °C: ρ = {rho[i]:6.1f} kg/m³, c_p = {cp[i]:5.2f} kJ/(kg K)")
    print("Zwischendruck bei Zwischenkühlung 40 °C:")
    for z in pzw:
        print(f"   {z['p_zw']:.0f} bar: Stufe 1 {z['T1']:.1f} °C, Stufe 2 {z['T2']:.1f} °C {kb.ok(z['T2'] <= eb.T_MAX_STUFE)}, "
              f"Z₂ {z['Z2']:.3f} {kb.ok(z['Z2'] >= eb.Z_Q017)}, w {z['w']:.2f} kJ/kg")
    print("Zwischenkühler-Temperatur bei 55 bar:")
    for z in zk:
        print(f"   {z['T_ZK']:.0f} °C: Z₂ {z['Z2']:.3f} (Siemens {kb.ok(z['Z2'] > eb.Z_MIN)}, Q-017 {kb.ok(z['Z2'] >= eb.Z_Q017)}), "
              f"Stufe 2 {z['T2']:.1f} °C {kb.ok(z['T2'] <= eb.T_MAX_STUFE)}, w {z['w']:.2f} kJ/kg")
    print("Kühlwasser (Kühler vor der Pumpe = KW + 6 K) -> Zieldruck S2 im Betrieb:")
    for z in kw:
        print(f"   KW {z['T_KW']:.0f} °C -> {z['T_K']:.0f} °C: ρ Pumpe {z['rho_pumpe']:.0f} kg/m³, "
              f"Kopf {z['p_kopf']:.1f} bar / {z['T_kopf']:.1f} °C, Pumpe {z['w_pumpe']:.2f} kJ/kg")

# ---- Abbildung 1: 91-bar-Isobare (pseudokritische Linie) ----------------------------------------
FARBE = {"rein": "#00304F", "gem": "#CA220E"}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.3))
for k, e in erg.items():
    a1.plot(e["isobare"]["T"], e["isobare"]["rho"], color=FARBE[k], lw=2, label=e["name"])
    a2.plot(e["isobare"]["T"], e["isobare"]["cp"], color=FARBE[k], lw=2, label=e["name"])
    for a in (a1, a2):
        a.axvline(e["T_pc_91"], color=FARBE[k], ls=":", lw=1.2)
    a2.text(e["T_pc_91"] + 0.3, 13.5 if k == "rein" else 11.5, f"pseudokritisch\n{kb.de(e['T_pc_91'])} °C",
            color=FARBE[k], fontsize=8)
for a in (a1, a2):
    a.axvline(eb.T_K, color="#007335", lw=1.5, ls="--")
    a.axvline(eb.T_ZK, color="#EE7203", lw=1.5, ls="--")
    a.grid(alpha=0.3)
a1.axhline(eb.RHO_MIN, color="#7F7F7F", lw=1, ls="--")
a1.text(11, eb.RHO_MIN + 12, "500 kg/m³: Mindestdichte Pumpe (Q-121 S. 2)", fontsize=8, color="#555")
a1.text(eb.T_K + 0.4, 250, "26 °C: Kühler vor\nder Pumpe", fontsize=8, color="#007335")
a1.text(eb.T_ZK + 0.4, 250, "40 °C: übliche\nNachkühlung Erdgas", fontsize=8, color="#EE7203")
a1.set(xlabel="Temperatur [°C]", ylabel="Dichte [kg/m³]", title="Dichte bei 91 bar (Pumpeneintritt)", ylim=(200, 950))
a2.set(xlabel="Temperatur [°C]", ylabel="c_p [kJ/(kg K)]", title="Wärmekapazität bei 91 bar", ylim=(0, 16))
a1.legend(fontsize=8)
fig.suptitle("Warum der Kühler vor der Pumpe auf 26 °C kühlt: 40 °C läge bei 91 bar an der pseudokritischen Linie",
             fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(ABB / "abb_kuehlung_pseudokritisch.png", dpi=170)
plt.close(fig)

# ---- Abbildung 2: Zwischenkühler-Temperatur -> Z und Austrittstemperatur Stufe 2 -----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
for k, e in erg.items():
    T = [z["T_ZK"] for z in e["zwischenkuehler"]]
    a1.plot(T, [z["Z2"] for z in e["zwischenkuehler"]], "-o", color=FARBE[k], label=e["name"])
    a2.plot(T, [z["T2"] for z in e["zwischenkuehler"]], "-o", color=FARBE[k], label=e["name"])
a1.axhline(eb.Z_MIN, color="#7F7F7F", ls="--", lw=1)
a1.text(20.5, eb.Z_MIN + 0.004, "Siemens Energy: Z > 0,65", fontsize=8)
a1.axhline(eb.Z_Q017, color="#7F7F7F", ls=":", lw=1)
a1.text(20.5, eb.Z_Q017 + 0.004, "Q-017 S. 44: Z ≥ 0,7", fontsize=8)
a2.axhline(eb.T_MAX_STUFE, color="#CA220E", ls="--", lw=1)
a2.text(20.5, eb.T_MAX_STUFE - 3, "Q-016 S. 4: ≤ 95 °C", fontsize=8, color="#CA220E")
for a in (a1, a2):
    a.axvline(eb.T_ZK, color="#EE7203", ls="--", lw=1.2)
    a.grid(alpha=0.3)
    a.set_xlabel("Zwischenkühler-Austritt [°C] (bei 55 bar)")
a1.set(ylabel="Realgasfaktor Z am Eintritt Stufe 2", title="Kälter kühlen senkt Z")
a2.set(ylabel="Austritt Stufe 2 [°C]", title="Wärmer kühlen hebt die Austrittstemperatur")
a1.legend(fontsize=8)
fig.suptitle("Zwischenkühler: 40 °C hält beide Grenzen ein (Z ≥ 0,7 und ≤ 95 °C)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(ABB / "abb_zwischenkuehler.png", dpi=170)
plt.close(fig)
print("\ngespeichert: abb_kuehlung_pseudokritisch.png, abb_zwischenkuehler.png")

with open(ABB / "kuehlung_ergebnisse.json", "w", encoding="utf-8") as f:
    json.dump(kb._rein_json(erg), f, ensure_ascii=False, indent=1)
print("gespeichert: kuehlung_ergebnisse.json")
