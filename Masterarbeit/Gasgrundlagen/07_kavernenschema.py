# -*- coding: utf-8 -*-
"""
G07 - Schema einer Speicherkaverne mit Bohrung und Druckgrenzen über der Teufe
============================================================================
Für die Grundlagen (Kap. 2.3): Wie ist eine Kavernenbohrung aufgebaut, worauf
beziehen sich die Drücke, und woher kommt der Höchstdruck?

Links  Schema (Breiten nicht maßstäblich, Teufen maßstäblich)
       Bohrlochkopf, Untertagesicherheitsventil, zementierte Rohrtouren,
       Förderstrang, Packer, LCCS, Kavernendach, Kaverne, Sumpf mit Restsole,
       Gebirgstemperatur als Farbskala.
Rechts Druckgrenzen über der Teufe: Gebirgsdruck aus der mittleren
       Gebirgsdichte, 85-%-Grenze für den Höchstdruck, Mindestdruck der
       Referenzkaverne (70 bar an der LCCS, linear über die Teufe übertragen) und
       das Druckfenster der Referenzkaverne an der LCCS mit Kissen- und Arbeitsgas.
       Stand 19.11.2026: Titel links ohne "Breiten nicht maßstäblich" (steht in der
       Bildunterschrift), Mindestdruck und Kissen-/Arbeitsgas ergänzt.

Herkunft der Zahlen (keine eigene Rechnung außer Grundrechenarten)
  LCCS 1200 m, 70 bis 210 bar, 650.000 m³     Referenzkaverne (kaverne_bausteine.TIEF,
                                              Tabelle Referenzbedingungen, Kap. 4)
  Bezugsteufe LCCS + 205 m = 1405 m            Q-028 Tab. 1 (kaverne_bausteine.DZ_BEZUG)
  Kavernendach LCCS + 40 m, Sumpf LCCS + 290 m Q-028 Tab. 1 (LCCS 1150 m, Dach 1190 m,
                                              Sumpf 1440 m), auf LCCS 1200 m übertragen
  Standrohr 80 m, Zwischenrohrtour 400 m,      Q-030 Abb. 8 (Bohrungsschema Option 1/2)
  Untertagesicherheitsventil 50 m, Packer
  oberhalb der LCCS, Förderstrang 8 5/8"
  Gebirge 10 °C + 0,03 K/m                     Q-028 (kaverne_bausteine.T_gebirge)
  mittlere Gebirgsdichte 2200 kg/m³            Q-003 S. 46 (Überlagerungsdruck)
  Höchstdruck höchstens 85 % des Gebirgsdrucks Q-038
  Lage des Salzstocks (Oberkante) nur schematisch.

Abbildung: Abbildungen/abb_G07_kavernenschema.png
Ergebnisse: Abbildungen/G07_kavernenschema.json

Braucht Kaverne/Grundlagen/kaverne_bausteine.py (wie 06).
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon, Rectangle

import gasgrundlagen_bausteine as gb

sys.path.insert(0, str(gb.ORDNER.parent / "Kaverne" / "Grundlagen"))
import kaverne_bausteine as kb  # noqa: E402

# ---- 1) Zahlen -----------------------------------------------------------------
KAV = kb.TIEF
Z_LCCS = KAV.z_lccs                       # 1200 m
Z_BEZUG = KAV.z_mitte                     # 1405 m
Z_DACH = Z_LCCS + 40.0                    # Q-028 Tab. 1: 1190 - 1150 m
Z_SUMPF = Z_LCCS + 290.0                  # Q-028 Tab. 1: 1440 - 1150 m
Z_STANDROHR, Z_ZWISCHEN, Z_SSV = 80.0, 400.0, 50.0   # Q-030 Abb. 8
Z_PACKER = Z_LCCS - 40.0                  # schematisch, oberhalb der LCCS (Q-030 Abb. 8)
Z_SALZ = 450.0                            # Oberkante Salzstock, nur schematisch
RHO_GEBIRGE = 2200.0                      # kg/m³, Q-003 S. 46
F_MAX = 0.85                              # Q-038
P_KRIT = kb.P_KRIT                        # 73,8 bar

T_0, T_LCCS, T_BEZUG = kb.T_gebirge(0.0), kb.T_gebirge(Z_LCCS), kb.T_gebirge(Z_BEZUG)
p_geb = lambda z: RHO_GEBIRGE * kb.G * z / 1e5          # bar
p_geb_lccs = p_geb(Z_LCCS)
print(f"Gebirgstemperatur: {T_0:.0f} °C an der Oberfläche, {T_LCCS:.1f} °C an der LCCS, "
      f"{T_BEZUG:.1f} °C in der Bezugsteufe {Z_BEZUG:.0f} m")
print(f"Gebirgsdruck an der LCCS ({RHO_GEBIRGE:.0f} kg/m³): {p_geb_lccs:.1f} bar, "
      f"85 %: {F_MAX * p_geb_lccs:.1f} bar")
print(f"Referenz {KAV.p_max:.0f} bar = {KAV.p_max / p_geb_lccs * 100:.1f} % des Gebirgsdrucks")
print(f"Gradienten: Gebirgsdruck {p_geb(1.0):.4f} bar/m, Referenz-Höchstdruck "
      f"{KAV.p_max / Z_LCCS:.4f} bar/m")


def de(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


def tsd(x):
    return f"{x:,.0f}".replace(",", ".")


# ---- 2) Abbildung -----------------------------------------------------------------
C_DECK, C_SALZ, C_CO2, C_SUMPF, C_SOLE = "#E9DFCC", "#EEF1F4", "#D9EAD3", "#B7A99A", "#BFD7EA"
C_ZEMENT, C_ROHR, C_TEXT = "#B5B5B5", "#222222", "#333333"
COL_CO2 = gb.STOFFE["CO2"][2]
Y_OBEN, Y_UNTEN = -210.0, 1560.0

fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 5.9), sharey=True,
                             gridspec_kw=dict(width_ratios=[1.75, 1.0], wspace=0.08))

# -- Gebirge
xs = np.linspace(-100, 100, 200)
salz_oben = Z_SALZ + 0.006 * xs**2
a1.add_patch(Rectangle((-100, 0), 200, Y_UNTEN, fc=C_DECK, ec="none", zorder=0))
a1.add_patch(Polygon(list(zip(xs, salz_oben)) + [(100, Y_UNTEN), (-100, Y_UNTEN)],
                     fc=C_SALZ, ec="#9AA5B1", lw=0.8, zorder=0.5))
a1.plot([-100, 100], [0, 0], color="#6B5B45", lw=1.2, zorder=1)
a1.text(-60, 170, "Deckgebirge", fontsize=8.5, color="#6B5B45", ha="center")
a1.text(-60, 820, "Salzstock\n(Steinsalz)", fontsize=8.5, color="#5A6775", ha="center")

# -- Gebirgstemperatur als Farbskala am linken Rand
cmap = LinearSegmentedColormap.from_list("T", ["#DCEBF7", "#FBE3C8", "#F2A27A"])
z_band = np.linspace(0, Z_SUMPF, 300)
a1.imshow(z_band[:, None], extent=(-97, -90, Z_SUMPF, 0), aspect="auto", cmap=cmap,
          zorder=2, origin="upper")
a1.add_patch(Rectangle((-97, 0), 7, Z_SUMPF, fc="none", ec="0.4", lw=0.6, zorder=2.1))
for z, T in ((0.0, T_0), (Z_LCCS, T_LCCS), (Z_BEZUG, T_BEZUG)):
    a1.plot([-90, -87], [z, z], color="0.3", lw=0.8, zorder=2.2)
    a1.text(-86, max(z, 22.0), f"{de(T, 0)} °C", fontsize=8, va="center", ha="left", zorder=3,
            color=C_TEXT)
a1.text(-93.5, 560, "Gebirgstemperatur 10 °C + 0,03 K/m", rotation=90, fontsize=8,
        va="center", ha="center", color="0.2", zorder=3)

# -- Kaverne (Dach, Zylinder, Boden), Halbbreite w(y)
yk = np.linspace(Z_DACH, Z_SUMPF, 300)
w = np.full_like(yk, 34.0)
dach = yk < Z_DACH + 55
w[dach] = np.maximum(5.0, 34.0 * np.sqrt(np.clip(1 - ((Z_DACH + 55 - yk[dach]) / 55) ** 2, 0, 1)))
boden = yk > Z_SUMPF - 45
w[boden] = 34.0 * np.sqrt(np.clip(1 - ((yk[boden] - (Z_SUMPF - 45)) / 45) ** 2, 0, 1))
w = w * (1 + 0.025 * np.sin((yk - Z_DACH) / 40.0))         # leicht unregelmäßige Wand
umriss = list(zip(w, yk)) + list(zip(-w[::-1], yk[::-1]))
hals = [(-5, Z_LCCS), (5, Z_LCCS), (5, Z_DACH), (-5, Z_DACH)]
a1.add_patch(Polygon(hals, fc=C_CO2, ec="none", zorder=3))
a1.add_patch(Polygon(umriss, fc=C_CO2, ec=COL_CO2, lw=1.0, zorder=3))
a1.plot([-5, -5], [Z_LCCS, Z_DACH + 1], color=COL_CO2, lw=1.0, zorder=3.1)
a1.plot([5, 5], [Z_LCCS, Z_DACH + 1], color=COL_CO2, lw=1.0, zorder=3.1)
# Sumpf mit Restsole
z_sole, z_sumpf_oben = Z_SUMPF - 42, Z_SUMPF - 34
for z0, z1, fc, hatch in ((z_sole, z_sumpf_oben, C_SOLE, None), (z_sumpf_oben, Z_SUMPF, C_SUMPF, "...")):
    sel = (yk >= z0) & (yk <= z1)
    poly = list(zip(w[sel], yk[sel])) + list(zip(-w[sel][::-1], yk[sel][::-1]))
    a1.add_patch(Polygon(poly, fc=fc, ec="none", hatch=hatch, zorder=3.2))
a1.text(0, 1296, "Kaverne\n" + f"{tsd(KAV.volumen)} m³", ha="center", va="center",
        fontsize=8.5, color=COL_CO2, zorder=4)
a1.plot(0, Z_BEZUG, "x", color=COL_CO2, ms=6, mew=1.5, zorder=4)
a1.text(4, Z_BEZUG, f"Bezugsteufe\n{tsd(Z_BEZUG)} m", fontsize=7.5, va="center",
        color=COL_CO2, zorder=4)

# -- Rohrtouren mit Zement (Halbbreiten schematisch)
touren = ((Z_STANDROHR, 11.0), (Z_ZWISCHEN, 8.0), (Z_LCCS, 5.0))
for z_schuh, b in touren:
    for s in (-1, 1):
        a1.add_patch(Rectangle((s * b if s > 0 else -b - 1.6, 0), 1.6, z_schuh,
                               fc=C_ZEMENT, ec="none", zorder=4))
        a1.plot([s * b, s * b], [0, z_schuh], color=C_ROHR, lw=1.1, zorder=5)
        a1.add_patch(Polygon([(s * b, z_schuh), (s * (b + 1.8), z_schuh - 12), (s * b, z_schuh - 12)],
                             fc=C_ROHR, ec="none", zorder=5))           # Rohrschuh
# Förderstrang
a1.add_patch(Rectangle((-2.2, -20), 4.4, Z_LCCS + 45, fc="white", ec="none", zorder=5.5))
a1.add_patch(Rectangle((-1.6, -20), 3.2, Z_LCCS + 45, fc=C_CO2, ec="none", zorder=5.6))
for s in (-1, 1):
    a1.plot([s * 2.2, s * 2.2], [-20, Z_LCCS + 25], color=C_ROHR, lw=1.0, zorder=6)
# Packer und Untertagesicherheitsventil
for s in (-1, 1):
    a1.add_patch(Rectangle((s * 2.2 if s > 0 else -5.0, Z_PACKER - 8), 2.8, 16,
                           fc="#555555", ec=C_ROHR, lw=0.6, zorder=6))
a1.add_patch(Polygon([(-4.5, Z_SSV - 14), (4.5, Z_SSV + 14), (4.5, Z_SSV - 14), (-4.5, Z_SSV + 14)],
                     fc="#C0392B", ec="#7B241C", lw=0.6, zorder=7))

# -- Bohrlochkopf und Leitung zur Obertageanlage
for y0, y1, b in ((-20, 0, 9.0), (-90, -20, 5.5), (-135, -90, 4.0)):
    a1.add_patch(Rectangle((-b, y0), 2 * b, y1 - y0, fc="#D5DBE1", ec=C_ROHR, lw=0.9, zorder=7))
a1.plot([4.0, 38], [-165, -165], color=C_ROHR, lw=2.2, zorder=6.5)
a1.plot([4.0, 4.0], [-165, -135], color=C_ROHR, lw=2.2, zorder=6.5)
a1.annotate("", xy=(50, -165), xytext=(36, -165),
            arrowprops=dict(arrowstyle="<|-|>", color=C_ROHR, lw=1.2), zorder=7)
a1.text(52, -165, "Obertageanlage", fontsize=8.5, va="center", ha="left", color=C_TEXT)

# -- Beschriftungen rechts mit Hinweislinien
def hinweis(text, xy, y_text, x_text=30, fett=False):
    a1.annotate(text, xy=xy, xytext=(x_text, y_text), fontsize=8, va="center", ha="left",
                color=C_TEXT, fontweight="bold" if fett else "normal", zorder=8,
                arrowprops=dict(arrowstyle="-", color="0.35", lw=0.6, shrinkA=1, shrinkB=0))

hinweis("Bohrlochkopf mit\nAbsperrarmaturen", (5.5, -60), -75)
hinweis("Untertagesicherheitsventil", (4.5, Z_SSV), 45)
hinweis("Standrohr", (12.6, Z_STANDROHR - 20), 110)
hinweis("Zwischenrohrtour", (9.6, 330), 300)
hinweis("Förderstrang 8 5/8\"", (2.2, 650), 640)
hinweis("letzte zementierte\nRohrtour mit Zement", (6.6, 900), 900)
hinweis("Packer", (5.0, Z_PACKER), Z_PACKER - 30)
hinweis(f"LCCS {tsd(Z_LCCS)} m", (6.8, Z_LCCS - 6), Z_LCCS + 8, fett=True)
hinweis("Kavernendach", (14, Z_DACH + 12), Z_DACH + 30, x_text=44)
hinweis("Sumpf mit Restsole", (20, Z_SUMPF - 25), Z_SUMPF + 25, x_text=44)

# Druckangaben am Kopf und an der LCCS (links)
a1.text(-12, -75, r"$p_\mathrm{Kopf}$", fontsize=9, ha="right", va="center", color=C_TEXT)
a1.text(-12, Z_LCCS - 12, r"$p_\mathrm{LCCS}$" + f" = {de(KAV.p_min, 0)} bis {de(KAV.p_max, 0)} bar",
        fontsize=8, ha="right", va="bottom", color=C_TEXT, zorder=8,
        bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.0))

a1.set_xlim(-100, 100)
a1.set_ylim(Y_UNTEN, Y_OBEN)
a1.set_xticks([])
a1.set_ylabel("Teufe in m")
a1.set_yticks(np.arange(0, 1600, 200))
a1.set_title("Kaverne und Bohrung", fontsize=10)
for sp in ("top", "right"):
    a1.spines[sp].set_visible(False)

# -- rechts: Druckgrenzen über der Teufe
z = np.linspace(0, 1550, 100)
a2.plot(p_geb(z), z, color="#6B5B45", lw=1.8,
        label=f"Gebirgsdruck ({tsd(RHO_GEBIRGE)} kg/m³)")
a2.plot(F_MAX * p_geb(z), z, color="#C0392B", lw=1.8, ls="--",
        label="Höchstdruck (85 %)")
a2.plot(KAV.p_min / Z_LCCS * z, z, color="#2E6DA4", lw=1.6, ls="-.",
        label="Mindestdruck")
a2.axvline(P_KRIT, color="0.45", ls=":", lw=1.0)
a2.text(P_KRIT - 4, 560, r"$p_\mathrm{krit}$ CO$_2$", rotation=90, fontsize=8,
        va="top", ha="right", color="0.3")
a2.plot([KAV.p_min, KAV.p_max], [Z_LCCS, Z_LCCS], color=COL_CO2, lw=5, solid_capstyle="butt",
        alpha=0.85, label="Druckfenster an der LCCS")
for p, col in ((p_geb_lccs, "#6B5B45"), (F_MAX * p_geb_lccs, "#C0392B"), (KAV.p_min, "#2E6DA4")):
    a2.plot(p, Z_LCCS, "o", color=col, ms=4, zorder=5)
# Kissengas bis zum Mindestdruck, Arbeitsgas bis zum Höchstdruck (Druckbereiche an der LCCS)
Z_PFEIL = Z_LCCS + 70
for p0, p1, txt in ((0.0, KAV.p_min, "Kissengas"), (KAV.p_min, KAV.p_max, "Arbeitsgas")):
    a2.annotate("", xy=(p1, Z_PFEIL), xytext=(p0, Z_PFEIL),
                arrowprops=dict(arrowstyle="<|-|>", color=C_TEXT, lw=0.9, mutation_scale=7), zorder=6)
    a2.text(p0 + 1 if p0 == 0.0 else 0.5 * (p0 + p1), Z_PFEIL + 22, txt, fontsize=7,
            ha="left" if p0 == 0.0 else "center", va="top", color=C_TEXT, zorder=6)
# Werte an der LCCS direkt an den Punkten
for p, txt, col in ((p_geb_lccs, de(p_geb_lccs, 0), "#6B5B45"), (F_MAX * p_geb_lccs, de(F_MAX * p_geb_lccs, 0), "#C0392B")):
    a2.text(p + 8, Z_LCCS - 14, txt, fontsize=7.5, ha="left", va="bottom", color=col, zorder=6)
a2.set_xlim(0, 340)
a2.set_xlabel("Druck in bar")
a2.set_title("Druckgrenzen über der Teufe", fontsize=10)
a2.grid(alpha=0.3)
a2.legend(loc="upper right", fontsize=7, framealpha=0.95, handlelength=2.2, borderpad=0.5)
a2.tick_params(axis="y", labelleft=False)
for sp in ("top", "right"):
    a2.spines[sp].set_visible(False)

fig.subplots_adjust(left=0.09, right=0.985, top=0.935, bottom=0.09)
fig.savefig(gb.ABB / "abb_G07_kavernenschema.png", dpi=175)
print("Abbildung gespeichert:", gb.ABB / "abb_G07_kavernenschema.png")

json.dump({
    "z_LCCS_m": Z_LCCS, "z_Kavernendach_m": Z_DACH, "z_Sumpf_m": Z_SUMPF, "z_Bezug_m": Z_BEZUG,
    "T_Oberflaeche_C": T_0, "T_LCCS_C": T_LCCS, "T_Bezug_C": T_BEZUG,
    "rho_Gebirge_kg_m3": RHO_GEBIRGE, "p_Gebirge_LCCS_bar": p_geb_lccs,
    "p_85prozent_LCCS_bar": F_MAX * p_geb_lccs, "p_max_Referenz_bar": KAV.p_max,
    "p_max_Anteil_Gebirgsdruck": KAV.p_max / p_geb_lccs, "p_min_Referenz_bar": KAV.p_min,
    "p_min_Gradient_bar_m": KAV.p_min / Z_LCCS,
    "Quellen": "Q-028 Tab. 1, Q-030 Abb. 8, Q-003 S. 46, Q-038",
}, open(gb.ABB / "G07_kavernenschema.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
