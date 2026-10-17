# -*- coding: utf-8 -*-
"""
Ausspeichergas - Stoffdatenblatt für den Ausspeicherpfad
============================================================================
Gegenstück zu gemisch_worstcase.py: dort steht, was in die Kaverne geht, hier,
was wieder herauskommt. Die Herleitung rechnet 06_zusammensetzung_nach_kaverne.py
und legt das Ergebnis in zusammensetzung_nach_kaverne.json ab. Der
Ausspeicherpfad importiert nur dieses Modul:

    import ausspeichergas as ag
    AS = ag.gemisch_trocken()          # CoolProp-AbstractState, Auslegungsfall
    y  = ag.wasser_im_co2(p, T)        # Wassersättigung für Abscheider/Trocknung

Übertrag der H₂-Studie Q-089 (UGS für DGMK 2024, Musterkaverne von Uniper) auf CO₂
  Q-089 Abschn. 5 nennt die Quellen von Verunreinigungen in einer Kaverne:
  Verdichteröl (Einspeicherung), Blanket-Reste (Diesel) aus der Solung,
  Restgas des früheren Speichermediums (Erdgas), mikrobiologische Prozesse
  (H₂S, CH₄) und Wasserdampf aus Restsole und feuchten Wänden. Dieselben
  Quellen gelten für CO₂ - die Mengen ändern sich aber mit dem Stoff:

  Wasser        CO₂ löst deutlich mehr Wasser als H₂, und im dichten Zustand
                mehr als im gasförmigen (Minimum nahe dem Phasenwechsel).
                Modell: Spycher, Pruess & Ennis-King (2003) für CO₂-H₂O.
                Auslegung: Austrittsstrom gesättigt über reinem Wasser im
                wasserreichsten Kavernenzustand (konservativ). Q-089 setzt bei
                voller Kaverne nur 75 % an (gesättigte Sole) - als Vergleich.
  Diesel/Öl     dichtes CO₂ ist ein starkes Lösungsmittel für Kohlenwasser-
                stoffe (Extraktionsmittel, Q-003 Kap. 8.2.2.1) -> Annahme:
                Restblanket und Verdichteröl lösen sich vollständig.
                In H₂ dagegen sättigungsbegrenzt (Q-089 Tab. 13).
  Resterdgas    gleiches Fingervolumen wie Q-089 Abschn. 6.3 (0,2-0,4 % des
                Kavernenvolumens), aber dichtes CO₂ enthält je m³ etwa 2,5-mal
                so viele Mole wie H₂ bei 210 bar -> CH₄-Anteil ~0,2 % statt 0,5 %.
  Mikrobiologie Sulfatreduzierer und Methanbildner brauchen einen Elektronen-
                donator - in H₂-Kavernen ist das der Wasserstoff selbst. Im
                Gemisch stehen nur 0,5 % H₂ zur Verfügung, in reinem CO₂ keiner;
                saure Sole (CO₂ gelöst, pH ~3-4) und hoher Salzgehalt hemmen
                zusätzlich (Q-089 Abschn. 6.4, Q-019 AP 3). Übernommen als
                Worst Case: H₂S 10 ppm (Q-089; = zulässiger Wert nach Q-030
                Kap. 1.4) und CH₄ + 50 ppm aus 4 H₂ + CO₂ -> CH₄ + 2 H₂O
                (nur Gemisch; verbraucht 200 ppm H₂).

Einheiten: bar, °C, Molanteile [-], ppm = mol-ppm, g/Nm³ bezogen auf trockenes Gas.
"""
import json
from pathlib import Path

import numpy as np
from CoolProp.CoolProp import PropsSI

ORDNER = Path(__file__).resolve().parent
JSON = ORDNER / "zusammensetzung_nach_kaverne.json"

R_CM3 = 83.1447          # bar·cm³/(mol·K)
A_W_AUSLEGUNG = 1.0      # Auslegung: Austrittsstrom gesättigt über reinem Wasser (konservativ)
A_W_SOLE = 0.75          # Vergleich: Wasseraktivität über gesättigter NaCl-Sole (Q-089 Abschn. 6.5, dort [6])
N_NORM = 1.01325e5 / (8.314462 * 273.15)   # mol/Nm³ ideales Gas (DIN 1343) = 44,6 mol/Nm³
M_H2O = 18.015           # g/mol
T_KRIT_K = PropsSI("Tcrit", "CO2")


# ---- 1) Gegenseitige Löslichkeit CO₂ - Wasser (Spycher et al. 2003) ----------------------
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
    """Spycher, Pruess & Ennis-King (2003), Geochim. Cosmochim. Acta 67(16), 3015-3031.

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
# (flüssiges CO₂) nahezu senkrecht bei ≈ 10 °C. Literaturwerte (Sloan & Koh 2008),
# NOCH NICHT in der Quellenmatrix - vor Verwendung in der Arbeit belegen.
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
    """Zusammensetzung aus 06 (zusammensetzung_nach_kaverne.json); fall=None -> Auslegungsfall."""
    if not JSON.exists():
        raise FileNotFoundError("zusammensetzung_nach_kaverne.json fehlt - zuerst 06 ausführen.")
    with open(JSON, encoding="utf-8") as f:
        d = json.load(f)
    return d["faelle"][fall or d["auslegungsfall"]]


def gemisch_trocken(fall=None):
    """CoolProp-AbstractState des getrockneten Ausspeichergases (ohne H₂O, ohne Spuren-KW).

    Schwere Kohlenwasserstoffe (Diesel, Verdichteröl) liegen im ppm-Bereich und
    haben kein CoolProp-Stoffmodell im Gemisch - sie gehen über den KW-Taupunkt
    in die Auslegung von Abscheider/Filter ein, nicht in die Zustandsgleichung.
    """
    import CoolProp.CoolProp as CP
    z = lade(fall)["trocken_coolprop"]
    namen = [k for k, x in z.items() if x > 0]
    x = np.array([z[k] for k in namen])
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
        print(f"\nAuslegungsfall {json.load(open(JSON, encoding='utf-8'))['auslegungsfall']}:")
        for k, v in z["feucht"].items():
            print(f"  {k:<16} {100*v:9.5f} mol-%")
