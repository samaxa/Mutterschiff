# -*- coding: utf-8 -*-
"""
Schritt 3 (Gemisch) - Einspeicherpfad mit Worst-Case-Gemisch vs. reines CO2
============================================================================
Gleiche Rechnung wie die Excel-Rechenübersicht (CO2_Zwischenspeicher_
Rechenuebersicht_Gemisch.xlsx): alle Zahlen kommen aus excel_werte_gemisch.py,
das auch die Mappe füllt. Skript und Excel zeigen also exakt dieselben Werte.

  1) Gassäule Kaverne -> Zieldruck am Bohrlochkopf (210 bar unten, 1200 m)
  2) S1 (dichte Phase):  Pumpe 91 bar / 15 °C -> Bohrlochkopf
  3) S2 (gasförmig 30 bar / 15 °C):
       alte Verdichtung   wie reines CO2: 1 Stufe bis 60 bar, auf 20 °C
                          kühlen/verflüssigen -> beim Gemisch bleibt es
                          gasförmig (3,4 bar unter der Taulinie), die Pumpe
                          kann nicht fördern
       neue Verdichtung   bis p_V = 90 bar (Cricondenbar 82,2 bar + 3 bar
                          Unsicherheit, Reserve), dort in der dichten Phase
                          auf 20 °C kühlen (kein Zweiphasengebiet, wie Q-016:
                          Endstufe 100 bar, dann 20 °C), Pumpe bis Kopfdruck
                          - 1 Stufe:  111,6 °C > 95 °C (Q-016) -> unzulässig
                          - 2 Stufen: Zwischendruck sqrt(30 * 90) = 52 bar,
                            Zwischenkühlung auf 20 °C (gasförmig)
  4) Vergleich:        Durchverdichten in 2 Stufen (Zwischendruck 50 bar)
                       bis Kopfdruck, Nachkühler

Reines CO2 wird mit denselben Funktionen gerechnet (p_V = 60 bar) und
liefert exakt die Werte der Mappe für reines CO2 (pruefung_rein()).

Annahmen (Übersicht der Mappe, Q-016): Wirkungsgrad Verdichter 84 % / 82 %,
Pumpe 80 %, Kühlung auf 20 °C, höchstens 95 °C je Stufe, Durchsatz
50.000-100.000 Nm3/h. Unsicherheit der Phasengrenze ±3 bar
(Dokumentation_Stoffmodelle_Validierung.docx, Kapitel 9).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import excel_werte_gemisch as ew

A, U_PG = ew.A, ew.U_PG
ROT, GRUEN, BLAU, VIOLETT, GRAU = "#CA220E", "#007335", "#0476D9", "#7030A0", "#7F7F7F"


def de(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


# ---- 1) Rechnen (identisch mit der Excel-Mappe) ------------------------------
print("Prüfung: gleiche Rechnung mit reinem CO2 = Mappe für reines CO2")
ew.pruefung_rein()
R = ew.werte(ew.REIN, alles=False)          # reines CO2, p_V = 60 bar
M = ew.werte()                              # Gemisch, p_V = 90 bar
pg = M["pg"]
p_cb = pg["cricondenbar"][1]


def summen(W):
    S1, S2, S2v, Dv = W["S1"], W["S2"], W["S2v"], W["Dv"]
    rho_n = S1["rho_n"]
    return dict(p_kopf=W["kav"]["voll"]["p_kopf"], S1=S1["w"], S2=S2["w1"] + S2["wP"],
                S2v=S2v["w1"] + S2v["w2"] + S2["wP"], Dv=Dv["w1"] + Dv["w2"],
                m=(A["V_min"] * rho_n / 3600, A["V_max"] * rho_n / 3600))


sR, sM = summen(R), summen(M)
alt = M["alt"]

print(f"\n{'':<44}{'reines CO₂':>14}{'Gemisch':>14}")
zeilen = [
    ("Kopfdruck bei voller Kaverne [bar]", sR["p_kopf"], sM["p_kopf"]),
    ("Massenstrom 50.000 Nm³/h [kg/s]", sR["m"][0], sM["m"][0]),
    ("S1 Pumpe: w [kJ/kg]", sR["S1"], sM["S1"]),
    ("S1 Pumpe: Austritt [°C]", R["S1"]["T2"], M["S1"]["T2"]),
    ("S2 Kühlerdruck p_V [bar]", R["A"]["p_V"], M["A"]["p_V"]),
    ("S2 1 Stufe: Austritt Verdichter [°C]", R["S2"]["T1a"], M["S2"]["T1a"]),
    ("S2 1 Stufe: w gesamt [kJ/kg]", sR["S2"], sM["S2"]),
    ("S2 2 Stufen: Zwischendruck [bar]", R["S2v"]["p_zw"], M["S2v"]["p_zw"]),
    ("S2 2 Stufen: Austritt Stufe 1 [°C]", R["S2v"]["T1a"], M["S2v"]["T1a"]),
    ("S2 2 Stufen: Austritt Stufe 2 [°C]", R["S2v"]["T2a"], M["S2v"]["T2a"]),
    ("S2 2 Stufen: w gesamt [kJ/kg]", sR["S2v"], sM["S2v"]),
    ("S2 Pumpe: Austritt [°C]", R["S2"]["TPa"], M["S2"]["TPa"]),
    ("Durchverdichten: w gesamt [kJ/kg]", sR["Dv"], sM["Dv"]),
]
for name, r, m in zeilen:
    print(f"{name:<44}{r:14.2f}{m:14.2f}")
print(f"\nPhase nach dem Kühler (20 °C): reines CO₂ flüssig (60 bar), "
      f"Gemisch {M['S2']['phaseV']} ({A['p_V']:.0f} bar, {de(A['p_V'] - p_cb)} bar über der Cricondenbar)")
print(f"Alte Verdichtung beim Gemisch: 1 Stufe bis {alt['p_V']:.0f} bar, {de(alt['T1a'])} °C, nach Kühlung auf "
      f"20 °C {alt['phase']} ({de(alt['abstand_tau'])} bar unter der Taulinie {de(alt['p_tau_TK'])} bar) "
      "-> Pumpe kann nicht fördern")
print(f"S2 1 Stufe beim Gemisch: {de(M['S2']['T1a'])} °C > {A['T_max']:.0f} °C -> 2 Stufen Pflicht")
print(f"Neue Verdichtung (2 Stufen) braucht {sM['S2v'] / sR['S2'] - 1:+.0%} Arbeit gegenüber reinem CO₂ "
      f"(alt, 1 Stufe) und {1 - sM['S2v'] / sM['Dv']:.0%} weniger als Durchverdichten.")


# ---- 2) Diagramm 1: Pfade im Phasendiagramm des Gemischs --------------------
def pfade(W):
    S2, S2v, Dv, S1 = W["S2"], W["S2v"], W["Dv"], W["S1"]
    p_V, p_kopf = W["A"]["p_V"], W["kav"]["voll"]["p_kopf"]
    ein = (A["T_S2"], A["p_S2"])
    return dict(
        S1=[(A["T_S1"], A["p_S1"]), (S1["T2"], p_kopf)],
        S2=[ein, (S2["T1a"], p_V), (A["T_K"], p_V), (S2["TPa"], p_kopf)],
        S2v=[ein, (S2v["T1a"], S2v["p_zw"]), (A["T_K"], S2v["p_zw"]), (S2v["T2a"], p_V), (A["T_K"], p_V),
             (S2["TPa"], p_kopf)],
        Dv=[ein, (Dv["T1a"], A["p_zw"]), (A["T_K"], A["p_zw"]), (Dv["T2a"], p_kopf), (S2["TPa"], p_kopf)])


P = pfade(M)
T_s = np.linspace(PropsSI("Ttriple", "CO2"), PropsSI("Tcrit", "CO2"), 150)
p_s = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_s]) / 1e5

fig, ax = plt.subplots(figsize=(12, 7))
ax.plot(T_s - 273.15, p_s, color=GRAU, lw=1.2, zorder=3, label="Sättigungslinie reines CO₂ (Vergleich)")
huelle_T = np.concatenate([pg["T_tau"], pg["T_blase"]])
huelle_p = np.concatenate([pg["p_tau"], pg["p_blase"]])
ax.fill(huelle_T, huelle_p, color="#F4B6B0", lw=0, zorder=1)
ax.plot(huelle_T, huelle_p, color=ROT, lw=2.0, zorder=4, label="Phasengrenze Gemisch (Tau-/Blasenlinie)")
ax.fill_between(pg["T_blase"], pg["p_blase"] - U_PG, pg["p_blase"] + U_PG, color=ROT, alpha=0.12, lw=0, zorder=1,
                label="Unsicherheit Phasengrenze ±3 bar")
ax.fill_between(pg["T_tau"], pg["p_tau"] - U_PG, pg["p_tau"] + U_PG, color=ROT, alpha=0.12, lw=0, zorder=1)
T_kG, p_kG = pg["krit"]
ax.plot(T_kG, p_kG, "o", color=ROT, ms=7, markeredgecolor="white", zorder=5)
ax.axhline(p_cb + U_PG, color=ROT, lw=0.8, ls="--", zorder=2)
ax.text(68, p_cb + U_PG + 1.2, f"Cricondenbar + 3 bar = {de(p_cb + U_PG)} bar", color=ROT, fontsize=8)

ax.plot(*zip(*P["S1"]), "-D", color=GRUEN, lw=2.5, ms=5, zorder=7, label="S1: Pumpe")
ax.plot(*zip(*P["S2"]), "-o", color=BLAU, lw=1.4, ms=4, zorder=6, alpha=0.45,
        label=f"S2 neu, 1 Stufe bis {A['p_V']:.0f} bar ({de(M['S2']['T1a'])} °C > 95 °C ✘)")
ax.plot(*zip(*P["S2v"]), "-o", color=BLAU, lw=2.6, ms=5, zorder=7,
        label=f"S2 neu, 2 Stufen bis {A['p_V']:.0f} bar → Kühler (dicht) → Pumpe ✔")
ax.plot(*zip(*P["Dv"]), "--o", color=VIOLETT, lw=1.6, ms=4, zorder=6, label="Vergleich: Durchverdichten (2 Stufen)")
alt_pfad = [(A["T_S2"], A["p_S2"]), (alt["T1a"], alt["p_V"]), (A["T_K"], alt["p_V"])]
ax.plot(*zip(*alt_pfad), ":", marker="x", color="#404040", lw=2.2, ms=7, zorder=6,
        label="S2 alt: 1 Stufe bis 60 bar wie reines CO₂ – bleibt gasförmig ✘")
ax.axvline(A["T_max"], color="#404040", lw=0.8, ls="--", zorder=2)
ax.text(A["T_max"] + 1, 5, "95 °C (Q-016)", fontsize=8, color="#404040")

txt = dict(fontsize=8.5, color="#303030", zorder=8)
ax.annotate(f"alt: 20 °C / 60 bar gasförmig,\n{de(alt['abstand_tau'])} bar unter der Taulinie",
            (A["T_K"], alt["p_V"]), xytext=(30, 30), arrowprops=dict(arrowstyle="->", color="#404040"), **txt)
ax.annotate(f"Kühler: {A['p_V']:.0f} bar → 20 °C, dicht\n{de(A['p_V'] - p_cb)} bar über der Cricondenbar",
            (A["T_K"], A["p_V"]), xytext=(-18, 106), arrowprops=dict(arrowstyle="->", color=BLAU), **txt)
ax.text(30, sM["p_kopf"] + 3, f"Bohrlochkopf {de(sM['p_kopf'])} bar", **txt)
ax.text(A["T_S2"] + 2, A["p_S2"] - 5, "S2 Netzübergabe", **txt)
ax.text(A["T_S1"] - 20, A["p_S1"] - 1, "S1 Netzübergabe", **txt)
ax.text(-15, 25, "zweiphasig", color=ROT, fontsize=10, weight="bold", zorder=8)
ax.set(xlim=(-20, 120), ylim=(0, 130), xlabel="Temperatur [°C]", ylabel="Druck [bar]")
ax.set_title("Einspeicherung S1/S2 mit Worst-Case-Gemisch: alte und neue Verdichtung (bis Bohrlochkopf)",
             fontsize=11)
ax.grid(alpha=0.3, zorder=0)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig("abb_einspeicherpfad_gemisch.png", dpi=170)
print("\ngespeichert: abb_einspeicherpfad_gemisch.png")

# ---- 3) Diagramm 2: spezifische Arbeit rein vs. Gemisch ---------------------
balken = [("S1 reines CO₂", [0, 0, R["S1"]["w"]]),
          ("S1 Gemisch", [0, 0, M["S1"]["w"]]),
          ("S2 reines CO₂ (1 Stufe, 60 bar)", [R["S2"]["w1"], 0, R["S2"]["wP"]]),
          ("S2 Gemisch neu, 1 Stufe 90 bar *", [M["S2"]["w1"], 0, M["S2"]["wP"]]),
          ("S2 Gemisch neu, 2 Stufen 90 bar", [M["S2v"]["w1"], M["S2v"]["w2"], M["S2"]["wP"]]),
          ("Durchverdichten reines CO₂", [R["Dv"]["w1"], R["Dv"]["w2"], 0]),
          ("Durchverdichten Gemisch", [M["Dv"]["w1"], M["Dv"]["w2"], 0])]
teile = [("Verdichter 1. Stufe", "#EE7203"), ("Verdichter 2. Stufe", "#C55A11"), ("Pumpe", GRUEN)]
fig2, ax2 = plt.subplots(figsize=(10, 5.2))
namen = [b[0] for b in balken]
w = np.array([b[1] for b in balken], dtype=float)
links = np.zeros(len(balken))
for j, (tname, farbe) in enumerate(teile):
    ax2.barh(namen, w[:, j], left=links, color=farbe, label=tname, height=0.6)
    links += w[:, j]
for y, summe in enumerate(links):
    ax2.text(summe + 1, y, f"{de(summe)} kJ/kg", va="center", fontsize=8.5, weight="bold")
ax2.invert_yaxis()
ax2.set_xlim(0, links.max() * 1.2)
ax2.set_xlabel("spezifische Arbeit bis Bohrlochkopf [kJ/kg]")
ax2.set_title("Spezifische Arbeit: reines CO₂ vs. Worst-Case-Gemisch", fontsize=11)
ax2.grid(axis="x", alpha=0.3)
ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=8, frameon=False)
fig2.text(0.5, 0.01, f"* 1 Stufe erreicht {de(M['S2']['T1a'])} °C > 95 °C (Q-016) – nur rechnerisch. Alte "
                     "Verdichtung (60 bar) beim Gemisch: keine Kette möglich, das Gemisch bleibt gasförmig.",
          ha="center", fontsize=8, color=ROT)
fig2.tight_layout(rect=[0, 0.04, 1, 1])
fig2.savefig("abb_arbeit_rein_vs_gemisch.png", dpi=170)
print("gespeichert: abb_arbeit_rein_vs_gemisch.png")

# ---- 4) Diagramm 3: Gassäule rein vs. Gemisch -------------------------------
fig3, (b1, b2) = plt.subplots(1, 2, figsize=(10, 5.5), sharey=True)
for stoff, farbe, name in ((ew.REIN, "#00304F", "reines CO₂"), (ew.GEM, ROT, "Gemisch")):
    z, p, T, rho, _ = ew.saeule(A["p_max"], stoff=stoff)
    b1.plot(rho, z, color=farbe, lw=2, label=name)
    b2.plot(p, z, color=farbe, lw=2, label=f"{name}: Kopf {de(p[-1])} bar")
b1.set(xlabel="Dichte [kg/m³]", ylabel="Teufe [m]", title="Dichte in der Gassäule")
b2.set(xlabel="Druck [bar]", title="Druck in der Gassäule")
b1.invert_yaxis()
for b in (b1, b2):
    b.grid(alpha=0.3)
    b.legend(fontsize=8.5)
fig3.suptitle("Gassäule Kaverne V1 (1200 m, 210 bar unten): reines CO₂ vs. Gemisch", fontsize=11)
fig3.tight_layout()
fig3.savefig("abb_gassaeule_rein_vs_gemisch.png", dpi=170)
print("gespeichert: abb_gassaeule_rein_vs_gemisch.png")
