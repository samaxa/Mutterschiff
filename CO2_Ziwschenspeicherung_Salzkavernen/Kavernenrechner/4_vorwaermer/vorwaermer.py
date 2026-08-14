#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ausspeicherung CO2/Erdgas-Kaverne: Vorwärmleistung vor der Druckreduzierung.
============================================================================
Methode: Drossel ist isenthalp (h=const) - der gesamte Enthalpiehub kommt vom Vorwärmer.
   Q = m_punkt * [ h(p2, T_ziel) - h(p1, T_ein) ]
Stoffdaten CoolProp (Span-Wagner CO2, GERG/Setzmann CH4).
Normbedingungen DIN 1343 (0 °C, 1,01325 bar).

Hinweis: eigenständige Vergleichsrechnung CO2 gegen Erdgas. Die Eingaben unten
sind bewusst nicht an die 1200-m-Kaverne der anderen Module gekoppelt - dort
läge die Kopftemperatur beim Ausspeichern bei rund 34 °C statt der 50 °C hier.
"""
import CoolProp.CoolProp as CP
bar = 1e5
C2K = lambda t: t+273.15
K2C = lambda t: t-273.15
Tn, pn = 273.15, 101325.0

def rho_norm(fluid): return CP.PropsSI('D', 'T', Tn, 'P', pn, fluid)
def m_punkt(fluid, Vn_h): return rho_norm(fluid)*Vn_h/3600.0   # kg/s

def drossel_austritt(fluid, T1, p1, p2):
    """isenthalpe Drossel: gibt (T2 [°C], Phase, Dampfanteil Q)"""
    h = CP.PropsSI('H', 'T', C2K(T1), 'P', p1*bar, fluid)
    T2 = K2C(CP.PropsSI('T', 'P', p2*bar, 'H', h, fluid))
    try:    q = CP.PropsSI('Q', 'P', p2*bar, 'H', h, fluid)
    except Exception: q = -1
    phase = "zweiphasig/flüssig" if 0 <= q <= 1 else "einphasig (Gas)"
    return T2, phase, q

def vorwaerm_T(fluid, p1, p2, T_ziel):
    """Temperatur vor der Drossel, damit nach Entspannung T_ziel erreicht wird"""
    h_ziel = CP.PropsSI('H', 'P', p2*bar, 'T', C2K(T_ziel), fluid)
    return K2C(CP.PropsSI('T', 'P', p1*bar, 'H', h_ziel, fluid))

def vorwaerm_leistung(fluid, p1, T_ein, p2, T_ziel, Vn_h):
    h_in  = CP.PropsSI('H', 'P', p1*bar, 'T', C2K(T_ein), fluid)
    h_out = CP.PropsSI('H', 'P', p2*bar, 'T', C2K(T_ziel), fluid)
    return m_punkt(fluid, Vn_h)*(h_out-h_in)/1000.0   # kW

def T_saturation(fluid, p2):
    try: return K2C(CP.PropsSI('T', 'P', p2*bar, 'Q', 0, fluid))
    except Exception: return None

# ============ EINGABEN (anpassen) ============
Vn       = 100000.0   # Nm3/h
p1       = 210.0      # bar  (Kaverne/Wellhead)
T_ein    = 50.0       # °C
T_ziel   = 17.5       # °C    (Ziel nach Drossel, Methan-Hydrat + Trocknung)
p2_liste = [50, 40, 30, 16]
# =============================================

def report():
    L = []; A = L.append
    A(f"Eintritt {p1:.0f} bar / {T_ein:.0f} °C   Ziel {T_ziel} °C   {Vn:.0f} Nm3/h")
    A("")
    for f, nm in [('CO2', 'CO2'), ('Methane', 'Erdgas(CH4)')]:
        A(f"{nm}: Normdichte {rho_norm(f):.3f} kg/Nm3  -  "
          f"Massenstrom {m_punkt(f, Vn)*3600:,.0f} kg/h ({m_punkt(f, Vn):.1f} kg/s)")
    A("")
    hdr = (f"{'p2[bar]':>8} {'Tsat(CO2)':>10} {'Gas':<12} {'T2 o.VW':>9} "
           f"{'Phase':<20} {'Vorwärm-T':>10} {'Q[kW]':>9}")
    A(hdr); A("-"*len(hdr))
    for p2 in p2_liste:
        tsat = T_saturation('CO2', p2)
        for f, nm in [('CO2', 'CO2'), ('Methane', 'CH4')]:
            T2, ph, q = drossel_austritt(f, T_ein, p1, p2)
            Tv = vorwaerm_T(f, p1, p2, T_ziel)
            Q  = vorwaerm_leistung(f, p1, T_ein, p2, T_ziel, Vn)
            ts = f"{tsat:6.1f}°C" if (f == 'CO2' and tsat) else ""
            A(f"{p2:>8} {ts:>10} {nm:<12} {T2:>8.1f}°C {ph:<20} {Tv:>9.1f}°C {Q:>9.0f}")
        A("-"*len(hdr))
    return "\n".join(L)

if __name__ == "__main__":
    txt = report()
    print(txt)
    open("report_vorwaermer.txt", "w", encoding="utf-8").write(txt+"\n")
