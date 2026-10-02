# -*- coding: utf-8 -*-
"""
Kaverne Schritt 04 - Förderstrang und Bohrlochkopf beim Ausspeichern (reines CO₂)
============================================================================
Was kommt beim Ausspeichern oben an? Der Kopfzustand ist der Startpunkt des
Ausspeicherpfads (Drossel, Vorwärmer, Trocknung, ggf. Rückverdichtung).

Eingang: Kavernenzustände während des Ausspeicherns aus 03 (kavernenzyklus.json),
für beide Kavernen und 50.000 / 100.000 Nm³/h. Für jeden Zeitpunkt wird der
Förderstrang von der LCCS bis zum Kopf gerechnet (kaverne_bausteine.strang_aufwaerts):

  dp = -(ρ·g + f/D · ρ·v²/2)·dz           Schwere + Reibung, 8 5/8"-Strang
  adiabat   h + g·z = konst.              schnell, kein Wärmeaustausch
  Gebirge   T = T_Gebirge(z)              langsam, voller Wärmeaustausch
Der reale Kopfzustand liegt zwischen beiden Grenzfällen (Q-028 Kap. 3: genauer
nur mit einem Bohrlochmodell mit Mehrphasenströmung).

Geprüft wird, was die Obertageanlage wissen muss:
  - Kopfdruck und -temperatur (Band über die Ausspeicherung)
  - Phase am Kopf und im Strang: Flüssigkeit oder Zweiphasenströmung im Strang
    vermeiden (Q-030 Kap. 1.1: Druckstöße; Q-028: Schwingungen, Druckspitzen)
  - Strömungsgeschwindigkeit ≤ 20 m/s (Q-030)
  - Übergabe: Kopfdruck gegen dichte Übergabe (91 bar, wie S1) und gasförmige
    Übergabe (30 bar, wie S2); Drosselung auf 30 bar (isenthalp) -> Temperatur
    nach der Drossel = Vorwärmbedarf

Ausgabe: Konsole, abb_K04_kopfzustand_pT.png, abb_K04_kopf_zeit.png,
bohrlochkopf_ausspeicherung.json (-> 05, 06, Ausspeicherpfad)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import kaverne_bausteine as kb

MED = kb.REIN
P_DICHT, P_GAS = kb.eb.p_S1, kb.eb.p_S2       # 91 / 30 bar - Übergabedrücke wie Einspeicherung
N_PUNKTE = 14                                  # Zeitpunkte je Ausspeicherung
zyklus = kb.lade_json("kavernenzyklus.json", "03_ein_ausspeicherrate.py")


def drossel(p1, T1, p2, h=None):
    """Isenthalpe Drosselung (reines CO₂): T und Phase nach der Drossel."""
    h = PropsSI("H", "P", p1 * 1e5, "T", T1 + 273.15, "CO2") if h is None else h
    T2 = PropsSI("T", "P", p2 * 1e5, "H", h, "CO2") - 273.15
    q = PropsSI("Q", "P", p2 * 1e5, "H", h, "CO2")
    return T2, (q if 0 <= q <= 1 else None)


def phase_text(p, T, q):
    return f"zweiphasig q={q:.2f}" if q is not None else MED.phase(p, T)


erg = {}
for kav in kb.KAVERNEN:
    erg[kav.kurz] = {}
    for name, r in zyklus[kav.kurz]["raten"].items():
        aus = [x for x in r["verlauf"] if x["art"] == "aus" and x["m_dot"] < 0]
        idx = np.unique(np.linspace(0, len(aus) - 1, N_PUNKTE).astype(int))
        punkte = []
        for i in idx:
            x = aus[i]
            m_dot = -x["m_dot"]
            h_u = kb.h_dampf(MED, x["p_lccs"]) if x["q"] is not None else None
            zeile = dict(t=x["t"], p_lccs=x["p_lccs"], T_kav=x["T"], m_dot=m_dot, kav_zweiphasig=x["q"] is not None)
            for modus in ("adiabat", "gebirge"):
                _, k = kb.strang_aufwaerts(MED, kav, x["p_lccs"], x["T"], m_dot, modus=modus, h_unten=h_u)
                if k is None:
                    zeile[modus] = None
                    continue
                h_k = PropsSI("H", "P", k["p"] * 1e5, "D", k["rho"], "CO2")
                T_d, q_d = drossel(k["p"], k["T"], P_GAS, h=h_k) if k["p"] > P_GAS else (k["T"], k["q"])
                zeile[modus] = dict(k, phase=phase_text(k["p"], k["T"], k["q"]), T_drossel_30=T_d, q_drossel_30=q_d)
            punkte.append(zeile)
        erg[kav.kurz][name] = punkte

def schwelle_zweiphasig(kav, punkte, it=10):
    """p_LCCS, unter dem der Strang (adiabat) erstmals zweiphasig wird - Bisektion zwischen den Stützstellen."""
    for a, b in zip(punkte, punkte[1:]):
        if a["adiabat"] and b["adiabat"] and not a["adiabat"]["zweiphasig_im_strang"] \
                and b["adiabat"]["zweiphasig_im_strang"] and not b["kav_zweiphasig"]:
            hi, lo = a["p_lccs"], b["p_lccs"]          # hi einphasig, lo zweiphasig
            for _ in range(it):
                mid = 0.5 * (hi + lo)
                T = np.interp(mid, [lo, hi], [b["T_kav"], a["T_kav"]])
                _, k = kb.strang_aufwaerts(MED, kav, mid, T, b["m_dot"])
                if k and k["zweiphasig_im_strang"]:
                    lo = mid
                else:
                    hi = mid
            return 0.5 * (hi + lo)
    return None


# ---- Konsole ----------------------------------------------------------------------------
schwellen = {kav.kurz: {} for kav in kb.KAVERNEN}
for kav in kb.KAVERNEN:
    print(f"\n==== {kav.name} ====")
    for name, punkte in erg[kav.kurz].items():
        print(f"  {name}:   t[d]  p_LCCS  T_Kav | Kopf adiabat: p / T / v / Phase            | Kopf Gebirge: p / T | nach Drossel 30 bar")
        for z in punkte:
            a, g = z["adiabat"], z["gebirge"]
            if a is None:
                print(f"    {z['t']:6.1f} {z['p_lccs']:6.1f} {z['T_kav']:5.1f} | Säule trägt nicht bis zum Kopf")
                continue
            strang = " (Strang zweiphasig)" if a["zweiphasig_im_strang"] else ""
            print(f"    {z['t']:6.1f} {z['p_lccs']:6.1f} {z['T_kav']:5.1f} | {a['p']:6.1f} bar {a['T']:5.1f} °C "
                  f"{a['v']:5.1f} m/s {a['phase'][:22]:<22}{strang} | {g['p']:6.1f} / {g['T']:4.1f} °C | "
                  f"{a['T_drossel_30']:6.1f} °C" + (f" q={a['q_drossel_30']:.2f}" if a["q_drossel_30"] is not None else ""))
        alle = [z["adiabat"] for z in punkte if z["adiabat"]] + [z["gebirge"] for z in punkte if z["gebirge"]]
        pk = [k["p"] for k in alle]
        vk = [k["v_max"] for k in alle]
        print(f"    -> Kopfdruck {min(pk):.1f}-{max(pk):.1f} bar; v_max {max(vk):.1f} m/s {kb.ok(max(vk) <= kb.V_MAX_STRANG)} "
              f"(≤ {kb.V_MAX_STRANG:.0f} m/s); Kopf unter {P_DICHT:.0f} bar (dichte Übergabe -> Rückverdichtung) "
              f"in {100*np.mean([p < P_DICHT for p in pk]):.0f} % der Punkte")
        p_s = schwelle_zweiphasig(kav, punkte)
        if p_s:
            schwellen[kav.kurz][name] = p_s
            print(f"    -> Strang wird (adiabat) zweiphasig, sobald p_LCCS unter {p_s:.0f} bar fällt"
                  + (" (Q-030 Option 2, ebenfalls 1200 m: Zweiphasengrenze am Kopf -> p_min auf 160 bar angehoben)"
                     if kav.kurz == "tief" else ""))

# ---- Abbildung 1: Kopfzustände im p-T-Diagramm -------------------------------------------------
FARBE = {"tief": "#00304F", "flach": "#EE7203"}
MARKER = {"50.000 Nm³/h": "o", "100.000 Nm³/h": "s"}
T_s = np.linspace(PropsSI("Ttriple", "CO2") + 10, PropsSI("Tcrit", "CO2"), 150)
fig, ax = plt.subplots(figsize=(10.5, 7))
ax.plot(T_s - 273.15, [PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_s], color="#1F4E79", lw=1.8,
        label="Sättigungslinie")
ax.plot(kb.T_KRIT, kb.P_KRIT, "o", color="#CA220E", ms=7)
for kav in kb.KAVERNEN:
    for name, punkte in erg[kav.kurz].items():
        a = [z["adiabat"] for z in punkte if z["adiabat"]]
        g = [z["gebirge"] for z in punkte if z["gebirge"]]
        ax.plot([k["T"] for k in a], [k["p"] for k in a], marker=MARKER[name], color=FARBE[kav.kurz], ls="none", ms=5,
                label=f"{kav.kurz}, {name}, adiabat")
        ax.plot([k["T"] for k in g], [k["p"] for k in g], marker=MARKER[name], color=FARBE[kav.kurz], ls="none", ms=5,
                mfc="white", label=f"{kav.kurz}, {name}, Gebirge")
for p, txt in ((P_DICHT, "dichte Übergabe 91 bar"), (P_GAS, "gasförmige Übergabe 30 bar")):
    ax.axhline(p, color="#007335", lw=1, ls="--")
    ax.text(-18, p + 1.5, txt, color="#007335", fontsize=8)
ax.set(xlim=(-20, 55), ylim=(0, 130), xlabel="Temperatur am Kopf [°C]", ylabel="Kopfdruck [bar]",
       title="Bohrlochkopf beim Ausspeichern: Band zwischen adiabat (gefüllt) und Gebirge (offen)")
ax.grid(alpha=0.3)
ax.legend(fontsize=7.5, loc="upper left", ncol=2)
fig.tight_layout()
fig.savefig(kb.ORDNER / "abb_K04_kopfzustand_pT.png", dpi=160)
print("\ngespeichert: abb_K04_kopfzustand_pT.png")

# ---- Abbildung 2: Kopfdruck, -temperatur und Geschwindigkeit über der Zeit ---------------------
fig, axs = plt.subplots(1, 3, figsize=(14, 4.8))
for kav in kb.KAVERNEN:
    for name, punkte in erg[kav.kurz].items():
        ls = "-" if "100" in name else ":"
        pts = [z for z in punkte if z["adiabat"]]
        t = [z["t"] for z in pts]
        axs[0].plot(t, [z["adiabat"]["p"] for z in pts], color=FARBE[kav.kurz], ls=ls, label=f"{kav.kurz}, {name}")
        axs[1].plot(t, [z["adiabat"]["T"] for z in pts], color=FARBE[kav.kurz], ls=ls)
        axs[1].plot(t, [z["adiabat"]["T_drossel_30"] for z in pts], color=FARBE[kav.kurz], ls=ls, alpha=0.4)
        axs[2].plot(t, [z["adiabat"]["v_max"] for z in pts], color=FARBE[kav.kurz], ls=ls)
axs[0].axhline(P_DICHT, color="#007335", ls="--", lw=1)
axs[2].axhline(kb.V_MAX_STRANG, color="#CA220E", ls="--", lw=1)
axs[0].set(xlabel="Zeit [d]", ylabel="Kopfdruck adiabat [bar]")
axs[1].set(xlabel="Zeit [d]", ylabel="T am Kopf (kräftig) / nach Drossel 30 bar (blass) [°C]")
axs[2].set(xlabel="Zeit [d]", ylabel="v_max im Strang [m/s]")
axs[0].legend(fontsize=8)
for a in axs:
    a.grid(alpha=0.3)
fig.suptitle("Ausspeichern, Kopfzustand im adiabaten Grenzfall (schnelle Förderung)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(kb.ORDNER / "abb_K04_kopf_zeit.png", dpi=150)
print("gespeichert: abb_K04_kopf_zeit.png")

kb.speichere_json("bohrlochkopf_ausspeicherung.json", dict(
    annahmen=dict(D_strang=kb.D_STRANG, f_darcy=kb.F_DARCY, v_max=kb.V_MAX_STRANG, p_dicht=P_DICHT, p_gas=P_GAS),
    p_lccs_strang_zweiphasig=schwellen,
    **erg))
