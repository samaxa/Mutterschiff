# -*- coding: utf-8 -*-
"""
Drei Prozesspfade, drei Entscheidungen — und wo sie schon gefahren werden.
==========================================================================
Stellt die gerechneten Pfade als Blockketten nebeneinander, markiert die
getroffene Wahl und ordnet jedem Pfad die Referenzprojekte zu, in denen
er bereits betrieben wird.

Zahlen aus gaspfad_vergleich.py und pumpe_oder_verdichter.py.
Aufruf: python pfadentscheidung.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
GRAU, HELLGRAU = "#4A4A4A", "#B8C4CC"

GASF = dict(fc="#FDF0E3", ec=ORANGE)      # gasförmig
DICHT = dict(fc="#E6F2EA", ec=GRUEN)      # flüssig / dicht
NEUTRAL = dict(fc="#EFF2F4", ec=HELLGRAU)

PFADE = [
    dict(
        name="Pfad D",
        unter="Anlieferung in\ndichter Phase",
        badge=("AUSLEGUNGSFALL", GRUEN),
        kette=[("Anlieferung OGE\n85 bar · 15 °C", DICHT),
               ("Pumpe\n→ 107,6 bar", DICHT),
               ("Gassäule 1200 m\n→ 210 bar", DICHT)],
        arbeit="3,21 kJ/kg", leistung="177 kW",
        refs=["Northern Lights, Øygarden (NO)",
              "flüssig per Schiff bei −26 °C / 15–19 bar,",
              "Puffertanks und Injektionspumpen, kein Verdichter.",
              "In Betrieb seit 08/2025, 1,5 Mt/a."],
        farbe=GRUEN),
    dict(
        name="Pfad G",
        unter="gasförmige\nAnlieferung",
        badge=("MITGEFÜHRTE VARIANTE", BLAU),
        kette=[("Anlieferung\n30 bar · 15 °C", GASF),
               ("Verdichter\n2 Stufen → 80 bar", GASF),
               ("Verflüssiger\n80 bar · 25 °C", DICHT),
               ("Pumpe\n→ 107,6 bar", DICHT)],
        arbeit="61,6 kJ/kg", leistung="3,4 MW",
        refs=["Snøhvit / Hammerfest LNG (NO)",
              "CO₂ aus Erdgas: verdichten, verflüssigen, zurückpumpen.",
              "Zwei Getriebeverdichter Siemens Energy, seit 2008.",
              "MOL EOR (HR): 88 km gasförmig, dann verflüssigt bei 200 bar."],
        farbe=BLAU),
    dict(
        name="Pfad 3",
        unter="Vergleichsfall,\nnicht gewählt",
        badge=("VERWORFEN", ROT),
        kette=[("Anlieferung\n30 bar · 15 °C", GASF),
               ("Verdichter\n3 Stufen → 107,6 bar", GASF),
               ("Nachkühler\n→ 30 °C", NEUTRAL)],
        arbeit="69,7 kJ/kg", leistung="3,8 MW",
        refs=["Porthos, Maasvlakte (NL)",
              "3 × Everllence RG 28-6, je 250 t/h, bis 180 bar;",
              "danach nur 22 km gasförmig zur Plattform P18-A.",
              "FPSO Pré-Sal (BR): Verdichter statt Pumpe wegen Platz und Gewicht."],
        farbe=ROT),
]

BW, BH, GAP = 2.24, 1.02, 0.30          # Blockmaße
X_KETTE, X_ENERGIE, X_REF = 2.75, 13.05, 15.05
FW, FH = 25.4, 6.5

SC = 1.6
fig, ax = plt.subplots(figsize=(FW / SC, FH / SC))
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
ax.set_xlim(0, FW)
ax.set_ylim(0, FH)
ax.axis("off")

for i, p in enumerate(PFADE):
    y = FH - 1.90 - i * 1.62
    yc = y + BH / 2

    # --- Zeilenhintergrund
    ax.add_patch(FancyBboxPatch((0.05, y - 0.40), FW - 0.15, BH + 0.80,
                                boxstyle="round,pad=0,rounding_size=0.10",
                                fc="#F7F9FA" if i % 2 == 0 else "#FFFFFF",
                                ec="none", zorder=0))

    # --- Name und Badge
    ax.text(0.25, yc + 0.30, p["name"], fontsize=13, fontweight="bold", color=p["farbe"], va="center")
    ax.text(0.25, yc - 0.14, p["unter"], fontsize=8.5, color=GRAU, va="center", linespacing=1.35)
    btxt, bcol = p["badge"]
    ax.add_patch(FancyBboxPatch((0.25, y - 0.34), max(1.15, 0.158 * len(btxt)), 0.30,
                                boxstyle="round,pad=0,rounding_size=0.14",
                                fc=bcol, ec="none", zorder=3))
    ax.text(0.25 + max(1.15, 0.158 * len(btxt)) / 2, y - 0.19, btxt, fontsize=7.2,
            fontweight="bold", color="white", ha="center", va="center", zorder=4)

    # --- Prozesskette
    x = X_KETTE
    for j, (label, stil) in enumerate(p["kette"]):
        ax.add_patch(FancyBboxPatch((x, y), BW, BH,
                                    boxstyle="round,pad=0,rounding_size=0.10",
                                    lw=1.7, zorder=2, **stil))
        ax.text(x + BW / 2, yc, label, fontsize=8.6, color=DUNKEL, ha="center",
                va="center", linespacing=1.45, zorder=3)
        if j < len(p["kette"]) - 1:
            ax.add_patch(FancyArrowPatch((x + BW + 0.05, yc), (x + BW + GAP - 0.05, yc),
                                         arrowstyle="-|>", mutation_scale=11,
                                         color="#8A8A8A", lw=1.5, zorder=3))
        x += BW + GAP

    # --- Energie
    ax.text(X_ENERGIE, yc + 0.17, p["arbeit"], fontsize=12, fontweight="bold",
            color=p["farbe"], va="center")
    ax.text(X_ENERGIE, yc - 0.20, p["leistung"], fontsize=8.6, color=GRAU, va="center")

    # --- Referenzprojekte
    ax.text(X_REF, yc + 0.42, p["refs"][0], fontsize=9.4, fontweight="bold",
            color=DUNKEL, va="center")
    for k, zeile in enumerate(p["refs"][1:]):
        ax.text(X_REF, yc + 0.13 - k * 0.27, zeile, fontsize=8.3, color=GRAU, va="center")

# --- Spaltenüberschriften
for x, t in ((X_KETTE, "Prozesskette"), (X_ENERGIE, "Wellenarbeit"),
             (X_REF, "Wird bereits so betrieben in")):
    ax.text(x, FH - 0.12, t, fontsize=10, fontweight="bold", color=DUNKEL, va="top", linespacing=1.4)
ax.plot([0.05, FW - 0.10], [FH - 0.60, FH - 0.60], color=HELLGRAU, lw=1.0)

ax.text(0.25, 0.36,
        "Der Unterschied zu Porthos ist nicht die Maschine, sondern was dahinter kommt: dort 22 km Leitung, hier 1200 m Gassäule. "
        "Die Säule liefert 103 bar umsonst — deshalb lohnt bei uns die Pumpe.",
        fontsize=9, color=DUNKEL, fontweight="bold", va="center")
ax.text(0.25, 0.12,
        "Leistungen bei 100.000 Nm³/h = 54,9 kg/s · eigene Rechnung (CoolProp) · Herstellerangaben Siemens Energy und Everllence, Stand 08/2026 · Northern Lights / Equinor · Q-002 · Q-013",
        fontsize=7.6, color="#7A7A7A", va="center")

fig.savefig("abb_pfadentscheidung.png", dpi=175)
print("gespeichert: abb_pfadentscheidung.png")
