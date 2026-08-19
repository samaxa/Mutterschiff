# -*- coding: utf-8 -*-
"""
Der Rechenweg hinter dem Teufenfenster
=======================================
Dritte Folie der Reihe nach rechenweg_pumpe.py und rechenweg_verdichter.py.

  A  Was geht hinein - und von wem stammt es?   Stoffdaten / Q-028 / eigene Annahme
  B  Der Rechenweg                              zwei Divisionen, von Hand nachvollziehbar
  C  Die Probe                                  Kontrolle an den Raendern

Alle Zahlen live aus CoolProp (Span & Wagner 1996).
Aufruf: python rechenweg_teufenfenster.py
"""
import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

F = "CO2"
BAR = 1e5

T_OBERFLAECHE = 10.0     # degC   Annahme der Quelle Q-028
GEO_GRADIENT = 0.03      # K/m    Annahme der Quelle Q-028
RHO_SALZ = 2200.0        # kg/m3  Standardwert Steinsalz
G_ERD = 9.81
ANTEIL_PMAX = 0.80       # -      Faustwert, standortabhaengig
ANTEIL_PMIN = 0.30       # -      Faustwert, standortabhaengig
MARGE_K = 3.0            # K      eigene Wahl
Z_ANNAHME = 1200.0       # m      bisherige Auslegungsannahme

T_KRIT = CP.PropsSI("Tcrit", F) - 273.15
P_KRIT = CP.PropsSI("pcrit", F) / BAR

BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
GRAU, HELLGRAU = "#4A4A4A", "#B8C4CC"
LILA = "#7A4FBF"


def de(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


GRAD_LITHO = RHO_SALZ * G_ERD / BAR            # bar/m
GRAD_PMIN = ANTEIL_PMIN * GRAD_LITHO           # bar/m
T_ZIEL = T_KRIT + MARGE_K
Z_MIN_T = (T_ZIEL - T_OBERFLAECHE) / GEO_GRADIENT
Z_MAX_P = P_KRIT / GRAD_PMIN

# ------------------------------------------------------------- Zeichnen
fig = plt.figure(figsize=(16.6, 6.9))
gs = fig.add_gridspec(1, 3, width_ratios=[1.14, 1.16, 0.94], wspace=0.16,
                      left=0.032, right=0.978, top=0.895, bottom=0.115)
axA, axB, axC = (fig.add_subplot(gs[0, i]) for i in range(3))
for ax in (axA, axB, axC):
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")


def titel(ax, txt):
    ax.set_title(txt, fontsize=12.5, fontweight="bold", color=DUNKEL, loc="left", pad=13)


# ================================================== A  Herkunft der Eingaben
titel(axA, "A  Was geht hinein — und von wem?")

EINGABEN = [
    ("T_krit", f"{de(T_KRIT,2)} °C", "Stoffdaten", GRUEN),
    ("p_krit", f"{de(P_KRIT,2)} bar", "Stoffdaten", GRUEN),
    ("Gebirge an der Oberfläche", f"{T_OBERFLAECHE:.0f} °C", "Q-028", BLAU),
    ("geothermischer Gradient", f"{de(GEO_GRADIENT*100,0)} K/100 m", "Q-028", BLAU),
    ("Dichte Steinsalz", f"{RHO_SALZ:.0f} kg/m³", "Standardwert", GRUEN),
    ("p_max / p_min lithostatisch", f"{ANTEIL_PMAX*100:.0f} % / {ANTEIL_PMIN*100:.0f} %",
     "eigene Annahme", ORANGE),
    ("Sicherheitsmarge zu T_krit", f"{MARGE_K:.0f} K", "eigene Wahl", ORANGE),
]
axA.text(0.20, 9.35, "Größe", fontsize=8.6, color=GRAU, va="center")
axA.text(5.35, 9.35, "Wert", fontsize=8.6, color=GRAU, va="center")
axA.text(7.55, 9.35, "Herkunft", fontsize=8.6, color=GRAU, va="center")
axA.plot([0.20, 9.85], [9.02, 9.02], color=HELLGRAU, lw=1.1)

y = 8.55
for name, wert, quelle, farbe in EINGABEN:
    axA.text(0.20, y, name, fontsize=9.3, color=DUNKEL, va="center")
    axA.text(5.35, y, wert, fontsize=9.5, color=DUNKEL, fontweight="bold", va="center")
    axA.add_patch(FancyBboxPatch((7.55, y - 0.23), 2.28, 0.46,
                                 boxstyle="round,pad=0,rounding_size=0.12",
                                 fc=farbe, ec="none", alpha=0.16, zorder=2))
    axA.text(8.69, y, quelle, fontsize=8.5, color=farbe, fontweight="bold",
             ha="center", va="center", zorder=3)
    y -= 0.86

axA.add_patch(FancyBboxPatch((0.20, 0.25), 9.65, 2.30,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#FFF6EC", ec=ORANGE, lw=1.6, zorder=2))
axA.text(0.55, 2.15, "Das Ergebnis ist ein Mischwert", fontsize=9.8, fontweight="bold",
         color=ORANGE, va="center", zorder=3)
axA.text(0.55, 1.15,
         "Zwei Eingaben stammen aus Q-028, damit die Validierung aufgeht.\n"
         "Zwei sind eigene Setzungen — und genau an ihnen hängt das Ergebnis:\n"
         "ohne die 3-K-Marge läge die Untergrenze bei 699 statt 799 m.",
         fontsize=8.8, color=DUNKEL, va="center", linespacing=1.75, zorder=3)

# ================================================== B  Rechenweg
titel(axB, "B  Der Rechenweg — zwei Divisionen")

axB.add_patch(FancyBboxPatch((0.05, 5.32), 9.85, 4.28,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#F4F7F9", ec=HELLGRAU, lw=1.2, zorder=1))
axB.text(0.42, 9.18, "① Untergrenze — wie tief muss es sein, damit es warm genug ist?",
         fontsize=9.5, fontweight="bold", color=DUNKEL, va="center", zorder=3)
axB.text(0.42, 8.48, "Bedingung:", fontsize=8.8, color=GRAU, va="center", zorder=3)
axB.text(2.10, 8.48, f"T(z) = {T_OBERFLAECHE:.0f} + {de(GEO_GRADIENT,2)} · z   >   "
                     f"T_krit + {MARGE_K:.0f} K = {de(T_ZIEL,2)} °C",
         fontsize=9.4, color=DUNKEL, fontweight="bold", va="center", zorder=3)
axB.add_patch(FancyBboxPatch((0.42, 6.62), 9.05, 1.42,
                             boxstyle="round,pad=0,rounding_size=0.14",
                             fc="white", ec=GRUEN, lw=1.6, zorder=2))
axB.text(0.75, 7.62, f"z  >  ({de(T_ZIEL,2)} − {T_OBERFLAECHE:.0f}) / {de(GEO_GRADIENT,2)}"
                     f"   =   {de(T_ZIEL-T_OBERFLAECHE,2)} / {de(GEO_GRADIENT,2)}",
         fontsize=10.4, color=DUNKEL, fontweight="bold", va="center", zorder=3)
axB.text(0.75, 7.00, f"z  >  {Z_MIN_T:.0f} m", fontsize=13, color=GRUEN,
         fontweight="bold", va="center", zorder=3)
axB.text(0.42, 6.02, "flacher wäre das Gebirge kälter — dann kann CO₂ in der Kaverne kondensieren",
         fontsize=8.5, color=GRAU, style="italic", va="center", zorder=3)

axB.add_patch(FancyBboxPatch((0.05, 0.28), 9.85, 4.62,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#F4F7F9", ec=HELLGRAU, lw=1.2, zorder=1))
axB.text(0.42, 4.48, "② Obergrenze — wie tief darf es sein, damit p_min unter p_krit bleibt?",
         fontsize=9.5, fontweight="bold", color=DUNKEL, va="center", zorder=3)
axB.text(0.42, 3.80, "Gradient:", fontsize=8.8, color=GRAU, va="center", zorder=3)
_litho_pa = f"{RHO_SALZ*G_ERD:,.0f}".replace(",", ".")
axB.text(2.10, 3.80, f"ρ_Salz · g = {RHO_SALZ:.0f} · {de(G_ERD,2)} = "
                     f"{_litho_pa} Pa/m = {de(GRAD_LITHO,4)} bar/m",
         fontsize=9.2, color=DUNKEL, fontweight="bold", va="center", zorder=3)
axB.text(0.42, 3.22, "davon 30 %:", fontsize=8.8, color=GRAU, va="center", zorder=3)
axB.text(2.10, 3.22, f"{de(ANTEIL_PMIN,2)} · {de(GRAD_LITHO,4)} = {de(GRAD_PMIN,4)} bar/m",
         fontsize=9.2, color=DUNKEL, fontweight="bold", va="center", zorder=3)
axB.add_patch(FancyBboxPatch((0.42, 1.42), 9.05, 1.42,
                             boxstyle="round,pad=0,rounding_size=0.14",
                             fc="white", ec=GRUEN, lw=1.6, zorder=2))
axB.text(0.75, 2.42, f"z  <  p_krit / {de(GRAD_PMIN,4)}   =   {de(P_KRIT,2)} / {de(GRAD_PMIN,4)}",
         fontsize=10.4, color=DUNKEL, fontweight="bold", va="center", zorder=3)
axB.text(0.75, 1.80, f"z  <  {Z_MAX_P:.0f} m", fontsize=13, color=GRUEN,
         fontweight="bold", va="center", zorder=3)
axB.text(0.42, 0.80, "tiefer bliebe der Speicher immer über p_krit — der große Dichteabfall\n"
                     "beim Ausspeichern fände gar nicht statt",
         fontsize=8.5, color=GRAU, style="italic", va="center", linespacing=1.6, zorder=3)

# ================================================== C  Probe
titel(axC, "C  Die Probe an den Rändern")

SPALTEN = (0.20, 2.55, 4.60, 6.65)
axC.text(SPALTEN[0], 9.40, "Teufe", fontsize=8.6, color=GRAU, va="center")
axC.text(SPALTEN[1], 9.40, "T_Gebirge", fontsize=8.6, color=GRAU, va="center")
axC.text(SPALTEN[2], 9.40, "p_min", fontsize=8.6, color=GRAU, va="center")
axC.text(SPALTEN[3], 9.40, "Urteil", fontsize=8.6, color=GRAU, va="center")
axC.plot([0.20, 9.85], [9.08, 9.08], color=HELLGRAU, lw=1.1)

y = 8.55
for z in (700, 799, 969, 1139, 1200):
    T = T_OBERFLAECHE + GEO_GRADIENT * z
    pmin = GRAD_PMIN * z
    rand = z in (799, 1139)
    if rand:
        urteil = "Untergrenze" if z == 799 else "Obergrenze"
        farbe = BLAU
    elif T < T_ZIEL:
        urteil, farbe = "T zu niedrig", ROT
    elif pmin > P_KRIT:
        urteil, farbe = "p_min > p_krit", ROT
    else:
        urteil, farbe = "im Fenster", GRUEN
    axC.text(SPALTEN[0], y, f"{z} m", fontsize=9.4, color=DUNKEL,
             fontweight="bold" if rand else "normal", va="center")
    axC.text(SPALTEN[1], y, f"{de(T,1)} °C", fontsize=9.4, color=DUNKEL, va="center")
    axC.text(SPALTEN[2], y, f"{de(pmin,1)} bar", fontsize=9.4, color=DUNKEL, va="center")
    axC.text(SPALTEN[3], y, urteil, fontsize=8.8, color=farbe, fontweight="bold", va="center")
    y -= 0.86

axC.text(0.20, 4.05, f"p_krit = {de(P_KRIT,2)} bar   ·   T_krit + {MARGE_K:.0f} K = "
                     f"{de(T_ZIEL,2)} °C", fontsize=8.6, color=GRAU, va="center",
         style="italic")

axC.add_patch(FancyBboxPatch((0.20, 0.25), 9.65, 3.28,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#FDECEA", ec=ROT, lw=1.6, zorder=2))
axC.text(0.55, 3.10, "Zwei Befunde", fontsize=9.8, fontweight="bold", color=ROT,
         va="center", zorder=3)
axC.text(0.55, 2.28,
         f"Die angenommenen {Z_ANNAHME:.0f} m liegen außerhalb: dort wäre\n"
         f"p_min = {de(GRAD_PMIN*Z_ANNAHME,1)} bar, also {de(GRAD_PMIN*Z_ANNAHME-P_KRIT,1)} bar "
         f"über dem kritischen Druck.",
         fontsize=8.8, color=DUNKEL, va="center", linespacing=1.7, zorder=3)
axC.text(0.55, 1.00,
         "Der Auslegungsdurchsatz 54,9 kg/s liegt über der höchsten\n"
         "zulässigen Rate im ganzen Fenster (53 kg/s bei 1139 m).\n"
         "Durchsatz, Teufe und Volumen sind nicht frei kombinierbar.",
         fontsize=8.8, color=DUNKEL, va="center", linespacing=1.7, zorder=3)

# ------------------------------------------------------------- Fuss
fig.text(0.032, 0.052,
         f"Randbedingungen: Gebirge {T_OBERFLAECHE:.0f} °C + {GEO_GRADIENT*100:.0f} K/100 m · "
         f"ρ_Salz {RHO_SALZ:.0f} kg/m³ · p_max {ANTEIL_PMAX*100:.0f} %, p_min "
         f"{ANTEIL_PMIN*100:.0f} % des lithostatischen Drucks · Sicherheitsmarge "
         f"{MARGE_K:.0f} K · Volumen 650.000 m³",
         fontsize=8.5, color=GRAU)
fig.text(0.032, 0.022,
         "Stoffdaten CoolProp / Span & Wagner (1996) · eigene Rechnung · "
         "Q-028 Buzogany & Kruck (SMRI 2022) · die Faustwerte 80 % / 30 % und die "
         "3-K-Marge sind standortabhängig zu ersetzen",
         fontsize=8, color="#7A7A7A")

fig.savefig("abb_rechenweg_teufenfenster.png", dpi=220)
print("gespeichert: abb_rechenweg_teufenfenster.png\n")
print(f"  T_krit {T_KRIT:.2f} degC | p_krit {P_KRIT:.2f} bar")
print(f"  Gradient litho {GRAD_LITHO:.4f} bar/m | p_min-Gradient {GRAD_PMIN:.4f} bar/m")
print(f"  Untergrenze z > {Z_MIN_T:.1f} m | Obergrenze z < {Z_MAX_P:.1f} m")
print(f"  Bei {Z_ANNAHME:.0f} m: p_min = {GRAD_PMIN*Z_ANNAHME:.1f} bar "
      f"({GRAD_PMIN*Z_ANNAHME-P_KRIT:+.1f} bar gegen p_krit)")
