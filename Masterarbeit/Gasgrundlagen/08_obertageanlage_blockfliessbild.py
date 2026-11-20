# -*- coding: utf-8 -*-
"""
G08 - Vereinfachtes Blockfließbild der Obertageanlage eines Erdgas-Kavernenspeichers
============================================================================
Für die Grundlagen (Kap. 2.6): Welche Prozessschritte durchläuft das Gas beim
Ein- und Ausspeichern, und wo trennt die Anlage Netzdruck und Kavernendruck?

Darstellung als Grundfließschema nach DIN EN ISO 10628-1 (Q-076): Blöcke für
Prozessschritte, Pfeile für die Fließrichtung, keine Armaturen, keine
Anlagenkennzeichen. Eigene Darstellung nach der Anlagendokumentation der
Speicherstation Epe (Q-036, Blockfließbilder Fahrwege und Druckbereiche) und
der Stationsbeschreibung in Q-035 (Folie 6 und 7).

Was übernommen ist (Q-036 Blockfließbilder Fahrweg 1, Kombifahrweg 6, Druckbereiche)
  Einspeichern        Netz → Stationseingangsfilter → Speicheranbindung mit
                      Gasmessung (Q-035 Folie 6, in Q-036 „Ein- und
                      Ausgangsmessung“, bidirektional) → Verdichter (parallel)
                      → Feldleitungen → Kavernen
  Ausspeichern        Kavernen → Feldleitungen → Wasserabscheider → Vorwärmer
                      → Druckreduzierung → Trocknung → Gasmessung → Netz
  Ausspeichern mit    wie Ausspeichern, nach der Trocknung zusätzlich über die
  Verdichtung         Verdichter (Kombifahrweg 6: Fahrweg 4 H-Gas, Fahrweg 8 L-Gas)
  Druckbereiche       ND-Bereich: Netzseite bis Verdichtereintritt, Trocknung,
                      Messung. HD-Bereich: Verdichteraustritt, Feldleitungen,
                      Kavernen, Wasserabscheider, Vorwärmer bis Druckreduzierung.
  Kühlung             im Blockfließbild nicht als eigener Block, Gaskühler auf
                      Erdgas-Verdichter- und Speicherstationen nach Q-017 S. 19
Was bewusst fehlt
  H-/L-Gas-Trennung, Ausgangs-Mess- und Regelanlage zum zweiten Netz, Anzahl
  der Einheiten, Armaturen, Bypässe, Kennzeichen (VK, FL, S ...). Die
  Zeichnungen tragen einen Schutzvermerk nach ISO 16016, die Abbildung zeigt
  deshalb nur den allgemeinen Aufbau.
Druckbereiche nur benannt, die Zahlen stehen im Text von Kap. 2.6: Netzdruck in
              Epe unter 84 bar, Kavernendruck 32 bis 209 bar (Q-035 Folie 6). Am
              Bohrlochkopf liegt der Druck um die Gassäule unter dem Kavernendruck.

Abbildung: Abbildungen/abb_G08_obertageanlage_blockfliessbild.png
Braucht nur matplotlib.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle

ORDNER = Path(__file__).resolve().parent
ABB = ORDNER / "Abbildungen"
ABB.mkdir(exist_ok=True)

# ---- Farben -----------------------------------------------------------------------
C_EIN = "#1F5A96"        # Einspeichern
C_AUS = "#C25A0C"        # Ausspeichern
C_ND, C_HD = "#EAF4E1", "#F7E6F0"            # Druckbereiche (Anlehnung an Q-036: grün / magenta)
C_ND_T, C_HD_T = "#4F7A28", "#8E3A6E"
C_BOX, C_RAND, C_TEXT = "#FFFFFF", "#555555", "#222222"

# ---- Geometrie --------------------------------------------------------------------
B, H = 1.22, 0.66                      # Blockbreite und -höhe
Y_EIN, Y_AUS = 2.35, 0.75              # Zeilen Einspeichern / Ausspeichern
X = dict(netz=0.25, filter=1.45, mess=2.85, trock=4.3, verd=5.85, dr=5.85,
         vw=7.4, wa=8.9, fl=10.4, kav=11.7)
X_RECHTS = X["kav"] + 0.5
X_GRENZE = X["verd"]                   # ND/HD-Grenze läuft durch Verdichtung und Druckreduzierung
Y_UNTEN, Y_OBEN = 0.05, 3.35

fig, ax = plt.subplots(figsize=(7.4, 3.0))
ax.set_xlim(-0.35, X_RECHTS + 0.2)
ax.set_ylim(-0.32, Y_OBEN + 0.02)
ax.axis("off")

# -- Druckbereiche
ax.add_patch(Rectangle((0.62, Y_UNTEN), X_GRENZE - 0.62, Y_OBEN - Y_UNTEN, color=C_ND, lw=0, zorder=0))
ax.add_patch(Rectangle((X_GRENZE, Y_UNTEN), X_RECHTS - X_GRENZE, Y_OBEN - Y_UNTEN, color=C_HD, lw=0, zorder=0))
ax.plot([X_GRENZE, X_GRENZE], [Y_UNTEN, Y_OBEN], color="0.55", lw=0.8, ls=(0, (4, 3)), zorder=0.5)
ax.text((0.62 + X_GRENZE) / 2, Y_OBEN - 0.13, "Niederdruckbereich", fontsize=8,
        ha="center", va="top", color=C_ND_T, fontweight="bold")
ax.text((X_GRENZE + X_RECHTS) / 2, Y_OBEN - 0.13, "Hochdruckbereich", fontsize=8,
        ha="center", va="top", color=C_HD_T, fontweight="bold")


def block(x, y, text, nr=None, b=B, h=H):
    ax.add_patch(FancyBboxPatch((x - b / 2, y - h / 2), b, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=C_BOX, ec=C_RAND, lw=1.0, zorder=3))
    ax.text(x, y, text, fontsize=7.8, ha="center", va="center", color=C_TEXT, zorder=4, linespacing=1.15)
    if nr is not None:
        ax.text(x - b / 2 + 0.02, y + h / 2 - 0.02, str(nr), fontsize=6.5, ha="center", va="center",
                color="white", zorder=5, fontweight="bold",
                bbox=dict(boxstyle="circle,pad=0.18", fc="0.35", ec="none"))


def pfeil(x0, y0, x1, y1, farbe, ls="-", lw=1.6):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=farbe, lw=lw, ls=ls, mutation_scale=9,
                                shrinkA=0, shrinkB=0))


def linie(xs, ys, farbe, ls="-", lw=1.6):
    ax.plot(xs, ys, color=farbe, lw=lw, ls=ls, zorder=2, solid_capstyle="butt")


# -- Netz und Kavernenfeld
ax.text(X["netz"], (Y_EIN + Y_AUS) / 2, "Fernleitungs-\nnetz", fontsize=7.5, ha="center", va="center",
        rotation=90, color=C_TEXT, fontweight="bold")
H_GROSS = Y_EIN - Y_AUS + H
block(X["mess"], (Y_EIN + Y_AUS) / 2, "Speicher-\nanbindung\nmit Gas-\nmessung", 2, h=H_GROSS)
block(X["fl"], (Y_EIN + Y_AUS) / 2, "Feld-\nleitungen", 4, h=H_GROSS)
ax.add_patch(FancyBboxPatch((X["kav"] - 0.42, Y_AUS - H / 2), 0.84, H_GROSS,
                            boxstyle="round,pad=0,rounding_size=0.06", fc="#E9E4DA", ec=C_RAND, lw=1.0, zorder=3))
for k, y in enumerate((Y_EIN + 0.08, (Y_EIN + Y_AUS) / 2, Y_AUS - 0.08)):
    ax.add_patch(matplotlib.patches.Ellipse((X["kav"], y), 0.36, 0.42, fc="#D5CDBE", ec="0.45", lw=0.7, zorder=4))
ax.text(X["kav"], Y_AUS - H / 2 - 0.08, "Kavernen", fontsize=7.5, ha="center", va="top", color=C_TEXT,
        fontweight="bold")

# -- Einspeicherpfad
block(X["filter"], Y_EIN, "Eingangs-\nfilter", 1)
block(X["verd"], Y_EIN, "Verdichtung\nund Kühlung", 3, b=1.42)
x_mess_l, x_mess_r = X["mess"] - B / 2, X["mess"] + B / 2
pfeil(0.55, Y_EIN, X["filter"] - B / 2, Y_EIN, C_EIN)
pfeil(X["filter"] + B / 2, Y_EIN, x_mess_l, Y_EIN, C_EIN)
pfeil(x_mess_r, Y_EIN, X["verd"] - 1.42 / 2, Y_EIN, C_EIN)
pfeil(X["verd"] + 1.42 / 2, Y_EIN, X["fl"] - B / 2, Y_EIN, C_EIN)
pfeil(X["fl"] + B / 2, Y_EIN, X["kav"] - 0.42, Y_EIN, C_EIN)

# -- Ausspeicherpfad (von rechts nach links)
block(X["wa"], Y_AUS, "Wasser-\nabscheider", 5)
block(X["vw"], Y_AUS, "Vor-\nwärmung", 6)
block(X["dr"], Y_AUS, "Druck-\nreduzierung", 7, b=1.42)
block(X["trock"], Y_AUS, "Trocknung", 8)
pfeil(X["kav"] - 0.42, Y_AUS, X["fl"] + B / 2, Y_AUS, C_AUS)
pfeil(X["fl"] - B / 2, Y_AUS, X["wa"] + B / 2, Y_AUS, C_AUS)
pfeil(X["wa"] - B / 2, Y_AUS, X["vw"] + B / 2, Y_AUS, C_AUS)
pfeil(X["vw"] - B / 2, Y_AUS, X["dr"] + 1.42 / 2, Y_AUS, C_AUS)
pfeil(X["dr"] - 1.42 / 2, Y_AUS, X["trock"] + B / 2, Y_AUS, C_AUS)
pfeil(X["trock"] - B / 2, Y_AUS, x_mess_r, Y_AUS, C_AUS)
pfeil(x_mess_l, Y_AUS, 0.55, Y_AUS, C_AUS)

# -- Ausspeichern mit Verdichtung: nach der Trocknung über die Verdichter zur Messung
#    hin unten in den Verdichter, zurück oben knapp unter der Einspeicherlinie
y_hin, y_rueck = Y_EIN - 0.24, Y_EIN - 0.12
x_ab = X["trock"] + 0.25
linie([x_ab, x_ab], [Y_AUS + H / 2, y_hin], C_AUS, ls=(0, (2.2, 1.6)), lw=1.3)
pfeil(x_ab, y_hin, X["verd"] - 1.42 / 2, y_hin, C_AUS, ls=(0, (2.2, 1.6)), lw=1.3)
pfeil(X["verd"] - 1.42 / 2, y_rueck, x_mess_r, y_rueck, C_AUS, ls=(0, (2.2, 1.6)), lw=1.3)

# -- Legende
handles = [Line2D([], [], color=C_EIN, lw=1.6, label="Einspeichern"),
           Line2D([], [], color=C_AUS, lw=1.6, label="Ausspeichern"),
           Line2D([], [], color=C_AUS, lw=1.3, ls=(0, (2.2, 1.6)), label="Ausspeichern mit Verdichtung")]
ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=3, fontsize=7.5,
          frameon=False, handlelength=2.2, columnspacing=1.2)

fig.tight_layout(pad=0.2)
fig.savefig(ABB / "abb_G08_obertageanlage_blockfliessbild.png", dpi=175)
print("Abbildung gespeichert:", ABB / "abb_G08_obertageanlage_blockfliessbild.png")
