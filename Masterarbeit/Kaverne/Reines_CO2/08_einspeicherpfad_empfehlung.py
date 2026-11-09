# -*- coding: utf-8 -*-
"""
Kaverne Schritt 08 (reines CO₂) - Einspeicherpfad: vom Netz zum Kavernenkopf
============================================================================
Stand 09.11.2026. Schlichte Phasendiagramme für die Arbeit, Erklärung der Pfeile im Text.

Regel (angelehnt an Q-012 Folie 16 und Q-030 S. 15/32):
  Kavernendruck an der LCCS bis etwa 155 bar: gasförmig einspeisen, Kopf auf 40 °C.
      S1: bei 91 bar vorwärmen, dann Ventil.  S2: nur so weit verdichten wie nötig, Kühler 40 °C.
  ab etwa 160 bar: dicht einspeisen (S1 Ventil bzw. Pumpe, S2 Pfad B mit Ventil bzw. Pumpe).
Kopfzustände aus Schritt 07 (einspeicherstrategie.json, 50.000 Nm³/h). Der Kopf bei 40 °C ist für
S1 und S2 derselbe (gleiche Säule), deshalb gilt die S2-Gasroute auch für S1.

Bild 1 abb_K08_einspeicherpfad.png: links S1, rechts S2, je Weg bei leerer und bei voller Kaverne.
Bild 2 abb_K08_ohne_vorwaermen.png: S1 nur mit Ventil, Kopf auf der Siedelinie.
Braucht vorher: Schritt 03 (kavernenzyklus.json) und 07 (einspeicherstrategie.json).
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI
from matplotlib.lines import Line2D

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402

eb = kb.eb
MED, KAV = kb.REIN, kb.TIEF
R50 = "50.000 Nm³/h"
ST = "Stillstand 21,67 d (Q-028)"
md = kb.raten(MED)[R50]
de = kb.de
st = MED.stoff
T_KOPF_GAS = 40.0          # °C, Kopftemperatur beim gasförmigen Einspeichern (Q-012 Folie 16)
T_HYDRAT = 10.0            # °C, Hydratgrenze mit freiem Wasser (Q-099 Folie 20)

Z = json.load(open(ORDNER / "kavernenzyklus.json", encoding="utf-8"))
S = json.load(open(ORDNER / "einspeicherstrategie.json", encoding="utf-8"))
P_LEER = Z["zyklen"][f"S1|{R50}|{ST}"]["kennwerte"][2]["p_lccs_start"]
P_VOLL = KAV.p_max
tab = S["tabelle"][R50]
h_ausl = {sz: tab[sz]["h_auslegung"] for sz in ("S1", "S2")}

# Kopfzustände
gas_leer = kb.einspeisen_strategie(MED, KAV, P_LEER, "S2", md, h_ausl["S2"])      # 40 °C, gasförmig
s1_voll = kb.einspeisen_strategie(MED, KAV, P_VOLL, "S1", md, h_ausl["S1"])       # Pumpe
s2_voll = kb.einspeisen_strategie(MED, KAV, P_VOLL, "S2", md, h_ausl["S2"])       # Pfad B + Pumpe
_, kalt = kb.kopf_einspeisen(MED, KAV, P_LEER, MED.h(eb.p_S1, eb.T_S1), md)       # S1 nur Ventil
kg = gas_leer["kopf"]
h_kg = PropsSI("H", "P", kg["p"] * 1e5, "T", kg["T"] + 273.15, "CO2")
T_vorw = PropsSI("T", "P", eb.p_S1 * 1e5, "H", h_kg, "CO2") - 273.15
q_vorw = md * (h_kg / 1000 - MED.h(eb.p_S1, eb.T_S1)) / 1000                      # MW
gas = [dict(p_lccs=P_LEER, T_kopf=kg["T"], p_kopf=kg["p"])] + \
    [x for x in tab["S2"]["neu"] if x["art"].startswith("gas") and x["p_lccs"] > P_LEER]
dicht = {sz: [x for x in tab[sz]["neu"] if x["p_lccs"] >= 160] for sz in ("S1", "S2")}
print(f"leer (S1 und S2): Kopf {de(kg['p'])} bar / {de(kg['T'])} °C; S1 vorwärmen auf {de(T_vorw)} °C, "
      f"{de(q_vorw)} MW")
print(f"gasförmig bis {gas[-1]['p_lccs']:.0f} bar: Kopf {de(gas[0]['p_kopf'])} bis {de(gas[-1]['p_kopf'])} bar")
for sz in ("S1", "S2"):
    d = dicht[sz]
    print(f"{sz} dicht ab 160 bar: Kopf {de(d[0]['p_kopf'])} bar / {de(d[0]['T_kopf'])} °C bis "
          f"{de(d[-1]['p_kopf'])} bar / {de(d[-1]['T_kopf'])} °C")
print(f"S1 nur Ventil, leer: Kopf {de(kalt['p'])} bar / {de(kalt['T'])} °C, {100 * kalt['q']:.0f} % Dampf")


def isenthalp(p1, T1, p2, n=40):
    h = PropsSI("H", "P", p1 * 1e5, "T", T1 + 273.15, "CO2")
    ps = np.linspace(p1, p2, n)
    return np.c_[[PropsSI("T", "P", p * 1e5, "H", h, "CO2") - 273.15 for p in ps], ps]


# ---- Zeichnen ------------------------------------------------------------------------------------
LEER, VOLL, GEM, ROT = "#1B7A3A", "#0B2A4A", "#555555", "#CA220E"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
Ts = np.linspace(-30, kb.T_KRIT, 300)
ps = np.array([PropsSI("P", "T", t + 273.15, "Q", 0, "CO2") / 1e5 for t in Ts])


def grund(ax):
    ax.plot(Ts, ps, color="#333333", lw=1.4, zorder=3)
    ax.plot(kb.T_KRIT, kb.P_KRIT, "o", color="#333333", mfc="white", ms=4.5, zorder=4)
    for txt, xy, ha in (("flüssig", (-26, 62), "left"), ("gasförmig", (-26, 6), "left"),
                        ("überkritisch", (86, 124), "right")):
        ax.text(*xy, txt, fontsize=7, color="#777777", style="italic", ha=ha)
    ax.set(xlim=(-30, 90), ylim=(0, 130), xlabel="Temperatur [°C]")
    ax.grid(alpha=0.25, zorder=0)


def pfeil(ax, pts, farbe, nr=None, at=0.5, d=(0, 0)):
    pts = np.asarray(pts, dtype=float)
    ax.plot(pts[:, 0], pts[:, 1], color=farbe, lw=1.9, zorder=6, solid_capstyle="round")
    ax.annotate("", pts[-1], pts[-2], arrowprops=dict(arrowstyle="-|>", color=farbe, lw=1.9, mutation_scale=10),
                zorder=7)
    if nr is not None:
        i = int(round(at * (len(pts) - 1)))
        if len(pts) == 2:
            x, y = pts[0] + at * (pts[1] - pts[0])
        else:
            x, y = pts[i]
        ax.text(x + d[0], y + d[1], str(nr), fontsize=6.8, color="white", weight="bold", ha="center", va="center",
                zorder=9, bbox=dict(boxstyle="circle,pad=0.18", fc=farbe, ec="none"))


def punkt(ax, T, p, txt, farbe="black", dx=2, dy=0, ha="left", mk="o"):
    ax.plot(T, p, mk, color=farbe, ms=5.5, zorder=8, mec="white", mew=0.6)
    ax.text(T + dx, p + dy, txt, fontsize=6.6, color=farbe, ha=ha, va="center", zorder=8)


fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 4.4), dpi=250, sharey=True)
for ax in (a1, a2):
    grund(ax)
a1.set_ylabel("Druck [bar]")

# S1
pfeil(a1, [(eb.T_S1, eb.p_S1), (T_vorw, eb.p_S1)], LEER, 1, d=(0, 4))
pfeil(a1, isenthalp(eb.p_S1, T_vorw, kg["p"]), LEER, 2, at=0.45, d=(4, 0))
kv = s1_voll["kopf"]
pfeil(a1, [(eb.T_S1, eb.p_S1), (kv["T"], kv["p"])], VOLL, 3, d=(-4, 0))
punkt(a1, eb.T_S1, eb.p_S1, "Netz", dx=-2, dy=-5, ha="right")
punkt(a1, kg["T"], kg["p"], "leer", LEER, dx=0, dy=-6, ha="center", mk="D")
punkt(a1, kv["T"], kv["p"], "voll", VOLL, dx=2.5, dy=3, mk="D")
a1.set_title("S1: flüssig aus dem Netz (91 bar / 15 °C)", loc="left", fontsize=8.3, weight="bold", color=VOLL)

# S2
_, V1, ZK, V2 = eb.zweistufig(st, eb.P_UEK, p_zw=eb.P_ZW, T_zk=eb.T_ZK)
pfeil(a2, [(eb.T_S2, eb.p_S2), (V1["T2"], eb.P_ZW)], GEM, 1, d=(1.5, -4.5))
pfeil(a2, [(V1["T2"], eb.P_ZW), (eb.T_ZK, eb.P_ZW)], GEM, 2, d=(0, -4))
pv = gas_leer["p_verdichter"]
if pv > eb.P_ZW:
    V2l = eb.stufe(st, eb.P_ZW, eb.T_ZK, pv, eb.eta_V2)
    pfeil(a2, [(eb.T_ZK, eb.P_ZW), (V2l["T2"], pv), (kb.T_NACHKUEHLER, pv)], LEER, 3, at=0.0, d=(5, 5.5))
kv2 = s2_voll["kopf"]
pfeil(a2, [(eb.T_ZK, eb.P_ZW), (V2["T2"], eb.P_UEK)], VOLL, 4, d=(3.5, -2))
pfeil(a2, [(V2["T2"], eb.P_UEK), (eb.T_K, eb.P_UEK)], VOLL, 5, d=(0, 4))
pfeil(a2, [(eb.T_K, eb.P_UEK), (kv2["T"], kv2["p"])], VOLL, 6, d=(-4, 0))
punkt(a2, eb.T_S2, eb.p_S2, "Netz", dx=-2, dy=-4, ha="right")
punkt(a2, kg["T"], kg["p"], "leer", LEER, dx=-2.5, dy=0, ha="right", mk="D")
punkt(a2, kv2["T"], kv2["p"], "voll", VOLL, dx=2.5, dy=3, mk="D")
a2.set_title("S2: gasförmig aus dem Netz (30 bar / 15 °C)", loc="left", fontsize=8.3, weight="bold", color=VOLL)

fig.legend(handles=[Line2D([], [], color=LEER, lw=2, label="Weg bei leerer Kaverne"),
                    Line2D([], [], color=VOLL, lw=2, label="Weg bei voller Kaverne"),
                    Line2D([], [], color=GEM, lw=2, label="gemeinsamer Weg")],
           loc="lower center", ncol=3, fontsize=6.6, frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.06, 1, 1))
fig.savefig(ORDNER / "abb_K08_einspeicherpfad.png", bbox_inches="tight")
plt.close(fig)

# Bild 2: S1 nur mit Ventil
alt = [x for x in tab["S1"]["alt"] if x["q_kopf"] is not None or x["abstand_bar"] < eb.U_PG]
fig, ax = plt.subplots(figsize=(4.6, 4.2), dpi=250)
grund(ax)
ax.axvline(T_HYDRAT, color="#7A4FB0", lw=0.9, ls="--", zorder=2)
ax.text(T_HYDRAT + 1.5, 126, "Hydratgrenze", fontsize=6.3, color="#7A4FB0", va="top")
pfeil(ax, isenthalp(eb.p_S1, eb.T_S1, kalt["p"], n=80), ROT, 1, at=0.15, d=(4, 0))
ax.plot([x["T_kopf"] for x in alt], [x["p_kopf"] for x in alt], "s", color=ROT, ms=3, zorder=7, mec="white",
        mew=0.4)
punkt(ax, eb.T_S1, eb.p_S1, "Netz", dx=-2, dy=-5, ha="right")
punkt(ax, kalt["T"], kalt["p"], "leer", ROT, dx=0, dy=-6, ha="center", mk="s")
ax.set_ylabel("Druck [bar]")
ax.set_title("S1 nur mit Ventil, ohne Vorwärmen", loc="left", fontsize=8.3, weight="bold", color=VOLL)
fig.tight_layout()
fig.savefig(ORDNER / "abb_K08_ohne_vorwaermen.png", bbox_inches="tight")
plt.close(fig)
print("gespeichert: abb_K08_einspeicherpfad.png, abb_K08_ohne_vorwaermen.png")
