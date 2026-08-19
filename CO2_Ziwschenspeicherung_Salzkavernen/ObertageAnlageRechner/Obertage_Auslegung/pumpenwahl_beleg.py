# -*- coding: utf-8 -*-
"""
Warum eine Pumpe und kein Verdichter - Rechnung und Beleg
==========================================================
  A  Der Realgasfaktor entlang der Prozesskette gegen das Siemens-Kriterium Z > 0,65
  B  Was es kosten wuerde, den Verdichter ueberhaupt anwendbar zu machen
  C  Belege: Herstellerdokument Q-047 und Mailauskunft Siemens Energy

Alle Zahlen live aus CoolProp (Span & Wagner 1996).
Aufruf: python pumpenwahl_beleg.py
"""
import numpy as np
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
Z_GRENZE = 0.65            # Siemens Energy, Auskunft Bleimund 08/2026
ETA_S = 0.80
P1, T1, P2 = 85.0, 15.0, 107.6

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


def welle(p1, T1_, p2, eta=ETA_S):
    h1 = CP.PropsSI("H", "P", p1 * BAR, "T", C2K(T1_), F)
    s1 = CP.PropsSI("S", "P", p1 * BAR, "T", C2K(T1_), F)
    h2s = CP.PropsSI("H", "P", p2 * BAR, "S", s1, F)
    return (h1 + (h2s - h1) / eta - h1) / 1000.0


RHO_N = CP.PropsSI("D", "T", 273.15, "P", 101325.0, F)
M_DOT = RHO_N * 100_000.0 / 3600.0

# --------------------------------------------------- A: Z entlang der Kette
PUNKTE = [
    ("Anlieferung Szenario 2\n30 bar · 15 °C", 30.0, 15.0),
    ("Verdichter Stufe 2 aus\n80 bar · 83,8 °C", 80.0, 83.8),
    ("Bohrlochkopf Ausspeisung\n120 bar · 34,2 °C", 120.0, 34.2),
    ("Verflüssiger Szenario 2\n80 bar · 25 °C", 80.0, 25.0),
    ("Pumpenaustritt\n107,6 bar · 17,5 °C", 107.6, 17.5),
    ("Anlieferung Szenario 1\n85 bar · 15 °C", 85.0, 15.0),
]
zs = [Z(p, t) for _, p, t in PUNKTE]

# --------------------------------------------------- B: Kosten der Turbotauglichkeit
T_TURBO = next(t for t in np.arange(T1, 120.0, 0.1) if Z(P1, t) >= Z_GRENZE)
q_heiz = h(P1, T_TURBO) - h(P1, T1)
w_pumpe = welle(P1, T1, P2)
w_verd = welle(P1, T_TURBO, P2)

# --------------------------------------------------- Zeichnen
fig = plt.figure(figsize=(16.6, 6.9))
gs = fig.add_gridspec(1, 3, width_ratios=[1.10, 0.96, 1.08], wspace=0.09,
                      left=0.118, right=0.977, top=0.895, bottom=0.155)
axA, axB, axC = (fig.add_subplot(gs[0, i]) for i in range(3))


def titel(ax, txt):
    ax.set_title(txt, fontsize=12.5, fontweight="bold", color=DUNKEL, loc="left", pad=13)


# ---------------- A
titel(axA, "A  Wo liegt der Betriebspunkt?")
ypos = np.arange(len(PUNKTE))
farben = [ORANGE if z >= Z_GRENZE else GRUEN for z in zs]
axA.barh(ypos, zs, height=0.62, color=farben, edgecolor="white", lw=1.4, zorder=3)
axA.axvline(Z_GRENZE, color=ROT, ls="--", lw=2.0, zorder=4)
axA.text(Z_GRENZE + 0.022, 2.15,
         f"Z = {de(Z_GRENZE,2)}\nGrenze der Siemens-\nLaufradrechnung",
         fontsize=9.0, color=ROT, fontweight="bold", va="center", linespacing=1.5, zorder=5)
for i, (lab, z) in enumerate(zip([p[0] for p in PUNKTE], zs)):
    axA.text(z + 0.012, i, de(z, 3), fontsize=9.8, fontweight="bold",
             color=farben[i], va="center", zorder=5)
axA.set_yticks(ypos)
axA.set_yticklabels([p[0] for p in PUNKTE], fontsize=8.8, color=DUNKEL, linespacing=1.4)
axA.set_xlim(0, 1.0)
axA.set_ylim(-0.55, len(PUNKTE) - 0.30)
axA.set_xlabel("Realgasfaktor  Z = p / (ρ · R · T)   [–]", fontsize=9.6)
axA.spines[["top", "right", "left"]].set_visible(False)
axA.tick_params(colors=GRAU, labelsize=9, left=False)
axA.grid(axis="x", color="#E4E9ED", lw=0.9)
axA.set_axisbelow(True)
from matplotlib.patches import Patch
axA.legend(handles=[Patch(facecolor=GRUEN, label="Pumpengebiet"),
                    Patch(facecolor=ORANGE, label="Verdichtergebiet")],
           frameon=False, fontsize=9.0, loc="upper right", bbox_to_anchor=(1.005, 1.03))

# ---------------- B
titel(axB, "B  Was ein Verdichter kosten würde")
axB.set_xlim(0, 10); axB.set_ylim(0, 10); axB.axis("off")

axB.text(0.15, 9.45, "Damit ein Turboverdichter am Auslegungspunkt\n"
                     "überhaupt rechenbar wäre, müsste der Strom erst\n"
                     f"von {T1:.0f} °C auf {de(T_TURBO,0)} °C aufgeheizt werden:",
         fontsize=9.3, color=GRAU, va="top", linespacing=1.65)

BLOECKE = [
    (f"{de(q_heiz*M_DOT/1000,1)} MW", "Heizleistung nur zum Aufheizen",
     f"{de(q_heiz,0)} kJ/kg · {de(M_DOT,1)} kg/s", ROT),
    (f"{de(w_verd*M_DOT,0)} kW", "Wellenleistung Verdichter",
     f"{de(w_verd,2)} kJ/kg bei ρ = {de(rho(P1,T_TURBO),0)} kg/m³", ORANGE),
    (f"{de(w_pumpe*M_DOT,0)} kW", "Wellenleistung Pumpe  ← gewählt",
     f"{de(w_pumpe,2)} kJ/kg bei ρ = {de(rho(P1,T1),0)} kg/m³", GRUEN),
]
y = 7.55
for wert, name, sub, farbe in BLOECKE:
    axB.add_patch(FancyBboxPatch((0.15, y - 1.42), 9.7, 1.50,
                                 boxstyle="round,pad=0,rounding_size=0.20",
                                 fc="#FFFFFF", ec=farbe, lw=2.0, zorder=2))
    axB.text(0.60, y - 0.48, wert, fontsize=16, fontweight="bold", color=farbe, va="center")
    axB.text(3.95, y - 0.34, name, fontsize=9.7, fontweight="bold", color=DUNKEL, va="center")
    axB.text(3.95, y - 0.85, sub, fontsize=8.5, color=GRAU, va="center")
    y -= 1.92

axB.add_patch(FancyBboxPatch((0.15, 0.35), 9.7, 1.45,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#FFF6EC", ec=ORANGE, lw=1.6, zorder=2))
axB.text(0.50, 1.38, f"Faktor {de(w_verd/w_pumpe,1)} bei der Wellenarbeit —",
         fontsize=10.0, fontweight="bold", color=DUNKEL, va="center", zorder=3)
axB.text(0.50, 0.95, f"und zusätzlich {de(q_heiz*M_DOT/1000,1)} MW Wärme, das",
         fontsize=10.0, fontweight="bold", color=DUNKEL, va="center", zorder=3)
axB.text(0.50, 0.58, f"{de(q_heiz*M_DOT/w_pumpe/M_DOT,0)}-fache der gesamten Pumpenleistung.",
         fontsize=10.0, fontweight="bold", color=DUNKEL, va="center", zorder=3)

# ---------------- C
titel(axC, "C  Der Beleg — Hersteller selbst")
axC.set_xlim(0, 10); axC.set_ylim(0, 10); axC.axis("off")

axC.add_patch(FancyBboxPatch((0.15, 5.55), 9.7, 4.05,
                             boxstyle="round,pad=0,rounding_size=0.20",
                             fc="#F4F7F9", ec=BLAU, lw=1.8, zorder=2))
axC.text(0.55, 9.20, "Q-047 · Siemens Energy White Paper (2024), S. 8",
         fontsize=9.3, fontweight="bold", color=BLAU, va="center")
axC.text(0.55, 8.30,
         "„The decision to use a pump depends on the\n"
         "temperature of the CO₂, which dictates its density\n"
         "and compressibility.“",
         fontsize=10.0, color=DUNKEL, va="center", linespacing=1.75, style="italic")
axC.text(0.55, 6.85,
         "Dieselbe Quelle nennt die Zentrifugalpumpe als eine\n"
         "der vier Technologien der CO₂-Verdichtung und be-\n"
         "ziffert die Einsparung gegenüber der Verdichterstufe\n"
         "mit bis zu 10 %.",
         fontsize=9.0, color=GRAU, va="center", linespacing=1.7)

axC.add_patch(FancyBboxPatch((0.15, 1.65), 9.7, 3.55,
                             boxstyle="round,pad=0,rounding_size=0.20",
                             fc="#FFF6EC", ec=ORANGE, lw=1.8, zorder=2))
axC.text(0.55, 4.82, "Auskunft Siemens Energy, 08/2026",
         fontsize=9.3, fontweight="bold", color=ORANGE, va="center")
axC.text(0.55, 3.95,
         "„Damit die Berechnung der Laufräder in unseren\n"
         "Berechnungsprogrammen zuverlässig ausgeführt wird,\n"
         "bleiben wir bei einem Z-Wert von > 0,65.“",
         fontsize=9.6, color=DUNKEL, va="center", linespacing=1.75, style="italic")
axC.text(0.55, 2.35,
         "Für den Auslegungspunkt nennt der Hersteller Z ≈ 0,25.\n"
         "Eigene Rechnung: 0,179. Der Turboverdichter ist damit\n"
         "herstellerseitig nicht belastbar auslegbar.",
         fontsize=9.0, color=GRAU, va="center", linespacing=1.7)

axC.text(0.15, 0.75,
         "Beides bestätigt die Wahl: nicht „Pumpe ist einfacher“,\n"
         "sondern der Verdichter ist hier nicht anwendbar.",
         fontsize=9.6, fontweight="bold", color=DUNKEL, va="center", linespacing=1.7)

# ---------------- Fuss
fig.text(0.028, 0.052,
         f"Randbedingungen: Anlieferung {P1:.0f} bar / {T1:.0f} °C · Bohrlochkopf {de(P2,1)} bar · "
         f"ηₛ = {de(ETA_S,2)} · 100.000 Nm³/h = {de(M_DOT,1)} kg/s · "
         f"Z-Grenze {de(Z_GRENZE,2)} ist ein Software-Gültigkeitsbereich, keine physikalische Grenze",
         fontsize=8.6, color=GRAU)
fig.text(0.028, 0.022,
         "Stoffdaten CoolProp / Span & Wagner (1996) · eigene Rechnung · Q-047 · "
         "Auskunft Siemens Energy Duisburg, 08/2026",
         fontsize=8, color="#7A7A7A")

fig.savefig("abb_pumpenwahl_beleg.png", dpi=220)
print("gespeichert: abb_pumpenwahl_beleg.png")
print(f"\n  Z-Werte:")
for (lab, p, t), z in zip(PUNKTE, zs):
    print(f"    {lab.splitlines()[0]:28} p={p:6.1f} T={t:5.1f}  Z={z:.3f}")
print(f"\n  Turbotauglich (Z>={Z_GRENZE}) bei 85 bar erst ab {T_TURBO:.1f} degC")
print(f"    Aufheizen 15 -> {T_TURBO:.1f} degC: {q_heiz:.1f} kJ/kg = {q_heiz*M_DOT/1000:.2f} MW")
print(f"    Welle Verdichter {w_verd:.2f} kJ/kg = {w_verd*M_DOT:.0f} kW")
print(f"    Welle Pumpe      {w_pumpe:.2f} kJ/kg = {w_pumpe*M_DOT:.0f} kW   -> Faktor {w_verd/w_pumpe:.1f}")
