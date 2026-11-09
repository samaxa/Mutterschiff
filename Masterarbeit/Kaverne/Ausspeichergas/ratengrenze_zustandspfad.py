"""Zusatz (Add-on): Ratengrenze entlang des echten Zustandspfads beim Ausspeichern.

Frage: Die bisherige Abbildung abb_K03_ratengrenze rechnet die Grenze bei fester
Gebirgstemperatur (52 °C). Beim Ausspeichern kühlt die Kaverne aber ab. Wo liegt die
Grenze, wenn man bei jedem Zeitschritt das (p, T) nimmt, das die Kaverne wirklich hat,
und wo wird deshalb gekürzt?

Vorgehen
  1. Ausspeichern von der vollen Kaverne (210 bar an der LCCS, Gebirgstemperatur) bis
     70 bar nachrechnen, mit denselben Annahmen wie kavernenzyklus in
     kaverne_bausteine.py: ein durchmischter Knoten, dm/dt = ṁ, dU/dt = ṁ·h + UA·(T_Geb − T),
     explizites Euler-Verfahren mit Δt = 0,02 d, Kürzung des Massenstroms, wenn der
     Druck an der LCCS schneller als 10 bar/d fällt (bis zu viermal).
  2. In jedem Zeitschritt drei Grenzen rechnen:
       isotherm  ṁ = V·(∂ρ/∂p)_T·(dp/dt)_max     (Gebirge heizt voll nach)
       isentrop  ṁ = V/c²·(dp/dt)_max            (keine Wärme)
       mit Wärme ṁ = ((dp/dt)_max + B·Q) / (A − g·Δz/V)
                 mit A = (∂p/∂ρ)_u/V + (∂p/∂u)_ρ·p/(ρ·m) = c²/V,  B = (∂p/∂u)_ρ/m,
                 Q = UA·(T_Geb − T): die Grenze bei dem Wärmestrom, der gerade wirklich fließt.
     Die ersten beiden wie in ratengrenze, aber beim echten (p_Mitte, T) statt bei 52 °C.
  3. Prüfung gegen die eigenen Ergebnisse (Tabelle 12 der Doku, reines CO₂, Stillstand
     21,67 d): 100.000 Nm³/h 81,7 d / 38,1 °C / 7 % gekürzt; 50.000 Nm³/h 165,9 d / 44,0 °C / 0 %.

Nur reines CO₂ und nur der erste Ausspeichervorgang. Eigenständig lauffähig
(numpy, matplotlib, CoolProp), greift nicht in die bestehenden Skripte ein.
Aufruf: python ratengrenze_zustandspfad.py   ->  abb_Z_ratengrenze_zustandspfad.png
"""
import numpy as np
import matplotlib.pyplot as plt
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI

# ---- Annahmen (wie kaverne_bausteine.py, Referenzkaverne) -------------------------
G = 9.81                      # m/s²
V = 650000.0                  # m³ (Q-028 Tab. 1)
Z_LCCS, DZ = 1200.0, 205.0    # m; Bezugsteufe 205 m unter der LCCS (Q-028 Tab. 1)
T_GEB = 10.0 + 0.03 * (Z_LCCS + DZ)   # °C, Gebirgstemperatur in der Kavernenmitte (Q-028)
P_MAX, P_MIN = 210.0, 70.0    # bar an der LCCS
UA = 546e3                    # W/K, an Q-028 kalibriert (Schritt 03)
DPDT = 10.0                   # bar/d (Q-030 Kap. 1.2.1, Q-089 Tab. 2)
DT_D = 0.02                   # d
RHO_N = PropsSI("D", "T", 273.15, "P", 101325, "CO2")   # kg/Nm³ (DIN 1343)
RATEN = {"100.000 Nm³/h": 1e5 * RHO_N / 3600, "50.000 Nm³/h": 5e4 * RHO_N / 3600}
SOLL = {"100.000 Nm³/h": (81.7, 38.1, 7), "50.000 Nm³/h": (165.9, 44.0, 0)}

AS = CP.AbstractState("HEOS", "CO2")
DT_S = DT_D * 86400.0
R_PA = DPDT * 1e5 / 86400.0   # Pa/s


def zustand(m, U):
    """p_Mitte [bar], T [°C], h [J/kg], p_LCCS [bar] aus Masse und innerer Energie."""
    rho, u = m / V, U / m
    AS.update(CP.DmassUmass_INPUTS, rho, u)
    p = AS.p() / 1e5
    return p, AS.T() - 273.15, AS.hmass(), p - rho * G * DZ / 1e5


def grenzen(m, T):
    """Drei Grenzraten [kg/s] im aktuellen Zustand (AS muss auf diesem Zustand stehen)."""
    rho, p = AS.rhomass(), AS.p()
    c = AS.speed_sound()
    dpdrho_u = AS.first_partial_deriv(CP.iP, CP.iDmass, CP.iUmass)
    dpdu_rho = AS.first_partial_deriv(CP.iP, CP.iUmass, CP.iDmass)
    drhodp_T = AS.first_partial_deriv(CP.iDmass, CP.iP, CP.iT)
    A = dpdrho_u / V + dpdu_rho * p / (rho * m)
    B = dpdu_rho / m
    Q = UA * (T_GEB - T)
    return dict(iso=V * drhodp_T * R_PA, isen=V / c**2 * R_PA,
                waerme=(R_PA + B * Q) / (A - G * DZ / V), Q=Q)


def startzustand():
    p = P_MAX
    for _ in range(50):
        rho = PropsSI("D", "P", p * 1e5, "T", T_GEB + 273.15, "CO2")
        p = P_MAX + rho * G * DZ / 1e5
    m = rho * V
    u = PropsSI("U", "P", p * 1e5, "T", T_GEB + 273.15, "CO2")
    return m, m * u


def ausspeichern(m_soll):
    m, U = startzustand()
    t, rows = 0.0, []
    while True:
        p, T, h, pL = zustand(m, U)
        if pL <= P_MIN:
            break
        gr = grenzen(m, T)
        md, begrenzt = m_soll, False
        for _ in range(5):
            m1 = m - md * DT_S
            U1 = U - md * h * DT_S + gr["Q"] * DT_S
            rate = (pL - zustand(m1, U1)[3]) / DT_D
            if rate <= DPDT * 1.0001:
                break
            md *= DPDT / rate
            begrenzt = True
        rows.append((t, pL, p, T, md, begrenzt, gr["iso"], gr["isen"], gr["waerme"]))
        m, U, t = m1, U1, t + DT_D
    a = np.array(rows, dtype=float)
    return dict(t=a[:, 0], pL=a[:, 1], pm=a[:, 2], T=a[:, 3], m=a[:, 4], begr=a[:, 5] > 0.5,
                iso=a[:, 6], isen=a[:, 7], waerme=a[:, 8], dauer=t)


def isentrop_52(pL):
    """Isentrope Grenze bei fester Gebirgstemperatur wie in der bisherigen Abbildung."""
    out = []
    for x in pL:
        p = x
        for _ in range(30):
            p = x + PropsSI("D", "P", p * 1e5, "T", T_GEB + 273.15, "CO2") * G * DZ / 1e5
        out.append(V / PropsSI("A", "P", p * 1e5, "T", T_GEB + 273.15, "CO2") ** 2 * R_PA)
    return np.array(out)


# ---- Rechnung und Prüfung -----------------------------------------------------------
erg = {}
print(f"T_Gebirge = {T_GEB:.2f} °C, Normdichte {RHO_N:.4f} kg/Nm³")
for name, md in RATEN.items():
    e = ausspeichern(md)
    erg[name] = e
    d0, T0, b0 = SOLL[name]
    anteil = 100 * e["begr"].mean()
    print(f"{name} ({md:.1f} kg/s): Dauer {e['dauer']:.1f} d (eigen {d0}), T_min {e['T'].min():.1f} °C (eigen {T0}), "
          f"gekürzt {anteil:.0f} % (eigen {b0} %)")
    if e["begr"].any():
        pb = e["pL"][e["begr"]]
        print(f"   gekürzt zwischen p_LCCS = {pb.max():.0f} und {pb.min():.0f} bar, "
              f"Tag {e['t'][e['begr']].min():.1f} bis {e['t'][e['begr']].max():.1f}")
    unter = e["waerme"] < md
    print(f"   Rate über der Grenze mit Wärme: {100*unter.mean():.0f} % der Schritte")

# ---- Abbildung ------------------------------------------------------------------------
BLAU_D, ROT, GRAU, SCHWARZ = "#00304F", "#CA220E", "#7F7F7F", "#1A1A1A"
fig, axs = plt.subplots(2, 2, figsize=(13, 7.6), sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1]))
for j, (name, e) in enumerate(erg.items()):
    ax, axT = axs[0, j], axs[1, j]
    pL = e["pL"]
    ax.fill_between(pL, e["isen"], e["iso"], color=BLAU_D, alpha=0.12, lw=0,
                    label="Band beim echten (p, T): isentrop bis isotherm")
    ax.plot(pL, e["iso"], color=BLAU_D, lw=1.2)
    ax.plot(pL, e["isen"], color=BLAU_D, lw=1.2, ls="--")
    ax.plot(pL, e["waerme"], color=BLAU_D, lw=2.6, label="Grenze mit dem Wärmestrom, der gerade fließt")
    ps = np.linspace(P_MIN, P_MAX, 25)
    ax.plot(ps, isentrop_52(ps), color=GRAU, lw=1.2, ls=":", label="isentrop bei 52 °C (bisherige Abbildung)")
    ax.axhline(RATEN[name], color=ROT, lw=1.2, label=f"geplant: {name} = {RATEN[name]:.0f} kg/s")
    ax.plot(pL, e["m"], color=SCHWARZ, lw=1.8, label="gefahrene Rate (nach Kürzung)")
    if e["begr"].any():
        ax.axvspan(pL[e["begr"]].min(), pL[e["begr"]].max(), color=ROT, alpha=0.08, lw=0)
        ax.text(pL[e["begr"]].mean(), 185, "hier gekürzt", color=ROT, ha="center", fontsize=9)
    ax.set(ylim=(0, 200), title=f"{name}: Ausspeichern {e['dauer']:.0f} d, gekürzt in {100*e['begr'].mean():.0f} % der Schritte")
    ax.set_ylabel("Rate [kg/s]")
    ax.grid(alpha=0.3)
    if j == 0:
        handles, labels = ax.get_legend_handles_labels()
        labels = [l.replace(f" = {RATEN[name]:.0f} kg/s", "").replace("100.000 Nm³/h", "Durchsatz") for l in labels]
    axT.plot(pL, e["T"], color=BLAU_D, lw=2, label="Kaverne (Mitte)")
    axT.axhline(T_GEB, color=GRAU, lw=1.2, ls="--", label=f"Gebirge {T_GEB:.0f} °C")
    axT.fill_between(pL, e["T"], T_GEB, color=ROT, alpha=0.08, lw=0, label="Temperaturdifferenz = Wärme vom Gebirge")
    axT.set(ylim=(35, 55), xlabel="Druck an der LCCS [bar]   (Ausspeichern läuft von rechts nach links)")
    axT.set_ylabel("T [°C]")
    axT.grid(alpha=0.3)
    axT.legend(fontsize=8, loc="lower right")
    ax.set_xlim(P_MIN, P_MAX)
fig.suptitle("Ratengrenze entlang des Zustandspfads beim Ausspeichern, reines CO₂, 10 bar/d", fontsize=13)
fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9, frameon=False)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig("abb_Z_ratengrenze_zustandspfad.png", dpi=170)
print("gespeichert: abb_Z_ratengrenze_zustandspfad.png")
