# -*- coding: utf-8 -*-
"""
Szenario G: verflüssigen und pumpen oder gasförmig durchverdichten?
====================================================================
Beide Wege führen von 30 bar / 15 °C auf 107,6 bar am Bohrlochkopf.
Links die Wellenarbeit (teure Währung), rechts die Kühllast (billige Währung).

Kernaussage: Die Verflüssigung kostet fast nichts extra, weil gekühlt
werden muss ohnehin — gespart wird dagegen eine ganze Verdichterstufe.

Stoffdaten CoolProp (Span & Wagner 1996). Aufruf: python gaspfad_vergleich.py
"""
import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BAR = 1e5
C2K = lambda t: t + 273.15
K2C = lambda t: t - 273.15
F = "CO2"
ETA = 0.80
T_ZK = 40.0
P_ZIEL = 107.6
VN = 100_000.0
RHO_N = CP.PropsSI("D", "T", 273.15, "P", 101325.0, F)
M_DOT = RHO_N * VN / 3600.0

BLAU, DUNKEL, ORANGE, ROT, GRUEN = "#0476D9", "#00304F", "#EE7203", "#CA220E", "#007335"
HELLBLAU, HELLGRAU = "#68AFE1", "#B8C4CC"


def h(p, T):
    return CP.PropsSI("H", "P", p * BAR, "T", C2K(T), F) / 1000.0


def stufe(p1, T1, p2):
    h1 = CP.PropsSI("H", "P", p1 * BAR, "T", C2K(T1), F)
    s1 = CP.PropsSI("S", "P", p1 * BAR, "T", C2K(T1), F)
    h2s = CP.PropsSI("H", "P", p2 * BAR, "S", s1, F)
    h2 = h1 + (h2s - h1) / ETA
    return (h2 - h1) / 1000.0, K2C(CP.PropsSI("T", "P", p2 * BAR, "H", h2, F))


# ---------------------------------------------- Pfad 2: verflüssigen und pumpen
w1, T1 = stufe(30.0, 15.0, 49.0)
q1 = h(49.0, T1) - h(49.0, T_ZK)
w2, T2 = stufe(49.0, T_ZK, 80.0)
q2 = h(80.0, T2) - h(80.0, 25.0)
wp, Tp = stufe(80.0, 25.0, P_ZIEL)
P2_W = [("Verdichter Stufe 1\n30 → 49 bar", w1, ORANGE),
        ("Verdichter Stufe 2\n49 → 80 bar", w2, ORANGE),
        ("Pumpe\n80 → 107,6 bar", wp, GRUEN)]
P2_Q = [("Zwischenkühler", q1, HELLBLAU), ("Verflüssiger", q2, BLAU)]

# ---------------------------------------------- Pfad 3: gasförmig durchverdichten
p_alt = [30.0, 46.2, 71.0, P_ZIEL]
P3_W, P3_Q = [], []
T = 15.0
for i in range(3):
    w, T_out = stufe(p_alt[i], T, p_alt[i + 1])
    P3_W.append((f"Verdichter Stufe {i+1}\n{p_alt[i]:.0f} → {p_alt[i+1]:.0f} bar", w, ORANGE))
    if i < 2:
        P3_Q.append((f"Zwischenkühler {i+1}", h(p_alt[i + 1], T_out) - h(p_alt[i + 1], T_ZK), HELLBLAU))
        T = T_ZK
    else:
        P3_Q.append(("Nachkühler auf 30 °C", h(P_ZIEL, T_out) - h(P_ZIEL, 30.0), BLAU))

W2, W3 = sum(x[1] for x in P2_W), sum(x[1] for x in P3_W)
Q2, Q3 = sum(x[1] for x in P2_Q), sum(x[1] for x in P3_Q)

# ---------------------------------------------- Zeichnen
fig, (axL, axR) = plt.subplots(1, 2, figsize=(15.2, 5.9),
                               gridspec_kw={"width_ratios": [1, 1]})
LABELS = ["Pfad 2\nverflüssigen\nund pumpen", "Pfad 3\ngasförmig\ndurchverdichten"]


def stapel(ax, daten, y, hoehe, mit_text=True, schwelle=6.0):
    links = 0.0
    for name, wert, farbe in daten:
        ax.barh(y, wert, left=links, height=hoehe, color=farbe,
                edgecolor="white", linewidth=1.6)
        if mit_text and wert > schwelle:
            ax.text(links + wert / 2, y, f"{name}\n{wert:.1f}", ha="center", va="center",
                    fontsize=8.5, color="white", fontweight="bold", linespacing=1.3)
        links += wert
    return links


for ax, (d2, d3), titel, einheit, gesamt in (
        (axL, (P2_W, P3_W), "Wellenarbeit — die teure Währung", "kJ/kg", (W2, W3)),
        (axR, (P2_Q, P3_Q), "Kühllast — die billige Währung", "kJ/kg", (Q2, Q3))):
    schwelle = 0.11 * max(gesamt)
    stapel(ax, d2, 1, 0.46, schwelle=schwelle)
    stapel(ax, d3, 0, 0.46, schwelle=schwelle)
    for y, g in ((1, gesamt[0]), (0, gesamt[1])):
        ax.text(g + max(gesamt) * 0.02, y, f"{g:.1f} {einheit}", va="center",
                fontsize=12, fontweight="bold", color=DUNKEL)
    ax.set_yticks([1, 0])
    ax.set_yticklabels(LABELS, fontsize=10, color=DUNKEL)
    ax.set_xlim(0, max(gesamt) * 1.26)
    ax.set_ylim(-0.55, 1.62)
    ax.set_xlabel(f"spezifisch [{einheit}]", fontsize=10)
    ax.set_title(titel, fontsize=12.5, fontweight="bold", color=DUNKEL, loc="left", pad=14)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(colors="#4A4A4A", labelsize=9, left=False)
    ax.grid(axis="x", color="#E4E9ED", lw=0.9)
    ax.set_axisbelow(True)

axL.annotate(f"Die letzten 28 bar:\nPumpe {wp:.1f} statt Verdichter {P3_W[2][1]:.1f} kJ/kg",
             (W2 - wp / 2, 1), (W2 * 0.30, 1.44), fontsize=10, color=GRUEN,
             fontweight="bold", ha="center",
             arrowprops=dict(arrowstyle="->", color=GRUEN, lw=1.4))
axL.text(0, -0.44, f"Pfad 2 spart {(1 - W2/W3)*100:.0f} % Wellenarbeit — "
                   f"{W2 * M_DOT / 1000:.2f} MW gegenüber {W3 * M_DOT / 1000:.2f} MW bei 100.000 Nm³/h.",
         fontsize=10, color=DUNKEL, fontweight="bold")
axR.text(0, -0.44, f"Kühlen muss man ohnehin: der Unterschied beträgt nur "
                   f"{abs(Q3 - Q2):.0f} kJ/kg oder {abs(Q3-Q2)/Q3*100:.0f} %.",
         fontsize=10, color=DUNKEL, fontweight="bold")
axR.text(0, 1.33, "Wärme geht an Kühlwasser oder Luftkühler, nicht an die Welle.",
         fontsize=9.5, color="#4A4A4A", style="italic")
from matplotlib.patches import Patch
axR.legend(handles=[Patch(facecolor=HELLBLAU, label="Zwischenkühler zwischen den Stufen"),
                    Patch(facecolor=BLAU, label="Verflüssiger bzw. Nachkühler am Ende")],
           frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1.0, 1.10))

fig.text(0.006, 0.028,
         "Randbedingungen: Anlieferung 30 bar / 15 °C · Ziel 107,6 bar am Bohrlochkopf · η_s = 0,80 · "
         "Zwischenkühlung 40 °C · Verflüssigung 80 bar / 25 °C · 100.000 Nm³/h = 54,9 kg/s",
         fontsize=8.5, color="#4A4A4A")
fig.text(0.006, 0.005,
         "Stoffdaten CoolProp / Span & Wagner (1996) · eigene Rechnung · Blatt 04 und 05 der Obertageauslegung",
         fontsize=8, color="#7A7A7A")
fig.tight_layout(rect=[0, 0.065, 1, 1.0])
fig.savefig("abb_gaspfad_vergleich.png", dpi=170)
print("gespeichert: abb_gaspfad_vergleich.png")

print(f"\nPfad 2  Wellenarbeit {W2:6.2f} kJ/kg | Kühllast {Q2:6.1f} kJ/kg")
print(f"Pfad 3  Wellenarbeit {W3:6.2f} kJ/kg | Kühllast {Q3:6.1f} kJ/kg")
print(f"Ersparnis Wellenarbeit {(1-W2/W3)*100:.1f} % | Mehrbedarf Kühlung {(Q2/Q3-1)*100:+.1f} %")
