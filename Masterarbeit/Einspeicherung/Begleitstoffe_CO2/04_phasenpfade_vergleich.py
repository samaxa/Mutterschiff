# -*- coding: utf-8 -*-
"""
Schritt 4 (Gemisch) - Phasenpfade der gasförmigen Anlieferung S2 im Vergleich
============================================================================
Frage: Auf welchem Weg durch das Phasendiagramm bringt man das CO₂ von der
gasförmigen Übergabe (30 bar / 15 °C) auf den Kopfdruck der Kaverne - und
welcher Weg funktioniert auch mit dem Worst-Case-Gemisch noch sicher?

Annahmen und Rechenbausteine kommen aus einspeicherung_bausteine.py - dieselben
wie in 03_einspeicherpfad_gemisch.py und in der Excel-Mappe
"CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx":
  Übergabe S2        30 bar / 15 °C
  Kühlung            Kühlwasser 20 °C -> CO₂ auf 26 °C (Kühlmittel + 6 K, Q-120 Folie 24)
  Grenzen            höchstens 95 °C je Stufe (Q-016), Z > 0,65 (Siemens Energy,
                     E-Mail-Auskunft 08/2026; Q-017 S. 43: Z ≥ 0,7)
  Wirkungsgrade      Verdichter 0,84 / 0,82 (Q-016), Pumpe 0,80 (eigene Annahme)
  Unsicherheit       Phasengrenze ±3 bar (Dokumentation Stoffmodelle, Kap. 9)

Die fünf Pfade
  A  unterkritisch verflüssigen   2 Stufen bis p_V (rein 60, Gemisch 80 bar), im
                                  Verflüssiger kühlen -> flüssig -> Pumpe. Geht nur bis
                                  20,4 °C (Gemisch) - deshalb mit 20 °C gerechnet
                                  (Kühlwasser 14 °C bzw. Kältemaschine)
  B  überkritisch kühlen          2 Stufen 30 -> 50 -> 91 bar (über der Cricondenbar),
                                  auf 26 °C kühlen -> dicht -> Pumpe. Kreuzt keine
                                  Phasengrenze. = gewählter S2-Pfad der Excel-Mappe
  C  durchverdichten              2 Stufen 30 -> 52 bar -> Kopfdruck, keine Pumpe
  D  tiefkalt verflüssigen        bei 30 bar mit Kältemaschine abkühlen, dann pumpen
                                  (Weg wie beim Schiffs-/Tankwagentransport)
  E  aus dem Zweiphasengebiet     Pumpe saugt ein Gas-Flüssig-Gemisch an
     pumpen                       (80 bar / 25 °C, frühere Variante der Vorarbeit)

Bewertet wird, was die Maschinen brauchen (Q-Kürzel = Quellen- und Wissensmatrix):
  Pumpe      einphasig und dicht am Eintritt: ρ ≥ 500 kg/m³ (Q-001 Kap. 5.2,
             Q-121 S. 2: 400-500 kg/m³), freies Gas höchstens ~2 Vol-%
             (Q-082 Abschn. 6.4.2), Abstand zur Blasenlinie (Q-121 S. 2, Q-040 C.5)
  Verdichter Eintritt gasförmig, kein Tropfen (Q-017 S. 44), Z > 0,65 (Siemens
             Energy, E-Mail-Auskunft 08/2026; Q-017 S. 43 nennt 0,7 als Richtwert),
             höchstens 95 °C je Stufe (Q-016)
  Kühlung    CO₂ wird selten kälter als Kühlmittel + 6 K (Q-120, Folie 24)

Ausgabe: Konsole, zwei Abbildungen und phasenpfade_ergebnisse.json
(Grundlage für Dokumentation_S2_Gemisch.docx und die Vergleichstabelle auf dem
Excel-Blatt "Einspeicherung S2").
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq

from einspeicherung_bausteine import (ReinCO2, Gemisch, kopfdruck, stufe, kuehler, pumpeneintritt,
                                      zweistufig, p_S1, T_S1, p_S2, T_S2, T_K, T_KW, DT_KUEHLER,
                                      P_ZW, P_UEK as p_UEK, P_ZW_DV as p_ZW_DV, RHO_MIN, Z_MIN,
                                      eta_V1, eta_V2, eta_P, V_NORM_MAX, U_PG)

# ---- 0) Stoffe und Annahmen: aus einspeicherung_bausteine.py (= Excel, Blatt Übersicht)
REIN, GEM = ReinCO2(), Gemisch()
p_V = {REIN.name: REIN.p_V, GEM.name: GEM.p_V}   # Verflüssigungsdruck Pfad A: 60 / 80 bar
T_A = 20.0              # °C, Kühlung Pfad A: höher geht beim Gemisch nicht (Blasenlinie + 3 bar)

# ---- 1) Zusätzliche Grenzwerte für den Pfadvergleich
RHO_WLOKA = 650.0       # kg/m3, "ab ca. 650 kg/m3 pumpbar" (Q-017 S. 30) - vorsichtig
GAS_MAX = 0.02          # 2 Vol-% freies Gas verträgt eine normale Kreiselpumpe (Q-082)


# ---- 2) Pfade ---------------------------------------------------------------
def T_bei_rho(p, rho_ziel, T_lo=0.0, T_hi=60.0):
    """Temperatur, bei der das Gemisch bei p die Dichte rho_ziel erreicht (überkritisch)."""
    return brentq(lambda T: GEM.rho(p, T) - rho_ziel, T_lo, T_hi, xtol=0.01)


def pfad_A(stoff, p_kopf):
    pV = p_V[stoff.name]
    p_zw, V1, ZK, V2 = zweistufig(stoff, pV, T_zk=T_A)
    VF = kuehler(stoff, pV, V2["h2"], T_A)
    P = stufe(stoff, pV, T_A, p_kopf, eta_P)
    return dict(p_zw=p_zw, V=[V1, V2], ZK=ZK, K=VF, P=P, ein=pumpeneintritt(stoff, pV, T_A),
                ein_26=pumpeneintritt(stoff, pV, T_K),
                phasenwechsel=dict(T_tau=stoff.tautemperatur(pV), T_blase=stoff.blasentemperatur(pV)),
                w=V1["w"] + V2["w"] + P["w"], q=ZK["q"] + VF["q"])


def pfad_B(stoff, p_kopf):
    p_zw, V1, ZK, V2 = zweistufig(stoff, p_UEK, p_zw=P_ZW)
    K = kuehler(stoff, p_UEK, V2["h2"], T_K)
    P = stufe(stoff, p_UEK, T_K, p_kopf, eta_P)
    return dict(p_zw=p_zw, V=[V1, V2], ZK=ZK, K=K, P=P, ein=pumpeneintritt(stoff, p_UEK, T_K),
                w=V1["w"] + V2["w"] + P["w"], q=ZK["q"] + K["q"])


def pfad_C(stoff, p_kopf, T_end):
    V1 = stufe(stoff, p_S2, T_S2, p_ZW_DV, eta_V1)
    ZK = kuehler(stoff, p_ZW_DV, V1["h2"], T_K)
    V2 = stufe(stoff, p_ZW_DV, T_K, p_kopf, eta_V2)
    NK = kuehler(stoff, p_kopf, V2["h2"], T_end)       # gleicher Endzustand wie Pfad B
    return dict(p_zw=p_ZW_DV, V=[V1, V2], ZK=ZK, K=NK, w=V1["w"] + V2["w"], q=ZK["q"] + NK["q"])


# ---- 3) Rechnen -------------------------------------------------------------
erg = {}
for stoff in (REIN, GEM):
    p_kopf = kopfdruck(stoff)
    A = pfad_A(stoff, p_kopf)
    B = pfad_B(stoff, p_kopf)
    C = pfad_C(stoff, p_kopf, B["P"]["T2"])
    rn = stoff.rho_norm()
    m_max = V_NORM_MAX * rn / 3600.0
    S1 = pumpeneintritt(stoff, p_S1, T_S1)
    erg[stoff.name] = dict(p_kopf=p_kopf, A=A, B=B, C=C, m_max=m_max, S1=S1)

    print(f"\n==== {stoff.name}: Kopfdruck {p_kopf:.2f} bar, ṁ_max {m_max:.1f} kg/s ====")
    for key, pf in (("A", A), ("B", B), ("C", C)):
        V1, V2 = pf["V"]
        print(f"Pfad {key}: V1 {V1['p1']:.0f}->{V1['p2']:.1f} bar {V1['T2']:.1f} °C (Z_ein {V1['Z1']:.3f}) | "
              f"V2 {V2['p1']:.1f}->{V2['p2']:.1f} bar {V2['T2']:.1f} °C (Z_ein {V2['Z1']:.3f}) | "
              f"w = {pf['w']:.2f} kJ/kg, q = {pf['q']:.1f} kJ/kg, P_max = {m_max * pf['w']:.0f} kW")
        if "ein" in pf:
            e = pf["ein"]
            print(f"        Pumpe ein {e['p']:.0f} bar / {e['T']:.0f} °C: ρ = {e['rho']:.0f} kg/m³, "
                  f"Abstand Phasengrenze {e['abstand_bar']:+.1f} bar, T-Reserve {e['T_reserve']:.1f} K, "
                  f"Pumpe w = {pf['P']['w']:.2f} kJ/kg -> {pf['P']['T2']:.1f} °C")
    print(f"        Pfad A mit Kühlwasser 20 °C (CO₂ {T_K:.0f} °C): {A['ein_26']['phase']}, "
          f"Gas {100 * A['ein_26']['gas']:.0f} Vol-% am Pumpeneintritt")

# ---- 4) Pfad D: tiefkalt verflüssigen bei 30 bar ----------------------------
# Reines CO2 siedet bei 30 bar bei -5,6 °C: Unterkühlen auf -10 °C reicht.
# Das Gemisch hat bei 30 bar KEINE Blasenlinie: der kleinste Blasendruck
# liegt oberhalb von 30 bar - es bleibt immer eine Gasphase übrig.
i_min = int(np.argmin(GEM.pg["p_blase"]))
p_blase_min = (GEM.pg["T_blase"][i_min], GEM.pg["p_blase"][i_min])
D_rein = dict(T_sat=REIN.blasentemperatur(p_S2), ein=pumpeneintritt(REIN, p_S2, -10.0))
D_gem = []
for T in (0.0, -10.0, -20.0, -30.0, -40.0, -50.0):
    y = GEM.dampfzusammensetzung(p_S2, T)
    D_gem.append(dict(T=T, gas=GEM.gasanteil(p_S2, T), phase=GEM.phase(p_S2, T),
                      y_CO2=y[0] if y else None, y_N2=y[1] if y else None, y_H2=y[4] if y else None))
print(f"\nPfad D: reines CO₂ siedet bei 30 bar bei {D_rein['T_sat']:.1f} °C "
      f"(-10 °C: {D_rein['ein']['abstand_bar']:.1f} bar über der Siedelinie)")
print(f"Pfad D: kleinster Blasendruck des Gemischs {p_blase_min[1]:.1f} bar bei {p_blase_min[0]:.1f} °C "
      f"-> bei 30 bar nie ganz flüssig")
for d in D_gem:
    zus = f", Gasphase {100*d['y_CO2']:.0f} % CO₂ / {100*d['y_N2']:.0f} % N₂ / {100*d['y_H2']:.0f} % H₂" if d["y_CO2"] else ""
    print(f"   30 bar / {d['T']:5.0f} °C: {d['phase']}, Gas {100*d['gas']:.1f} Vol-%{zus}")

# ---- 5) Pfad E: Pumpe saugt aus dem Zweiphasengebiet an ---------------------
E = pumpeneintritt(GEM, 80.0, 25.0)
print(f"\nPfad E: 80 bar / 25 °C: {E['phase']}, Gas {100*E['gas']:.1f} Vol-% (Grenze ~{100*GAS_MAX:.0f} Vol-%)")

# ---- 6) Wie warm darf gekühlt werden? (Kühlmittel + 6 K) ---------------------
T_K_liste = np.arange(14.0, 36.0, 2.0)
sens = []
for Tk in T_K_liste:
    zeile = dict(T_K=float(Tk), T_KW=float(Tk - DT_KUEHLER))
    for stoff in (REIN, GEM):
        pV = p_V[stoff.name]
        eA = pumpeneintritt(stoff, pV, Tk)
        eB = pumpeneintritt(stoff, p_UEK, Tk)
        wB = stufe(stoff, p_UEK, Tk, erg[stoff.name]["p_kopf"], eta_P)["w"]
        kurz = "rein" if stoff is REIN else "gem"
        zeile[f"A_{kurz}_abstand"] = eA["abstand_bar"]
        zeile[f"A_{kurz}_gas"] = eA["gas"]
        zeile[f"A_{kurz}_phase"] = eA["phase"]
        zeile[f"A_{kurz}_rho"] = eA["rho"]
        zeile[f"B_{kurz}_rho"] = eB["rho"]
        zeile[f"B_{kurz}_wP"] = wB
    sens.append(zeile)

# Grenztemperaturen
T_K_max_A = {  # Blasenlinie + 3 bar = p_V
    REIN.name: brentq(lambda T: REIN.blasendruck(T) + U_PG - p_V[REIN.name], 0, 30),
    GEM.name: brentq(lambda T: GEM.blasendruck(T) + U_PG - p_V[GEM.name], 0, 27),
}
T_K_max_B = {"500": T_bei_rho(p_UEK, RHO_MIN), "650": T_bei_rho(p_UEK, RHO_WLOKA)}
T_K_max_B_rein = {
    "500": brentq(lambda T: REIN.rho(p_UEK, T) - RHO_MIN, 0, 60),
    "650": brentq(lambda T: REIN.rho(p_UEK, T) - RHO_WLOKA, 0, 60),
}
print("\nKühltemperatur T_K höchstens (Kühlmittel = T_K − 6 K):")
for stoff in (REIN, GEM):
    print(f"  {stoff.name}: Pfad A {T_K_max_A[stoff.name]:.1f} °C (Kühlmittel {T_K_max_A[stoff.name]-DT_KUEHLER:.1f} °C)")
print(f"  Gemisch Pfad B (91 bar): ρ ≥ 500 bis {T_K_max_B['500']:.1f} °C, ρ ≥ 650 bis {T_K_max_B['650']:.1f} °C")
print(f"  rein    Pfad B (91 bar): ρ ≥ 500 bis {T_K_max_B_rein['500']:.1f} °C, ρ ≥ 650 bis {T_K_max_B_rein['650']:.1f} °C")
print(f"{'T_K':>5} {'KW':>5} | {'Pfad A rein (60 bar)':<24} | {'Pfad A Gemisch (80 bar)':<30} | B rein ρ | B Gem ρ  w_P")


def zustand_A(z, kurz):
    """Kurztext Pumpeneintritt Pfad A: Abstand zur Blasenlinie oder Phase."""
    if z[f"A_{kurz}_gas"] == 0.0:
        return f"flüssig, {z[f'A_{kurz}_abstand']:+.1f} bar"
    if z[f"A_{kurz}_gas"] == 1.0:
        return "gasförmig"
    return f"zweiphasig, {100 * z[f'A_{kurz}_gas']:.0f} Vol-% Gas"


for z in sens:
    print(f"{z['T_K']:5.0f} {z['T_KW']:5.0f} | {zustand_A(z, 'rein'):<24} | {zustand_A(z, 'gem'):<30} "
          f"| {z['B_rein_rho']:8.0f} | {z['B_gem_rho']:7.0f} {z['B_gem_wP']:5.2f}")

# Z-Faktor vor Stufe 2: wie warm muss der Zwischenkühler bei 50 bar mindestens
# sein, damit Z > 0,65 (Siemens) bzw. Z ≥ 0,7 (Q-017)? Begründung für Zwischendruck 50 bar / 26 °C
p_zw_B = erg[GEM.name]["B"]["p_zw"]
zk_variation = []
for T_zk in (20.0, 25.0, 30.0, 35.0, 40.0):
    V2 = stufe(GEM, p_zw_B, T_zk, p_UEK, eta_V2)
    zk_variation.append(dict(T_ZK=T_zk, Z=V2["Z1"], T2=V2["T2"], w=V2["w"]))
print(f"\nZwischenkühler vor Stufe 2 (Pfad B, Gemisch, {p_zw_B:.1f} bar):")
for z in zk_variation:
    print(f"   {z['T_ZK']:4.0f} °C: Z = {z['Z']:.3f}, Austritt {z['T2']:.1f} °C, w₂ = {z['w']:.2f} kJ/kg")

# ---- 7) Dichtefenster des Gemischs (für die Excel-Heatmap) ------------------
P_RASTER = [80, 82, 85, 88, 91, 95, 100, 105, 110, 115]
T_RASTER = [15, 20, 25, 28, 30, 32, 35, 40]
dichtefeld = [[GEM.rho(p, T) if p > GEM.p_sicher else GEM._pt(p, T).rhomass() for T in T_RASTER]
              for p in P_RASTER]
zweiphasig = [[GEM.gasanteil(p, T) not in (0.0, 1.0) for T in T_RASTER] for p in P_RASTER]

# Linie ρ = 500 kg/m3 im überkritischen Gebiet (für Diagramm und Excel)
iso500 = [(float(T_bei_rho(p, RHO_MIN)), float(p)) for p in np.arange(84.0, 131.0, 4.0)]

# ---- 8) Abbildung 1: Pfade im Phasendiagramm des Gemischs -------------------
ROT, GRUEN, BLAU, VIOLETT, GRAU, ORANGE = "#CA220E", "#007335", "#0476D9", "#7030A0", "#8C8C8C", "#EE7203"
pg = GEM.pg
fig, ax = plt.subplots(figsize=(11, 7))
T_s = np.linspace(PropsSI("Ttriple", "CO2"), PropsSI("Tcrit", "CO2"), 150)
ax.plot(T_s - 273.15, [PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_s],
        color=GRAU, lw=1.2, ls="--", label="Sättigungslinie reines CO₂")
T_huelle = np.concatenate([pg["T_tau"], pg["T_blase"]])
p_huelle = np.concatenate([pg["p_tau"], pg["p_blase"]])
ax.fill(T_huelle, p_huelle, color=ROT, alpha=0.15, lw=0)
ax.plot(T_huelle, p_huelle, color=ROT, lw=1.6, label="Zweiphasengebiet Gemisch")
ax.plot(*zip(*iso500), color=ORANGE, lw=1.4, ls=":", label="ρ = 500 kg/m³ (Gemisch)")


def zeichne(pf, pumpe, farbe, ls, name):
    V1, V2 = pf["V"]
    T = [T_S2, V1["T2"], pf["ZK"]["T"], V2["T2"], pf["K"]["T"]]
    p = [p_S2, V1["p2"], V1["p2"], V2["p2"], pf["K"]["p"]]
    if pumpe:
        T.append(pf["P"]["T2"])
        p.append(pf["P"]["p2"])
    ax.plot(T, p, color=farbe, ls=ls, lw=2, marker="o", ms=4, label=name)


g = erg[GEM.name]
zeichne(g["A"], True, BLAU, "-", "A unterkritisch verflüssigen (80 bar, 20 °C)")
zeichne(g["B"], True, GRUEN, "-", "B überkritisch kühlen (91 bar, 26 °C) – gewählt")
zeichne(g["C"], False, VIOLETT, "--", "C durchverdichten")
ax.plot([T_S2, -40], [p_S2, p_S2], color=GRAU, lw=2, ls="-.", marker="o", ms=4,
        label="D tiefkalt bei 30 bar (bleibt zweiphasig)")
ax.plot(25, 80, "x", color=ROT, ms=10, mew=2.5, label="E Pumpe im Zweiphasengebiet (18 Vol-% Gas)")
ax.axhline(GEM.P_GRENZE + U_PG, color=ROT, lw=0.8, ls=":")
ax.text(-38, GEM.P_GRENZE + U_PG + 1.5, "Cricondenbar + 3 bar", color=ROT, fontsize=8)
ax.set(xlim=(-45, 100), ylim=(0, 125), xlabel="Temperatur [°C]", ylabel="Druck [bar]",
       title="Phasenpfade der gasförmigen Anlieferung S2 – Worst-Case-Gemisch")
ax.grid(alpha=0.3)
ax.legend(loc="upper left", fontsize=8)
fig.tight_layout()
fig.savefig("abb_phasenpfade_gemisch.png", dpi=200)
print("\ngespeichert: abb_phasenpfade_gemisch.png")

# ---- 9) Abbildung 2: Dichte am Pumpeneintritt über der Kühltemperatur -------
fig, ax = plt.subplots(figsize=(9, 5.5))
T_fein = np.arange(14.0, 36.01, 0.5)
rho_A = [GEM.rho(p_V[GEM.name], T) for T in T_fein]
rho_B = [GEM.rho(p_UEK, T) for T in T_fein]
ax.plot(T_fein, rho_A, color=BLAU, lw=2, label="Pfad A: 80 bar (unterkritisch)")
ax.plot(T_fein, rho_B, color=GRUEN, lw=2, label="Pfad B: 91 bar (überkritisch)")
ax.axhspan(0, RHO_MIN, color=ROT, alpha=0.08)
ax.axvline(T_K, color=GRUEN, lw=1.2, ls="--", label=f"Auslegung: {T_K:.0f} °C (Kühlwasser {T_KW:.0f} °C)")
ax.axhline(RHO_MIN, color=ROT, lw=1, ls="--", label="500 kg/m³: Grenze Pumpe (Q-001, Q-121)")
ax.axhline(RHO_WLOKA, color=ORANGE, lw=1, ls=":", label="650 kg/m³: vorsichtig (Q-017)")
ax.axvline(T_K_max_A[GEM.name], color=BLAU, lw=0.8, ls=":",
           label=f"Pfad A: höchstens {T_K_max_A[GEM.name]:.1f} °C (3 bar über der Blasenlinie)")
ax.axvspan(GEM.blasentemperatur(p_V[GEM.name]), GEM.tautemperatur(p_V[GEM.name]), color=BLAU, alpha=0.12,
           label="Pfad A zweiphasig (Gasblasen am Pumpeneintritt)")
sek = ax.secondary_xaxis("top", functions=(lambda T: T - DT_KUEHLER, lambda T: T + DT_KUEHLER))
sek.set_xlabel("nötige Kühlmitteltemperatur [°C] (T_K − 6 K, Q-120)")
ax.set(xlabel="Kühltemperatur T_K = Pumpeneintritt [°C]", ylabel="Dichte am Pumpeneintritt [kg/m³]",
       xlim=(14, 36), ylim=(150, 820))
ax.grid(alpha=0.3)
ax.legend(fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig("abb_kuehltemperatur_pumpeneintritt.png", dpi=200)
print("gespeichert: abb_kuehltemperatur_pumpeneintritt.png")


# ---- 10) Export für das Excel-Blatt -----------------------------------------
def rein_json(x):
    if isinstance(x, dict):
        return {k: rein_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rein_json(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if np.isnan(x) else float(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


export = dict(
    annahmen=dict(p_S2=p_S2, T_S2=T_S2, T_K=T_K, T_KW=T_KW, T_A=T_A, P_ZW=P_ZW, p_V=p_V, p_UEK=p_UEK,
                  p_ZW_DV=p_ZW_DV,
                  DT_KUEHLER=DT_KUEHLER, RHO_MIN=RHO_MIN, RHO_WLOKA=RHO_WLOKA, Z_MIN=Z_MIN,
                  GAS_MAX=GAS_MAX, U_PG=U_PG),
    grenze=dict(rein=REIN.P_GRENZE, gem=GEM.P_GRENZE, blase_min=p_blase_min),
    erg=erg, D_rein=D_rein, D_gem=D_gem, E=E, sens=sens, zk_variation=zk_variation,
    T_K_max_A=T_K_max_A, T_K_max_B=T_K_max_B, T_K_max_B_rein=T_K_max_B_rein,
    dichtefeld=dict(p=P_RASTER, T=T_RASTER, rho=dichtefeld, zweiphasig=zweiphasig),
    iso500=iso500,
)
with open("phasenpfade_ergebnisse.json", "w", encoding="utf-8") as f:
    json.dump(rein_json(export), f, ensure_ascii=False, indent=1)
print("gespeichert: phasenpfade_ergebnisse.json")
