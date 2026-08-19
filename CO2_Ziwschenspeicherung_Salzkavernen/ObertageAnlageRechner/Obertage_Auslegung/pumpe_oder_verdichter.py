# -*- coding: utf-8 -*-
"""
Ab wann lohnt sich eine Pumpe? — Visualisierung der Maschinenwahl
==================================================================
Die Frage "Pumpe oder Verdichter" entscheidet sich nicht an einer Meinung,
sondern an der Dichte des angelieferten CO2. Diese hängt allein davon ab,
auf welcher Seite der Siedelinie der Anlieferzustand liegt.

Drei Teilbilder:
  A  Wo liegt die Grenze?      p-T-Karte mit Siedelinie und Betriebspunkten
  B  Warum liegt sie dort?     Dichtesprung am Siededruck
  C  Was kostet das?           spezifische Wellenarbeit bis zum Bohrlochkopf

Stoffdaten: CoolProp (Span & Wagner 1996). Aufruf: python pumpe_oder_verdichter.py
"""
import numpy as np
import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ----------------------------------------------------------- Randbedingungen
F = "CO2"
BAR = 1e5
C2K = lambda t: t + 273.15
K2C = lambda t: t - 273.15

T_ANL = 15.0        # °C, Anliefertemperatur (Annahme, Blatt 01)
P_ZIEL = 107.6      # bar, Bohrlochkopfdruck (Modul 1_auslegung)
ETA = 0.80          # -, isentroper Wirkungsgrad
T_ZK = 40.0         # °C, Zwischenkühlung
T_VERFL = 25.0      # °C, Zustand nach Verflüssiger
P_VERFL = 80.0      # bar, Ende der Verdichtung in Szenario G
R_MAX = 2.2         # -, maximales Druckverhältnis je Stufe
VN = 100_000.0      # Nm³/h
RHO_N = CP.PropsSI("D", "T", 273.15, "P", 101325.0, F)
M_DOT = RHO_N * VN / 3600.0

TC = K2C(CP.PropsSI("Tcrit", F))
PC = CP.PropsSI("pcrit", F) / BAR
P_SAT = CP.PropsSI("P", "T", C2K(T_ANL), "Q", 0, F) / BAR

# Uniper-Palette
BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"


def h(p, T):
    return CP.PropsSI("H", "P", p * BAR, "T", C2K(T), F) / 1000.0


def rho(p, T):
    return CP.PropsSI("D", "P", p * BAR, "T", C2K(T), F)


def druckerhoehung(p1, T1, p2):
    """Isentrope Druckerhöhung mit Wirkungsgrad -> (w [kJ/kg], T2 [°C])"""
    h1 = CP.PropsSI("H", "P", p1 * BAR, "T", C2K(T1), F)
    s1 = CP.PropsSI("S", "P", p1 * BAR, "T", C2K(T1), F)
    h2s = CP.PropsSI("H", "P", p2 * BAR, "S", s1, F)
    h2 = h1 + (h2s - h1) / ETA
    return (h2 - h1) / 1000.0, K2C(CP.PropsSI("T", "P", p2 * BAR, "H", h2, F))


def verdichterkette(p1, T1, p2):
    """Mehrstufig mit Zwischenkühlung auf T_ZK. -> (w gesamt [kJ/kg], Stufenzahl)"""
    n = max(1, int(np.ceil(np.log(p2 / p1) / np.log(R_MAX))))
    r = (p2 / p1) ** (1.0 / n)
    w, T, p = 0.0, T1, p1
    for i in range(n):
        p_next = p * r
        dw, T = druckerhoehung(p, T, p_next)
        w += dw
        p = p_next
        if i < n - 1:
            T = T_ZK
    return w, n


def route_gas(p1):
    """Anlieferung gasförmig: verdichten auf 80 bar, verflüssigen, pumpen."""
    w_v, n = verdichterkette(p1, T_ANL, P_VERFL)
    w_p, _ = druckerhoehung(P_VERFL, T_VERFL, P_ZIEL)
    return w_v + w_p, n


def route_pumpe(p1):
    """Anlieferung flüssig/dicht: direkt pumpen."""
    w, _ = druckerhoehung(p1, T_ANL, P_ZIEL)
    return w


# ----------------------------------------------------------- Rechnen
p_gas = np.linspace(5.0, P_SAT - 0.15, 90)
p_fl = np.linspace(P_SAT + 0.15, 100.0, 90)

w_gas = np.array([route_gas(p)[0] for p in p_gas])
w_fl = np.array([route_pumpe(p) for p in p_fl])
rho_gas = np.array([rho(p, T_ANL) for p in p_gas])
rho_fl = np.array([rho(p, T_ANL) for p in p_fl])

w_D = route_pumpe(85.0)
w_G = route_gas(30.0)[0]

# ----------------------------------------------------------- Zeichnen
fig, (axA, axB, axC) = plt.subplots(1, 3, figsize=(16.4, 5.4))
for ax in (axA, axB, axC):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors="#4A4A4A", labelsize=9)

# ---- A: p-T-Karte
T_line = np.linspace(-20.0, TC, 400)
p_line = np.array([CP.PropsSI("P", "T", C2K(t), "Q", 0, F) / BAR for t in T_line])
axA.fill_between(T_line, p_line, 130, color=GRUEN, alpha=0.10)
axA.fill_between([TC, 45], [PC, PC], [130, 130], color=GRUEN, alpha=0.10)
axA.fill_between(T_line, 0, p_line, color=ORANGE, alpha=0.12)
axA.fill_between([TC, 45], 0, [PC, PC], color=ORANGE, alpha=0.12)
axA.plot(T_line, p_line, color=DUNKEL, lw=2.0)
axA.plot([TC], [PC], "o", color=ROT, ms=8, zorder=5)
axA.annotate("kritischer Punkt\n31,0 °C / 73,8 bar", (TC, PC), (34, 96),
             fontsize=8.5, color=ROT, ha="center",
             arrowprops=dict(arrowstyle="->", color=ROT, lw=1))
axA.text(-18, 118, "PUMPE möglich\nflüssig / dicht", fontsize=11, fontweight="bold",
         color=GRUEN, va="center")
axA.text(31, 20, "VERDICHTER nötig\ngasförmig", fontsize=11, fontweight="bold",
         color=ORANGE, va="center", ha="center")
axA.plot([85], [85 * 0 + 85], marker="")
axA.plot(15, 85, "o", color=BLAU, ms=10, zorder=6)
axA.annotate("Szenario D\n85 bar / 15 °C", (15, 85), (-8, 96), fontsize=9,
             color=BLAU, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=BLAU, lw=1.2))
axA.plot(15, 30, "o", color=ORANGE, ms=10, zorder=6)
axA.annotate("Szenario G\n30 bar / 15 °C", (15, 30), (-10, 16), fontsize=9,
             color=ORANGE, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.2))
axA.axhline(P_SAT, color=DUNKEL, ls=":", lw=1.2)
axA.text(-19, P_SAT + 2.5, f"Siededruck bei 15 °C: {P_SAT:.1f} bar",
         fontsize=8.5, color=DUNKEL)
axA.set_xlim(-20, 45)
axA.set_ylim(0, 130)
axA.set_xlabel("Temperatur [°C]", fontsize=10)
axA.set_ylabel("Druck [bar]", fontsize=10)
axA.set_title("A  Wo liegt die Grenze?", fontsize=12, fontweight="bold",
              color=DUNKEL, loc="left", pad=12)

# ---- B: Dichtesprung
axB.plot(p_gas, rho_gas, color=ORANGE, lw=2.4, label="gasförmig")
axB.plot(p_fl, rho_fl, color=GRUEN, lw=2.4, label="flüssig / dicht")
axB.plot([P_SAT, P_SAT], [rho_gas[-1], rho_fl[0]], color=DUNKEL, ls="--", lw=1.6)
axB.axvline(P_SAT, color=DUNKEL, ls=":", lw=1.0, alpha=0.6)
axB.annotate(f"Sprung von {rho_gas[-1]:.0f} auf {rho_fl[0]:.0f} kg/m³\nam Siededruck",
             (P_SAT, (rho_gas[-1] + rho_fl[0]) / 2), (12, 560), fontsize=9.5,
             color=DUNKEL, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=DUNKEL, lw=1.2))
axB.plot(30, rho(30, T_ANL), "o", color=ORANGE, ms=9)
axB.plot(85, rho(85, T_ANL), "o", color=BLAU, ms=9)
axB.text(86, rho(85, T_ANL) - 55, f"D: {rho(85, T_ANL):.0f} kg/m³",
         fontsize=9, color=BLAU, fontweight="bold", ha="right")
axB.text(31, rho(30, T_ANL) + 45, f"G: {rho(30, T_ANL):.0f} kg/m³",
         fontsize=9, color=ORANGE, fontweight="bold")
axB.set_xlim(0, 100)
axB.set_ylim(0, 950)
axB.set_xlabel("Anlieferdruck bei 15 °C [bar]", fontsize=10)
axB.set_ylabel("Dichte [kg/m³]", fontsize=10)
axB.set_title("B  Warum liegt sie dort?", fontsize=12, fontweight="bold",
              color=DUNKEL, loc="left", pad=12)
axB.legend(frameon=False, fontsize=9, loc="upper left")

# ---- C: Wellenarbeit
axC.semilogy(p_gas, w_gas, color=ORANGE, lw=2.4,
             label="verdichten → verflüssigen → pumpen")
axC.semilogy(p_fl, w_fl, color=GRUEN, lw=2.4, label="nur pumpen")
axC.axvline(P_SAT, color=DUNKEL, ls=":", lw=1.0, alpha=0.6)
axC.plot(30, w_G, "o", color=ORANGE, ms=9, zorder=5)
axC.plot(85, w_D, "o", color=BLAU, ms=9, zorder=5)
axC.annotate(f"Szenario G\n{w_G:.1f} kJ/kg\n{w_G * M_DOT / 1000:.1f} MW",
             (30, w_G), (5, 6.0), fontsize=9, color=ORANGE, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.2))
axC.annotate(f"Szenario D\n{w_D:.2f} kJ/kg\n{w_D * M_DOT:.0f} kW",
             (85, w_D), (60, 33), fontsize=9, color=BLAU, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=BLAU, lw=1.2))
axC.text(3, 1.7, f"ab {P_SAT:.1f} bar ist die Pumpe\nüberhaupt erst anwendbar",
         fontsize=9.5, color=GRUEN, fontweight="bold", va="top")
axC.set_xlim(0, 100)
axC.set_ylim(1, 600)
axC.set_xlabel("Anlieferdruck bei 15 °C [bar]", fontsize=10)
axC.set_ylabel(f"Wellenarbeit bis {P_ZIEL:.1f} bar [kJ/kg]", fontsize=10)
axC.set_title("C  Was kostet das?", fontsize=12, fontweight="bold",
              color=DUNKEL, loc="left", pad=12)
axC.legend(frameon=False, fontsize=9, loc="upper right")

fig.text(0.008, 0.028,
         f"Randbedingungen: Anliefertemperatur {T_ANL:.0f} °C · Zielzustand {P_ZIEL} bar am Bohrlochkopf · "
         f"η_s = {ETA} · Zwischenkühlung {T_ZK:.0f} °C · Verflüssigung bei {P_VERFL:.0f} bar / {T_VERFL:.0f} °C · "
         f"{VN:,.0f} Nm³/h = {M_DOT:.1f} kg/s".replace(",", "."),
         fontsize=8.5, color="#4A4A4A")
fig.text(0.008, 0.005,
         "Stoffdaten CoolProp / Span & Wagner (1996) · eigene Rechnung · Annahmen aus CO2_Obertageauslegung.xlsx, Blatt 01",
         fontsize=8, color="#7A7A7A")
fig.tight_layout(rect=[0, 0.065, 1, 0.99])
fig.savefig("abb_pumpe_oder_verdichter.png", dpi=170)
print("gespeichert: abb_pumpe_oder_verdichter.png")

print(f"\nSiededruck bei {T_ANL:.0f} °C: {P_SAT:.2f} bar")
print(f"Dichte knapp darunter {rho_gas[-1]:.1f} kg/m3, knapp darüber {rho_fl[0]:.1f} kg/m3")
print(f"Szenario D (85 bar): {w_D:.2f} kJ/kg = {w_D * M_DOT:.0f} kW")
print(f"Szenario G (30 bar): {w_G:.2f} kJ/kg = {w_G * M_DOT / 1000:.2f} MW  "
      f"({verdichterkette(30.0, T_ANL, P_VERFL)[1]} Verdichterstufen)")
print(f"Verhältnis: Faktor {w_G / w_D:.1f}")
