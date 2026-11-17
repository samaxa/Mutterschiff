# -*- coding: utf-8 -*-
"""
G01 - Phasendiagramm von reinem CO2 mit dem Betriebsbereich der Anlage
============================================================================
Fragen aus der Präsentation: Was heißt überkritisch? Gibt es dort einen
Phasenübergang? Und warum ist das für die Kavernenanlage ein Problem?

Abbildung 1 (abb_G01_phasendiagramm_co2.png)
  Sauberes p-T-Diagramm: fest, flüssig, gasförmig, überkritisch,
  Siede-, Schmelz- und Sublimationslinie, Tripel- und kritischer Punkt,
  pseudokritische Linie (cp-Maximum) und der Betriebsbereich der
  Referenzanlage (30 bis 210 bar, 5 bis 65 °C, Herleitung im Kopf von
  gasgrundlagen_bausteine.py).

Abbildung 2 (abb_G01_dichte_isothermen.png)
  Dichte über dem Druck für mehrere Temperaturen. Unter 31 °C springt die
  Dichte an der Siedelinie (Phasenwechsel). Über 31 °C steigt sie stetig,
  aber in der Nähe der pseudokritischen Linie sehr steil. Kein
  Phasenwechsel, trotzdem ändert sich das Verhalten stark.

Abbildung 3 (abb_G01_pseudokritisch.png)
  Enthalpie und isobare Wärmekapazität über der Temperatur für Isobaren unter
  und über dem kritischen Druck. Zeigt, dass der Übergang flüssigkeitsähnlich ->
  gasähnlich oberhalb von p_krit stetig, nahe der pseudokritischen Linie aber mit
  sehr großem Wärmebedarf je Kelvin abläuft (pseudokritisches Sieden).

Ergebnisse: Abbildungen/G01_phasendiagramm.json
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import gasgrundlagen_bausteine as gb

# ---- 1) Linien -----------------------------------------------------------------
kw = gb.kennwerte("CO2")
T_krit, p_krit = kw["T_krit"], kw["p_krit"]
T_tr, p_tr = kw["T_tripel"], kw["p_tripel"]
T_s, p_s = gb.saettigungslinie_co2()
T_pk, p_pk = gb.pseudokritische_linie_co2()

Tmin, Tmax, Pmin, Pmax = -80.0, 100.0, 0.0, 230.0
T_sub = np.linspace(Tmin + 273.15, T_tr + 273.15, 150)
p_sub = gb.sublimation_bar(T_sub)
T_mel = np.linspace(T_tr + 273.15, T_tr + 273.15 + 6.0, 100)
p_mel = gb.schmelz_bar(T_mel)
T_sub, T_mel = T_sub - 273.15, T_mel - 273.15

print(f"Kritischer Punkt: {T_krit:.2f} °C / {p_krit:.2f} bar, "
      f"ρ = {PropsSI('rhomass_critical', 'CO2'):.1f} kg/m³")
print(f"Tripelpunkt:      {T_tr:.2f} °C / {p_tr:.2f} bar")
print("Pseudokritische Linie (cp-Maximum):")
for p in (80.0, 91.0, 120.0, 150.0, 210.0):
    print(f"  {p:5.0f} bar -> {np.interp(p, p_pk, T_pk):5.1f} °C")

# Siededruck an den Grenzen des Betriebsbereichs
p_s5 = PropsSI("P", "T", gb.K(gb.BETRIEB_T[0]), "Q", 0, "CO2") / 1e5
p_s15 = PropsSI("P", "T", gb.K(15.0), "Q", 0, "CO2") / 1e5
print(f"\nBetriebsbereich {gb.BETRIEB_P[0]:.0f}-{gb.BETRIEB_P[1]:.0f} bar, "
      f"{gb.BETRIEB_T[0]:.0f}-{gb.BETRIEB_T[1]:.0f} °C")
print(f"  Siededruck bei  5 °C: {p_s5:5.1f} bar  -> die Siedelinie läuft von "
      f"{p_s5:.1f} bar / 5 °C bis zum kritischen Punkt durch den Bereich")
print(f"  Siededruck bei 15 °C: {p_s15:5.1f} bar")

# ---- 2) Abbildung 1: Phasendiagramm ---------------------------------------------
C_FEST, C_GAS, C_FLUE, C_SUP = "#D9D2E9", "#CFE2F3", "#D9EAD3", "#FCE5CD"
COL_FEST, COL_GAS, COL_FLUE, COL_SUP = "#5F2176", "#164a73", "#007335", "#a3480b"
COL_REIN, COL_BB = "#00304F", "#333333"


def flaechen(ax):
    gas = [(Tmin, Pmin), (Tmax, Pmin), (Tmax, p_krit), (T_krit, p_krit)]
    gas += list(zip(T_s[::-1], p_s[::-1])) + list(zip(T_sub[::-1], p_sub[::-1]))
    ax.add_patch(plt.Polygon(gas, closed=True, fc=C_GAS, ec="none", zorder=0))
    fest = [(Tmin, Pmax), (T_mel[-1], Pmax)] + list(zip(T_mel[::-1], p_mel[::-1]))
    fest += list(zip(T_sub[::-1], p_sub[::-1]))
    ax.add_patch(plt.Polygon(fest, closed=True, fc=C_FEST, ec="none", zorder=0))
    flue = list(zip(T_s, p_s)) + [(T_krit, Pmax), (T_mel[-1], Pmax)]
    flue += list(zip(T_mel[::-1], p_mel[::-1]))
    ax.add_patch(plt.Polygon(flue, closed=True, fc=C_FLUE, ec="none", zorder=0))
    ax.add_patch(plt.Rectangle((T_krit, p_krit), Tmax - T_krit, Pmax - p_krit,
                               fc=C_SUP, ec="none", zorder=0))


fig, ax = plt.subplots(figsize=(7.4, 5.6))
# Schriftgrößen für den Druck bei 0,8 Textbreite (mindestens rund 7 pt im PDF)
flaechen(ax)
ax.plot(T_sub, p_sub, color="#333333", lw=1.4, zorder=3, label="Sublimationslinie")
ax.plot(T_mel, p_mel, color=COL_FEST, lw=1.4, zorder=3, label="Schmelzlinie")
ax.plot(T_s, p_s, color=COL_REIN, lw=2.0, zorder=3, label="Siedelinie")
ax.plot(T_pk, p_pk, color=COL_SUP, lw=1.4, ls=":", zorder=3,
        label="pseudokritische Linie ($c_p$-Maximum)")
ax.plot(T_krit, p_krit, "o", color=COL_REIN, ms=8, zorder=5, mec="white", mew=1.5)
ax.plot(T_tr, p_tr, "o", color="#333333", ms=6, zorder=5, mec="white", mew=1.2)

# Betriebsbereich der Referenzanlage
(t0, t1), (q0, q1) = gb.BETRIEB_T, gb.BETRIEB_P
ax.add_patch(plt.Rectangle((t0, q0), t1 - t0, q1 - q0, fc="none", ec=COL_BB, lw=1.6,
                           ls="--", zorder=6, label="Betriebsbereich Referenzanlage"))

# Beschriftungen: jeweils mitten in die Fläche, mit Abstand zu allen Linien
box = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8)
ax.text(-68, 110, "fest", fontsize=12, color=COL_FEST, weight="bold", ha="center", va="center", bbox=box)
ax.text(-22, 150, "flüssig", fontsize=13, color=COL_FLUE, weight="bold", ha="center", va="center", bbox=box)
ax.text(40, 14, "gasförmig", fontsize=13, color=COL_GAS, weight="bold", ha="center", va="center", bbox=box)
ax.text(84, 140, "überkritisch", fontsize=12, color=COL_SUP, weight="bold", ha="center", va="center", bbox=box)
# beide Seiten der pseudokritischen Linie (kein Phasenwechsel, nur Übergang)
ax.text(48, 178, "flüssigkeits-\nähnlich", fontsize=10, color=COL_SUP, style="italic",
        ha="center", va="center", zorder=7)
ax.text(87, 100, "gasähnlich", fontsize=10, color=COL_SUP, style="italic",
        ha="center", va="center", zorder=7)
ax.annotate("kritischer Punkt\n" + f"{T_krit:.1f} °C / {p_krit:.1f} bar".replace(".", ","), (T_krit, p_krit),
            textcoords="data", xytext=(68, 36), fontsize=9, color=COL_REIN, bbox=box,
            arrowprops=dict(arrowstyle="-", color=COL_REIN, lw=0.7))
ax.annotate("Tripelpunkt\n" + f"{T_tr:.1f} °C / {p_tr:.1f} bar".replace(".", ",").replace("-", "−"), (T_tr, p_tr),
            textcoords="data", xytext=(-50, 42), ha="left", va="center", fontsize=9,
            color="#333333", bbox=box, arrowprops=dict(arrowstyle="-", color="#333333", lw=0.7))

ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)
ax.set_xlabel("Temperatur [°C]", fontsize=11)
ax.set_ylabel("Druck [bar]", fontsize=11)
# Legende in der Ecke oben links, Beschriftungen liegen darunter
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.95, borderaxespad=0.4,
          handlelength=2.2, labelspacing=0.35)
ax.grid(alpha=0.25, zorder=1)
ax.tick_params(labelsize=10)
fig.tight_layout()
fig.savefig(gb.ABB / "abb_G01_phasendiagramm_co2.png", dpi=175)
plt.close(fig)
print("\ngespeichert: abb_G01_phasendiagramm_co2.png")

# ---- 3) Abbildung 2: Dichte über Druck --------------------------------------------
ISO = [(15.0, "#1F4E79"), (25.0, "#2E75B6"), (T_krit, "#00304F"),
       (40.0, "#C55A11"), (50.0, "#a3480b"), (60.0, "#7F3F00")]
p_lin = np.linspace(10.0, 230.0, 900)
isothermen = {}
fig, ax = plt.subplots(figsize=(9, 5.6))
ax.axvspan(*gb.BETRIEB_P, color="#E7E6E6", alpha=0.6, zorder=0, label="Druckbereich Referenzanlage")
for T, farbe in ISO:
    rho = []
    for p in p_lin:
        if T < T_krit:
            ps = PropsSI("P", "T", gb.K(T), "Q", 0, "CO2") / 1e5
            q = 1 if p < ps else 0                                   # richtige Seite der Siedelinie
            rho.append(PropsSI("D", "P", p * 1e5, "T", gb.K(T), "CO2") if abs(p - ps) > 1e-3
                       else PropsSI("D", "T", gb.K(T), "Q", q, "CO2"))
        else:
            rho.append(PropsSI("D", "P", p * 1e5, "T", gb.K(T) + (1e-3 if T == T_krit else 0.0), "CO2"))
    rho = np.array(rho)
    name = "31,0 °C (kritisch)" if T == T_krit else f"{T:.0f} °C"
    ax.plot(p_lin, rho, color=farbe, lw=2.0 if T == T_krit else 1.6,
            ls="--" if T == T_krit else "-", label=name, zorder=3)
    isothermen[name] = {"p": p_lin[::30].round(2).tolist(), "rho": rho[::30].round(2).tolist()}
    if T < T_krit:
        ps = PropsSI("P", "T", gb.K(T), "Q", 0, "CO2") / 1e5
        r_g = PropsSI("D", "T", gb.K(T), "Q", 1, "CO2")
        r_f = PropsSI("D", "T", gb.K(T), "Q", 0, "CO2")
        ax.plot([ps, ps], [r_g, r_f], color=farbe, lw=1.0, ls=":", zorder=2)
        print(f"{T:4.0f} °C: Sprung an der Siedelinie bei {ps:5.1f} bar von {r_g:5.0f} auf {r_f:5.0f} kg/m³")

ax.set_xlim(10, 230)
ax.set_ylim(0, 1000)
ax.set_xlabel("Druck [bar]")
ax.set_ylabel("Dichte [kg/m³]")
ax.set_title("Dichte von CO₂ über dem Druck")
ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92, title="Temperatur", title_fontsize=8.5)
ax.grid(alpha=0.25, zorder=1)
fig.tight_layout()
fig.savefig(gb.ABB / "abb_G01_dichte_isothermen.png", dpi=175)
plt.close(fig)
print("gespeichert: abb_G01_dichte_isothermen.png")

# Dichteänderung über 91 bar bei 30 bis 50 °C (steilster Bereich, für den Text)
r35 = PropsSI("D", "P", 91e5, "T", gb.K(35.0), "CO2")
r45 = PropsSI("D", "P", 91e5, "T", gb.K(45.0), "CO2")
print(f"\n91 bar: 35 °C -> {r35:.0f} kg/m³, 45 °C -> {r45:.0f} kg/m³ "
      f"(Faktor {r35 / r45:.1f} auf 10 K, ohne Phasenwechsel)")

# ---- 4) Abbildung 3: Übergang über die pseudokritische Linie ----------------------
# Enthalpie und isobare Wärmekapazität über der Temperatur für Isobaren unter und über
# dem kritischen Druck. Unterhalb von p_krit springt die Enthalpie an der Siedelinie um die
# Verdampfungsenthalpie, oberhalb steigt sie stetig, um die pseudokritische Temperatur
# aber sehr steil (pseudokritisches Sieden, Banuti 2015/2019).
ISOBAREN = [(60.0, "#164a73"), (80.0, "#00304F"), (91.0, "#C55A11"),
            (120.0, "#a3480b"), (150.0, "#7F3F00"), (210.0, "#595959")]
T_lin = np.linspace(0.0, 100.0, 1001)
fig, (axh, axc) = plt.subplots(1, 2, figsize=(10.5, 4.6))
pk_kennwerte = {}
for p, farbe in ISOBAREN:
    name = f"{p:.0f} bar"
    if p < p_krit:
        Ts = PropsSI("T", "P", p * 1e5, "Q", 0, "CO2") - 273.15
        h_f = PropsSI("H", "P", p * 1e5, "Q", 0, "CO2") / 1e3
        h_g = PropsSI("H", "P", p * 1e5, "Q", 1, "CO2") / 1e3
        for zweig in (T_lin[T_lin < Ts - 0.05], T_lin[T_lin > Ts + 0.05]):
            h = [PropsSI("H", "P", p * 1e5, "T", gb.K(t), "CO2") / 1e3 for t in zweig]
            c = [PropsSI("C", "P", p * 1e5, "T", gb.K(t), "CO2") / 1e3 for t in zweig]
            axh.plot(zweig, h, color=farbe, lw=1.6, label=name if zweig[0] < Ts else None)
            axc.plot(zweig, c, color=farbe, lw=1.6, label=name if zweig[0] < Ts else None)
        axh.plot([Ts, Ts], [h_f, h_g], color=farbe, lw=1.6)
        axc.axvline(Ts, color=farbe, lw=1.0, ls=":")
        axh.annotate((f"Verdampfung bei {Ts:.1f} °C".replace(".", ",") + "\n"
                      + r"$\Delta h_v$" + f" = {h_g - h_f:.0f} kJ/kg"),
                     (Ts, (h_f + h_g) / 2), xytext=(2, 515), textcoords="data",
                     ha="left", va="center", fontsize=8.5, color=farbe,
                     arrowprops=dict(arrowstyle="-", color=farbe, lw=0.7))
        axc.text(Ts + 1.0, 40, f"Verdampfung {p:.0f} bar", rotation=90, ha="left", va="top",
                 fontsize=8, color=farbe)
        pk_kennwerte[name] = {"T_siede": Ts, "dh_v": h_g - h_f}
        continue
    h = np.array([PropsSI("H", "P", p * 1e5, "T", gb.K(t), "CO2") for t in T_lin]) / 1e3
    c = np.array([PropsSI("C", "P", p * 1e5, "T", gb.K(t), "CO2") for t in T_lin]) / 1e3
    axh.plot(T_lin, h, color=farbe, lw=1.6, label=name)
    axc.plot(T_lin, c, color=farbe, lw=1.6, label=name)
    i = int(np.argmax(c))
    axh.plot(T_lin[i], h[i], "o", color=farbe, ms=5, mec="white", mew=0.8, zorder=5)
    axc.plot(T_lin[i], c[i], "o", color=farbe, ms=5, mec="white", mew=0.8, zorder=5)
    Tpk = float(T_lin[i])
    dh10 = (PropsSI("H", "P", p * 1e5, "T", gb.K(Tpk + 5), "CO2")
            - PropsSI("H", "P", p * 1e5, "T", gb.K(Tpk - 5), "CO2")) / 1e3
    pk_kennwerte[name] = {
        "T_pk": Tpk, "cp_max": float(c[i]),
        "dh_Tpk_pm5K": dh10,
        "rho_Tpk_minus5K": PropsSI("D", "P", p * 1e5, "T", gb.K(Tpk - 5), "CO2"),
        "rho_Tpk_plus5K": PropsSI("D", "P", p * 1e5, "T", gb.K(Tpk + 5), "CO2"),
        "kappa_T_max_1_per_bar": max(PropsSI("isothermal_compressibility", "P", p * 1e5,
                                             "T", gb.K(t), "CO2") for t in T_lin[T_lin > 31.5]) * 1e5,
    }
    print(f"{name}: T_pk = {Tpk:5.1f} °C, cp_max = {c[i]:5.1f} kJ/(kg K), "
          f"Δh über ±5 K = {dh10:5.1f} kJ/kg")
axh.set_xlabel("Temperatur [°C]")
axh.set_ylabel("spez. Enthalpie [kJ/kg]")
axh.set_title("Enthalpie über der Temperatur")
axh.set_xlim(0, 100)
axc.set_xlabel("Temperatur [°C]")
axc.set_ylabel("isobare Wärmekapazität $c_p$ [kJ/(kg K)]")
axc.set_title("Isobare Wärmekapazität über der Temperatur")
axc.set_yscale("log")
axc.set_ylim(0.8, 60)
axc.set_yticks([1, 2, 5, 10, 20, 50])
axc.set_xlim(0, 100)
axc.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
axh.legend(loc="lower right", fontsize=8.5, framealpha=0.95, title="Druck", title_fontsize=8.5)
axc.text(0.98, 0.97, "Punkte: pseudokritische Temperatur ($c_p$-Maximum)", transform=axc.transAxes,
         ha="right", va="top", fontsize=8.5, color="#333333")
for a in (axh, axc):
    a.grid(alpha=0.25, zorder=1)
fig.tight_layout()
fig.savefig(gb.ABB / "abb_G01_pseudokritisch.png", dpi=175)
plt.close(fig)
print("gespeichert: abb_G01_pseudokritisch.png")

# Kühlung bei 91 bar von 60 °C auf 15 °C: Anteil der Wärme zwischen 35 und 45 °C
q_ges = (PropsSI("H", "P", 91e5, "T", gb.K(60.0), "CO2") - PropsSI("H", "P", 91e5, "T", gb.K(15.0), "CO2")) / 1e3
q_pk = (PropsSI("H", "P", 91e5, "T", gb.K(45.0), "CO2") - PropsSI("H", "P", 91e5, "T", gb.K(35.0), "CO2")) / 1e3
print(f"Kühlung 91 bar 60 -> 15 °C: {q_ges:.1f} kJ/kg, davon 35-45 °C {q_pk:.1f} kJ/kg ({q_pk / q_ges:.0%})")
pk_kennwerte["kuehlung_91bar_60_15C"] = {"q_gesamt": q_ges, "q_35_45C": q_pk}

json.dump({
    "krit": {"T": T_krit, "p": p_krit, "rho": PropsSI("rhomass_critical", "CO2")},
    "tripel": {"T": T_tr, "p": p_tr},
    "betriebsbereich": {"p": gb.BETRIEB_P, "T": gb.BETRIEB_T},
    "siededruck_5C": p_s5, "siededruck_15C": p_s15,
    "pseudokritisch": {"p": p_pk.tolist(), "T": T_pk.round(3).tolist()},
    "rho_91bar": {"35C": r35, "45C": r45},
    "isothermen": isothermen,
    "pseudokritischer_uebergang": pk_kennwerte,
}, open(gb.ABB / "G01_phasendiagramm.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
