# -*- coding: utf-8 -*-
"""
Kaverne Schritt 05 - Worst-Case-Gemisch gegenüber reinem CO₂ in der Kaverne
============================================================================
Dieselben Rechnungen wie 01-04, jetzt mit dem Worst-Case-Gemisch der
Einspeicherung (95 % CO₂, 2,4 % N₂, 1 % Ar, 1 % CH₄, 0,5 % H₂, 0,1 % CO;
gemisch_worstcase.py) und direkt neben reinem CO₂:

  a  Stillstand: Kopfdruck voll / leer (Zieldruck Einspeicherung)
  b  Arbeitsgas isotherm (TGV, CGV, WGV)
  c  Ratengrenze aus 10 bar/d
  d  Kavernenbilanz bei 50.000 / 100.000 Nm³/h: Abkühlung, Phasengrenze
  e  Kopfzustand beim Ausspeichern (adiabat), Anfang und Ende

Warum sich das Gemisch anders verhält (Phasengrenze aus gemisch_worstcase.py):
  reines CO₂ hat eine Siedelinie bis zum kritischen Punkt 31,0 °C / 73,8 bar.
  Das Gemisch hat ein Zweiphasengebiet bis zur Cricondenbar 82,2 bar und zur
  Cricondentherm 28,1 °C. Die leichten Begleitstoffe (N₂, Ar, H₂, CH₄)
  senken die Dichte im dichten Bereich und weiten das Zweiphasengebiet zu
  höheren Drücken - die Flüssigkeit entsteht beim Gemisch also schon bei
  höherem Druck, aber erst bei tieferer Temperatur.

Gemisch im Zweiphasengebiet: die Kavernenbilanz endet dort, weil der schnelle
(ρ, T)-Flash dort nur metastabile Werte liefert (kaverne_bausteine.Medium).
Für die Auslegung reicht der Zeitpunkt, an dem die Grenze erreicht wird.

Ausgabe: Konsole, abb_K05_gemisch_vs_rein.png, abb_K05_kaverne_huelle_pT.png,
gemisch_vs_rein.json (-> 06)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import kaverne_bausteine as kb

REIN, GEM = kb.REIN, kb.gemisch()
STOFFE = (REIN, GEM)
pg = GEM.stoff.pg
print(f"Phasengrenze Gemisch: krit. Punkt {pg['krit'][0]:.1f} °C / {pg['krit'][1]:.1f} bar, "
      f"Cricondenbar {pg['cricondenbar'][1]:.1f} bar, Cricondentherm {pg['cricondentherm'][0]:.1f} °C "
      f"(reines CO₂: {kb.T_KRIT:.1f} °C / {kb.P_KRIT:.1f} bar)")

erg = {kav.kurz: {} for kav in kb.KAVERNEN}
for kav in kb.KAVERNEN:
    for med in STOFFE:
        e = {}
        # a) Stillstand
        e["kopf_voll"] = kb.kopfdruck(med, kav, kav.p_max)
        e["kopf_leer"] = kb.kopfdruck(med, kav, kav.p_min)
        # b) Arbeitsgas isotherm
        e["TGV"] = kb.inventar(med, kav, kav.p_max)
        e["CGV"] = kb.inventar(med, kav, kav.p_min)
        e["WGV"] = e["TGV"] - e["CGV"]
        # c) Ratengrenze 10 bar/d, isotherm
        e["rate_dpdt"] = {f"{p:.0f}": kav.volumen * med.drho_dp(kb.p_mitte(med, kav, p, kav.T_mitte), kav.T_mitte)
                          * kb.DPDT_MAX / 86400 for p in (kav.p_max, 0.5 * (kav.p_max + kav.p_min), kav.p_min)}
        # d) Kavernenbilanz
        e["raten"] = {}
        for name, m_dot in zip(("50.000 Nm³/h", "100.000 Nm³/h"), kb.massenstrom(med)):
            vl = kb.kavernenzyklus(med, kav, m_dot, phasen=[("aus", kav.p_min)], stopp_bei_zweiphasig=True)
            kw = kb.zyklus_kennwerte(vl)[0]
            ende = vl[-1]
            # e) Kopfzustand adiabat am Anfang und am Ende (bzw. an der Phasengrenze)
            koepfe = []
            # Gemisch im Zweiphasengebiet braucht den freien Flash (~55 ms) -> gröberes Raster (30 m)
            n = 40 if med.ist_gemisch else 300
            for x in (vl[0], ende):
                _, k = kb.strang_aufwaerts(med, kav, x["p_lccs"], x["T"], m_dot, n=n)
                koepfe.append(dict(t=x["t"], p_lccs=x["p_lccs"], T_kav=x["T"],
                                   kopf=None if k is None else dict(p=k["p"], T=k["T"], rho=k["rho"], v=k["v_max"],
                                                                    zweiphasig_im_strang=k["zweiphasig_im_strang"])))
            e["raten"][name] = dict(m_dot=m_dot, kennwerte=kw, verlauf=[dict(t=x["t"], p_lccs=x["p_lccs"], p_mitte=x["p_mitte"],
                                    T=x["T"], m=x["m"]) for x in vl[::5]], koepfe=koepfe,
                                    zweiphasig=ende["q"] is not None, p_ende=ende["p_lccs"], T_ende=ende["T"])
        erg[kav.kurz][med.kurz] = e

# ---- Konsole ---------------------------------------------------------------------------------
print(f"\nKontrolle gegen die Einspeicherung (Gemisch, Excel-Mappe): Kopfdruck tief/voll 114,931 bar -> "
      f"{erg['tief']['gem']['kopf_voll']:.3f} bar {kb.ok(abs(erg['tief']['gem']['kopf_voll'] - 114.931) < 0.01)}")
for kav in kb.KAVERNEN:
    r, g = erg[kav.kurz]["rein"], erg[kav.kurz]["gem"]
    print(f"\n==== {kav.name} ====                 rein        Gemisch")
    print(f"  Kopfdruck voll (Stillstand)  {r['kopf_voll']:8.2f}    {g['kopf_voll']:8.2f} bar  ({g['kopf_voll']-r['kopf_voll']:+.2f})")
    print(f"  Kopfdruck leer (Stillstand)  {r['kopf_leer']:8.2f}    {g['kopf_leer']:8.2f} bar  ({g['kopf_leer']-r['kopf_leer']:+.2f})")
    print(f"  TGV                          {r['TGV']/1e3:8.1f}    {g['TGV']/1e3:8.1f} kt   ({100*(g['TGV']/r['TGV']-1):+.1f} %)")
    print(f"  WGV isotherm                 {r['WGV']/1e3:8.1f}    {g['WGV']/1e3:8.1f} kt   "
          f"({100*r['WGV']/r['TGV']:.0f} % / {100*g['WGV']/g['TGV']:.0f} % des Inhalts)")
    for p in r["rate_dpdt"]:
        print(f"  Ratengrenze 10 bar/d @{p:>4} bar {r['rate_dpdt'][p]:8.1f}    {g['rate_dpdt'][p]:8.1f} kg/s")
    for name in r["raten"]:
        for kurz, e in (("rein", r), ("Gemisch", g)):
            x = e["raten"][name]
            kw = x["kennwerte"]
            zust = (f"ZWEIPHASIG nach {kw['dauer']:.1f} d bei {x['p_ende']:.1f} bar / {x['T_ende']:.1f} °C"
                    if x["zweiphasig"] else f"einphasig bis p_min, T_min {kw['T_min']:.1f} °C, {kw['dauer']:.1f} d")
            koepfe = " | ".join(f"{k['p_lccs']:.0f}->{k['kopf']['p']:.0f} bar/{k['kopf']['T']:.0f} °C"
                                + ("*" if k["kopf"]["zweiphasig_im_strang"] else "")
                                for k in x["koepfe"] if k["kopf"])
            print(f"  {name:<14} {kurz:<8} {x['m_dot']:5.1f} kg/s: {zust}")
            print(f"  {'':<24}Kopf adiabat (LCCS -> Kopf, * = Strang zweiphasig): {koepfe}")

# ---- Abbildung 1: Kennzahlen nebeneinander ------------------------------------------------------
FARBE = {"rein": "#00304F", "gem": "#CA220E"}
fig, axs = plt.subplots(1, 3, figsize=(14, 4.8))
x = np.arange(len(kb.KAVERNEN))
for j, (med, dx) in enumerate(zip(STOFFE, (-0.2, 0.2))):
    e = [erg[k.kurz][med.kurz] for k in kb.KAVERNEN]
    axs[0].bar(x + dx, [a["kopf_voll"] for a in e], 0.38, color=FARBE[med.kurz], alpha=0.85, label=med.name)
    axs[0].bar(x + dx, [a["kopf_leer"] for a in e], 0.38, color="white", alpha=0.6, hatch="//", edgecolor=FARBE[med.kurz])
    axs[1].bar(x + dx, [a["TGV"] / 1e3 for a in e], 0.38, color=FARBE[med.kurz], alpha=0.35)
    axs[1].bar(x + dx, [a["WGV"] / 1e3 for a in e], 0.38, color=FARBE[med.kurz], alpha=0.85)
    axs[2].bar(x + dx, [a["raten"]["100.000 Nm³/h"]["T_ende"] for a in e], 0.38, color=FARBE[med.kurz], alpha=0.85)
for a, t in zip(axs, ("Kopfdruck Stillstand [bar]\n(voll gefüllt, leer schraffiert)",
                      "Inhalt [kt] (blass: TGV, kräftig: WGV isotherm)",
                      "T Kaverne am Ende des Ausspeicherns bzw.\nan der Phasengrenze, 100.000 Nm³/h [°C]")):
    a.set_xticks(x)
    a.set_xticklabels([k.kurz for k in kb.KAVERNEN])
    a.set_title(t, fontsize=9.5)
    a.grid(alpha=0.3, axis="y")
axs[2].axhline(kb.T_KRIT, color="#555", ls="--", lw=1)
axs[2].axhline(pg["cricondentherm"][0], color=FARBE["gem"], ls=":", lw=1)
axs[0].legend(fontsize=8)
fig.suptitle("Kaverne: Worst-Case-Gemisch gegenüber reinem CO₂", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(kb.ORDNER / "abb_K05_gemisch_vs_rein.png", dpi=150)
print("\ngespeichert: abb_K05_gemisch_vs_rein.png")

# ---- Abbildung 2: Kavernenzustand beim Ausspeichern gegen die Phasengrenzen --------------------
T_s = np.linspace(PropsSI("Ttriple", "CO2") + 20, PropsSI("Tcrit", "CO2"), 150)
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.plot(T_s - 273.15, [PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_s], color=FARBE["rein"], lw=1.5,
        label="Sättigungslinie reines CO₂")
huelle_T = np.concatenate([pg["T_tau"], pg["T_blase"]])
huelle_p = np.concatenate([pg["p_tau"], pg["p_blase"]])
ax.fill(huelle_T, huelle_p, color=FARBE["gem"], alpha=0.12, lw=0)
ax.plot(huelle_T, huelle_p, color=FARBE["gem"], lw=1.5, label="Zweiphasengebiet Gemisch")
STIL = {"tief": "-", "flach": "--"}
for kav in kb.KAVERNEN:
    for med in STOFFE:
        vl = erg[kav.kurz][med.kurz]["raten"]["100.000 Nm³/h"]["verlauf"]
        ax.plot([v["T"] for v in vl], [v["p_mitte"] for v in vl], color=FARBE[med.kurz], ls=STIL[kav.kurz], lw=2,
                label=f"{kav.kurz}, {med.name}, 100.000 Nm³/h")
        ax.plot(vl[-1]["T"], vl[-1]["p_mitte"], "o", color=FARBE[med.kurz], ms=5)
ax.set(xlim=(0, 55), ylim=(20, 230), xlabel="Temperatur Kaverneninhalt [°C]", ylabel="Druck Kavernenmitte [bar]",
       title="Ausspeichern mit 100.000 Nm³/h: Kavernenzustand bis p_min bzw. bis zur Phasengrenze")
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(kb.ORDNER / "abb_K05_kaverne_huelle_pT.png", dpi=160)
print("gespeichert: abb_K05_kaverne_huelle_pT.png")

kb.speichere_json("gemisch_vs_rein.json", dict(
    phasengrenze_gemisch=dict(krit=pg["krit"], cricondenbar=pg["cricondenbar"], cricondentherm=pg["cricondentherm"]),
    **erg))
