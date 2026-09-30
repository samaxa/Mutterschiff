# -*- coding: utf-8 -*-
"""
Schritt 2/3 (Gemisch) - Einspeicherpfad mit Worst-Case-Gemisch vs. reines CO2
============================================================================
Gleiche Rechenkette wie im Clean Case (Ordner ../Clean_CO2), aber mit dem
Worst-Case-Gemisch aus gemisch_worstcase.py:

  1) Gassäule Kaverne -> Zieldruck am Bohrlochkopf
  2) S1 (dichte Phase):  Pumpe 91 bar / 15 °C -> Bohrlochkopf
  3) S2 (gasförmig):     Verdichter 1 -> Zwischenkühler -> Verdichter 2
                         -> Kühler -> Pumpe -> Bohrlochkopf
  4) Vergleich:          Durchverdichten in 3 Stufen

Jeder Schritt wird zweimal gerechnet - reines CO2 und Gemisch - mit
denselben Funktionen. Die Werte für reines CO2 müssen dabei exakt die aus
den Clean-Case-Skripten sein (Kontrolle: Kopfdruck 107,60 bar).

Annahmen: unverändert aus dem Clean Case
  Kaverne V1     1200 m, 210 bar am Kavernenboden, Gebirge 10 °C + 0,03 K/m
  S2             30 bar / 15 °C, Zwischendruck 49 bar, Zwischenkühler 40 °C,
                 Kühler 80 bar / 25 °C
  Wirkungsgrade  Verdichter 0,84 / 0,82 / 0,80 (Q-016), Pumpe 0,80
  Durchsatz      50.000-100.000 Nm3/h (0 °C, 1,01325 bar)

Neu für das Gemisch: der S2-Kühleraustritt 80 bar / 25 °C liegt im
Zweiphasengebiet des Gemischs (siehe 01_phasendiagramm_rein_vs_gemisch.py).
Deshalb werden für S2 drei Varianten gerechnet:
  A  wie Clean Case (80 bar / 25 °C)      -> zweiphasig, nicht pumpbar
  B  stärker kühlen (80 bar / 20 °C)      -> 3,3 bar über der Blasenlinie
  C  höher verdichten (86 bar / 25 °C)    -> 3,8 bar über der Cricondenbar
Mindestabstand zur Phasengrenze: 3 bar (Unsicherheit der Phasengrenze,
siehe Dokumentation_Stoffmodelle_Validierung.docx, Kapitel 9).

Isentrope Zustandsänderung wie im Clean Case: h2s bei gleicher Entropie,
mit Wirkungsgrad eta auf die reale Enthalpieerhöhung skaliert.
Für das Gemisch wird dafür die Temperatur über den PT-Flash gesucht
(Klasse Gemisch, _T_suchen) - funktioniert in jeder CoolProp-Version.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI, PhaseSI

import gemisch_worstcase as gw

VERSION = CP.get_global_param_string("version")
print(f"CoolProp-Version: {VERSION}")
if int(VERSION.split(".")[0]) < 8:
    # Geprüft mit 6.6.0: Phasengrenze und alle einphasigen Werte identisch zu
    # 8.0.0, aber der Dampfanteil im Zweiphasengebiet weicht ab (80 bar / 25 °C:
    # Q = 0,04 statt 0,11; GERG-2008 in thermopack: 0,13). Ältere Versionen
    # nutzen einen anderen Flash-Algorithmus. Betrifft nur Variante S2-A.
    print("  Hinweis: CoolProp < 8 - Werte im Zweiphasengebiet (S2-A) ungenau. "
          "Empfohlen: pip install CoolProp==8.0.0")

# ---- 0) Stoffe: gleiche Schnittstelle für reines CO2 und Gemisch ------------
# Einheiten an der Schnittstelle: bar, °C, kJ/kg, kJ/(kg K), kg/m3


class ReinCO2:
    name = "reines CO₂"
    T_KRIT_C = PropsSI("Tcrit", "CO2") - 273.15

    def rho(self, p_bar, T_C):
        """Dichte wie in der Gassäule des Clean Case (nahe Siedelinie: Gasast)."""
        T, p = T_C + 273.15, p_bar * 1e5
        if T_C >= self.T_KRIT_C:
            return PropsSI("D", "P", p, "T", T, "CO2")
        psat = PropsSI("P", "T", T, "Q", 0, "CO2")
        if abs(p - psat) / psat < 5e-4:
            return PropsSI("D", "T", T, "Q", 1, "CO2")
        return PropsSI("D", "P", p, "T", T, "CO2")

    def h(self, p_bar, T_C):
        return PropsSI("H", "P", p_bar * 1e5, "T", T_C + 273.15, "CO2") / 1000

    def s(self, p_bar, T_C):
        return PropsSI("S", "P", p_bar * 1e5, "T", T_C + 273.15, "CO2") / 1000

    def h_ps(self, p_bar, s):
        return PropsSI("H", "P", p_bar * 1e5, "S", s * 1000, "CO2") / 1000

    def T_ph(self, p_bar, h):
        T = PropsSI("T", "P", p_bar * 1e5, "H", h * 1000, "CO2") - 273.15
        return T, PhaseSI("P", p_bar * 1e5, "H", h * 1000, "CO2")

    def phase(self, p_bar, T_C):
        return PhaseSI("P", p_bar * 1e5, "T", T_C + 273.15, "CO2")

    def rho_norm(self):
        return PropsSI("D", "P", 101325, "T", 273.15, "CO2")


class Gemisch:
    name = "Worst-Case-Gemisch"

    def __init__(self):
        self.AS = gw.gemisch()
        # Für die Gassäule (nur dichte Phase oberhalb der Cricondenbar):
        # Phase vorgeben spart die Stabilitätsanalyse -> etwa 10x schneller,
        # Dichte identisch (geprüft gegen freien PT-Flash).
        self.AS_dicht = gw.gemisch()
        self.AS_dicht.specify_phase(CP.iphase_liquid)
        self.p_sicher = gw.phasengrenze()["cricondenbar"][1] + 3.0   # bar

    def _pt(self, p_bar, T_C):
        # PT-Flash mit Kontrolle der Dichtelösung (siehe gw.pt_zustand)
        return gw.pt_zustand(p_bar, T_C, self.AS)

    def rho(self, p_bar, T_C):
        if p_bar > self.p_sicher:
            self.AS_dicht.update(CP.PT_INPUTS, p_bar * 1e5, T_C + 273.15)
            return self.AS_dicht.rhomass()
        return self._pt(p_bar, T_C).rhomass()

    def h(self, p_bar, T_C):
        return self._pt(p_bar, T_C).hmass() / 1000

    def s(self, p_bar, T_C):
        return self._pt(p_bar, T_C).smass() / 1000

    # Isentroper Endzustand und Temperatur aus Enthalpie:
    # Der PS- bzw. PH-Flash von CoolProp funktioniert für Gemische erst ab
    # neueren Versionen ohne weiteres (ältere Versionen verlangen eine vorher
    # gebaute Phasenhüllkurve: "phase envelope must be built to carry out
    # HSU_P_flash for mixture"). Deshalb wird hier die Temperatur selbst
    # gesucht: bei festem p steigen s(T) und h(T) streng mit T, also wird
    # s(p, T) = s_ziel bzw. h(p, T) = h_ziel mit dem PT-Flash nach T gelöst.
    # Das funktioniert in jeder CoolProp-Version, auch im Zweiphasengebiet.

    def _T_suchen(self, p_bar, groesse, ziel, T_min=-50.0, T_max=250.0, tol=1e-5):
        """Löst groesse(p, T) = ziel nach T [°C] (Regula falsi, Illinois-Variante)."""
        a, b = T_min, T_max
        fa, fb = groesse(p_bar, a) - ziel, groesse(p_bar, b) - ziel
        if fa * fb > 0:
            raise ValueError(f"Zielwert bei {p_bar:.1f} bar nicht zwischen {T_min} und {T_max} °C")
        seite = 0
        for _ in range(100):
            c = b - fb * (b - a) / (fb - fa)
            fc = groesse(p_bar, c) - ziel
            if abs(fc) < tol or abs(b - a) < 1e-7:
                return c
            if fc * fb > 0:
                b, fb = c, fc
                if seite == -1:
                    fa /= 2
                seite = -1
            else:
                a, fa = c, fc
                if seite == 1:
                    fb /= 2
                seite = 1
        raise RuntimeError(f"T-Suche bei {p_bar:.1f} bar nicht konvergiert")

    def h_ps(self, p_bar, s):
        T = self._T_suchen(p_bar, self.s, s, tol=1e-7)     # s in kJ/(kg K)
        return self.h(p_bar, T)

    def T_ph(self, p_bar, h):
        T = self._T_suchen(p_bar, self.h, h, tol=1e-5)     # h in kJ/kg
        self._pt(p_bar, T)
        return T, self._phasenname()

    def phase(self, p_bar, T_C):
        self._pt(p_bar, T_C)
        return self._phasenname()

    def _phasenname(self):
        if self.AS.phase() == CP.iphase_twophase:
            return f"ZWEIPHASIG (Q = {self.AS.Q():.2f})"
        return gw._phasenname(self.AS.phase())

    def rho_norm(self):
        return self._pt(1.01325, 0.0).rhomass()


REIN, GEM = ReinCO2(), Gemisch()

# ---- 1) Randbedingungen (identisch Clean Case) ------------------------------
TEUFE = 1200.0          # m
P_MAX_LCCS = 210.0      # bar, Kavernenboden
T_OBERFLAECHE = 10.0    # °C
GRADIENT = 0.03         # K/m
G = 9.81                # m/s2

p_S1, T_S1 = 91.0, 15.0             # S1 Netzübergabe
p_ein, T_ein = 30.0, 15.0           # S2 Netzübergabe
p_zw, T_ZK = 49.0, 40.0             # Zwischendruck, nach Zwischenkühler
eta_V1, eta_V2, eta_V3 = 0.84, 0.82, 0.80
eta_P = 0.80
V_NORM_MIN, V_NORM_MAX = 50000.0, 100000.0   # Nm3/h
ABSTAND_MIN = 3.0                            # bar, Unsicherheit Phasengrenze


def T_gebirge(z):
    return T_OBERFLAECHE + GRADIENT * z


# ---- 2) Bausteine (wie Clean Case, aber für beide Stoffe) -------------------
def gassaeule(stoff, p_lccs_bar, n=600):
    """dp/dz = rho(p,T)*g von unten (Kavernenboden) nach oben (Kopf).

    Gibt Kopfdruck und das Profil (z, p, T, rho) zurück.
    """
    dz = TEUFE / n
    p = p_lccs_bar
    profil = []
    for i in range(n):
        z = TEUFE - i * dz
        rho = stoff.rho(p, T_gebirge(z))
        profil.append((z, p, T_gebirge(z), rho))
        p -= rho * G * dz / 1e5
    profil.append((0.0, p, T_gebirge(0.0), stoff.rho(p, T_gebirge(0.0))))
    return p, np.array(profil)


def stufe(stoff, p1_bar, T1_C, p2_bar, eta):
    """Eine Verdichter- oder Pumpenstufe: isentrop + Wirkungsgrad."""
    h1 = stoff.h(p1_bar, T1_C)
    s1 = stoff.s(p1_bar, T1_C)
    h2s = stoff.h_ps(p2_bar, s1)
    h2 = h1 + (h2s - h1) / eta
    T2, phase2 = stoff.T_ph(p2_bar, h2)
    return dict(p1=p1_bar, T1=T1_C, p2=p2_bar, T2=T2, h1=h1, h2=h2, w=h2 - h1, phase2=phase2)


def abstand_phasengrenze(p_bar, T_C):
    """Abstand eines flüssigen Punkts zur Blasenlinie des Gemischs [bar]."""
    p_bl = gw.blasendruck(T_C)
    if np.isnan(p_bl):                      # oberhalb Cricondentherm: keine Blasenlinie
        return p_bar - gw.phasengrenze()["cricondenbar"][1]
    return p_bar - p_bl


def kette_S2(stoff, p_kopf, p_kuehl, T_kuehl):
    V1 = stufe(stoff, p_ein, T_ein, p_zw, eta_V1)
    q_ZK = V1["h2"] - stoff.h(p_zw, T_ZK)
    V2 = stufe(stoff, p_zw, T_ZK, p_kuehl, eta_V2)
    q_K = V2["h2"] - stoff.h(p_kuehl, T_kuehl)
    P = stufe(stoff, p_kuehl, T_kuehl, p_kopf, eta_P)
    return dict(V1=V1, V2=V2, P=P, q_ZK=q_ZK, q_K=q_K,
                phase_K=stoff.phase(p_kuehl, T_kuehl), p_kuehl=p_kuehl, T_kuehl=T_kuehl,
                w=V1["w"] + V2["w"] + P["w"], q=q_ZK + q_K,
                pfad=[(T_ein, p_ein), (V1["T2"], p_zw), (T_ZK, p_zw), (V2["T2"], p_kuehl),
                      (T_kuehl, p_kuehl), (P["T2"], p_kopf)])


def durchverdichten(stoff, p_kopf, T_end):
    r = (p_kopf / p_ein) ** (1 / 3)
    p_D = [p_ein, p_ein * r, p_ein * r**2, p_kopf]
    D1 = stufe(stoff, p_D[0], T_ein, p_D[1], eta_V1)
    D2 = stufe(stoff, p_D[1], T_ZK, p_D[2], eta_V2)
    D3 = stufe(stoff, p_D[2], T_ZK, p_D[3], eta_V3)
    q = (D1["h2"] - stoff.h(p_D[1], T_ZK)) + (D2["h2"] - stoff.h(p_D[2], T_ZK)) \
        + (D3["h2"] - stoff.h(p_kopf, T_end))
    return dict(D=[D1, D2, D3], w=D1["w"] + D2["w"] + D3["w"], q=q,
                pfad=[(T_ein, p_ein), (D1["T2"], p_D[1]), (T_ZK, p_D[1]), (D2["T2"], p_D[2]),
                      (T_ZK, p_D[2]), (D3["T2"], p_kopf), (T_end, p_kopf)])


def massenstrom(stoff):
    rho_n = stoff.rho_norm()
    return V_NORM_MIN * rho_n / 3600.0, V_NORM_MAX * rho_n / 3600.0


# ---- 3) Rechnen: reines CO2 und Gemisch ------------------------------------
erg = {}
for stoff in (REIN, GEM):
    print(f"\n==== {stoff.name} ====")
    p_kopf, profil = gassaeule(stoff, P_MAX_LCCS)
    S1 = stufe(stoff, p_S1, T_S1, p_kopf, eta_P)
    m_min, m_max = massenstrom(stoff)
    e = dict(p_kopf=p_kopf, profil=profil, S1=S1, m=(m_min, m_max),
             rho_kav=stoff.rho(P_MAX_LCCS, T_gebirge(TEUFE)))
    print(f"Gassäule: {P_MAX_LCCS:.0f} bar unten -> {p_kopf:.2f} bar am Bohrlochkopf")
    print(f"Dichte am Kavernenboden: {e['rho_kav']:.1f} kg/m3")
    print(f"S1 Pumpe: {p_S1:.0f} -> {p_kopf:.2f} bar, {T_S1:.0f} -> {S1['T2']:.2f} °C, "
          f"w = {S1['w']:.2f} kJ/kg ({S1['phase2']})")

    if stoff is REIN:
        varianten = {"S2": (80.0, 25.0)}
    else:
        varianten = {"S2-A wie Clean Case": (80.0, 25.0),
                     "S2-B Kühler 20 °C": (80.0, 20.0),
                     "S2-C 86 bar": (86.0, 25.0)}
    e["S2"] = {}
    for vname, (pk, Tk) in varianten.items():
        k = kette_S2(stoff, p_kopf, pk, Tk)
        e["S2"][vname] = k
        print(f"{vname}:")
        print(f"  V1 {p_ein:.0f}->{p_zw:.0f} bar: T_aus {k['V1']['T2']:.1f} °C, w = {k['V1']['w']:.2f} kJ/kg")
        print(f"  Zwischenkühler -> {T_ZK:.0f} °C: q = {k['q_ZK']:.2f} kJ/kg")
        print(f"  V2 {p_zw:.0f}->{pk:.0f} bar: T_aus {k['V2']['T2']:.1f} °C, w = {k['V2']['w']:.2f} kJ/kg")
        print(f"  Kühler -> {pk:.0f} bar / {Tk:.0f} °C: q = {k['q_K']:.2f} kJ/kg  ({k['phase_K']})")
        if stoff is GEM:
            a = abstand_phasengrenze(pk, Tk)
            bewertung = "ok" if a >= ABSTAND_MIN else "NICHT ausreichend"
            print(f"  Abstand zur Phasengrenze: {a:+.1f} bar (mind. {ABSTAND_MIN:.0f} bar) -> {bewertung}")
            k["abstand"] = a
        print(f"  Pumpe {pk:.0f}->{p_kopf:.2f} bar: T_aus {k['P']['T2']:.2f} °C, w = {k['P']['w']:.2f} kJ/kg")
        print(f"  Summe: w = {k['w']:.2f} kJ/kg, q = {k['q']:.2f} kJ/kg")

    T_end = e["S2"][list(varianten)[-1]]["P"]["T2"]
    e["D"] = durchverdichten(stoff, p_kopf, T_end)
    print(f"Durchverdichten: w = {e['D']['w']:.2f} kJ/kg, q = {e['D']['q']:.2f} kJ/kg")
    erg[stoff.name] = e

R, M = erg[REIN.name], erg[GEM.name]

# ---- 4) Auswirkungen: Gegenüberstellung ------------------------------------
M_CO2 = PropsSI("M", "CO2")
M_gem = gw.gemisch().molar_mass()
w_CO2 = gw.MOLANTEILE[0] * M_CO2 / M_gem           # Massenanteil CO2 im Gemisch


def leistung(w, m):
    return f"{m[0] * w:6.0f}-{m[1] * w:6.0f} kW"


print("\n==== Auswirkungen des Worst-Case-Gemischs ====")
print(f"CO2-Massenanteil im Gemisch: {100 * w_CO2:.1f} %")
print(f"Massenstrom bei 50.000-100.000 Nm3/h: rein {R['m'][0]:.1f}-{R['m'][1]:.1f} kg/s, "
      f"Gemisch {M['m'][0]:.1f}-{M['m'][1]:.1f} kg/s")
print(f"Kopfdruck:           rein {R['p_kopf']:7.2f} bar | Gemisch {M['p_kopf']:7.2f} bar "
      f"({M['p_kopf'] - R['p_kopf']:+.2f} bar)")
print(f"Dichte Kavernenboden: rein {R['rho_kav']:6.1f} kg/m3 | Gemisch {M['rho_kav']:6.1f} kg/m3 "
      f"({100 * (M['rho_kav'] / R['rho_kav'] - 1):+.1f} %), CO2 darin "
      f"{100 * (M['rho_kav'] * w_CO2 / R['rho_kav'] - 1):+.1f} %")
print(f"S1 Pumpe:            rein {R['S1']['w']:6.2f} kJ/kg | Gemisch {M['S1']['w']:6.2f} kJ/kg "
      f"({100 * (M['S1']['w'] / R['S1']['w'] - 1):+.0f} %)")
print(f"                     rein {leistung(R['S1']['w'], R['m'])} | Gemisch {leistung(M['S1']['w'], M['m'])}")
wR = R["S2"]["S2"]
for vname, k in M["S2"].items():
    print(f"{vname:<20} w = {k['w']:6.2f} kJ/kg ({100 * (k['w'] / wR['w'] - 1):+.0f} % zu rein {wR['w']:.2f}), "
          f"q = {k['q']:6.2f} kJ/kg, Leistung {leistung(k['w'], M['m'])}")
print(f"Durchverdichten:     rein {R['D']['w']:6.2f} kJ/kg | Gemisch {M['D']['w']:6.2f} kJ/kg")

# ---- 5) Diagramm 1: Einspeicherpfade im Phasendiagramm des Gemischs --------
ROT, GRUEN, BLAU, VIOLETT, GRAU = "#CA220E", "#007335", "#0476D9", "#7030A0", "#8C8C8C"
pg = gw.phasengrenze()
T_krit_C = REIN.T_KRIT_C
p_krit_bar = PropsSI("Pcrit", "CO2") / 1e5
T_s = np.linspace(PropsSI("Ttriple", "CO2"), PropsSI("Tcrit", "CO2"), 150)
p_s = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_s]) / 1e5

Tmin, Tmax, Pmin, Pmax = -20.0, 100.0, 0.0, 130.0
fig, ax = plt.subplots(figsize=(11, 7))
# Hintergrund neutral: die farbigen Phasenflächen von reinem CO2 gelten für
# das Gemisch nicht mehr; maßgebend ist die Phasengrenze des Gemischs
ax.plot(T_s - 273.15, p_s, color="#00304F", lw=1.4, zorder=3, label="Sättigungslinie reines CO₂")
T_kG, p_kG = pg["krit"]
ax.plot(T_kG, p_kG, "o", color=ROT, ms=7, markeredgecolor="white", zorder=5)
bereich = dict(fontsize=11, weight="bold", color="#9A9A9A", ha="center", zorder=2)
ax.text(-5, 110, "flüssig / dicht", **bereich)
ax.text(80, 20, "gasförmig", **bereich)
ax.text(80, 110, "überkritisch", **bereich)

# Zweiphasengebiet Gemisch mit Unsicherheitsband ±3 bar
huelle_T = np.concatenate([pg["T_tau"], pg["T_blase"]])
huelle_p = np.concatenate([pg["p_tau"], pg["p_blase"]])
ax.fill(huelle_T, huelle_p, fc="none", ec=ROT, hatch="///", lw=0, alpha=0.45, zorder=1)
ax.fill_between(pg["T_blase"], pg["p_blase"] - ABSTAND_MIN, pg["p_blase"] + ABSTAND_MIN,
                color=ROT, alpha=0.13, lw=0, zorder=1, label="Unsicherheit Phasengrenze ±3 bar")
ax.fill_between(pg["T_tau"], pg["p_tau"] - ABSTAND_MIN, pg["p_tau"] + ABSTAND_MIN,
                color=ROT, alpha=0.13, lw=0, zorder=1)
ax.plot(huelle_T, huelle_p, color=ROT, lw=2.0, zorder=4, label="Phasengrenze Gemisch")

# Clean Case S2 zum Vergleich
ax.plot(*zip(*R["S2"]["S2"]["pfad"]), "-", color=GRAU, lw=1.2, zorder=5,
        label="S2 reines CO₂ (Clean Case)")
stile = {"S2-A wie Clean Case": (ROT, "--", "o"), "S2-B Kühler 20 °C": (BLAU, "-", "o"),
         "S2-C 86 bar": (VIOLETT, "-", "s")}
for vname, k in M["S2"].items():
    farbe, ls, mk = stile[vname]
    ax.plot(*zip(*k["pfad"]), ls=ls, marker=mk, color=farbe, lw=2.0, ms=5, zorder=6,
            label=f"{vname} (Gemisch)")
ax.plot([T_S1, M["S1"]["T2"]], [p_S1, M["p_kopf"]], "-D", color=GRUEN, lw=2.5, ms=6, zorder=7,
        label="S1 Pumpe (Gemisch)")

txt = dict(fontsize=8.5, color="#303030", zorder=8)
ax.annotate("S2-A: Kühleraustritt 80 bar / 25 °C\nim Zweiphasengebiet", (25, 80), xytext=(40, 96),
            arrowprops=dict(arrowstyle="->", color=ROT, lw=1.0), color=ROT, fontsize=8.5, weight="bold")
ax.text(-19, 41, "Zweiphasengebiet\nGemisch", color=ROT, fontsize=8.5, weight="bold", zorder=8)
ax.text(T_ein + 2, p_ein - 5, "S2 Netzübergabe", **txt)
ax.text(T_S1 - 19, p_S1 - 1, "S1 Netzübergabe", **txt)
ax.text(5, M["p_kopf"] + 4, f"Bohrlochkopf Gemisch {M['p_kopf']:.1f} bar".replace(".", ","), **txt)
ax.axhline(M["p_kopf"], color=GRUEN, lw=0.8, ls=":", zorder=2)
ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("Einspeicherpfade mit Worst-Case-Gemisch im p-T-Diagramm (bis Bohrlochkopf)", fontsize=11)
ax.grid(alpha=0.3, zorder=1)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig("abb_einspeicherpfad_gemisch.png", dpi=170)
print("\ngespeichert: abb_einspeicherpfad_gemisch.png")

# ---- 6) Diagramm 2: spezifische Arbeit rein vs. Gemisch --------------------
zeilen = [("S1 reines CO₂", [0, 0, 0, R["S1"]["w"]]),
          ("S1 Gemisch", [0, 0, 0, M["S1"]["w"]]),
          ("S2 reines CO₂", [wR["V1"]["w"], wR["V2"]["w"], 0, wR["P"]["w"]])]
for vname, k in M["S2"].items():
    zeilen.append((vname.replace("S2-", "S2 Gemisch ") + (" *" if "A" in vname.split()[0] else ""),
                   [k["V1"]["w"], k["V2"]["w"], 0, k["P"]["w"]]))
zeilen += [("Durchverdichten rein", [d["w"] for d in R["D"]["D"]][:2] + [R["D"]["D"][2]["w"], 0]),
           ("Durchverdichten Gemisch", [d["w"] for d in M["D"]["D"]][:2] + [M["D"]["D"][2]["w"], 0])]
teile = [("Verdichter 1. Stufe", "#EE7203"), ("Verdichter 2. Stufe", "#F4B183"),
         ("Verdichter 3. Stufe", "#C55A11"), ("Pumpe", GRUEN)]

fig2, ax2 = plt.subplots(figsize=(10, 5.2))
namen = [z[0] for z in zeilen]
werte = np.array([z[1] for z in zeilen], dtype=float)
links = np.zeros(len(zeilen))
for j, (tname, farbe) in enumerate(teile):
    ax2.barh(namen, werte[:, j], left=links, color=farbe, label=tname, height=0.6)
    links += werte[:, j]
for y, summe in enumerate(links):
    ax2.text(summe + 1, y, f"{summe:.1f} kJ/kg".replace(".", ","), va="center", fontsize=8.5, weight="bold")
ax2.invert_yaxis()
ax2.set_xlim(0, links.max() * 1.18)
ax2.set_xlabel("spezifische Arbeit bis Bohrlochkopf [kJ/kg]")
ax2.set_title("Spezifische Arbeit: reines CO₂ vs. Worst-Case-Gemisch", fontsize=11)
ax2.grid(axis="x", alpha=0.3)
ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4, fontsize=8, frameon=False)
fig2.text(0.5, 0.01, "* S2-A: Pumpeneintritt zweiphasig (Q = 0,11) - rechnerisch, technisch nicht zulässig",
          ha="center", fontsize=8, color=ROT)
fig2.tight_layout(rect=[0, 0.04, 1, 1])
fig2.savefig("abb_arbeit_rein_vs_gemisch.png", dpi=170)
print("gespeichert: abb_arbeit_rein_vs_gemisch.png")

# ---- 7) Diagramm 3: Gassäule rein vs. Gemisch ------------------------------
fig3, (b1, b2) = plt.subplots(1, 2, figsize=(10, 5.5), sharey=True)
for e, farbe, name in ((R, "#00304F", "reines CO₂"), (M, ROT, "Gemisch")):
    z, p, T, rho = e["profil"].T
    b1.plot(rho, z, color=farbe, lw=2, label=name)
    b2.plot(p, z, color=farbe, lw=2, label=f"{name}: Kopf {e['p_kopf']:.1f} bar".replace(".", ","))
b1.set(xlabel="Dichte [kg/m³]", ylabel="Teufe [m]", title="Dichte in der Gassäule")
b2.set(xlabel="Druck [bar]", title="Druck in der Gassäule")
b1.invert_yaxis()
for b in (b1, b2):
    b.grid(alpha=0.3)
    b.legend(fontsize=8.5)
fig3.suptitle("Gassäule Kaverne V1 (1200 m, 210 bar unten): reines CO₂ vs. Gemisch", fontsize=11)
fig3.tight_layout()
fig3.savefig("abb_gassaeule_rein_vs_gemisch.png", dpi=170)
print("gespeichert: abb_gassaeule_rein_vs_gemisch.png")
