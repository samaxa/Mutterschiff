# -*- coding: utf-8 -*-
"""
Abbildungen zur Zyklussimulation
================================
Erzeugt abb5 und abb6 aus zyklus.py.

  abb5_zyklus.png          Druck, Temperatur und Inventar ueber einen Zyklus,
                           gefahren mit zwei Ausspeicherraten.
  abb6_inventarmessung.png warum der Kavernendruck unterhalb p_krit kein
                           Fuellstandsmass mehr ist.

Aufruf:  python zyklus_plot.py
"""
from CoolProp.CoolProp import PropsSI
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import zyklus as Z

# Die beiden verglichenen Raten: Nennrate und die Rate, bei der die
# Druckaenderungsgrenze dpdt_max bindend wird.
RATEN = [
    (Z.m_dot_nom, "#185FA5", f"Nennrate ~100 kNm³/h ({Z.m_dot_nom:.0f} kg/s)"),
    (234.0,       "#D85A30", f"Maximalrate {Z.dpdt_max:.0f} bar/d (234 kg/s)"),
]


def abb_zyklus(datei="abb5_zyklus.png"):
    """Druck-, Temperatur- und Inventarverlauf fuer beide Raten."""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 11), sharex=True)

    for m_dot, farbe, name in RATEN:
        r = Z.simuliere(Z.phasen, m_dot=m_dot)
        t = [x["t"] for x in r]
        ax1.plot(t, [x["p"] for x in r], color=farbe, lw=2.0, label=name)
        ax2.plot(t, [x["T"] for x in r], color=farbe, lw=2.0, label=name)
        ax3.plot(t, [x["m"] for x in r], color=farbe, lw=2.0, label=name)
        mm = [x["m"] for x in r]
        ag = (max(mm)-min(mm))/max(mm)*100
        # Beschriftung mittig in die Inventarkurve
        ax3.text(t[len(t)//2], (max(mm)+min(mm))/2, f"Arbeitsgas {ag:.0f} %",
                 color=farbe, fontsize=12, fontweight="bold", ha="center")

    ax1.axhline(Z.PC, color="gray", ls=":", lw=1.4)
    ax1.text(2, Z.PC+2, f"p_krit {Z.PC:.1f} bar", color="gray", fontsize=10)
    ax1.set_ylabel("Kavernendruck [bar]", fontsize=10.5)

    ax2.axhline(Z.T_rock, color="#5B8C2A", ls="--", lw=1.6)
    ax2.text(2, Z.T_rock+0.7, f"Gebirgstemperatur {Z.T_rock:.0f} °C",
             color="#5B8C2A", fontsize=10)
    ax2.axhline(Z.TC, color="gray", ls=":", lw=1.4)
    ax2.text(2, Z.TC+0.7, f"T_krit {Z.TC:.1f} °C", color="gray", fontsize=10)
    ax2.set_ylabel("Kavernentemperatur [°C]", fontsize=10.5)

    ax3.set_ylabel("Inventar [kt]", fontsize=10.5)
    ax3.set_xlabel("Zeit [Tage]", fontsize=11)

    for a in (ax1, ax2, ax3):
        a.grid(alpha=.3); a.legend(fontsize=9.5, loc="upper right")
    fig.suptitle("Zyklussimulation: Ausspeichern → Stillstand → Einspeichern "
                 "→ Stillstand → Ausspeichern", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.975])
    fig.savefig(datei, dpi=150); plt.close(fig)
    return datei


def abb_inventarmessung(datei="abb6_inventarmessung.png"):
    """Inventar ueber Druck: oberhalb p_krit eindeutig, unterhalb nicht."""
    fig, ax = plt.subplots(figsize=(11, 6.6))

    # Isothermen um die Gebirgstemperatur herum
    isothermen = [(Z.T_rock-10, "#185FA5"), (Z.T_rock, "#1D9E75"), (Z.T_rock+10, "#7B68C8")]
    p = np.linspace(Z.PC, 210, 320)
    for T, farbe in isothermen:
        inv = [PropsSI("D", "P", pp*1e5, "T", T+273.15, "CO2")*Z.V/1e6 for pp in p]
        stil = "-" if abs(T-Z.T_rock) > 1e-9 else "-"
        breite = 2.8 if abs(T-Z.T_rock) < 1e-9 else 2.0
        zusatz = "  (Gebirge)" if abs(T-Z.T_rock) < 1e-9 else ""
        ax.plot(p, inv, stil, color=farbe, lw=breite,
                label=f"einphasig, T = {T:.0f} °C{zusatz}")

    # Zweiphasengebiet: bei gegebenem p liegt das Inventar zwischen
    # Siede- und Taulinie - der Druck sagt dann nichts mehr ueber den Fuellstand.
    p2 = np.linspace(35, Z.PC, 200)
    unten, oben = [], []
    for pp in p2:
        try:
            rho_g = PropsSI("D", "P", pp*1e5, "Q", 1, "CO2")
            rho_l = PropsSI("D", "P", pp*1e5, "Q", 0, "CO2")
        except ValueError:
            continue
        unten.append(rho_g*Z.V/1e6); oben.append(rho_l*Z.V/1e6)
    ax.fill_between(p2[:len(unten)], unten, oben, color="#D85A30", alpha=.18,
                    label="Zweiphasengebiet: derselbe Druck,\njedes Inventar dazwischen möglich")

    ax.axvline(Z.PC, color="gray", ls=":", lw=1.6)
    ax.text(Z.PC+1.5, ax.get_ylim()[1]*0.92, "p_krit", color="gray", fontsize=10.5)
    ax.set_xlabel("Kavernendruck [bar]", fontsize=11)
    ax.set_ylabel("Inventar [kt]", fontsize=11)
    ax.set_title("Warum der Druck unterhalb p_krit kein Füllstandsmaß mehr ist",
                 fontsize=13.5, fontweight="bold")
    ax.grid(alpha=.3); ax.legend(fontsize=9.5, loc="lower right")
    fig.tight_layout(); fig.savefig(datei, dpi=150); plt.close(fig)
    return datei


if __name__ == "__main__":
    print("Erzeugt:", abb_zyklus(), abb_inventarmessung(), sep="\n  ")
