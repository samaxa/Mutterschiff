# -*- coding: utf-8 -*-
"""
G05 - Joule-Thomson-Koeffizient: CO2, Erdgas und Wasserstoff
============================================================================
µ_JT = (∂T/∂p)_h sagt, um wie viel Kelvin das Gas je bar Druckabsenkung in
einer Drossel abkühlt (µ_JT > 0) oder sich erwärmt (µ_JT < 0).

Links: CO2 auf vier Isothermen (20, 30, 40, 50 °C) über dem Druck. Unter
31 °C springt µ_JT an der Siedelinie, weil sich dort die Phase ändert. In
der dichten Phase ist µ_JT klein, im Gas groß.
Rechts: die drei Gase bei 50 °C. CO2 kühlt im Gas um ein Vielfaches stärker
ab als Erdgas. Wasserstoff hat bei diesen Temperaturen ein negatives µ_JT.

Validierung: Vergleich mit den Werten aus dem NIST Chemistry WebBook, die
in der alten Mappe (Blatt „JT-Koeffi_Gase“) abgefragt wurden
(Daten/nist_webbook_jt.csv, CO2 und CH4, 20 bis 50 °C, 10 bis 250 bar).
Auf der Siedelinie gibt NIST zwei Werte aus (Dampf und Flüssigkeit); sie
werden mit CoolProp bei Q = 1 bzw. Q = 0 verglichen.

Hinweis zur alten Mappe: dort wurden die 20- und 30-°C-Werte im Diagramm über
der Druckspalte der 50-°C-Daten aufgetragen. Wegen der zusätzlichen
Siedepunkte (57,3 bzw. 72,1 bar) sind die Kurven dort um ein bis zwei
Druckstufen verschoben. Hier wird jede Isotherme über ihrem eigenen Druck
aufgetragen.

Ergebnisse: Abbildungen/G05_jt_koeffizient.json
"""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import gasgrundlagen_bausteine as gb


def mu_jt(stoff, p_bar, T_C, q=None):
    f = gb.STOFFE[stoff][0]
    if q is None:
        return PropsSI("d(T)/d(P)|Hmass", "P", p_bar * 1e5, "T", gb.K(T_C), f) * 1e5
    return PropsSI("d(T)/d(P)|Hmass", "T", gb.K(T_C), "Q", q, f) * 1e5


# ---- 1) Validierung gegen NIST ---------------------------------------------------
nist = list(csv.DictReader(open(gb.DATEN / "nist_webbook_jt.csv", encoding="utf-8")))
vergleich = []
for r in nist:
    st, T, p, mu_n, ph = r["stoff"], float(r["T_C"]), float(r["p_bar"]), float(r["mu_JT_K_per_bar"]), r["phase"]
    p_s = PropsSI("P", "T", gb.K(T), "Q", 0, gb.STOFFE[st][0]) / 1e5 if T < gb.kennwerte(st)["T_krit"] else None
    if p_s is not None and abs(p - p_s) < 0.05:
        mu_c = mu_jt(st, p, T, q=1 if ph == "vapor" else 0)
    else:
        mu_c = mu_jt(st, p, T)
    vergleich.append({"stoff": st, "T": T, "p": p, "phase": ph, "nist": mu_n, "coolprop": mu_c,
                      "abw": mu_c - mu_n, "abw_rel": (mu_c - mu_n) / mu_n * 100})
for st in ("CO2", "CH4"):
    v = [x for x in vergleich if x["stoff"] == st]
    ma = max(v, key=lambda x: abs(x["abw"]))
    mr = max(v, key=lambda x: abs(x["abw_rel"]))
    print(f"{st}: {len(v)} Punkte, größte Abweichung {ma['abw']:+.4f} K/bar "
          f"({ma['T']:.0f} °C / {ma['p']:.1f} bar), größte relative {mr['abw_rel']:+.2f} % "
          f"({mr['T']:.0f} °C / {mr['p']:.1f} bar)")

# ---- 2) Kurven ----------------------------------------------------------------------
p_lin = np.linspace(10.0, 250.0, 481)
kurven = {}
for st in gb.STOFFE:
    kurven[st] = {}
    for T in gb.T_ISOTHERMEN:
        mu = []
        for p in p_lin:
            try:
                mu.append(mu_jt(st, p, T))
            except ValueError:                                  # genau auf der Siedelinie
                mu.append(np.nan)
        kurven[st][f"{T:.0f}"] = np.array(mu)

print("\nµ_JT bei 50 °C [K/bar]:")
for p in (10, 50, 80, 100, 150, 210):
    werte = "  ".join(f"{gb.STOFFE[st][1].split(' ')[0]} {mu_jt(st, p, 50.0):+6.3f}" for st in gb.STOFFE)
    print(f"  {p:4d} bar: {werte}")

# ---- 3) Abbildung ------------------------------------------------------------------
FARBEN_T = {"20": "#1F4E79", "30": "#2E75B6", "40": "#C55A11", "50": "#7F3F00"}
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.4))
for T, mu in kurven["CO2"].items():
    ax1.plot(p_lin, mu, color=FARBEN_T[T], lw=1.8, label=f"{T} °C (CoolProp)")
    v = [x for x in vergleich if x["stoff"] == "CO2" and f"{x['T']:.0f}" == T]
    ax1.plot([x["p"] for x in v], [x["nist"] for x in v], "o", mfc="none", mec=FARBEN_T[T], ms=5)
ax1.plot([], [], "o", mfc="none", mec="#555555", ms=5, label="NIST WebBook")
ax1.set_xlabel("Druck [bar]")
ax1.set_ylabel("µ_JT [K/bar]")
ax1.set_title("CO₂: Joule-Thomson-Koeffizient")
ax1.set_xlim(0, 250)
ax1.set_ylim(0, 1.25)
ax1.grid(alpha=0.25)
ax1.legend(loc="upper right", fontsize=8.5)

for st, (f, name, farbe) in gb.STOFFE.items():
    ax2.plot(p_lin, kurven[st]["50"], color=farbe, lw=2.0, label=name)
ax2.axhline(0.0, color="#333333", lw=0.8)
ax2.text(240, 0.03, "Abkühlung beim Drosseln", ha="right", fontsize=8.5, color="#555555")
ax2.text(240, -0.11, "Erwärmung beim Drosseln", ha="right", fontsize=8.5, color="#555555")
ax2.set_xlabel("Druck [bar]")
ax2.set_ylabel("µ_JT [K/bar]")
ax2.set_title("Vergleich bei 50 °C")
ax2.set_xlim(0, 250)
ax2.set_ylim(-0.15, 1.0)
ax2.grid(alpha=0.25)
ax2.legend(loc="upper right", fontsize=8.5)
fig.tight_layout()
fig.savefig(gb.ABB / "abb_G05_jt_koeffizient.png", dpi=175)
plt.close(fig)
print("\ngespeichert: abb_G05_jt_koeffizient.png")

json.dump({
    "validierung_nist": vergleich,
    "kurven": {st: {T: {"p": p_lin[::10].tolist(), "mu_JT": np.nan_to_num(mu[::10], nan=-999).round(5).tolist()}
                    for T, mu in d.items()} for st, d in kurven.items()},
}, open(gb.ABB / "G05_jt_koeffizient.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
