# -*- coding: utf-8 -*-
"""
Rechenschritte 01-04 der Kaverne - einmal programmiert, für beide Stoffe genutzt
============================================================================
Die Skripte in Reines_CO2/ und Begleitstoffe_CO2/ rufen diese Funktionen mit ihrem
Stoff auf (reines CO₂ bzw. Worst-Case-Gemisch) und legen Ergebnisse (JSON) und
Abbildungen (PNG) in ihrem eigenen Ordner ab. So rechnen beide Ordner garantiert
gleich, und eine Änderung wirkt auf beide.

  schritt_01  Stillstand und Zieldruck im Betrieb: ruhende Säule (voll, Grenzfall, leer)
              und strömende Säule beim Einspeisen mit S1 / S2 (Kopplung Einspeicherung)
  schritt_02  Arbeitsgas, Kissengas und Teufenfenster (warum 1200 m)
  schritt_03  Ratengrenze aus 10 bar/d, Kavernenbilanz über den Zyklus (S1/S2,
              50.000/100.000 Nm³/h, Stillstand 21,67 d gegen kontinuierlich), Grenzrate
  schritt_04  Bohrlochkopf: Kopfdruckfenster beim Ein- und Ausspeichern (Regelgröße),
              Phase im Strang, Drossel, Reibungseinfluss

Alle Annahmen und Fundstellen: kaverne_bausteine.py.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import kaverne_bausteine as kb

KAV = kb.TIEF
FARBE_S = {"S1": "#007335", "S2": "#0476D9"}
STIL_R = {"50.000 Nm³/h": ":", "100.000 Nm³/h": "-"}
STIL_ST = {"Stillstand 21,67 d (Q-028)": "-", "kontinuierlich (0 d)": "--"}
ROT, BLAU_D, GRAU = "#CA220E", "#00304F", "#8C8C8C"
RATE_A = "100.000 Nm³/h"                    # Auslegungsrate
ST_A = "Stillstand 21,67 d (Q-028)"         # Auslegungsbetriebsweise


def _titel(med):
    return "reines CO₂" if not med.ist_gemisch else "Worst-Case-Gemisch"


def phasengrenze_zeichnen(ax, med, T_min=-20.0):
    """Siedelinie (rein) bzw. Zweiphasengebiet (Gemisch, mit Siedelinie rein zum Vergleich)."""
    T_s = np.linspace(max(PropsSI("Ttriple", "CO2"), T_min + 273.15), PropsSI("Tcrit", "CO2"), 150)
    p_s = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_s]) / 1e5
    if not med.ist_gemisch:
        ax.plot(T_s - 273.15, p_s, color="#1F4E79", lw=1.8, label="Sättigungslinie reines CO₂")
        ax.plot(kb.T_KRIT, kb.P_KRIT, "o", color=ROT, ms=6)
        return
    ax.plot(T_s - 273.15, p_s, color=GRAU, lw=1.0, ls="--", label="Sättigungslinie reines CO₂ (Vergleich)")
    pg = med.stoff.pg
    T_h = np.concatenate([pg["T_tau"], pg["T_blase"]])
    p_h = np.concatenate([pg["p_tau"], pg["p_blase"]])
    ax.fill(T_h, p_h, color=ROT, alpha=0.13, lw=0)
    ax.plot(T_h, p_h, color=ROT, lw=1.6, label="Zweiphasengebiet Gemisch")


def _zweiphasig_maske(med, profil):
    """True, wo die ruhende Säule auf der Siedelinie (rein) bzw. im Zweiphasengebiet (Gemisch) liegt."""
    return np.array([med.in_huelle(p, T) if med.ist_gemisch else
                     (T < kb.T_KRIT and abs(p - PropsSI("P", "T", T + 273.15, "Q", 0, "CO2") / 1e5)
                      / (PropsSI("P", "T", T + 273.15, "Q", 0, "CO2") / 1e5) < 0.003)
                     for z, p, T, rho in profil])


def _alle_50m(profil, spalten=4):
    """Profil (von oben nach unten) auf 50-m-Raster für die Excel-Diagramme."""
    z = np.array([float(r[0]) for r in profil])
    raster = np.arange(0.0, KAV.z_lccs + 0.1, 50.0)
    return [[float(zz)] + [float(np.interp(zz, z, [float(r[k]) for r in profil])) for k in range(1, spalten)]
            for zz in raster]


# =============================================================================================
def schritt_01(med, ordner):
    """Stillstand (ruhende Säule) und Zieldruck im Betrieb (strömende Säule beim Einspeisen)."""
    print(f"\n######## Schritt 01 - {_titel(med)}: Stillstand und Zieldruck im Betrieb ########")
    p_lith = 2200.0 * kb.G * KAV.z_lccs / 1e5            # Q-003 Kap. 4.2: 2200 kg/m³ (Einordnung)
    try:
        p_grenz = kb.p_lccs_fuer_kopf(med, KAV, med.p_grenze)
    except RuntimeError:
        p_grenz = np.nan
    faelle = [("voll", KAV.p_max), ("Grenzfall", p_grenz), ("leer", KAV.p_min)]
    saeulen = {}
    for name, pl in faelle:
        p_kopf, profil = kb.gassaeule(med, KAV, pl)
        zp = _zweiphasig_maske(med, profil)
        pm = kb.p_mitte(med, KAV, pl, KAV.T_mitte)
        saeulen[name] = dict(p_lccs=pl, p_kopf=p_kopf, profil=profil,
                             zweiphasig_bereich=(float(profil[zp, 0].min()), float(profil[zp, 0].max())) if zp.any() else None,
                             p_mitte=pm, rho_kaverne=med.rho(pm, KAV.T_mitte), phase_kaverne=med.phase(pm, KAV.T_mitte),
                             rho_kopf=float(profil[0, 3]), rho_lccs=float(profil[-1, 3]),
                             phase_kopf=med.phase(p_kopf, kb.T_OBERFLAECHE))
    # Zieldruck im Betrieb: strömende Säule beim Einspeisen (gekoppelt an S1 / S2)
    betrieb = {}
    for szen in kb.SZENARIEN:
        betrieb[szen] = {}
        for rate, m in kb.raten(med).items():
            betrieb[szen][rate] = kb.zieldruck_einspeisen(med, KAV, szen, m)
    # Reibungseinfluss beim Einspeisen (gleiche Kopf-Enthalpie, f = 0)
    for szen in kb.SZENARIEN:
        z = betrieb[szen][RATE_A]
        _, k0 = kb.kopf_einspeisen(med, KAV, KAV.p_max, z["h_kopf"], z["m_dot"], f=0.0)
        z["p_kopf_ohne_reibung"] = k0["p"]

    # ---- Konsole
    print(f"LCCS {KAV.z_lccs:.0f} m ({KAV.T_lccs:.1f} °C), Kavernenmitte {KAV.z_mitte:.0f} m ({KAV.T_mitte:.1f} °C), "
          f"V = {kb.tsd(KAV.volumen)} m³; p_max {KAV.p_max:.0f} bar = {KAV.p_max/p_lith:.2f}·Gebirgsdruck")
    for name, s in saeulen.items():
        txt = f"  Stillstand {name:<9} LCCS {s['p_lccs']:6.1f} bar -> Kopf {s['p_kopf']:6.2f} bar ({s['phase_kopf']})"
        if s["zweiphasig_bereich"]:
            txt += f"; zweiphasig {s['zweiphasig_bereich'][0]:.0f}-{s['zweiphasig_bereich'][1]:.0f} m"
        print(txt)
    print(f"  Grenzfall: Kopf = {kb.de(med.p_grenze)} bar ({'p_krit' if not med.ist_gemisch else 'Cricondenbar'}) "
          f"bei {p_grenz:.1f} bar an der LCCS")
    print("  Zieldruck im Betrieb (210 bar an der LCCS, strömend, adiabat, Pumpe η = 0,80):")
    for szen, rr in betrieb.items():
        for rate, z in rr.items():
            print(f"    {szen} {rate:<14} Kopf {z['p_kopf']:6.2f} bar / {z['T_kopf']:5.1f} °C, LCCS {z['T_lccs']:5.1f} °C, "
                  f"Pumpe {z['w_pumpe']:.2f} kJ/kg, v_Kopf {z['v_kopf']:.2f} m/s"
                  + (f", ohne Reibung {z['p_kopf_ohne_reibung']:.2f} bar" if "p_kopf_ohne_reibung" in z else ""))

    # ---- Abbildung 1: Säulen über der Teufe
    fig, axs = plt.subplots(1, 3, figsize=(14, 6.8), sharey=True)
    stil = {"voll": "-", "Grenzfall": "--", "leer": ":"}
    z_t = np.linspace(0, KAV.z_lccs, 50)
    axs[0].plot(kb.T_gebirge(z_t), z_t, color="#333", lw=2, label="Gebirge (Stillstand)")
    for name, s in saeulen.items():
        pr = s["profil"]
        rho = pr[:, 3].copy()
        rho[_zweiphasig_maske(med, pr)] = np.nan
        axs[1].plot(pr[:, 1], pr[:, 0], color=BLAU_D, ls=stil[name], lw=2,
                    label=f"Stillstand {name}: Kopf {kb.de(s['p_kopf'])} bar")
        axs[2].plot(rho, pr[:, 0], color=BLAU_D, ls=stil[name], lw=2)
    for szen, rr in betrieb.items():
        z = rr[RATE_A]
        pr = z["profil"]
        zz = np.array([float(r[0]) for r in pr])
        axs[0].plot([float(r[2]) for r in pr], zz, color=FARBE_S[szen], lw=2, label=f"Einspeisen {szen}")
        axs[1].plot([float(r[1]) for r in pr], zz, color=FARBE_S[szen], lw=2,
                    label=f"Einspeisen {szen} (voll, {RATE_A}): Kopf {kb.de(z['p_kopf'])} bar")
        axs[2].plot([float(r[3]) for r in pr], zz, color=FARBE_S[szen], lw=2)
    axs[0].axvline(med.T_ct, color=ROT, ls="--", lw=1)
    axs[1].axvline(med.p_grenze, color=GRAU, ls=":", lw=1.2)
    axs[0].set(title="Temperatur [°C]", ylabel="Teufe [m]", xlim=(0, 60), ylim=(KAV.z_lccs * 1.03, 0))
    axs[1].set(title="Druck [bar]", xlim=(0, 230))
    axs[2].set(title="Dichte [kg/m³]", xlim=(0, 1000))
    axs[0].legend(fontsize=8, loc="lower left")
    axs[1].legend(fontsize=7.5, loc="lower left")
    for a in axs:
        a.grid(alpha=0.3)
    fig.suptitle(f"Säule im Bohrloch, {_titel(med)}: Stillstand (Gebirgstemperatur, nach Q-028 Fig. 3) und "
                 f"Einspeisen (strömend, adiabat)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(ordner / "abb_K01_gassaeulen.png", dpi=160)
    plt.close(fig)

    # ---- Abbildung 2: Betriebsfenster im p-T-Diagramm
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    phasengrenze_zeichnen(ax, med)
    for name, s in saeulen.items():
        pr = s["profil"]
        ax.plot(pr[:, 2], pr[:, 1], color=BLAU_D, ls=stil[name], lw=1.8, label=f"Stillstand {name}")
    for szen, rr in betrieb.items():
        pr = rr[RATE_A]["profil"]
        ax.plot([float(r[2]) for r in pr], [float(r[1]) for r in pr], color=FARBE_S[szen], lw=2.2,
                label=f"Einspeisen {szen} ({RATE_A})")
    ax.plot([KAV.T_lccs] * 2, [KAV.p_min, KAV.p_max], color=BLAU_D, lw=6, alpha=0.6, solid_capstyle="butt",
            label=f"Kaverne an der LCCS: {kb.de(KAV.p_min, 0)}–{kb.de(KAV.p_max, 0)} bar")
    ax.set(xlim=(-10, 70), ylim=(0, 240), xlabel="Temperatur [°C]", ylabel="Druck [bar]",
           title=f"Betriebsfenster Bohrloch und Kaverne, {_titel(med)}")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(ordner / "abb_K01_betriebsfenster_pT.png", dpi=160)
    plt.close(fig)

    erg = dict(kaverne=dict(name=KAV.name, z_lccs=KAV.z_lccs, z_mitte=KAV.z_mitte, T_lccs=KAV.T_lccs,
                            T_mitte=KAV.T_mitte, p_max=KAV.p_max, p_min=KAV.p_min, volumen=KAV.volumen, UA=KAV.UA),
               p_lith=p_lith, p_grenze=med.p_grenze, p_lccs_grenzfall=p_grenz,
               saeulen={n: dict({k: v for k, v in s.items() if k != "profil"}, profil_50m=_alle_50m(s["profil"]))
                        for n, s in saeulen.items()},
               betrieb={szen: {rate: dict({k: v for k, v in z.items() if k not in ("profil", "pumpe")},
                                          pumpe=dict(h1=z["pumpe"]["h1"], h2s=z["pumpe"]["h2s"], h2=z["pumpe"]["h2"],
                                                     T2=z["pumpe"]["T2"], rho1=z["pumpe"]["rho1"]),
                                          profil_50m=_alle_50m([(r[0], r[1], r[2], r[3]) for r in z["profil"]]))
                               for rate, z in rr.items()} for szen, rr in betrieb.items()})
    kb.speichere_json(ordner, "kaverne_stillstand.json", erg)
    return erg


# =============================================================================================
T_MARGE = 3.0      # K über T_krit bzw. Cricondentherm in Kavernenmitte (eigene Annahme, Sicherheitsabstand)
DBI_Q030_TAB3 = [("Option 2", 240, 50, 825.637), ("Option 2", 160, 50, 722.101), ("Option 2", 100, 50, 384.334),
                 ("Option 2", 55, 50, 119.482), ("Option 1", 260, 84, 677.684), ("Option 1", 70, 84, 131.309),
                 ("Option 3", 50, 33, 120.816), ("Option 3", 40, 33, 87.986)]


def schritt_02(med, ordner):
    """Arbeitsgas, Kissengas (isotherm / isentrop) und Teufenfenster."""
    print(f"\n######## Schritt 02 - {_titel(med)}: Arbeitsgas und Teufenfenster ########")
    still = kb.lade_json(ordner, "kaverne_stillstand.json", "01")
    dbi = []
    if not med.ist_gemisch:
        for opt, p, T, r in DBI_Q030_TAB3:
            rc = PropsSI("D", "P", p * 1e5, "T", T + 273.15, "CO2")
            dbi.append(dict(option=opt, p=p, T=T, rho_dbi=r, rho_coolprop=rc, abw=rc / r - 1))
        print("Kontrolle Dichte CoolProp gegen DBI (Q-030 Tab. 3): Option 2 (= Referenzkaverne) "
              f"größte Abweichung {100 * max(abs(d['abw']) for d in dbi[:4]):.3f} %")

    def inhalt_isentrop(p_lccs_min):
        T0 = KAV.T_mitte
        pm0 = kb.p_mitte(med, KAV, KAV.p_max, T0)
        s = med.s(pm0, T0)
        pm, T = p_lccs_min + 2.0, T0
        for _ in range(8):
            zs = med.zustand_ps(pm, s, T)
            T, rho = zs["T"], zs["rho"]
            pm = p_lccs_min + rho * kb.G * (KAV.z_mitte - KAV.z_lccs) / 1e5
        zs = med.zustand_ps(pm, s, T)
        return zs["rho"] * KAV.volumen / 1000, zs["T"], zs["q"]

    TGV = kb.inventar(med, KAV, KAV.p_max)
    varianten = [("geomechanisch (Q-028)", KAV.p_min),
                 (("überkritisch (p_krit)" if not med.ist_gemisch else "über der Cricondenbar"), med.p_grenze),
                 ("Bohrloch dicht (Grenzfall 01)", still["p_lccs_grenzfall"])]
    zeilen = []
    for name, pmin in varianten:
        if pmin is None or not KAV.p_min <= pmin < KAV.p_max:
            continue
        CGV_iso = kb.inventar(med, KAV, pmin)
        try:
            CGV_ise, T_ise, q_ise = inhalt_isentrop(pmin)
        except (RuntimeError, ValueError):
            CGV_ise, T_ise, q_ise = np.nan, np.nan, None
        zeilen.append(dict(variante=name, p_min=pmin, CGV_iso=CGV_iso, CGV_ise=CGV_ise, T_ise=T_ise, q_ise=q_ise,
                           WGV_iso=TGV - CGV_iso, WGV_ise=TGV - CGV_ise,
                           anteil_iso=(TGV - CGV_iso) / TGV, anteil_ise=(TGV - CGV_ise) / TGV))
    z_bezug_min = (med.T_ct + T_MARGE - kb.T_OBERFLAECHE) / kb.GRADIENT
    z_lccs_min = z_bezug_min - kb.DZ_BEZUG
    z_lccs_max = med.p_grenze / kb.GRAD_PMIN
    print(f"TGV {kb.tsd(TGV)} t bei {KAV.p_max:.0f} bar / {KAV.T_mitte:.1f} °C")
    for z in zeilen:
        print(f"  p_min {z['variante']:<30}{z['p_min']:6.1f} bar | isotherm WGV {kb.tsd(z['WGV_iso'])} t "
              f"({100*z['anteil_iso']:.0f} %) | isentrop {100*z['anteil_ise']:.0f} %, T {z['T_ise']:.1f} °C")
    print(f"Teufenfenster: LCCS {z_lccs_min:.0f}-{z_lccs_max:.0f} m -> Referenzkaverne 1200 m "
          f"{kb.ok(z_lccs_min <= KAV.z_lccs <= z_lccs_max)}")

    # Dichtekurve bei Gebirgstemperatur (für Abbildung und Excel)
    pp = np.arange(20.0, 231.0, 5.0)
    kurve = [[float(p), float(med.rho(p, KAV.T_mitte))] for p in pp]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.5, 6), gridspec_kw=dict(width_ratios=[1.3, 1]))
    ax.plot([k[0] for k in kurve], [k[1] for k in kurve], color=BLAU_D, lw=1.2, alpha=0.6)
    pw = np.linspace(KAV.p_min, KAV.p_max, 80)
    pm = [kb.p_mitte(med, KAV, p, KAV.T_mitte) for p in pw]
    ax.plot(pm, [med.rho(p, KAV.T_mitte) for p in pm], color=BLAU_D, lw=3.5,
            label=f"Betriebsfenster {kb.de(KAV.p_min, 0)}–{kb.de(KAV.p_max, 0)} bar (LCCS), {kb.de(KAV.T_mitte)} °C")
    ax.axvline(med.p_grenze, color=GRAU, ls=":", lw=1.2)
    ax.set(xlabel="Druck in Kavernenmitte [bar]", ylabel="Dichte [kg/m³]", xlim=(20, 240), ylim=(0, 950),
           title="Dichte über Druck bei Gebirgstemperatur")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    x = np.arange(len(zeilen))
    ax2.bar(x - 0.2, [100 * z["anteil_iso"] for z in zeilen], 0.4, color="#007335", label="langsam / isotherm")
    ax2.bar(x + 0.2, [100 * z["anteil_ise"] for z in zeilen], 0.4, color="#0476D9", label="schnell / isentrop")
    ax2.axhspan(22, 32, color="#999", alpha=0.2)
    ax2.text(len(zeilen) - 0.55, 27, "Q-028\n22–32 %", fontsize=7.5, color="#555", va="center")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{z['variante']}\n{kb.de(z['p_min'])} bar" for z in zeilen], fontsize=7.5)
    ax2.set(ylabel="Arbeitsgasanteil WGV/TGV [%]", ylim=(0, 100), title="Arbeitsgas je Mindestdruck (Klammer)")
    ax2.grid(alpha=0.3, axis="y")
    ax2.legend(fontsize=8)
    fig.suptitle(f"Arbeitsgas Referenzkaverne, {_titel(med)} (V = 650.000 m³)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(ordner / "abb_K02_arbeitsgas.png", dpi=160)
    plt.close(fig)

    erg = dict(TGV=TGV, varianten=zeilen, dbi_kontrolle=dbi, dichtekurve=kurve,
               teufenfenster=dict(T_grenze=med.T_ct, p_grenze=med.p_grenze, T_marge=T_MARGE,
                                  z_bezug_min=z_bezug_min, z_lccs_min=z_lccs_min, z_lccs_max=z_lccs_max))
    kb.speichere_json(ordner, "arbeitsgas.json", erg)
    return erg


# =============================================================================================
def _ausduennen(vl, k=10):
    return [x for i, x in enumerate(vl) if i % k == 0 or i == len(vl) - 1 or x["art"] != vl[i - 1]["art"]]


def schritt_03(med, ordner):
    """Ratengrenze, Kavernenbilanz über den Zyklus (gekoppelt an S1/S2), Betriebsweise, Grenzrate."""
    print(f"\n######## Schritt 03 - {_titel(med)}: Raten und Kavernenzyklus ########")
    still = kb.lade_json(ordner, "kaverne_stillstand.json", "01")
    rr = kb.raten(med)
    for name, m in rr.items():
        print(f"  {name} = {m:.2f} kg/s = {m * 86.4:.0f} t/d = {m * 86.4 * 365 / 1e6:.2f} Mt/a")

    valid = None
    if not med.ist_gemisch:      # Nachrechnung der Q-028-Simulation (reines CO₂)
        q028 = kb.Kaverne("Q-028 Validierungskaverne", "q028", 1150.0, 1355.0, 135.0, 70.0, 650000.0)
        v = kb.kavernenzyklus(med, q028, 1000.0, phasen=[("aus", 70.0)], dpdt_max=kb.DPDT_VORSICHTIG,
                              dt=0.01, T_geb=55.0)
        raten_th = [abs(x["m_dot"]) * 3.6 for x in v[:-1]]
        valid = dict(p_ende=v[-1]["p_mitte"], T_ende=v[-1]["T"], rate_min_th=min(raten_th), rate_max_th=max(raten_th),
                     quelle=dict(p_ende=77.6, T_ende=33.1, rate_min_th=90, rate_max_th=600))
        print(f"  Validierung Q-028: Ende {valid['p_ende']:.1f} bar / {valid['T_ende']:.1f} °C (Q-028: 77,6 / 33,1), "
              f"Raten {valid['rate_min_th']:.0f}-{valid['rate_max_th']:.0f} t/h (Q-028: ca. 90-600)")

    pl = np.linspace(KAV.p_min, KAV.p_max, 29)
    grenze = dict(p=pl.tolist())
    for art in ("isotherm", "isentrop"):
        for d in (kb.DPDT_VORSICHTIG, kb.DPDT_MAX):
            grenze[f"{art}_{d:.0f}"] = [float(kb.ratengrenze(med, KAV, p, d, art)) for p in pl]

    zyklen = {}
    for szen in kb.SZENARIEN:
        for rate, m in rr.items():
            z = still["betrieb"][szen][rate]
            for st_name, t_st in kb.STILLSTAENDE.items():
                vl = kb.kavernenzyklus(med, KAV, m, h_ein=z["h_lccs"], t_still=t_st,
                                       stopp_bei_zweiphasig=med.ist_gemisch)
                kw = kb.zyklus_kennwerte(vl)
                aus = kw[0]
                ein = next(k for k in kw if k["art"] == "ein") if any(k["art"] == "ein" for k in kw) else None
                ag = aus["m_start"] - aus["m_ende"]
                dauer = sum(k["dauer"] for k in kw)
                zyklen[f"{szen}|{rate}|{st_name}"] = dict(
                    szenario=szen, rate=rate, betriebsweise=st_name, m_dot=m, h_ein_lccs=z["h_lccs"],
                    T_ein_lccs=z["T_lccs"], kennwerte=kw, arbeitsgas_t=ag, anteil_arbeitsgas=ag / aus["m_start"],
                    zyklusdauer_d=dauer, T_max_ein=ein["T_max"] if ein else None,
                    verlauf=_ausduennen(vl, 10))
                print(f"  {szen} {rate:<14} {st_name:<26}: aus {aus['dauer']:5.1f} d bis {aus['T_min']:.1f} °C"
                      f"{' ZWEIPHASIG' if aus['zweiphasig'] else ''}, AG {kb.tsd(ag)} t ({100*ag/aus['m_start']:.0f} %)"
                      + (f", ein {ein['dauer']:.1f} d bis {ein['T_max']:.1f} °C" if ein else "")
                      + f", Zyklus {dauer:.0f} d")
    gr = kb.grenzrate(med, KAV)
    print(f"  Grenzrate einphasig: {'nicht bindend (> 150 kg/s)' if not gr['bindend'] else gr['rate']}")

    # ---- Abbildungen
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.fill_between(grenze["p"], grenze["isentrop_10"], grenze["isotherm_10"], color=BLAU_D, alpha=0.15,
                    label="10 bar/d: Band schnell (isentrop) bis langsam (isotherm)")
    ax.plot(grenze["p"], grenze["isotherm_10"], color=BLAU_D, lw=2)
    ax.plot(grenze["p"], grenze["isentrop_10"], color=BLAU_D, lw=2, ls="--")
    ax.plot(grenze["p"], grenze["isotherm_6"], color=GRAU, lw=1.2, ls=":", label="6 bar/d isotherm (Q-028)")
    for name, m in rr.items():
        ax.axhline(m, color=ROT, lw=1, ls=STIL_R[name])
        ax.text(KAV.p_max - 2, m + 3, name, ha="right", fontsize=8, color=ROT)
    ax.set(xlabel="Druck an der LCCS [bar]", ylabel="zulässige Rate [kg/s]", ylim=(0, 400),
           title=f"Ratengrenze aus der Druckänderungsrate ṁ_max = V·(∂ρ/∂p)·(dp/dt)_max, {_titel(med)}")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ordner / "abb_K03_ratengrenze.png", dpi=160)
    plt.close(fig)

    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    for key, zk in zyklen.items():
        if zk["betriebsweise"] != ST_A:
            continue
        vl = zk["verlauf"]
        t = [x["t"] for x in vl]
        kw = dict(color=FARBE_S[zk["szenario"]], ls=STIL_R[zk["rate"]], lw=1.7)
        axs[0].plot(t, [x["p_lccs"] for x in vl], label=f"{zk['szenario']}, {zk['rate']}", **kw)
        axs[1].plot(t, [x["T"] for x in vl], **kw)
        axs[2].plot(t, [x["m"] / 1000 for x in vl], **kw)
    axs[1].axhline(med.T_ct, color=ROT, ls="--", lw=1)
    axs[1].axhline(KAV.T_mitte, color="#555", ls=":", lw=1)
    axs[0].set(xlabel="Zeit [d]", ylabel="p an der LCCS [bar]")
    axs[1].set(xlabel="Zeit [d]", ylabel="T Kaverneninhalt [°C]")
    axs[2].set(xlabel="Zeit [d]", ylabel="Inhalt [kt]")
    axs[0].legend(fontsize=8)
    for a in axs:
        a.grid(alpha=0.3)
    fig.suptitle(f"Speicherzyklus {_titel(med)}: aus – 21,67 d – ein (Einspeisung S1 bzw. S2) – 21,67 d "
                 "(10 bar/d, UA nach Q-028)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(ordner / "abb_K03_zyklus.png", dpi=150)
    plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for key, zk in zyklen.items():
        if zk["rate"] != RATE_A:
            continue
        vl = zk["verlauf"]
        kw = dict(color=FARBE_S[zk["szenario"]], ls=STIL_ST[zk["betriebsweise"]], lw=1.7)
        axs[0].plot([x["t"] for x in vl], [x["p_lccs"] for x in vl], label=f"{zk['szenario']}, {zk['betriebsweise']}", **kw)
        axs[1].plot([x["t"] for x in vl], [x["T"] for x in vl], **kw)
    axs[0].set(xlabel="Zeit [d]", ylabel="p an der LCCS [bar]")
    axs[1].set(xlabel="Zeit [d]", ylabel="T Kaverneninhalt [°C]")
    axs[1].axhline(KAV.T_mitte, color="#555", ls=":", lw=1)
    axs[0].legend(fontsize=8)
    for a in axs:
        a.grid(alpha=0.3)
    fig.suptitle(f"Betriebsweise {_titel(med)}, {RATE_A}: Stillstand 21,67 d (Q-028) gegen kontinuierlich", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(ordner / "abb_K03_betriebsweise.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    phasengrenze_zeichnen(ax, med, T_min=0)
    for key, zk in zyklen.items():
        if zk["betriebsweise"] != ST_A:
            continue
        vl = zk["verlauf"]
        ax.plot([x["T"] for x in vl], [x["p_mitte"] for x in vl], color=FARBE_S[zk["szenario"]],
                ls=STIL_R[zk["rate"]], lw=1.6, label=f"{zk['szenario']}, {zk['rate']}")
    ax.set(xlim=(0, 60), ylim=(0, 240), xlabel="Temperatur Kaverneninhalt [°C]", ylabel="Druck Kavernenmitte [bar]",
           title=f"Zustandspfad des Kaverneninhalts über einen Zyklus, {_titel(med)}")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ordner / "abb_K03_zyklus_pT.png", dpi=160)
    plt.close(fig)

    erg = dict(validierung_q028=valid, ratengrenze=grenze, grenzrate=gr, zyklen=zyklen,
               raten={k: v for k, v in rr.items()})
    kb.speichere_json(ordner, "kavernenzyklus.json", erg)
    return erg


# =============================================================================================
N_PUNKTE = 14


def _schwelle(f_einphasig, lo, hi, it=12):
    """Bisektion: kleinster p_LCCS in [lo, hi], ab dem f_einphasig(p) wahr ist (hi muss wahr sein)."""
    if f_einphasig(lo):
        return None
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if f_einphasig(mid) else (mid, hi)
    return 0.5 * (lo + hi)


def _zwischen(ordner, name, abh, rechne):
    """Zwischenergebnis aus ordner/_zwischen_04/name.json laden, wenn es neuer ist als die
    Eingangsdateien abh - sonst rechnen und ablegen. Damit lässt sich Schritt 04 (Gemisch:
    über eine Stunde) in Teilen und parallel rechnen und nach einem Abbruch fortsetzen."""
    d = ordner / "_zwischen_04"
    d.mkdir(exist_ok=True)
    f = d / (name.replace("|", "_").replace(" ", "_").replace(".", "").replace("³", "3").replace("/", "") + ".json")
    if f.exists() and all(f.stat().st_mtime > (ordner / a).stat().st_mtime for a in abh):
        with open(f, encoding="utf-8") as fh:
            print(f"  {name}: Zwischenergebnis geladen ({f.name})")
            return json.load(fh)
    erg = rechne()
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(kb._rein_json(erg), fh, ensure_ascii=False)
    return erg


def _raster(med):
    # Gemisch im Zweiphasengebiet braucht den freien Flash (~0,1-0,4 s je Aufruf) -> gröberes Raster
    return (50, 8, 5) if med.ist_gemisch else (300, N_PUNKTE, 10)     # n_strang, n_pkt, Bisektionsschritte


def _ausspeisen(med, zyk, rate):
    """Ausspeisen mit einer Rate: Kopfzustände über den Zyklus und Band mit zweiphasigem Strang."""
    n_strang, n_pkt, it = _raster(med)
    vl = zyk["zyklen"][f"S2|{rate}|{ST_A}"]["verlauf"]
    pts = [x for x in vl if x["art"] == "aus" and x["m_dot"] < 0]
    idx = np.unique(np.linspace(0, len(pts) - 1, n_pkt).astype(int))
    zeilen = []
    for i in idx:
        x = pts[i]
        m = -x["m_dot"]
        h_u = kb.h_dampf(med, x["p_lccs"]) if x["q"] is not None else None
        _, k = kb.strang_aufwaerts(med, KAV, x["p_lccs"], x["T"], m, n=n_strang, h_unten=h_u)
        if k is None:
            zeilen.append(dict(t=x["t"], p_lccs=x["p_lccs"], T_kav=x["T"], m_dot=m, kopf=None))
            continue
        T_d, q_d = kb.drossel(med, kb.P_GAS, k["h"], k["T"]) if k["p"] > kb.P_GAS else (k["T"], k["q"])
        zeilen.append(dict(t=x["t"], p_lccs=x["p_lccs"], T_kav=x["T"], m_dot=m,
                           kopf=dict(p=k["p"], T=k["T"], rho=k["rho"], v=k["v"], v_max=k["v_max"], q=k["q"],
                                     zweiphasig_im_strang=k["zweiphasig_im_strang"]),
                           T_drossel_30=T_d, q_drossel_30=q_d,
                           V_kopf_m3h=m / k["rho"] * 3600))

    # Band, in dem der Strang (adiabat) zweiphasig ist: der Weg von dicht (oben im Fenster)
    # zu gasförmig (unten) kann durch das Zweiphasengebiet führen. Übergänge zwischen
    # benachbarten Stützstellen werden per Bisektion genau bestimmt.
    def zweiphasig_aus(p):
        t = sorted(zeilen, key=lambda z: z["p_lccs"])
        T = float(np.interp(p, [z["p_lccs"] for z in t], [z["T_kav"] for z in t]))
        m = float(np.interp(p, [z["p_lccs"] for z in t], [z["m_dot"] for z in t]))
        _, k = kb.strang_aufwaerts(med, KAV, p, T, m, n=n_strang)
        return k is None or k["zweiphasig_im_strang"]
    flags = [(z["p_lccs"], z["kopf"] is None or z["kopf"]["zweiphasig_im_strang"]) for z in zeilen]
    uebergaenge = []
    for (p_a, f_a), (p_b, f_b) in zip(flags, flags[1:]):
        if f_a != f_b:
            hi, lo = (p_a, p_b) if p_a > p_b else (p_b, p_a)
            f_hi = zweiphasig_aus(hi)
            for _ in range(it):
                mid = 0.5 * (hi + lo)
                if zweiphasig_aus(mid) == f_hi:
                    hi = mid
                else:
                    lo = mid
            uebergaenge.append(0.5 * (hi + lo))
    zp = [p for p, f in flags if f]
    band = None
    if zp:
        oben = min([u for u in uebergaenge if u >= max(zp)] or [max(zp)])
        unten = max([u for u in uebergaenge if u <= min(zp)]) if any(u <= min(zp) for u in uebergaenge) else None
        band = dict(p_lccs_oben=oben, p_lccs_unten=unten)
    return dict(punkte=zeilen, strang_zweiphasig=band)


def _einspeisen(med, still, zyk, szen, rate):
    """Einspeisen S1/S2 mit einer Rate: Kopfdruck über den Zyklus, ab wann einphasig, ab wann Pumpe."""
    n_strang, n_pkt, it = _raster(med)
    z = still["betrieb"][szen][rate]
    vl = zyk["zyklen"][f"{szen}|{rate}|{ST_A}"]["verlauf"]
    pts = [x for x in vl if x["art"] == "ein" and x["m_dot"] > 0]
    if not pts:
        return None
    idx = np.unique(np.linspace(0, len(pts) - 1, n_pkt).astype(int))
    zeilen = []
    for i in idx:
        x = pts[i]
        e = kb.einspeisen_geregelt(med, KAV, x["p_lccs"], szen, x["m_dot"], z["h_kopf"], n=n_strang)
        k = e["kopf"]
        zeilen.append(dict(t=x["t"], p_lccs=x["p_lccs"], T_kav=x["T"], m_dot=x["m_dot"], pumpe=e["pumpe"],
                           kopf=None if k is None else dict(p=k["p"], T=k["T"], rho=k["rho"], v=k["v"],
                                                            zweiphasig_im_strang=k["zweiphasig_im_strang"])))
    m = z["m_dot"]

    def einphasig_ein(p):
        e = kb.einspeisen_geregelt(med, KAV, p, szen, m, z["h_kopf"], n=n_strang)
        return e["kopf"] is not None and not e["kopf"]["zweiphasig_im_strang"]

    def pumpe_noetig(p):
        return kb.einspeisen_geregelt(med, KAV, p, szen, m, z["h_kopf"], n=n_strang)["pumpe"]

    # Klammer aus den Stützstellen: letzter zweiphasiger / erster einphasiger Punkt usw.
    lo_e = max([z_["p_lccs"] for z_ in zeilen if z_["kopf"] and z_["kopf"]["zweiphasig_im_strang"]] or [KAV.p_min])
    hi_e = min([z_["p_lccs"] for z_ in zeilen if z_["kopf"] and not z_["kopf"]["zweiphasig_im_strang"]
                and z_["p_lccs"] > lo_e] or [KAV.p_max])
    lo_p = max([z_["p_lccs"] for z_ in zeilen if not z_["pumpe"]] or [KAV.p_min])
    hi_p = min([z_["p_lccs"] for z_ in zeilen if z_["pumpe"] and z_["p_lccs"] > lo_p] or [KAV.p_max])
    s_ein = _schwelle(einphasig_ein, lo_e, hi_e, it=it)
    s_pumpe = _schwelle(pumpe_noetig, lo_p, hi_p, it=it)
    return dict(szenario=szen, rate=rate, punkte=zeilen, p_kopf_auslegung=z["p_kopf"],
                p_lccs_einphasig_ab=s_ein, p_lccs_pumpe_ab=s_pumpe)


TEILE_04 = ["aus|" + r for r in kb.RATEN] + [f"ein|{s}|{r}" for s in kb.SZENARIEN for r in kb.RATEN]


def schritt_04(med, ordner, teile=None):
    """Kopfdruckfenster beim Ein- und Ausspeichern, Phase im Strang, Drossel, Reibung.

    teile: None = alles rechnen (Zwischenergebnisse werden wiederverwendet), sonst eine
    Auswahl aus TEILE_04 - dann nur diese Teile rechnen und ablegen (z. B. zwei Prozesse
    parallel: "aus|..." und "ein|..."). Ein Lauf ohne teile setzt danach alles zusammen.
    """
    print(f"\n######## Schritt 04 - {_titel(med)}: Bohrlochkopf ########", flush=True)
    still = kb.lade_json(ordner, "kaverne_stillstand.json", "01")
    zyk = kb.lade_json(ordner, "kavernenzyklus.json", "03")
    n_strang, n_pkt, it = _raster(med)
    abh = ("kaverne_stillstand.json", "kavernenzyklus.json")
    auswahl = TEILE_04 if teile is None else teile
    aus, ein = {}, {}
    for t in auswahl:
        if t.startswith("aus|"):
            rate = t.split("|")[1]
            aus[rate] = _zwischen(ordner, t, abh, lambda rate=rate: _ausspeisen(med, zyk, rate))
        else:
            _, szen, rate = t.split("|")
            e = _zwischen(ordner, t, abh, lambda szen=szen, rate=rate: _einspeisen(med, still, zyk, szen, rate))
            if e is not None:
                ein[f"{szen}|{rate}"] = e
        print(f"  Teil fertig: {t}", flush=True)
    if teile is not None:
        return None

    # ---- Reibungseinfluss beim Ausspeichern (Anfang, Mitte, Ende; Auslegungsrate)
    reibung = []
    pts = aus[RATE_A]["punkte"]
    for z in (pts[0], pts[len(pts) // 2], pts[-1]):
        if z["kopf"] is None:
            continue
        _, k0 = kb.strang_aufwaerts(med, KAV, z["p_lccs"], z["T_kav"], z["m_dot"], n=n_strang, f=0.0)
        reibung.append(dict(p_lccs=z["p_lccs"], p_kopf=z["kopf"]["p"], T_kopf=z["kopf"]["T"],
                            p_kopf_f0=k0["p"], T_kopf_f0=k0["T"],
                            dp=z["kopf"]["p"] - k0["p"], dT=z["kopf"]["T"] - k0["T"]))

    # ---- Kopfdruckfenster (Regelgröße)
    fenster = dict(
        stillstand_voll=still["saeulen"]["voll"]["p_kopf"], stillstand_leer=still["saeulen"]["leer"]["p_kopf"],
        **{f"einspeisen_{k.replace('|', '_')}_max": max(z["kopf"]["p"] for z in e["punkte"] if z["kopf"])
           for k, e in ein.items()},
        **{f"einspeisen_{k.replace('|', '_')}_min": min(z["kopf"]["p"] for z in e["punkte"] if z["kopf"])
           for k, e in ein.items()},
        **{f"ausspeisen_{r}_max": max(z["kopf"]["p"] for z in a["punkte"] if z["kopf"]) for r, a in aus.items()},
        **{f"ausspeisen_{r}_min": min(z["kopf"]["p"] for z in a["punkte"] if z["kopf"]) for r, a in aus.items()},
        **{f"ausspeisen_{r}_T_min": min(z["kopf"]["T"] for z in a["punkte"] if z["kopf"]) for r, a in aus.items()},
        **{f"ausspeisen_{r}_T_drossel_min": min(z["T_drossel_30"] for z in a["punkte"] if z["kopf"])
           for r, a in aus.items()},
        **{f"ausspeisen_{r}_v_max": max(z["kopf"]["v_max"] for z in a["punkte"] if z["kopf"]) for r, a in aus.items()})

    # ---- Konsole
    for rate, a in aus.items():
        k = [z["kopf"] for z in a["punkte"] if z["kopf"]]
        print(f"  Ausspeisen {rate}: Kopf {min(x['p'] for x in k):.1f}-{max(x['p'] for x in k):.1f} bar, "
              f"T {min(x['T'] for x in k):.1f}-{max(x['T'] for x in k):.1f} °C, v_max {max(x['v_max'] for x in k):.1f} m/s, "
              f"nach Drossel 30 bar bis {min(z['T_drossel_30'] for z in a['punkte'] if z['kopf']):.1f} °C; "
              + (f"Strang zweiphasig zwischen {a['strang_zweiphasig']['p_lccs_oben']:.0f} und "
                 + (f"{a['strang_zweiphasig']['p_lccs_unten']:.0f}" if a['strang_zweiphasig']['p_lccs_unten'] else "p_min")
                 + " bar an der LCCS" if a["strang_zweiphasig"] else "Strang immer einphasig"))
    for key, e in ein.items():
        k = [z["kopf"] for z in e["punkte"] if z["kopf"]]
        print(f"  Einspeisen {key}: Kopf {min(x['p'] for x in k):.1f}-{max(x['p'] for x in k):.1f} bar; "
              f"Pumpe nötig ab {e['p_lccs_pumpe_ab'] or 0:.0f} bar an der LCCS, einphasig ab {e['p_lccs_einphasig_ab'] or 0:.0f} bar")
    for r in reibung:
        print(f"  Reibung Ausspeisen @ {r['p_lccs']:.0f} bar: Δp {r['dp']:+.2f} bar, ΔT {r['dT']:+.2f} K")

    # ---- Abbildung 1: Kopfdruck über den Zyklus
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.5))
    for rate, a in aus.items():
        pts = [z for z in a["punkte"] if z["kopf"]]
        axs[0].plot([z["p_lccs"] for z in pts], [z["kopf"]["p"] for z in pts], color=BLAU_D, ls=STIL_R[rate], lw=2,
                    label=f"Ausspeisen {rate}")
    for key, e in ein.items():
        pts = [z for z in e["punkte"] if z["kopf"]]
        axs[0].plot([z["p_lccs"] for z in pts], [z["kopf"]["p"] for z in pts], color=FARBE_S[e["szenario"]],
                    ls=STIL_R[e["rate"]], lw=2, label=f"Einspeisen {key.replace('|', ', ')}")
    pl = np.linspace(KAV.p_min, KAV.p_max, 15)
    axs[0].plot(pl, [kb.kopfdruck(med, KAV, p, n=200) for p in pl], color=GRAU, lw=1.2, ls="-.", label="Stillstand")
    axs[0].axhline(kb.P_RUECKGABE, color="#7030A0", lw=1, ls="--")
    axs[0].text(KAV.p_min + 2, kb.P_RUECKGABE + 2, "91 bar: Lieferdruck / Rückgabe (OGE)", fontsize=8, color="#7030A0")
    axs[0].set(xlabel="Druck an der LCCS [bar]", ylabel="Kopfdruck [bar]",
               title="Kopfdruck = Regelgröße: was oben anliegt, wenn unten p_LCCS herrscht")
    axs[0].legend(fontsize=7.5)
    for rate, a in aus.items():
        pts = [z for z in a["punkte"] if z["kopf"]]
        axs[1].plot([z["t"] for z in pts], [z["kopf"]["T"] for z in pts], color=BLAU_D, ls=STIL_R[rate], lw=2,
                    label=f"Kopf, {rate}")
        axs[1].plot([z["t"] for z in pts], [z["T_drossel_30"] for z in pts], color=ROT, ls=STIL_R[rate], lw=1.5,
                    label=f"nach Drossel 30 bar, {rate}")
    axs[1].axhline(kb.T_KOPF_MIN_EPE, color="#7030A0", lw=1, ls="--")
    axs[1].text(0.5, kb.T_KOPF_MIN_EPE + 0.7, "5 °C: min. Kopftemperatur Epe (Q-035 Folie 36)", fontsize=8,
                color="#7030A0")
    axs[1].set(xlabel="Zeit ab Beginn des Ausspeicherns [d]", ylabel="Temperatur [°C]",
               title="Ausspeisen (adiabat): Kopf und nach der Drossel")
    axs[1].legend(fontsize=7.5)
    for a in axs:
        a.grid(alpha=0.3)
    fig.suptitle(f"Bohrlochkopf, {_titel(med)}: Kopfdruckfenster beim Ein- und Ausspeichern", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(ordner / "abb_K04_kopfdruckfenster.png", dpi=150)
    plt.close(fig)

    # ---- Abbildung 2: Kopfzustände im p-T-Diagramm
    fig, ax = plt.subplots(figsize=(10.5, 7))
    phasengrenze_zeichnen(ax, med)
    for rate, a in aus.items():
        pts = [z for z in a["punkte"] if z["kopf"]]
        ax.plot([z["kopf"]["T"] for z in pts], [z["kopf"]["p"] for z in pts], marker="o", color=BLAU_D,
                ls=STIL_R[rate], ms=4, label=f"Kopf Ausspeisen, {rate}")
    for key, e in ein.items():
        pts = [z for z in e["punkte"] if z["kopf"]]
        ax.plot([z["kopf"]["T"] for z in pts], [z["kopf"]["p"] for z in pts], marker="s", color=FARBE_S[e["szenario"]],
                ls=STIL_R[e["rate"]], ms=4, label=f"Kopf Einspeisen {key.replace('|', ', ')}")
    for p, txt in ((kb.P_RUECKGABE, "91 bar"), (kb.P_GAS, "30 bar")):
        ax.axhline(p, color="#7030A0", lw=1, ls="--")
        ax.text(-18, p + 1.5, txt, color="#7030A0", fontsize=8)
    ax.set(xlim=(-20, 55), ylim=(0, 140), xlabel="Temperatur am Kopf [°C]", ylabel="Kopfdruck [bar]",
           title=f"Kopfzustände beim Ein- und Ausspeichern, {_titel(med)}")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(ordner / "abb_K04_kopfzustand_pT.png", dpi=160)
    plt.close(fig)

    erg = dict(annahmen=dict(D_strang=kb.D_STRANG, f_darcy=kb.F_DARCY, v_max=kb.V_MAX_STRANG, p_rueckgabe=kb.P_RUECKGABE,
                             p_gas=kb.P_GAS, T_kopf_min_epe=kb.T_KOPF_MIN_EPE),
               ausspeisen=aus, einspeisen=ein, reibung_ausspeisen=reibung,
               reibung_einspeisen={s: dict(p_kopf=still["betrieb"][s][RATE_A]["p_kopf"],
                                           p_kopf_f0=still["betrieb"][s][RATE_A].get("p_kopf_ohne_reibung"))
                                   for s in kb.SZENARIEN},
               kopfdruckfenster=fenster)
    kb.speichere_json(ordner, "bohrlochkopf.json", erg)
    return erg
