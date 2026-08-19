# -*- coding: utf-8 -*-
"""
Wie das Teufen- und Druckfenster zustande kommt
================================================
Erzaehlt das Vorgehen statt nur das Ergebnis:

  A  Vorgehen und Validierung   Modell nach Q-028 nachgebaut und geprueft
  B  Das Teufenfenster          drei Randbedingungen spannen 799-1139 m auf
  C  Der Zielkonflikt           flach = mehr Anteil, tief = mehr Durchsatz

Die Fenstergrenzen werden live gerechnet. Die ratenabhaengigen Werte in Panel C
stammen aus Modul 3_teufenoptimierung (report_teufe.txt).
Aufruf: python teufenfenster_herleitung.py
"""
import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

F = "CO2"
BAR = 1e5

# --- Randbedingungen (identisch mit co2_kaverne3.py) ---------------------
T_OBERFLAECHE = 10.0     # degC
GEO_GRADIENT = 0.03      # K/m
RHO_SALZ = 2200.0        # kg/m3
G_ERD = 9.81
ANTEIL_PMAX = 0.80       # - von lithostatisch
ANTEIL_PMIN = 0.30       # -
MARGE_K = 3.0            # K Sicherheitsabstand zur kritischen Temperatur
Z_GEOMECH = 700.0        # m, standortabhaengig
Z_ANNAHME = 1200.0       # m, bisherige Annahme der Auslegung

T_KRIT = CP.PropsSI("Tcrit", F) - 273.15
P_KRIT = CP.PropsSI("pcrit", F) / BAR

BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
GRAU, HELLGRAU = "#4A4A4A", "#B8C4CC"

# --- die drei Schranken, live gerechnet ---------------------------------
Z_MIN_T = (T_KRIT + MARGE_K - T_OBERFLAECHE) / GEO_GRADIENT      # Untergrenze
Z_MAX_P = P_KRIT * BAR / (ANTEIL_PMIN * RHO_SALZ * G_ERD)        # Obergrenze
Z_U = max(Z_MIN_T, Z_GEOMECH)
Z_O = Z_MAX_P

# --- ratenabhaengige Werte aus Modul 3 (report_teufe.txt) ---------------
TEUFEN = [799, 884, 969, 1054, 1139]
AG_PROZ = [84, 82, 78, 74, 67]
DURCHSATZ = [144, 276, 406, 532, 644]      # kt/a
GRENZRATE = [10, 19, 29, 41, 53]           # kg/s

# ------------------------------------------------------------- Zeichnen
fig = plt.figure(figsize=(16.6, 6.9))
gs = fig.add_gridspec(1, 3, width_ratios=[1.06, 0.86, 1.08], wspace=0.26,
                      left=0.033, right=0.978, top=0.895, bottom=0.155)
axA, axB, axC = (fig.add_subplot(gs[0, i]) for i in range(3))


def titel(ax, txt):
    ax.set_title(txt, fontsize=12.5, fontweight="bold", color=DUNKEL, loc="left", pad=13)


# ============================================== A  Vorgehen und Validierung
titel(axA, "A  Vorgehen — und woran es geprüft ist")
axA.set_xlim(0, 10); axA.set_ylim(0, 10); axA.axis("off")

SCHRITTE = [
    ("1", "Rechenmodell nachgebaut",
     "Q-028 (Buzogany & Kruck, SMRI 2022) rechnet\n"
     "eine CO₂-Salzkaverne. Dasselbe Vorgehen in\n"
     "Python, Stoffdaten aus CoolProp.", GRUEN),
    ("2", "gegen die Quelle validiert",
     "Erst wenn die Zahlen der Quelle reproduziert\n"
     "werden, ist das Modell belastbar.", BLAU),
    ("3", "auf die eigene Kaverne angewendet",
     "Betriebsfenster und Teufe werden damit zum\n"
     "Ergebnis — nicht zur Vorgabe.", ORANGE),
]
y = 9.40
for nr, kopf, text, farbe in SCHRITTE:
    axA.add_patch(FancyBboxPatch((0.05, y - 0.60), 0.58, 0.58,
                                 boxstyle="circle,pad=0", fc=farbe, ec="none", zorder=3))
    axA.text(0.34, y - 0.31, nr, fontsize=11, fontweight="bold", color="white",
             ha="center", va="center", zorder=4)
    axA.text(0.92, y - 0.18, kopf, fontsize=10.2, fontweight="bold", color=farbe, va="center")
    axA.text(0.92, y - 1.06, text, fontsize=8.8, color=GRAU, va="center", linespacing=1.7)
    y -= 2.06

axA.add_patch(FancyBboxPatch((0.05, 0.15), 9.85, 3.10,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#F4F7F9", ec=HELLGRAU, lw=1.3, zorder=2))
axA.text(0.42, 2.92, "Validierung gegen Q-028", fontsize=9.8, fontweight="bold",
         color=DUNKEL, va="center", zorder=3)

SPALTEN_X = (0.42, 4.20, 6.30, 8.10)
axA.text(SPALTEN_X[0], 2.32, "Größe", fontsize=8.4, color=GRAU, va="center", zorder=3)
axA.text(SPALTEN_X[1], 2.32, "eigen", fontsize=8.4, color=GRUEN, va="center",
         fontweight="bold", zorder=3)
axA.text(SPALTEN_X[2], 2.32, "Q-028", fontsize=8.4, color=BLAU, va="center",
         fontweight="bold", zorder=3)
axA.text(SPALTEN_X[3], 2.32, "Abweichung", fontsize=8.4, color=GRAU, va="center", zorder=3)

VAL = [("kritische Teufe (T = T_krit)", "699 m", "725 m", "3,6 %"),
       ("Arbeitsgasanteil", "62 – 68 %", "22 – 32 %", "obere Schranke")]
for i, (n, e, q, a) in enumerate(VAL):
    yy = 1.76 - i * 0.52
    axA.text(SPALTEN_X[0], yy, n, fontsize=8.6, color=DUNKEL, va="center", zorder=3)
    axA.text(SPALTEN_X[1], yy, e, fontsize=8.8, color=GRUEN, fontweight="bold",
             va="center", zorder=3)
    axA.text(SPALTEN_X[2], yy, q, fontsize=8.8, color=BLAU, fontweight="bold",
             va="center", zorder=3)
    axA.text(SPALTEN_X[3], yy, a, fontsize=8.4, color=GRAU, va="center", zorder=3)

axA.text(0.42, 0.62, "Der Arbeitsgaswert ist kein Widerspruch: die eigene Zahl ist\n"
                     "die isotherme obere Schranke, die Quelle rechnet ratenabhängig.",
         fontsize=8.2, color=GRAU, va="center", style="italic", linespacing=1.65, zorder=3)

# ============================================== B  Teufenfenster
titel(axB, "B  Woraus das Fenster folgt")
axB.set_xlim(0, 10)
axB.set_ylim(1320, 600)
axB.add_patch(Rectangle((0, 600), 10, Z_U - 600, fc=ROT, alpha=0.10, ec="none", zorder=1))
axB.add_patch(Rectangle((0, Z_O), 10, 1320 - Z_O, fc=ROT, alpha=0.10, ec="none", zorder=1))
axB.add_patch(Rectangle((0, Z_U), 10, Z_O - Z_U, fc=GRUEN, alpha=0.16, ec="none", zorder=1))

axB.axhline(Z_MIN_T, color=ROT, lw=2.0, ls="--", zorder=4)
axB.text(0.35, Z_MIN_T - 18,
         f"T_Gebirge > T_krit + {MARGE_K:.0f} K   →   z > {Z_MIN_T:.0f} m\n"
         "sonst ist Flüssigphase in der Kaverne möglich",
         fontsize=8.5, color=ROT, fontweight="bold", va="bottom", linespacing=1.6, zorder=6)

axB.axhline(Z_MAX_P, color=ROT, lw=2.0, ls="--", zorder=4)
axB.text(0.35, Z_MAX_P + 18,
         f"p_min < p_krit   →   z < {Z_MAX_P:.0f} m\n"
         "sonst nur der flache Teil der Dichtekurve",
         fontsize=8.5, color=ROT, fontweight="bold", va="top", linespacing=1.6, zorder=6)

axB.axhline(Z_GEOMECH, color=GRAU, lw=1.5, ls=":", zorder=4)
axB.text(9.65, Z_GEOMECH - 14, f"Geomechanik   z > {Z_GEOMECH:.0f} m", fontsize=8.2,
         color=GRAU, ha="right", va="bottom", zorder=6)

axB.annotate("", xy=(9.1, Z_U), xytext=(9.1, Z_O),
             arrowprops=dict(arrowstyle="<->", color=GRUEN, lw=2.2), zorder=6)
axB.text(8.75, (Z_U + Z_O) / 2, f"zulässig\n{Z_U:.0f} – {Z_O:.0f} m", fontsize=10.5,
         fontweight="bold", color=GRUEN, ha="right", va="center", linespacing=1.6, zorder=6)

axB.plot([2.6], [Z_ANNAHME], "o", ms=11, color=ORANGE, mec="white", mew=1.6, zorder=8)
axB.annotate(f"bisherige Annahme {Z_ANNAHME:.0f} m\nliegt {Z_ANNAHME - Z_O:.0f} m darunter",
             xy=(2.6, Z_ANNAHME), xytext=(6.1, 1272), fontsize=8.5, color=ORANGE,
             fontweight="bold", ha="center", va="center", linespacing=1.6, zorder=9,
             bbox=dict(boxstyle="round,pad=0.26", fc="white", ec=ORANGE, lw=1.2, alpha=0.96),
             arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.3))

axB.set_ylabel("Teufe  [m]", fontsize=9.8)
axB.set_xticks([])
axB.spines[["top", "right", "bottom"]].set_visible(False)
axB.tick_params(colors=GRAU, labelsize=9)

# ============================================== C  Zielkonflikt
titel(axC, "C  Zwei Optima — je nach Zielgröße")
axC.plot(TEUFEN, AG_PROZ, "o-", color=GRUEN, lw=2.4, ms=7, zorder=5)
axC.set_xticks(TEUFEN)
axC.set_xticklabels([f"{z} m\nmax {r} kg/s" for z, r in zip(TEUFEN, GRENZRATE)],
                    fontsize=8.4, linespacing=1.5)
axC.set_xlabel("Teufe und die dazu zulässige Ausspeicherrate", fontsize=9.6)
axC.set_ylabel("Arbeitsgasanteil  [%]", fontsize=9.8, color=GRUEN)
axC.tick_params(axis="y", colors=GRUEN, labelsize=9)
axC.tick_params(axis="x", colors=GRAU)
axC.set_ylim(58, 94)
axC.spines[["top"]].set_visible(False)
axC.grid(axis="y", color="#E4E9ED", lw=0.9)
axC.set_axisbelow(True)

axD = axC.twinx()
axD.plot(TEUFEN, DURCHSATZ, "s--", color=BLAU, lw=2.4, ms=7, zorder=5)
axD.set_ylabel("Jahresdurchsatz  [kt/a]", fontsize=9.8, color=BLAU)
axD.tick_params(axis="y", colors=BLAU, labelsize=9)
axD.set_ylim(60, 780)
axD.spines[["top"]].set_visible(False)

axC.annotate(f"{AG_PROZ[0]} %", (TEUFEN[0], AG_PROZ[0]), textcoords="offset points",
             xytext=(8, -16), fontsize=9, color=GRUEN, fontweight="bold", zorder=7)
axC.annotate(f"{AG_PROZ[-1]} %", (TEUFEN[-1], AG_PROZ[-1]), textcoords="offset points",
             xytext=(-32, -16), fontsize=9, color=GRUEN, fontweight="bold", zorder=7)
axD.annotate(f"{DURCHSATZ[0]} kt/a", (TEUFEN[0], DURCHSATZ[0]), textcoords="offset points",
             xytext=(8, 6), fontsize=9, color=BLAU, fontweight="bold", zorder=7)
axD.annotate(f"{DURCHSATZ[-1]} kt/a", (TEUFEN[-1], DURCHSATZ[-1]), textcoords="offset points",
             xytext=(-54, 4), fontsize=9, color=BLAU, fontweight="bold", zorder=7)

axC.text(0.035, 0.975,
         "flach  →  hoher Anteil nutzbar, kleine zulässige Rate\n"
         "tief    →  hoher Durchsatz, aber mehr Kissengas\n"
         "Welches Optimum gilt, entscheidet das Geschäftsmodell.",
         transform=axC.transAxes, fontsize=8.6, color=DUNKEL, fontweight="bold",
         va="top", linespacing=1.75, zorder=9,
         bbox=dict(boxstyle="round,pad=0.36", fc="white", ec=HELLGRAU, lw=1.0, alpha=0.96))

# ------------------------------------------------------------- Fuss
fig.text(0.033, 0.052,
         f"Randbedingungen: Gebirge {T_OBERFLAECHE:.0f} °C + {GEO_GRADIENT*100:.0f} K/100 m · "
         f"ρ_Salz {RHO_SALZ:.0f} kg/m³ · p_max {ANTEIL_PMAX*100:.0f} %, p_min "
         f"{ANTEIL_PMIN*100:.0f} % des lithostatischen Drucks · Sicherheitsmarge "
         f"{MARGE_K:.0f} K zur kritischen Temperatur · Volumen 650.000 m³",
         fontsize=8.4, color=GRAU)
fig.text(0.033, 0.021,
         "Fenstergrenzen live gerechnet (CoolProp / Span & Wagner 1996) · ratenabhängige Werte "
         "aus Modul 3_teufenoptimierung · Q-028 Buzogany & Kruck (SMRI 2022) · "
         "UA = 546 kW/K ist eine Annahme und geht direkt in die Grenzrate ein",
         fontsize=8, color="#7A7A7A")

fig.savefig("abb_teufenfenster_herleitung.png", dpi=220)
print("gespeichert: abb_teufenfenster_herleitung.png\n")
print(f"  T_krit = {T_KRIT:.2f} degC,  p_krit = {P_KRIT:.2f} bar")
print(f"  Untergrenze aus Temperatur:  z > {Z_MIN_T:.0f} m")
print(f"  Obergrenze aus p_min<p_krit: z < {Z_MAX_P:.0f} m")
print(f"  Geomechanik:                 z > {Z_GEOMECH:.0f} m")
print(f"  -> zulaessiges Fenster: {Z_U:.0f} - {Z_O:.0f} m")
print(f"  Die Annahme {Z_ANNAHME:.0f} m liegt {Z_ANNAHME - Z_O:.0f} m darunter.")
