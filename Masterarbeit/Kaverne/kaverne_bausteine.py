# -*- coding: utf-8 -*-
"""
Gemeinsame Bausteine der Kavernenrechnung - tiefe und flache Kaverne
============================================================================
Annahmen und Rechenbausteine aller Kaverne-Skripte (01-06) stehen hier an
EINER Stelle. Die Stoffe (reines CO₂, Worst-Case-Gemisch) kommen unverändert
aus Einspeicherung/Begleitstoffe_CO2 (gemisch_worstcase.py,
einspeicherung_bausteine.py) - Ein- und Ausspeicherung rechnen also mit
demselben Stoffmodell und derselben Zusammensetzung.

Kavernen (Stand 01.10.2026) - gleiche Kaverne, nur die Teufe ändert sich
                        tief (V1)      flach (V2)
  LCCS-Teufe            1200 m         700 m          Q-030 Tab. 1, Option 2 / Option 3
  Bezugsteufe Temperatur 1405 m        905 m          LCCS + 205 m wie Q-028 Tab. 1
                                                      (LCCS 1150 m, Kavernentemperatur bei 1355 m)
  Gebirge in Bezugsteufe 52,2 °C       37,2 °C        10 °C + 0,03 K/m (Q-028)
  p_max an der LCCS     210 bar        122,5 bar      V1 wie Einspeicherung; V2 mit denselben
  p_min an der LCCS     70 bar         40,8 bar       Gradienten 0,175 / 0,0583 bar/m
                                                      (Q-030 Option 3: 125 / 40 bar)
  Volumen               650.000 m³     650.000 m³     Q-028 Tab. 1 ("accessible for storage")
  Gleiches Volumen und gleiche Form, damit der Vergleich nur die Teufe zeigt.
  Uniper-Bestandskavernen haben 250.000 m³ (Q-030 Tab. 1, alle Teufen); Massen
  und Raten aus der Druckänderungsrate skalieren linear mit V, Phasen,
  Temperaturen und Anteile (%) hängen nicht vom Volumen ab.

Betrieb
  Druckänderungsrate    ≤ 10 bar/d an der LCCS (Q-030 Kap. 1.2.1; Q-089 Tab. 2),
                        vorsichtig 6 bar/d (Q-028 Tab. 1)
  Förderstrang          8 5/8" 36# J55, Innendurchmesser 198,8 mm (Q-030 Kap. 1.2.1)
                        Strömungsgeschwindigkeit ≤ 20 m/s (Q-030 Kap. 1.2.1)
  Rohrreibung           Darcy-Reibungszahl 0,016 (Q-003 Kap. 6.2: 0,015-0,017, neues Stahlrohr)
  Einspeisetemperatur   30 °C an der LCCS (Q-028 Tab. 1)
  Stillstand            21,67 d zwischen Aus- und Einspeichern (Q-028 Kap. 4)
  Wärmeübergang         UA = 546 kW/K bei 650.000 m³, an der Q-028-Simulation kalibriert
                        (Kavernenrechner/zyklus.py; Nachrechnung in 03); für andere
                        Volumen über die Oberfläche (∝ V^2/3) umgerechnet
  Durchsatz             50.000 / 100.000 Nm³/h (wie Einspeicherung)

Modellgrenzen (gelten für alle Skripte)
  Kaverne als ein ideal durchmischter Knoten (Kavernenmitte), Druck an der
  LCCS = Knotendruck - ρ·g·(z_Mitte - z_LCCS). Q-028 bestätigt dauerhafte
  Konvektion im Kavernenraum, das stützt die Durchmischung. Keine Sole, keine
  Lösung von CO₂ in Sole (Q-028: "completely debrined"), Wärmeübergang als
  konstantes UA statt instationärer Wärmeleitung im Gebirge.

Einheiten an den Schnittstellen: bar, °C, kJ/kg, kg/m³, kg/s, t.
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI
from matplotlib.path import Path as Polygonpfad
from scipy.optimize import brentq

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Einspeicherung" / "Begleitstoffe_CO2"))
import einspeicherung_bausteine as eb  # noqa: E402  (Stoffklassen, Durchsatz, Gebirge)
import gemisch_worstcase as gw         # noqa: E402  (Zusammensetzung, Phasengrenze)

# ---- 1) Annahmen --------------------------------------------------------------
G = 9.81                                   # m/s²
T_OBERFLAECHE, GRADIENT = eb.T_OBERFLAECHE, eb.GRADIENT   # 10 °C, 0,03 K/m (Q-028)
T_KRIT = PropsSI("Tcrit", "CO2") - 273.15  # 30,98 °C
P_KRIT = PropsSI("pcrit", "CO2") / 1e5     # 73,77 bar

GRAD_PMAX = 210.0 / 1200.0                 # bar/m, Kaverne V1: 210 bar an der LCCS in 1200 m
GRAD_PMIN = 70.0 / 1200.0                  # bar/m, Kaverne V1: 70 bar an der LCCS in 1200 m
V_GEO = 650000.0                           # m³, Q-028 Tab. 1
DZ_BEZUG = 205.0                           # m, Bezugsteufe der Kavernentemperatur unter der LCCS (Q-028 Tab. 1)

DPDT_MAX = 10.0                            # bar/d (Q-030, Q-089)
DPDT_VORSICHTIG = 6.0                      # bar/d (Q-028)
D_STRANG = 7.825 * 0.0254                  # m, 8 5/8" 36# -> 198,8 mm
A_STRANG = np.pi * D_STRANG**2 / 4.0       # m²
V_MAX_STRANG = 20.0                        # m/s (Q-030)
F_DARCY = 0.016                            # - (Q-003 Kap. 6.2)
T_EIN_LCCS = 30.0                          # °C (Q-028)
T_STILLSTAND = 21.67                       # d (Q-028)
UA_REF, V_REF = 546.0, 650000.0            # kW/K bei m³ (kalibriert an Q-028, siehe 03)
V_NORM_MIN, V_NORM_MAX = eb.V_NORM_MIN, eb.V_NORM_MAX     # Nm³/h


def T_gebirge(z):
    """Ungestörte Gebirgstemperatur [°C] in der Teufe z [m]."""
    return T_OBERFLAECHE + GRADIENT * z


@dataclass(frozen=True)
class Kaverne:
    name: str
    kurz: str
    z_lccs: float          # m, Teufe letzte zementierte Rohrtour (Bezug für p_max/p_min)
    z_mitte: float         # m, Bezugsteufe der Kavernentemperatur ("Kavernenmitte")
    p_max: float           # bar an der LCCS
    p_min: float           # bar an der LCCS
    volumen: float = V_GEO

    @property
    def T_lccs(self):
        return T_gebirge(self.z_lccs)

    @property
    def T_mitte(self):
        return T_gebirge(self.z_mitte)

    @property
    def UA(self):
        """Wärmeübergang Kaverne <-> Gebirge [kW/K], mit der Oberfläche skaliert (∝ V^2/3)."""
        return UA_REF * (self.volumen / V_REF) ** (2.0 / 3.0)


TIEF = Kaverne("Kaverne tief (V1, LCCS 1200 m)", "tief", 1200.0, 1200.0 + DZ_BEZUG, 210.0, 70.0)
FLACH = Kaverne("Kaverne flach (V2, LCCS 700 m)", "flach", 700.0, 700.0 + DZ_BEZUG,
                GRAD_PMAX * 700.0, GRAD_PMIN * 700.0)
KAVERNEN = (TIEF, FLACH)


# ---- 2) Stoffe: einheitliche Schnittstelle für Kaverne und Förderstrang -------
class Medium:
    """Stoffwerte für reines CO₂ und das Worst-Case-Gemisch mit gleicher Schnittstelle.

    Die Einspeicherung braucht nur Zustände aus (p, T). In Kaverne und
    Förderstrang kommen zwei weitere Eingabepaare dazu:
      (ρ, u)  Kavernenbilanz - Masse und innere Energie sind die Bilanzgrößen
      (p, h)  strömende Säule - Energiebilanz h + g·z = konst.
    Reines CO₂ rechnet CoolProp direkt, auch im Zweiphasengebiet (Dampfanteil q).

    Für das Gemisch sind diese Flashes zu langsam (PH-Flash ~1 s je Aufruf,
    freier PT-Flash ~55 ms). Deshalb: außerhalb der Hüllkurve wird die Phase
    vorgegeben (dichter Ast über der Cricondenbar bzw. Blasenlinie, sonst
    Gasast) - geprüft gegen den freien Flash von gemisch_worstcase.pt_zustand
    auf einem Raster 10-300 bar / -10-100 °C, Abweichung < 1e-6. Innerhalb der
    Hüllkurve rechnet der freie Flash (zweiphasig, langsam, kommt selten vor).
    """

    def __init__(self, stoff):
        self.stoff = stoff
        self.name, self.kurz = stoff.name, stoff.kurz
        self.ist_gemisch = isinstance(stoff, eb.Gemisch)
        if self.ist_gemisch:
            pg = stoff.pg
            self._huelle = Polygonpfad(np.column_stack([
                np.concatenate([pg["T_tau"], pg["T_blase"]]),
                np.concatenate([pg["p_tau"], pg["p_blase"]])]))
            self.p_cb = pg["cricondenbar"][1]
            self.T_ct = pg["cricondentherm"][0]
            self._gas = gw.gemisch()
            self._gas.specify_phase(CP.iphase_gas)
            self._dicht = gw.gemisch()
            self._dicht.specify_phase(CP.iphase_liquid)
            self._frei = gw.gemisch()
        else:
            self.p_cb, self.T_ct = P_KRIT, T_KRIT
            self._AS = CP.AbstractState("HEOS", "CO2")

    # -- Phasengrenze --
    def in_huelle(self, p, T):
        """Gemisch: liegt (p, T) im Zweiphasengebiet? Reines CO₂: nur auf der Siedelinie."""
        if self.ist_gemisch:
            return bool(self._huelle.contains_point((T, p)))
        if T >= T_KRIT:
            return False
        ps = PropsSI("P", "T", T + 273.15, "Q", 0, "CO2") / 1e5
        return abs(p - ps) / ps < 5e-4

    def _pt(self, p, T):
        """AbstractState des Gemischs bei (p, T) - schnell außerhalb der Hüllkurve.

        Innerhalb der Hüllkurve rechnet der freie Flash (zweiphasig). Direkt an der
        Phasengrenze und nahe dem kritischen Punkt scheitern einzelne Flashes
        ("lost a phase", keine Dichtelösung) - dann wird mit leicht verschobener
        Temperatur wiederholt (≤ 0,2 K, für die Auslegung ohne Bedeutung).
        """
        for dT in (0.0, 0.03, -0.03, 0.2, -0.2):
            Tt = T + dT
            if self.in_huelle(p, Tt):
                try:
                    return gw.pt_zustand(p, Tt, self._frei)
                except ValueError:
                    pass
            p_bl = gw.blasendruck(Tt)
            dicht = p > self.p_cb or (not np.isnan(p_bl) and p > p_bl)
            # Überkritisch und gasähnlich (z. B. 85 bar / 70 °C) findet der dichte Ast
            # keine Lösung, sehr dicht (250 bar) der Gasast nicht - dann der andere Ast.
            for AS in ((self._dicht, self._gas) if dicht else (self._gas, self._dicht)):
                try:
                    AS.update(CP.PT_INPUTS, p * 1e5, Tt + 273.15)
                    return AS
                except ValueError:
                    pass
        raise ValueError(f"Gemisch: kein Zustand bei {p:.2f} bar / {T:.2f} °C")

    # -- Zustände aus (p, T) --
    def rho(self, p, T):
        if self.ist_gemisch:
            return self._pt(p, T).rhomass()
        return self.stoff.rho(p, T)          # nahe der Siedelinie Gasast, wie Einspeicherung

    def h(self, p, T):
        if self.ist_gemisch:
            return self._pt(p, T).hmass() / 1000
        try:
            return self.stoff.h(p, T)
        except ValueError:                   # genau auf der Siedelinie: Flüssigseite
            return self.stoff.h(p, T - 0.01)

    def u(self, p, T):
        if self.ist_gemisch:
            return self._pt(p, T).umass() / 1000
        return PropsSI("U", "P", p * 1e5, "T", T + 273.15, "CO2") / 1000

    def schall(self, p, T):
        """Schallgeschwindigkeit [m/s]; nan im Zweiphasengebiet."""
        try:
            if self.ist_gemisch:
                AS = self._pt(p, T)
                return np.nan if AS.phase() == CP.iphase_twophase else AS.speed_sound()
            return PropsSI("A", "P", p * 1e5, "T", T + 273.15, "CO2")
        except ValueError:
            return np.nan

    def drho_dp(self, p, T, dp=0.5):
        """(∂ρ/∂p)_T [kg/m³ je bar], zentrale Differenz."""
        return (self.rho(p + dp, T) - self.rho(p - dp, T)) / (2 * dp)

    def phase(self, p, T):
        return self.stoff.phase(p, T)

    # -- Zustand aus (p, h): strömende Säule --
    def zustand_ph(self, p, h, T0):
        """T, ρ und Dampfanteil q (None = einphasig) bei p [bar], h [kJ/kg]."""
        if not self.ist_gemisch:
            AS = self._AS
            AS.update(CP.HmassP_INPUTS, h * 1000, p * 1e5)
            q = AS.Q() if AS.phase() == CP.iphase_twophase else None
            return dict(T=AS.T() - 273.15, rho=AS.rhomass(), q=q)
        # h(p, T) ist monoton in T, hat aber an der Phasengrenze einen Knick -> Sekante,
        # bei Fehlschlag geklammert suchen
        f = lambda x: self.h(p, x) - h
        try:
            T = _sekante(f, T0, T0 - 0.5, tol=1e-6)
            if not T0 - 30.0 < T < T0 + 10.0:       # im Zweiphasengebiet ist h(T) flach - Ausreißer
                raise RuntimeError
        except (RuntimeError, ValueError):
            lo, hi = T0 - 3.0, T0 + 1.0
            while f(lo) > 0:
                lo -= 10.0
            while f(hi) < 0:
                hi += 10.0
            T = brentq(f, lo, hi, xtol=1e-4)
        AS = self._pt(p, T)
        q = None
        if self.in_huelle(p, T):
            q = AS.Q() if AS.phase() == CP.iphase_twophase else np.nan
        return dict(T=T, rho=AS.rhomass(), q=q)

    # -- Zustand aus (ρ, u): Kavernenbilanz --
    def zustand_rho_u(self, rho, u, T0):
        """p, T, h und Dampfanteil q bei ρ [kg/m³], u [kJ/kg]; T0 = Startwert [°C]."""
        if not self.ist_gemisch:
            AS = self._AS
            AS.update(CP.DmassUmass_INPUTS, rho, u * 1000)
            q = AS.Q() if AS.phase() == CP.iphase_twophase else None
            return dict(p=AS.p() / 1e5, T=AS.T() - 273.15, h=AS.hmass() / 1000, q=q)
        # Gemisch: Zustandsgleichung ist explizit in (ρ, T) - nur T iterieren
        AS = self._gas

        def f(T):
            AS.update(CP.DmassT_INPUTS, rho, T + 273.15)
            return AS.umass() / 1000 - u
        try:
            T = _sekante(f, T0, T0 - 0.5)
        except RuntimeError:
            T = brentq(f, T0 - 15.0, T0 + 15.0, xtol=1e-6)
        AS.update(CP.DmassT_INPUTS, rho, T + 273.15)
        p = AS.p() / 1e5
        # im Zweiphasengebiet ist der (ρ,T)-Wert nur metastabil -> nur markieren (q = nan);
        # die Gemisch-Bilanz endet dort (stopp_bei_zweiphasig in 05)
        q = np.nan if self.in_huelle(p, T) else None
        return dict(p=p, T=T, h=AS.hmass() / 1000, q=q)

    def rho_norm(self):
        return self.stoff.rho_norm()


def _sekante(f, x0, x1, tol=1e-7, maxit=40):
    f0, f1 = f(x0), f(x1)
    for _ in range(maxit):
        if abs(f1) < tol:
            return x1
        if f1 == f0:
            break
        x0, f0, x1 = x1, f1, x1 - f1 * (x1 - x0) / (f1 - f0)
        f1 = f(x1)
    if abs(f1) < 1e-4:
        return x1
    raise RuntimeError("Sekante konvergiert nicht")


REIN = Medium(eb.ReinCO2())
_GEMISCH = None


def gemisch():
    """Worst-Case-Gemisch als Medium (erst bei Bedarf - die Phasengrenze kostet ~1 s)."""
    global _GEMISCH
    if _GEMISCH is None:
        _GEMISCH = Medium(eb.Gemisch())
    return _GEMISCH


def massenstrom(med):
    """Massenstrom [kg/s] bei 50.000 und 100.000 Nm³/h (0 °C, 1,01325 bar)."""
    return eb.massenstrom(med.stoff)


def nm3h(med, m_dot):
    """kg/s -> Nm³/h."""
    return m_dot * 3600.0 / med.rho_norm()


# ---- 3) Ruhende Säule (Stillstand) ---------------------------------------------
def gassaeule(med, kav, p_lccs, n=600):
    """dp/dz = ρ(p,T)·g von der LCCS nach oben, T = Gebirge (Stillstand, Q-028 Kap. 3).

    Rückgabe: Kopfdruck [bar] und Profil als Array (z, p, T, ρ) von oben nach unten.
    """
    dz = kav.z_lccs / n
    p = p_lccs
    profil = []
    for i in range(n):
        z = kav.z_lccs - i * dz
        rho = med.rho(p, T_gebirge(z))
        profil.append((z, p, T_gebirge(z), rho))
        p -= rho * G * dz / 1e5
    profil.append((0.0, p, T_gebirge(0.0), med.rho(p, T_gebirge(0.0))))
    return p, np.array(profil[::-1])


def kopfdruck(med, kav, p_lccs, n=600):
    return gassaeule(med, kav, p_lccs, n)[0]


def p_lccs_fuer_kopf(med, kav, p_kopf, n=600):
    """Welcher Druck an der LCCS ergibt im Stillstand den Kopfdruck p_kopf? (Sekante)"""
    rho0 = med.rho(p_kopf + 20.0, T_gebirge(kav.z_lccs / 2))
    x0 = p_kopf + rho0 * G * kav.z_lccs / 1e5
    return _sekante(lambda pl: kopfdruck(med, kav, pl, n) - p_kopf, x0, x0 + 5.0, tol=1e-6)


def p_mitte(med, kav, p_lccs, T):
    """Druck in Kavernenmitte aus dem Druck an der LCCS (Kaverneninhalt bei T)."""
    pm = p_lccs
    for _ in range(6):
        pm = p_lccs + med.rho(0.5 * (p_lccs + pm), T) * G * (kav.z_mitte - kav.z_lccs) / 1e5
    return pm


def inventar(med, kav, p_lccs, T=None):
    """Kaverneninhalt [t] bei p an der LCCS und Kaverneninhalt bei T (Standard: Gebirge)."""
    T = kav.T_mitte if T is None else T
    return med.rho(p_mitte(med, kav, p_lccs, T), T) * kav.volumen / 1000.0


# ---- 4) Kavernenbilanz über einen Speicherzyklus --------------------------------
def kavernenzyklus(med, kav, m_dot, phasen=None, dpdt_max=DPDT_MAX, dt=0.02, T_ein=T_EIN_LCCS,
                   stopp_bei_zweiphasig=False, T_geb=None, p_start=None):
    """Massen- und Energiebilanz des Kaverneninhalts (ein Knoten, ideal durchmischt).

        dm/dt = ṁ                                   (+ ein, - aus)
        dU/dt = ṁ·h_strom + UA·(T_Gebirge - T)      h_strom: aus = h(Kaverne), ein = h(p, 30 °C)

    Start: voll (p_max an der LCCS, oder p_start) und Gebirgstemperatur, also nach
    langem Stillstand. Die Rate wird gekürzt, sobald der Druck an der LCCS schneller als
    dpdt_max [bar/d] fällt oder steigt (Q-028, Q-030). Zustand je Schritt aus (ρ, u).

    Rückgabe: Liste von dicts je Zeitschritt (t [d], Abschnitt, p_lccs, p_mitte, T, m [t],
    m_dot [kg/s, + ein / - aus], begrenzt, q).
    """
    phasen = phasen or [("aus", kav.p_min), ("still", T_STILLSTAND),
                        ("ein", kav.p_max), ("still", T_STILLSTAND)]
    V, UA = kav.volumen, kav.UA
    T_geb = kav.T_mitte if T_geb is None else T_geb       # abweichend nur für die Q-028-Nachrechnung
    dzk = kav.z_mitte - kav.z_lccs
    pm = p_mitte(med, kav, kav.p_max if p_start is None else p_start, T_geb)
    m = med.rho(pm, T_geb) * V
    U = m * med.u(pm, T_geb)                  # kJ
    T, t = T_geb, 0.0
    dts = dt * 86400.0
    verlauf = []

    def p_lccs_von(zs, masse):
        return zs["p"] - masse / V * G * dzk / 1e5

    for art, ziel in phasen:
        t_ab = 0.0
        while True:
            zs = med.zustand_rho_u(m / V, U / m, T)
            T = zs["T"]
            pl = p_lccs_von(zs, m)
            fertig = ((art == "aus" and pl <= ziel) or (art == "ein" and pl >= ziel)
                      or (art == "still" and t_ab >= ziel) or t > 1500)
            md = {"aus": -m_dot, "ein": m_dot}.get(art, 0.0)
            if fertig:
                md = 0.0
            h_strom = zs["h"] if md <= 0 else med.h(zs["p"], T_ein)
            begrenzt = False
            if md != 0.0:                     # Probeschritt: dp/dt an der LCCS einhalten
                for _ in range(4):
                    m2 = m + md * dts
                    U2 = U + (md * h_strom + UA * (T_geb - T)) * dts
                    rate = abs(p_lccs_von(med.zustand_rho_u(m2 / V, U2 / m2, T), m2) - pl) / dt
                    if rate <= dpdt_max * 1.001:
                        break
                    md *= dpdt_max / rate
                    begrenzt = True
            verlauf.append(dict(t=t, art=art, p_lccs=pl, p_mitte=zs["p"], T=T, m=m / 1000,
                                m_dot=md, begrenzt=begrenzt, q=zs["q"]))
            if fertig or (stopp_bei_zweiphasig and zs["q"] is not None):
                break
            m += md * dts
            U += (md * h_strom + UA * (T_geb - T)) * dts
            t += dt
            t_ab += dt
        if stopp_bei_zweiphasig and verlauf[-1]["q"] is not None:
            break
    return verlauf


def zyklus_kennwerte(verlauf):
    """Kennwerte je Abschnitt (aus, still, ein, still) aus kavernenzyklus()."""
    abschnitte, aktuell = [], None
    for x in verlauf:
        if aktuell is None or x["art"] != aktuell[0]["art"]:
            aktuell = []
            abschnitte.append(aktuell)
        aktuell.append(x)
    kw = []
    for a in abschnitte:
        mit_strom = [x for x in a if x["m_dot"] != 0.0]
        zp = [x for x in a if x["q"] is not None]
        kw.append(dict(
            art=a[0]["art"], t_start=a[0]["t"], dauer=a[-1]["t"] - a[0]["t"],
            p_lccs_start=a[0]["p_lccs"], p_lccs_ende=a[-1]["p_lccs"],
            T_start=a[0]["T"], T_ende=a[-1]["T"],
            T_min=min(x["T"] for x in a), T_max=max(x["T"] for x in a),
            m_start=a[0]["m"], m_ende=a[-1]["m"],
            m_dot_mittel=float(np.mean([abs(x["m_dot"]) for x in mit_strom])) if mit_strom else 0.0,
            anteil_begrenzt=(sum(x["begrenzt"] for x in mit_strom) / len(mit_strom)) if mit_strom else 0.0,
            zweiphasig=bool(zp), t_zweiphasig=zp[0]["t"] if zp else None,
            q_max=max((x["q"] for x in zp if not np.isnan(x["q"])), default=None)))
    return kw


def grenzrate(med, kav, dpdt_max=DPDT_MAX, lo=2.0, hi=150.0, it=10):
    """Höchste konstante Ausspeicherrate [kg/s], bei der der Kaverneninhalt einphasig bleibt.

    Bisektion über die Rate. Geprüft wird nur das Ausspeichern (dort kühlt die
    Kaverne ab). Bleibt sogar hi einphasig, begrenzt die Druckänderungsrate
    allein - dann wird hi zurückgegeben und als 'nicht bindend' gekennzeichnet.
    """
    def einphasig(rate):
        v = kavernenzyklus(med, kav, rate, phasen=[("aus", kav.p_min)], dpdt_max=dpdt_max,
                           dt=0.05, stopp_bei_zweiphasig=True)
        return all(x["q"] is None for x in v)
    if einphasig(hi):
        return dict(rate=hi, bindend=False)
    if not einphasig(lo):
        return dict(rate=None, bindend=True)
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if einphasig(mid) else (lo, mid)
    return dict(rate=lo, bindend=True)


# ---- 5) Strömende Säule im Förderstrang (Ausspeichern) -------------------------
def strang_aufwaerts(med, kav, p_lccs, T_unten, m_dot, modus="adiabat", n=300, h_unten=None):
    """Förderstrang von der LCCS zum Kopf beim Ausspeichern.

        dp = -(ρ·g + f/D · ρ·v²/2)·dz        Schwere + Reibung (Darcy)
        modus "adiabat":  h + g·z = konst.  -> schnelle Förderung, kein Wärmeaustausch
        modus "gebirge":  T = T_Gebirge(z)  -> langsame Förderung, voller Wärmeaustausch
    Der reale Zustand liegt zwischen beiden Grenzfällen (Q-028 Kap. 3: zuverlässig
    nur mit einem Bohrlochmodell mit Mehrphasenströmung).

    h_unten: Enthalpie am Strangeintritt, wenn die Kaverne zweiphasig ist (dann
    strömt Dampf vom Kavernendach in den Strang); sonst h(p_lccs, T_unten).

    Rückgabe: Profil (z, p, T, ρ, v, q) von oben nach unten und Kopfzustand (dict).
    Kopf = None, wenn der Druck unterwegs auf 1 bar fällt (Säule trägt nicht).
    """
    dz = kav.z_lccs / n
    p, T = p_lccs, T_unten
    h = med.h(p, T) if h_unten is None else h_unten
    profil = []
    for i in range(n + 1):
        z = kav.z_lccs - i * dz
        if modus == "adiabat":
            zs = med.zustand_ph(p, h, T)
        else:
            T_z = T_gebirge(z)
            zs = dict(T=T_z, rho=med.rho(p, T_z), q=None)
        T, rho = zs["T"], zs["rho"]
        v = m_dot / (rho * A_STRANG)
        profil.append((z, p, T, rho, v, zs["q"]))
        if i == n:
            break
        p -= (rho * G + F_DARCY / D_STRANG * rho * v * v / 2.0) * dz / 1e5
        h -= G * dz / 1000.0
        if p <= 1.0:
            return np.array(profil[::-1], dtype=object), None
    z, p, T, rho, v, q = profil[-1]
    kopf = dict(p=p, T=T, rho=rho, v=v, q=q, zweiphasig_im_strang=any(r[5] is not None for r in profil),
                v_max=max(r[4] for r in profil))
    return np.array(profil[::-1], dtype=object), kopf


# ---- 6) Hilfsfunktionen: JSON-Kette, Zahlenformat --------------------------------
def speichere_json(name, daten):
    """Ergebnis eines Prozessschritts für die folgenden Skripte ablegen."""
    def rein(x):
        if isinstance(x, dict):
            return {str(k): rein(v) for k, v in x.items()}
        if isinstance(x, (list, tuple, np.ndarray)):
            return [rein(v) for v in x]
        if isinstance(x, (np.floating, float)):
            return None if np.isnan(x) else float(x)
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, np.bool_):
            return bool(x)
        return x
    with open(ORDNER / name, "w", encoding="utf-8") as f:
        json.dump(rein(daten), f, ensure_ascii=False, indent=1)
    print(f"gespeichert: {name}")


def h_dampf(med, p):
    """Enthalpie [kJ/kg] des gesättigten Dampfs bei p (reines CO₂) bzw. auf der Taulinie (Gemisch)."""
    if not med.ist_gemisch:
        return PropsSI("H", "P", p * 1e5, "Q", 1, "CO2") / 1000
    AS = gw.gemisch()
    AS.update(CP.PQ_INPUTS, p * 1e5, 1.0)
    return AS.hmass() / 1000


def lade_json(name, erzeugt_von):
    datei = ORDNER / name
    if not datei.exists():
        raise FileNotFoundError(f"{name} fehlt - zuerst {erzeugt_von} ausführen.")
    with open(datei, encoding="utf-8") as f:
        return json.load(f)


def de(x, nd=1):
    """Zahl mit Dezimalkomma (für Abbildungen)."""
    return f"{x:.{nd}f}".replace(".", ",")


def ok(bedingung):
    return "✔" if bedingung else "✘"
