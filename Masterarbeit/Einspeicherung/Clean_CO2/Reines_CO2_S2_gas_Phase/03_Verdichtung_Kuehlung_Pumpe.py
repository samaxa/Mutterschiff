# -*- coding: utf-8 -*-
"""
Schritt 2 - Verdichtung, Verflüssigung, Pumpe: Netzübergabe -> Bohrlochkopf (Szenario 2, gasförmig)
============================================================================
Eingangszustand: 30 bar / 15 °C, unverändert aus Schritt 01_02 (gasförmig).
Gas lässt sich nicht pumpen, deshalb die Kette (wie Blatt "Einspeicherung S2"
der Excel-Mappe für reines CO₂, Annahmen nach Q-016):

  Basisfall   Verdichter (1 Stufe) -> Verflüssiger -> Pumpe
  Variante    Verdichter 1 -> Zwischenkühler -> Verdichter 2 -> Verflüssiger -> Pumpe
  Vergleich   Durchverdichten in 2 Stufen bis zum Kopfdruck (ohne Pumpe)

Zielzustand wie in Szenario 1: 107,60 bar am Bohrlochkopf, vorgegeben durch
die Kaverne (Gassäule von unten nach oben, gleicher Rechenweg wie in
Szenario 1 und in der Excel-Rechenübersicht).

Annahmen (Q-016 = Bielka et al. 2023, S. 4, Kap. 2.3; alle auch in der Excel):
  Kühlung            auf 20 °C nach jeder Stufe (setzt Kühlwasser voraus)
  Austritt           höchstens 95 °C je Verdichterstufe
  Verflüssigung      60 bar: Sättigungsdruck bei 20 °C ist 57,3 bar, darüber flüssig
  eta Verdichter     0,84 / 0,82 (erste Stufe 84 %, je weitere Stufe −2 %)
  eta Pumpe          0,80 (eigene Annahme wie in Szenario 1)
  Zwischendruck      Variante: √(30 · 60) = 42,4 bar (gleiches Druckverhältnis)
                     Durchverdichten: 50 bar (muss unter 57,3 bar bleiben, sonst
                     kondensiert das CO₂ schon im Zwischenkühler)
Frühere Annahmen der Vorarbeit (Zwischendruck 49 bar / 40 °C, Kühler 80 bar /
25 °C) sind damit ersetzt.

Hinweis Verflüssiger: 60 bar liegen unter p_krit (73,8 bar). Das CO₂ kondensiert
hier wirklich - bei 22,0 °C (Sättigungstemperatur bei 60 bar) - und wird danach
auf 20 °C unterkühlt. Der Abstand zur Sättigungslinie ist nur 2,7 bar bzw. 2,0 K
(Unsicherheit der Phasengrenze nach Doku: 3 bar). Welcher Weg durchs
Phasendiagramm robuster ist (z. B. überkritisch auf 91 bar verdichten und dann
kühlen), zeigt ../../Begleitstoffe_CO2/Prozesskette/04_phasenpfade_vergleich.py.

Rechenweg jeder Stufe wie in Szenario 1: isentrope Zustandsänderung
(h_s bei gleicher Entropie), mit Wirkungsgrad eta auf die reale
Enthalpieerhöhung skaliert. Kühler: abgeführte Wärme q = h_vor - h_nach.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI, PhaseSI

# ---- 1) Kaverne Version 1 - Randbedingungen (wie Szenario 1) ---------------
TEUFE = 1200.0  # m
P_MAX_LCCS = 210.0  # bar, Zieldruck am Kavernenboden
T_OBERFLAECHE = 10.0  # °C, Gebirge an der Oberfläche
GRADIENT = 0.03  # K/m, geothermischer Gradient
G = 9.81  # m/s2

# ---- 2) Zieldruck am Bohrlochkopf: Gassäule von unten nach oben -----------
# identisch zu Szenario 1 / 03_Pumpe_Verdichtung.py
T_KRIT_C = PropsSI("Tcrit", "CO2") - 273.15


def T_gebirge(z):
    return T_OBERFLAECHE + GRADIENT * z


def dichte(p_bar, T_c):
    """Dichte wie in der Gassäule: nahe der Siedelinie wird der Gasast gewählt."""
    T = T_c + 273.15
    p = p_bar * 1e5
    if T_c >= T_KRIT_C:
        return PropsSI("D", "P", p, "T", T, "CO2")
    psat = PropsSI("P", "T", T, "Q", 0, "CO2")
    if abs(p - psat) / psat < 5e-4:
        return PropsSI("D", "T", T, "Q", 1, "CO2")
    return PropsSI("D", "P", p, "T", T, "CO2")


def kopfdruck(p_lccs_bar, n=600):
    """Integriert dp/dz = rho(p,T)*g von der Teufe (LCCS) nach oben zum Kopf."""
    dz = TEUFE / n
    p = p_lccs_bar
    for i in range(n):
        z = TEUFE - i * dz
        p -= dichte(p, T_gebirge(z)) * G * dz / 1e5
    return p


p_kopf = kopfdruck(P_MAX_LCCS)
print(f"Zieldruck am Bohrlochkopf (Kaverne Version 1): {p_kopf:.2f} bar")

# ---- 3) Annahmen Szenario 2 (Q-016) ----------------------------------------
p_ein, T_ein = 30.0, 15.0   # bar, °C - Eingangszustand aus Schritt 01_02
T_K = 20.0                  # °C, Kühlung nach jeder Stufe
T_MAX = 95.0                # °C, höchstens je Verdichterstufe
p_V = 60.0                  # bar, Verflüssigungsdruck
p_zw_DV = 50.0              # bar, Zwischendruck Durchverdichten
eta_V1, eta_V2 = 0.84, 0.82     # Verdichter, Q-016
eta_P = 0.80                    # Pumpe, eigene Annahme

p_sat_TK = PropsSI("P", "T", T_K + 273.15, "Q", 0, "CO2") / 1e5
T_sat_pV = PropsSI("T", "P", p_V * 1e5, "Q", 0, "CO2") - 273.15


# ---- 4) Bausteine ----------------------------------------------------------
def H(p_bar, T_C):
    return PropsSI("H", "P", p_bar * 1e5, "T", T_C + 273.15, "CO2") / 1000   # kJ/kg


def stufe(p1_bar, T1_C, p2_bar, eta):
    """Eine Verdichter- oder Pumpenstufe: isentrop + Wirkungsgrad."""
    h1 = H(p1_bar, T1_C)
    s1 = PropsSI("S", "P", p1_bar * 1e5, "T", T1_C + 273.15, "CO2")
    h2s = PropsSI("H", "P", p2_bar * 1e5, "S", s1, "CO2") / 1000   # isentrop: gleiche Entropie
    h2 = h1 + (h2s - h1) / eta                                     # mit Wirkungsgradverlust
    T2 = PropsSI("T", "P", p2_bar * 1e5, "H", h2 * 1000, "CO2") - 273.15
    phase2 = PhaseSI("P", p2_bar * 1e5, "H", h2 * 1000, "CO2")
    return dict(h1=h1, h2s=h2s, h2=h2, T2=T2, phase2=phase2, w=h2 - h1)


def pruef(bedingung):
    return "✔" if bedingung else "✘"


# ---- 5) Basisfall: 1 Stufe -> Verflüssiger -> Pumpe --------------------------
V = stufe(p_ein, T_ein, p_V, eta_V1)
h_VF = H(p_V, T_K)
q_VF = V["h2"] - h_VF
phase_VF = PhaseSI("P", p_V * 1e5, "T", T_K + 273.15, "CO2")
P = stufe(p_V, T_K, p_kopf, eta_P)
w_basis = V["w"] + P["w"]

print("\nSzenario 2 - Basisfall (1 Verdichterstufe):")
print(f"  Verdichter:     {p_ein:.0f} -> {p_V:.0f} bar, {T_ein:.0f} -> {V['T2']:.1f} °C "
      f"{pruef(V['T2'] <= T_MAX)} (≤ {T_MAX:.0f} °C),  w = {V['w']:.2f} kJ/kg")
print(f"  Verflüssiger:   {V['T2']:.1f} -> {T_K:.0f} °C bei {p_V:.0f} bar, Kondensation bei {T_sat_pV:.1f} °C,"
      f"  q = {q_VF:.2f} kJ/kg  ({phase_VF})")
print(f"                  Abstand zur Sättigungslinie {p_V - p_sat_TK:.2f} bar {pruef(p_V - p_sat_TK >= 3)} (≥ 3 bar), "
      f"Unterkühlung {T_sat_pV - T_K:.1f} K")
print(f"  Pumpe:          {p_V:.0f} -> {p_kopf:.2f} bar, {T_K:.0f} -> {P['T2']:.2f} °C,  w = {P['w']:.2f} kJ/kg")
print(f"  Summe Arbeit:   {w_basis:.2f} kJ/kg,  Wärme: {q_VF:.2f} kJ/kg")

# ---- 6) Variante: 2 Stufen mit Zwischenkühlung -------------------------------
p_zw = np.sqrt(p_ein * p_V)
V1 = stufe(p_ein, T_ein, p_zw, eta_V1)
q_ZK = V1["h2"] - H(p_zw, T_K)
V2 = stufe(p_zw, T_K, p_V, eta_V2)
q_VF2 = V2["h2"] - h_VF
w_var = V1["w"] + V2["w"] + P["w"]

print(f"\nVariante - 2 Verdichterstufen (Zwischendruck {p_zw:.1f} bar):")
print(f"  Stufe 1: {V1['T2']:.1f} °C, w = {V1['w']:.2f} kJ/kg | Zwischenkühler q = {q_ZK:.2f} kJ/kg "
      f"(gasförmig: {p_zw:.1f} < {p_sat_TK:.1f} bar {pruef(p_zw <= p_sat_TK - 3)})")
print(f"  Stufe 2: {V2['T2']:.1f} °C, w = {V2['w']:.2f} kJ/kg | Verflüssiger q = {q_VF2:.2f} kJ/kg")
print(f"  Summe Arbeit:   {w_var:.2f} kJ/kg ({1 - w_var / w_basis:.0%} weniger als 1 Stufe)")

# ---- Durchsatz, Leistung, Kühlleistung -------------------------------------
V_NORM_MIN, V_NORM_MAX = 50000.0, 100000.0  # Nm3/h
rho_n = PropsSI("D", "P", 101325, "T", 273.15, "CO2")
m_min, m_max = V_NORM_MIN * rho_n / 3600.0, V_NORM_MAX * rho_n / 3600.0   # kg/s
print(f"\n  Durchsatz: {V_NORM_MIN:.0f}-{V_NORM_MAX:.0f} Nm3/h -> {m_min:.1f}-{m_max:.1f} kg/s")
print(f"  Antriebsleistung Basisfall: {m_min * w_basis:.0f}-{m_max * w_basis:.0f} kW, "
      f"Variante: {m_min * w_var:.0f}-{m_max * w_var:.0f} kW")
print(f"  Kühlleistung Verflüssiger (Basisfall): {m_min * q_VF:.0f}-{m_max * q_VF:.0f} kW")

# ---- 7) Vergleich: Durchverdichten (2 Stufen, ohne Pumpe) ------------------
# Gleicher Eintritt, Zwischenkühlung auf 20 °C, am Ende Nachkühler auf denselben
# Endzustand wie der Basisfall (107,60 bar, Temperatur nach Pumpe) - fairer Vergleich
D1 = stufe(p_ein, T_ein, p_zw_DV, eta_V1)
D2 = stufe(p_zw_DV, T_K, p_kopf, eta_V2)
T_D_end = P["T2"]
q_D = (D1["h2"] - H(p_zw_DV, T_K)) + (D2["h2"] - H(p_kopf, T_D_end))
w_D = D1["w"] + D2["w"]

print(f"\nVergleich Durchverdichten (2 Stufen, Zwischendruck {p_zw_DV:.0f} bar):")
for i, D in enumerate([D1, D2], 1):
    print(f"  Stufe {i}: T_aus {D['T2']:.1f} °C {pruef(D['T2'] <= T_MAX)}, w = {D['w']:.2f} kJ/kg")
print(f"  Summe Arbeit: {w_D:.2f} kJ/kg,  Summe Wärme: {q_D:.2f} kJ/kg")
print(f"\n  -> Verflüssigen und Pumpen braucht {1 - w_basis / w_D:.0%} (Basisfall) bzw. "
      f"{1 - w_var / w_D:.0%} (Variante) weniger Arbeit als Durchverdichten.")

# Szenario 1 nur als Vergleichsbalken im Diagramm (Pumpe 91 bar / 15 °C -> Kopf)
S1 = stufe(91.0, 15.0, p_kopf, eta_P)
print(f"  Zum Vergleich S1 (nur Pumpe): {S1['w']:.2f} kJ/kg")

# ---- 8) Diagramm 1: p-T mit den Pfaden -------------------------------------
# Wie Diagramm 1 im Blatt "Phasendiagramm" der Excel
T_krit = PropsSI("Tcrit", "CO2")
p_krit = PropsSI("Pcrit", "CO2")
T_tripel = PropsSI("Ttriple", "CO2")
p_tripel = PropsSI("ptriple", "CO2")
T_krit_C, T_tripel_C = T_krit - 273.15, T_tripel - 273.15
p_krit_bar, p_tripel_bar = p_krit / 1e5, p_tripel / 1e5

T_saett = np.linspace(T_tripel, T_krit, 200)
p_saett_bar = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_saett]) / 1e5
T_saett_C = T_saett - 273.15


def sublimation_bar(T_K_):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K_ / T_tripel
    return p_tripel_bar * np.exp((T_tripel / T_K_) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K_):
    x = T_K_ / T_tripel - 1.0
    return p_tripel_bar * (1.0 + 1955.5390 * x + 2055.4593 * x**2)


Tmin, Tmax = -80.0, 110.0
Pmin, Pmax = 0.0, 130.0
T_sub = np.linspace(Tmin + 273.15, T_tripel, 150)
p_sub_bar, T_sub_C = sublimation_bar(T_sub), T_sub - 273.15
T_melt = np.linspace(T_tripel, T_tripel * 1.02, 100)
p_melt_bar, T_melt_C = schmelz_bar(T_melt), T_melt - 273.15

C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, ROT = "#5F2176", "#CA220E"
GRUEN, BLAU, HELLBLAU, VIOLETT = "#007335", "#0476D9", "#68AFE1", "#7030A0"

fig, ax = plt.subplots(figsize=(10, 6.5))

gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, p_krit_bar), (T_krit_C, p_krit_bar)]
gas += list(zip(T_saett_C[::-1], p_saett_bar[::-1])) + list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))
fest = [(Tmin, Pmax), (T_melt_C[-1], p_melt_bar[-1])] + list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
fest += list(zip(T_sub_C[::-1], p_sub_bar[::-1]))
ax.add_patch(plt.Polygon(fest, closed=True, fc=C_FEST, ec="none", zorder=0))
flue = list(zip(T_saett_C, p_saett_bar)) + [(T_krit_C, Pmax), (T_melt_C[-1], Pmax)]
flue += list(zip(T_melt_C[::-1], p_melt_bar[::-1]))
ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))
ax.add_patch(plt.Rectangle((T_krit_C, p_krit_bar), Tmax - T_krit_C, Pmax - p_krit_bar,
                           fc=C_SUP, ec="none", zorder=0))

ax.plot(T_sub_C, p_sub_bar, color="#333333", lw=1.5, zorder=3, label="Sublimationslinie")
ax.plot(T_saett_C, p_saett_bar, color="#00304F", lw=1.8, zorder=3, label="Sättigungslinie")
ax.plot(T_melt_C, p_melt_bar, color=COL_FEST, lw=1.5, zorder=3, label="Schmelzlinie")
ax.plot(T_tripel_C, p_tripel_bar, "o", color="black", ms=5, zorder=5)
ax.plot(T_krit_C, p_krit_bar, "o", color=ROT, ms=8, zorder=5)

# Pfade: Punkte (T, p) in der Reihenfolge der Kette
pfad_S1 = [(15.0, 91.0), (S1["T2"], p_kopf)]
pfad_basis = [(T_ein, p_ein), (V["T2"], p_V), (T_K, p_V), (P["T2"], p_kopf)]
pfad_var = [(T_ein, p_ein), (V1["T2"], p_zw), (T_K, p_zw), (V2["T2"], p_V)]
pfad_D = [(T_ein, p_ein), (D1["T2"], p_zw_DV), (T_K, p_zw_DV), (D2["T2"], p_kopf), (T_D_end, p_kopf)]

ax.plot(*zip(*pfad_S1), "-D", color=GRUEN, lw=2.5, ms=6, zorder=6, label="S1: Pumpe")
ax.plot(*zip(*pfad_basis), "-o", color=BLAU, lw=2.2, ms=6, zorder=7,
        label="S2: verdichten → verflüssigen → pumpen")
ax.plot(*zip(*pfad_var), ":o", color=HELLBLAU, lw=2.0, ms=4, zorder=7, label="S2-Variante: 2 Verdichterstufen")
ax.plot(*zip(*pfad_D), "--o", color=VIOLETT, lw=1.5, ms=4, zorder=6, label="Vergleich: Durchverdichten (2 Stufen)")

txt = dict(fontsize=8, weight="bold", color="#404040", ha="center", va="center", zorder=8)
ax.text(T_ein, p_ein - 5, "S2 Netzübergabe", **txt)
ax.text(V["T2"] + 6, p_V + 4, "Verdichter 1 Stufe", **txt)
ax.text(T_K - 14, p_V, "Verflüssiger", **txt)
ax.text(T_K - 12, p_zw + 1, "Zwischenkühler", **txt)
ax.text((S1["T2"] + P["T2"]) / 2, p_kopf + 6, f"Bohrlochkopf {p_kopf:.1f} bar".replace(".", ","), **txt)
ax.text(-3, 91, "S1 Netzübergabe", **txt)
ax.text(D2["T2"] + 8, p_kopf - 4, "Stufe 2", **txt)

big = dict(fontsize=12, weight="bold", color="#404040", ha="center", va="center", zorder=2)
ax.text(-71, 70, "fest", **big)
ax.text(-30, 105, "flüssig", **big)
ax.text(72, 12, "gasförmig", **big)
ax.text(85, 120, "überkritisch", **big)

ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("Einspeicherung reines CO₂: Prozesspfade S1, S2 und Vergleich Durchverdichten", fontsize=11)
ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.set_xticks(np.arange(Tmin, Tmax + 1, 20))
ax.set_yticks(np.arange(Pmin, Pmax + 1, 10))
ax.grid(color="white", lw=0.5, zorder=1)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig("abb_verdichtung_S2.png", dpi=160)
print("\ngespeichert: abb_verdichtung_S2.png")

# ---- 9) Diagramm 2: spezifische Arbeit, gestapelte Balken ------------------
# Wie das Balkendiagramm im Blatt "Einspeicherung S2" der Excel
wege = ["S1 dichte Phase", "S2 Basisfall:\n1 Stufe + Pumpe", "S2 Variante:\n2 Stufen + Pumpe",
        "Vergleich:\nDurchverdichten"]
anteile = [("Verdichter 1. Stufe", [0.0, V["w"], V1["w"], D1["w"]], "#EE7203"),
           ("Verdichter 2. Stufe", [0.0, 0.0, V2["w"], D2["w"]], "#F4B183"),
           ("Pumpe", [S1["w"], P["w"], P["w"], 0.0], GRUEN)]

fig2, ax2 = plt.subplots(figsize=(8.5, 4.6))
links = np.zeros(len(wege))
for name, werte, farbe in anteile:
    werte = np.array(werte)
    bars = ax2.barh(wege, werte, left=links, color=farbe, label=name, height=0.55)
    for b, v in zip(bars, werte):
        if v > 3:
            ax2.text(b.get_x() + b.get_width() / 2, b.get_y() + b.get_height() / 2,
                     f"{v:.1f}".replace(".", ","), ha="center", va="center", fontsize=8)
    links += werte
for y, summe in enumerate(links):
    ax2.text(summe + 1, y, f"{summe:.2f} kJ/kg".replace(".", ","), va="center", fontsize=9, weight="bold")

ax2.invert_yaxis()
ax2.set_xlim(0, max(links) * 1.2)
ax2.set_xlabel("spezifische Arbeit [kJ/kg]")
ax2.set_title("Spezifische Arbeit bis zum Bohrlochkopf (reines CO₂)", fontsize=11)
ax2.grid(axis="x", alpha=0.3)
ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=8, frameon=False)
fig2.text(0.5, 0.01, f"Verflüssigen und Pumpen braucht {1 - w_basis / w_D:.0%} weniger Arbeit als "
          f"Durchverdichten, mit 2 Stufen {1 - w_var / w_D:.0%}.", ha="center", fontsize=8.5, color=GRUEN,
          weight="bold")
fig2.tight_layout(rect=[0, 0.04, 1, 1])
fig2.savefig("abb_vergleich_arbeit_S2.png", dpi=160)
print("gespeichert: abb_vergleich_arbeit_S2.png")
