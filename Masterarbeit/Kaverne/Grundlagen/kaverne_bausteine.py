# -*- coding: utf-8 -*-
"""
Gemeinsame Bausteine der Kavernenrechnung - Referenzkaverne (LCCS 1200 m)
============================================================================
Annahmen und Rechenbausteine aller Kaverne-Skripte stehen hier
(Ordner Reines_CO2/, Begleitstoffe_CO2/, Ausspeichergas/).

Die Stoffe (reines CO₂, Worst-Case-Gemisch) kommen unverändert aus Einspeicherung/Begleitstoffe_CO2/Grundlagen
(gemisch_worstcase.py, einspeicherung_bausteine.py) - Ein- und Ausspeicherung rechnen damit mit demselben
Stoffmodell und derselben Zusammensetzung.


Stand 15.10.2026 - nach der Besprechung mit Katrin Vosbeck (Kavernenannahmen):
  * nur noch die tiefe Kaverne (LCCS 1200 m, 650.000 m³); die flache Kaverne entfällt.
    Begründung aus der Quelle: DBI verwirft die flache Option 3 selbst, weil dort fast
    sofort eine Flüssigphase in Kaverne bzw. am Kopf entsteht (Q-030 S. 17, Kap. 1.2.1.2).
    Die Wirkung der Teufe bleibt über das Teufenfenster (Schritt 02) erklärt.
  * 250.000 m³ (Uniper-Bestand) wird nur diskutiert, nicht gerechnet (Q-029, Q-030 Tab. 1).
  * Förderstrang nur noch adiabate betrachtung (schnelle Förderung, kein Wärmeaustausch mit dem
    Gebirge); der Grenzfall "voller Wärmeaustausch" entfällt, da Katrin meinte das dies vernachlässigbar klein ist.
    Der Wärmeaustausch zwischen Kaverneninhalt und Gebirge bleibt (UA).
  * Einspeisung gekoppelt an die Einspeicherung: Enthalpie am Kopf = Pumpenaustritt
    S1 bzw. S2, an der LCCS h = h_Kopf + g·z (adiabater Strang) - statt fest 30 °C.
  * Regelung über den Bohrlochkopfdruck: Kopfdruck beim Ein- und Ausspeichern wird
    über den ganzen Zyklus ausgewiesen (max. = Pumpe, min. = Rückverdichtung).
  * Betriebsweise: Stillstand 21,67 d (Q-028) gegen kontinuierlich (0 d).

Annahmen                Wert                    Quelle (Fundstelle)
  LCCS-Teufe            1200 m                  Q-030 Tab. 1, Option 2 (Uniper-Bestand)
  Bezugsteufe Inhalt    LCCS + 205 m = 1405 m   Q-028 Tab. 1: LCCS 1150 m, Kavernen-
                                                temperatur in 1355 m angegeben
  Gebirge               10 °C + 0,03 K/m        Q-028 Kap. 3 / Tab. 1
  p_max an der LCCS     210 bar                 Vorgabe M. Wall; passt zu Epe (Q-035 Folie 5)
  p_min an der LCCS     70 bar                  Q-028 Tab. 1
  Volumen               650.000 m³              Q-028 Tab. 1 ("accessible for storage");
                                                bestätigt in der Besprechung 15.10.2026
  Druckänderungsrate    ≤ 10 bar/d an der LCCS  Q-030 Kap. 1.2.1; Q-089 Tab. 2
                        (vorsichtig 6 bar/d)    Q-028 Tab. 1
  Förderstrang          8 5/8" 36# J55,         Q-030 Tab. 1 und Kap. 1.2.1
                        Innendurchmesser 198,8 mm
  Strömungsgeschw.      ≤ 20 m/s                Q-030 Kap. 1.2.1
  Rohrreibung           Darcy f = 0,016         Q-003 Kap. 6.2: 0,015-0,017 (neues Stahlrohr)
  Stillstand            21,67 d                 Q-028 Kap. 4, S. 10 (Betriebsszenario der
                                                Simulation, an der UA kalibriert ist); zulässig
                                                nach Q-035 Folie 31 (unterer Druckbereich
                                                höchstens 60 Tage je Jahr)
  Wärmeübergang         UA = 546 kW/K           an der Simulation aus Q-028 kalibriert
                                                (Nachrechnung in Schritt 03)
  Durchsatz             50.000 / 100.000 Nm³/h  wie Einspeicherung (abgestimmt mit M. Wall)
  Startzustand          voll, Gebirgstemperatur Q-028 Tab. 1 (gleiche Annahme)
  Einspeisung (Kopf)    h des Pumpenaustritts   einspeicherung_bausteine (S1: 91 bar / 15 °C,
                        im Auslegungspunkt      S2: Kühler 91 bar / 26 °C, jeweils + Pumpe);
                                                bei kleinerem Kopfdruck isenthalp gedrosselt
                                                (Q-030 S. 15: "injected with a constant
                                                temperature at the wellhead")

Modellgrenzen (gelten für alle Skripte)
  Kaverne als ein ideal durchmischtes Kontrollvolumen (Knoten - Kavernenmitte), Druck an der
  LCCS = Knotendruck - ρ·g·(z_Mitte - z_LCCS). Q-028 bestätigt dauerhafte
  Konvektion im Kavernenraum, das stützt die Durchmischung. Keine Sole, keine
  Lösung von CO₂ in Sole (Q-028: "completely debrined"), Wärmeübergang als
  konstantes UA statt instationärer Wärmeleitung im Gebirge. Förderstrang
  einphasig, homogen; wird er zweiphasig, wird das nur angezeigt (Q-028 S. 11:
  Bohrlochmodell mit Mehrphasenströmung nötig - für Aus- UND Einspeisung).

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

GRUNDLAGEN = Path(__file__).resolve().parent                 # Kaverne/Grundlagen
KAVERNE = GRUNDLAGEN.parent                                   # Kaverne
ORDNER_REIN = KAVERNE / "Reines_CO2"
ORDNER_GEM = KAVERNE / "Begleitstoffe_CO2"
ORDNER_AUSSPEICHERGAS = KAVERNE / "Ausspeichergas"
sys.path.insert(0, str(KAVERNE.parent / "Einspeicherung" / "Begleitstoffe_CO2" / "Grundlagen"))
import einspeicherung_bausteine as eb  # noqa: E402  (Stoffklassen, Pumpe, Durchsatz, Gebirge)
import gemisch_worstcase as gw         # noqa: E402  (Zusammensetzung, Phasengrenze)

# ---- 1) Annahmen --------------------------------------------------------------
G = 9.81                                   # m/s²
T_OBERFLAECHE, GRADIENT = eb.T_OBERFLAECHE, eb.GRADIENT   # 10 °C, 0,03 K/m (Q-028)
T_KRIT = PropsSI("Tcrit", "CO2") - 273.15  # 30,98 °C
P_KRIT = PropsSI("pcrit", "CO2") / 1e5     # 73,77 bar

GRAD_PMAX = 210.0 / 1200.0                 # bar/m (nur Teufenfenster in 02)
GRAD_PMIN = 70.0 / 1200.0                  # bar/m (nur Teufenfenster in 02)
V_GEO = 650000.0                           # m³, Q-028 Tab. 1
DZ_BEZUG = 205.0                           # m, Bezugsteufe der Kavernentemperatur unter der LCCS (Q-028 Tab. 1)

DPDT_MAX = 10.0                            # bar/d (Q-030 Kap. 1.2.1, Q-089 Tab. 2)
DPDT_VORSICHTIG = 6.0                      # bar/d (Q-028 Tab. 1)
D_STRANG = 7.825 * 0.0254                  # m, 8 5/8" 36# J55 -> 198,8 mm (Q-030 Tab. 1)
A_STRANG = np.pi * D_STRANG**2 / 4.0       # m²
V_MAX_STRANG = 20.0                        # m/s (Q-030 Kap. 1.2.1)
F_DARCY = 0.016                            # - (Q-003 Kap. 6.2: 0,015-0,017)
T_EIN_Q028 = 30.0                          # °C an der LCCS - nur noch für die Nachrechnung von Q-028
T_STILLSTAND = 21.67                       # d (Q-028 Kap. 4, S. 10)
STILLSTAENDE = {"Stillstand 21,67 d (Q-028)": T_STILLSTAND, "kontinuierlich (0 d)": 0.0}
UA_REF, V_REF = 546.0, 650000.0            # kW/K bei m³ (kalibriert an Q-028, siehe 03)
V_NORM_MIN, V_NORM_MAX = eb.V_NORM_MIN, eb.V_NORM_MAX     # Nm³/h
RATEN = ("50.000 Nm³/h", "100.000 Nm³/h")
P_RUECKGABE = eb.p_S1                      # 91 bar: Rückgabe ins Netz, dichte Übergabe (OGE 16.09.2026)
P_GAS = eb.p_S2                            # 30 bar: gasförmige Übergabe / Drosselung
T_KOPF_MIN_EPE = 5.0                       # °C, minimal zulässige Gastemperatur am Kavernenkopf Epe (Q-035 Folie 36)
SPEICHERBEDARF_Q002 = (0.21, 1.21)         # Mt, Zwischenspeicherbedarf Szenarien 1-8 (Q-002 S. 94-95)

# Einspeiseszenarien: beide pumpen von 91 bar auf den Kopfdruck, nur der Pumpeneintritt unterscheidet sich
SZENARIEN = {
    "S1": dict(name="S1 dicht: Pumpe ab 91 bar / 15 °C", p_ein=eb.p_S1, T_ein=eb.T_S1),
    "S2": dict(name="S2 gasförmig: 2 Stufen, Kühler 91 bar / 26 °C, Pumpe", p_ein=eb.P_UEK, T_ein=eb.T_K),
}


def T_gebirge(z):
    """Ungestörte Gebirgstemperatur [°C] in der Teufe z [m] (Q-028)."""
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


TIEF = Kaverne("Referenzkaverne (LCCS 1200 m)", "tief", 1200.0, 1200.0 + DZ_BEZUG, 210.0, 70.0)
KAVERNEN = (TIEF,)


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

    @property
    def p_grenze(self):
        """Höchster Druck mit Phasenwechsel: p_krit (rein) bzw. Cricondenbar (Gemisch)."""
        return self.p_cb

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

    def s(self, p, T):
        if self.ist_gemisch:
            return self._pt(p, T).smass() / 1000
        return self.stoff.s(p, T)

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
            if not T0 - 30.0 < T < T0 + 30.0:       # im Zweiphasengebiet ist h(T) flach - Ausreißer
                raise RuntimeError
        except (RuntimeError, ValueError):
            lo, hi = T0 - 3.0, T0 + 3.0
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
        # die Gemisch-Bilanz endet dort (stopp_bei_zweiphasig)
        q = np.nan if self.in_huelle(p, T) else None
        return dict(p=p, T=T, h=AS.hmass() / 1000, q=q)

    def zustand_ps(self, p, s, T0):
        """T, ρ und q bei p [bar], s [kJ/(kg K)] - für die isentrope Entspannung (02)."""
        if not self.ist_gemisch:
            AS = self._AS
            AS.update(CP.PSmass_INPUTS, p * 1e5, s * 1000)
            q = AS.Q() if AS.phase() == CP.iphase_twophase else None
            return dict(T=AS.T() - 273.15, rho=AS.rhomass(), q=q)
        T = _sekante(lambda x: self.s(p, x) - s, T0, T0 - 0.5, tol=1e-7)
        q = np.nan if self.in_huelle(p, T) else None
        return dict(T=T, rho=self.rho(p, T), q=q)

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


def medium(kurz):
    """'rein' -> reines CO₂, 'gem' -> Worst-Case-Gemisch."""
    return REIN if kurz == "rein" else gemisch()


def massenstrom(med):
    """Massenstrom [kg/s] bei 50.000 und 100.000 Nm³/h (0 °C, 1,01325 bar)."""
    return eb.massenstrom(med.stoff)


def raten(med):
    """{'50.000 Nm³/h': ṁ, '100.000 Nm³/h': ṁ} in kg/s."""
    return dict(zip(RATEN, massenstrom(med)))


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


# ---- 4) Strömende Säule im Förderstrang (adiabat, beide Richtungen) -----------
def strang(med, kav, p_lccs, h_lccs, m_dot, richtung, n=300, f=F_DARCY, T0=None):
    """Förderstrang von der LCCS bis zum Kopf, Schritt für Schritt nach oben gerechnet.

        Impuls:   dp = -(ρ·g ± f/D · ρ·v²/2)·dz      Schwere ± Reibung (Darcy-Weisbach)
                  "aus": Strömung nach oben, Reibung zehrt zusätzlich am Druck (+)
                  "ein": Strömung nach unten, Reibung wirkt gegen die Strömung (-):
                         der Kopf braucht um den Reibungsverlust MEHR Druck
        Energie:  h + g·z = konst. (adiabat, Grenzfall schnelle Förderung). Die
                  Reibungswärme bleibt im Fluid - ihr Temperatureinfluss steckt über
                  den niedrigeren Druck (Joule-Thomson) schon in T(p, h).
    Q-028 Kap. 3 / S. 11: genauer nur mit einem Bohrlochmodell mit Mehrphasenströmung;
    hier homogen, ein zweiphasiger Abschnitt wird nur angezeigt.

    Rückgabe: Profil (z, p, T, ρ, v, q) von oben nach unten und Kopfzustand (dict),
    Kopf = None, wenn der Druck unterwegs auf 1 bar fällt (Säule trägt nicht).
    """
    vz = {"aus": 1.0, "ein": -1.0}[richtung]
    dz = kav.z_lccs / n
    p, h = p_lccs, h_lccs
    T = kav.T_lccs if T0 is None else T0
    profil = []
    for i in range(n + 1):
        z = kav.z_lccs - i * dz
        zs = med.zustand_ph(p, h, T)
        T, rho = zs["T"], zs["rho"]
        v = m_dot / (rho * A_STRANG)
        profil.append((z, p, T, rho, v, zs["q"]))
        if i == n:
            break
        p -= (rho * G + vz * f / D_STRANG * rho * v * v / 2.0) * dz / 1e5
        h -= G * dz / 1000.0
        if p <= 1.0:
            return np.array(profil[::-1], dtype=object), None
    z, p, T, rho, v, q = profil[-1]
    kopf = dict(p=p, T=T, h=h, rho=rho, v=v, q=q,
                zweiphasig_im_strang=any(r[5] is not None for r in profil),
                v_max=max(r[4] for r in profil))
    return np.array(profil[::-1], dtype=object), kopf


def strang_aufwaerts(med, kav, p_lccs, T_unten, m_dot, n=300, h_unten=None, f=F_DARCY):
    """Ausspeichern: Förderstrang von der LCCS zum Kopf (adiabat).

    h_unten: Enthalpie am Strangeintritt, wenn die Kaverne zweiphasig ist (dann
    strömt Dampf vom Kavernendach in den Strang); sonst h(p_lccs, T_unten).
    """
    h = med.h(p_lccs, T_unten) if h_unten is None else h_unten
    return strang(med, kav, p_lccs, h, m_dot, "aus", n=n, f=f, T0=T_unten)


def kopf_einspeisen(med, kav, p_lccs, h_kopf, m_dot, n=300, f=F_DARCY):
    """Einspeisen: welcher Kopfdruck ergibt p_lccs an der LCCS bei Kopf-Enthalpie h_kopf?

    Adiabat ist h an der LCCS = h_Kopf + g·z_LCCS (unabhängig von der Reibung). Damit
    ist der Zustand an der LCCS bekannt und die Säule wird von dort nach oben gerechnet.
    """
    h_lccs = h_kopf + G * kav.z_lccs / 1000.0
    T0 = med.zustand_ph(p_lccs, h_lccs, kav.T_lccs)["T"]
    prof, kopf = strang(med, kav, p_lccs, h_lccs, m_dot, "ein", n=n, f=f, T0=T0)
    if kopf is not None:
        kopf.update(h_lccs=h_lccs, T_lccs=T0)
    return prof, kopf


def zieldruck_einspeisen(med, kav, szen, m_dot, p_lccs=None, n=300, f=F_DARCY, T_ein=None):
    """Zieldruck der Pumpe im Betrieb: Kopfdruck, der beim Einspeisen p_lccs (Standard p_max) ergibt.

    Die Kopftemperatur hängt am Pumpenaustritt und der wiederum am Kopfdruck -> Iteration
    (konvergiert in 2-3 Schritten). Start: Kopfdruck der ruhenden Säule (Stillstand).
    szen: 'S1' oder 'S2' (SZENARIEN). Pumpe: einspeicherung_bausteine.stufe (η = 0,80).
    T_ein: abweichende Pumpeneintrittstemperatur (nur für Sensitivitäten).
    """
    sz = dict(SZENARIEN[szen])
    if T_ein is not None:                  # Sensitivität Pumpeneintritt (z. B. Sommer-Kühlwasser)
        sz["T_ein"] = T_ein
    p_lccs = kav.p_max if p_lccs is None else p_lccs
    p_kopf = kopfdruck(med, kav, p_lccs)
    for _ in range(12):
        P = eb.stufe(med.stoff, sz["p_ein"], sz["T_ein"], p_kopf, eb.eta_P)
        prof, k = kopf_einspeisen(med, kav, p_lccs, P["h2"], m_dot, n=n, f=f)
        if abs(k["p"] - p_kopf) < 1e-4:
            p_kopf = k["p"]
            break
        p_kopf = k["p"]
    P = eb.stufe(med.stoff, sz["p_ein"], sz["T_ein"], p_kopf, eb.eta_P)
    return dict(szenario=szen, p_lccs=p_lccs, m_dot=m_dot, p_kopf=p_kopf, T_kopf=P["T2"], h_kopf=P["h2"],
                w_pumpe=P["w"], pumpe=P, h_lccs=k["h_lccs"], T_lccs=k["T_lccs"], v_kopf=k["v"],
                zweiphasig_im_strang=k["zweiphasig_im_strang"], profil=prof)


def einspeisen_geregelt(med, kav, p_lccs, szen, m_dot, h_auslegung, n=200):
    """Einspeisen bei beliebigem Kavernendruck: Kopfdruck und ob die Pumpe läuft.

    Reicht der Lieferdruck (91 bar) nicht, läuft die Pumpe (Kopf-Enthalpie wie im
    Auslegungspunkt h_auslegung). Sonst wird am Kopf isenthalp gedrosselt: dann
    ist die Kopf-Enthalpie die des Lieferzustands (91 bar / 15 bzw. 26 °C).
    """
    sz = SZENARIEN[szen]
    h_liefer = med.h(sz["p_ein"], sz["T_ein"])
    _, k = kopf_einspeisen(med, kav, p_lccs, h_liefer, m_dot, n=n)
    pumpe = k is not None and k["p"] > sz["p_ein"]
    if pumpe:
        _, k = kopf_einspeisen(med, kav, p_lccs, h_auslegung, m_dot, n=n)
    return dict(p_lccs=p_lccs, pumpe=pumpe, kopf=k)


# ---- 5) Kavernenbilanz über einen Speicherzyklus --------------------------------
def kavernenzyklus(med, kav, m_dot, phasen=None, dpdt_max=DPDT_MAX, dt=0.02, h_ein=None,
                   T_ein=T_EIN_Q028, stopp_bei_zweiphasig=False, T_geb=None, p_start=None,
                   t_still=T_STILLSTAND):
    """Massen- und Energiebilanz des Kaverneninhalts (ein Knoten, ideal durchmischt).

        dm/dt = ṁ                                   (+ ein, - aus)
        dU/dt = ṁ·h_strom + UA·(T_Gebirge - T)
        h_strom: aus = h(Kaverne); ein = h_ein an der LCCS (= h_Kopf + g·z, gekoppelt an
                 die Einspeicherung S1/S2); ohne h_ein: h(p, T_ein) - nur für Q-028.

    Start: voll (p_max an der LCCS, oder p_start) und Gebirgstemperatur, also nach
    langem Stillstand (Q-028 Tab. 1). Die Rate wird gekürzt, sobald der Druck an der
    LCCS schneller als dpdt_max [bar/d] fällt oder steigt (Q-028, Q-030). Zustand je
    Schritt aus (ρ, u). Zyklus wie Q-028 Kap. 4: aus - Stillstand - ein - Stillstand;
    t_still = 0 ergibt die kontinuierliche Betriebsweise (Besprechung 15.10.2026).

    Rückgabe: Liste von dicts je Zeitschritt (t [d], Abschnitt, p_lccs, p_mitte, T, m [t],
    m_dot [kg/s, + ein / - aus], begrenzt, q).
    """
    phasen = phasen or [("aus", kav.p_min), ("still", t_still),
                        ("ein", kav.p_max), ("still", t_still)]
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
                      or (art == "still" and t_ab >= ziel - 1e-9) or t > 1500)
            md = {"aus": -m_dot, "ein": m_dot}.get(art, 0.0)
            if fertig:
                md = 0.0
            if md <= 0:
                h_strom = zs["h"]
            else:
                h_strom = h_ein if h_ein is not None else med.h(zs["p"], T_ein)
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
            q_max=max((x["q"] for x in zp if x["q"] is not None and not np.isnan(x["q"])), default=None)))
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


def ratengrenze(med, kav, p_lccs, dpdt, art):
    """ṁ_max = V · (∂ρ/∂p) · (dp/dt)_max [kg/s] (Q-028 Fig. 5); isotherm oder isentrop (1/c²)."""
    T = kav.T_mitte
    pm = p_mitte(med, kav, p_lccs, T)
    drho = med.drho_dp(pm, T) if art == "isotherm" else 1e5 / med.schall(pm, T) ** 2
    return kav.volumen * drho * dpdt / 86400.0


# ---- 6) Drossel und Hilfsfunktionen ---------------------------------------------
def drossel(med, p2, h, T0):
    """Isenthalpe Drosselung auf p2: T und Dampfanteil q (None = einphasig)."""
    zs = med.zustand_ph(p2, h, T0)
    return zs["T"], zs["q"]


def h_dampf(med, p):
    """Enthalpie [kJ/kg] des gesättigten Dampfs bei p (reines CO₂) bzw. auf der Taulinie (Gemisch)."""
    if not med.ist_gemisch:
        return PropsSI("H", "P", p * 1e5, "Q", 1, "CO2") / 1000
    AS = gw.gemisch()
    AS.update(CP.PQ_INPUTS, p * 1e5, 1.0)
    return AS.hmass() / 1000


def _rein_json(x):
    if isinstance(x, dict):
        return {str(k): _rein_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [_rein_json(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if np.isnan(x) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, Kaverne):
        return x.name
    return x


def speichere_json(ordner, name, daten):
    """Ergebnis eines Prozessschritts für die folgenden Skripte und die Excel-Mappe ablegen."""
    with open(Path(ordner) / name, "w", encoding="utf-8") as f:
        json.dump(_rein_json(daten), f, ensure_ascii=False, indent=1)
    print(f"gespeichert: {Path(ordner).name}/{name}")


def lade_json(ordner, name, erzeugt_von):
    datei = Path(ordner) / name
    if not datei.exists():
        raise FileNotFoundError(f"{Path(ordner).name}/{name} fehlt - zuerst {erzeugt_von} ausführen.")
    with open(datei, encoding="utf-8") as f:
        return json.load(f)


def de(x, nd=1):
    """Zahl mit Dezimalkomma (für Abbildungen)."""
    return f"{x:.{nd}f}".replace(".", ",")


def tsd(x):
    """Tausenderpunkt: 201449 -> '201.449'."""
    return f"{x:,.0f}".replace(",", ".")


def ok(bedingung):
    return "✔" if bedingung else "✘"
