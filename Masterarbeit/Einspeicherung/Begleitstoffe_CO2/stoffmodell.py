# -*- coding: utf-8 -*-
"""
Stoffmodelle für die Einspeicherung: reines CO2 und Worst-Case-Gemisch
============================================================================
Gemeinsame Schnittstelle für beide Stoffe, damit jede Rechnung (Gassäule,
Pumpe, Verdichter) für reines CO2 und für das Gemisch mit genau denselben
Funktionen läuft. Genutzt von 03_einspeicherpfad_gemisch.py und
04_excel_rechenuebersicht_gemisch.py.

Einheiten an der Schnittstelle: bar, °C, kJ/kg, kJ/(kg K), kg/m3
  ReinCO2   CoolProp PropsSI (Span & Wagner 1996) - wie in den Clean-Case-Skripten
  Gemisch   CoolProp AbstractState (HEOS, GERG-2008-Mischungsregel), siehe
            gemisch_worstcase.py
"""
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI, PhaseSI

import gemisch_worstcase as gw

VERSION = CP.get_global_param_string("version")
print(f"CoolProp-Version: {VERSION}")
if int(VERSION.split(".")[0]) < 8:
    # Geprüft mit 6.6.0: Phasengrenze und alle einphasigen Werte identisch zu
    # 8.0.0, aber der Dampfanteil im Zweiphasengebiet weicht ab (80 bar / 25 °C:
    # Q = 0,04 statt 0,11; GERG-2008 in thermopack: 0,13). Ältere Versionen
    # nutzen einen anderen Flash-Algorithmus. Betrifft nur Variante S2-A.
    print("  Hinweis: CoolProp < 8 - Werte im Zweiphasengebiet (S2-A) ungenau. "
          "Empfohlen: pip install CoolProp==8.0.0")


# Einheiten an der Schnittstelle: bar, °C, kJ/kg, kJ/(kg K), kg/m3


class ReinCO2:
    name = "reines CO₂"
    T_KRIT_C = PropsSI("Tcrit", "CO2") - 273.15

    def rho(self, p_bar, T_C):
        """Dichte wie in der Gassäule des Clean Case (nahe Siedelinie: Gasast)."""
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
        T = PropsSI("T", "P", p_bar * 1e5, "H", h * 1000, "CO2") - 273.15
        return T, PhaseSI("P", p_bar * 1e5, "H", h * 1000, "CO2")

    def phase(self, p_bar, T_C):
        return PhaseSI("P", p_bar * 1e5, "T", T_C + 273.15, "CO2")

    def rho_norm(self):
        return PropsSI("D", "P", 101325, "T", 273.15, "CO2")


class Gemisch:
    name = "Worst-Case-Gemisch"

    def __init__(self):
        self.AS = gw.gemisch()
        # Für die Gassäule (nur dichte Phase oberhalb der Cricondenbar):
        # Phase vorgeben spart die Stabilitätsanalyse -> etwa 10x schneller,
        # Dichte identisch (geprüft gegen freien PT-Flash).
        self.AS_dicht = gw.gemisch()
        self.AS_dicht.specify_phase(CP.iphase_liquid)
        self.p_sicher = gw.phasengrenze()["cricondenbar"][1] + 3.0   # bar

    def _pt(self, p_bar, T_C):
        # PT-Flash mit Kontrolle der Dichtelösung (siehe gw.pt_zustand)
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

    # Isentroper Endzustand und Temperatur aus Enthalpie:
    # Der PS- bzw. PH-Flash von CoolProp funktioniert für Gemische erst ab
    # neueren Versionen ohne weiteres (ältere Versionen verlangen eine vorher
    # gebaute Phasenhüllkurve: "phase envelope must be built to carry out
    # HSU_P_flash for mixture"). Deshalb wird hier die Temperatur selbst
    # gesucht: bei festem p steigen s(T) und h(T) streng mit T, also wird
    # s(p, T) = s_ziel bzw. h(p, T) = h_ziel mit dem PT-Flash nach T gelöst.
    # Das funktioniert in jeder CoolProp-Version, auch im Zweiphasengebiet.

    def _T_suchen(self, p_bar, groesse, ziel, T_min=-50.0, T_max=250.0, tol=1e-5):
        """Löst groesse(p, T) = ziel nach T [°C] (Regula falsi, Illinois-Variante)."""
        a, b = T_min, T_max
        fa, fb = groesse(p_bar, a) - ziel, groesse(p_bar, b) - ziel
        if fa * fb > 0:
            raise ValueError(f"Zielwert bei {p_bar:.1f} bar nicht zwischen {T_min} und {T_max} °C")
        seite = 0
        for _ in range(100):
            c = b - fb * (b - a) / (fb - fa)
            fc = groesse(p_bar, c) - ziel
            if abs(fc) < tol or abs(b - a) < 1e-7:
                return c
            if fc * fb > 0:
                b, fb = c, fc
                if seite == -1:
                    fa /= 2
                seite = -1
            else:
                a, fa = c, fc
                if seite == 1:
                    fb /= 2
                seite = 1
        raise RuntimeError(f"T-Suche bei {p_bar:.1f} bar nicht konvergiert")

    def h_ps(self, p_bar, s):
        T = self._T_suchen(p_bar, self.s, s, tol=1e-7)     # s in kJ/(kg K)
        return self.h(p_bar, T)

    def T_ph(self, p_bar, h):
        T = self._T_suchen(p_bar, self.h, h, tol=1e-5)     # h in kJ/kg
        self._pt(p_bar, T)
        return T, self._phasenname()

    def phase(self, p_bar, T_C):
        self._pt(p_bar, T_C)
        return self._phasenname()

    def _phasenname(self):
        if self.AS.phase() == CP.iphase_twophase:
            return f"ZWEIPHASIG (Q = {self.AS.Q():.2f})"
        return gw._phasenname(self.AS.phase())

    def rho_norm(self):
        return self._pt(1.01325, 0.0).rhomass()
