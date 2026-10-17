# -*- coding: utf-8 -*-
"""
Gemeinsame Bausteine der Einspeicherrechnung - reines CO₂ und Worst-Case-Gemisch
============================================================================
Hier stehen die Annahmen und Rechenbausteine an EINER Stelle, damit
Prozesskette/03_S1_pumpe_gemisch.py, 03_S2_verdichtung_kuehlung_pumpe_gemisch.py
und 04_phasenpfade_vergleich.py mit genau
denselben Werten rechnen wie die Excel-Mappe
"CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx" (Blatt Übersicht).

Annahmen (Stand 15.10.2026, Fundstellen = Quellen- und Wissensmatrix):
  Kaverne V1         1200 m, 210 bar (voll) / 70 bar (leer) an der LCCS,
                     Gebirge 10 °C + 0,03 K/m (Q-028 Kap. 3)
  S1 dicht           91 bar / 15 °C (OGE-Austausch 16.09.2026, Pkt. 6)
  S2 gasförmig       30 bar / 15 °C (Vorarbeit - Quelle noch offen)
  S2-Pfad            überkritisch kühlen (Pfad B, Begründung: 04_phasenpfade_vergleich.py,
                     Handbuch_Einspeicherung.docx Kap. 8.6) - für reines CO₂ UND Gemisch:
                     2 Verdichterstufen 30 -> 55 -> 91 bar, Kühler bei 91 bar, Pumpe

  Kühlung - zwei Kühler mit verschiedenem Zweck (Besprechung K. Vosbeck 15.10.2026):
  Zwischenkühler     CO₂ auf T_ZK = 40 °C. Zweck: Verdichterarbeit senken und Stufe 2
  (50-55 bar)        unter 95 °C halten. Q-017 S. 37 (Tab. Rahmenbedingungen):
                     "Soll-Kühltemperatur CO₂ 40 °C"; Q-063 Kap. 5.1 (PDF-S. 22): CO₂
                     "no more than about 40 °C", Kühlung zwischen und nach den Stufen.
                     Zu tief kühlen schadet: Q-017 S. 19 (Volumen sinkt so stark, dass
                     Wirkungsgradverluste entstehen), Z sinkt (Q-017 S. 44).
                     Die 20 °C aus Q-016 S. 4 werden NICHT übernommen: dort dient die
                     Kühlung der Wasserabscheidung vor der TEG-Trocknung (nasses CO₂ aus
                     der Abscheidung) - das CO₂ aus dem Netz ist bereits trocken.
  Kühler vor Pumpe   CO₂ auf T_K = 26 °C = Kühlwasser 20 °C + 6 K. Zweck: Pumpe braucht
  (91 bar)           dichtes, einphasiges CO₂ weit weg von der pseudokritischen Linie
                     (rein ~40 °C, Gemisch ~33 °C bei 91 bar).
                     Q-120 Folie 24: CO₂ "seldom lower than 6 deg C warmer than the air or
                     water"; Q-120 Folie 32: für Pumpen "cool to 80 to 90 °F (27 to 32 °C)",
                     über 38 °C deutlich mehr Förderhöhe nötig; Q-121 S. 2: Mindestdichte
                     400-500 kg/m³, S. 3: Wirkungsgrad sinkt mit steigender Saugtemperatur;
                     Q-063 Kap. 6 (PDF-S. 33): dichte Phase über 40 °C möglicherweise instabil.
  Zwischendruck      P_ZW = 55 bar (eigene Herleitung, 05_kuehlung_begruendung.py): höchster
                     runder Druck, bei dem am Eintritt Stufe 2 (40 °C) Z ≥ 0,7 (Q-017 S. 44)
                     für beide Gasqualitäten gilt; beide Stufen bleiben dann mit Abstand
                     unter 95 °C (Q-016 S. 4). Mit 50 bar läge Stufe 2 bei 93-94 °C.
  Grenzen            höchstens 95 °C je Verdichterstufe (Q-016 S. 4, dort [24]); Realgasfaktor
                     am Eintritt jeder Verdichterstufe Z > 0,65 (Siemens Energy Duisburg,
                     E-Mail-Auskunft 08/2026: "Damit die Berechnung der Laufräder in
                     unseren Berechnungsprogrammen zuverlässig ausgeführt wird, bleiben
                     wir bei einem Z-Wert von > 0,65"; strengerer Literaturrichtwert
                     Z ≥ 0,7 nach Q-017 S. 44 wird zum Vergleich mit ausgegeben);
                     gilt nur für Verdichter, nicht für die Pumpe. Dichte am
                     Pumpeneintritt ≥ 500 kg/m³ (Q-121 S. 2, Q-001 Kap. 5.2)
  Wirkungsgrade      Verdichter 0,84 / 0,82 (Q-016 S. 4: 84 % in Stufe 1, je weitere Stufe
                     −2 %), Pumpe 0,80 (eigene Annahme - Lücke, Herstellerangabe einholen)
  Durchsatz          50.000-100.000 Nm³/h (0 °C, 1,01325 bar; abgestimmt mit M. Wall)
  Unsicherheit       Phasengrenze ±3 bar (Dokumentation Stoffmodelle, Kap. 9)
  Zieldruck          nicht mehr die ruhende Gassäule, sondern die strömende Säule beim
                     Einspeisen mit der Temperatur nach der Pumpe:
                     Kaverne/Grundlagen/kaverne_bausteine.zieldruck_einspeisen()
Nur für den Pfadvergleich (04): Verflüssigungsdruck Pfad A p_V = 60 bar (rein)
bzw. 80 bar (Gemisch) bei 20 °C (Zwischenkühler ebenfalls 20 °C, da A ohnehin kaltes
Kühlmittel braucht), Durchverdichten (Pfad C) mit Zwischendruck 52 bar und
Zwischenkühlung auf T_K = 26 °C (mit 40 °C läge Stufe 2 über 95 °C).

Einheiten an der Schnittstelle der Stoffklassen: bar, °C, kJ/kg, kJ/(kg K), kg/m³.
"""
import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI, PhaseSI

import gemisch_worstcase as gw

# ---- 1) Annahmen (identisch Excel, Blatt Übersicht) -------------------------
TEUFE = 1200.0              # m, Kaverne V1
P_MAX_LCCS = 210.0          # bar, Kavernenboden voll
P_MIN_LCCS = 70.0           # bar, Kavernenboden leer
T_OBERFLAECHE = 10.0        # °C
GRADIENT = 0.03             # K/m
G = 9.81                    # m/s²

p_S1, T_S1 = 91.0, 15.0     # dichte Anlieferung
p_S2, T_S2 = 30.0, 15.0     # gasförmige Anlieferung
T_KW = 20.0                 # °C, Kühlwasser (Auslegung)
DT_KUEHLER = 6.0            # K, CO₂ selten kälter als Kühlmittel + 6 K (Q-120, Folie 24)
T_K = T_KW + DT_KUEHLER     # °C, CO₂ nach dem Kühler vor der Pumpe (91 bar) = 26 °C (Q-120 Folie 24/32)
T_ZK = 40.0                 # °C, CO₂ nach dem Zwischenkühler (Q-017 S. 37; Q-063 Kap. 5.1)
T_MAX_STUFE = 95.0          # °C, höchstens je Verdichterstufe (Q-016 S. 4)
Z_MIN = 0.65                # Realgasfaktor am Verdichterstufeneintritt mindestens (Siemens Energy Duisburg, E-Mail-Auskunft 08/2026)
Z_Q017 = 0.7                # strengerer Literaturrichtwert (Q-017 S. 44: "Als Grenzwert des Z-Faktors wird durch
                            # verschiedenste Hersteller 0,7 angegeben"), nur zum Vergleich
RHO_MIN = 500.0             # kg/m³, Pumpeneintritt mindestens (Q-121 S. 2, Q-001 Kap. 5.2)
P_ZW = 55.0                 # bar, Zwischendruck S2: Z ≥ 0,7 am Eintritt Stufe 2 (40 °C), beide Stufen < 95 °C
                            # (Herleitung: Prozesskette/05_kuehlung_begruendung.py)
P_UEK = 91.0                # bar, Druck nach Verdichtung = Kühldruck = Pumpeneintritt S2
                            # (Cricondenbar 82,2 bar + 8,8 bar; = Übergabedruck S1)
P_ZW_DV = 52.0              # bar, Zwischendruck Pfad C Durchverdichten (nur Vergleich)
eta_V1, eta_V2, eta_P = 0.84, 0.82, 0.80   # Q-016 S. 4 / Q-016 S. 4 / eigene Annahme
V_NORM_MIN, V_NORM_MAX = 50000.0, 100000.0   # Nm³/h
U_PG = 3.0                  # bar, Unsicherheit der Phasengrenze


def T_gebirge(z):
    return T_OBERFLAECHE + GRADIENT * z


# ---- 2) Stoffe: gleiche Schnittstelle für reines CO2 und Gemisch ------------
class ReinCO2:
    name = "reines CO₂"
    kurz = "rein"
    p_V = 60.0                                   # Verflüssigungsdruck (Excel)
    T_KRIT_C = PropsSI("Tcrit", "CO2") - 273.15
    P_GRENZE = PropsSI("Pcrit", "CO2") / 1e5     # darüber keine Phasengrenze mehr

    def rho(self, p_bar, T_C):
        """Dichte wie in der Gassäule (nahe der Siedelinie: Gasast)."""
        T, p = T_C + 273.15, p_bar * 1e5
        if T_C >= self.T_KRIT_C:
            return PropsSI("D", "P", p, "T", T, "CO2")
        psat = PropsSI("P", "T", T, "Q", 0, "CO2")
        if abs(p - psat) / psat < 5e-4:
            return PropsSI("D", "T", T, "Q", 1, "CO2")
        return PropsSI("D", "P", p, "T", T, "CO2")

    def h(self, p_bar, T_C):
        return PropsSI("H", "P", p_bar * 1e5, "T", T_C + 273.15, "CO2") / 1000

    def s(self, p_bar, T_C):
        return PropsSI("S", "P", p_bar * 1e5, "T", T_C + 273.15, "CO2") / 1000

    def h_ps(self, p_bar, s):
        return PropsSI("H", "P", p_bar * 1e5, "S", s * 1000, "CO2") / 1000

    def T_ph(self, p_bar, h):
        return PropsSI("T", "P", p_bar * 1e5, "H", h * 1000, "CO2") - 273.15

    def Z(self, p_bar, T_C):
        return PropsSI("Z", "P", p_bar * 1e5, "T", T_C + 273.15, "CO2")

    def phase(self, p_bar, T_C):
        return PhaseSI("P", p_bar * 1e5, "T", T_C + 273.15, "CO2")

    def blasendruck(self, T_C):
        if T_C >= self.T_KRIT_C:
            return np.nan
        return PropsSI("P", "T", T_C + 273.15, "Q", 0, "CO2") / 1e5

    def taudruck(self, T_C):
        return self.blasendruck(T_C)

    def blasentemperatur(self, p_bar):
        if p_bar >= self.P_GRENZE:
            return np.nan
        return PropsSI("T", "P", p_bar * 1e5, "Q", 0, "CO2") - 273.15

    def tautemperatur(self, p_bar):
        return self.blasentemperatur(p_bar)

    def gasanteil(self, p_bar, T_C):
        """Reines CO2 ist bei gegebenem p und T nie zweiphasig (nur auf der Linie)."""
        return 1.0 if "gas" in self.phase(p_bar, T_C) else 0.0   # auch "supercritical_gas"

    def rho_norm(self):
        return PropsSI("D", "P", 101325, "T", 273.15, "CO2")


class Gemisch:
    name = "Worst-Case-Gemisch"
    kurz = "gem"
    p_V = 80.0                                   # Verflüssigungsdruck (Excel)

    def __init__(self):
        self.AS = gw.gemisch()
        self.pg = gw.phasengrenze()
        self.P_GRENZE = self.pg["cricondenbar"][1]
        # Gassäule: nur dichte Phase oberhalb der Cricondenbar - Phase vorgeben
        # spart die Stabilitätsanalyse (etwa 10x schneller, Dichte identisch)
        self.AS_dicht = gw.gemisch()
        self.AS_dicht.specify_phase(CP.iphase_liquid)
        self.p_sicher = self.P_GRENZE + U_PG

    def _pt(self, p_bar, T_C):
        return gw.pt_zustand(p_bar, T_C, self.AS)

    def rho(self, p_bar, T_C):
        if p_bar > self.p_sicher:
            self.AS_dicht.update(CP.PT_INPUTS, p_bar * 1e5, T_C + 273.15)
            return self.AS_dicht.rhomass()
        return self._pt(p_bar, T_C).rhomass()

    def h(self, p_bar, T_C):
        return self._pt(p_bar, T_C).hmass() / 1000

    def s(self, p_bar, T_C):
        return self._pt(p_bar, T_C).smass() / 1000

    def h_ps(self, p_bar, s):
        self.AS.update(CP.PSmass_INPUTS, p_bar * 1e5, s * 1000)
        h, T = self.AS.hmass() / 1000, self.AS.T() - 273.15
        # Kontrolle: Rückrechnung mit PT-Flash muss dieselbe Entropie liefern
        if abs(self.s(p_bar, T) - s) > 1e-4:
            raise RuntimeError(f"PS-Flash nicht konsistent bei {p_bar:.1f} bar")
        return h

    def T_ph(self, p_bar, h):
        self.AS.update(CP.HmassP_INPUTS, h * 1000, p_bar * 1e5)
        T = self.AS.T() - 273.15
        if abs(self.h(p_bar, T) - h) > 0.01:
            raise RuntimeError(f"PH-Flash nicht konsistent bei {p_bar:.1f} bar")
        return T

    def Z(self, p_bar, T_C):
        return self._pt(p_bar, T_C).compressibility_factor()

    def phase(self, p_bar, T_C):
        s = self._pt(p_bar, T_C)
        if s.phase() == CP.iphase_twophase:
            return f"zweiphasig (Q = {s.Q():.2f})"
        return gw._phasenname(s.phase())

    def blasendruck(self, T_C):
        return gw.blasendruck(T_C)

    def taudruck(self, T_C):
        return gw.taudruck(T_C)

    def blasentemperatur(self, p_bar):
        """Temperatur, ab der bei p die erste Gasblase entsteht (nan über der Cricondenbar)."""
        if p_bar >= self.P_GRENZE:
            return np.nan
        T, p = self.pg["T_blase"][::-1], self.pg["p_blase"][::-1]
        i_krit = int(np.argmax(T))                  # nur der Ast unterhalb des krit. Punkts
        return float(np.interp(p_bar, p[: i_krit + 1], T[: i_krit + 1]))

    def tautemperatur(self, p_bar):
        """Temperatur, ab der bei p der erste Tropfen ausfällt (Ast bis zur Cricondentherm)."""
        if p_bar >= self.P_GRENZE:
            return np.nan
        i = int(np.argmax(self.pg["T_tau"]))
        return float(np.interp(p_bar, self.pg["p_tau"][: i + 1], self.pg["T_tau"][: i + 1]))

    def gasanteil(self, p_bar, T_C):
        """Volumenanteil der Gasphase [-] (0 = ganz flüssig/dicht, 1 = ganz gasförmig)."""
        s = self._pt(p_bar, T_C)
        if s.phase() != CP.iphase_twophase:
            return 1.0 if s.phase() == CP.iphase_gas else 0.0
        Q = s.Q()
        rv = s.saturated_vapor_keyed_output(CP.iDmolar)
        rl = s.saturated_liquid_keyed_output(CP.iDmolar)
        return (Q / rv) / (Q / rv + (1 - Q) / rl)

    def dampfzusammensetzung(self, p_bar, T_C):
        """Molanteile der Gasphase im Zweiphasengebiet (None, wenn einphasig)."""
        s = self._pt(p_bar, T_C)
        if s.phase() != CP.iphase_twophase:
            return None
        return list(s.mole_fractions_vapor())

    def rho_norm(self):
        return self._pt(1.01325, 0.0).rhomass()


# ---- 3) Rechenbausteine -----------------------------------------------------
def gassaeule(stoff, p_lccs_bar=P_MAX_LCCS, n=600):
    """dp/dz = rho(p,T)*g von unten (Kavernenboden) nach oben (Kopf), wie Excel.

    Gibt Kopfdruck und das Profil (z, p, T, rho) von oben nach unten zurück.
    """
    dz = TEUFE / n
    p = p_lccs_bar
    profil = []
    for i in range(n):
        z = TEUFE - i * dz
        rho = stoff.rho(p, T_gebirge(z))
        profil.append((z, p, T_gebirge(z), rho))
        p -= rho * G * dz / 1e5
    profil.append((0.0, p, T_gebirge(0.0), stoff.rho(p, T_gebirge(0.0))))
    return p, np.array(profil[::-1])


def kopfdruck(stoff, p_lccs_bar=P_MAX_LCCS, n=600):
    return gassaeule(stoff, p_lccs_bar, n)[0]


def stufe(stoff, p1, T1, p2, eta):
    """Verdichter- oder Pumpenstufe: isentrop + Wirkungsgrad (wie Excel)."""
    h1, s1 = stoff.h(p1, T1), stoff.s(p1, T1)
    h2s = stoff.h_ps(p2, s1)
    h2 = h1 + (h2s - h1) / eta
    return dict(p1=p1, T1=T1, p2=p2, h1=h1, h2s=h2s, h2=h2, T2=stoff.T_ph(p2, h2),
                w=h2 - h1, Z1=stoff.Z(p1, T1), rho1=stoff.rho(p1, T1))


def kuehler(stoff, p, h_vor, T_nach):
    """Kühler/Verflüssiger bei konstantem Druck: abgeführte Wärme q = h_vor - h_nach."""
    h_nach = stoff.h(p, T_nach)
    return dict(p=p, T=T_nach, h=h_nach, q=h_vor - h_nach, phase=stoff.phase(p, T_nach))


def pumpeneintritt(stoff, p, T):
    """Was die Pumpe am Eintritt sieht: Dichte, Gasanteil, Abstand zur Phasengrenze."""
    p_bl = stoff.blasendruck(T)
    T_bl = stoff.blasentemperatur(p)
    return dict(p=p, T=T, rho=stoff.rho(p, T), gas=stoff.gasanteil(p, T),
                abstand_bar=(p - p_bl) if not np.isnan(p_bl) else p - stoff.P_GRENZE,
                ueber_grenze=bool(p >= stoff.P_GRENZE),
                T_reserve=(T_bl - T) if not np.isnan(T_bl) else np.nan,
                phase=stoff.phase(p, T))


def zweistufig(stoff, p_end, p_zw=None, T_zk=T_ZK, p_ein=p_S2, T_ein=T_S2):
    """2 Stufen p_ein -> p_zw -> p_end mit Zwischenkühlung auf T_zk (Standard 40 °C).

    Ohne p_zw: gleiches Druckverhältnis in beiden Stufen, p_zw = √(p_ein · p_end).
    """
    p_zw = np.sqrt(p_ein * p_end) if p_zw is None else p_zw
    V1 = stufe(stoff, p_ein, T_ein, p_zw, eta_V1)
    ZK = kuehler(stoff, p_zw, V1["h2"], T_zk)
    V2 = stufe(stoff, p_zw, T_zk, p_end, eta_V2)
    return p_zw, V1, ZK, V2


def massenstrom(stoff):
    """Massenstrom [kg/s] bei V_n,min und V_n,max (Normzustand 0 °C, 1,01325 bar)."""
    rn = stoff.rho_norm()
    return V_NORM_MIN * rn / 3600.0, V_NORM_MAX * rn / 3600.0


def kette_S2(stoff, p_kopf):
    """S2 (Pfad B): 2 Stufen 30 -> P_ZW -> P_UEK mit Zwischenkühlung auf T_ZK (40 °C),
    Kühler bei P_UEK auf T_K (26 °C), Pumpe auf den Kopfdruck p_kopf.

    Gleiche Kette für reines CO₂ und Gemisch (Besprechung 15.10.2026: gleiche Kühllogik,
    damit der Vergleich nur den Stoff zeigt). Rückgabe: alle Zwischenzustände.
    """
    p_zw, V1, ZK, V2 = zweistufig(stoff, P_UEK, p_zw=P_ZW, T_zk=T_ZK)
    K = kuehler(stoff, P_UEK, V2["h2"], T_K)
    P = stufe(stoff, P_UEK, T_K, p_kopf, eta_P)
    return dict(p_zw=p_zw, V1=V1, ZK=ZK, V2=V2, K=K, P=P, ein=pumpeneintritt(stoff, P_UEK, T_K),
                w=V1["w"] + V2["w"] + P["w"], q=ZK["q"] + K["q"],
                pfad=[(T_S2, p_S2), (V1["T2"], p_zw), (T_ZK, p_zw), (V2["T2"], P_UEK),
                      (T_K, P_UEK), (P["T2"], p_kopf)])
