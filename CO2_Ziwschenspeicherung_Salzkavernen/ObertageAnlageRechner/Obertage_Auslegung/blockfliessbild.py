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
    fh = 7.35 + 0.26 * len(fussnoten)

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

    y0 = 0.36 + (len(fussnoten) - 1) * 0.26
    for i, f in enumerate(fussnoten):
        ax.text(0, y0 - i * 0.26, f, fontsize=10, color=GRAU, va="center")

    fig.tight_layout(pad=0.35)
    fig.savefig(datei, dpi=170)
    plt.close(fig)
    print("gespeichert:", datei)



# ================================================================== Szenario D
ein_S1 = [
    ("E1", "dicht", "Anlieferung OGE", ["Fernleitung, ESD,", "\u00dcbergabe Netzbetreiber"],
     "85 bar \u00b7 15 °C", DICHT),
    ("E2", "dicht", "Filter + Messung", ["Partikelfilter, Coriolis,", "Mengenerfassung"],
     "85 bar \u00b7 15 °C", GAS),
    ("E3", "dicht", "Pumpe", ["mehrstufige Radialpumpe,", "\u03b7 = 0,8; w = 3,21 kJ/kg"],
     "\u2192 107,6 bar \u00b7 17,5 °C", DICHT),
    ("E4", "dicht", "Sonde / Bohrkopf", ["18 \u2192 46 °C; homogen,", "keine Phasengrenze"],
     "108 \u2192 210 bar", LILA),
]
aus_S1 = [
    ("A6", "dicht", "R\u00fccklieferung OGE", ["Coriolis, Mengenerfassung;", "\u00dcbergabe in Spec"],
     "85 bar \u00b7 \u2264 25 °C", DICHT),
    ("A5", "dicht", "Aufbereitung", ["Bedarf OFFEN \u2014 erst nach", "Feuchtemessung entscheidbar"],
     "85 bar \u00b7 \u2264 25 °C", UEBER),
    ("A4", "dicht", "Nachk\u00fchler", ["h\u00e4lt OGE-Spec 5\u201325 °C;", "0,5\u20130,9 MW"],
     "85 bar \u00b7 \u2192 \u2264 25 °C", GAS),
    ("A3", "dicht", "Drossel", ["Regelventil, 1 Stufe, JT;", "\u00fcber OGE-Spec"],
     "\u2192 85 bar \u00b7 29,5 °C", UEBER),
    ("A2", "dicht", "Abscheider", ["freies Wasser und Sole", "vor der Drossel"],
     "120 bar \u00b7 34,2 °C", GAS),
    ("A1", "dicht", "Bohrlochkopf", ["Eigendruck; Auslegung", "Nennrate, adiabat"],
     "120 bar \u00b7 34,2 °C", LILA),
]
zeichne(
    "bfb_sz1.png", "",
    "SZENARIO 1 \u2014 ANNAHMEN: Anlieferung 85 bar / 15 °C in dichter Phase \u00b7 Teufe 1200 m \u00b7 Gebirge 10 °C + 3 °C/100 m \u00b7 \u03b7_Pumpe = 0,8 \u00b7 50.000\u2013100.000 Nm\u00b3/h = 27,5\u201355 kg/s",
    "\u2460 EINSPEICHERUNG \u2014 Filter, Messung, Pumpe \u2192", ein_S1,
    [(0, 4, "dichte / \u00fcberkritische Phase \u2014 durchgehend einphasig", LILA)],
    "\u2461 AUSSPEICHERUNG \u2014 Eigendruck, Abscheider, Drossel, Nachk\u00fchler \u2190", aus_S1,
    [(0, 6, "dichte / \u00fcberkritische Phase \u2014 durchgehend einphasig", LILA)],
    ["70\u2013210 bar", "46 °C", "\u00fcberkritisch", "650.000 m\u00b3", "", "Solesumpf:", "Wasser/Sole"],
    ["Pumpenleistung 88\u2013176 kW; Betriebsvolumenstrom 113\u2013226 m\u00b3/h bei \u0394p = 23 bar \u2192 Radialpumpe nach API 610.",
     "Filter und Messung liegen unmittelbar an der \u00dcbergabestelle \u2014 die Mengenerfassung erfolgt in Masse, nicht in Normvolumen.",
     "ZONE I (p_LCCS 167\u2013210 bar): Bohrloch durchgehend dicht. ZONE II (137\u2013167 bar): Kopf unterkritisch. ZONE III (70\u2013137 bar): Zweiphasengebiet.",
     "A5 ist bewusst als offener Block gef\u00fchrt: ob nach Solekontakt getrocknet werden muss, ist ohne Feuchtemesswert nicht entscheidbar (Q-019, Q-050).",
     "Kein Verdichter und kein Vorw\u00e4rmer \u2014 daf\u00fcr ein Nachk\u00fchler, den es in der Erdgasanlage nicht gibt."])

# ================================================================== Szenario 2
ein_S2 = [
    ("E1", "Gas", "Anlieferung Gas", ["Gas-Pipeline;", "Spec 25\u201335 bar / 5\u201325 °C"],
     "30 bar \u00b7 15 °C", GAS),
    ("E2", "Gas", "Filter + Messung", ["Partikelfilter, Coriolis,", "Mengenerfassung"],
     "30 bar \u00b7 15 °C", GAS),
    ("E3", "Gas", "Verdichter St. 1", ["\u03b7 = 0,8; r \u2248 1,63", "Maschinentyp offen"],
     "\u2192 49 bar \u00b7 56,4 °C", GAS),
    ("E4", "Gas", "Zwischenk\u00fchler", ["R\u00fcckk\u00fchlung vor", "Stufe 2"], "49 bar \u00b7 40 °C", GAS),
    ("E5", "Gas", "Verdichter St. 2", ["nur bis knapp \u00fcber p_krit;", "1,6\u20133,1 MW gesamt"],
     "\u2192 80 bar \u00b7 83,9 °C", GAS),
    ("E6", "dicht", "Verfl\u00fcssiger", ["\u03c1 = 777 kg/m\u00b3, homogen;", "234 kJ/kg abzuf\u00fchren"],
     "80 bar \u00b7 25 °C", DICHT),
    ("E7", "dicht", "Pumpe (Kernstrang)", ["w = 4,4 kJ/kg; 121\u2013241 kW", "\u2192 ab hier wie Szenario 1"],
     "\u2192 108 bar \u00b7 29,5 °C", DICHT),
]
aus_S2 = [
    ("A7", "Gas", "Abgabe Gas-Pipeline", ["Coriolis,", "Mengenerfassung"],
     "30 bar \u00b7 15 °C", GAS),
    ("A6", "Gas", "Trocknung (TEG)", ["Optimum 30\u201350 bar", "\u2192 hier gut einbindbar"],
     "30 bar \u00b7 \u2264 25 °C", UEBER),
    ("A5", "Gas", "Vorw\u00e4rmer 2", ["vor Drossel 2;", "0,7\u20131,5 MW"], "60 bar \u00b7 \u2192 46 °C", UEBER),
    ("A4", "\u00dcberg.", "Drossel 1", ["isenthalp, JT;", "10 K \u00fcber T_sat"],
     "\u2192 60 bar \u00b7 32 °C", UEBER),
    ("A3", "dicht", "Vorw\u00e4rmer 1", ["von 41 °C;", "3,7\u20137,5 MW"], "120 bar \u00b7 \u2192 75 °C", UEBER),
    ("A2", "dicht", "Abscheider", ["freies Wasser und Sole", "vor der Vorw\u00e4rmung"],
     "120 bar \u00b7 41 °C", GAS),
    ("A1", "dicht", "Bohrlochkopf", ["Auslegung wie Sz. 1;", "Teillast bis ~20 °C"],
     "120 bar \u00b7 41 °C", LILA),
]
zeichne(
    "bfb_sz2.png", "",
    "SZENARIO 2 \u2014 ANNAHMEN: Anlieferung 30 bar / 15 °C gasf\u00f6rmig \u00b7 Teufe 1200 m \u00b7 Gebirge 10 °C + 3 °C/100 m \u00b7 \u03b7 = 0,8 \u00b7 50.000\u2013100.000 Nm\u00b3/h = 27,5\u201355 kg/s",
    "\u2460 EINSPEICHERUNG \u2014 Filter, Messung, Verdichtung, Verfl\u00fcssigung, Pumpe \u2192", ein_S2,
    [(0, 5, "gasf\u00f6rmig", KAV), (5, 7, "dichte Phase", LILA)],
    "\u2461 AUSSPEICHERUNG \u2014 Abscheiden, zweistufig vorw\u00e4rmen und drosseln, trocknen \u2190", aus_S2,
    [(0, 2, "gasf\u00f6rmig", KAV), (2, 5, "JT-\u00dcbergang", UEBER), (5, 7, "dichte Phase", LILA)],
    ["70\u2013210 bar", "46 °C", "\u00fcberkritisch", "650.000 m\u00b3", "", "Solesumpf:", "Wasser/Sole"],
    ["Verdichter endet bei 80 bar: verfl\u00fcssigen und pumpen statt gasf\u00f6rmig durchzuverdichten \u2014 spart rund 12 % Wellenarbeit (Szenario 3).",
     "Siemens Energy nennt f\u00fcr die Verdichtung drei Technologien \u2014 Getriebe-, Einwellen- und Kolbenverdichter (Auswahl offen).",
     "Ohne Vorw\u00e4rmung direkt auf 30 bar: \u22125,6 °C und zweiphasig (q = 0,45) \u2014 au\u00dferhalb Spec, nicht zul\u00e4ssig.",
     "Die Trocknung liegt in Szenario 2 auf der Niederdruckseite und damit im TEG-Optimum (Q-050) \u2014 in Szenario 1 ist das nicht der Fall.",
     "Einstufige Alternative: eine Vorw\u00e4rmung auf h\u00f6here Temperatur statt zwei Stufen \u2014 noch zu pr\u00fcfen."])
