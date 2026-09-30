# -*- coding: utf-8 -*-
"""
Worst-Case-Gemisch Anlieferung - Stoffdaten-Definition für CoolProp
============================================================================
Vorschlag Worst-Case-Gemisch an der Netzübergabe (Tabelle "Vorschlag
Worst-Case-Gemisch Anlieferung"):

  Komponente   mol-%   Beleg
  CO2          95,0    DIN EN 18397 / ISO 27913
  N2            2,4    Porthos-Grenzwert
  Ar            1,0    ca. Oxyfuel-Zusammensetzung
  CH4           1,0    Porthos-Grenzwert
  H2            0,5    DIN EN 18397 / DVGW C 260
  CO            0,1    DIN EN 18397 (1000 ppm)
  Σ Begleitst.  5,0    = Grenze DIN EN 18397

Diese Datei ist das "Stoffdatenblatt" des Gemischs: alle weiteren Skripte
(Phasendiagramm, später Verdichtung/Pumpe/Kaverne mit Gemisch) importieren
von hier, damit die Zusammensetzung nur an EINER Stelle steht.

CoolProp und Gemische
  Reinstoffe rechnet man mit PropsSI("D", "P", p, "T", T, "CO2").
  Für Gemische nimmt man besser die AbstractState-Schnittstelle:
      AS = AbstractState("HEOS", "CO2&Nitrogen&Argon&...")
      AS.set_mole_fractions([0.95, 0.024, ...])
      AS.update(PT_INPUTS, p, T)      -> danach AS.rhomass(), AS.hmass(), ...
  HEOS = Helmholtz-Gleichungen der Reinstoffe (für CO2 Span-Wagner) plus
  Mischungsregel nach Kunz & Wagner (GERG-2008).

  Wechselwirkungsparameter (Binärpaare mit CO2), in CoolProp hinterlegt:
    CO2-N2, CO2-Ar, CO2-CH4 : GERG-2008 inkl. Departure-Funktion (F = 1)
    CO2-H2, CO2-CO          : nur angepasste Mischungsregel (F = 0),
                              also etwas ungenauer - bei 0,5 % H2 und
                              0,1 % CO für den Worst-Case vertretbar.

  Die Zustandsgleichung kennt keine feste Phase (Trockeneis). Unterhalb
  des Tripelpunkts von reinem CO2 (-56,6 °C) werden deshalb keine
  Gemischwerte ausgewertet.

Direkt ausführen gibt die Zusammensetzung und die Kennwerte des Gemischs aus:
    python gemisch_worstcase.py
"""
from functools import lru_cache

import numpy as np
import CoolProp.CoolProp as CP

# ---- 1) Zusammensetzung -----------------------------------------------------
# (Anzeigename, CoolProp-Name, mol-%, Beleg)
ZUSAMMENSETZUNG = [
    ("CO₂", "CO2",            95.0, "DIN EN 18397 / ISO 27913"),
    ("N₂",  "Nitrogen",        2.4, "Porthos-Grenzwert"),
    ("Ar",  "Argon",           1.0, "ca. Oxyfuel-Zusammensetzung"),
    ("CH₄", "Methane",         1.0, "Porthos-Grenzwert"),
    ("H₂",  "Hydrogen",        0.5, "DIN EN 18397 / DVGW C 260"),
    ("CO",  "CarbonMonoxide",  0.1, "DIN EN 18397 (1000 ppm)"),
]

KOMPONENTEN = [k[1] for k in ZUSAMMENSETZUNG]
MOLANTEILE = [k[2] / 100.0 for k in ZUSAMMENSETZUNG]      # mol-% -> Molanteil
FLUID_STRING = "&".join(KOMPONENTEN)                        # "CO2&Nitrogen&..."

assert abs(sum(MOLANTEILE) - 1.0) < 1e-9, "Molanteile ergeben nicht 100 %"

# Tripelpunkt von reinem CO2: Untergrenze für die Gemischauswertung (s.o.)
T_TRIPEL_CO2 = CP.PropsSI("Ttriple", "CO2")


def gemisch():
    """Neuer AbstractState mit der Worst-Case-Zusammensetzung."""
    AS = CP.AbstractState("HEOS", FLUID_STRING)
    AS.set_mole_fractions(MOLANTEILE)
    return AS


def stoffwerte(p_bar, T_C, AS=None):
    """Zustand des Gemischs bei p [bar], T [°C] (PT-Flash).

    Gibt ein dict zurück: Phase, Dichte [kg/m3], Enthalpie [kJ/kg],
    Entropie [kJ/kgK] und - falls zweiphasig - den Dampfanteil Q.
    """
    AS = AS or gemisch()
    AS.update(CP.PT_INPUTS, p_bar * 1e5, T_C + 273.15)
    ergebnis = {
        "phase": _phasenname(AS.phase()),
        "rho": AS.rhomass(),
        "h": AS.hmass() / 1000.0,
        "s": AS.smass() / 1000.0,
    }
    if AS.phase() == CP.iphase_twophase:
        ergebnis["Q"] = AS.Q()
    return ergebnis


def _phasenname(i):
    namen = {
        CP.iphase_liquid: "flüssig",
        CP.iphase_gas: "gasförmig",
        CP.iphase_twophase: "ZWEIPHASIG",
        CP.iphase_supercritical: "überkritisch",
        CP.iphase_supercritical_gas: "überkritisch (gasähnlich)",
        CP.iphase_supercritical_liquid: "überkritisch (flüssigkeitsähnlich)",
    }
    return namen.get(i, str(i))


@lru_cache(maxsize=1)
def phasengrenze():
    """Phasengrenze (Zweiphasengebiet) des Gemischs im p-T-Diagramm.

    Bei einem Gemisch gibt es keine einzelne Dampfdrucklinie mehr wie bei
    reinem CO2, sondern ein Zweiphasengebiet zwischen
      Taulinie   (Q = 1): erster Flüssigkeitstropfen fällt aus
      Blasenlinie (Q = 0): erste Gasblase entsteht
    Beide treffen sich im kritischen Punkt des Gemischs.

    CoolProp verfolgt die ganze Hüllkurve mit build_phase_envelope. Die
    Rechnung läuft über die Taulinie hoch zum kritischen Punkt und über die
    Blasenlinie wieder herunter. Unterhalb des CO2-Tripelpunkts (Feststoff,
    s.o.) wird abgeschnitten; dort läuft die Rechnung außerdem in einen
    unphysikalischen Hochdruckast.

    Rückgabe: dict mit Arrays T_tau, p_tau, T_blase, p_blase in °C / bar
    sowie kritischem Punkt, Cricondenbar (max. Druck) und
    Cricondentherm (max. Temperatur) des Zweiphasengebiets.
    """
    AS = gemisch()
    AS.build_phase_envelope("")
    PE = AS.get_phase_envelope_data()
    T = np.array(PE.T)
    p = np.array(PE.p)
    Q = np.array(PE.Q)

    # Taulinie: erster Block mit Q = 1, danach Blasenlinie bis Q wieder springt
    i_krit = int(np.argmax(Q < 0.5))
    i_ende = i_krit + int(np.argmax(Q[i_krit:] > 0.5)) if np.any(Q[i_krit:] > 0.5) else len(Q)

    tau = T[:i_krit] >= T_TRIPEL_CO2
    blase = T[i_krit:i_ende] >= T_TRIPEL_CO2
    T_tau, p_tau = T[:i_krit][tau], p[:i_krit][tau]
    T_bl, p_bl = T[i_krit:i_ende][blase], p[i_krit:i_ende][blase]

    # Kritischer Punkt: Übergang Q=1 -> Q=0, zwischen den beiden Nachbarpunkten
    T_krit = 0.5 * (T[i_krit - 1] + T[i_krit])
    p_krit = 0.5 * (p[i_krit - 1] + p[i_krit])

    T_alle = np.concatenate([T_tau, T_bl])
    p_alle = np.concatenate([p_tau, p_bl])
    i_pmax, i_Tmax = int(np.argmax(p_alle)), int(np.argmax(T_alle))

    C = 273.15
    return {
        "T_tau": T_tau - C, "p_tau": p_tau / 1e5,
        "T_blase": T_bl - C, "p_blase": p_bl / 1e5,
        "krit": (T_krit - C, p_krit / 1e5),
        "cricondenbar": (T_alle[i_pmax] - C, p_alle[i_pmax] / 1e5),
        "cricondentherm": (T_alle[i_Tmax] - C, p_alle[i_Tmax] / 1e5),
    }


def blasendruck(T_C):
    """Blasendruck [bar] bei T [°C]: oberhalb davon ist das Gemisch einphasig flüssig.

    Aus der Hüllkurve interpoliert - ein direkter QT-Flash (Q = 0) findet
    nahe dem kritischen Punkt oft keine Lösung.
    """
    pg = phasengrenze()
    # Blasenlinie läuft vom kritischen Punkt zu tiefen T -> für interp umdrehen
    return float(np.interp(T_C, pg["T_blase"][::-1], pg["p_blase"][::-1], left=np.nan, right=np.nan))


def taudruck(T_C):
    """Taudruck [bar] bei T [°C]: unterhalb davon ist das Gemisch einphasig gasförmig."""
    pg = phasengrenze()
    i = int(np.argmax(pg["T_tau"]))       # nur bis zum Cricondentherm (monoton in T)
    return float(np.interp(T_C, pg["T_tau"][:i + 1], pg["p_tau"][:i + 1], left=np.nan, right=np.nan))


if __name__ == "__main__":
    print("Worst-Case-Gemisch Anlieferung")
    print(f"  {'Komponente':<10} {'mol-%':>6}   Beleg")
    for name, _, x, beleg in ZUSAMMENSETZUNG:
        print(f"  {name:<10} {x:>6.1f}   {beleg}")
    print(f"  {'Σ Begleit.':<10} {100 - ZUSAMMENSETZUNG[0][2]:>6.1f}   = Grenze DIN EN 18397")

    AS = gemisch()
    print(f"\nMolare Masse: {AS.molar_mass()*1000:.2f} g/mol  (reines CO2: 44.01 g/mol)")

    pg = phasengrenze()
    print("\nZweiphasengebiet des Gemischs (CoolProp build_phase_envelope):")
    print(f"  kritischer Punkt: {pg['krit'][0]:.1f} °C / {pg['krit'][1]:.1f} bar")
    print(f"  Cricondenbar:     {pg['cricondenbar'][0]:.1f} °C / {pg['cricondenbar'][1]:.1f} bar")
    print(f"  Cricondentherm:   {pg['cricondentherm'][0]:.1f} °C / {pg['cricondentherm'][1]:.1f} bar")
