# -*- coding: utf-8 -*-
"""
Gasgrundlagen - Annahmen und Rechenbausteine
============================================================================
Grundlagenrechnungen für Kap. 3 der Masterarbeit: Wie verhält sich CO2 im
Vergleich zu Erdgas und Wasserstoff, wenn es gedrosselt (isenthalp) oder
verdichtet (isentrop) wird, und warum liegt die Kavernenanlage genau im
Bereich des Phasenübergangs?

Herkunft: erste Untersuchung in der alten Quellenmatrix
(1_Quellen-_und_Wissensmatrix_alt.xlsx, Blätter „Isenthalpe_Entspannung_Gase“
und „JT-Koeffi_Gase“). Dort wurden die Zustände einzeln mit CoolProp Online
und dem NIST Webbook abgefragt. Hier rechnet Python dieselben Fälle mit
CoolProp direkt, die Excel-Mappe CO2_Gasgrundlagen_Rechenuebersicht.xlsx
zeigt die Rechenschritte.

Stoffe und Zustandsgleichungen (CoolProp, HEOS)
  CO2       Span & Wagner (1996)                        Q-100
  Methan    Setzmann & Wagner (1991), steht für Erdgas  (vereinfachend)
  H2        Leachman et al. (2009), Normal-Wasserstoff
  Erdgas wird vereinfachend als reines Methan gerechnet. Höhere
  Kohlenwasserstoffe und N2 ändern die Zahlenwerte, nicht die Aussage.

Annahmen (jede Zahl mit Begründung)
  P_SPEICHER, T_SPEICHER  210 bar / 50 °C  Startpunkt der Drosselung. 210 bar
                          ist der Höchstdruck an der LCCS (Vorgabe Uniper, wie
                          einspeicherung_bausteine.P_MAX_LCCS). 50 °C liegt
                          zwischen Gebirgstemperatur an der LCCS (46 °C) und
                          der Kaverne nach dem Einspeichern (bis 63 °C,
                          Kaverne/Reines_CO2/kavernenzyklus.json).
  P_ENDE_DROSSEL          10 bar  Enddruck der Drosselung (wie alte Rechnung).
  P_START_V, T_START_V    10 bar / 15 °C  Start der Verdichtung. 15 °C =
                          Temperatur an der Netzübergabe (Tabelle Referenz-
                          bedingungen, Kap. 4).
  P_ENDE_V                210 bar  Ende der Verdichtung (= P_SPEICHER).
  Verdichtung einstufig, isentrop, ohne Kühlung: idealer Vergleichsprozess,
  keine Auslegung. Die reale Verdichtung (zwei Stufen, Zwischenkühlung,
  Wirkungsgrad) steht in Einspeicherung/.
  P_PUMPE_EIN, T_PUMPE_EIN 91 bar / 15 °C  Anlieferung S1 (dichte Phase).
  T_ISOTHERMEN            20, 30, 40, 50 °C  wie NIST-Abfrage der alten Mappe.
  BETRIEBSBEREICH         30 bis 210 bar, 5 bis 65 °C  Hüllkurve aller
                          Zustände der Referenzanlage (siehe unten).

Betriebsbereich der Referenzanlage (aus den eigenen Rechnungen)
  Druck   30 bar   gasförmige Anlieferung/Rückgabe S2 (Tabelle Referenz)
          210 bar  Höchstdruck an der LCCS
  Temp.   5 °C     tiefste Kopftemperatur beim Ausspeichern (5,8 °C bei
                   100.000 Nm³/h, Kaverne/Reines_CO2/bohrlochkopf.json)
          65 °C    höchste Kaverntemperatur beim Einspeichern (63,4 °C,
                   S2 / 100.000 Nm³/h, kavernenzyklus.json), aufgerundet
  Darin liegen der kritische Punkt (31,0 °C / 73,8 bar) und das obere Ende
  der Siedelinie. Genau das ist die Schwierigkeit der Anlage.

Direkt ausführen gibt die Kennwerte der drei Stoffe aus:
    python gasgrundlagen_bausteine.py
"""
from pathlib import Path

import numpy as np
from CoolProp.CoolProp import PropsSI, PhaseSI

ORDNER = Path(__file__).resolve().parent              # Gasgrundlagen
ABB = ORDNER / "Abbildungen"                           # Abbildungen und Ergebnisdateien
DATEN = ORDNER / "Daten"                               # NIST-Vergleichswerte
ABB.mkdir(exist_ok=True)

# ---- Stoffe ------------------------------------------------------------------
# (Kurzname, CoolProp-Name, Anzeigename, Farbe wie Blatt „Medienvergleich“)
STOFFE = {
    "CO2": ("CO2",      "CO₂",           "#007335"),
    "CH4": ("Methane",  "Erdgas (CH₄)",  "#E36C09"),
    "H2":  ("Hydrogen", "Wasserstoff (H₂)", "#164a73"),
}

# ---- Annahmen ----------------------------------------------------------------
P_SPEICHER, T_SPEICHER = 210.0, 50.0     # bar, °C  Start Drosselung
P_ENDE_DROSSEL = 10.0                    # bar
P_START_V, T_START_V = 10.0, 15.0        # bar, °C  Start Verdichtung
P_ENDE_V = 210.0                         # bar
P_PUMPE_EIN, T_PUMPE_EIN = 91.0, 15.0    # bar, °C  Anlieferung S1
T_ISOTHERMEN = [20.0, 30.0, 40.0, 50.0]  # °C
P_RASTER = np.arange(210.0, 9.0, -10.0)  # 210, 200, ..., 10 bar (wie alte Mappe)

BETRIEB_P = (30.0, 210.0)                # bar
BETRIEB_T = (5.0, 65.0)                  # °C

# Normzustand DIN 1343 (wie einspeicherung_bausteine)
P_NORM, T_NORM = 1.01325, 0.0            # bar, °C

R_UNIVERSELL = 8.314462618               # J/(mol K)


def K(T_C):
    return T_C + 273.15


def phase(stoff, p_bar, T_C=None, h=None):
    """Phase als deutsches Wort. Entweder (p, T) oder (p, h)."""
    f = STOFFE[stoff][0]
    if h is not None:
        q = PropsSI("Q", "P", p_bar * 1e5, "H", h, f)
        if 0.0 <= q <= 1.0:
            return "zweiphasig"
        T_C = PropsSI("T", "P", p_bar * 1e5, "H", h, f) - 273.15
    ph = PhaseSI("P", p_bar * 1e5, "T", K(T_C), f)
    return {"gas": "gasförmig", "liquid": "flüssig", "supercritical": "überkritisch",
            "supercritical_gas": "überkritisch (gasähnlich)",
            "supercritical_liquid": "überkritisch (flüssigkeitsähnlich)",
            "twophase": "zweiphasig"}.get(ph, ph)


def zustand(stoff, p_bar, T_C):
    """Stoffwerte bei p, T (Einheiten wie in der Mappe)."""
    f = STOFFE[stoff][0]
    p, T = p_bar * 1e5, K(T_C)
    return {
        "p": p_bar, "T": T_C,
        "rho": PropsSI("D", "P", p, "T", T, f),                     # kg/m³
        "h": PropsSI("H", "P", p, "T", T, f) / 1e3,                 # kJ/kg
        "s": PropsSI("S", "P", p, "T", T, f) / 1e3,                 # kJ/(kg K)
        "cp": PropsSI("C", "P", p, "T", T, f) / 1e3,                # kJ/(kg K)
        "Z": PropsSI("Z", "P", p, "T", T, f),
        "w": PropsSI("A", "P", p, "T", T, f),                       # m/s Schallgeschwindigkeit
        "mu_JT": PropsSI("d(T)/d(P)|Hmass", "P", p, "T", T, f) * 1e5,  # K/bar
        "mu_S": PropsSI("d(T)/d(P)|Smass", "P", p, "T", T, f) * 1e5,   # K/bar
        "phase": phase(stoff, p_bar, T_C),
    }


def kennwerte(stoff):
    f = STOFFE[stoff][0]
    M = PropsSI("M", f)                                             # kg/mol
    return {
        "M": M * 1e3,                                               # g/mol
        "R_s": R_UNIVERSELL / M,                                    # J/(kg K)
        "T_krit": PropsSI("Tcrit", f) - 273.15,
        "p_krit": PropsSI("Pcrit", f) / 1e5,
        "T_tripel": PropsSI("Ttriple", f) - 273.15,
        "p_tripel": PropsSI("ptriple", f) / 1e5,
        "rho_norm": PropsSI("D", "P", P_NORM * 1e5, "T", K(T_NORM), f),
    }


def isenthalpe_entspannung(stoff, p_start=P_SPEICHER, T_start=T_SPEICHER, p_liste=P_RASTER):
    """Drossel: h bleibt gleich. Gibt je Druck T, rho, Dampfanteil und Phase."""
    f = STOFFE[stoff][0]
    h0 = PropsSI("H", "P", p_start * 1e5, "T", K(T_start), f)
    zeilen = []
    for p in p_liste:
        T = PropsSI("T", "P", p * 1e5, "H", h0, f) - 273.15
        q = PropsSI("Q", "P", p * 1e5, "H", h0, f)
        zeilen.append({"p": float(p), "T": T,
                       "rho": PropsSI("D", "P", p * 1e5, "H", h0, f),
                       "q": q if 0.0 <= q <= 1.0 else None,
                       "phase": phase(stoff, p, h=h0)})
    return h0 / 1e3, zeilen


def eintritt_zweiphasig(stoff, p_start=P_SPEICHER, T_start=T_SPEICHER):
    """Druck, bei dem die Drossellinie das Zweiphasengebiet erreicht (None, wenn nie)."""
    f = STOFFE[stoff][0]
    h0 = PropsSI("H", "P", p_start * 1e5, "T", K(T_start), f)
    p_hi, p_lo = p_start, P_ENDE_DROSSEL
    q = PropsSI("Q", "P", p_lo * 1e5, "H", h0, f)
    if not 0.0 <= q <= 1.0:
        return None
    for _ in range(60):                                             # Bisektion
        p_m = 0.5 * (p_hi + p_lo)
        q = PropsSI("Q", "P", p_m * 1e5, "H", h0, f)
        if 0.0 <= q <= 1.0:
            p_lo = p_m
        else:
            p_hi = p_m
    p = 0.5 * (p_hi + p_lo)
    return p, PropsSI("T", "P", p * 1e5, "H", h0, f) - 273.15


def isentrope_verdichtung(stoff, p_start=P_START_V, T_start=T_START_V, p_liste=None):
    """Idealer Verdichter: s bleibt gleich. Gibt je Druck T, rho, spezifische Arbeit."""
    f = STOFFE[stoff][0]
    if p_liste is None:
        p_liste = P_RASTER[::-1]
    s0 = PropsSI("S", "P", p_start * 1e5, "T", K(T_start), f)
    h0 = PropsSI("H", "P", p_start * 1e5, "T", K(T_start), f)
    rho_n = kennwerte(stoff)["rho_norm"]
    zeilen = []
    for p in p_liste:
        h = PropsSI("H", "P", p * 1e5, "S", s0, f)
        zeilen.append({"p": float(p),
                       "T": PropsSI("T", "P", p * 1e5, "S", s0, f) - 273.15,
                       "rho": PropsSI("D", "P", p * 1e5, "S", s0, f),
                       "w_kg": (h - h0) / 1e3,                     # kJ/kg
                       "w_Nm3": (h - h0) / 1e3 * rho_n})            # kJ/Nm³
    return s0 / 1e3, h0 / 1e3, zeilen


def pumpe_isentrop(p_ein=P_PUMPE_EIN, T_ein=T_PUMPE_EIN, p_aus=P_ENDE_V):
    """Ideale Pumpe in dichter Phase und Näherung w = Δp/ρ (inkompressibel)."""
    s0 = PropsSI("S", "P", p_ein * 1e5, "T", K(T_ein), "CO2")
    h0 = PropsSI("H", "P", p_ein * 1e5, "T", K(T_ein), "CO2")
    h1 = PropsSI("H", "P", p_aus * 1e5, "S", s0, "CO2")
    rho = PropsSI("D", "P", p_ein * 1e5, "T", K(T_ein), "CO2")
    return {"rho_ein": rho, "w_kg": (h1 - h0) / 1e3,
            "w_kg_naeherung": (p_aus - p_ein) * 1e5 / rho / 1e3,
            "T_aus": PropsSI("T", "P", p_aus * 1e5, "S", s0, "CO2") - 273.15}


def saettigungslinie_co2(n=200):
    T = np.linspace(PropsSI("Ttriple", "CO2"), PropsSI("Tcrit", "CO2"), n)
    p = np.array([PropsSI("P", "T", t, "Q", 0, "CO2") for t in T]) / 1e5
    return T - 273.15, p


def pseudokritische_linie_co2(p_liste=np.arange(75.0, 231.0, 5.0)):
    """Widom-Linie: Temperatur des cp-Maximums je Druck oberhalb p_krit."""
    T_C = []
    for p in p_liste:
        T_grob = np.linspace(31.5, 120.0, 400)
        cp = [PropsSI("C", "P", p * 1e5, "T", K(t), "CO2") for t in T_grob]
        i = int(np.argmax(cp))
        T_fein = np.linspace(T_grob[max(i - 2, 0)], T_grob[min(i + 2, len(T_grob) - 1)], 200)
        cp = [PropsSI("C", "P", p * 1e5, "T", K(t), "CO2") for t in T_fein]
        T_C.append(float(T_fein[int(np.argmax(cp))]))
    return np.array(T_C), np.array(p_liste)


# Sublimations- und Schmelzlinie nach Span & Wagner (1996), wie in
# Einspeicherung/Begleitstoffe_CO2/Stoffmodell/01_phasendiagramm_rein_vs_gemisch.py
_T_TR = PropsSI("Ttriple", "CO2")
_P_TR = PropsSI("ptriple", "CO2") / 1e5


def sublimation_bar(T_K):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / _T_TR
    return _P_TR * np.exp((_T_TR / T_K) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K):
    a1, a2 = 1955.5390, 2055.4593
    x = T_K / _T_TR - 1.0
    return _P_TR * (1.0 + a1 * x + a2 * x**2)


if __name__ == "__main__":
    print(f"{'Stoff':<18}{'M g/mol':>9}{'R_s':>8}{'T_krit':>8}{'p_krit':>8}{'ρ_n':>8}")
    for k in STOFFE:
        kw = kennwerte(k)
        print(f"{STOFFE[k][1]:<18}{kw['M']:9.3f}{kw['R_s']:8.1f}{kw['T_krit']:8.1f}"
              f"{kw['p_krit']:8.1f}{kw['rho_norm']:8.4f}")
    print(f"\nZustand {P_SPEICHER:.0f} bar / {T_SPEICHER:.0f} °C:")
    for k in STOFFE:
        z = zustand(k, P_SPEICHER, T_SPEICHER)
        print(f"  {STOFFE[k][1]:<18} ρ = {z['rho']:7.1f} kg/m³  Z = {z['Z']:.3f}  "
              f"µ_JT = {z['mu_JT']:+.3f} K/bar  {z['phase']}")
