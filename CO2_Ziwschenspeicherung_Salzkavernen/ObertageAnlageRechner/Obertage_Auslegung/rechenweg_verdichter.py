# -*- coding: utf-8 -*-
"""
Von Zustand 1 zu Zustand 2 - der Rechenweg der Verdichterauslegung (Szenario 2)
===============================================================================
Gegenstueck zu rechenweg_pumpe.py, aber fuer die gasfoermige Anlieferung.

  A  Was ist gegeben, was gesucht?   30 bar / 15 degC gasfoermig -> 107,6 bar
  B  Wieviele Stufen?                Arbeit und Austrittstemperatur ueber der Stufenzahl
  C  Warum bei 80 bar aufhoeren?     Uebergabe an die Pumpe statt dritter Stufe

Alle Zahlen live aus CoolProp (Span & Wagner 1996).
Aufruf: python rechenweg_verdichter.py
"""
import math

import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

F = "CO2"
BAR = 1e5
C2K = lambda t: t + 273.15
K2C = lambda t: t - 273.15
R_S = 8.314462618 / CP.PropsSI("M", F)

P1, T1 = 30.0, 15.0        # bar, degC  Anlieferung gasfoermig (Blatt 01)
P_UM = 80.0                # bar        Umschaltdruck auf die Pumpe
P2 = 107.6                 # bar        Bohrlochkopf
T_ZK = 40.0                # degC       Zwischenkuehlung (Annahme)
T_VERFL = 25.0             # degC       nach Verfluessiger (Annahme)
ETA_S = 0.80
R_MAX = 2.2                # -          max. Druckverhaeltnis je Stufe (Konvention)
Z_GRENZE = 0.65

BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
GRAU, HELLGRAU, HELLBLAU = "#4A4A4A", "#B8C4CC", "#68AFE1"


def de(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def h(p, T):
    return CP.PropsSI("H", "P", p * BAR, "T", C2K(T), F) / 1000.0


def rho(p, T):
    return CP.PropsSI("D", "P", p * BAR, "T", C2K(T), F)


def Z(p, T):
    return p * BAR / (rho(p, T) * R_S * C2K(T))


def stufe(p_ein, T_ein, p_aus):
    """-> (w [kJ/kg], T_aus [degC], T_aus isentrop [degC])"""
    h1 = CP.PropsSI("H", "P", p_ein * BAR, "T", C2K(T_ein), F)
    s1 = CP.PropsSI("S", "P", p_ein * BAR, "T", C2K(T_ein), F)
    h2s = CP.PropsSI("H", "P", p_aus * BAR, "S", s1, F)
    h2 = h1 + (h2s - h1) / ETA_S
    return ((h2 - h1) / 1000.0,
            K2C(CP.PropsSI("T", "P", p_aus * BAR, "H", h2, F)),
            K2C(CP.PropsSI("T", "P", p_aus * BAR, "S", s1, F)))


def kette(n, p_ein=P1, p_aus=P_UM, T_ein=T1):
    """n Stufen mit gleichem Druckverhaeltnis, Zwischenkuehlung auf T_ZK."""
    r = (p_aus / p_ein) ** (1.0 / n)
    w, q, T, p, T_max = 0.0, 0.0, T_ein, p_ein, -99.0
    for i in range(n):
        p_next = p * r
        dw, T_out, _ = stufe(p, T, p_next)
        w += dw
        T_max = max(T_max, T_out)
        if i < n - 1:
            q += h(p_next, T_out) - h(p_next, T_ZK)
            T = T_ZK
        else:
            T = T_out
        p = p_next
    return r, w, T_max, T, q


RHO_N = CP.PropsSI("D", "T", 273.15, "P", 101325.0, F)
M_DOT = RHO_N * 100_000.0 / 3600.0
M_MIN = RHO_N * 50_000.0 / 3600.0

N_REGEL = math.ceil(math.log(P_UM / P1) / math.log(R_MAX))
STUFEN = [1, 2, 3, 4, 5]
ERG = {n: kette(n) for n in STUFEN}
r2, w2, Tmax2, Tout2, q2 = ERG[2]

# Panel C: die letzten 28 bar
w_stufe3, T_st3, _ = stufe(P_UM, T_ZK, P2)                 # dritte Verdichterstufe
w_pumpe, T_pump, _ = stufe(P_UM, T_VERFL, P2)              # Pumpe nach Verfluessigung
q_extra = h(P_UM, T_ZK) - h(P_UM, T_VERFL)                 # Mehrkuehlung 40 -> 25 degC

# Kuehllast ueber die GANZE Kette, damit die Aussage nicht am Einzelschritt haengt.
# Pfad 2: Zwischenkuehler + Verfluessiger.  Pfad 3: zwei Zwischenkuehler + Nachkuehler 30 degC.
_r, _w2, _tmax, _tout2, q_zk = kette(2)
Q_PFAD2 = q_zk + (h(P_UM, _tout2) - h(P_UM, T_VERFL))
_p3 = [P1, 46.2, 71.0, P2]
Q_PFAD3, _T = 0.0, T1
for _i in range(3):
    _dw, _To, _ = stufe(_p3[_i], _T, _p3[_i + 1])
    Q_PFAD3 += h(_p3[_i + 1], _To) - h(_p3[_i + 1], T_ZK if _i < 2 else 30.0)
    _T = T_ZK

# ----------------------------------------------------------- Zeichnen
fig = plt.figure(figsize=(16.6, 6.9))
gs = fig.add_gridspec(1, 3, width_ratios=[1.00, 1.16, 1.06], wspace=0.24,
                      left=0.033, right=0.978, top=0.895, bottom=0.145)
axA, axB, axC = (fig.add_subplot(gs[0, i]) for i in range(3))


def titel(ax, txt):
    ax.set_title(txt, fontsize=12.5, fontweight="bold", color=DUNKEL, loc="left", pad=13)


def kasten(ax, x, y, w_, h_, fc, ec, lw=1.8):
    ax.add_patch(FancyBboxPatch((x, y), w_, h_,
                                boxstyle="round,pad=0,rounding_size=0.22",
                                fc=fc, ec=ec, lw=lw, zorder=2))


# ================================================== A
titel(axA, "A  Was ist gegeben, was gesucht?")
axA.set_xlim(0, 10); axA.set_ylim(0, 10); axA.axis("off")

kasten(axA, 0.25, 6.30, 9.5, 3.15, "#FDF0E3", ORANGE)
axA.text(0.72, 9.02, "ZUSTAND 1   Anlieferung gasförmig", fontsize=10.5,
         fontweight="bold", color=ORANGE, va="center")
axA.text(0.72, 8.38, f"{P1:.0f} bar   ·   {T1:.0f} °C   ·   Gas",
         fontsize=12.5, fontweight="bold", color=DUNKEL, va="center")
for i, (k, v) in enumerate([
        ("ρ₁", de(rho(P1, T1), 1) + " kg/m³"),
        ("Z₁", de(Z(P1, T1), 3) + "   → Turbogebiet"),
        ("p_sat", de(CP.PropsSI("P", "T", C2K(T1), "Q", 0, F) / BAR, 1) + " bar bei 15 °C")]):
    axA.text(0.95, 7.72 - i * 0.48, k, fontsize=9.6, color=GRAU, va="center")
    axA.text(2.45, 7.72 - i * 0.48, "=  " + v, fontsize=10.0, color=DUNKEL,
             fontweight="bold", va="center")

axA.text(0.30, 5.72, "30 bar liegt UNTER dem Siededruck → das CO₂ ist Gas.\n"
                     "Eine Pumpe ist hier nicht anwendbar.",
         fontsize=9.3, color=ORANGE, fontweight="bold", va="center", linespacing=1.6)

axA.add_patch(FancyArrowPatch((5.0, 5.15), (5.0, 4.30), arrowstyle="-|>",
                              mutation_scale=16, lw=2.2, color=ORANGE, zorder=4))
axA.text(5.38, 4.72, "VERDICHTER", fontsize=11, fontweight="bold", color=ORANGE, va="center")

kasten(axA, 0.25, 0.95, 9.5, 3.15, "#E8F1FA", BLAU)
axA.text(0.72, 3.68, "ZUSTAND 2   Bohrlochkopf", fontsize=10.5, fontweight="bold",
         color=BLAU, va="center")
axA.text(0.72, 3.04, f"{de(P2,1)} bar   ·   dicht", fontsize=12.5,
         fontweight="bold", color=DUNKEL, va="center")
axA.text(0.95, 2.32, "gesucht:", fontsize=9.6, color=ROT, va="center")
axA.text(2.45, 2.32, "Stufenzahl, Arbeit, Temperaturen", fontsize=10.0,
         color=ROT, fontweight="bold", va="center")
axA.text(0.95, 1.80, "und:", fontsize=9.6, color=ROT, va="center")
axA.text(2.45, 1.80, "wo hört der Verdichter auf?", fontsize=10.0,
         color=ROT, fontweight="bold", va="center")
axA.text(0.95, 1.30, "Ziel-ṁ:", fontsize=9.6, color=GRAU, va="center")
axA.text(2.45, 1.30, f"{de(M_MIN,1)} – {de(M_DOT,1)} kg/s", fontsize=10.0,
         color=DUNKEL, fontweight="bold", va="center")

axA.text(0.25, 0.35, "Dieselbe Enthalpiebilanz wie bei der Pumpe — nur wird sie\n"
                     "hier mehrfach angewendet, mit Kühlung dazwischen.",
         fontsize=9.4, color=DUNKEL, fontweight="bold", va="center", linespacing=1.65)

# ================================================== B
titel(axB, "B  Wieviele Stufen?")
xs = list(range(1, 6))
ws = [ERG[n][1] for n in xs]
tm = [ERG[n][2] for n in xs]
farben = [ORANGE if n != 2 else GRUEN for n in xs]
axB.bar(xs, ws, width=0.60, color=farben, edgecolor="white", lw=1.5, zorder=3)
for n, w_, t_ in zip(xs, ws, tm):
    lab = de(w_, 1) + ("   ← gewählt" if n == 2 else "")
    axB.text(n if n != 2 else n - 0.28, w_ + 0.55, lab,
             ha="center" if n != 2 else "left", fontsize=9.8, fontweight="bold",
             color=GRUEN if n == 2 else ORANGE, zorder=5)
axB.set_ylim(50, 64)
axB.set_xticks(xs)
axB.set_xlabel("Anzahl Verdichterstufen  (30 → 80 bar)", fontsize=9.8)
axB.set_ylabel("Wellenarbeit  [kJ/kg]", fontsize=9.8)
axB.spines[["top", "right"]].set_visible(False)
axB.tick_params(colors=GRAU, labelsize=9)
axB.grid(axis="y", color="#E4E9ED", lw=0.9)
axB.set_axisbelow(True)

axT = axB.twinx()
axT.plot(xs, tm, "o--", color=ROT, lw=1.8, ms=7, zorder=6)
for n, t_ in zip(xs, tm):
    axT.text(n + 0.16, t_ + 2.5, de(t_, 0) + " °C", fontsize=8.6, color=ROT, zorder=6)
axT.set_ylabel("höchste Austrittstemperatur  [°C]", fontsize=9.8, color=ROT)
axT.tick_params(colors=ROT, labelsize=9)
axT.set_ylim(40, 130)
axT.spines[["top", "left"]].set_visible(False)

axB.text(0.055, 0.975,
         f"Formale Regel im Code:   n = ⌈ ln(p₂/p₁) / ln(r_max) ⌉   mit r_max = {de(R_MAX,1)}\n"
         f"⌈ ln({P_UM:.0f}/{P1:.0f}) / ln({de(R_MAX,1)}) ⌉ = ⌈ {de(math.log(P_UM/P1)/math.log(R_MAX),2)} ⌉ = "
         f"{N_REGEL}  →  Druckverhältnis {de(r2,2)} je Stufe",
         transform=axB.transAxes, fontsize=8.7, color=DUNKEL, fontweight="bold",
         va="top", linespacing=1.75, zorder=8,
         bbox=dict(boxstyle="round,pad=0.36", fc="white", ec=HELLGRAU, lw=1.0, alpha=0.96))

# ================================================== C
titel(axC, "C  Warum bei 80 bar aufhören?")
axC.set_xlim(0, 10); axC.set_ylim(0, 10); axC.axis("off")

axC.text(0.20, 9.45, f"Nach Stufe 2 liegen {P_UM:.0f} bar an. Zwei Wege\n"
                     f"führen von dort auf {de(P2,1)} bar:",
         fontsize=9.4, color=GRAU, va="top", linespacing=1.65)

WEGE = [
    (f"{de(w_stufe3,1)} kJ/kg", "3. Verdichterstufe",
     f"kühlen auf {T_ZK:.0f} °C, dann verdichten\nρ = {de(rho(P_UM,T_ZK),0)} kg/m³ · Z = {de(Z(P_UM,T_ZK),2)}",
     ORANGE),
    (f"{de(w_pumpe,1)} kJ/kg", "Verflüssigen + Pumpe  ← gewählt",
     f"kühlen auf {T_VERFL:.0f} °C, dann pumpen\nρ = {de(rho(P_UM,T_VERFL),0)} kg/m³ · Z = {de(Z(P_UM,T_VERFL),2)}",
     GRUEN),
]
y = 8.10
for wert, name, sub, farbe in WEGE:
    kasten(axC, 0.20, y - 1.72, 9.6, 1.80, "#FFFFFF", farbe, lw=2.0)
    axC.text(0.62, y - 0.52, wert, fontsize=14.5, fontweight="bold", color=farbe, va="center")
    axC.text(3.85, y - 0.38, name, fontsize=9.6, fontweight="bold", color=DUNKEL, va="center")
    axC.text(3.85, y - 1.06, sub, fontsize=8.4, color=GRAU, va="center", linespacing=1.5)
    y -= 2.16

axC.add_patch(FancyBboxPatch((0.20, 2.72), 9.6, 1.36,
                             boxstyle="round,pad=0,rounding_size=0.14",
                             fc="#F4F7F9", ec=HELLGRAU, lw=1.1, zorder=2))
axC.text(0.55, 3.42, f"Faktor {de(w_stufe3/w_pumpe,1)} bei der Wellenarbeit. Die Verflüssigung kostet\n"
                     f"hier {de(q_extra,0)} kJ/kg mehr Kühlung — über die ganze Kette aber\n"
                     f"weniger als Pfad 3 ({de(Q_PFAD2,0)} gegen {de(Q_PFAD3,0)} kJ/kg).",
         fontsize=8.9, fontweight="bold", color=DUNKEL, va="center",
         linespacing=1.65, zorder=3)

axC.add_patch(FancyBboxPatch((0.20, 0.30), 9.6, 2.30,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#E8F1FA", ec=BLAU, lw=1.7, zorder=2))
axC.text(0.55, 2.20, "Q-047 · Siemens Energy White Paper (2024), S. 8",
         fontsize=8.9, fontweight="bold", color=BLAU, va="center", zorder=3)
axC.text(0.55, 1.38,
         "„…the IGC can be combined with a centrifugal pump\n"
         "(once the CO₂ is above the critical pressure) […] when the\n"
         "compressibility is typically too low and the density too high\n"
         "for a classical compressor stage.“",
         fontsize=8.7, color=DUNKEL, va="center", linespacing=1.7,
         style="italic", zorder=3)
axC.text(0.55, 0.55, f"{P_UM:.0f} bar liegt über p_krit = 73,8 bar.",
         fontsize=8.9, color=BLAU, fontweight="bold", va="center", zorder=3)

# ----------------------------------------------------------- Fuss
fig.text(0.033, 0.052,
         f"Randbedingungen: Anlieferung {P1:.0f} bar / {T1:.0f} °C gasförmig · Umschaltdruck {P_UM:.0f} bar · "
         f"Bohrlochkopf {de(P2,1)} bar · ηₛ = {de(ETA_S,2)} · Zwischenkühlung {T_ZK:.0f} °C · "
         f"Verflüssigung {T_VERFL:.0f} °C · 100.000 Nm³/h = {de(M_DOT,1)} kg/s",
         fontsize=8.5, color=GRAU)
fig.text(0.033, 0.022,
         "Stoffdaten CoolProp / Span & Wagner (1996) · eigene Rechnung · Blatt 05 der "
         "Obertageauslegung · r_max = 2,2 ist eine Auslegungskonvention, keine physikalische Grenze",
         fontsize=8, color="#7A7A7A")

fig.savefig("abb_rechenweg_verdichter.png", dpi=220)
print("gespeichert: abb_rechenweg_verdichter.png\n")
print(f"{'Stufen':>7}{'r':>8}{'w [kJ/kg]':>12}{'T max':>9}{'Zwischenk.':>12}")
for n in STUFEN:
    r, w_, tmax, tout, q = ERG[n]
    print(f"{n:>7}{r:>8.3f}{w_:>12.2f}{tmax:>8.1f} C{q:>10.1f}")
print(f"\nRegel: n = ceil(ln({P_UM:.0f}/{P1:.0f})/ln({R_MAX})) = {N_REGEL}")
print(f"Letzte {P2-P_UM:.1f} bar:  3. Stufe {w_stufe3:.2f} kJ/kg  gegen  Pumpe {w_pumpe:.2f} kJ/kg"
      f"  -> Faktor {w_stufe3/w_pumpe:.1f}")
print(f"Mehrkuehlung dafuer: {q_extra:.1f} kJ/kg = {q_extra*M_DOT/1000:.2f} MW")
