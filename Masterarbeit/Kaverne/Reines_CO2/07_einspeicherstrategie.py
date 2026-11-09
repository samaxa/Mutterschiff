# -*- coding: utf-8 -*-
"""
Kaverne Schritt 07 (reines CO₂) - Betriebsstrategie beim Einspeichern
============================================================================
Stand 09.11.2026. Frage: Was passiert am Kopf, solange der Lieferdruck reicht und keine
Pumpe läuft (Überströmen), und wie hält man den Kopf dabei einphasig?

Bisher (Schritt 04, kb.einspeisen_geregelt): S1 und S2 kommen immer mit dem Lieferzustand
91 bar / 15 °C bzw. 91 bar / 26 °C an das Regelventil am Kopf und werden kalt gedrosselt.
Bei leerer Kaverne liegt der Kopf dann bei rund 20 bar / -20 °C im Zweiphasengebiet.

Neu (kb.einspeisen_strategie):
  S1  Überströmen über das Regelventil; ist der Kopf danach nicht einphasig (3 bar Abstand
      zur Siedelinie), wird bei 91 bar vorgewärmt, gerade so weit wie nötig.
  S2  nur so weit verdichten, wie der Kopf braucht, und gasförmig einspeisen (Nachkühler
      40 °C). Erst wenn das nicht mehr geht, Pfad B (91 bar, Kühler 26 °C, Pumpe/Drossel).

Das Skript rechnet
  1) für beide Raten und Szenarien über den Kavernendruck an der LCCS (70-210 bar) den
     Kopfzustand alt und neu, Antrieb, Kühlung, Vorwärmung und h an der LCCS,
  2) den Speicherzyklus neu, mit h an der LCCS abhängig vom Kavernendruck
     (kb.kavernenzyklus mit h_ein als Funktion), und die Energie je Einspeicherung,
  3) zwei Abbildungen: abb_K07_saeule_erklaert.png (warum am Kopf gedrosselt wird) und
     abb_K07_einspeicherstrategie.png (Kopfzustände und Leistung, alt gegen neu, 50.000 Nm³/h).
Braucht vorher: Schritt 03 (kavernenzyklus.json) in diesem Ordner.
Ausgabe: einspeicherstrategie.json und die beiden PNG.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402

eb = kb.eb
MED, KAV = kb.REIN, kb.TIEF
RATEN = kb.raten(MED)                      # {"50.000 Nm³/h": kg/s, "100.000 Nm³/h": kg/s}
R50 = "50.000 Nm³/h"
ST = "Stillstand 21,67 d (Q-028)"
P_GRID = np.r_[np.arange(70.0, 210.0, 5.0), 210.0]
de = lambda x, n=1: f"{x:.{n}f}".replace(".", ",")


def basis(pl, szen, md, h_ausl):
    """Alter Stand (Schritt 04): kalt drosseln oder pumpen, S2 immer über Pfad B."""
    e = kb.einspeisen_geregelt(MED, KAV, pl, szen, md, h_ausl, n=150)
    k, st = e["kopf"], MED.stoff
    if szen == "S1":
        w = eb.stufe(st, eb.p_S1, eb.T_S1, k["p"], eb.eta_P)["w"] if e["pumpe"] else 0.0
        q = 0.0
    else:
        _, V1, ZK, V2 = eb.zweistufig(st, eb.P_UEK, p_zw=eb.P_ZW, T_zk=eb.T_ZK)
        q = ZK["q"] + V2["h2"] - MED.h(eb.P_UEK, eb.T_K)
        w = V1["w"] + V2["w"] + (eb.stufe(st, eb.P_UEK, eb.T_K, k["p"], eb.eta_P)["w"] if e["pumpe"] else 0.0)
    return dict(p_lccs=pl, szenario=szen, art="Pumpe" if e["pumpe"] else "Drossel (kalt)", kopf=k,
                w=w, q_kuehl=q, q_heiz=0.0, h_lccs=k["h_lccs"], T_lccs=k["T_lccs"])


def kurz(e):
    k = e["kopf"]
    return dict(p_lccs=e["p_lccs"], art=e["art"], p_kopf=k["p"], T_kopf=k["T"], q_kopf=k["q"],
                abstand_bar=kb.abstand_phasengrenze(k["p"], k["T"], k["q"]),
                zweiphasig_im_strang=k["zweiphasig_im_strang"], v_max=k["v_max"],
                w=e["w"], q_kuehl=e["q_kuehl"], q_heiz=e["q_heiz"], T_vorw=e.get("T_vorw"),
                T_kuehler=e.get("T_kuehler"), p_verdichter=e.get("p_verdichter"),
                h_lccs=e["h_lccs"], T_lccs=e["T_lccs"])


# ---- 1) Kopfzustand und Energie über dem Kavernendruck -----------------------------------------
tab = {}
for r, md in RATEN.items():
    tab[r] = {}
    for sz in ("S1", "S2"):
        h_ausl = kb.zieldruck_einspeisen(MED, KAV, sz, md)["h_kopf"]
        alt = [kurz(basis(pl, sz, md, h_ausl)) for pl in P_GRID]
        neu = [kurz(kb.einspeisen_strategie(MED, KAV, pl, sz, md, h_ausl)) for pl in P_GRID]
        tab[r][sz] = dict(alt=alt, neu=neu, h_auslegung=h_ausl)
        for a, b in zip(alt, neu):
            print(f"{r} {sz} p_LCCS {a['p_lccs']:5.1f}: alt {a['art']:<15} Kopf {a['p_kopf']:6.1f} bar "
                  f"{a['T_kopf']:6.1f} °C {'2ph' if a['q_kopf'] is not None else '   '} | neu {b['art']:<34} "
                  f"Kopf {b['p_kopf']:6.1f} bar {b['T_kopf']:6.1f} °C, Abstand {b['abstand_bar']:5.1f}, "
                  f"w {b['w']:5.1f} q_k {b['q_kuehl']:6.1f} q_h {b['q_heiz']:6.1f} kJ/kg, T_LCCS {b['T_lccs']:5.1f} °C")

# ---- 2) Speicherzyklus mit h an der LCCS abhängig vom Kavernendruck ------------------------------
Z = json.load(open(ORDNER / "kavernenzyklus.json", encoding="utf-8"))
zyklus = {}
for r, md in RATEN.items():
    zyklus[r] = {}
    for sz in ("S1", "S2"):
        neu = tab[r][sz]["neu"]
        pg = [x["p_lccs"] for x in neu]
        f = lambda col: (lambda pl: float(np.interp(pl, pg, [x[col] for x in neu])))
        h_ein = f("h_lccs")
        vl = kb.kavernenzyklus(MED, KAV, md, h_ein=h_ein)
        kw = kb.zyklus_kennwerte(vl)
        ein = next(x for x in kw if x["art"] == "ein")
        E = dict(heiz=0.0, antrieb=0.0, kuehl=0.0)
        dt_h = None
        for x0, x1 in zip(vl, vl[1:]):
            if x0["art"] != "ein" or x0["m_dot"] <= 0:
                continue
            dt_h = (x1["t"] - x0["t"]) * 24.0
            E["heiz"] += x0["m_dot"] * f("q_heiz")(x0["p_lccs"]) * dt_h / 1000.0      # MWh
            E["antrieb"] += x0["m_dot"] * f("w")(x0["p_lccs"]) * dt_h / 1000.0
            E["kuehl"] += x0["m_dot"] * f("q_kuehl")(x0["p_lccs"]) * dt_h / 1000.0
        # alter Stand aus Schritt 03 (h an der LCCS fest) zum Vergleich
        alt_kw = next(x for x in Z["zyklen"][f"{sz}|{r}|{ST}"]["kennwerte"] if x["art"] == "ein")
        alt = tab[r][sz]["alt"]
        fa = lambda col: (lambda pl: float(np.interp(pl, pg, [x[col] for x in alt])))
        Ea = dict(heiz=0.0, antrieb=0.0, kuehl=0.0)
        va = [x for x in Z["zyklen"][f"{sz}|{r}|{ST}"]["verlauf"] if x["art"] == "ein" and x["m_dot"] > 0]
        for x0, x1 in zip(va, va[1:]):
            dt_h = (x1["t"] - x0["t"]) * 24.0
            Ea["antrieb"] += x0["m_dot"] * fa("w")(x0["p_lccs"]) * dt_h / 1000.0
            Ea["kuehl"] += x0["m_dot"] * fa("q_kuehl")(x0["p_lccs"]) * dt_h / 1000.0
        zyklus[r][sz] = dict(
            neu=dict(dauer_ein=ein["dauer"], T_min_ein=ein["T_min"], T_max_ein=ein["T_max"],
                     m_voll=ein["m_ende"], energie_MWh=E),
            alt=dict(dauer_ein=alt_kw["dauer"], T_min_ein=alt_kw["T_min"], T_max_ein=alt_kw["T_max"],
                     m_voll=alt_kw["m_ende"], energie_MWh=Ea))
        n_, a_ = zyklus[r][sz]["neu"], zyklus[r][sz]["alt"]
        print(f"Zyklus {sz} {r}: Einspeichern alt {de(a_['dauer_ein'])} d, T_max {de(a_['T_max_ein'])} °C, "
              f"voll {a_['m_voll']:.0f} t | neu {de(n_['dauer_ein'])} d, T_max {de(n_['T_max_ein'])} °C, "
              f"voll {n_['m_voll']:.0f} t | Energie alt {a_['energie_MWh']} | neu {n_['energie_MWh']}")

# ---- 3a) Erklärbild: Druck und Temperatur in der Säule bei leerer Kaverne (S1, 50.000 Nm³/h) ----
md = RATEN[R50]
pl0 = Z["zyklen"][f"S1|{R50}|{ST}"]["kennwerte"][2]["p_lccs_start"]      # Beginn Einspeichern
h0 = MED.h(eb.p_S1, eb.T_S1)


def saeule_von_oben(p_kopf, h_kopf, m, n=300):
    """Säule vom Kopf nach unten (Einspeisen, adiabat, Reibung gegen die Strömung)."""
    dz = KAV.z_lccs / n
    p, h, T, out = p_kopf, h_kopf, eb.T_S1, []
    for i in range(n + 1):
        zs = MED.zustand_ph(p, h, T)
        T, rho = zs["T"], zs["rho"]
        v = m / (rho * kb.A_STRANG)
        out.append((i * dz, p, T, zs["q"]))
        p += (rho * kb.G - kb.F_DARCY / kb.D_STRANG * rho * v * v / 2.0) * dz / 1e5
        h += kb.G * dz / 1000.0
    return out


# Fall A: Kopf hält 91 bar (Ventil offen), gerechnet mit dem Auslegungsstrom
A = saeule_von_oben(eb.p_S1, h0, md)
# welcher Strom würde fließen, wenn der Kopf 91 bar hätte? (Reibung frisst den Überdruck)
lo, hi = md, 2000.0
for _ in range(30):
    mid = 0.5 * (lo + hi)
    k = kb.kopf_einspeisen(MED, KAV, pl0, h0, mid, n=150)[1]
    lo, hi = (mid, hi) if k["p"] < eb.p_S1 else (lo, mid)
m_offen = 0.5 * (lo + hi)
v_offen = m_offen / (MED.rho(eb.p_S1, eb.T_S1) * kb.A_STRANG)
# Fall B: kalt gedrosselt, Fall C: vorgewärmt (Strategie)
profB, kB = kb.kopf_einspeisen(MED, KAV, pl0, h0, md)
eC = kb.einspeisen_strategie(MED, KAV, pl0, "S1", md, tab[R50]["S1"]["h_auslegung"])
profC, kC = kb.kopf_einspeisen(MED, KAV, pl0, eC["h_kopf"], md)
B = [(r[0], r[1], r[2], r[5]) for r in profB]          # Profil: (Teufe, p, T, ρ, v, q), oben zuerst
C = [(r[0], r[1], r[2], r[5]) for r in profC]
print(f"Erklärbild: LCCS {de(pl0)} bar; A: unten {de(A[-1][1])} bar; offen würden {m_offen:.0f} kg/s "
      f"({m_offen / md:.0f}-fach, {de(v_offen)} m/s) fließen; B: Kopf {de(kB['p'])} bar / {de(kB['T'])} °C; "
      f"C: vorgewärmt auf {de(eC['T_vorw'])} °C, Kopf {de(kC['p'])} bar / {de(kC['T'])} °C, "
      f"Heizleistung {de(md * eC['q_heiz'] / 1000)} MW")

ROT, GRUEN, NAVY, GRAU = "#CA220E", "#1B7A3A", "#0B2A4A", "#8C8C8C"
BLAU, HELLBLAU = "#1F6FD1", "#8FB8EE"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 4.9), dpi=250, sharey=True)


def linie(ax, P_, idx, farbe, lab=None):
    z = np.array([r[0] for r in P_])
    y = np.array([r[idx] for r in P_], dtype=float)
    zw = np.array([r[3] is not None for r in P_])
    ax.plot(y, z, color=farbe, lw=1.6, label=lab)
    if zw.any():
        ax.plot(np.where(zw, y, np.nan), np.where(zw, z, np.nan), color=farbe, lw=5, alpha=0.3,
                solid_capstyle="butt")


linie(a1, A, 1, GRAU, "A: oben 91 bar, Strang ganz flüssig (gedacht)")
linie(a1, B, 1, ROT, f"B: Ventil drosselt kalt, oben {de(kB['p'])} bar")
linie(a1, C, 1, GRUEN, f"C: erst auf {de(eC['T_vorw'], 0)} °C vorwärmen, dann Ventil, oben {de(kC['p'])} bar")
a1.plot(pl0, KAV.z_lccs, "D", color=NAVY, ms=6, zorder=6)
a1.annotate(f"Kaverne leer: {de(pl0)} bar", (pl0, KAV.z_lccs), (95, 1140), fontsize=6.8, color=NAVY,
            arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.7))
a1.annotate(f"A wäre unten {de(A[-1][1], 0)} bar.\nDie Kaverne hat nur {de(pl0, 0)} bar.\n"
            f"Ohne Ventil würden {m_offen:.0f} kg/s\nstatt {de(md)} kg/s fließen.",
            (A[-1][1], KAV.z_lccs), (132, 250), fontsize=6.6, color="#555555",
            arrowprops=dict(arrowstyle="-", color=GRAU, lw=0.7))
a1.text(80, 820, "dicke Linie = CO₂ kocht\n(flüssig + Dampf)", fontsize=6.4, color="#555555", va="center")
a1.set(xlim=(0, 215), ylim=(KAV.z_lccs + 30, -30), xlabel="Druck im Förderstrang [bar]",
       ylabel="Tiefe unter dem Kopf [m]")
a1.set_title("Druck: unten muss es zur Kaverne passen", loc="left", fontsize=8.5, weight="bold", color=NAVY)

linie(a2, A, 2, GRAU)
linie(a2, B, 2, ROT)
linie(a2, C, 2, GRUEN)
a2.annotate(f"B oben: {de(kB['T'])} °C,\n{100 * kB['q']:.0f} % Dampf", (kB["T"], 0), (-7, 110), fontsize=6.8,
            color=ROT, arrowprops=dict(arrowstyle="-", color=ROT, lw=0.7))
a2.annotate(f"C oben: {de(kC['T'])} °C, Gas,\n"
            f"{de(kb.abstand_phasengrenze(kC['p'], kC['T'], kC['q']))} bar weg von der Siedelinie,\n"
            f"Vorwärmer {de(md * eC['q_heiz'] / 1000)} MW", (kC["T"], 0), (27, 130),
            fontsize=6.8, color=GRUEN, arrowprops=dict(arrowstyle="-", color=GRUEN, lw=0.7))
a2.set(xlim=(-25, 70), xlabel="Temperatur im Förderstrang [°C]")
a2.set_title("Temperatur: Druckabbau am Ventil kühlt (Joule-Thomson)", loc="left", fontsize=8.5,
             weight="bold", color=NAVY)
for a in (a1, a2):
    a.grid(alpha=0.3)
fig.suptitle(f"Einspeichern S1 (91 bar / 15 °C flüssig) bei leerer Kaverne, {R50}, reines CO₂",
             fontsize=8.5, x=0.01, ha="left", color=NAVY)
h_, l_ = a1.get_legend_handles_labels()
fig.legend(h_, l_, loc="lower center", ncol=3, fontsize=6.6, frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(ORDNER / "abb_K07_saeule_erklaert.png", bbox_inches="tight")
plt.close(fig)

# ---- 3b) Kopfzustände und Leistung, alt gegen neu (50.000 Nm³/h) ---------------------------------
T_K, P_K = kb.T_KRIT, kb.P_KRIT
Ts = np.linspace(-25, T_K - 0.01, 300)
ps = np.array([PropsSI("P", "T", t + 273.15, "Q", 0, "CO2") / 1e5 for t in Ts])
fig = plt.figure(figsize=(8.4, 5.4), dpi=250)
gs = fig.add_gridspec(2, 2, width_ratios=(1.15, 1), hspace=0.45, wspace=0.22)
b1, b2, b3 = fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1])
b1.plot(Ts, ps, color=GRAU, lw=1.6, label="Siedelinie")
b1.fill_between(Ts, ps - eb.U_PG, ps + eb.U_PG, color=GRAU, alpha=0.2, lw=0, label="± 3 bar Mindestabstand")
b1.add_patch(plt.Rectangle((T_K, P_K - eb.U_PG), eb.U_PG, 2 * eb.U_PG, color=GRAU, alpha=0.2, lw=0))
b1.plot(T_K, P_K, "o", color=GRAU, mfc="white", ms=5, zorder=5)
b1.annotate("kritischer Punkt", (T_K, P_K), (T_K + 2, P_K + 23), fontsize=6.3, color="#555555",
            arrowprops=dict(arrowstyle="-", color=GRAU, lw=0.6))


def nach_art(ax, zeilen, farbe, mk, ls, lab):
    """Kopfzustände je Betriebsart als eigene Linie (keine Verbindung über einen Wechsel)."""
    erst = True
    for art in dict.fromkeys(x["art"] for x in zeilen):
        g = [x for x in zeilen if x["art"] == art]
        ax.plot([x["T_kopf"] for x in g], [x["p_kopf"] for x in g], ls=ls, marker=mk, ms=2.8, lw=1.1,
                color=farbe, label=lab if erst else None)
        erst = False


nach_art(b1, tab[R50]["S1"]["alt"], ROT, "s", "--", "S1 bisher: immer kalt drosseln")
nach_art(b1, tab[R50]["S1"]["neu"], GRUEN, "s", "-", "S1 neu: vorwärmen, wo nötig")
nach_art(b1, tab[R50]["S2"]["alt"], HELLBLAU, "o", "--", "S2 bisher: immer 91 bar / 26 °C")
nach_art(b1, tab[R50]["S2"]["neu"], BLAU, "o", "-", "S2 neu: nur so weit verdichten wie nötig")


def marke(ax, zeilen, pl, farbe, dx, dy):
    x = min(zeilen, key=lambda r: abs(r["p_lccs"] - pl))
    ax.annotate(f"{x['p_lccs']:.0f}", (x["T_kopf"], x["p_kopf"]), (x["T_kopf"] + dx, x["p_kopf"] + dy),
                fontsize=6.0, color=farbe, ha="center", va="center",
                arrowprops=dict(arrowstyle="-", color=farbe, lw=0.5))


for pl, dx, dy in ((70, 0, -8.5), (150, -7, 8)):
    marke(b1, tab[R50]["S1"]["alt"], pl, ROT, dx, dy)
for pl, dx, dy in ((70, 1, -8.5), (100, 5, -4), (150, 3.5, 6.5), (155, -4.5, 11), (195, -5.5, 2)):
    marke(b1, tab[R50]["S1"]["neu"], pl, GRUEN, dx, dy)
for pl, dx, dy in ((70, 4, -5.5), (155, 4.5, -3), (160, -3.5, 6)):
    marke(b1, tab[R50]["S2"]["neu"], pl, BLAU, dx, dy)
b1.text(-23, 123, "Zahl am Punkt = Kavernendruck an der LCCS [bar]\n"
        "S1 ab 155 bar und S2 ab 160 bar: neu = bisher", fontsize=6.2, color="#555555", va="top")
b1.set(xlim=(-25, 50), ylim=(0, 128), xlabel="Temperatur am Kopf nach dem Ventil [°C]",
       ylabel="Druck am Kopf nach dem Ventil [bar]")
b1.set_title("Wo landet der Kopf? (50.000 Nm³/h)", loc="left", fontsize=8.5, weight="bold", color=NAVY)
b1.legend(loc="lower right", fontsize=5.9, framealpha=0.95)

pg = np.array([x["p_lccs"] for x in tab[R50]["S1"]["neu"]])


def bereiche(ax, zeilen, farben):
    arten = [x["art"] for x in zeilen]
    i0 = 0
    for i in range(1, len(arten) + 1):
        if i == len(arten) or arten[i] != arten[i0]:
            lo_ = pg[i0] if i0 == 0 else 0.5 * (pg[i0 - 1] + pg[i0])
            hi_ = pg[-1] if i == len(arten) else 0.5 * (pg[i - 1] + pg[i])
            ax.axvspan(lo_, hi_, color=farben[arten[i0]], alpha=0.10, lw=0)
            schmal = hi_ - lo_ < 20
            ax.text(0.5 * (lo_ + hi_), 0.97, arten[i0] if schmal else arten[i0].replace(" + ", " +\n"),
                    transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=5.8, color="#444444",
                    rotation=90 if schmal else 0)
            i0 = i


bereiche(b2, tab[R50]["S1"]["neu"], {"Vorwärmen + Drossel": GRUEN, "Drossel": GRAU, "Pumpe": NAVY})
b2.plot(pg, [md * x["q_heiz"] / 1000 for x in tab[R50]["S1"]["neu"]], color=GRUEN, lw=1.6,
        label="Vorwärmer (Wärme)")
b2.plot(pg, [md * x["w"] / 1000 for x in tab[R50]["S1"]["neu"]], color=NAVY, lw=1.2, label="Pumpe")
b2.set(xlim=(70, 210), ylim=(0, 7.5), ylabel="Leistung [MW]")
b2.set_title("S1 neu: was es kostet", loc="left", fontsize=8.5, weight="bold", color=NAVY)
b2.legend(loc="center right", fontsize=5.9, framealpha=0.95)

bereiche(b3, tab[R50]["S2"]["neu"], {"gasförmig (nur verdichten)": BLAU, "Pfad B + Drossel": GRAU,
                                     "Pfad B + Pumpe": NAVY})
for var, farbe, ls, lab in (("alt", HELLBLAU, "--", "bisher"), ("neu", BLAU, "-", "neu")):
    b3.plot(pg, [md * x["w"] / 1000 for x in tab[R50]["S2"][var]], color=farbe, ls=ls, lw=1.5,
            label=f"Antrieb {lab}")
    b3.plot(pg, [md * x["q_kuehl"] / 1000 for x in tab[R50]["S2"][var]], color=farbe, ls=ls, lw=1.0,
            marker=".", ms=3, label=f"Kühlung {lab}")
b3.set(xlim=(70, 210), ylim=(0, 9.5), xlabel="Kavernendruck an der LCCS [bar]", ylabel="Leistung [MW]")
b3.set_title("S2: Antrieb und Kühlung, bisher und neu", loc="left", fontsize=8.5, weight="bold", color=NAVY)
b3.legend(loc="lower right", fontsize=5.9, framealpha=0.95, bbox_to_anchor=(1, 0.2))
for a in (b1, b2, b3):
    a.grid(alpha=0.3)
fig.savefig(ORDNER / "abb_K07_einspeicherstrategie.png", bbox_inches="tight")
plt.close(fig)

kb.speichere_json(ORDNER, "einspeicherstrategie.json", dict(
    erzeugt_von="07_einspeicherstrategie.py", stand="09.11.2026",
    regeln=dict(mindestabstand_bar=eb.U_PG, T_nachkuehler=kb.T_NACHKUEHLER, p_verdichter_max=eb.P_UEK,
                T_stufe_max=eb.T_MAX_STUFE),
    tabelle=tab, zyklus=zyklus,
    erklaerbild=dict(p_lccs=pl0, A_unten=A[-1][1], m_offen=m_offen, v_offen=v_offen,
                     B=dict(p=kB["p"], T=kB["T"], q=kB["q"]),
                     C=dict(T_vorw=eC["T_vorw"], p=kC["p"], T=kC["T"], P_heiz_MW=md * eC["q_heiz"] / 1000))))
print("gespeichert: einspeicherstrategie.json, abb_K07_saeule_erklaert.png, abb_K07_einspeicherstrategie.png")
