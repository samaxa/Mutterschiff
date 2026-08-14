# -*- coding: utf-8 -*-
"""Blockfliessbilder im Kartenstil (Szenario-Layout)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrow

GAS   = "#2E7BC4"
DICHT = "#1E8A5F"
LILA  = "#6B5FBF"
UEBER = "#D9534F"
KAV   = "#4E9A51"
TXT   = "#1A1A1A"
GRAU  = "#4A4A4A"
PFEIL = "#8A8A8A"

W, H = 2.28, 1.86          # Kartenmass
GAP  = 0.30                # Abstand zwischen Karten


def karte(ax, x, y, code, badge, titel, zeilen, wert, farbe):
    ax.add_patch(FancyBboxPatch((x, y), W, H,
                                boxstyle="round,pad=0,rounding_size=0.13",
                                lw=2.0, ec=farbe, fc="white", zorder=3))
    ax.text(x + 0.16, y + H - 0.24, code, fontsize=12.5, fontweight="bold",
            color=TXT, va="center", zorder=5)
    bw = 0.20 + 0.085 * len(badge)
    bx = x + W - 0.16 - bw
    ax.add_patch(FancyBboxPatch((bx, y + H - 0.38), bw, 0.28,
                                boxstyle="round,pad=0,rounding_size=0.13",
                                lw=1.3, ec=farbe, fc="white", zorder=4))
    ax.text(bx + bw / 2, y + H - 0.24, badge, fontsize=8.8, color=farbe,
            ha="center", va="center", zorder=5)
    ax.text(x + 0.16, y + H - 0.56, titel, fontsize=12.5, fontweight="bold",
            color=TXT, va="center", zorder=5)
    ax.plot([x + 0.16, x + W - 0.16], [y + H - 0.72] * 2,
            color="#CFD4D9", lw=1.1, zorder=5)
    for i, z in enumerate(zeilen):
        ax.text(x + 0.16, y + H - 0.94 - i * 0.235, z, fontsize=9.4,
                color=GRAU, va="center", zorder=5)
    ax.add_patch(FancyBboxPatch((x + 0.15, y + 0.14), W - 0.30, 0.38,
                                boxstyle="round,pad=0,rounding_size=0.11",
                                lw=1.4, ec=farbe, fc="white", zorder=4))
    ax.text(x + W / 2, y + 0.33, wert, fontsize=9.8, color=TXT,
            ha="center", va="center", zorder=5)


def pfeil(ax, x, y, dx):
    ax.add_patch(FancyArrow(x, y, dx, 0, width=0.020, head_width=0.115,
                            head_length=0.115, length_includes_head=True,
                            color=PFEIL, zorder=2))


def band(ax, x0, x1, y, text, farbe):
    ax.add_patch(FancyBboxPatch((x0, y), x1 - x0, 0.34,
                                boxstyle="round,pad=0,rounding_size=0.15",
                                lw=0, fc=farbe, alpha=0.16, zorder=1))
    ax.text((x0 + x1) / 2, y + 0.17, text, fontsize=11, color=farbe,
            ha="center", va="center", zorder=5)


def zeichne(datei, titel, untertitel, kopf_ein, ein, baender_ein,
            kopf_aus, aus, baender_aus, kaverne, fussnoten):
    n = max(len(ein), len(aus))
    breite = n * W + (n - 1) * GAP
    kav_x = breite + 0.62
    kav_w = 1.95
    fw = kav_x + kav_w + 0.30
    fh = 7.05 + 0.24 * len(fussnoten)

    fig, ax = plt.subplots(figsize=(fw, fh))
    ax.set_xlim(-0.30, fw - 0.30)
    ax.set_ylim(0, fh)
    ax.axis("off")

    if titel:
        ax.text(fw / 2 - 0.30, fh - 0.34, titel, fontsize=17, fontweight="bold",
                ha="center", color=TXT)
        ax.text(fw / 2 - 0.30, fh - 0.72, untertitel, fontsize=10.5, ha="center",
                color=GRAU)
    else:
        ax.text(fw / 2 - 0.30, fh - 0.42, untertitel, fontsize=11, ha="center",
                color=GRAU)

    y_ein = fh - 3.20
    y_aus = y_ein - 3.02

    for kopf, reihe, y, baender, rueck in (
            (kopf_ein, ein, y_ein, baender_ein, False),
            (kopf_aus, aus, y_aus, baender_aus, True)):
        ax.text(0, y + H + 0.28, kopf, fontsize=13, fontweight="bold", color=TXT)
        for i, k in enumerate(reihe):
            x = i * (W + GAP)
            karte(ax, x, y, *k)
            if i < len(reihe) - 1:
                if rueck:
                    pfeil(ax, x + W + GAP - 0.06, y + H / 2, -(GAP - 0.12))
                else:
                    pfeil(ax, x + W + 0.06, y + H / 2, GAP - 0.12)
        xe = (len(reihe) - 1) * (W + GAP) + W
        if rueck:
            pfeil(ax, kav_x - 0.06, y + H / 2, -(kav_x - 0.06 - xe - 0.06))
        else:
            pfeil(ax, xe + 0.06, y + H / 2, kav_x - xe - 0.12)
        for x0f, x1f, t, c in baender:
            band(ax, x0f * (W + GAP), x1f * (W + GAP) - GAP, y - 0.52, t, c)

    ky = y_aus - 0.52
    kh = (y_ein + H) - ky
    ax.add_patch(FancyBboxPatch((kav_x, ky), kav_w, kh,
                                boxstyle="round,pad=0,rounding_size=0.15",
                                lw=0, fc=KAV, alpha=0.10, zorder=1))
    ax.add_patch(FancyBboxPatch((kav_x, ky), kav_w, kh,
                                boxstyle="round,pad=0,rounding_size=0.15",
                                lw=2.0, ec=KAV, fc="none", zorder=2))
    ax.text(kav_x + kav_w / 2, ky + kh / 2 + 0.55, "SALZ-\nKAVERNE",
            fontsize=14, fontweight="bold", color=KAV, ha="center",
            va="center", linespacing=1.35, zorder=5)
    for i, z in enumerate(kaverne):
        ax.text(kav_x + kav_w / 2, ky + kh / 2 - 0.15 - i * 0.28, z,
                fontsize=10.5, color="#3B7A3E", ha="center", zorder=5)

    for i, f in enumerate(fussnoten):
        ax.text(0, 0.62 - i * 0.26, f, fontsize=10, color=GRAU, va="center")

    fig.tight_layout(pad=0.35)
    fig.savefig(datei, dpi=170)
    plt.close(fig)
    print("gespeichert:", datei)



# ================================================================== Szenario D
ein_D = [
    ("E1", "dicht", "Anlieferung OGE", ["Fernleitung, ESD,", "Filter + Messung"],
     "85 bar · 15 °C", DICHT),
    ("E2", "dicht", "Pumpe", ["mehrstufige Radialpumpe,", "η = 0,8; w = 3,66 kJ/kg"],
     "→ 110,8 bar · 17,9 °C", DICHT),
    ("E3", "dicht", "Sonde / Bohrkopf", ["18 → 51 °C; homogen,", "keine Phasengrenze"],
     "111 → 210 bar", LILA),
]
aus_D = [
    ("A4", "dicht", "Rücklieferung OGE", ["in Spec;", "Ende: Pumpe boostet"],
     "85 bar · ≤ 25 °C", DICHT),
    ("A3", "dicht", "Nachkühler", ["hält OGE-Spec 5–25 °C;", "0,8–1,5 MW"],
     "85 bar · → ≤ 25 °C", GAS),
    ("A2", "dicht", "Drossel", ["Regelventil, 1 Stufe, JT;", "über OGE-Spec"],
     "→ 85 bar · 32 °C", UEBER),
    ("A1", "dicht", "Bohrlochkopf", ["Eigendruck; Auslegung", "Nennrate, adiabat"],
     "120 bar · 37,9 °C", LILA),
]
zeichne(
    "bfb_szD.png", "",
    "ANNAHMEN: Anlieferung 85 bar / 15 °C · Teufe 1200 m · Gebirge 15 °C + 3 °C/100 m · η_Pumpe = 0,8 · 50.000–100.000 Nm³/h = 27,5–55 kg/s",
    "① EINSPEICHERUNG — nur Pumpe →", ein_D,
    [(0, 3, "dichte / überkritische Phase — durchgehend einphasig", LILA)],
    "② AUSSPEICHERUNG — Eigendruck + Drossel + Nachkühler ←", aus_D,
    [(0, 4, "dichte / überkritische Phase — durchgehend einphasig", LILA)],
    ["70–210 bar", "51 °C", "überkritisch", "650.000 m³", "", "Solesumpf:", "Wasser/Sole"],
    ["Pumpenleistung 101–201 kW; Betriebsvolumenstrom 113–226 m³/h → Radialpumpe nach API 610.",
     "Die Pumpe fällt je nach Anlieferdruck unterschiedlich aus: je höher der Übergabedruck, desto kleiner der Hub.",
     "ZONE I (p_LCCS 167–210 bar): Bohrloch durchgehend dicht. ZONE II (137–167 bar): Kopf unterkritisch. ZONE III (70–137 bar): Zweiphasengebiet.",
     "Kein Verdichter, keine Trocknung, kein Vorwärmer — dafür ein Nachkühler, den es in der Erdgasanlage nicht gibt."])

# ================================================================== Szenario G
ein_G = [
    ("E1", "Gas", "Anlieferung Gas", ["Gas-Pipeline;", "Spec 25–35 bar / 5–25 °C"],
     "30 bar · 15 °C", GAS),
    ("E2", "Gas", "Verdichter St. 1", ["η = 0,8; r ≈ 1,63", "Maschinentyp offen"],
     "→ 49 bar · 56,4 °C", GAS),
    ("E3", "Gas", "Zwischenkühler", ["Rückkühlung vor", "Stufe 2"], "49 bar · 40 °C", GAS),
    ("E4", "Gas", "Verdichter St. 2", ["nur bis knapp über p_krit;", "1,6–3,1 MW gesamt"],
     "→ 80 bar · 83,8 °C", GAS),
    ("E5", "dicht", "Nachkühler", ["VERFLÜSSIGUNG;", "ρ = 777 kg/m³, homogen"],
     "80 bar · 25 °C", DICHT),
    ("E6", "dicht", "Pumpe (Kernstrang)", ["w = 4,9 kJ/kg; 135–269 kW", "→ ab hier wie Szenario D"],
     "→ 111 bar · 30 °C", DICHT),
]
aus_G = [
    ("A5", "Gas", "Abgabe Gas-Pipeline", ["Messung, ggf.", "Trocknung/Reinigung"],
     "30 bar · 15 °C", GAS),
    ("A4", "Gas", "Vorwärmer 2", ["vor Drossel 2;", "0,7–1,5 MW"], "60 bar · → 46 °C", UEBER),
    ("A3", "Überg.", "Drossel 1", ["isenthalp, JT;", "10 K über T_sat"],
     "→ 60 bar · 32 °C", UEBER),
    ("A2", "dicht", "Vorwärmer 1", ["von 41 °C;", "3,7–7,5 MW"], "120 bar · → 75 °C", UEBER),
    ("A1", "dicht", "Bohrlochkopf", ["Auslegung wie Sz. D;", "Teillast bis ~20 °C"],
     "120 bar · 41 °C", LILA),
]
zeichne(
    "bfb_szG.png", "",
    "ANNAHMEN: Anlieferung 30 bar / 15 °C · Teufe 1200 m · Gebirge 15 °C + 3 °C/100 m · η = 0,8 · 50.000–100.000 Nm³/h = 27,5–55 kg/s",
    "① EINSPEICHERUNG — Gas → Verdichtung → Verflüssigung → Pumpe →", ein_G,
    [(0, 4, "gasförmig", KAV), (4, 6, "dichte Phase", LILA)],
    "② AUSSPEICHERUNG — zweistufig vorwärmen und drosseln ←", aus_G,
    [(0, 2, "gasförmig", KAV), (2, 4, "JT-Übergang", UEBER), (4, 5, "dichte Phase", LILA)],
    ["70–210 bar", "51 °C", "überkritisch", "650.000 m³", "", "Solesumpf:", "Wasser/Sole"],
    ["Verdichter endet bei 80 bar: verflüssigen und pumpen statt gasförmig durchzuverdichten.",
     "Siemens Energy nennt für die Verdichtung drei Technologien — Getriebe-, Einwellen- und Kolbenverdichter (Auswahl offen).",
     "Ohne Vorwärmung direkt auf 30 bar: −5,6 °C und zweiphasig (q = 0,21) — außerhalb Spec, nicht zulässig.",
     "Einstufige Alternative: eine Vorwärmung auf höhere Temperatur statt zwei Stufen — noch zu prüfen."])
