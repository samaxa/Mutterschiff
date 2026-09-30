# -*- coding: utf-8 -*-
"""
Rechenteil für die Excel-Rechenübersicht mit Worst-Case-Gemisch
============================================================================
Rechnet alle Stoffwerte, die in der Mappe "CO2_Zwischenspeicher_Rechenuebersicht"
als graue CoolProp-Werte stehen, neu für das Worst-Case-Gemisch - mit
denselben Rechenwegen wie die Mappe für reines CO2:

  Kaverne & Gassäule   Gassäule in 600 Schritten à 2 m, von unten nach oben,
                       drei Füllstände (voll, Grenzfall, leer)
  Medienvergleich      nötiger Kopfdruck über der Teufe (600-1600 m)
  Einspeicherung S1    Pumpe, isentrop + Wirkungsgrad
  Einspeicherung S2    Verdichter, Verflüssiger, Pumpe; Variante 2 Stufen;
                       Vergleich Durchverdichten
  Diagrammdaten        Phasengebiete (gestapelte Flächen), Phasengrenze,
                       Sicherheitsabstand ±3 bar, Beschriftungen

Neue Annahmen für das Gemisch (Rest wie reines CO2):
  p_V = 90 bar   Enddruck der Verdichtung = Druck, bei dem auf T_K = 20 °C
                 gekühlt wird. Cricondenbar 82,2 bar + 3 bar Unsicherheit
                 = 85,2 bar Minimum, gewählt 90 bar (Reserve). Darüber gibt es
                 kein Zweiphasengebiet: der Kühler kühlt in der dichten Phase,
                 es wird nichts kondensiert (wie Q-016: Endstufe 100 bar, dann
                 20 °C). Reines CO2: Verflüssigen bei 60 bar.
  Grenzfall      Kopfdruck = Cricondenbar (82,2 bar) statt p_krit (73,8 bar):
                 darüber ist das Gemisch bei jeder Temperatur einphasig
  Alte Verdichtung (nur zum Vergleich): wie reines CO2, 1 Stufe bis 60 bar,
                 Verflüssigen bei 20 °C - beim Gemisch bleibt es dort gasförmig.

Dieselben Funktionen rechnen auch reines CO2 (werte(ReinCO2(), p_V=60)).
Damit lässt sich prüfen, dass die Rechnung exakt die Werte der Mappe für
reines CO2 liefert (siehe pruefung_rein()).

Ergebnis: dict mit allen Werten (werte()), wird von
04_excel_rechenuebersicht_gemisch.py in die Mappe geschrieben und von
03_einspeicherpfad_gemisch.py für die Diagramme genutzt.
"""
import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI

import gemisch_worstcase as gw
from stoffmodell import Gemisch, ReinCO2

# ---- Annahmen (Übersicht der Mappe) -----------------------------------------
A = dict(p_S1=91.0, T_S1=15.0, p_S2=30.0, T_S2=15.0, T_K=20.0, T_max=95.0,
         p_V=90.0, p_zw=50.0, z=1200.0, T0=10.0, grad=0.03, p_max=210.0, p_min=70.0,
         rho_salz=2200.0, V_min=50000.0, V_max=100000.0,
         eta_V1=0.84, eta_V2=0.82, eta_P=0.80)
P_V_REIN = 60.0     # bar, Verflüssigungsdruck reines CO2 (Mappe reines CO2) = "alte Verdichtung"
U_PG = 3.0          # bar, Unsicherheit der Phasengrenze (Dokumentation Kap. 9)
G = 9.81
T_TRIPEL_C = PropsSI("Ttriple", "CO2") - 273.15
P_TRIPEL = PropsSI("ptriple", "CO2") / 1e5

GEM = Gemisch()
REIN = ReinCO2()


# ---- Gassäule ---------------------------------------------------------------
def saeule(p_unten, z_ges=A["z"], dz=2.0, stoff=GEM):
    """dp/dz = rho(p,T)*g von unten nach oben (wie Blatt Kaverne & Gassäule).

    Gibt Arrays z, p, T, rho und zweiphasig (bool) zurück, von unten nach oben.
    """
    n = int(round(z_ges / dz))
    p = p_unten
    zs, ps, Ts, rhos, zwei = [], [], [], [], []
    for i in range(n + 1):
        z = z_ges - i * dz
        T = A["T0"] + A["grad"] * z
        rho = stoff.rho(p, T)
        zweiphasig = (stoff is GEM and p <= GEM.p_sicher and GEM.AS.phase() == CP.iphase_twophase)
        zs.append(z), ps.append(p), Ts.append(T), rhos.append(rho), zwei.append(zweiphasig)
        if i < n:
            p -= rho * G * dz / 1e5
    return tuple(np.array(a) for a in (zs, ps, Ts, rhos, zwei))


def kopfdruck(p_unten, z_ges=A["z"], stoff=GEM):
    return saeule(p_unten, z_ges, stoff=stoff)[1][-1]


def sekante(f, x0, x1, tol=1e-6):
    f0, f1 = f(x0), f(x1)
    for _ in range(50):
        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        if abs(x2 - x1) < tol:
            return x2
        x0, f0, x1, f1 = x1, f1, x2, f(x2)
    raise RuntimeError("Sekantenverfahren nicht konvergiert")


def profil_50m(s):
    """Werte alle 50 m (Zeilen 49-73 der Mappe: 0, 50, ..., 1200 m)."""
    z, p, T, rho, zwei = s
    aus = {}
    for zz in np.arange(0, A["z"] + 1, 50):
        i = int(np.argmin(np.abs(z - zz)))
        aus[zz] = (T[i], p[i], rho[i], zwei[i])
    return aus


# ---- Stufen (Pumpe / Verdichter) ---------------------------------------------
def phase_text(stoff, p, T):
    if stoff is GEM:
        st = gw.stoffwerte(p, T)
        return {"flüssig": "dicht (flüssig)", "gasförmig": "gasförmig"}.get(st["phase"], st["phase"])
    return stoff.phase(p, T)


def stufe(stoff, p1, T1, p2, eta):
    """Isentrop + Wirkungsgrad (wie die Mappe): h1, h2s, h2, T2."""
    h1 = stoff.h(p1, T1)
    h2s = stoff.h_ps(p2, stoff.s(p1, T1))
    h2 = h1 + (h2s - h1) / eta
    T2, _ = stoff.T_ph(p2, h2)
    return h1, h2s, h2, T2


def s2_kette(stoff, p_V, p_kopf):
    """S2 wie Blatt 'Einspeicherung S2': Basisfall 1 Stufe bis p_V, Variante 2 Stufen,
    Kühler/Verflüssiger auf T_K bei p_V, Pumpe bis Kopfdruck."""
    h1, h1s, h1a, T1a = stufe(stoff, A["p_S2"], A["T_S2"], p_V, A["eta_V1"])
    hV = stoff.h(p_V, A["T_K"])
    _, hPs, hPa, TPa = stufe(stoff, p_V, A["T_K"], p_kopf, A["eta_P"])
    S2 = dict(p_V=p_V, h1=h1, h1s=h1s, h1a=h1a, T1a=T1a, hV=hV, phaseV=phase_text(stoff, p_V, A["T_K"]),
              hPs=hPs, hPa=hPa, TPa=TPa, w1=h1a - h1, wP=hPa - hV, qV=h1a - hV)
    p_zw = np.sqrt(A["p_S2"] * p_V)
    _, h1s_v, h1a_v, T1a_v = stufe(stoff, A["p_S2"], A["T_S2"], p_zw, A["eta_V1"])
    hZK, h2s_v, h2a_v, T2a_v = stufe(stoff, p_zw, A["T_K"], p_V, A["eta_V2"])
    S2v = dict(p_zw=p_zw, h1s=h1s_v, h1a=h1a_v, T1a=T1a_v, hZK=hZK, h2s=h2s_v, h2a=h2a_v, T2a=T2a_v,
               w1=h1a_v - h1, w2=h2a_v - hZK, phaseZK=phase_text(stoff, p_zw, A["T_K"]))
    return S2, S2v


def werte(stoff=GEM, p_V=None, alles=True):
    """Alle Werte der Mappe für stoff (Gemisch: p_V = 90 bar, reines CO2: 60 bar).

    alles=False rechnet nur Gassäule (voll), S1 und S2 - für die Prüfung mit
    reinem CO2 und für 03_einspeicherpfad_gemisch.py.
    """
    p_V = p_V if p_V is not None else (A["p_V"] if stoff is GEM else P_V_REIN)
    W = {"A": dict(A, p_V=p_V), "U_PG": U_PG}

    # -- Kaverne & Gassäule --
    voll = saeule(A["p_max"], stoff=stoff)
    W["kav"] = {}
    faelle = [("voll", voll, A["p_max"])]
    if alles:
        pg = gw.phasengrenze()
        W["pg"] = pg
        p_cb = pg["cricondenbar"][1]
        leer = saeule(A["p_min"], stoff=stoff)
        p_grenz = sekante(lambda pu: kopfdruck(pu, stoff=stoff) - p_cb, 170.0, 180.0)
        faelle += [("grenz", saeule(p_grenz, stoff=stoff), p_grenz), ("leer", leer, A["p_min"])]
    for name, sl, pu in faelle:
        z, p, T, rho, zwei = sl
        tief_2ph = z[zwei].max() if zwei.any() else 0.0
        W["kav"][name] = dict(p_unten=pu, p_kopf=p[-1], T_kopf=T[-1], rho_kopf=rho[-1],
                              rho_unten=rho[0], profil=profil_50m(sl), tief_2ph=tief_2ph)
    W["T_Kav"] = A["T0"] + A["grad"] * A["z"]
    p_kopf = W["kav"]["voll"]["p_kopf"]

    # -- S1 --
    h1, h2s, h2, T2 = stufe(stoff, A["p_S1"], A["T_S1"], p_kopf, A["eta_P"])
    W["S1"] = dict(h1=h1, s1=stoff.s(A["p_S1"], A["T_S1"]), h2s=h2s, h2=h2, T2=T2,
                   phase1=phase_text(stoff, A["p_S1"], A["T_S1"]), phase2=phase_text(stoff, p_kopf, T2),
                   rho_n=stoff.rho_norm(), w=h2 - h1)

    # -- S2: Basisfall (1 Stufe) und Variante (2 Stufen) bis p_V, Kühler, Pumpe --
    W["S2"], W["S2v"] = s2_kette(stoff, p_V, p_kopf)

    # -- Vergleich Durchverdichten: 2 Stufen bis Kopfdruck, Nachkühler auf T nach Pumpe --
    h1 = W["S2"]["h1"]
    _, h1s_d, h1a_d, T1a_d = stufe(stoff, A["p_S2"], A["T_S2"], A["p_zw"], A["eta_V1"])
    hZK_d, h2s_d, h2a_d, T2a_d = stufe(stoff, A["p_zw"], A["T_K"], p_kopf, A["eta_V2"])
    hN = stoff.h(p_kopf, W["S2"]["TPa"])
    W["Dv"] = dict(h1s=h1s_d, h1a=h1a_d, T1a=T1a_d, hZK=hZK_d, h2s=h2s_d, h2a=h2a_d, T2a=T2a_d,
                   hN=hN, w1=h1a_d - h1, w2=h2a_d - hZK_d)
    if not alles:
        return W

    # -- nur Gemisch: Phasengrenze an den Kühlern, alte Verdichtung, Diagramme --
    W["mv_kopf"] = {zz: kopfdruck(A["p_max"], zz) for zz in (600, 800, 1000, 1200, 1400, 1600)}
    p_bl_TK, p_tau_TK = gw.blasendruck(A["T_K"]), gw.taudruck(A["T_K"])
    W["S2"].update(p_cb=p_cb, p_bl_TK=p_bl_TK, p_tau_TK=p_tau_TK)
    W["Dv"]["p_zw_min"] = _p_zw_min(W["S2"]["h1"], p_kopf)
    W["Dv"]["p_zw_max"] = p_tau_TK - U_PG
    # alte Verdichtung: wie reines CO2 (1 Stufe bis 60 bar, auf 20 °C kühlen)
    _, _, h1a_alt, T1a_alt = stufe(GEM, A["p_S2"], A["T_S2"], P_V_REIN, A["eta_V1"])
    W["alt"] = dict(p_V=P_V_REIN, T1a=T1a_alt, w1=h1a_alt - W["S2"]["h1"],
                    phase=phase_text(GEM, P_V_REIN, A["T_K"]), p_tau_TK=p_tau_TK,
                    abstand_tau=p_tau_TK - P_V_REIN)
    W["dia"] = diagrammdaten(pg)
    return W


def _p_zw_min(h1, p_kopf):
    """Kleinster Zwischendruck, bei dem Stufe 2 (T_K -> Kopfdruck) höchstens T_max erreicht."""
    def T_aus(p_zw):
        return stufe(GEM, p_zw, A["T_K"], p_kopf, A["eta_V2"])[3] - A["T_max"]
    return sekante(T_aus, 40.0, 50.0, tol=1e-3)


def pruefung_rein():
    """Gleiche Rechnung mit reinem CO2 muss die Werte der Mappe für reines CO2 liefern."""
    W = werte(REIN, alles=False)
    soll = {("kav", "voll", "p_kopf"): 107.603219569636, ("S1", "h1"): 231.1882381347587,
            ("S1", "h2s"): 233.0661478349782, ("S1", "T2"): 16.80325648836964,
            ("S1", "rho_n"): 1.97681274147157, ("S2", "h1"): 462.3387941882859,
            ("S2", "h1s"): 495.0787698118331, ("S2", "T1a"): 73.15539245907911,
            ("S2", "hV"): 254.2786549964349, ("S2", "hPs"): 260.2376364212104,
            ("S2", "TPa"): 27.54224349896373, ("S2v", "h1s"): 478.1016351370513,
            ("S2v", "T1a"): 43.10167600301611, ("S2v", "hZK"): 448.6254348683687,
            ("S2v", "h2s"): 462.9659131351239, ("S2v", "T2a"): 48.44610457479314,
            ("Dv", "h1s"): 485.9886448799301, ("Dv", "T1a"): 57.10272017421391,
            ("Dv", "hZK"): 432.3819368542681, ("Dv", "h2s"): 462.3311435176642,
            ("Dv", "T2a"): 83.36578155893835, ("Dv", "hN"): 261.7273817774039}
    fehler = 0
    for schluessel, wert in soll.items():
        ist = W
        for k in schluessel:
            ist = ist[k]
        ok = abs(ist - wert) < 1e-6 * max(1.0, abs(wert))
        fehler += not ok
        print(f"  {'.'.join(schluessel):<16} Mappe {wert:12.6f}  Skript {ist:12.6f}  {'✔' if ok else '✘'}")
    print("Prüfung reines CO2:", "alle Werte identisch" if not fehler else f"{fehler} Abweichungen")
    return fehler == 0


# ---- Diagrammdaten ----------------------------------------------------------
def sublimation_bar(T_K):
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    T_t = T_TRIPEL_C + 273.15
    th = 1.0 - T_K / T_t
    return P_TRIPEL * np.exp((T_t / T_K) * (a1 * th + a2 * th**1.9 + a3 * th**2.9))


def schmelz_bar(T_K):
    T_t = T_TRIPEL_C + 273.15
    x = T_K / T_t - 1.0
    return P_TRIPEL * (1.0 + 1955.5390 * x + 2055.4593 * x**2)


def diagrammdaten(pg):
    """Gestapelte Phasenflächen (Summe 250 bar) und Linienpunkte."""
    T_kG, p_kG = pg["krit"]
    SUMME = 250.0
    flaechen = []
    for T in np.arange(-80.0, 120.0 + 0.25, 0.5):          # bis 120 °C (S2 Basisfall 1 Stufe: 112 °C)
        gas = zwei = flue = sup = fest = 0.0
        if T < T_TRIPEL_C:
            gas = float(sublimation_bar(T + 273.15))
            fest = SUMME - gas
        elif T <= T_kG:
            p_tau, p_bl = gw.taudruck(T), gw.blasendruck(T)
            p_schm = float(schmelz_bar(T + 273.15))
            gas, zwei = p_tau, p_bl - p_tau
            oben = min(p_schm, SUMME)
            flue = oben - p_bl
            fest = SUMME - oben
        else:
            gas, sup = p_kG, SUMME - p_kG
        flaechen.append((T, gas, zwei, flue, sup, fest))

    # Phasengrenze als eine Linie: Taulinie hoch zum krit. Punkt, Blasenlinie zurück (70 Punkte)
    T_tau, p_tau = pg["T_tau"], pg["p_tau"]
    T_bl, p_bl = pg["T_blase"], pg["p_blase"]
    nah = T_kG - 2.0
    tau_fern = np.linspace(T_tau.min(), nah, 28)
    tau_pts = [(T, gw.taudruck(T)) for T in tau_fern] + [(T, p) for T, p in zip(T_tau, p_tau) if T > nah]
    bl_nah = [(T, p) for T, p in zip(T_bl, p_bl) if T > nah]
    bl_fern = np.linspace(nah, T_bl.min(), 70 - len(tau_pts) - len(bl_nah))
    huelle = tau_pts + bl_nah + [(T, gw.blasendruck(T)) for T in bl_fern]
    assert len(huelle) == 70, len(huelle)

    # Sicherheitsabstand ±3 bar: Blasenlinie + 3 (sicher flüssig), Taulinie - 3 (sicher gasförmig)
    T_grid_bl = np.linspace(T_bl.min(), T_bl.max(), 30)
    sicher_fl = [(T, np.interp(T, T_bl[::-1], p_bl[::-1]) + U_PG) for T in T_grid_bl]
    i_ct = int(np.argmax(T_tau))
    T_grid_tau = np.linspace(T_tau.min(), T_tau[i_ct], 30)
    sicher_gas = [(T, max(np.interp(T, T_tau[:i_ct + 1], p_tau[:i_ct + 1]) - U_PG, 0.0)) for T in T_grid_tau]

    # reines CO2 zum Vergleich
    T_s = np.linspace(T_TRIPEL_C + 273.15, PropsSI("Tcrit", "CO2") - 1e-3, 41)
    rein = [(T - 273.15, PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5) for T in T_s]
    return dict(flaechen=flaechen, huelle=huelle, sicher_fl=sicher_fl, sicher_gas=sicher_gas,
                rein=rein, krit=(T_kG, p_kG))


if __name__ == "__main__":
    import json, time
    t = time.time()
    pruefung_rein()
    W = werte()
    kurz = {k: v for k, v in W.items() if k not in ("dia", "pg", "mv_kopf")}
    for name in ("voll", "grenz", "leer"):
        kurz["kav"][name] = {k: v for k, v in W["kav"][name].items() if k != "profil"}
    print(json.dumps(kurz, indent=1, default=float, ensure_ascii=False))
    print(f"Rechenzeit {time.time() - t:.0f} s")
