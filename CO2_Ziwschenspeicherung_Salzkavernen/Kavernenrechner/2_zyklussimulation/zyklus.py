# -*- coding: utf-8 -*-
"""Vereinfachte Kavernensimulation: Massen- und Energiebilanz über einen Zyklus."""
from CoolProp.CoolProp import PropsSI
import numpy as np, json

V        = 650000.0     # m3
# --- Geologie: identisch zu co2_kaverne.py und teufenoptimierung.py ---
TEUFE    = 1200.0       # m, Teufe der Kaverne
T_OBERFL = 10.0         # degC, Gebirgstemperatur an der Oberflaeche (Annahme der Quelle)
GEO_GRAD = 0.03         # K/m, geothermischer Gradient
T_rock   = T_OBERFL + GEO_GRAD*TEUFE   # = 46 degC, ungestoerte Gebirgstemperatur
UA       = 546e3        # W/K, Waermeuebergang Kaverne<->Gebirge
T_inj    = 30.0         # degC, Einspeichertemperatur an der LCCS
m_dot_nom= 55.0         # kg/s (~100.000 Nm3/h)
dpdt_max = 6.0          # bar/Tag
PC       = PropsSI('pcrit','CO2')/1e5
TC       = PropsSI('Tcrit','CO2')-273.15

def zustand(m,U):
    rho=m/V; u=U/m
    p=PropsSI('P','D',rho,'U',u,'CO2')/1e5
    T=PropsSI('T','D',rho,'U',u,'CO2')-273.15
    try:    q=PropsSI('Q','D',rho,'U',u,'CO2')
    except Exception: q=-1
    return p,T,rho,q

def simuliere(phasen,dt=0.01,m_dot=None):
    """m_dot: Ein-/Ausspeicherrate in kg/s. None -> Nennrate m_dot_nom."""
    if m_dot is None: m_dot = m_dot_nom
    p0,T0=135.0,T_rock
    rho0=PropsSI('D','P',p0*1e5,'T',T0+273.15,'CO2')
    m=rho0*V; U=m*PropsSI('U','P',p0*1e5,'T',T0+273.15,'CO2')
    t=0.0; out=[]
    for art,ziel,dauer in phasen:
        tp=0.0
        while True:
            p,T,rho,q = zustand(m,U)
            out.append(dict(t=t,p=p,T=T,m=m/1e6,q=q,art=art))
            if art=="stillstand":
                if tp>=dauer: break
                md=0.0
            elif art=="aus":
                if p<=ziel: break
                md=-m_dot
            else:
                if p>=ziel: break
                md=+m_dot
            # Ratenbegrenzung auf dpdt_max
            if md!=0.0:
                dts=dt*86400
                h=(PropsSI('H','P',p*1e5,'T',T_inj+273.15,'CO2') if md>0 else U/m+p*1e5/rho)
                m2=m+md*dts; U2=U+md*h*dts+UA*(T_rock-T)*dts
                p2,_,_,_=zustand(m2,U2)
                if abs(p2-p)/dt>dpdt_max:
                    md*= dpdt_max/(abs(p2-p)/dt)
            dts=dt*86400
            h=(PropsSI('H','P',p*1e5,'T',T_inj+273.15,'CO2') if md>0 else U/m+p*1e5/rho)
            m+=md*dts; U+=md*h*dts+UA*(T_rock-T)*dts
            t+=dt; tp+=dt
            if t>400: break
    return out

phasen=[("aus",70.0,None),("stillstand",None,21.67),
        ("ein",200.0,None),("stillstand",None,21.67),
        ("aus",70.0,None),("stillstand",None,20.0)]

def _zustandstext(y):
    if 0<=y["q"]<=1: return "ZWEIPHASIG q=%.2f"%y["q"]
    return "überkritisch" if y["p"]>=PC and y["T"]>=TC else "einphasig"

def report(r):
    L=[]; A=L.append
    A(f"Simuliert: {len(r)} Schritte, {r[-1]['t']:.0f} Tage")
    A(f"Teufe {TEUFE:.0f} m | Gebirge {T_OBERFL:.0f} °C + {GEO_GRAD*100:.0f} °C/100 m -> T_Gebirge {T_rock:.0f} °C")
    A(f"Rate {m_dot_nom:.0f} kg/s | UA {UA/1e3:.0f} kW/K | max. {dpdt_max:.0f} bar/Tag")
    A("")
    A(f"{'Phase':<12}{'Ende t':>8}{'p':>9}{'T':>8}{'Inventar':>11}  Zustand")
    A("-"*62)
    letzte=None
    for i,x in enumerate(r):
        if letzte and x["art"]!=letzte:
            y=r[i-1]
            A(f"{letzte:<12}{y['t']:7.1f}d{y['p']:8.1f}b{y['T']:7.1f}°C{y['m']:10.1f}kt  {_zustandstext(y)}")
        letzte=x["art"]
    y=r[-1]
    A(f"{letzte:<12}{y['t']:7.1f}d{y['p']:8.1f}b{y['T']:7.1f}°C{y['m']:10.1f}kt  {_zustandstext(y)}")
    mm=[x["m"] for x in r]
    A("")
    A(f"Inventar min/max: {min(mm):.1f} / {max(mm):.1f} kt -> Arbeitsgas {max(mm)-min(mm):.1f} kt = {(max(mm)-min(mm))/max(mm)*100:.0f} %")
    A(f"Kissengas {min(mm)/max(mm)*100:.0f} %  (Vollsimulation der Quelle: 68-78 % Kissengas)")
    return "\n".join(L)

if __name__ == "__main__":
    r = simuliere(phasen)
    txt = report(r)
    print(txt)
    open("report_zyklus.txt","w",encoding="utf-8").write(txt+"\n")
    json.dump(r,open('zyklus.json','w'))
