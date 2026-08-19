# -*- coding: utf-8 -*-
"""
Zyklussimulation - folientaugliche Fassung
===========================================
abb5_zyklus.png ist 14 x 11 Zoll mit drei gestapelten Diagrammen und auf einer
Folie nicht lesbar. Diese Fassung zeigt dieselbe Rechnung im Querformat und
stellt die Aussage in den Vordergrund.

  A  Kaverneninnentemperatur   der schnelle Fall faellt unter T_krit
  B  Inventar                  daraus folgt das nutzbare Arbeitsgas
  C  Modell, Ergebnis, Folge

Rechnung aus zyklus.py (Massen- und Energiebilanz der Kaverne).
Aufruf: python zyklus_folie.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import zyklus as Z

BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
GRAU, HELLGRAU = "#4A4A4A", "#B8C4CC"

RATEN = [
    (Z.m_dot_nom, BLAU, f"langsam — {Z.m_dot_nom:.0f} kg/s  (Nennrate ~100.000 Nm³/h)"),
    (234.0, ROT, f"schnell — 234 kg/s  (Grenze {Z.dpdt_max:.0f} bar/Tag)"),
]


def de(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


print("simuliere ...")
ERG = []
for m_dot, farbe, name in RATEN:
    r = Z.simuliere(Z.phasen, m_dot=m_dot)
    mm = [x["m"] for x in r]
    tt = [x["T"] for x in r]
    ag = (max(mm) - min(mm)) / max(mm) * 100.0
    ERG.append(dict(r=r, farbe=farbe, name=name, m_dot=m_dot,
                    ag=ag, m_min=min(mm), m_max=max(mm), T_min=min(tt)))
    print(f"  {m_dot:6.0f} kg/s -> T_min {min(tt):5.1f} degC, "
          f"Inventar {min(mm):.1f}-{max(mm):.1f} kt, Arbeitsgas {ag:.0f} %")

# ------------------------------------------------------------- Zeichnen
fig = plt.figure(figsize=(16.6, 6.9))
gs = fig.add_gridspec(2, 2, width_ratios=[1.62, 1.00], height_ratios=[1, 1],
                      wspace=0.16, hspace=0.28,
                      left=0.045, right=0.978, top=0.895, bottom=0.135)
axT = fig.add_subplot(gs[0, 0])
axM = fig.add_subplot(gs[1, 0], sharex=axT)
axC = fig.add_subplot(gs[:, 1])
axC.set_xlim(0, 10); axC.set_ylim(0, 10); axC.axis("off")

# ---------------- A  Temperatur
for e in ERG:
    axT.plot([x["t"] for x in e["r"]], [x["T"] for x in e["r"]],
             color=e["farbe"], lw=2.2, label=e["name"])
axT.axhline(Z.TC, color=ROT, ls="--", lw=1.6, zorder=1)
axT.text(196, Z.TC - 1.5, f"T_krit = {de(Z.TC,1)} °C", fontsize=8.6, color=ROT,
         fontweight="bold", va="top")
axT.axhline(Z.T_rock, color=GRUEN, ls=":", lw=1.5, zorder=1)
axT.text(196, Z.T_rock + 1.0, f"Gebirge {Z.T_rock:.0f} °C", fontsize=8.6, color=GRUEN,
         va="bottom")
axT.annotate(f"fällt auf {de(ERG[1]['T_min'],1)} °C\n→ unter T_krit, zweiphasig",
             xy=(14, ERG[1]["T_min"]), xytext=(56, 25.0), fontsize=8.8, color=ROT,
             fontweight="bold", ha="left", va="center", linespacing=1.6,
             bbox=dict(boxstyle="round,pad=0.28", fc="white", ec=ROT, lw=1.2, alpha=0.96),
             arrowprops=dict(arrowstyle="->", color=ROT, lw=1.3))
axT.set_ylabel("Kaverne  [°C]", fontsize=9.6)
axT.set_ylim(24, 60)
axT.legend(frameon=False, fontsize=8.8, loc="upper right", ncol=1)
axT.spines[["top", "right"]].set_visible(False)
axT.tick_params(colors=GRAU, labelsize=8.8, labelbottom=False)
axT.grid(axis="y", color="#EDF1F4", lw=0.9)
axT.set_axisbelow(True)
axT.set_title("A  Die Rate bestimmt, wie stark die Kaverne auskühlt",
              fontsize=11.5, fontweight="bold", color=DUNKEL, loc="left", pad=10)

# ---------------- B  Inventar
for e in ERG:
    axM.plot([x["t"] for x in e["r"]], [x["m"] for x in e["r"]],
             color=e["farbe"], lw=2.2)
    axM.axhline(e["m_min"], color=e["farbe"], ls=":", lw=1.0, alpha=0.6)
for e, xa in zip(ERG, (185, 62)):
    axM.annotate("", xy=(xa, e["m_max"]), xytext=(xa, e["m_min"]),
                 arrowprops=dict(arrowstyle="<->", color=e["farbe"], lw=1.8))
    axM.text(xa + 5, (e["m_max"] + e["m_min"]) / 2,
             f"Arbeitsgas\n{e['ag']:.0f} %", fontsize=9.2, color=e["farbe"],
             fontweight="bold", va="center", linespacing=1.5)
axM.set_ylabel("Inventar  [kt]", fontsize=9.6)
axM.set_xlabel("Zeit  [Tage]", fontsize=9.6)
axM.spines[["top", "right"]].set_visible(False)
axM.tick_params(colors=GRAU, labelsize=8.8)
axM.grid(axis="y", color="#EDF1F4", lw=0.9)
axM.set_axisbelow(True)
axM.set_title("B  Und damit, wieviel nutzbar bleibt",
              fontsize=11.5, fontweight="bold", color=DUNKEL, loc="left", pad=10)

# ---------------- C  Modell und Ergebnis
axC.set_title("C  Modell und Ergebnis", fontsize=12.5, fontweight="bold",
              color=DUNKEL, loc="left", pad=12)

axC.add_patch(FancyBboxPatch((0.15, 7.30), 9.70, 2.30,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#F4F7F9", ec=HELLGRAU, lw=1.3, zorder=2))
axC.text(0.50, 9.15, "Massen- und Energiebilanz der Kaverne", fontsize=9.4,
         fontweight="bold", color=DUNKEL, va="center", zorder=3)
axC.text(0.50, 8.42, "dm/dt  =  ṁ", fontsize=10.6, color=DUNKEL,
         fontweight="bold", va="center", zorder=3)
axC.text(0.50, 7.80, "dU/dt  =  ṁ·h  +  UA·(T_Gebirge − T_Kaverne)", fontsize=10.6,
         color=DUNKEL, fontweight="bold", va="center", zorder=3)

y = 6.30
for e in ERG:
    axC.add_patch(FancyBboxPatch((0.15, y - 1.62), 9.70, 1.72,
                                 boxstyle="round,pad=0,rounding_size=0.18",
                                 fc="#FFFFFF", ec=e["farbe"], lw=2.0, zorder=2))
    axC.text(0.55, y - 0.48, f"{e['ag']:.0f} %", fontsize=17, fontweight="bold",
             color=e["farbe"], va="center", zorder=3)
    axC.text(2.75, y - 0.34, e["name"].split("—")[0].strip().capitalize()
             + f" · {e['m_dot']:.0f} kg/s", fontsize=9.6, fontweight="bold",
             color=DUNKEL, va="center", zorder=3)
    axC.text(2.75, y - 0.92, f"Kaverne kühlt auf {de(e['T_min'],0)} °C · "
                             f"Inventar {de(e['m_min'],0)}–{de(e['m_max'],0)} kt",
             fontsize=8.5, color=GRAU, va="center", zorder=3)
    y -= 2.06

axC.add_patch(FancyBboxPatch((0.15, 0.20), 9.70, 1.85,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             fc="#FFF6EC", ec=ORANGE, lw=1.6, zorder=2))
axC.text(0.50, 1.62, "Die Rate ist ein Auslegungsfreiheitsgrad", fontsize=9.6,
         fontweight="bold", color=ORANGE, va="center", zorder=3)
axC.text(0.50, 0.82,
         "Q-028 vermutet den Zusammenhang qualitativ, hier ist er beziffert.\n"
         "Q-038 stützt dieselbe Richtung geomechanisch: eine begrenzte Rate\n"
         "senkt auch die thermisch induzierte Rissbildung an der Kavernenwand.",
         fontsize=8.5, color=DUNKEL, va="center", linespacing=1.7, zorder=3)

# ------------------------------------------------------------- Fuss
fig.text(0.045, 0.048,
         f"Simulierter Zyklus: Ausspeichern → Stillstand → Einspeichern → Stillstand → "
         f"Ausspeichern · Volumen {Z.V/1000:.0f}·10³ m³ · Teufe {Z.TEUFE:.0f} m · "
         f"Gebirge {Z.T_rock:.0f} °C · Einspeichertemperatur {Z.T_inj:.0f} °C · "
         f"Druckänderung begrenzt auf {Z.dpdt_max:.0f} bar/Tag",
         fontsize=8.4, color=GRAU)
fig.text(0.045, 0.019,
         "eigene Rechnung (CoolProp / Span & Wagner 1996) · zyklus.py · Q-028 · Q-038 · "
         "Vereinfachungen: Kaverne ideal durchmischt, Bohrloch nicht modelliert, "
         "UA = 546 kW/K ist eine Annahme",
         fontsize=8, color="#7A7A7A")

fig.savefig("abb_zyklus_folie.png", dpi=220)
print("\ngespeichert: abb_zyklus_folie.png")
