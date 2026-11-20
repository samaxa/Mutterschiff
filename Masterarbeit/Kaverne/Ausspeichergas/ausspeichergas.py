# -*- coding: utf-8 -*-
"""
Ausspeichergas - Stoffdatenblatt für den Ausspeicherpfad
============================================================================
Gegenstück zu gemisch_worstcase.py: dort steht, was in die Kaverne geht, hier,
was wieder herauskommt. Die Herleitung rechnet 06_zusammensetzung_nach_kaverne.py
(dieser Ordner) und legt das Ergebnis in zusammensetzung_nach_kaverne.json ab. Der
Ausspeicherpfad (HYSYS-Eingabe) importiert nur dieses Modul:

    import ausspeichergas as ag
    AS = ag.gemisch_trocken()               # CoolProp-AbstractState, Auslegungsfall (gem_max)
    AS = ag.gemisch_trocken("rein_min")     # andere Fälle, siehe ag.FAELLE
    y  = ag.wasser_im_co2(p, T)             # Wassersättigung für Abscheider/Trocknung

Stand 18.11.2026: gleiche Logik wie die Mappe CO2_Ausspeichergas_Zusammensetzung.xlsx
(dieser Ordner, Blätter 04 bis 12). Die Molanteile in zusammensetzung_nach_kaverne.json
stimmen mit Blatt 12, Abschnitt 3 (feucht) und Abschnitt 7 (trocken, CoolProp-Namen) überein.

Fälle (Spalten D bis I der Mappe):
  rein_min                  reines CO₂, Min-Fall, S1 (Pumpe, kein Verdichter), Stillstand
  rein_max                  reines CO₂, Max-Fall, S2 (Verdichter), Stillstand
  gem_min                   Gemisch,    Min-Fall, S1, Stillstand
  gem_max                   Gemisch,    Max-Fall, S2, Stillstand  -> AUSLEGUNGSFALL
  gem_max_ohne_stillstand   wie gem_max, Ausspeichern direkt nach dem Einspeichern
  gem_max_ab_2_zyklus       wie gem_max, Resterdgas ist mit dem 1. Zyklus ausgetragen
  zusätzlich (nicht in der Mappe): rein_min/rein_max/gem_min_ab_2_zyklus

Bandbreite (Besprechung K. Vosbeck 15.10.2026). Seite = "Seite x von 56" in Q-089.

  Eintrag              Min-Fall                       Max-Fall (Auslegung)            Quelle
  Wasser               voll 75 % der Sättigung        gesättigt über reinem Wasser    Q-089 Abschn. 6.5, Tab. 19 (S. 39);
                       (Sole), leer 100 %             (a_w = 1); ohne Stillstand:     Q-137 Abschn. 3; Q-124 (Spycher)
                                                      wärmster Zustand Ende Einsp.
  Resterdgas           Finger 1000 m³ je 500.000 m³,  Finger 2000 m³ je 500.000 m³,   Q-089 Abschn. 6.3, Tab. 16/17;
                       Erdgas H Russland              Erdgas H Nordsee; nur 1. Zyklus Q-140 (OGE 2022)
  Diesel-Blanket       Fall 4a: 0,084 m³,             Fall 4c: 1,76 m³,               Q-089 Tab. 10 (S. 23);
                       Aromaten 7 %                   Aromaten 38 %                   Q-142, Q-141 Anhang II
  Verdichteröl         S1: 0 (kein Verdichter)        S2: 0,260 kg je 10⁵ Nm³         Q-089 Tab. 20 (S. 39); Q-139 S. 64
                       (S2 Min: 0,135 kg)
  H₂S mikrobiell       0 (Bildung gehemmt)            10 ppm                          Q-089 Abschn. 6.4.2; Q-126, Q-128
  CH₄ mikrobiell       0                              50 ppm, verbraucht 4 H₂ (Gem.)  Q-089 Abschn. 6.4.3, Tab. 20
  H₂S/COS Anlieferung  0                              5 / 15 ppm (nur Gemisch)        Q-096 (Porthos, Schwefel 20 ppm)
  O₂/NOx Anlieferung   0                              40 / 5 ppm (nur Gemisch)        Q-096 (Porthos)
  CO₂ in der Restsole  nur Information (1 % Sole), geht nicht in die Zusammensetzung   Q-003, Q-136, Q-137

Übertrag auf CO₂ (warum sich die Mengen gegenüber H₂ ändern):
  Wasser        CO₂ löst deutlich mehr Wasser als H₂, im dichten Zustand mehr als
                im gasförmigen. Modell: Spycher, Pruess & Ennis-King (2003, Q-124).
  Diesel/Öl     dichtes CO₂ ist ein starkes Lösungsmittel für Kohlenwasserstoffe
                (Q-003 Kap. 8.2.2.1) -> Restblanket und Verdichteröl lösen sich vollständig.
  Resterdgas    gleiches Fingervolumen wie Q-089, aber dichtes CO₂ enthält je m³ etwa
                2,5-mal so viele Mole wie H₂ -> kleinerer Anteil. Zusammensetzung als
                Erdgas H statt reinem Methan: C₂+ (bis C6+) fürs KW-Taupunkt-Thema.
  Mikrobiologie im Gemisch nur 0,5 % H₂ als Nahrung, in reinem CO₂ keiner; saure (pH ≈ 3,
                Q-127) und gesättigte Sole bremsen die Mikroben, schließen sie aber nicht
                aus (Q-126 S. 12, Q-128). Max-Fall: Werte aus Q-089 als Worst Case.

Randbedingung Rückgabe ins Netz (OGE-Austausch 16.09.2026, Notizen S. Maxara):
  H₂O ≤ 30 ppm, H₂S < 0,5 ppm, mindestens 91 bar; Glykoltrocknung und Aminwäsche
  ausgeschlossen -> Adsorption (TSA) und H₂S-Entfernung im Ausspeicherpfad (HYSYS).

CoolProp: Für Carbonylsulfid (COS) fehlen in CoolProp die Wechselwirkungsparameter mit
N₂, Ar, Ethan, Butan, Pentan, Hexan, H₂, CO und O₂. gemisch_trocken() setzt für diese
Paare die einfache Lorentz-Berthelot-Regel. Bei 15 ppm COS ändert das die Dichte um
weniger als 0,01 % (geprüft gegen COS als H₂S gezählt).

Einheiten: bar, °C, Molanteile [-], ppm = mol-ppm, g/Nm³ bezogen auf trockenes Gas.
"""
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from CoolProp.CoolProp import PropsSI

ORDNER = Path(__file__).resolve().parent
JSON = ORDNER / "zusammensetzung_nach_kaverne.json"

R_CM3 = 83.1447          # bar·cm³/(mol·K)
A_W_AUSLEGUNG = 1.0      # Auslegung: Austrittsstrom gesättigt über reinem Wasser (konservativ)
A_W_SOLE = 0.75          # Min-Fall: Wasseraktivität über gesättigter NaCl-Sole (Q-089 Abschn. 6.5, Q-137 Abschn. 3)
N_NORM = 1.01325e5 / (8.314462 * 273.15)   # mol/Nm³ ideales Gas (DIN 1343) = 44,6 mol/Nm³
M_H2O = 18.015           # g/mol
T_KRIT_K = PropsSI("Tcrit", "CO2")

FAELLE = ("rein_min", "rein_max", "gem_min", "gem_max", "gem_max_ohne_stillstand", "gem_max_ab_2_zyklus",
          "rein_min_ab_2_zyklus", "rein_max_ab_2_zyklus", "gem_min_ab_2_zyklus")
AUSLEGUNGSFALL = "gem_max"


# ---- 1) Gegenseitige Löslichkeit CO₂ - Wasser (Spycher et al. 2003, Q-124) ---------------
def _rk_co2(p, T_K):
    """Molvolumen [cm³/mol] von CO₂ nach Redlich-Kwong mit Spycher-Parametern."""
    a, b = 7.54e7 - 4.13e4 * T_K, 27.80
    koeff = [1.0, -R_CM3 * T_K / p, -(R_CM3 * T_K * b / p - a / (p * np.sqrt(T_K)) + b * b),
             -a * b / (p * np.sqrt(T_K))]
    wurzeln = np.roots(koeff)
    wurzeln = np.real(wurzeln[np.abs(np.imag(wurzeln)) < 1e-8])
    wurzeln = wurzeln[wurzeln > b]
    fluessig = T_K < T_KRIT_K and p > PropsSI("P", "T", T_K, "Q", 0, "CO2") / 1e5
    return (wurzeln.min() if fluessig else wurzeln.max()), a, b, fluessig


def loeslichkeit(p, T):
    """Spycher, Pruess & Ennis-King (2003), Geochim. Cosmochim. Acta 67(16), 3015-3031 (Q-124).

    Gültig 12-100 °C, bis 600 bar. Rückgabe: (y_H2O in der CO₂-Phase über reinem
    Wasser, x_CO2 im Wasser) als Molanteile.
    """
    T_K = T + 273.15
    V, a, b, fluessig = _rk_co2(p, T_K)
    log_K_h2o = -2.209 + 3.097e-2 * T - 1.098e-4 * T**2 + 2.048e-7 * T**3
    log_K_co2 = (1.169 + 1.368e-2 * T - 5.380e-5 * T**2 if fluessig
                 else 1.189 + 1.304e-2 * T - 5.446e-5 * T**2)
    Z = p * V / (R_CM3 * T_K)

    def ln_phi(b_k, a_k):
        return (np.log(V / (V - b)) + b_k / (V - b) - 2 * a_k / (R_CM3 * T_K**1.5 * b) * np.log((V + b) / V)
                + a * b_k / (R_CM3 * T_K**1.5 * b * b) * (np.log((V + b) / V) - b / (V + b)) - np.log(Z))
    phi_h2o, phi_co2 = np.exp(ln_phi(18.18, 7.89e7)), np.exp(ln_phi(b, a))
    A = 10**log_K_h2o / (phi_h2o * p) * np.exp((p - 1) * 18.1 / (R_CM3 * T_K))
    B = phi_co2 * p / (55.508 * 10**log_K_co2) * np.exp(-(p - 1) * 32.6 / (R_CM3 * T_K))
    y = (1 - B) / (1 / A - B)
    return y, B * (1 - y)


def wasser_im_co2(p, T, a_w=1.0):
    """Wassersättigung der CO₂-Phase [Molanteil]; a_w = 0,75 über gesättigter Sole."""
    return a_w * loeslichkeit(p, T)[0]


def g_pro_Nm3(y_h2o):
    """Molanteil Wasser -> g Wasser je Nm³ trockenes Gas."""
    return y_h2o / (1 - y_h2o) * N_NORM * M_H2O


def co2_molalitaet(p, T):
    """Gelöstes CO₂ [mol/kg Wasser] - reines Wasser, obere Schranke für Sole."""
    x = loeslichkeit(p, T)[1]
    return 55.508 * x / (1 - x)


# ---- 2) Hydratbildung (Näherung) -----------------------------------------------------------
# CO₂-Hydrat ist nur mit freiem Wasser stabil. Gleichgewichtslinie zwischen den
# Quadrupelpunkten Q1 (≈ 0 °C / 12,6 bar) und Q2 (≈ 9,8 °C / 44,9 bar), darüber
# (flüssiges CO₂) nahezu senkrecht bei ≈ 10 °C. Literaturwerte (Sloan & Koh 2008,
# Clathrate Hydrates of Natural Gases, 3. Aufl.) - NOCH NICHT in der Quellenmatrix,
# vor Verwendung in der Arbeit aufnehmen (Q-015 behandelt Hydrate bei der Injektion).
Q1, Q2 = (0.0, 12.6), (9.8, 44.9)


def T_hydrat(p):
    """Grenztemperatur [°C], unter der bei freiem Wasser CO₂-Hydrat entstehen kann."""
    if p >= Q2[1]:
        return Q2[0] + 0.01 * (p - Q2[1])         # fast senkrecht
    if p <= Q1[1]:
        return Q1[0] - 1.0
    return Q1[0] + (Q2[0] - Q1[0]) * np.log(p / Q1[1]) / np.log(Q2[1] / Q1[1])


# ---- 3) Ergebnis für den Ausspeicherpfad ----------------------------------------------------
def lade(fall=None):
    """Zusammensetzung aus 06 (zusammensetzung_nach_kaverne.json); fall=None -> Auslegungsfall (gem_max).

    Rückgabe: dict mit "feucht" (Molanteile inkl. Water, NOx, Diesel, Öl), "trocken"
    (Molanteile ohne Wasser, alle Stoffe) und "trocken_coolprop" (nur Stoffe mit
    CoolProp-Modell, normiert = Blatt 12 Abschnitt 7 der Mappe). Fälle: siehe FAELLE.
    """
    if not JSON.exists():
        raise FileNotFoundError("zusammensetzung_nach_kaverne.json fehlt - zuerst 06 ausführen.")
    with open(JSON, encoding="utf-8") as f:
        d = json.load(f)
    fall = fall or d["auslegungsfall"]
    if fall not in d["faelle"]:
        raise KeyError(f"Fall {fall!r} unbekannt - vorhanden: {', '.join(d['faelle'])}")
    return d["faelle"][fall]


def _mischungsregeln_ergaenzen(namen):
    """Fehlende binäre Parameter (betrifft COS) durch Lorentz-Berthelot ersetzen."""
    import CoolProp.CoolProp as CP
    for a, b in combinations(namen, 2):
        try:
            CP.AbstractState("HEOS", f"{a}&{b}")
        except ValueError:
            try:
                CP.apply_simple_mixing_rule(CP.get_fluid_param_string(a, "CAS"),
                                            CP.get_fluid_param_string(b, "CAS"), "Lorentz-Berthelot")
            except ValueError:
                pass                                    # schon gesetzt


def gemisch_trocken(fall=None):
    """CoolProp-AbstractState des getrockneten Ausspeichergases (ohne H₂O, NOx und schwere KW).

    Schwere Kohlenwasserstoffe (Diesel, Verdichteröl) liegen unter 1 ppm und
    haben kein CoolProp-Stoffmodell im Gemisch - sie gehen über den KW-Taupunkt
    in die Auslegung von Abscheider/Filter ein, nicht in die Zustandsgleichung.
    NOx (5 ppm) fehlt in CoolProp ebenfalls; in HYSYS als NO bzw. NO₂ ergänzen.
    """
    import CoolProp.CoolProp as CP
    z = lade(fall)["trocken_coolprop"]
    namen = [k for k, x in z.items() if x > 0]
    x = np.array([z[k] for k in namen])
    _mischungsregeln_ergaenzen(namen)
    AS = CP.AbstractState("HEOS", "&".join(namen))
    AS.set_mole_fractions(list(x / x.sum()))
    return AS


if __name__ == "__main__":
    print("Kontrolle Spycher et al. (2003):")
    for p, T in ((100, 25), (100, 50), (200, 50)):
        y, x = loeslichkeit(p, T)
        print(f"  {p} bar / {T} °C: H₂O in CO₂ {1e3*y:.2f}·10⁻³ ({g_pro_Nm3(y):.2f} g/Nm³), "
              f"CO₂ in Wasser {co2_molalitaet(p, T):.2f} mol/kg")
    if JSON.exists():
        z = lade()
        print(f"\nAuslegungsfall {AUSLEGUNGSFALL} (feucht):")
        for k, v in z["feucht"].items():
            print(f"  {k:<18} {1e6*v:12.3f} mol-ppm")
        AS = gemisch_trocken()
        AS.update(__import__("CoolProp").CoolProp.PT_INPUTS, 91e5, 288.15)
        print(f"\nTrockenes Gas bei 91 bar / 15 °C: {AS.rhomass():.1f} kg/m³")
