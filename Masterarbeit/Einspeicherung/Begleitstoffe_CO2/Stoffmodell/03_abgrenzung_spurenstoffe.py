# -*- coding: utf-8 -*-
"""
Schritt 0c - Abgrenzung: welche Begleitstoffe werden gerechnet, welche nicht?
============================================================================
Frage: Das Stoffmodell führt CO2 und fünf nicht kondensierbare Begleitstoffe
(N2, Ar, CH4, H2, CO). Ein spezifikationskonformer CO2-Strom enthält darüber
hinaus Spurenstoffe im ppm-Bereich. Ist es zulässig, diese wegzulassen?

Das Skript belegt die Abgrenzung mit drei Prüfungen statt mit einer Behauptung:

  A  Was kann CoolProp überhaupt? Für jeden Spurenstoff wird geprüft, ob der
     Reinstoff in der HEOS-Datenbank existiert und ob das Binärpaar mit CO2
     rechenbar ist. Ergebnis: rund die Hälfte der in ISO 27913 Tabelle A.2
     genannten Stoffe ist gar nicht darstellbar. Ein vollständiges Gemisch
     ist in CoolProp also nicht baubar, nur ein halbvollständiges.

  B  Wie groß wäre der Fehler? Das Worst-Case-Gemisch (6 Komponenten) wird
     gegen dasselbe Gemisch plus H2O, O2 und H2S (9 Komponenten) gerechnet.
     Verglichen werden Blasen- und Taudruck über QT-Flash. Die Abweichung
     ist gegen die Modellunsicherheit der Phasengrenze von +-3 bar aus
     02_validierung_stoffmodelle.py zu sehen.

  C  Gilt das pauschal? Nein. Gegenprobe mit Kohlenwasserstoffen: dieselbe
     Konzentration wirkt je nach Kettenlänge völlig verschieden. Deshalb
     begrenzt ISO 27913 Tabelle A.2 die Aliphaten ab C3 nicht über eine
     ppm-Zahl, sondern über einen Kohlenwasserstoff-Taupunkt < -20 °C
     (Tabelle A.1 Fußnote d: schwere Kohlenwasserstoffe ab C3 dürfen den
     Taupunkt nicht unter den von reinem CO2 verschieben).

Grenzwerte der Spurenstoffe in B: DVGW C 260 (A) Tabelle 5 - H2O 30 ppm-mol,
O2 40 ppm-mol, H2S 5 ppm-mol. Das sind die drei reaktiven Spurenstoffe mit
den höchsten Grenzwerten, die CoolProp tragen kann.

Methodischer Hinweis zu A: "rechenbar" heißt nicht "angepasst". Fehlt eine
Departure-Funktion, rechnet CoolProp mit der geschätzten Mischungsregel
(F = 0), wie im Kopf von gemisch_worstcase.py für CO2-H2 und CO2-CO erläutert.
Die Zahlen aus C sind deshalb Größenordnung und Richtung, kein Messwert.

Ergebnis: Konsolenausgabe (drei Tabellen), abb_abgrenzung_spurenstoffe.png
          und abgrenzung_spurenstoffe.json (-> Dokumentation)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import CoolProp
import CoolProp.CoolProp as CP

import json
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parents[1]           # Begleitstoffe_CO2
sys.path.insert(0, str(ORDNER / "Grundlagen"))         # gemisch_worstcase
ABB = ORDNER / "Abbildungen"                           # Abbildungen und Ergebnisdateien

import gemisch_worstcase as gw

print(f"CoolProp-Version: {CoolProp.__version__}")

# Modellunsicherheit der Phasengrenze aus 02_validierung_stoffmodelle.py
UNSICHERHEIT_BAR = 3.0

# Reaktive Spurenstoffe, die CoolProp tragen kann (DVGW C 260 Tabelle 5)
SPUREN_B = [("Water", 30.0), ("Oxygen", 40.0), ("HydrogenSulfide", 5.0)]   # ppm-mol


# ---- Hilfsfunktionen --------------------------------------------------------
def molanteile(zusatz=()):
    """Molanteile des Worst-Case-Gemischs, optional + Spurenstoffe [ppm-mol].

    Die Spurenstoffe werden ergänzt und anschließend wird auf die Summe 1
    normiert; CO2 sinkt dadurch geringfügig (95,0000 -> 94,9929 mol-%).
    """
    namen = list(gw.KOMPONENTEN)
    x = [k[2] / 100.0 for k in gw.ZUSAMMENSETZUNG]
    for stoff, ppm in zusatz:
        namen.append(stoff)
        x.append(ppm * 1e-6)
    s = sum(x)
    return namen, [xi / s for xi in x]


def zustand(namen, x):
    AS = CP.AbstractState("HEOS", "&".join(namen))
    AS.set_mole_fractions(x)
    return AS


def p_sat(namen, x, T_C, Q):
    """Blasendruck (Q=0) bzw. Taudruck (Q=1) [bar] bei T [°C], None bei Abbruch."""
    try:
        AS = zustand(namen, x)
        AS.update(CP.QT_INPUTS, Q, T_C + 273.15)
        return AS.p() / 1e5
    except Exception:
        return None


def taupunkt(namen, x, p_bar):
    """Taupunkt [°C] bei festem Druck (PQ-Flash), None bei Abbruch."""
    try:
        AS = zustand(namen, x)
        AS.update(CP.PQ_INPUTS, p_bar * 1e5, 1.0)
        return AS.T() - 273.15
    except Exception:
        return None


export = {"quelle": "03_abgrenzung_spurenstoffe.py",
          "unsicherheit_phasengrenze_bar": UNSICHERHEIT_BAR}

# ---- A) Was kann CoolProp? --------------------------------------------------
# (Anzeigename, CoolProp-Name, Gruppe nach ISO 27913 Tabelle A.1/A.2)
KANDIDATEN = [
    ("H2O",              "Water",            "reaktiv"),
    ("O2",               "Oxygen",           "reaktiv"),
    ("H2S",              "HydrogenSulfide",  "reaktiv"),
    ("SO2",              "SulfurDioxide",    "reaktiv"),
    ("COS",              "CarbonylSulfide",  "reaktiv"),
    ("NOx (Probe N2O)",  "NitrousOxide",     "reaktiv"),
    ("NH3",              "Ammonia",          "reaktiv"),
    ("Methanol",         "Methanol",         "organisch"),
    ("Ethanol",          "Ethanol",          "organisch"),
    ("n-Butan (C4)",     "n-Butane",         "organisch"),
    ("n-Octan (C8)",     "n-Octane",         "organisch"),
    ("n-Decan (C10)",    "n-Decane",         "organisch"),
    ("Benzol (BTEX)",    "Benzene",          "organisch"),
    ("Toluol (BTEX)",    "Toluene",          "organisch"),
    ("MEA (Amin)",       "MEA",              "organisch"),
    ("MDEA (Amin)",      "MDEA",             "organisch"),
    ("MEG (Glykol)",     "EthyleneGlycol",   "organisch"),
    ("TEG (Glykol)",     "TEG",              "organisch"),
    ("HCN",              "HydrogenCyanide",  "weitere"),
    ("Quecksilber",      "Mercury",          "weitere"),
]

print("\nA) Welche Spurenstoffe kann CoolProp (HEOS) im Gemisch mit CO2 rechnen?")
print(f"   {'Stoff':<17} {'CoolProp-Name':<17} {'Gruppe':<10} {'Reinstoff':<10} "
      f"{'mit CO2':<9} Befund")
tab_a, n_ja = [], 0
for anzeige, name, gruppe in KANDIDATEN:
    try:
        CP.PropsSI("M", name)
        rein = True
    except Exception:
        rein = False
    if not rein:
        ja, befund = False, "kein Reinstoff in der HEOS-Datenbank"
    else:
        try:
            AS = CP.AbstractState("HEOS", f"CO2&{name}")
            AS.set_mole_fractions([0.9999, 0.0001])
            AS.update(CP.QT_INPUTS, 0.0, 273.15)       # Blasendruck bei 0 °C
            ja, befund = True, f"rechenbar, p = {AS.p()/1e5:.3f} bar"
        except Exception as e:
            ja, befund = False, "kein Binaerpaar mit CO2 hinterlegt"
    n_ja += int(ja)
    print(f"   {anzeige:<17} {name:<17} {gruppe:<10} {'ja' if rein else 'nein':<10} "
          f"{'ja' if ja else 'nein':<9} {befund}")
    tab_a.append({"stoff": anzeige, "coolprop": name, "gruppe": gruppe,
                  "reinstoff": rein, "mit_co2": ja, "befund": befund})
print(f"   -> {n_ja} von {len(KANDIDATEN)} Stoffen rechenbar, "
      f"{len(KANDIDATEN) - n_ja} nicht. Ein vollstaendiges Gemisch ist nicht baubar.")
export["A_darstellbarkeit"] = tab_a

# ---- B) Wie groß waere der Fehler? -----------------------------------------
n6, x6 = molanteile()
n9, x9 = molanteile(SPUREN_B)
M6, M9 = zustand(n6, x6).molar_mass() * 1000, zustand(n9, x9).molar_mass() * 1000

print("\nB) Worst-Case-Gemisch (6 Komponenten) gegen dasselbe + H2O/O2/H2S (9 Komponenten)")
print(f"   Zusatz: " + ", ".join(f"{s} {ppm:.0f} ppm-mol" for s, ppm in SPUREN_B)
      + "   (DVGW C 260 Tabelle 5)")
print(f"   CO2 sinkt durch die Normierung von {x6[0]*100:.4f} auf {x9[0]*100:.4f} mol-%")
print(f"   Molare Masse {M6:.5f} -> {M9:.5f} g/mol  ({M9-M6:+.5f})")
print(f"\n   {'T [°C]':>7} {'Blase 6K':>10} {'Blase 9K':>10} {'Delta':>9}"
      f" {'Tau 6K':>10} {'Tau 9K':>10} {'Delta':>9}")
# Temperaturbereich: Der Vergleich kann nicht beliebig weit nach oben laufen.
#   untere Grenze  Tripelpunkt von reinem CO2 (-56,6 °C); darunter kennt die
#                  Zustandsgleichung keine feste Phase (siehe gemisch_worstcase.py)
#   obere Grenze   Oberhalb des Cricondentherms (28,1 °C) gibt es ueberhaupt
#                  keine Phasengrenze mehr, das Gemisch ist bei jedem Druck
#                  einphasig. Schon ab etwa 10 K unter dem kritischen Punkt
#                  (28,0 °C) konvergiert der QT-Flash unzuverlaessig, wie im
#                  Kopf von gemisch_worstcase.phasengrenze() beschrieben.
# Die Prozesskette laeuft zwar bis 95 °C (T_MAX_STUFE), dort liegt aber kein
# Zweiphasengebiet mehr - ein Vergleich von Blasen- und Taudruck waere dort
# nicht ungenau, sondern undefiniert.
# Die obere Grenze gilt fuer BEIDE Gemische gleich: Der QT-Flash liefert fuer
# 6 und 9 Komponenten bis 18 °C Ergebnisse und versagt ab 20 °C bei beiden
# (geprueft am 06.10.2026). Sie ist also kein Argument fuer oder gegen eines der
# Modelle. Die Begruendung fuer das 6-Komponenten-Modell liefern Teil A
# (nicht darstellbar) und Teil B (nicht relevant).
T_PUNKTE = [-50.0, -40.0, -30.0, -20.0, -10.0, 0.0, 10.0, 15.0]
tab_b, d_max = [], 0.0
for T in T_PUNKTE:
    b6, b9 = p_sat(n6, x6, T, 0.0), p_sat(n9, x9, T, 0.0)
    d6, d9 = p_sat(n6, x6, T, 1.0), p_sat(n9, x9, T, 1.0)
    db = (b9 - b6) if (b6 and b9) else None
    dd = (d9 - d6) if (d6 and d9) else None
    for d in (db, dd):
        if d is not None:
            d_max = max(d_max, abs(d))
    f = lambda v, nk=4: f"{v:.{nk}f}" if v is not None else "n/a"
    print(f"   {T:>7.1f} {f(b6):>10} {f(b9):>10} {f(db):>9}"
          f" {f(d6):>10} {f(d9):>10} {f(dd):>9}")
    tab_b.append({"T_C": T, "blase_6K": b6, "blase_9K": b9, "d_blase": db,
                  "tau_6K": d6, "tau_9K": d9, "d_tau": dd})
print(f"\n   Groesste Abweichung {d_max:.4f} bar gegen {UNSICHERHEIT_BAR:.0f} bar "
      f"Modellunsicherheit -> Faktor {UNSICHERHEIT_BAR/d_max:.0f}")
print("   Die drei reaktiven Spurenstoffe sind damit thermodynamisch vernachlaessigbar.")
export["B_vergleich"] = {"zusatz_ppm": {s: p for s, p in SPUREN_B},
                         "M_6K": M6, "M_9K": M9, "punkte": tab_b,
                         "max_abweichung_bar": d_max}

# ---- C) Gegenprobe Kohlenwasserstoffe --------------------------------------
P_TAU = 30.0        # bar, Netzuebergabe Szenario 2
VARIANTEN = [("ohne Kohlenwasserstoff", None, 0.0),
             ("n-Butan (C4)",  "n-Butane", 1200.0),
             ("n-Decan (C10)", "n-Decane", 1200.0),
             ("n-Butan (C4)",  "n-Butane", 10000.0),
             ("n-Decan (C10)", "n-Decane", 10000.0)]

print(f"\nC) Gegenprobe: Taupunkt bei {P_TAU:.0f} bar, je nach Kettenlaenge")
print("   1200 ppm-mol = Grenzwert Porthos fuer Aliphaten C2-C10")
print("   10000 ppm-mol = 1 mol-%, Grenzwert ISO 27913 Tabelle A.2 (dichte Phase)")
print(f"\n   {'Variante':<26} {'Zusatz':>14} {'Taupunkt':>12}")
tab_c, T_basis = [], None
for label, stoff, ppm in VARIANTEN:
    nn, xx = molanteile() if stoff is None else molanteile([(stoff, ppm)])
    Tt = taupunkt(nn, xx, P_TAU)
    if stoff is None:
        T_basis = Tt
    zus = "-" if stoff is None else (f"{ppm:.0f} ppm" if ppm < 10000 else f"{ppm/1e4:.0f} mol-%")
    dT = "" if (Tt is None or T_basis is None or stoff is None) else f"  ({Tt-T_basis:+.1f} K)"
    print(f"   {label:<26} {zus:>14} {('n/a' if Tt is None else f'{Tt:+8.2f} °C'):>12}{dT}")
    tab_c.append({"variante": label, "stoff": stoff, "ppm_mol": ppm, "taupunkt_C": Tt})
print("   -> Dieselbe Konzentration wirkt je nach Kettenlaenge voellig verschieden.")
print("      Deshalb begrenzt ISO 27913 die Aliphaten ab C3 ueber eine Taupunkt-")
print("      bedingung (< -20 °C) und nicht ueber eine ppm-Zahl.")
export["C_kohlenwasserstoffe"] = {"p_bar": P_TAU, "varianten": tab_c}

# ---- Abbildung --------------------------------------------------------------
fig, ax1 = plt.subplots(1, 1, figsize=(8.0, 5.4))

# Achsen wie im Phasendiagramm 01 (-80..100 °C, 0..130 bar), damit die
# Abbildung neben Abbildung 1 der Dokumentation lesbar bleibt.
T_MIN_AX, T_MAX_AX, P_MIN_AX, P_MAX_AX = -80.0, 100.0, 0.0, 130.0

pg = gw.phasengrenze()          # vollstaendige Huellkurve des Worst Case (6 Komponenten)
ax1.plot(pg["T_tau"], pg["p_tau"], "-", color="#1f4e79", lw=2.0,
         label="6 Komponenten (Modell)")
ax1.plot(pg["T_blase"], pg["p_blase"], "-", color="#1f4e79", lw=2.0)

# 9 Komponenten: build_phase_envelope bricht fuer dieses Gemisch ab, deshalb
# QT-Raster ueber den Bereich, in dem der Flash zuverlaessig konvergiert.
# Q=0 traegt bis -55 °C, Q=1 erst ab etwa -42 °C; darunter konvergiert der
# Flash auf der Taulinie auf eine unphysikalische Loesung.
for Q, T_von in ((0.0, -55.0), (1.0, -42.0)):
    T_KURVE = np.arange(T_von, 18.1, 1.0)
    pp = [p_sat(n9, x9, T, Q) for T in T_KURVE]
    T_ok = [T for T, p in zip(T_KURVE, pp) if p is not None]
    p_ok = [p for p in pp if p is not None]
    ax1.plot(T_ok, p_ok, "--", color="#d1495b", lw=1.6,
             label="9 Komponenten (+ H₂O/O₂/H₂S)" if Q == 0 else None)

T_cct, p_cct = pg["cricondentherm"]
ax1.plot([T_cct], [p_cct], "o", color="#1f4e79", ms=6, zorder=6)
ax1.annotate(f"Cricondentherm {T_cct:.1f} °C\ndarueber keine Phasengrenze mehr",
             (T_cct, p_cct), textcoords="offset points", xytext=(26, -4), fontsize=8.5,
             arrowprops=dict(arrowstyle="-", color="#555555", lw=0.7))

ax1.set_xlim(T_MIN_AX, T_MAX_AX)
ax1.set_ylim(P_MIN_AX, P_MAX_AX)
ax1.set_xlabel("Temperatur [°C]")
ax1.set_ylabel("Druck [bar]")
ax1.set_title("Zweiphasengebiet mit und ohne reaktive Spurenstoffe")
ax1.grid(alpha=0.3)
ax1.legend(loc="upper left", fontsize=9)

fig.tight_layout()
fig.savefig(ABB / "abb_abgrenzung_spurenstoffe.png", dpi=175)
print(f"\nAbbildung: {ABB / 'abb_abgrenzung_spurenstoffe.png'}")

with open(ABB / "abgrenzung_spurenstoffe.json", "w", encoding="utf-8") as f:
    json.dump(export, f, ensure_ascii=False, indent=1)
print(f"Ergebnisse: {ABB / 'abgrenzung_spurenstoffe.json'}")
