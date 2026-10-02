# -*- coding: utf-8 -*-
"""
Kaverne Schritt 03 - Ein- und Ausspeicherrate (reines CO₂)
============================================================================
Welche Rate verträgt die Kaverne - und was passiert bei 50.000 und
100.000 Nm³/h mit Druck, Temperatur und Phase des Kaverneninhalts?

Drei Grenzen bestimmen die Rate einer Kaverne:
  1  Druckänderungsrate an der LCCS ≤ 10 bar/d (Q-030, Q-089), vorsichtig
     6 bar/d (Q-028). Die zulässige Rate folgt aus der Dichteänderung je bar:
         ṁ_max = V · (∂ρ/∂p) · (dp/dt)_max            (Q-028 Fig. 5: "produced mass per bar")
     isotherm (langsam): (∂ρ/∂p)_T,  isentrop (schnell): (∂ρ/∂p)_s = 1/c²
  2  Phase in der Kaverne: beim Ausspeichern kühlt der Inhalt ab (Entspannung,
     Q-030: positiver Joule-Thomson-Koeffizient). Fällt er ins Zweiphasengebiet,
     ist der Druck kein Maß mehr für den Inhalt (Q-028 Kap. 3) und Flüssigkeit
     sammelt sich im Sumpf. "Grenzrate" = höchste konstante Rate, bei der der
     Inhalt bis p_min einphasig bleibt.
  3  Strömungsgeschwindigkeit im Förderstrang ≤ 20 m/s (Q-030) -> Schritt 04.

Kavernenbilanz (kaverne_bausteine.kavernenzyklus): ein ideal durchmischter
Knoten, Masse und innere Energie, Wärmeübergang UA zum Gebirge, Zyklus wie
Q-028: Ausspeichern bis p_min - 21,67 d Stillstand - Einspeichern (30 °C an der
LCCS) bis p_max - 21,67 d Stillstand.

Validierung: Q-028 selbst nachgerechnet (650.000 m³, 1150/1355 m, 55 °C,
135 -> 70 bar mit der höchsten Rate bei 6 bar/d). Q-028: Ende 77,6 bar /
33,1 °C, Raten etwa 90-600 t/h.

Ausgabe: Konsole, abb_K03_ratengrenze.png, abb_K03_zyklus.png,
abb_K03_zyklus_pT.png, kavernenzyklus.json (-> 04, 05, 06)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import kaverne_bausteine as kb

MED = kb.REIN
m_50, m_100 = kb.massenstrom(MED)
RATEN = {"50.000 Nm³/h": m_50, "100.000 Nm³/h": m_100}
print(f"Durchsatz: 50.000 Nm³/h = {m_50:.1f} kg/s = {m_50*86.4:.0f} t/d, "
      f"100.000 Nm³/h = {m_100:.1f} kg/s = {m_100*86.4:.0f} t/d")

# ---- 0) Validierung gegen Q-028 ------------------------------------------------------
Q028 = kb.Kaverne("Q-028 Validierungskaverne", "q028", 1150.0, 1355.0, 135.0, 70.0, 650000.0)
v = kb.kavernenzyklus(MED, Q028, 1000.0, phasen=[("aus", 70.0)], dpdt_max=kb.DPDT_VORSICHTIG,
                      dt=0.01, T_geb=55.0)
raten = [abs(x["m_dot"]) * 3.6 for x in v[:-1]]
print(f"\nValidierung Q-028 (UA = {Q028.UA:.0f} kW/K, 6 bar/d, höchste Rate):")
print(f"  Ende Ausspeichern: {v[-1]['p_mitte']:.1f} bar / {v[-1]['T']:.1f} °C   (Q-028: 77,6 bar / 33,1 °C)")
print(f"  Raten {min(raten):.0f}-{max(raten):.0f} t/h                (Q-028: ca. 90-600 t/h)")
print(f"  Inhalt {v[0]['m']:.0f} -> {v[-1]['m']:.0f} t, Dauer {v[-1]['t']:.1f} d")

# ---- 1) Grenze 1: Druckänderungsrate ----------------------------------------------------
def ratengrenze(kav, p_lccs, dpdt, art):
    T = kav.T_mitte
    pm = kb.p_mitte(MED, kav, p_lccs, T)
    if art == "isotherm":
        drho = MED.drho_dp(pm, T)
    else:
        drho = 1e5 / MED.schall(pm, T) ** 2           # (∂ρ/∂p)_s = 1/c², je bar
    return kav.volumen * drho * dpdt / 86400.0       # kg/s


grenze = {}
for kav in kb.KAVERNEN:
    pl = np.linspace(kav.p_min, kav.p_max, 80)
    grenze[kav.kurz] = dict(p=pl, **{f"{art}_{d:.0f}": np.array([ratengrenze(kav, p, d, art) for p in pl])
                                    for art in ("isotherm", "isentrop") for d in (kb.DPDT_VORSICHTIG, kb.DPDT_MAX)})

print("\nGrenze 1 - zulässige Rate aus 10 bar/d (isotherm / isentrop) [kg/s]:")
for kav in kb.KAVERNEN:
    g = grenze[kav.kurz]
    for p_ziel in (kav.p_max, 0.5 * (kav.p_max + kav.p_min), kav.p_min):
        i = int(np.argmin(abs(g["p"] - p_ziel)))
        print(f"  {kav.kurz:<6}{g['p'][i]:6.1f} bar: {g['isotherm_10'][i]:6.1f} / {g['isentrop_10'][i]:6.1f} kg/s")
    eng = g["p"][g["isotherm_10"] < m_100]
    if eng.size:
        print(f"         100.000 Nm³/h ({m_100:.1f} kg/s) überschreitet 10 bar/d (isotherm) "
              f"zwischen {eng.min():.0f} und {eng.max():.0f} bar an der LCCS")

# ---- 2) Kavernenbilanz bei 50.000 / 100.000 Nm³/h ---------------------------------------
erg = {}
for kav in kb.KAVERNEN:
    erg[kav.kurz] = {}
    for name, m_dot in RATEN.items():
        verlauf = kb.kavernenzyklus(MED, kav, m_dot)
        erg[kav.kurz][name] = dict(m_dot=m_dot, verlauf=verlauf, kw=kb.zyklus_kennwerte(verlauf))
    erg[kav.kurz]["grenzrate"] = kb.grenzrate(MED, kav)

for kav in kb.KAVERNEN:
    print(f"\n==== {kav.name}: UA {kav.UA:.0f} kW/K, Gebirge {kav.T_mitte:.1f} °C ====")
    for name in RATEN:
        r = erg[kav.kurz][name]
        aus, st1, ein, st2 = r["kw"]
        wgv = aus["m_start"] - aus["m_ende"]
        zp = (f"ZWEIPHASIG ab Tag {aus['t_zweiphasig']:.1f} (q bis {aus['q_max']:.2f})"
              if aus["zweiphasig"] else "einphasig")
        print(f"  {name} ({r['m_dot']:.1f} kg/s):")
        print(f"    aus   {aus['dauer']:5.1f} d, {aus['p_lccs_start']:.0f}->{aus['p_lccs_ende']:.0f} bar, "
              f"T {aus['T_start']:.1f}->{aus['T_min']:.1f} °C, {zp}")
        print(f"          Arbeitsgas {wgv:,.0f} t = {100 * wgv / aus['m_start']:.0f} % des Inhalts, "
              f"Rate in {100 * aus['anteil_begrenzt']:.0f} % der Zeit durch 10 bar/d gekürzt "
              f"(Mittel {aus['m_dot_mittel']:.1f} kg/s)".replace(",", "."))
        print(f"    still {st1['dauer']:5.1f} d: Druck erholt sich {st1['p_lccs_start']:.1f} -> {st1['p_lccs_ende']:.1f} bar, "
              f"T -> {st1['T_ende']:.1f} °C")
        print(f"    ein   {ein['dauer']:5.1f} d, T bis {ein['T_max']:.1f} °C, "
              f"gekürzt in {100 * ein['anteil_begrenzt']:.0f} % der Zeit")
        print(f"    still {st2['dauer']:5.1f} d: Druck fällt beim Abkühlen {st2['p_lccs_start']:.1f} -> {st2['p_lccs_ende']:.1f} bar")
    g = erg[kav.kurz]["grenzrate"]
    if g["rate"] is None:
        print("  Grenzrate: auch langsamstes Ausspeichern wird zweiphasig")
    elif not g["bindend"]:
        print(f"  Grenzrate: bis {g['rate']:.0f} kg/s einphasig - begrenzend ist allein die Druckänderungsrate")
    else:
        print(f"  Grenzrate (einphasig bis p_min): {g['rate']:.1f} kg/s = {kb.nm3h(MED, g['rate']):,.0f} Nm³/h"
              .replace(",", "."))

# ---- 3) Abbildung 1: Ratengrenze aus der Druckänderungsrate -------------------------------
FARBE = {"tief": "#00304F", "flach": "#EE7203"}
fig, axs = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
for ax, kav in zip(axs, kb.KAVERNEN):
    g = grenze[kav.kurz]
    ax.fill_between(g["p"], g["isentrop_10"], g["isotherm_10"], color=FARBE[kav.kurz], alpha=0.15,
                    label="10 bar/d: Band schnell (isentrop) bis langsam (isotherm)")
    ax.plot(g["p"], g["isotherm_10"], color=FARBE[kav.kurz], lw=2)
    ax.plot(g["p"], g["isentrop_10"], color=FARBE[kav.kurz], lw=2, ls="--")
    ax.plot(g["p"], g["isotherm_6"], color="#888", lw=1.2, ls=":", label="6 bar/d isotherm (Q-028)")
    for name, m in RATEN.items():
        ax.axhline(m, color="#CA220E", lw=1, ls="-." if "50" in name[:3] else "-")
        ax.text(kav.p_max - 2, m + 3, name, ha="right", fontsize=8, color="#CA220E")
    if erg[kav.kurz]["grenzrate"]["bindend"] and erg[kav.kurz]["grenzrate"]["rate"]:
        ax.axhline(erg[kav.kurz]["grenzrate"]["rate"], color="#7030A0", lw=1.5)
        ax.text(kav.p_min + 1, erg[kav.kurz]["grenzrate"]["rate"] + 3, "Grenzrate einphasig",
                fontsize=8, color="#7030A0")
    ax.axvline(kb.P_KRIT, color="#888", ls=":", lw=1)
    ax.set(xlabel="Druck an der LCCS [bar]", title=kav.name, ylim=(0, 400))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7.5, loc="upper right")
axs[0].set_ylabel("zulässige Ein-/Ausspeicherrate [kg/s]")
fig.suptitle("Grenze 1: ṁ_max = V·(∂ρ/∂p)·(dp/dt)_max - hohe Raten nur nahe p_krit möglich (Q-028)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(kb.ORDNER / "abb_K03_ratengrenze.png", dpi=160)
print("\ngespeichert: abb_K03_ratengrenze.png")

# ---- 4) Abbildung 2: Zyklus über der Zeit -----------------------------------------------------
STIL = {"50.000 Nm³/h": ":", "100.000 Nm³/h": "-"}
fig, axs = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
for zeile, kav in enumerate(kb.KAVERNEN):
    for name in RATEN:
        vl = erg[kav.kurz][name]["verlauf"]
        t = [x["t"] for x in vl]
        axs[zeile, 0].plot(t, [x["p_lccs"] for x in vl], color=FARBE[kav.kurz], ls=STIL[name], lw=1.8, label=name)
        axs[zeile, 1].plot(t, [x["T"] for x in vl], color=FARBE[kav.kurz], ls=STIL[name], lw=1.8)
        axs[zeile, 2].plot(t, [x["m"] / 1000 for x in vl], color=FARBE[kav.kurz], ls=STIL[name], lw=1.8)
        zp = [x for x in vl if x["q"] is not None]
        if zp:
            axs[zeile, 1].plot([x["t"] for x in zp], [x["T"] for x in zp], "x", color="#CA220E", ms=3)
    axs[zeile, 1].axhline(kb.T_KRIT, color="#CA220E", ls="--", lw=1)
    axs[zeile, 1].axhline(kav.T_mitte, color="#555", ls=":", lw=1)
    axs[zeile, 0].axhline(kb.P_KRIT, color="#888", ls=":", lw=1)
    axs[zeile, 0].set_ylabel(f"{kav.kurz}: p an der LCCS [bar]")
    axs[zeile, 1].set_ylabel("T Kaverne [°C]  (x = zweiphasig)")
    axs[zeile, 2].set_ylabel("Inhalt [kt]")
    axs[zeile, 0].legend(fontsize=8)
for a in axs.flat:
    a.grid(alpha=0.3)
for a in axs[1]:
    a.set_xlabel("Zeit [d]")
fig.suptitle("Speicherzyklus nach Q-028: ausspeichern - 21,67 d Stillstand - einspeichern - 21,67 d Stillstand "
             "(10 bar/d, UA nach Q-028)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(kb.ORDNER / "abb_K03_zyklus.png", dpi=150)
print("gespeichert: abb_K03_zyklus.png")

# ---- 5) Abbildung 3: Zustandspfad der Kaverne im p-T-Diagramm ------------------------------------
T_s = np.linspace(PropsSI("Ttriple", "CO2") + 20, PropsSI("Tcrit", "CO2"), 150)
fig, ax = plt.subplots(figsize=(9.5, 6.5))
ax.plot(T_s - 273.15, [PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_s], color="#1F4E79", lw=1.8,
        label="Sättigungslinie")
ax.plot(kb.T_KRIT, kb.P_KRIT, "o", color="#CA220E", ms=7)
for kav in kb.KAVERNEN:
    for name in RATEN:
        vl = erg[kav.kurz][name]["verlauf"]
        ax.plot([x["T"] for x in vl], [x["p_mitte"] for x in vl], color=FARBE[kav.kurz], ls=STIL[name], lw=1.6,
                label=f"{kav.kurz}, {name}")
ax.set(xlim=(0, 60), ylim=(0, 240), xlabel="Temperatur Kaverneninhalt [°C]", ylabel="Druck Kavernenmitte [bar]",
       title="Zustandspfad des Kaverneninhalts über einen Zyklus")
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(kb.ORDNER / "abb_K03_zyklus_pT.png", dpi=160)
print("gespeichert: abb_K03_zyklus_pT.png")


# ---- 6) Übergabe -------------------------------------------------------------------------------
def ausduennen(vl, k=10):
    """Jeden k-ten Zeitschritt plus jeden Abschnittswechsel - reicht für 04/06 und Diagramme."""
    return [x for i, x in enumerate(vl) if i % k == 0 or i == len(vl) - 1 or x["art"] != vl[i - 1]["art"]]


kb.speichere_json("kavernenzyklus.json", dict(
    validierung_q028=dict(p_ende=v[-1]["p_mitte"], T_ende=v[-1]["T"], rate_min_th=min(raten), rate_max_th=max(raten),
                          quelle=dict(p_ende=77.6, T_ende=33.1, rate_th=(90, 600))),
    **{kav.kurz: dict(grenzrate=erg[kav.kurz]["grenzrate"],
                      raten={name: dict(m_dot=erg[kav.kurz][name]["m_dot"], kennwerte=erg[kav.kurz][name]["kw"],
                                        verlauf=ausduennen(erg[kav.kurz][name]["verlauf"]))
                             for name in RATEN})
       for kav in kb.KAVERNEN}))
