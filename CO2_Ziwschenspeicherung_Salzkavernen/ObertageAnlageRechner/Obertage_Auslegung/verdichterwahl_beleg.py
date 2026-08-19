# -*- coding: utf-8 -*-
"""
Welcher Verdichter - Betriebspunkt, Bauart und Beleg (Szenario 2)
==================================================================
Gegenstueck zu pumpenwahl_beleg.py, aber fuer die gasfoermige Anlieferung.

  A  Der Betriebspunkt der Maschine      Volumenstrom, Druckverhaeltnis, Z, Leistung
  B  Welche Bauart?                      Herstellervergleich aus Q-047
  C  Was daraus folgt                    Kandidaten und offene Punkte

Alle gerechneten Zahlen live aus CoolProp (Span & Wagner 1996).
Aufruf: python verdichterwahl_beleg.py
"""
import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

F = "CO2"
BAR = 1e5
C2K = lambda t: t + 273.15
K2C = lambda t: t - 273.15
R_S = 8.314462618 / CP.PropsSI("M", F)

P1, T1 = 30.0, 15.0
P_ZW, T_ZW = 49.0, 40.0
P_UM = 80.0
ETA_S = 0.80
Z_GRENZE = 0.65

BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
GRAU, HELLGRAU = "#4A4A4A", "#B8C4CC"


def de(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def rho(p, T):
    return CP.PropsSI("D", "P", p * BAR, "T", C2K(T), F)


def Z(p, T):
    return p * BAR / (rho(p, T) * R_S * C2K(T))


def h(p, T):
    return CP.PropsSI("H", "P", p * BAR, "T", C2K(T), F) / 1000.0


def stufe(p1, Ta, p2):
    h1 = CP.PropsSI("H", "P", p1 * BAR, "T", C2K(Ta), F)
    s1 = CP.PropsSI("S", "P", p1 * BAR, "T", C2K(Ta), F)
    h2s = CP.PropsSI("H", "P", p2 * BAR, "S", s1, F)
    h2 = h1 + (h2s - h1) / ETA_S
    return (h2 - h1) / 1000.0, K2C(CP.PropsSI("T", "P", p2 * BAR, "H", h2, F))


RHO_N = CP.PropsSI("D", "T", 273.15, "P", 101325.0, F)
M_MIN, M_MAX = RHO_N * 50_000.0 / 3600.0, RHO_N * 100_000.0 / 3600.0

w1, Ta1 = stufe(P1, T1, P_ZW)
w2, Ta2 = stufe(P_ZW, T_ZW, P_UM)
W_GES = w1 + w2
Q_ZW = h(P_ZW, Ta1) - h(P_ZW, T_ZW)
Q_VF = h(P_UM, Ta2) - h(P_UM, 25.0)

V1_MIN, V1_MAX = M_MIN / rho(P1, T1) * 3600, M_MAX / rho(P1, T1) * 3600
V2_MIN, V2_MAX = M_MIN / rho(P_ZW, T_ZW) * 3600, M_MAX / rho(P_ZW, T_ZW) * 3600

# ----------------------------------------------------------- Zeichnen
fig = plt.figure(figsize=(16.6, 6.9))
gs = fig.add_gridspec(1, 3, width_ratios=[1.00, 1.22, 1.00], wspace=0.15,
                      left=0.033, right=0.978, top=0.895, bottom=0.115)
axA, axB, axC = (fig.add_subplot(gs[0, i]) for i in range(3))
for ax in (axA, axB, axC):
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")


def titel(ax, txt):
    ax.set_title(txt, fontsize=12.5, fontweight="bold", color=DUNKEL, loc="left", pad=13)


# ================================================== A
titel(axA, "A  Der Betriebspunkt der Maschine")

ZEILEN = [
    ("Massenstrom", f"{de(M_MIN,1)} – {de(M_MAX,1)} kg/s", DUNKEL),
    ("Eintrittsvolumenstrom Stufe 1", f"{V1_MIN:.0f} – {V1_MAX:.0f} m³/h", BLAU),
    ("Eintrittsvolumenstrom Stufe 2", f"{V2_MIN:.0f} – {V2_MAX:.0f} m³/h", GRAU),
    ("Druckverhältnis gesamt", f"{de(P_UM/P1,2)}   ({de((P_UM/P1)**0.5,2)} je Stufe)", DUNKEL),
    ("Realgasfaktor Z am Eintritt", f"{de(Z(P1,T1),3)}   →  Turbogebiet", GRUEN),
    ("Wellenleistung", f"{de(W_GES*M_MIN/1000,2)} – {de(W_GES*M_MAX/1000,2)} MW", ORANGE),
    ("Kühllast gesamt", f"{de((Q_ZW+Q_VF)*M_MIN/1000,1)} – {de((Q_ZW+Q_VF)*M_MAX/1000,1)} MW", BLAU),
]
y = 9.15
for name, wert, farbe in ZEILEN:
    axA.text(0.20, y, name, fontsize=9.4, color=GRAU, va="center")
    axA.text(0.20, y - 0.46, wert, fontsize=11.0, fontweight="bold", color=farbe, va="center")
    axA.plot([0.20, 9.80], [y - 0.80, y - 0.80], color="#EDF1F4", lw=1.1, zorder=1)
    y -= 1.10

axA.add_patch(FancyBboxPatch((0.20, 0.15), 9.60, 1.32,
                             boxstyle="round,pad=0,rounding_size=0.16",
                             fc="#E6F2EA", ec=GRUEN, lw=1.5, zorder=2))
axA.text(0.55, 1.05, "Z = 0,805 liegt klar über der Siemens-Grenze 0,65.",
         fontsize=9.4, fontweight="bold", color=GRUEN, va="center", zorder=3)
axA.text(0.55, 0.55, "Anders als in Szenario 1 ist der Turboverdichter hier\n"
                     "herstellerseitig auslegbar.",
         fontsize=9.0, color=DUNKEL, va="center", linespacing=1.6, zorder=3)

# ================================================== B
titel(axB, "B  Welche Bauart?  —  Herstellervergleich Q-047")

SPALTEN = ["Getriebe-\nverdichter", "Einwellen-\nverdichter", "Kolben-\nverdichter"]
ZEILEN_B = [
    ("Investitionskosten", ["am niedrigsten", "10–15 % höher", "8–10 % höher"]),
    ("Leistungsaufnahme", ["Referenz", "10–20 % höher", "5–10 % höher"]),
    ("Grundfläche", ["12,5 × 10,5 m", "20 × 12,5 m", "20 × 15 m"]),
    ("Regelbereich", ["30–40 %", "30–40 %", "75–85 %"]),
    ("Verfügbarkeit", ["> 99 %", "> 99 %", "95–97 %"]),
    ("Montagekosten", ["50 %", "50 %", "150 %"]),
]
X0, XW = 3.05, 2.28
axB.add_patch(FancyBboxPatch((X0 - 0.10, 1.62), XW - 0.06, 7.72,
                             boxstyle="round,pad=0,rounding_size=0.14",
                             fc="#E6F2EA", ec=GRUEN, lw=1.8, zorder=1))
for j, sp in enumerate(SPALTEN):
    axB.text(X0 + j * XW + XW / 2 - 0.10, 8.95, sp, fontsize=9.0, fontweight="bold",
             color=GRUEN if j == 0 else DUNKEL, ha="center", va="center",
             linespacing=1.5, zorder=3)
y = 7.95
for name, werte in ZEILEN_B:
    axB.text(0.10, y, name, fontsize=8.9, color=GRAU, va="center")
    for j, w in enumerate(werte):
        axB.text(X0 + j * XW + XW / 2 - 0.10, y, w, fontsize=8.7,
                 fontweight="bold" if j == 0 else "normal",
                 color=GRUEN if j == 0 else DUNKEL, ha="center", va="center", zorder=3)
    axB.plot([0.10, 9.90], [y - 0.52, y - 0.52], color="#EDF1F4", lw=1.0, zorder=0)
    y -= 1.04

axB.text(0.10, 1.15, "Achtung beim Zitieren: die Tabelle gilt für 1 Mt/a von 2 auf 150 bar\n"
                     "(Zementwerk, 10–11 MW). Unser Fall ist kleiner und hat ein anderes\n"
                     "Druckverhältnis — die relativen Aussagen gelten, die absoluten nicht.",
         fontsize=8.5, color=ROT, va="center", linespacing=1.65, style="italic")

# ================================================== C
titel(axC, "C  Was daraus folgt")

axC.add_patch(FancyBboxPatch((0.20, 6.35), 9.60, 3.05,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#E6F2EA", ec=GRUEN, lw=1.8, zorder=2))
axC.text(0.55, 8.95, "Bauart: Getriebeverdichter", fontsize=10.6, fontweight="bold",
         color=GRUEN, va="center", zorder=3)
axC.text(0.55, 7.95,
         "Zwei Stufen mit Zwischenkühlung sitzen bauartbedingt\n"
         "in je eigenem Gehäuse — genau das, was hier gebraucht\n"
         "wird. Bei CO₂ ist er die Standardbauart: Porthos,\n"
         "Snøhvit, Brevik, Net Zero Teesside, Tangguh.",
         fontsize=8.9, color=DUNKEL, va="center", linespacing=1.72, zorder=3)

axC.add_patch(FancyBboxPatch((0.20, 3.45), 9.60, 2.55,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#F4F7F9", ec=HELLGRAU, lw=1.3, zorder=2))
axC.text(0.55, 5.60, "Herstellerkandidaten", fontsize=10.0, fontweight="bold",
         color=DUNKEL, va="center", zorder=3)
axC.text(0.55, 4.55,
         "Everllence RG-Reihe — bis 250 bar (Q-048, Q-049)\n"
         "Siemens Energy STC-GV — bis rund 200 bar (Q-047)\n"
         "Kolbenverdichter als Variante bei hohem Regelbedarf",
         fontsize=8.9, color=DUNKEL, va="center", linespacing=1.72, zorder=3)

axC.add_patch(FancyBboxPatch((0.20, 0.20), 9.60, 3.00,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#FFF6EC", ec=ORANGE, lw=1.6, zorder=2))
axC.text(0.55, 2.80, "Offen", fontsize=10.0, fontweight="bold", color=ORANGE,
         va="center", zorder=3)
axC.text(0.55, 1.55,
         "Angebote und Kennfelder — Anfrage an Siemens läuft\n"
         "Kolben- gegen Turboverdichter bei 2:1 Regelbereich\n"
         "Kühlkonzept für 7–14 MW: Wasser oder Luft\n"
         "Werkstoffe und Wellendichtung bei feuchtem CO₂",
         fontsize=8.9, color=DUNKEL, va="center", linespacing=1.72, zorder=3)

# ----------------------------------------------------------- Fuss
fig.text(0.033, 0.052,
         f"Randbedingungen: Anlieferung {P1:.0f} bar / {T1:.0f} °C gasförmig · zwei Stufen auf "
         f"{P_UM:.0f} bar · Zwischenkühlung {T_ZW:.0f} °C · ηₛ = {de(ETA_S,2)} · "
         f"50.000–100.000 Nm³/h = {de(M_MIN,1)}–{de(M_MAX,1)} kg/s",
         fontsize=8.5, color=GRAU)
fig.text(0.033, 0.022,
         "eigene Rechnung (CoolProp / Span & Wagner 1996) · Herstellervergleich aus Q-047, "
         "Siemens Energy White Paper (2024), Figure 5 · Q-048 · Q-049",
         fontsize=8, color="#7A7A7A")

fig.savefig("abb_verdichterwahl_beleg.png", dpi=220)
print("gespeichert: abb_verdichterwahl_beleg.png\n")
print(f"  V Stufe 1: {V1_MIN:.0f} - {V1_MAX:.0f} m3/h   Z = {Z(P1,T1):.3f}")
print(f"  V Stufe 2: {V2_MIN:.0f} - {V2_MAX:.0f} m3/h   Z = {Z(P_ZW,T_ZW):.3f}")
print(f"  Welle: {W_GES*M_MIN/1000:.2f} - {W_GES*M_MAX/1000:.2f} MW")
print(f"  Kuehllast: {(Q_ZW+Q_VF)*M_MIN/1000:.1f} - {(Q_ZW+Q_VF)*M_MAX/1000:.1f} MW")
