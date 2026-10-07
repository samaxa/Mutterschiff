# -*- coding: utf-8 -*-
"""
Schritt 0d - Sensitivität: Wie stark hängt die Phasengrenze von der Zusammensetzung ab?
============================================================================
Frage: Das Worst-Case-Gemisch hat sechs Komponenten, und die Aufteilung der
Begleitstoffe ist zum Teil eine eigene Annahme. Wären die Ergebnisse mit einer
anderen Aufteilung oder mit mehr Komponenten andere?

Das Skript prüft das mit drei Rechnungen:

  A  Stoffpaare: Wie gut sind die Paare im Modell beschrieben? Für das Gemisch
     mit sechs und mit neun Komponenten (+ H2O, O2, H2S) wird je Stoffpaar aus
     CoolProp ausgelesen, ob eine an Messdaten angepasste Departure-Funktion,
     nur angepasste reduzierende Parameter oder gar keine Anpassung vorliegt.
     Ergebnis: Die zusätzlichen Paare sind überwiegend schwächer beschrieben.
     Mehr Komponenten erhöhen die Genauigkeit also nicht.

  B  Aufteilung: Die freien 4,4 mol-% (5 % minus H2 0,5 % und CO 0,1 %) werden
     vollständig einem Stoff zugeordnet (nur N2, nur Ar, nur CH4). Dazu ein
     Vergleichsfall nach Porthos mit 4 mol-% Begleitstoffen und das Gemisch
     mit neun Komponenten (Zusatz wie in 03_abgrenzung_spurenstoffe.py).

  C  Abbildung: alle Phasengrenzen in einem p-T-Diagramm, mit dem
     Mindestabstand (Cricondenbar + 3 bar) und dem Betriebsdruck 91 bar.

Rechenweg der Phasengrenze
  Hüllkurve mit build_phase_envelope (wie gemisch_worstcase.phasengrenze()).
  Verwendet werden nur Punkte oberhalb des CO2-Tripelpunkts und unter 200 bar;
  darunter bzw. darüber läuft die Rechnung in einen unphysikalischen Ast.
  Blasen- und Taudruck bei 15 °C kommen aus dem QT-Flash. Für die Abbildung
  wird die Hüllkurve bis 10 K unter dem kritischen Punkt mit QT-Flashes im
  1-K-Raster verdichtet (näher am kritischen Punkt konvergiert der Flash
  nicht zuverlässig, siehe gemisch_worstcase.py).

Ergebnis: Konsolenausgabe (zwei Tabellen), abb_sensitivitaet_zusammensetzung.png
          und sensitivitaet_zusammensetzung.json
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import CoolProp
import CoolProp.CoolProp as CP

import itertools
import json
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parents[1]           # Begleitstoffe_CO2
sys.path.insert(0, str(ORDNER / "Grundlagen"))         # gemisch_worstcase
ABB = ORDNER / "Abbildungen"                           # Abbildungen und Ergebnisdateien

import gemisch_worstcase as gw

print(f"CoolProp-Version: {CoolProp.__version__}")

UNSICHERHEIT_BAR = 3.0        # Mindestabstand zur Phasengrenze (02_validierung_stoffmodelle.py)
P_BETRIEB = 91.0              # bar, Druck vor den Pumpen (S1 Netzübergabe, S2 nach Kühler)
T_TRIPEL = CP.PropsSI("Ttriple", "CO2")

# Reaktive Spurenstoffe wie in 03_abgrenzung_spurenstoffe.py (DVGW C 260 Tabelle 5)
SPUREN = [("Water", 30.0), ("Oxygen", 40.0), ("HydrogenSulfide", 5.0)]      # ppm-mol

NAMEN6 = list(gw.KOMPONENTEN)      # CO2, Nitrogen, Argon, Methane, Hydrogen, CarbonMonoxide
ANZEIGE = {"CO2": "CO₂", "Nitrogen": "N₂", "Argon": "Ar", "Methane": "CH₄",
           "Hydrogen": "H₂", "CarbonMonoxide": "CO", "Water": "H₂O", "Oxygen": "O₂",
           "HydrogenSulfide": "H₂S"}

# ---- A) Stoffpaare ----------------------------------------------------------
def paar(a, b):
    """Art der Beschreibung eines Stoffpaars in CoolProp und Quelle der Parameter."""
    ca, cb = (CP.get_fluid_param_string(s, "CAS") for s in (a, b))
    for c1, c2 in ((ca, cb), (cb, ca)):            # Reihenfolge ist in CoolProp festgelegt
        try:
            F = float(CP.get_mixture_binary_pair_data(c1, c2, "F"))
            par = [float(CP.get_mixture_binary_pair_data(c1, c2, k))
                   for k in ("betaT", "gammaT", "betaV", "gammaV")]
            quelle = CP.get_mixture_binary_pair_data(c1, c2, "BibTeX")
            break
        except ValueError:
            continue
    else:
        return "nicht hinterlegt", ""
    if F != 0:
        return "Departure-Funktion", quelle
    if all(abs(v - 1.0) < 1e-12 for v in par):
        return "ohne Anpassung", quelle
    return "reduzierende Parameter", quelle


ARTEN = ["Departure-Funktion", "reduzierende Parameter", "ohne Anpassung", "nicht hinterlegt"]
namen9 = NAMEN6 + [s for s, _ in SPUREN]
tab_a = []
for a, b in itertools.combinations(namen9, 2):
    art, quelle = paar(a, b)
    tab_a.append({"paar": f"{ANZEIGE[a]}–{ANZEIGE[b]}", "art": art, "quelle": quelle,
                  "im_6K_modell": a in NAMEN6 and b in NAMEN6})

print("\nA) Beschreibung der Stoffpaare in CoolProp (HEOS)")
print(f"   {'Beschreibung':<26} {'6 Komp.':>8} {'zusätzlich bei 9 Komp.':>24}")
zaehlung = {}
for art in ARTEN:
    n6 = sum(1 for t in tab_a if t["art"] == art and t["im_6K_modell"])
    nz = sum(1 for t in tab_a if t["art"] == art and not t["im_6K_modell"])
    zaehlung[art] = {"sechs": n6, "zusaetzlich": nz}
    print(f"   {art:<26} {n6:>8} {nz:>24}")
n6 = sum(z["sechs"] for z in zaehlung.values())
nz = sum(z["zusaetzlich"] for z in zaehlung.values())
print(f"   {'Summe':<26} {n6:>8} {nz:>24}")
print("   Zusätzliche Paare ohne Anpassung: "
      + ", ".join(t["paar"] for t in tab_a if t["art"] == "ohne Anpassung" and not t["im_6K_modell"]))


# ---- B) Phasengrenze der Varianten -------------------------------------------
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


def phasengrenze(namen, x):
    """Hüllkurve einer Zusammensetzung: Tau- und Blasenlinie [°C, bar] und Kennpunkte."""
    AS = zustand(namen, x)
    AS.build_phase_envelope("")
    PE = AS.get_phase_envelope_data()
    T, p, Q = np.array(PE.T), np.array(PE.p) / 1e5, np.array(PE.Q)
    ok = (T >= T_TRIPEL) & (p < 200.0)                # ohne Feststoff, ohne Hochdruckast
    T, p, Q = T[ok] - 273.15, p[ok], Q[ok]
    tau, blase = Q > 0.5, Q < 0.5
    i_k = int(np.argmax(blase))                       # erster Punkt der Blasenlinie
    krit = (0.5 * (T[i_k - 1] + T[i_k]), 0.5 * (p[i_k - 1] + p[i_k]))
    i_p = int(np.argmax(p))

    def verdichten(Th, ph, Qv):
        """Bis 10 K unter dem kritischen Punkt QT-Flash im 1-K-Raster, darüber Hüllkurve."""
        T_schnitt = krit[0] - 10.0
        o = np.argsort(Th)
        Th, ph = Th[o], ph[o]
        Tr, pr = [], []
        for Tc in np.arange(-20.0, T_schnitt, 1.0):
            ps = p_sat(namen, x, Tc, Qv)
            # Kontrolle gegen die Hüllkurve: falsche Flash-Lösungen verwerfen
            if ps is not None and abs(ps - np.interp(Tc, Th, ph)) < 1.5:
                Tr.append(Tc)
                pr.append(ps)
        nah = Th >= T_schnitt
        return np.concatenate([Tr, Th[nah]]), np.concatenate([pr, ph[nah]])

    T_tau, p_tau = verdichten(T[tau], p[tau], 1.0)
    T_bl, p_bl = verdichten(T[blase], p[blase], 0.0)

    def bei_15(Qv, Tl, pl):
        """Sättigungsdruck bei 15 °C: QT-Flash, sonst Interpolation auf der Linie."""
        ps = p_sat(namen, x, 15.0, Qv)
        o = np.argsort(Tl)
        p_linie = float(np.interp(15.0, Tl[o], pl[o]))
        return ps if ps is not None and abs(ps - p_linie) < 1.5 else p_linie

    return {"T_tau": T_tau, "p_tau": p_tau, "T_blase": T_bl, "p_blase": p_bl,
            "krit": krit, "cricondenbar": (T[i_p], p[i_p]),
            "p_blase15": bei_15(0.0, T_bl, p_bl), "p_tau15": bei_15(1.0, T_tau, p_tau)}


def mit_spuren(x6):
    x = list(x6) + [ppm * 1e-6 for _, ppm in SPUREN]
    s = sum(x)
    return [xi / s for xi in x]


X_BASIS = list(gw.MOLANTEILE)
#            Name                               CO2    N2     Ar     CH4    H2       CO
VARIANTEN = [
    ("Worst-Case-Gemisch (gewählt)",   NAMEN6, X_BASIS),
    ("4,4 % nur N₂",                   NAMEN6, [0.95, 0.044, 0.0,   0.0,   0.005,   0.001]),
    ("4,4 % nur Ar",                   NAMEN6, [0.95, 0.0,   0.044, 0.0,   0.005,   0.001]),
    ("4,4 % nur CH₄",                  NAMEN6, [0.95, 0.0,   0.0,   0.044, 0.005,   0.001]),
    # Porthos: N2 2,4 / Ar 0,4 / CH4 1,0 / CO 750 ppm; H2 als Rest bis zur Summengrenze 4 %
    ("Vergleichsfall Porthos (4 %)",   NAMEN6, [0.96, 0.024, 0.004, 0.01,  0.00125, 0.00075]),
    ("9 Komponenten (+ H₂O, O₂, H₂S)", namen9, mit_spuren(X_BASIS)),
]

print("\nB) Phasengrenze der Varianten")
print(f"   {'Variante':<32} {'krit. Punkt':>18} {'Cricondenbar':>18} "
      f"{'Blase 15°C':>11} {'Tau 15°C':>9} {'91 bar liegt':>13}")
erg = {}
for name, namen, x in VARIANTEN:
    nn = [n for n, xi in zip(namen, x) if xi > 0]
    xx = [xi for xi in x if xi > 0]
    try:
        pg = phasengrenze(nn, xx)
    except Exception:
        # Für 9 Komponenten bricht build_phase_envelope ab. Dann wie in
        # 03_abgrenzung_spurenstoffe.py nur QT-Flashes; sie liefern bis 18 °C Ergebnisse,
        # kritischer Punkt und Cricondenbar sind so nicht bestimmbar.
        raster = np.arange(-20.0, 18.5, 1.0)
        linie = {}
        for Qv in (0.0, 1.0):
            pkt = [(Tc, p_sat(nn, xx, Tc, Qv)) for Tc in raster]
            linie[Qv] = (np.array([Tc for Tc, ps in pkt if ps is not None]),
                         np.array([ps for Tc, ps in pkt if ps is not None]))
        pg = {"krit": (np.nan, np.nan), "cricondenbar": (np.nan, np.nan),
              "T_tau": linie[1.0][0], "p_tau": linie[1.0][1],
              "T_blase": linie[0.0][0], "p_blase": linie[0.0][1],
              "p_blase15": p_sat(nn, xx, 15.0, 0.0) or np.nan,
              "p_tau15": p_sat(nn, xx, 15.0, 1.0) or np.nan}
    erg[name] = pg
    if np.isnan(pg["cricondenbar"][1]):
        print(f"   {name:<32} {'nicht bestimmbar':>18} {'nicht bestimmbar':>18} "
              f"{pg['p_blase15']:7.1f} bar {pg['p_tau15']:5.1f} bar {'–':>13}")
        continue
    reserve = P_BETRIEB - pg["cricondenbar"][1]
    print(f"   {name:<32} {pg['krit'][0]:6.1f} °C/{pg['krit'][1]:5.1f} bar "
          f"{pg['cricondenbar'][0]:6.1f} °C/{pg['cricondenbar'][1]:5.1f} bar "
          f"{pg['p_blase15']:7.1f} bar {pg['p_tau15']:5.1f} bar {reserve:7.1f} bar über")

basis = erg[VARIANTEN[0][0]]
neun = erg[VARIANTEN[-1][0]]
print(f"\n   9 gegen 6 Komponenten bei 15 °C: Blasendruck {neun['p_blase15'] - basis['p_blase15']:+.3f} bar, "
      f"Taudruck {neun['p_tau15'] - basis['p_tau15']:+.3f} bar")
p_grenze = basis["cricondenbar"][1] + UNSICHERHEIT_BAR
cb = [pg["cricondenbar"][1] for pg in erg.values() if not np.isnan(pg["cricondenbar"][1])]
print(f"\n   Cricondenbar aller Varianten: {min(cb):.1f} bis {max(cb):.1f} bar")
print(f"   Mindestdruck (Cricondenbar gewählt + {UNSICHERHEIT_BAR:.0f} bar): {p_grenze:.1f} bar")
print(f"   Ungünstigste Variante liegt {max(cb) - basis['cricondenbar'][1]:+.1f} bar über dem "
      f"gewählten Gemisch, {P_BETRIEB - max(cb):.1f} bar unter dem Betriebsdruck.")

# ---- C) Abbildung -------------------------------------------------------------
ROT, BLAU, GRAU, GRUEN, ORANGE, VIOLETT = "#CA220E", "#164a73", "#666666", "#007335", "#a3480b", "#5b2a86"
stil = {
    "Worst-Case-Gemisch (gewählt)":   dict(color=ROT, lw=2.6, ls="-", zorder=5),
    "4,4 % nur N₂":                   dict(color=BLAU, lw=1.6, ls="--", zorder=3),
    "4,4 % nur Ar":                   dict(color=ORANGE, lw=1.6, ls="-.", zorder=3),
    "4,4 % nur CH₄":                  dict(color=GRAU, lw=1.6, ls=":", zorder=3),
    "Vergleichsfall Porthos (4 %)":   dict(color=VIOLETT, lw=1.6, ls="-", zorder=4),
    "9 Komponenten (+ H₂O, O₂, H₂S)": dict(color="black", lw=1.1, ls=(0, (1, 2.5)), zorder=6),
}

fig, ax = plt.subplots(figsize=(8.5, 6.2))
T_s = np.linspace(273.15 - 5, CP.PropsSI("Tcrit", "CO2"), 120)
ax.plot(T_s - 273.15, [CP.PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_s],
        color="#00304F", lw=1.4, label="reines CO₂ (Span-Wagner)")
for name, pg in erg.items():
    if len(pg["T_blase"]) == 0:
        continue
    if np.isnan(pg["cricondenbar"][1]):               # nur QT-Raster: zwei getrennte Linien
        ax.plot(pg["T_tau"], pg["p_tau"], label=name + ", bis 18 °C", **stil[name])
        ax.plot(pg["T_blase"], pg["p_blase"], **stil[name])
        continue
    # geschlossene Hüllkurve: Taulinie aufsteigend, Blasenlinie zurück
    ax.plot(np.concatenate([pg["T_tau"], pg["T_blase"][::-1]]),
            np.concatenate([pg["p_tau"], pg["p_blase"][::-1]]), label=name, **stil[name])

ax.axhline(p_grenze, color=ROT, lw=1.0, ls="--")
ax.text(0.6, p_grenze + 0.6, f"Mindestdruck {p_grenze:.1f} bar (Cricondenbar gewählt + {UNSICHERHEIT_BAR:.0f} bar)".replace(".", ","),
        color=ROT, fontsize=9)

ax.set_xlim(0, 35)
ax.set_ylim(35, 95)
ax.set_xlabel("Temperatur [°C]")
ax.set_ylabel("Druck [bar]")
ax.set_title("Phasengrenze bei veränderter Zusammensetzung der Begleitstoffe")
ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(ABB / "abb_sensitivitaet_zusammensetzung.png", dpi=175)
print("\ngespeichert: abb_sensitivitaet_zusammensetzung.png")

# ---- D) Einfluss der einzelnen Begleitstoffe ---------------------------------
# Zweistoffgemisch CO2 + 1 mol-% Begleitstoff bei 15 °C gegen reines CO2
p_rein = CP.PropsSI("P", "T", 288.15, "Q", 0, "CO2") / 1e5
print(f"\nD) Anstieg von Blasen- und Taudruck bei 15 °C je 1 mol-% (rein: {p_rein:.2f} bar)")
tab_d = []
for stoff in ["Hydrogen", "Nitrogen", "Argon", "CarbonMonoxide", "Methane"]:
    d_bl = p_sat(["CO2", stoff], [0.99, 0.01], 15.0, 0.0) - p_rein
    d_tau = p_sat(["CO2", stoff], [0.99, 0.01], 15.0, 1.0) - p_rein
    print(f"   {ANZEIGE[stoff]:<4} Blasendruck {d_bl:+5.1f} bar   Taudruck {d_tau:+5.1f} bar")
    tab_d.append({"stoff": ANZEIGE[stoff], "d_blase_bar": round(d_bl, 2), "d_tau_bar": round(d_tau, 2)})

# ---- Ergebnisdatei --------------------------------------------------------------
def r(v):
    return None if v is None or np.isnan(v) else round(float(v), 3)


export = {
    "quelle": "04_sensitivitaet_zusammensetzung.py",
    "coolprop_version": CoolProp.__version__,
    "A_stoffpaare": {"zaehlung": zaehlung, "paare": tab_a},
    "B_varianten": [
        {"variante": name,
         "molanteile": {n: xi for n, xi in zip(namen, x) if xi > 0},
         "krit_C_bar": [r(erg[name]["krit"][0]), r(erg[name]["krit"][1])],
         "cricondenbar_C_bar": [r(erg[name]["cricondenbar"][0]), r(erg[name]["cricondenbar"][1])],
         "p_blase15_bar": r(erg[name]["p_blase15"]), "p_tau15_bar": r(erg[name]["p_tau15"])}
        for name, namen, x in VARIANTEN],
    "mindestdruck_bar": r(p_grenze), "p_betrieb_bar": P_BETRIEB,
}
with open(ABB / "sensitivitaet_zusammensetzung.json", "w", encoding="utf-8") as f:
    json.dump(export, f, indent=1, ensure_ascii=False)
print("gespeichert: sensitivitaet_zusammensetzung.json")
