# -*- coding: utf-8 -*-
"""
Schritt 4 - Gassäule im Bohrloch (Szenario 1, dichte Phase)
============================================================================
Dieselbe Rechnung, die in 03_pumpe.py als Hilfsfunktion den Zieldruck der
Pumpe geliefert hat - hier als eigener, sichtbarer Schritt mit drei
Betriebspunkten, analog zu Buzogany & Kruck (2022, Q-028), Figur 3:

  "voll"       pLCCS = 210 bar  (Kaverne Version 1: p_max)
  "Grenzfall"  pLCCS, bei der der Kopfdruck genau den kritischen Druck
               erreicht (Sekantenverfahren) - Grenze zwischen "kein
               Phasenwechsel im Bohrloch" und "Phasenwechsel im Bohrloch"
  "leer"       pLCCS = 70 bar   (Kaverne Version 1: p_min_geomech)

Unterschied zur Quelle: dort 1150 m LCCS-Teufe (Validierungsfall), hier
1200 m (Kaverne Version 1, siehe Dokumentation_S1_dichte_Phase.docx).

NUR STILLSTAND: Die Säulen gelten für ruhendes CO2 mit Gebirgstemperatur und
für die drei Füllstände nach Q-028. Was Injektion und Ausspeicherung für das
Fenster bedeuten (Reibungsdruckverlust im Strang, Wärmeaustausch mit dem
Gebirge, Erwärmung bzw. Abkühlung in der Kaverne, Drosselung beim
Ausspeichern), ist hier nicht dargestellt.

Hinweis Nassdampfgebiet: beim leeren Fall (70 bar) liegt der Druck von
0 bis ca. 236 m fast exakt auf der Sättigungslinie. Dort ist die Dichte durch
(p, T) allein nicht bestimmt - das Modell kippt sonst bei praktisch jedem
Gitterpunkt zwischen Gas- (~135 kg/m3) und Flüssigkeitsast (~850 kg/m3),
auch bei feiner Auflösung (n=600). Kein Rechenfehler, sondern eine echte
Modellgrenze der statischen Säule (kein Dampfanteil als Zustandsgröße) -
deshalb wird dieser Bereich in der Dichtekurve nicht gerechnet dargestellt,
sondern geradlinig überbrückt.

Abbildungen (gleich aufgebaut wie in der Excel-Rechenübersicht):
  abb_gassaeule.png                  Blatt "Kaverne & Gassäule", drei Felder
  abb_betriebsfenster_stillstand.png Blatt "Phasendiagramm", Diagramm 2
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

# ---- 1) Kaverne Version 1 - Randbedingungen --------------------------------
TEUFE = 1200.0
T_OBERFLAECHE = 10.0
GRADIENT = 0.03
P_MAX = 210.0            # bar
P_MIN_GEOMECH = 70.0     # bar
G = 9.81
T_KRIT_C = PropsSI("Tcrit", "CO2") - 273.15
P_KRIT_BAR = PropsSI("Pcrit", "CO2") / 1e5

# ---- 2) Grundfunktionen -----------------------------------------------------
def T_gebirge(z):
    return T_OBERFLAECHE + GRADIENT * z


def dichte(p_bar, T_c):
    """Dichte mit expliziter Phasenwahl nahe der Siedelinie (siehe Hinweis oben)."""
    T = T_c + 273.15
    p = p_bar * 1e5
    if T_c >= T_KRIT_C:
        return PropsSI("D", "P", p, "T", T, "CO2")
    psat = PropsSI("P", "T", T, "Q", 0, "CO2")
    if abs(p - psat) / psat < 5e-4:          # praktisch auf der Siedelinie
        return PropsSI("D", "T", T, "Q", 1, "CO2")
    return PropsSI("D", "P", p, "T", T, "CO2")


def saeule_aufwaerts(p_lccs, n=600):
    """Integriert dp/dz = rho*g von der Teufe (LCCS) nach oben zum Kopf.

    Rückgabe von oben nach unten sortiert: (z, T, p, rho) je Stützstelle.
    """
    dz = TEUFE / n
    p = p_lccs
    out = []
    for i in range(n + 1):
        z = TEUFE - i * dz
        T = T_gebirge(z)
        rho = dichte(p, T)
        out.append((z, T, p, rho))
        if i < n:
            p -= rho * G * dz / 1e5
    return out[::-1]


def sekante(f, x0, x1, tol=1e-4, maxit=30):
    f0, f1 = f(x0), f(x1)
    for _ in range(maxit):
        if abs(f1) < tol:
            return x1
        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        x0, f0, x1, f1 = x1, f1, x2, f(x2)
    return x1


# ---- 3) Grenzfall: Kopfdruck = kritischer Druck ----------------------------
# Gleiche Schrittzahl (600) wie bei den eigentlichen Säulen, sonst landet der
# Kopf nicht genau auf p_krit. Startwerte liegen nahe an der Lösung.
f_grenz = lambda pl: saeule_aufwaerts(pl, 600)[0][2] - P_KRIT_BAR
p_lccs_grenz = sekante(f_grenz, 160.0, 180.0, tol=1e-6)

FAELLE = [
    ("voll (pLCCS = 210 bar)", P_MAX),
    (f"Grenzfall (pLCCS = {p_lccs_grenz:.1f} bar)".replace(".", ","), p_lccs_grenz),
    ("leer (pLCCS = 70 bar)", P_MIN_GEOMECH),
]

print("Gassäule, Kaverne Version 1 (1200 m, Gebirge 10 °C + 0,03 K/m):")
ergebnisse = []
for lbl, pl in FAELLE:
    rows = saeule_aufwaerts(pl, 600)
    kopf = rows[0]
    print(f"  {lbl:32s} -> Kopf {kopf[2]:6.1f} bar / {kopf[1]:5.1f} °C"
          f" | rho oben {kopf[3]:6.1f}, unten {rows[-1][3]:6.1f} kg/m3")
    ergebnisse.append((lbl, rows))

print("\nKontrolle gegen Schritt 2: Kopfdruck bei voller Kaverne sollte 107,60 bar sein"
      f" -> {ergebnisse[0][1][0][2]:.2f} bar")


# ---- Nassdampf-Erkennung ----------------------------------------------------
# Nahe der Sättigungslinie (|p - p_sat(T)| < 0.3 %) ist die Dichte durch (p, T)
# nicht mehr eindeutig bestimmt - ein statisches Säulenmodell (kein Dampfanteil
# als Zustandsgröße) kann dort willkürlich zwischen Gas- und Flüssigkeitsast
# springen. Diese Punkte werden für die Dichtekurve ausgeblendet statt falsch
# als glatte Linie gezeichnet.
def nassdampf_maske(rows, tol=0.003):
    maske = []
    for z, T, p, rho in rows:
        if T >= T_KRIT_C:
            maske.append(False)
            continue
        psat = PropsSI("P", "T", T + 273.15, "Q", 0, "CO2") / 1e5
        maske.append(abs(p - psat) / psat < tol)
    return maske


for lbl, rows in ergebnisse:
    m = nassdampf_maske(rows)
    if any(m):
        tiefen = [r[0] for r, mm in zip(rows, m) if mm]
        print(f"  Nassdampfgebiet bei '{lbl}': {min(tiefen):.0f}-{max(tiefen):.0f} m"
              " (Dichte dort nicht durch p,T bestimmt)")

# ---- 4) Drei-Felder-Diagramm, wie Buzogany & Kruck (2022) Fig. 3 -----------
fig, axs = plt.subplots(1, 3, figsize=(12.5, 6.5), sharey=True)
z_achse = [r[0] for r in ergebnisse[0][1]]

axs[0].plot([r[1] for r in ergebnisse[0][1]], z_achse, color="#333333", lw=2)
axs[0].set_title("Geologisches\nTemperaturprofil [°C]")
axs[0].axvline(T_KRIT_C, color="#CA220E", ls="--", lw=1.1)
axs[0].text(T_KRIT_C + 1, TEUFE * 0.05, f"T_krit {T_KRIT_C:.0f} °C", fontsize=8.5, color="#CA220E")

# Linien wie in der Excel: voll grün durchgezogen, Grenzfall blau gestrichelt,
# leer orange gepunktet
stile = [("-", "#007335"), ("--", "#0476D9"), (":", "#EE7203")]
nd_bereich = None
nd_rho_bereich = None
for (lbl, rows), (ls, col) in zip(ergebnisse, stile):
    zz = [r[0] for r in rows]
    maske = nassdampf_maske(rows)
    axs[1].plot([r[2] for r in rows], zz, ls=ls, color=col, lw=2, label=lbl)

    # Im Nassdampfgebiet keine echte Dichte gezeichnet, sondern eine gerade
    # Verbindung zwischen den Werten davor/danach - damit die Linie sichtbar
    # bleibt, ohne die unbestimmten (oszillierenden) Zwischenwerte zu zeigen.
    rho_plot = [r[3] for r in rows]
    if any(maske):
        idx = [i for i, mm in enumerate(maske) if mm]
        i0, i1 = max(idx[0] - 1, 0), min(idx[-1] + 1, len(rho_plot) - 1)
        for i in range(i0 + 1, i1):
            frac = (zz[i] - zz[i0]) / (zz[i1] - zz[i0])
            rho_plot[i] = rho_plot[i0] + frac * (rho_plot[i1] - rho_plot[i0])
        tiefen = [zz[i] for i in idx]
        nd_bereich = (min(tiefen), max(tiefen))
        nd_rho_bereich = (rho_plot[i0], rho_plot[i1])
    axs[2].plot(rho_plot, zz, ls=ls, color=col, lw=2, label=lbl)

if nd_bereich:
    x_pfeil = sum(nd_rho_bereich) / 2   # an der Linie selbst, nicht an der Achse
    axs[2].annotate("", xy=(x_pfeil, nd_bereich[1]), xytext=(x_pfeil, nd_bereich[0]),
                     arrowprops=dict(arrowstyle="<->", color="#555555", lw=1.1))
    axs[2].text(x_pfeil + 55, (nd_bereich[0] + nd_bereich[1]) / 2,
                "mehrphasen\nGebiet", fontsize=7.5, color="#555555", va="center")

axs[1].axvline(P_KRIT_BAR, color="#888", ls=":", lw=1.2)
axs[1].text(P_KRIT_BAR + 3, TEUFE * 0.75, f"p_krit {P_KRIT_BAR:.1f} bar".replace(".", ","), fontsize=8.5,
            color="#666", rotation=90, va="center")

for a, t in zip(axs[1:], ["Druck [bar]", "Dichte [kg/m³]"]):
    a.set_title(t)
    a.legend(fontsize=7.8, loc="lower left")

axs[0].set_ylabel("Teufe z [m]")
axs[0].set_ylim(TEUFE * 1.05, 0)
axs[0].set_xlim(0, 60)          # Achsen wie in der Excel
axs[1].set_xlim(0, 250)
axs[2].set_xlim(0, 1000)
for a in axs:
    a.grid(alpha=0.3)

fig.suptitle("Gassäule Kaverne Version 1 (1200 m) - Temperatur, Druck, Dichte\n"
             "Darstellung nach Buzogany & Kruck (2022), Fig. 3 (dort: 1150 m)",
             fontsize=11)
fig.text(0.5, 0.01, "NUR STILLSTAND: ruhendes CO₂ mit Gebirgstemperatur, drei Füllstände nach Q-028. "
         "Injektion und Ausspeicherung sind hier nicht dargestellt.",
         ha="center", fontsize=8.5, color="#9C0006", weight="bold")
fig.tight_layout(rect=[0, 0.03, 1, 0.93])
fig.savefig("abb_gassaeule.png", dpi=160)
print("\ngespeichert: abb_gassaeule.png")


# ---- 5) Betriebsfenster im Stillstand, p-T-Diagramm -------------------------
# Wie Diagramm 2 im Blatt "Phasendiagramm" der Excel: jede Gassäule ist eine
# Linie vom Bohrlochkopf (0 m, 10 °C) bis zur Kaverne (1200 m, 46 °C). Das
# Band zwischen "voll" und "leer" ist das Betriebsfenster im Stillstand.
T_TRIPEL = PropsSI("Ttriple", "CO2")
P_TRIPEL_BAR = PropsSI("ptriple", "CO2") / 1e5
T_TRIPEL_C = T_TRIPEL - 273.15
TMIN, TMAX, PMIN, PMAX = -80.0, 100.0, 0.0, 250.0


def sublimation_bar(T_K):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / T_TRIPEL
    return P_TRIPEL_BAR * np.exp((T_TRIPEL / T_K) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K):
    x = T_K / T_TRIPEL - 1.0
    return P_TRIPEL_BAR * (1.0 + 1955.5390 * x + 2055.4593 * x**2)


T_saett = np.linspace(T_TRIPEL, T_KRIT_C + 273.15, 200)
p_saett = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_saett]) / 1e5
T_saett_C = T_saett - 273.15
T_sub = np.linspace(TMIN + 273.15, T_TRIPEL, 150)
p_sub, T_sub_C = sublimation_bar(T_sub), T_sub - 273.15
# Schmelzlinie bis zum oberen Diagrammrand (PMAX)
x_top = (-1955.5390 + np.sqrt(1955.5390**2 + 4 * 2055.4593 * (PMAX / P_TRIPEL_BAR - 1))) / (2 * 2055.4593)
T_melt = np.linspace(T_TRIPEL, T_TRIPEL * (1 + x_top), 50)
p_melt, T_melt_C = schmelz_bar(T_melt), T_melt - 273.15

C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
NAVY = "#00304F"

fig2, ax = plt.subplots(figsize=(10, 6.5))
gas = [(TMIN, PMIN), (TMAX, PMIN), (TMAX, P_KRIT_BAR), (T_KRIT_C, P_KRIT_BAR)]
gas += list(zip(T_saett_C[::-1], p_saett[::-1])) + list(zip(T_sub_C[::-1], p_sub[::-1]))
ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))
fest = [(TMIN, PMAX), (T_melt_C[-1], PMAX)] + list(zip(T_melt_C[::-1], p_melt[::-1]))
fest += list(zip(T_sub_C[::-1], p_sub[::-1]))
ax.add_patch(plt.Polygon(fest, closed=True, fc=C_FEST, ec="none", zorder=0))
flue = list(zip(T_saett_C, p_saett)) + [(T_KRIT_C, PMAX), (T_melt_C[-1], PMAX)]
flue += list(zip(T_melt_C[::-1], p_melt[::-1]))
ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))
ax.add_patch(plt.Rectangle((T_KRIT_C, P_KRIT_BAR), TMAX - T_KRIT_C, PMAX - P_KRIT_BAR,
                           fc=C_SUP, ec="none", zorder=0))

ax.plot(T_sub_C, p_sub, color="#333333", lw=1.5, zorder=3, label="Sublimationslinie")
ax.plot(T_saett_C, p_saett, color="#1F4E79", lw=1.75, zorder=3, label="Sättigungslinie")
ax.plot(T_melt_C, p_melt, color="#5F2176", lw=1.5, zorder=3, label="Schmelzlinie")
ax.plot(T_TRIPEL_C, P_TRIPEL_BAR, "o", color="black", ms=5, zorder=5, label="Tripelpunkt")
ax.plot(T_KRIT_C, P_KRIT_BAR, "o", color="#CA220E", ms=7, zorder=5, label="Kritischer Punkt")

# Gassäulen: x = Temperatur, y = Druck, je Stützstelle eine Teufe
stile_pT = [("--", NAVY, 2.0), ((0, (8, 4)), "#2E75B6", 1.5), (":", NAVY, 2.0)]
namen_pT = ["Gassäule Kaverne voll (210 bar unten)", "Gassäule Grenzfall (Kopf = p_krit)",
            "Gassäule Kaverne leer (70 bar unten)"]
for (lbl, rows), (ls, col, lw), nm in zip(ergebnisse, stile_pT, namen_pT):
    ax.plot([r[1] for r in rows], [r[2] for r in rows], ls=ls, color=col, lw=lw, zorder=4, label=nm)

T_KAV = T_gebirge(TEUFE)
kopf_voll, kopf_leer = ergebnisse[0][1][0][2], ergebnisse[2][1][0][2]
ax.plot([T_KAV, T_KAV], [P_MIN_GEOMECH, P_MAX], color=NAVY, lw=5, zorder=4,
        label=f"Kaverne V1 (LCCS, {TEUFE:.0f} m): {P_MIN_GEOMECH:.0f}–{P_MAX:.0f} bar")
ax.plot([T_OBERFLAECHE, T_OBERFLAECHE], [kopf_leer, kopf_voll], color="#7F7F7F", lw=5, zorder=4,
        label=f"Bohrlochkopf (0 m): {kopf_leer:.0f}–{kopf_voll:.1f} bar".replace(".", ","))

txt = dict(fontsize=8, weight="bold", color=NAVY, va="center", zorder=6)
# rechts neben dem Kavernen-Balken
ax.text(T_KAV + 2.5, P_MAX, f"Kaverne voll {P_MAX:.0f} bar", ha="left", **txt)
ax.text(T_KAV + 2.5, p_lccs_grenz, f"Grenzfall {p_lccs_grenz:.1f} bar".replace(".", ","), ha="left", **txt)
ax.text(T_KAV + 2.5, P_MIN_GEOMECH, f"Kaverne leer {P_MIN_GEOMECH:.0f} bar", ha="left", **txt)
# links neben dem Kopf-Balken
ax.text(T_OBERFLAECHE - 2.5, kopf_voll, f"Kopf {kopf_voll:.1f} bar".replace(".", ","), ha="right", **txt)
ax.text(T_OBERFLAECHE - 2.5, P_KRIT_BAR, f"Kopf {P_KRIT_BAR:.1f} bar = p_krit".replace(".", ","), ha="right", **txt)
ax.text(T_OBERFLAECHE - 2.5, kopf_leer + 3, f"Kopf {kopf_leer:.0f} bar = p_sat({T_OBERFLAECHE:.0f} °C)", ha="right", **txt)
ax.text(29, 100, "Betriebsfenster", ha="center", **txt)

big = dict(fontsize=12, weight="bold", color="#404040", ha="center", va="center", zorder=6)
ax.text(-71, 150, "fest", **big)
ax.text(-12, 170, "flüssig", **big)
ax.text(78, 25, "gasförmig", **big)
ax.text(78, 160, "überkritisch", **big)

ax.set_xlim(TMIN, TMAX)
ax.set_ylim(PMIN, PMAX)
ax.set_xticks(np.arange(TMIN, TMAX + 1, 20))
ax.set_yticks(np.arange(PMIN, PMAX + 1, 25))
ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("NUR STILLSTAND – Bohrloch und Kaverne V1: Gassäulen für voll, Grenzfall und leer\n"
             "(nach Q-028, Fig. 3)", fontsize=11, color=NAVY, weight="bold")
ax.grid(color="white", lw=0.5, zorder=1)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig2.text(0.01, 0.01, "Injektion und Ausspeicherung (Reibung, Wärmeaustausch, Erwärmung/Abkühlung in der Kaverne, "
          "Drosselung) sind hier nicht dargestellt.", fontsize=8, color="#9C0006", weight="bold")
fig2.tight_layout(rect=[0, 0.03, 1, 1])
fig2.savefig("abb_betriebsfenster_stillstand.png", dpi=160)
print("gespeichert: abb_betriebsfenster_stillstand.png")
