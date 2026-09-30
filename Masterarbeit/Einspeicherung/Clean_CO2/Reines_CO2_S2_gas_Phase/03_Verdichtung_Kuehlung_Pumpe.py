# -*- coding: utf-8 -*-
"""
Schritt 2 - Verdichtung, Kühlung, Pumpe: Netzübergabe -> Bohrlochkopf (Szenario 2, gasförmig)
============================================================================
Eingangszustand: 30 bar / 15 °C, unverändert aus Schritt 01_02 (gasförmig).
Gas lässt sich nicht pumpen, deshalb die Kette

  Verdichter 1 -> Zwischenkühler -> Verdichter 2 -> Kühler ("Verflüssiger") -> Pumpe

Zielzustand wie in Szenario 1: 107,60 bar am Bohrlochkopf, vorgegeben durch
die Kaverne (Gassäule von unten nach oben, gleicher Rechenweg wie in
Szenario 1 und in der Excel-Rechenübersicht).

Annahmen (alle in der Excel auf der Übersicht):
  Zwischendruck      49 bar  - ca. Wurzel(30 * 80): gleiches Druckverhältnis
                               in beiden Stufen (übliche Auslegungsregel)
  Zwischenkühler     40 °C   - Annahme aus Vorarbeit (Kühlwasser), zu prüfen
  Kühler             80 bar / 25 °C - Annahme aus Vorarbeit, zu prüfen
  eta Verdichter     0,84 / 0,82 - Q-016 (Bielka et al. 2023, S. 4, Kap. 2.3):
                               erste Stufe 84 %, je weitere Stufe -2 %
  eta Pumpe          0,80    - eigene Annahme wie in Szenario 1

Hinweis "Verflüssiger": 80 bar liegen über p_krit (73,8 bar). Es gibt also
keine echte Kondensation - das CO2 wird beim Abkühlen stetig dichter, am
stärksten um die pseudokritische Temperatur (cp-Maximum, bei 80 bar ca. 35 °C).
Genauer wäre "Kühler auf dichte Phase".

Rechenweg jeder Stufe wie in Szenario 1: isentrope Zustandsänderung
(h_s bei gleicher Entropie), mit Wirkungsgrad eta auf die reale
Enthalpieerhöhung skaliert. Kühler: abgeführte Wärme q = h_vor - h_nach.

Zum Vergleich wird am Ende das "Durchverdichten" gerechnet: drei
Verdichterstufen direkt bis 107,60 bar, ohne Pumpe (Block "Vergleich:
Durchverdichten" im Blatt "Einspeicherung S2" der Excel).
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

# ---- 3) Annahmen Szenario 2 ------------------------------------------------
p_ein, T_ein = 30.0, 15.0   # bar, °C - Eingangszustand aus Schritt 01_02
p_zw = 49.0                 # bar, Zwischendruck
T_ZK = 40.0                 # °C, nach Zwischenkühler
p_kuehl, T_kuehl = 80.0, 25.0   # bar, °C - nach Kühler ("Verflüssiger")
eta_V1, eta_V2 = 0.84, 0.82     # Verdichter, Q-016
eta_V3 = 0.80                   # nur für den Vergleich Durchverdichten, Q-016
eta_P = 0.80                    # Pumpe, eigene Annahme


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


# ---- 5) Kette Szenario 2 ---------------------------------------------------
V1 = stufe(p_ein, T_ein, p_zw, eta_V1)
h_ZK = H(p_zw, T_ZK)
q_ZK = V1["h2"] - h_ZK

V2 = stufe(p_zw, T_ZK, p_kuehl, eta_V2)
h_K = H(p_kuehl, T_kuehl)
q_K = V2["h2"] - h_K
phase_K = PhaseSI("P", p_kuehl * 1e5, "T", T_kuehl + 273.15, "CO2")

P = stufe(p_kuehl, T_kuehl, p_kopf, eta_P)

w_ges = V1["w"] + V2["w"] + P["w"]
q_ges = q_ZK + q_K

print("\nSzenario 2 - Kette:")
print(f"  Verdichter 1:   {p_ein:.0f} -> {p_zw:.0f} bar, {T_ein:.0f} -> {V1['T2']:.1f} °C,"
      f"  w = {V1['w']:.2f} kJ/kg  ({V1['phase2']})")
print(f"  Zwischenkühler: {V1['T2']:.1f} -> {T_ZK:.0f} °C,  q = {q_ZK:.2f} kJ/kg")
print(f"  Verdichter 2:   {p_zw:.0f} -> {p_kuehl:.0f} bar, {T_ZK:.0f} -> {V2['T2']:.1f} °C,"
      f"  w = {V2['w']:.2f} kJ/kg  ({V2['phase2']})")
print(f"  Kühler:         {V2['T2']:.1f} -> {T_kuehl:.0f} °C,  q = {q_K:.2f} kJ/kg  ({phase_K})")
print(f"  Pumpe:          {p_kuehl:.0f} -> {p_kopf:.2f} bar, {T_kuehl:.0f} -> {P['T2']:.2f} °C,"
      f"  w = {P['w']:.2f} kJ/kg  ({P['phase2']})")
print(f"  Summe Arbeit:   {w_ges:.2f} kJ/kg,  Summe Wärme: {q_ges:.2f} kJ/kg")

# ---- Durchsatz, Leistung, Kühlleistung -------------------------------------
# Bandbreite wie in Szenario 1: 50.000-100.000 Nm3/h (0 °C, 1,01325 bar)
V_NORM_MIN, V_NORM_MAX = 50000.0, 100000.0  # Nm3/h
rho_n = PropsSI("D", "P", 101325, "T", 273.15, "CO2")
m_min, m_max = V_NORM_MIN * rho_n / 3600.0, V_NORM_MAX * rho_n / 3600.0   # kg/s

print(f"\n  Durchsatz: {V_NORM_MIN:.0f}-{V_NORM_MAX:.0f} Nm3/h -> {m_min:.1f}-{m_max:.1f} kg/s")
print(f"  Antriebsleistung gesamt: {m_min * w_ges:.0f}-{m_max * w_ges:.0f} kW")
print(f"  Kühlleistung gesamt:     {m_min * q_ges:.0f}-{m_max * q_ges:.0f} kW")

# ---- 6) Vergleich: Durchverdichten (3 Stufen, ohne Pumpe) ------------------
# Gleicher Eintritt, gleiches Druckverhältnis in allen drei Stufen,
# Zwischenkühlung auf 40 °C wie oben. Am Ende kühlt ein Nachkühler auf
# denselben Endzustand wie Szenario 2 (107,60 bar, Temperatur nach Pumpe) -
# nur so ist der Vergleich fair.
r = (p_kopf / p_ein) ** (1 / 3)
p_D = [p_ein, p_ein * r, p_ein * r**2, p_kopf]

D1 = stufe(p_D[0], T_ein, p_D[1], eta_V1)
D2 = stufe(p_D[1], T_ZK, p_D[2], eta_V2)
D3 = stufe(p_D[2], T_ZK, p_D[3], eta_V3)
T_D_end = P["T2"]
q_D = (D1["h2"] - H(p_D[1], T_ZK)) + (D2["h2"] - H(p_D[2], T_ZK)) + (D3["h2"] - H(p_kopf, T_D_end))
w_D = D1["w"] + D2["w"] + D3["w"]

print("\nVergleich Durchverdichten (3 Stufen):")
print(f"  Druckverhältnis je Stufe: {r:.3f} -> {p_D[1]:.1f} / {p_D[2]:.1f} / {p_D[3]:.1f} bar")
for i, D in enumerate([D1, D2, D3], 1):
    print(f"  Stufe {i}: T_aus {D['T2']:.1f} °C, w = {D['w']:.2f} kJ/kg")
print(f"  Summe Arbeit: {w_D:.2f} kJ/kg,  Summe Wärme: {q_D:.2f} kJ/kg")
print(f"\n  -> Kühlen und Pumpen (S2) braucht {1 - w_ges / w_D:.0%} weniger Arbeit als Durchverdichten,"
      f" bei fast gleicher Wärme ({q_ges:.0f} zu {q_D:.0f} kJ/kg).")

# Szenario 1 nur als Vergleichsbalken im Diagramm (Pumpe 91 bar / 15 °C -> Kopf)
S1 = stufe(91.0, 15.0, p_kopf, eta_P)
print(f"  Zum Vergleich S1 (nur Pumpe): {S1['w']:.2f} kJ/kg")

# ---- 7) Diagramm 1: p-T mit den Pfaden -------------------------------------
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


def sublimation_bar(T_K):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / T_tripel
    return p_tripel_bar * np.exp((T_tripel / T_K) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K):
    x = T_K / T_tripel - 1.0
    return p_tripel_bar * (1.0 + 1955.5390 * x + 2055.4593 * x**2)


Tmin, Tmax = -80.0, 100.0
Pmin, Pmax = 0.0, 130.0
T_sub = np.linspace(Tmin + 273.15, T_tripel, 150)
p_sub_bar, T_sub_C = sublimation_bar(T_sub), T_sub - 273.15
T_melt = np.linspace(T_tripel, T_tripel * 1.02, 100)
p_melt_bar, T_melt_C = schmelz_bar(T_melt), T_melt - 273.15

C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, COL_GAS, COL_FLUE, COL_SUP, ROT = "#5F2176", "#164a73", "#007335", "#a3480b", "#CA220E"
GRUEN, BLAU, VIOLETT = "#007335", "#0476D9", "#7030A0"

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
pfad_S2 = [(T_ein, p_ein), (V1["T2"], p_zw), (T_ZK, p_zw), (V2["T2"], p_kuehl),
           (T_kuehl, p_kuehl), (P["T2"], p_kopf)]
pfad_D = [(T_ein, p_ein), (D1["T2"], p_D[1]), (T_ZK, p_D[1]), (D2["T2"], p_D[2]),
          (T_ZK, p_D[2]), (D3["T2"], p_kopf), (T_D_end, p_kopf)]

ax.plot(*zip(*pfad_S1), "-D", color=GRUEN, lw=2.5, ms=6, zorder=6, label="S1: Pumpe")
ax.plot(*zip(*pfad_S2), "-o", color=BLAU, lw=2.2, ms=6, zorder=7,
        label="S2: verdichten → kühlen → verflüssigen → pumpen")
ax.plot(*zip(*pfad_D), "--o", color=VIOLETT, lw=1.5, ms=4, zorder=6, label="Vergleich: Durchverdichten (3 Stufen)")

txt = dict(fontsize=8, weight="bold", color="#404040", ha="center", va="center", zorder=8)
ax.text(T_ein, p_ein - 5, "S2 Netzübergabe", **txt)
ax.text(V1["T2"] + 8, p_zw + 3, "Verdichter 1", **txt)
ax.text(T_ZK - 10, p_zw + 4, "Zwischenkühler", **txt)
ax.text(V2["T2"] + 6, p_kuehl + 4, "Verdichter 2", **txt)
ax.text(T_kuehl - 14, p_kuehl, "Verflüssiger", **txt)
ax.text((S1["T2"] + P["T2"]) / 2, p_kopf + 6, f"Bohrlochkopf {p_kopf:.1f} bar".replace(".", ","), **txt)
ax.text(-3, 91, "S1 Netzübergabe", **txt)
ax.text(D2["T2"] + 9, p_D[2], "Stufe 2", **txt)
ax.text(D3["T2"] + 9, p_kopf - 4, "Stufe 3", **txt)

big = dict(fontsize=12, weight="bold", color="#404040", ha="center", va="center", zorder=2)
ax.text(-71, 70, "fest", **big)
ax.text(-30, 105, "flüssig", **big)
ax.text(72, 12, "gasförmig", **big)
ax.text(85, 120, "überkritisch", **big)

ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("Einspeicherung: Prozesspfade S1, S2 und Vergleich Durchverdichten (bis Bohrlochkopf)",
             fontsize=11)
ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.set_xticks(np.arange(Tmin, Tmax + 1, 20))
ax.set_yticks(np.arange(Pmin, Pmax + 1, 10))
ax.grid(color="white", lw=0.5, zorder=1)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig("abb_verdichtung_S2.png", dpi=160)
print("\ngespeichert: abb_verdichtung_S2.png")

# ---- 8) Diagramm 2: spezifische Arbeit, gestapelte Balken ------------------
# Wie das Balkendiagramm im Blatt "Einspeicherung S2" der Excel
wege = ["S1 dichte Phase", "S2: 2 Stufen +\nKühler + Pumpe", "Vergleich:\nDurchverdichten"]
anteile = [("Verdichter 1. Stufe", [0.0, V1["w"], D1["w"]], "#EE7203"),
           ("Verdichter 2. Stufe", [0.0, V2["w"], D2["w"]], "#F4B183"),
           ("Verdichter 3. Stufe", [0.0, 0.0, D3["w"]], "#C55A11"),
           ("Pumpe", [S1["w"], P["w"], 0.0], GRUEN)]

fig2, ax2 = plt.subplots(figsize=(8.5, 4.2))
links = np.zeros(3)
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
ax2.set_title("Spezifische Arbeit bis zum Bohrlochkopf", fontsize=11)
ax2.grid(axis="x", alpha=0.3)
ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4, fontsize=8, frameon=False)
fig2.text(0.5, 0.01, f"S2 braucht {1 - w_ges / w_D:.0%} weniger Arbeit als Durchverdichten "
          f"- bei fast gleicher abzuführender Wärme ({q_ges:.0f} zu {q_D:.0f} kJ/kg).",
          ha="center", fontsize=8.5, color=GRUEN, weight="bold")
fig2.tight_layout(rect=[0, 0.04, 1, 1])
fig2.savefig("abb_vergleich_arbeit_S2.png", dpi=160)
print("gespeichert: abb_vergleich_arbeit_S2.png")
