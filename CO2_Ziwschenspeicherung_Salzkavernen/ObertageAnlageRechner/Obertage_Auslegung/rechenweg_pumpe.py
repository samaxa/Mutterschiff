# -*- coding: utf-8 -*-
"""
Von Zustand 1 zu Zustand 2 - der Rechenweg der Pumpenauslegung
===============================================================
Macht die 3,21 kJ/kg und die 176 kW Schritt fuer Schritt nachvollziehbar.

  A  Was ist gegeben, was gesucht?   Zustand 1 -> Zustand 2
  B  Der Rechenweg                   Enthalpiebilanz, isentrop, Wirkungsgrad
  C  Von der Arbeit zur Maschine     Leistungskette bis zur Motornenngroesse

Alle Zahlen live aus CoolProp (Span & Wagner 1996) - nichts eingetippt.
Aufruf: python rechenweg_pumpe.py
"""
import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

F = "CO2"
BAR = 1e5
C2K = lambda t: t + 273.15
K2C = lambda t: t - 273.15


def de(x, n=2):
    """Zahl mit deutschem Dezimalkomma."""
    return f"{x:.{n}f}".replace(".", ",")


# ----------------------------------------------------------- Randbedingungen
P1, T1 = 85.0, 15.0        # bar, degC  Anlieferung OGE (Blatt 01)
P2 = 107.6                 # bar        Bohrlochkopf (Modul 1_auslegung)
ETA_S = 0.80               # -          isentroper Wirkungsgrad (Annahme)
ETA_M = 0.955              # -          Motorwirkungsgrad (Annahme)
MARGE = 1.10               # -          Antriebsmarge API 610 (> 55 kW)
VN_MIN, VN_MAX = 50_000.0, 100_000.0     # Nm3/h

# Uniper-Palette
BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
GRAU, HELLGRAU = "#4A4A4A", "#B8C4CC"

# ----------------------------------------------------------- Rechnen
RHO_N = CP.PropsSI("D", "T", 273.15, "P", 101325.0, F)
M_MIN = RHO_N * VN_MIN / 3600.0
M_MAX = RHO_N * VN_MAX / 3600.0

h1 = CP.PropsSI("H", "P", P1 * BAR, "T", C2K(T1), F)
s1 = CP.PropsSI("S", "P", P1 * BAR, "T", C2K(T1), F)
rho1 = CP.PropsSI("D", "P", P1 * BAR, "T", C2K(T1), F)
u1 = CP.PropsSI("U", "P", P1 * BAR, "T", C2K(T1), F)

h2s = CP.PropsSI("H", "P", P2 * BAR, "S", s1, F)
T2s = K2C(CP.PropsSI("T", "P", P2 * BAR, "S", s1, F))

w_s = (h2s - h1) / 1000.0
w = w_s / ETA_S
h2 = h1 + (h2s - h1) / ETA_S
T2 = K2C(CP.PropsSI("T", "P", P2 * BAR, "H", h2, F))

dp = (P2 - P1) * BAR
v1 = 1.0 / rho1
w_naeh = v1 * dp / ETA_S / 1000.0          # Handrechnung

V_MIN = M_MIN / rho1 * 3600.0
V_MAX = M_MAX / rho1 * 3600.0
H_FOERDER = dp / (rho1 * 9.81)

P_HYD = M_MAX * w_s
P_WELLE = M_MAX * w
P_EL = P_WELLE / ETA_M
P_MOTOR = P_WELLE * MARGE
NORM = [110, 132, 160, 200, 250, 315]
P_NENN = next(n for n in NORM if n >= P_MOTOR)

# ----------------------------------------------------------- Zeichnen
fig = plt.figure(figsize=(16.6, 6.9))
gs = fig.add_gridspec(1, 3, width_ratios=[1.00, 1.34, 0.90], wspace=0.14,
                      left=0.032, right=0.978, top=0.895, bottom=0.115)
axA, axB, axC = (fig.add_subplot(gs[0, i]) for i in range(3))
for ax in (axA, axB, axC):
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")


def titel(ax, txt):
    ax.set_title(txt, fontsize=12.5, fontweight="bold", color=DUNKEL, loc="left", pad=13)


def kasten(ax, x, y, w_, h_, fc, ec, lw=1.8):
    ax.add_patch(FancyBboxPatch((x, y), w_, h_,
                                boxstyle="round,pad=0,rounding_size=0.22",
                                fc=fc, ec=ec, lw=lw, zorder=2))


# ================================================== A  Zustand 1 -> Zustand 2
titel(axA, "A  Was ist gegeben, was gesucht?")

kasten(axA, 0.25, 5.95, 9.5, 3.45, "#E6F2EA", GRUEN)
axA.text(0.72, 8.98, "ZUSTAND 1   Anlieferung OGE", fontsize=10.5, fontweight="bold",
         color=GRUEN, va="center")
axA.text(0.72, 8.32, f"{P1:.0f} bar   ·   {T1:.0f} °C   ·   flüssig / dicht",
         fontsize=12.5, fontweight="bold", color=DUNKEL, va="center")
for i, (k, v) in enumerate([
        ("h₁", de(h1 / 1000, 2) + " kJ/kg"),
        ("s₁", de(s1 / 1000, 4) + " kJ/(kg·K)"),
        ("ρ₁", de(rho1, 1) + " kg/m³")]):
    axA.text(0.95, 7.62 - i * 0.50, k, fontsize=10, color=GRAU, va="center")
    axA.text(2.10, 7.62 - i * 0.50, "=  " + v, fontsize=10.2, color=DUNKEL,
             fontweight="bold", va="center")
axA.text(0.95, 6.30, f"h = u + p·v = {de(u1/1000,1)} + {de(P1*BAR*v1/1000,1)} kJ/kg",
         fontsize=8.9, color=GRAU, va="center", style="italic")

axA.add_patch(FancyArrowPatch((5.0, 5.82), (5.0, 4.68), arrowstyle="-|>",
                              mutation_scale=17, lw=2.4, color=BLAU, zorder=4))
axA.text(5.38, 5.25, "PUMPE", fontsize=11.5, fontweight="bold", color=BLAU, va="center")

kasten(axA, 0.25, 1.15, 9.5, 3.35, "#E8F1FA", BLAU)
axA.text(0.72, 4.08, "ZUSTAND 2   Bohrlochkopf", fontsize=10.5, fontweight="bold",
         color=BLAU, va="center")
axA.text(0.72, 3.42, f"{de(P2,1)} bar   ·   {de(T2,1)} °C   ·   flüssig / dicht",
         fontsize=12.5, fontweight="bold", color=DUNKEL, va="center")
axA.text(0.95, 2.66, "p₂", fontsize=10, color=GRAU, va="center")
axA.text(2.10, 2.66, "=  gegeben  (Gassäule → 210 bar)", fontsize=10.2, color=DUNKEL,
         fontweight="bold", va="center")
axA.text(0.95, 2.16, "h₂", fontsize=10, color=ROT, va="center")
axA.text(2.10, 2.16, "=  GESUCHT", fontsize=10.2, color=ROT, fontweight="bold", va="center")
axA.text(0.95, 1.66, "T₂", fontsize=10, color=ROT, va="center")
axA.text(2.10, 1.66, "=  folgt aus h₂", fontsize=10.2, color=ROT,
         fontweight="bold", va="center")

axA.text(0.25, 0.48, "Die Pumpe ist adiabat (q = 0)  →  Wellenarbeit = h₂ − h₁.\n"
                     "Die ganze Aufgabe reduziert sich auf: wie groß ist h₂ ?",
         fontsize=9.6, color=DUNKEL, fontweight="bold", va="center", linespacing=1.7)

# ================================================== B  Rechenweg
titel(axB, "B  Der Rechenweg — vier Schritte")

SCHRITTE = [
    ("1", "Die ideale, verlustfreie Maschine erzeugt keine Entropie:",
     f"s₂ = s₁ = {de(s1/1000,4)} kJ/(kg·K)",
     "zwei Zustandsgrößen (p₂, s₂) legen den Zustand vollständig fest", GRUEN),
    ("2", "Damit ist h₂ₛ ablesbar — aus Tabelle oder log p-h-Diagramm:",
     f"h₂ₛ({de(P2,1)} bar ; s₁) = {de(h2s/1000,2)} kJ/kg",
     f"zugehörige Temperatur T₂ₛ = {de(T2s,2)} °C", GRUEN),
    ("3", "Ideale (isentrope) Arbeit als Differenz der Enthalpien:",
     f"wₛ = h₂ₛ − h₁ = {de(h2s/1000,2)} − {de(h1/1000,2)} = {de(w_s,3)} kJ/kg",
     "das ist die theoretische Untergrenze — verlustfrei", BLAU),
    ("4", f"Reibung berücksichtigen, ηₛ = {de(ETA_S,2)} (Annahme):",
     f"w = wₛ / ηₛ = {de(w_s,3)} / {de(ETA_S,2)} = {de(w,2)} kJ/kg",
     f"T₂ = {de(T2,2)} °C — davon {de(T2s-T1,2)} K Verdichtung, {de(T2-T2s,2)} K Reibung", ORANGE),
]
y = 9.80
for nr, kopf, formel, fuss, farbe in SCHRITTE:
    axB.add_patch(FancyBboxPatch((0.05, y - 1.02), 0.60, 0.60,
                                 boxstyle="circle,pad=0", fc=farbe, ec="none", zorder=3))
    axB.text(0.35, y - 0.72, nr, fontsize=11.5, fontweight="bold", color="white",
             ha="center", va="center", zorder=4)
    axB.text(0.90, y - 0.06, kopf, fontsize=9.4, color=GRAU, va="center")
    axB.add_patch(FancyBboxPatch((0.90, y - 1.12), 9.0, 0.68,
                                 boxstyle="round,pad=0,rounding_size=0.12",
                                 fc="#F4F7F9", ec=HELLGRAU, lw=1.0, zorder=2))
    axB.text(1.16, y - 0.78, formel, fontsize=10.8, fontweight="bold", color=DUNKEL,
             va="center", zorder=3)
    axB.text(1.16, y - 1.46, fuss, fontsize=8.9, color=GRAU, va="center", style="italic")
    y -= 2.05

axB.add_patch(FancyBboxPatch((0.90, 0.20), 9.0, 0.88,
                             boxstyle="round,pad=0,rounding_size=0.14",
                             fc="#FFF6EC", ec=ORANGE, lw=1.6, zorder=2))
axB.text(1.16, 0.79, "Gegenprobe von Hand — Flüssigkeit ist inkompressibel, also w ≈ Δp / (ρ · η):",
         fontsize=8.9, color=GRAU, va="center", zorder=3, style="italic")
axB.text(1.16, 0.44, f"{de(dp/BAR,1)}·10⁵ Pa / ({de(rho1,0)} · {de(ETA_S,2)}) = "
                     f"{de(w_naeh,2)} kJ/kg     →  nur {de(abs(w_naeh-w)/w*100,1)} % Abweichung",
         fontsize=10.0, fontweight="bold", color=DUNKEL, va="center", zorder=3)

# ================================================== C  Leistungskette
titel(axC, "C  Von der Arbeit zur Maschine")

KETTE = [
    (f"{P_HYD:.0f} kW", "Nutzleistung am Fluid", "V̇ · Δp  —  verlustfrei", GRUEN),
    (f"{P_WELLE:.0f} kW", "Wellenleistung", f"÷ ηₛ = {de(ETA_S,2)}   ← Wert auf der Folie", BLAU),
    (f"{P_EL:.0f} kW", "elektrische Aufnahme", f"÷ η_Motor = {de(ETA_M,3)}", ORANGE),
    (f"{P_NENN:.0f} kW", "Motornenngröße", f"× {de(MARGE,2)} nach API 610, dann Normgröße", ROT),
]
y = 9.30
for wert, name, formel, farbe in KETTE:
    kasten(axC, 0.25, y - 1.34, 9.5, 1.40, "#FFFFFF", farbe, lw=1.9)
    axC.text(0.68, y - 0.44, wert, fontsize=15.5, fontweight="bold", color=farbe, va="center")
    axC.text(3.45, y - 0.30, name, fontsize=10.2, fontweight="bold", color=DUNKEL, va="center")
    axC.text(3.45, y - 0.82, formel, fontsize=8.7, color=GRAU, va="center")
    if farbe != ROT:
        axC.add_patch(FancyArrowPatch((5.0, y - 1.42), (5.0, y - 1.90),
                                      arrowstyle="-|>", mutation_scale=13,
                                      lw=1.7, color=HELLGRAU, zorder=4))
    y -= 2.00

axC.add_patch(FancyBboxPatch((0.25, 0.22), 9.5, 1.42,
                             boxstyle="round,pad=0,rounding_size=0.16",
                             fc="#F4F7F9", ec=HELLGRAU, lw=1.2, zorder=2))
axC.text(0.60, 1.35, "Auslegungspunkt für die Herstelleranfrage", fontsize=9.6,
         fontweight="bold", color=DUNKEL, va="center", zorder=3)
axC.text(0.60, 0.94, f"V̇ = {V_MIN:.0f} – {V_MAX:.0f} m³/h        H = {de(H_FOERDER,0)} m",
         fontsize=10.4, fontweight="bold", color=BLAU, va="center", zorder=3)
axC.text(0.60, 0.52, "Volumenstrom und Förderhöhe sind die\nAuswahlgrößen — nicht die Leistung",
         fontsize=8.4, color=GRAU, va="center", style="italic", zorder=3, linespacing=1.5)

# ----------------------------------------------------------- Fusszeilen
fig.text(0.032, 0.052,
         f"Randbedingungen: Anlieferung {P1:.0f} bar / {T1:.0f} °C · Bohrlochkopf {de(P2,1)} bar · "
         f"ηₛ = {de(ETA_S,2)} · η_Motor = {de(ETA_M,3)} · "
         f"50.000–100.000 Nm³/h = {de(M_MIN,1)}–{de(M_MAX,1)} kg/s",
         fontsize=8.6, color=GRAU)
fig.text(0.032, 0.022,
         "Stoffdaten CoolProp / Span & Wagner (1996) · eigene Rechnung · "
         "Blatt 03 der Obertageauslegung · Antriebsmarge nach API 610 / ISO 13709 (noch zu verifizieren)",
         fontsize=8, color="#7A7A7A")

fig.savefig("abb_rechenweg_pumpe.png", dpi=220)
print("gespeichert: abb_rechenweg_pumpe.png")
print(f"\n  h1  = {h1/1000:8.3f} kJ/kg   s1 = {s1/1000:.5f} kJ/(kg K)   rho1 = {rho1:.2f} kg/m3")
print(f"  h2s = {h2s/1000:8.3f} kJ/kg   ->  w_s = {w_s:.4f} kJ/kg")
print(f"  w   = {w:8.4f} kJ/kg   (Handrechnung {w_naeh:.4f}, {abs(w_naeh-w)/w*100:.2f} %)")
print(f"  T2  = {T2:8.2f} degC")
print(f"  Leistungskette: {P_HYD:.0f} -> {P_WELLE:.0f} -> {P_EL:.0f} -> Normmotor {P_NENN:.0f} kW")
print(f"  Betriebspunkt:  V = {V_MIN:.0f} - {V_MAX:.0f} m3/h, H = {H_FOERDER:.1f} m")
