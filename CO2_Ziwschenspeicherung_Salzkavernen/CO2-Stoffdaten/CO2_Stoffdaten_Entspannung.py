"""
CO2-Stoffdaten fuer die Salzkavernen-Speicherung
====================================================

Auswertung der isenthalpen Entspannung (Ausspeicherung) von CO2 sowie
- zum Stoffvergleich - von Methan (CH4) und Wasserstoff (H2).

Die Entspannungspfade sind ECHTE Daten aus
    Quellen- und Wissensmatrix.xlsx
    Blatt "Isenthalpe_Entspannung_Gase"
(isenthalpe / Joule-Thomson-Entspannung, Start 210 bar / 50 °C,
h = konstant, herunter bis 30 bar).

Phasengrenzen und Stoffdaten werden LOKAL mit CoolProp gerechnet
(Zustandsgleichungen, z. B. Span-Wagner fuer CO2) - nichts online.

Pro Gas wird EIN eigenstaendiges Bild erzeugt:
    links   p-T-Phasendiagramm des jeweiligen Gases + Entspannungspfad
    rechts  p-h-Diagramm (Mollier) desselben Gases + Entspannungspfad

So sieht man je Gas, durch welche Phasen die isenthalpe Entspannung laeuft.

Die urspruengliche Datei CO2_Stoffdaten.py bleibt unveraendert.
Ausfuehren mit Python 3.10 (dort ist CoolProp installiert):

    py -3.10 CO2_Stoffdaten_Entspannung.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.ticker import ScalarFormatter
from CoolProp.CoolProp import PropsSI


# ============================================================
# 0) Globale Einstellungen
# ============================================================

SAVE_PNG = True


# ============================================================
# 1) ECHTE Entspannungsdaten aus der Wissensmatrix
# ============================================================
#
# Quelle: Quellen- und Wissensmatrix.xlsx,
#         Blatt "Isenthalpe_Entspannung_Gase"
# Isenthalpe (Joule-Thomson) Entspannung, h = konstant,
# Start jeweils 210 bar / 50 °C, herunter bis 30 bar.
#
# Pro Gas zusaetzlich hinterlegt:
#   fluid       CoolProp-Name
#   isotherms_C Isothermen, die im p-h-Diagramm gezeichnet werden
#   range       (Tmin, Tmax, Pmin, Pmax) fuer das p-T-Phasendiagramm

EXPANSION = {
    "CO2": {
        "fluid": "CO2",
        "label": "CO2",
        "color": "#c43c39",
        "marker": "o",
        "range": (-100.0, 60.0, 0.1, 250.0),
        "isotherms_C": [-50, -30, -10, 0, 10, 20, 31, 40, 50, 60],
        "P_bar": [210, 200, 190, 180, 170, 160, 150, 140, 130, 120,
                  110, 100, 90, 80, 70, 60, 50, 40, 30],
        "T_C": [50.0, 49.299, 48.537, 47.707, 46.801, 45.809, 44.72,
                43.518, 42.185, 40.697, 39.021, 37.113, 34.9, 32.26,
                28.683, 21.978, 14.284, 5.3, -5.552],
    },
    "CH4": {
        "fluid": "CH4",
        "label": "CH4",
        "color": "#1a7a3a",
        "marker": "s",
        "range": (-190.0, 60.0, 0.08, 250.0),
        "isotherms_C": [-160, -120, -83, -60, -40, -20, 0, 20, 50],
        "P_bar": [210, 200, 190, 180, 170, 160, 150, 140, 130, 120,
                  110, 100, 90, 80, 70, 60, 50, 40, 30],
        "T_C": [50.0, 48.489, 46.858, 45.099, 43.203, 41.159, 38.956,
                36.584, 34.028, 31.278, 28.32, 25.14, 21.725, 18.063,
                14.14, 9.945, 5.468, 0.701, -4.361],
    },
    "H2": {
        "fluid": "Hydrogen",
        "label": "H2",
        "color": "#3b5bdb",
        "marker": "^",
        "range": (-262.0, 70.0, 0.05, 250.0),
        "isotherms_C": [-240, -200, -120, -50, 0, 50, 100],
        "P_bar": [210, 200, 190, 180, 170, 160, 150, 140, 130, 120,
                  110, 100, 90, 80, 70, 60, 50, 40, 30],
        "T_C": [50.0, 50.557, 50.98, 51.4, 51.817, 52.23, 52.64,
                53.046, 53.449, 53.848, 54.243, 54.635, 55.022, 55.406,
                55.786, 56.162, 56.535, 56.903, 57.269],
    },
}

# Welche Gase sollen geplottet werden?
GASES = ["CO2", "CH4", "H2"]


# ============================================================
# 2) Hilfsfunktionen fuer Stoffdaten ueber CoolProp
# ============================================================

def safe_propssi(output, name1, val1, name2, val2, fluid):
    """PropsSI-Aufruf, der bei Fehlern np.nan zurueckgibt."""
    try:
        return PropsSI(output, name1, val1, name2, val2, fluid)
    except Exception:
        return np.nan


def enthalpy_kJ(T_C, P_bar, fluid):
    """Spezifische Enthalpie [kJ/kg] aus (T, p)."""
    val = safe_propssi("H", "T", T_C + 273.15, "P", P_bar * 1e5, fluid)
    return val / 1000.0 if np.isfinite(val) else np.nan


def process_enthalpy_J(fluid, T0_C=50.0, p0_bar=210.0):
    """Prozess-Enthalpie [J/kg] am Startpunkt der isenthalpen Entspannung."""
    return PropsSI("H", "T", T0_C + 273.15, "P", p0_bar * 1e5, fluid)


def state_from_ph(p_bar, h_J, fluid):
    """Zustand entlang der Isenthalpe aus (p, h).

    Funktioniert auch im Zweiphasengebiet, wo (T, p) nicht eindeutig ist.
    Liefert: T [°C], Dampfanteil Q (-1 = einphasig), Phasenindex,
             JT-Koeffizient mu [K/bar].
    """
    T = safe_propssi("T", "P", p_bar * 1e5, "H", h_J, fluid)
    Q = safe_propssi("Q", "P", p_bar * 1e5, "H", h_J, fluid)
    ph = safe_propssi("Phase", "P", p_bar * 1e5, "H", h_J, fluid)
    mu = safe_propssi("d(T)/d(P)|H", "P", p_bar * 1e5, "H", h_J, fluid)
    return (T - 273.15 if np.isfinite(T) else np.nan,
            Q, ph,
            mu * 1e5 if np.isfinite(mu) else np.nan)


def saturation_line(fluid, n=400):
    """Saettigungslinie (fluessig<->gasfoermig) vom Tripel- zum krit. Punkt.

    Rueckgabe: T [°C], p [bar], jeweils inklusive Tripel- und kritischem Punkt.
    """
    Tt = PropsSI("Ttriple", fluid)
    Tc = PropsSI("Tcrit", fluid)
    Pt = PropsSI("ptriple", fluid) / 1e5
    Pc = PropsSI("Pcrit", fluid) / 1e5
    Ti = np.linspace(Tt + 0.01, Tc - 0.001, n)
    Pi = np.array([PropsSI("P", "T", T, "Q", 0, fluid) / 1e5 for T in Ti])
    T_C = np.concatenate(([Tt], Ti, [Tc])) - 273.15
    P_bar = np.concatenate(([Pt], Pi, [Pc]))
    return T_C, P_bar


# ============================================================
# 3) CO2-Feststoffgrenzen (Span/Wagner) - nur fuer CO2 relevant
# ============================================================

CO2_T_TRIPLE_K = 216.592
CO2_P_TRIPLE_BAR = 5.1795


def co2_sublimation_pressure_bar(T_K):
    """Sublimationsdruck von CO2 (fest <-> gasfoermig) in bar."""
    T_K = np.asarray(T_K, dtype=float)
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    theta = 1.0 - T_K / CO2_T_TRIPLE_K
    exponent = (CO2_T_TRIPLE_K / T_K
                * (a1 * theta + a2 * theta**1.9 + a3 * theta**2.9))
    return CO2_P_TRIPLE_BAR * np.exp(exponent)


def co2_melting_pressure_bar(T_K):
    """Schmelzdruck von CO2 (fest <-> fluessig) in bar."""
    T_K = np.asarray(T_K, dtype=float)
    a1, a2 = 1955.5390, 2055.4593
    x = T_K / CO2_T_TRIPLE_K - 1.0
    return CO2_P_TRIPLE_BAR * (1.0 + a1 * x + a2 * x**2)


# ============================================================
# 4) p-T-Phasendiagramm je Gas
# ============================================================

COL_GAS = "#b9d7f0"
COL_LIQ = "#b8d8a8"
COL_SUP = "#f4c7a1"
COL_SOL = "#a8a8c8"


def _draw_expansion_path_pT(ax, key):
    """Zeichnet den Entspannungspfad ins p-T-Diagramm (mit Zweiphasen-Marker)."""
    d = EXPANSION[key]
    T = np.array(d["T_C"]); P = np.array(d["P_bar"], dtype=float)
    h0 = process_enthalpy_J(d["fluid"])
    Q = np.array([safe_propssi("Q", "P", p * 1e5, "H", h0, d["fluid"])
                  for p in P])
    twp = (Q >= 0) & (Q <= 1)
    ax.plot(T, P, "-", color=d["color"], linewidth=3, zorder=12,
            label=f"Entspannung {d['label']} (isenthalp)")
    ax.scatter(T[~twp], P[~twp], color=d["color"], s=42, zorder=13)
    if twp.any():
        ax.scatter(T[twp], P[twp], facecolor="white", edgecolor=d["color"],
                   s=52, linewidth=1.6, zorder=13,
                   label="zweiphasig (auf Sättigungslinie)")
    for i in range(0, len(T) - 1, 2):
        ax.annotate("", xy=(T[i + 1], P[i + 1]), xytext=(T[i], P[i]),
                    arrowprops=dict(arrowstyle="->", color="#8b1a1a",
                                    linewidth=1.4), zorder=14)


def make_pt_co2(ax):
    """Detailliertes p-T-Phasendiagramm fuer CO2 inkl. Trockeneis."""
    Tmin, Tmax, Pmin, Pmax = EXPANSION["CO2"]["range"]
    Tt_K = CO2_T_TRIPLE_K
    Tt_C = Tt_K - 273.15
    Pt = CO2_P_TRIPLE_BAR
    Tc_K = PropsSI("Tcrit", "CO2"); Tc_C = Tc_K - 273.15
    Pc = PropsSI("Pcrit", "CO2") / 1e5

    # Sublimationslinie
    T_sub_K = np.linspace(max(154.0, Tmin + 273.15), Tt_K, 500)
    T_sub_C = T_sub_K - 273.15
    P_sub = co2_sublimation_pressure_bar(T_sub_K)

    # Saettigungslinie
    T_sat_C, P_sat = saturation_line("CO2")

    # Schmelzlinie bis Pmax
    a1, a2 = 1955.5390, 2055.4593
    tgt = Pmax / Pt - 1.0
    x_top = (-a1 + np.sqrt(a1**2 + 4.0 * a2 * tgt)) / (2.0 * a2)
    T_melt_K = np.linspace(Tt_K, Tt_K * (1.0 + x_top), 400)
    T_melt_C = T_melt_K - 273.15
    P_melt = co2_melting_pressure_bar(T_melt_K)

    # Flaechen
    gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, Pc), (Tc_C, Pc)]
    gas += list(zip(T_sat_C[::-1], P_sat[::-1]))
    gas += list(zip(T_sub_C[::-1], P_sub[::-1]))
    ax.add_patch(Polygon(gas, closed=True, facecolor=COL_GAS,
                         edgecolor="none", alpha=0.55))

    sol = [(Tmin, Pmax), (T_melt_C[-1], P_melt[-1])]
    sol += list(zip(T_melt_C[::-1], P_melt[::-1]))
    sol += list(zip(T_sub_C[::-1], P_sub[::-1]))
    ax.add_patch(Polygon(sol, closed=True, facecolor=COL_SOL,
                         edgecolor="none", alpha=0.55))

    liq = [(T_melt_C[-1], Pmax), (Tc_C, Pmax)]
    liq += list(zip(T_sat_C[::-1], P_sat[::-1]))
    liq += list(zip(T_melt_C, P_melt))
    ax.add_patch(Polygon(liq, closed=True, facecolor=COL_LIQ,
                         edgecolor="none", alpha=0.55))

    sup = [(Tc_C, Pc), (Tmax, Pc), (Tmax, Pmax), (Tc_C, Pmax)]
    ax.add_patch(Polygon(sup, closed=True, facecolor=COL_SUP,
                         edgecolor="none", alpha=0.55))

    # Grenzlinien
    ax.plot(T_sub_C, P_sub, color="#303030", linewidth=2.0)
    ax.plot(T_sat_C, P_sat, color="#0b4f8a", linewidth=2.3)
    ax.plot(T_melt_C, P_melt, color="#5d3a7e", linewidth=2.0)

    # Punkte
    ax.scatter(Tt_C, Pt, color="black", s=55, zorder=10)
    ax.annotate(f"Tripelpunkt\n{Tt_C:.1f} °C | {Pt:.2f} bar",
                xy=(Tt_C, Pt), xytext=(-46, 8.5),
                arrowprops=dict(arrowstyle="->", color="black"), fontsize=9)
    ax.scatter(Tc_C, Pc, color="#c00000", s=55, zorder=10)
    ax.annotate(f"krit. Punkt\n{Tc_C:.1f} °C | {Pc:.1f} bar",
                xy=(Tc_C, Pc), xytext=(34, 42),
                arrowprops=dict(arrowstyle="->", color="#c00000"),
                fontsize=9, color="#c00000")

    # Beschriftungen
    for x, y, txt, col in [(-88, 30, "fest\nTrockeneis", "#35355f"),
                           (-25, 1.0, "gasförmig", "#164a73"),
                           (-12, 55, "flüssig", "#3f702d"),
                           (50, 150, "superkritisch", "#a3480b")]:
        ax.text(x, y, txt, fontsize=12, ha="center", color=col,
                bbox=dict(facecolor="white", alpha=0.6, edgecolor="none"))

    _finish_pt_axes(ax, "CO2", Tmin, Tmax, Pmin, Pmax, Pt, Pc)


def make_pt_generic(ax, key):
    """Vereinfachtes p-T-Phasendiagramm fuer Gase ohne Feststoffmodell (CH4, H2).

    Der Feststoffbereich liegt fuer CH4/H2 weit unterhalb des Plotbereichs und
    wird daher nicht dargestellt.
    """
    d = EXPANSION[key]
    fluid = d["fluid"]
    Tmin, Tmax, Pmin, Pmax = d["range"]
    Tt_C = PropsSI("Ttriple", fluid) - 273.15
    Pt = PropsSI("ptriple", fluid) / 1e5
    Tc_C = PropsSI("Tcrit", fluid) - 273.15
    Pc = PropsSI("Pcrit", fluid) / 1e5

    T_sat_C, P_sat = saturation_line(fluid)

    # Gasbereich (unten / rechts der Saettigungslinie)
    gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, Pc), (Tc_C, Pc)]
    gas += list(zip(T_sat_C[::-1], P_sat[::-1]))
    gas += [(Tt_C, Pt), (Tmin, Pt)]
    ax.add_patch(Polygon(gas, closed=True, facecolor=COL_GAS,
                         edgecolor="none", alpha=0.55))

    # Fluessigbereich (oberhalb der Saettigungslinie, zwischen Tripel und krit.)
    liq = list(zip(T_sat_C, P_sat)) + [(Tc_C, Pmax), (Tt_C, Pmax)]
    ax.add_patch(Polygon(liq, closed=True, facecolor=COL_LIQ,
                         edgecolor="none", alpha=0.55))

    # Superkritisch
    sup = [(Tc_C, Pc), (Tmax, Pc), (Tmax, Pmax), (Tc_C, Pmax)]
    ax.add_patch(Polygon(sup, closed=True, facecolor=COL_SUP,
                         edgecolor="none", alpha=0.55))

    # Grenzlinie + Punkte
    ax.plot(T_sat_C, P_sat, color="#0b4f8a", linewidth=2.3)
    ax.scatter(Tt_C, Pt, color="black", s=50, zorder=10)
    ax.annotate(f"Tripelpunkt\n{Tt_C:.1f} °C | {Pt:.3f} bar",
                xy=(Tt_C, Pt), xytext=(10, 12), textcoords="offset points",
                fontsize=8)
    ax.scatter(Tc_C, Pc, color="#c00000", s=55, zorder=10)
    ax.annotate(f"krit. Punkt\n{Tc_C:.1f} °C | {Pc:.1f} bar",
                xy=(Tc_C, Pc), xytext=(18, 24), textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="#c00000"),
                fontsize=8, color="#c00000")

    # grobe Beschriftungen
    midT = 0.5 * (Tt_C + Tc_C)
    ax.text(midT, np.sqrt(Pt * Pc), "flüssig", fontsize=12, ha="center",
            color="#3f702d", bbox=dict(facecolor="white", alpha=0.6,
                                       edgecolor="none"))
    ax.text(0.5 * (Tc_C + Tmax), Pmin * 4, "gasförmig", fontsize=12,
            ha="center", color="#164a73",
            bbox=dict(facecolor="white", alpha=0.6, edgecolor="none"))
    ax.text(0.5 * (Tc_C + Tmax), np.sqrt(Pc * Pmax), "superkritisch",
            fontsize=12, ha="center", color="#a3480b",
            bbox=dict(facecolor="white", alpha=0.6, edgecolor="none"))
    ax.text(0.02, 0.02, "Feststoffbereich weit unterhalb -\nnicht dargestellt",
            transform=ax.transAxes, fontsize=7.5, va="bottom", color="#555")

    _finish_pt_axes(ax, d["label"], Tmin, Tmax, Pmin, Pmax, Pt, Pc)


def _finish_pt_axes(ax, label, Tmin, Tmax, Pmin, Pmax, Pt, Pc):
    ax.set_xlim(Tmin, Tmax)
    ax.set_ylim(Pmin, Pmax)
    ax.set_yscale("log")
    ax.set_xlabel("Temperatur (°C)", fontsize=12)
    ax.set_ylabel("Druck (bar, log.)", fontsize=12)
    ax.set_title(f"{label}: p-T-Phasendiagramm der Entspannung", fontsize=13)
    ticks = sorted(set([Pmin, 1.0, round(Pt, 3), 10.0, round(Pc, 1),
                        100.0, Pmax]))
    ticks = [t for t in ticks if Pmin <= t <= Pmax]
    ax.set_yticks(ticks)
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.grid(True, which="both", alpha=0.22)


def make_pt_diagram(ax, key):
    if key == "CO2":
        make_pt_co2(ax)
    else:
        make_pt_generic(ax, key)
    _draw_expansion_path_pT(ax, key)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)


# ============================================================
# 5) p-h-Diagramm je Gas
# ============================================================

def saturation_dome_ph(fluid):
    """Enthalpien [kJ/kg] und Druck [bar] der Zweiphasen-Glocke."""
    Tcrit = PropsSI("Tcrit", fluid)
    Ttrip = PropsSI("Ttriple", fluid)
    T_dome = np.linspace(Ttrip + 0.01, Tcrit - 0.01, 300)
    h_liq, h_vap, p_dome = [], [], []
    for T in T_dome:
        try:
            h_liq.append(PropsSI("H", "T", T, "Q", 0, fluid) / 1000.0)
            h_vap.append(PropsSI("H", "T", T, "Q", 1, fluid) / 1000.0)
            p_dome.append(PropsSI("P", "T", T, "Q", 0, fluid) / 1e5)
        except Exception:
            h_liq.append(np.nan); h_vap.append(np.nan); p_dome.append(np.nan)
    return np.array(h_liq), np.array(h_vap), np.array(p_dome)


def plot_isotherm_ph(ax, T_C, fluid, p_lo, p_hi, color):
    """Zeichnet eine Isotherme in das p-h-Diagramm."""
    T_K = T_C + 273.15
    Tcrit = PropsSI("Tcrit", fluid)
    if T_K >= Tcrit:
        ps = np.logspace(np.log10(p_lo), np.log10(p_hi), 160)
        hs = [enthalpy_kJ(T_C, p, fluid) for p in ps]
        ax.plot(hs, ps, color=color, linewidth=1.0, alpha=0.8)
        ax.annotate(f"{T_C:g}°C", xy=(hs[-1], ps[-1]), fontsize=7,
                    color=color, ha="left", va="center")
        return
    try:
        Psat = PropsSI("P", "T", T_K, "Q", 0, fluid) / 1e5
        h_vap = PropsSI("H", "T", T_K, "Q", 1, fluid) / 1000.0
        h_liq = PropsSI("H", "T", T_K, "Q", 0, fluid) / 1000.0
    except Exception:
        return
    if Psat > p_lo:
        ps_g = np.logspace(np.log10(p_lo), np.log10(Psat * 0.999), 60)
        ax.plot([enthalpy_kJ(T_C, p, fluid) for p in ps_g], ps_g,
                color=color, linewidth=1.0, alpha=0.8)
    ax.plot([h_liq, h_vap], [Psat, Psat], color=color,
            linewidth=1.0, alpha=0.45, linestyle=":")
    if Psat < p_hi:
        ps_l = np.logspace(np.log10(Psat * 1.001), np.log10(p_hi), 60)
        hs_l = [enthalpy_kJ(T_C, p, fluid) for p in ps_l]
        ax.plot(hs_l, ps_l, color=color, linewidth=1.0, alpha=0.8)
        ax.annotate(f"{T_C:g}°C", xy=(hs_l[-1], ps_l[-1]), fontsize=7,
                    color=color, ha="left", va="center")


def plot_isentrope_ph(ax, s_kJ, fluid, p_lo, p_hi, color):
    """Zeichnet eine Isentrope (s = const) in das p-h-Diagramm."""
    ps = np.logspace(np.log10(p_lo), np.log10(p_hi), 160)
    hs = []
    for p in ps:
        val = safe_propssi("H", "P", p * 1e5, "S", s_kJ * 1000.0, fluid)
        hs.append(val / 1000.0 if np.isfinite(val) else np.nan)
    ax.plot(hs, ps, color=color, linewidth=0.9, alpha=0.7, linestyle="--")


def make_ph_diagram(ax, key, p_lo=0.5, p_hi=300.0):
    """p-h-Diagramm fuer ein Fluid aus EXPANSION[key]."""
    d = EXPANSION[key]
    fluid = d["fluid"]
    P_path = np.array(d["P_bar"], dtype=float)
    Tc_C = PropsSI("Tcrit", fluid) - 273.15
    Pc = PropsSI("Pcrit", fluid) / 1e5

    # Zweiphasen-Glocke
    h_liq, h_vap, p_dome = saturation_dome_ph(fluid)
    ax.plot(h_liq, p_dome, color="#0b4f8a", linewidth=2.2)
    ax.plot(h_vap, p_dome, color="#0b4f8a", linewidth=2.2,
            label="Sättigung (Glocke)")

    # kritischer Punkt
    h_crit = enthalpy_kJ(Tc_C + 0.001, Pc, fluid)
    ax.scatter(h_crit, Pc, color="#c00000", s=60, zorder=10)
    ax.annotate(f"krit. Punkt\n{Tc_C:.1f}°C", xy=(h_crit, Pc),
                xytext=(8, 6), textcoords="offset points",
                fontsize=8, color="#c00000")

    # Isothermen
    for T_C in d["isotherms_C"]:
        plot_isotherm_ph(ax, T_C, fluid, p_lo, p_hi, color="#b07d2b")

    # Prozess-Enthalpie (konstant) -> Pfad ist senkrecht
    h0_J = process_enthalpy_J(fluid)
    h0_kJ = h0_J / 1000.0

    # Isentropen aus den Entropien entlang der Isenthalpe
    s_vals = []
    for p in P_path:
        s = safe_propssi("S", "P", p * 1e5, "H", h0_J, fluid)
        if np.isfinite(s):
            s_vals.append(round(s / 1000.0, 2))
    for s in sorted(set(s_vals))[::2]:
        plot_isentrope_ph(ax, s, fluid, p_lo, p_hi, color="#7a7a7a")

    # Entspannungspfad: isenthalp = senkrecht bei h0
    h_path = np.full(len(P_path), h0_kJ)
    Q_path = np.array([safe_propssi("Q", "P", p * 1e5, "H", h0_J, fluid)
                       for p in P_path])
    twp = (Q_path >= 0) & (Q_path <= 1)
    ax.plot(h_path, P_path, "-", color=d["color"], linewidth=3, zorder=12,
            label=f"Entspannung {d['label']} (h=const)")
    ax.scatter(h_path[~twp], P_path[~twp], color=d["color"], s=42, zorder=13)
    if twp.any():
        ax.scatter(h_path[twp], P_path[twp], facecolor="white",
                   edgecolor=d["color"], s=52, linewidth=1.6, zorder=13,
                   label="zweiphasig (im Dom)")
    ax.annotate("", xy=(h0_kJ, P_path[-1]), xytext=(h0_kJ, P_path[0]),
                arrowprops=dict(arrowstyle="->", color="#8b1a1a",
                                linewidth=1.5), zorder=11)

    ax.set_yscale("log")
    ax.set_xlabel("spezifische Enthalpie h (kJ/kg)", fontsize=12)
    ax.set_ylabel("Druck (bar, log.)", fontsize=12)
    ax.set_title(f"{d['label']}: p-h-Diagramm der isenthalpen Entspannung",
                 fontsize=13)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    ax.text(0.02, 0.98, "ocker = Isothermen\ngrau gestrichelt = Isentropen",
            transform=ax.transAxes, fontsize=7.5, va="top",
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))


# ============================================================
# 6) Ein eigenstaendiges Bild je Gas erzeugen
# ============================================================

figs = []
for key in GASES:
    d = EXPANSION[key]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(17, 8))
    make_pt_diagram(axL, key)
    make_ph_diagram(axR, key)
    fig.suptitle(
        f"{d['label']}: isenthalpe Entspannung 210 bar / 50 °C -> 30 bar",
        fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    figs.append((key, fig))


# ============================================================
# 7) Konsolen-Auswertung
# ============================================================

phase_names = {0: "fluessig", 1: "ueberkritisch", 2: "ueberkrit. Gas",
               3: "ueberkrit. Fluessig", 4: "gasfoermig", 5: "gas",
               6: "zweiphasig"}

for key in GASES:
    d = EXPANSION[key]
    print("=" * 72)
    print(f"Isenthalpe Entspannung {d['label']}  (Start 210 bar / 50 °C)")
    print("=" * 72)
    P = np.array(d["P_bar"], dtype=float)
    h0_J = process_enthalpy_J(d["fluid"])
    p_flash = None
    for p in P:
        T_C, Q, ph, mu = state_from_ph(p, h0_J, d["fluid"])
        twp = np.isfinite(Q) and 0 <= Q <= 1
        if twp and p_flash is None:
            p_flash = p
        pname = (phase_names.get(int(ph), f"Phase {ph}")
                 if np.isfinite(ph) else "?")
        q_str = f"Q={Q:5.3f}" if twp else "einphasig"
        print(f"  p={p:6.1f} bar  T={T_C:8.3f} °C  {q_str:>10}  "
              f"mu={mu:6.3f} K/bar  -> {pname}")
    T_start = state_from_ph(P[0], h0_J, d["fluid"])[0]
    T_end = state_from_ph(P[-1], h0_J, d["fluid"])[0]
    print(f"  --> dT gesamt: {T_end - T_start:+.2f} K  |  "
          f"h = {h0_J/1000:.1f} kJ/kg (konstant)")
    if p_flash is not None:
        print(f"  --> tritt ins Zweiphasengebiet ein ab ca. {p_flash:.0f} bar")
    else:
        print("  --> bleibt durchgehend einphasig")
    print()


# ============================================================
# 8) Speichern und anzeigen
# ============================================================

if SAVE_PNG:
    for key, fig in figs:
        fname = f"Entspannung_{EXPANSION[key]['label']}_pT_ph.png"
        fig.savefig(fname, dpi=200, bbox_inches="tight")
        print(f"gespeichert: {fname}")

plt.show()
