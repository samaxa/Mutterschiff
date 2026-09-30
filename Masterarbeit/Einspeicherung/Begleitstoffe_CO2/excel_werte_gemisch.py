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
  p_V  = 80 bar  Blasendruck bei 20 °C = 76,7 bar + 3 bar Unsicherheit der
                 Phasengrenze -> sicher vollständig flüssig (reines CO2: 60 bar)
  Grenzfall      Kopfdruck = Cricondenbar (82,2 bar) statt p_krit (73,8 bar):
                 darüber ist das Gemisch bei jeder Temperatur einphasig

Ergebnis: dict mit allen Werten (werte()), wird von
04_excel_rechenuebersicht_gemisch.py in die Mappe geschrieben.
"""
import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI

import gemisch_worstcase as gw
from stoffmodell import Gemisch

# ---- Annahmen (Übersicht der Mappe) -----------------------------------------
A = dict(p_S1=91.0, T_S1=15.0, p_S2=30.0, T_S2=15.0, T_K=20.0, T_max=95.0,
         p_V=80.0, p_zw=50.0, z=1200.0, T0=10.0, grad=0.03, p_max=210.0, p_min=70.0,
         rho_salz=2200.0, V_min=50000.0, V_max=100000.0,
         eta_V1=0.84, eta_V2=0.82, eta_P=0.80)
U_PG = 3.0          # bar, Unsicherheit der Phasengrenze (Dokumentation Kap. 9)
G = 9.81
T_TRIPEL_C = PropsSI("Ttriple", "CO2") - 273.15
P_TRIPEL = PropsSI("ptriple", "CO2") / 1e5

GEM = Gemisch()


# ---- Gassäule ---------------------------------------------------------------
def saeule(p_unten, z_ges=A["z"], dz=2.0):
    """dp/dz = rho(p,T)*g von unten nach oben (wie Blatt Kaverne & Gassäule).

    Gibt Arrays z, p, T, rho und zweiphasig (bool) zurück, von unten nach oben.
    """
    n = int(round(z_ges / dz))
    p = p_unten
    zs, ps, Ts, rhos, zwei = [], [], [], [], []
    for i in range(n + 1):
        z = z_ges - i * dz
        T = A["T0"] + A["grad"] * z
        rho = GEM.rho(p, T)
        zweiphasig = p <= GEM.p_sicher and GEM.AS.phase() == CP.iphase_twophase
        zs.append(z), ps.append(p), Ts.append(T), rhos.append(rho), zwei.append(zweiphasig)
        if i < n:
            p -= rho * G * dz / 1e5
    return tuple(np.array(a) for a in (zs, ps, Ts, rhos, zwei))


def kopfdruck(p_unten, z_ges=A["z"]):
    return saeule(p_unten, z_ges)[1][-1]


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
def h(p, T):
    return GEM.h(p, T)


def s(p, T):
    return GEM.s(p, T)


def phase_text(p, T):
    st = gw.stoffwerte(p, T)
    return {"flüssig": "dicht (flüssig)", "gasförmig": "gasförmig"}.get(st["phase"], st["phase"])


def werte():
    W = {"A": A, "U_PG": U_PG}
    pg = gw.phasengrenze()
    W["pg"] = pg
    T_kG, p_kG = pg["krit"]
    p_cb = pg["cricondenbar"][1]

    # -- Kaverne & Gassäule --
    voll = saeule(A["p_max"])
    leer = saeule(A["p_min"])
    p_grenz = sekante(lambda pu: kopfdruck(pu) - p_cb, 170.0, 180.0)
    grenz = saeule(p_grenz)
    W["kav"] = {}
    for name, sl, pu in (("voll", voll, A["p_max"]), ("grenz", grenz, p_grenz), ("leer", leer, A["p_min"])):
        z, p, T, rho, zwei = sl
        tief_2ph = z[zwei].max() if zwei.any() else 0.0
        W["kav"][name] = dict(p_unten=pu, p_kopf=p[-1], T_kopf=T[-1], rho_kopf=rho[-1],
                              rho_unten=rho[0], profil=profil_50m(sl), tief_2ph=tief_2ph)
    W["T_Kav"] = A["T0"] + A["grad"] * A["z"]

    # -- Medienvergleich: Kopfdruck über der Teufe --
    W["mv_kopf"] = {zz: kopfdruck(A["p_max"], zz) for zz in (600, 800, 1000, 1200, 1400, 1600)}

    # -- S1 --
    p_kopf = W["kav"]["voll"]["p_kopf"]
    h1, s1 = h(A["p_S1"], A["T_S1"]), s(A["p_S1"], A["T_S1"])
    h2s = GEM.h_ps(p_kopf, s1)
    h2 = h1 + (h2s - h1) / A["eta_P"]
    T2, _ = GEM.T_ph(p_kopf, h2)
    rho_n = GEM.rho_norm()
    W["S1"] = dict(h1=h1, s1=s1, h2s=h2s, h2=h2, T2=T2, phase1=phase_text(A["p_S1"], A["T_S1"]),
                   phase2=phase_text(p_kopf, T2), rho_n=rho_n, w=h2 - h1)

    # -- S2 Basisfall: 1 Stufe bis p_V, Verflüssiger bei T_K, Pumpe --
    h1 = h(A["p_S2"], A["T_S2"]); s1 = s(A["p_S2"], A["T_S2"])
    h1s = GEM.h_ps(A["p_V"], s1)
    h1a = h1 + (h1s - h1) / A["eta_V1"]
    T1a, _ = GEM.T_ph(A["p_V"], h1a)
    p_bl_TK, p_tau_TK = gw.blasendruck(A["T_K"]), gw.taudruck(A["T_K"])
    # Blasen- und Tautemperatur bei p_V (Temperaturgleit der Kondensation)
    T_bl_pV = _T_auf_linie(pg["T_blase"], pg["p_blase"], A["p_V"])
    T_tau_pV = _T_auf_linie(pg["T_tau"], pg["p_tau"], A["p_V"])
    hV = h(A["p_V"], A["T_K"])
    sV = s(A["p_V"], A["T_K"])
    hPs = GEM.h_ps(p_kopf, sV)
    hPa = hV + (hPs - hV) / A["eta_P"]
    TPa, _ = GEM.T_ph(p_kopf, hPa)
    W["S2"] = dict(h1=h1, h1s=h1s, h1a=h1a, T1a=T1a, p_bl_TK=p_bl_TK, p_tau_TK=p_tau_TK,
                   T_bl_pV=T_bl_pV, T_tau_pV=T_tau_pV, hV=hV, phaseV=phase_text(A["p_V"], A["T_K"]),
                   hPs=hPs, hPa=hPa, TPa=TPa, w1=h1a - h1, wP=hPa - hV, qV=h1a - hV)

    # -- S2 Variante: 2 Stufen bis p_V --
    p_zw_v = np.sqrt(A["p_S2"] * A["p_V"])
    h1s_v = GEM.h_ps(p_zw_v, s1)
    h1a_v = h1 + (h1s_v - h1) / A["eta_V1"]
    T1a_v, _ = GEM.T_ph(p_zw_v, h1a_v)
    hZK = h(p_zw_v, A["T_K"])
    h2s_v = GEM.h_ps(A["p_V"], s(p_zw_v, A["T_K"]))
    h2a_v = hZK + (h2s_v - hZK) / A["eta_V2"]
    T2a_v, _ = GEM.T_ph(A["p_V"], h2a_v)
    W["S2v"] = dict(p_zw=p_zw_v, h1s=h1s_v, h1a=h1a_v, T1a=T1a_v, hZK=hZK, h2s=h2s_v, h2a=h2a_v,
                    T2a=T2a_v, w1=h1a_v - h1, w2=h2a_v - hZK, phaseZK=phase_text(p_zw_v, A["T_K"]))

    # -- Vergleich Durchverdichten: 2 Stufen bis Kopfdruck --
    h1s_d = GEM.h_ps(A["p_zw"], s1)
    h1a_d = h1 + (h1s_d - h1) / A["eta_V1"]
    T1a_d, _ = GEM.T_ph(A["p_zw"], h1a_d)
    hZK_d = h(A["p_zw"], A["T_K"])
    h2s_d = GEM.h_ps(p_kopf, s(A["p_zw"], A["T_K"]))
    h2a_d = hZK_d + (h2s_d - hZK_d) / A["eta_V2"]
    T2a_d, _ = GEM.T_ph(p_kopf, h2a_d)
    hN = h(p_kopf, TPa)
    W["Dv"] = dict(h1s=h1s_d, h1a=h1a_d, T1a=T1a_d, hZK=hZK_d, h2s=h2s_d, h2a=h2a_d, T2a=T2a_d,
                   hN=hN, w1=h1a_d - h1, w2=h2a_d - hZK_d)
    # zulässiger Bereich Zwischendruck: unten 95-°C-Grenze Stufe 2, oben Taudruck - 3 bar
    W["Dv"]["p_zw_min"] = _p_zw_min(s1, h1, p_kopf)
    W["Dv"]["p_zw_max"] = p_tau_TK - U_PG

    # -- Diagrammdaten --
    W["dia"] = diagrammdaten(pg)
    return W


def _T_auf_linie(T_linie, p_linie, p):
    """Temperatur, bei der eine Phasenlinie den Druck p erreicht (unterhalb der Cricondenbar)."""
    T_linie, p_linie = np.asarray(T_linie), np.asarray(p_linie)
    ordnung = np.argsort(T_linie)
    T_s, p_s = T_linie[ordnung], p_linie[ordnung]
    # nur den monotonen Teil bis zum Druckmaximum
    i_max = int(np.argmax(p_s))
    # oberhalb des Tiefpunkts der Blasenlinie (-37 °C) ist p(T) monoton steigend
    i_min = int(np.argmin(p_s[:i_max + 1]))
    return float(np.interp(p, p_s[i_min:i_max + 1], T_s[i_min:i_max + 1]))


def _p_zw_min(s1, h1, p_kopf):
    """Kleinster Zwischendruck, bei dem Stufe 2 (T_K -> Kopfdruck) höchstens T_max erreicht."""
    def T_aus(p_zw):
        h2s = GEM.h_ps(p_kopf, s(p_zw, A["T_K"]))
        hzk = h(p_zw, A["T_K"])
        return GEM.T_ph(p_kopf, hzk + (h2s - hzk) / A["eta_V2"])[0] - A["T_max"]
    return sekante(T_aus, 40.0, 50.0, tol=1e-3)


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
    for T in np.arange(-80.0, 110.0 + 0.25, 0.5):          # bis 110 °C (S2 Basisfall 100 °C)
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
    W = werte()
    kurz = {k: v for k, v in W.items() if k not in ("dia", "pg")}
    for name in ("voll", "grenz", "leer"):
        kurz["kav"][name] = {k: v for k, v in W["kav"][name].items() if k != "profil"}
    print(json.dumps(kurz, indent=1, default=float, ensure_ascii=False))
    print(f"Rechenzeit {time.time() - t:.0f} s")
