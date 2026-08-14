import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.ticker import ScalarFormatter
from CoolProp.CoolProp import PropsSI


# ============================================================
# 1) Referenzpunkte von reinem CO2
# ============================================================

# Tripelpunkt nach Span und Wagner
T_triple_K = 216.592             # K
T_triple_C = T_triple_K - 273.15
P_triple_bar = 5.1795            # bar

# Kritischer Punkt aus CoolProp
T_critical_K = PropsSI("Tcrit", "CO2")
T_critical_C = T_critical_K - 273.15
P_critical_bar = PropsSI("Pcrit", "CO2") / 1e5


# ============================================================
# 2) Funktionen für die Phasengrenzen
# ============================================================

def sublimation_pressure_bar(T_K):
    """
    Sublimationsdruck von CO2:
    Phasengrenze fest <-> gasförmig.

    Gültiger Referenzbereich ungefähr:
    154 K bis zum Tripelpunkt bei 216.592 K.

    Ausgabe:
        Druck in bar
    """
    T_K = np.asarray(T_K, dtype=float)

    a1 = -14.740846
    a2 = 2.4327015
    a3 = -5.3061778

    theta = 1.0 - T_K / T_triple_K

    exponent = (
        T_triple_K / T_K
        * (
            a1 * theta
            + a2 * theta**1.9
            + a3 * theta**2.9
        )
    )

    return P_triple_bar * np.exp(exponent)


def melting_pressure_bar(T_K):
    """
    Schmelzdruck von CO2:
    Phasengrenze fest <-> flüssig.

    Ausgabe:
        Druck in bar
    """
    T_K = np.asarray(T_K, dtype=float)

    a1 = 1955.5390
    a2 = 2055.4593

    x = T_K / T_triple_K - 1.0

    return P_triple_bar * (
        1.0
        + a1 * x
        + a2 * x**2
    )


# ============================================================
# 3) Eigene Prozess-/Entspannungsdaten
# ============================================================

# WICHTIG:
# Die Reihenfolge entspricht der Prozessrichtung.
# Für eine Entspannung deshalb vom hohen zum niedrigen Druck.

T_path = np.array([
    80, 70, 60, 50, 40, 30, 20,
    10, 0, -10, -20, -30, -40, -50
], dtype=float)

P_path = np.array([
    160, 150, 140, 130, 120, 110, 100,
    90, 80, 70, 60, 50, 40, 30
], dtype=float)

if len(T_path) != len(P_path):
    raise ValueError(
        f"T_path enthält {len(T_path)} Werte, "
        f"P_path enthält aber {len(P_path)} Werte."
    )

if np.any(P_path <= 0):
    raise ValueError(
        "Alle Druckwerte müssen für die logarithmische "
        "Darstellung größer als 0 bar sein."
    )


# ============================================================
# 4) Plotgrenzen
# ============================================================

# Die Grenzen werden an die Prozessdaten angepasst
Tmin = min(-100.0, np.min(T_path) - 5)
Tmax = max(60.0, np.max(T_path) + 5)

Pmin = 0.1
Pmax = max(250.0, np.max(P_path) * 1.10)


# ============================================================
# 5) Sublimationslinie: fest <-> gasförmig
# ============================================================

# Für Tmin = -100 °C liegt die Temperatur noch im
# Gültigkeitsbereich der Span-Wagner-Korrelation.
T_sub_min_K = max(154.0, Tmin + 273.15)

T_sub_K = np.linspace(
    T_sub_min_K,
    T_triple_K,
    500
)

T_sub_C = T_sub_K - 273.15
P_sub_bar = sublimation_pressure_bar(T_sub_K)


# ============================================================
# 6) Sättigungslinie: flüssig <-> gasförmig
# ============================================================

# Nicht exakt an Tripel- und kritischem Punkt rechnen,
# um numerische Probleme in CoolProp zu vermeiden.
T_sat_inner_K = np.linspace(
    T_triple_K + 0.001,
    T_critical_K - 0.001,
    500
)

P_sat_inner_bar = np.array([
    PropsSI(
        "P",
        "T", T,
        "Q", 0,
        "CO2"
    ) / 1e5
    for T in T_sat_inner_K
])

# Tripel- und kritischen Punkt manuell ergänzen
T_sat_K = np.concatenate((
    [T_triple_K],
    T_sat_inner_K,
    [T_critical_K]
))

P_sat_bar = np.concatenate((
    [P_triple_bar],
    P_sat_inner_bar,
    [P_critical_bar]
))

T_sat_C = T_sat_K - 273.15


# ============================================================
# 7) Schmelzlinie: fest <-> flüssig
# ============================================================

# Temperatur berechnen, bei der die Schmelzlinie Pmax erreicht.
# Dazu wird die quadratische Gleichung analytisch gelöst.
a1_melt = 1955.5390
a2_melt = 2055.4593

target = Pmax / P_triple_bar - 1.0

x_top = (
    -a1_melt
    + np.sqrt(a1_melt**2 + 4.0 * a2_melt * target)
) / (2.0 * a2_melt)

T_melt_top_K = T_triple_K * (1.0 + x_top)

T_melt_K = np.linspace(
    T_triple_K,
    T_melt_top_K,
    400
)

T_melt_C = T_melt_K - 273.15
P_melt_bar = melting_pressure_bar(T_melt_K)


# ============================================================
# 8) Plot erstellen
# ============================================================

fig, ax = plt.subplots(figsize=(14, 8))


# ------------------------------------------------------------
# Gasförmige Region
# ------------------------------------------------------------

gas_vertices = [
    (Tmin, Pmin),
    (Tmax, Pmin),
    (Tmax, P_critical_bar),
    (T_critical_C, P_critical_bar),
]

# Vom kritischen Punkt entlang der Sättigungslinie
# zurück zum Tripelpunkt
gas_vertices += list(zip(
    T_sat_C[::-1],
    P_sat_bar[::-1]
))

# Vom Tripelpunkt entlang der Sublimationslinie
# zurück zur tiefsten Temperatur
gas_vertices += list(zip(
    T_sub_C[::-1],
    P_sub_bar[::-1]
))

gas_patch = Polygon(
    gas_vertices,
    closed=True,
    facecolor="#b9d7f0",
    edgecolor="none",
    alpha=0.55,
    label="gasförmig"
)

ax.add_patch(gas_patch)


# ------------------------------------------------------------
# Feststoffregion / Trockeneis
# ------------------------------------------------------------

solid_vertices = [
    (Tmin, Pmax),
    (T_melt_C[-1], P_melt_bar[-1]),
]

# Von oben entlang der Schmelzlinie zum Tripelpunkt
solid_vertices += list(zip(
    T_melt_C[::-1],
    P_melt_bar[::-1]
))

# Vom Tripelpunkt entlang der Sublimationslinie nach links
solid_vertices += list(zip(
    T_sub_C[::-1],
    P_sub_bar[::-1]
))

solid_patch = Polygon(
    solid_vertices,
    closed=True,
    facecolor="#a8a8c8",
    edgecolor="none",
    alpha=0.55,
    label="fest / Trockeneis"
)

ax.add_patch(solid_patch)


# ------------------------------------------------------------
# Flüssige Region
# ------------------------------------------------------------

liquid_vertices = [
    (T_melt_C[-1], Pmax),
    (T_critical_C, Pmax),
]

# Vom oberen Rand über den kritischen Punkt
# entlang der Sättigungslinie zum Tripelpunkt
liquid_vertices += list(zip(
    T_sat_C[::-1],
    P_sat_bar[::-1]
))

# Vom Tripelpunkt entlang der Schmelzlinie nach oben
liquid_vertices += list(zip(
    T_melt_C,
    P_melt_bar
))

liquid_patch = Polygon(
    liquid_vertices,
    closed=True,
    facecolor="#b8d8a8",
    edgecolor="none",
    alpha=0.55,
    label="flüssig"
)

ax.add_patch(liquid_patch)


# ------------------------------------------------------------
# Superkritische Region
# ------------------------------------------------------------

supercritical_vertices = [
    (T_critical_C, P_critical_bar),
    (Tmax, P_critical_bar),
    (Tmax, Pmax),
    (T_critical_C, Pmax)
]

supercritical_patch = Polygon(
    supercritical_vertices,
    closed=True,
    facecolor="#f4c7a1",
    edgecolor="none",
    alpha=0.55,
    label="superkritisch"
)

ax.add_patch(supercritical_patch)


# ============================================================
# 9) Phasengrenzlinien
# ============================================================

ax.plot(
    T_sub_C,
    P_sub_bar,
    color="#303030",
    linewidth=2.2,
    label="Sublimationslinie"
)

ax.plot(
    T_sat_C,
    P_sat_bar,
    color="#0b4f8a",
    linewidth=2.5,
    label="Sättigungslinie"
)

ax.plot(
    T_melt_C,
    P_melt_bar,
    color="#5d3a7e",
    linewidth=2.2,
    label="Schmelzlinie"
)


# ============================================================
# 10) Tripelpunkt und kritischer Punkt
# ============================================================

ax.scatter(
    T_triple_C,
    P_triple_bar,
    color="black",
    s=70,
    zorder=10
)

ax.annotate(
    (
        f"Tripelpunkt\n"
        f"{T_triple_C:.1f} °C | {P_triple_bar:.2f} bar"
    ),
    xy=(T_triple_C, P_triple_bar),
    xytext=(-48, 8.5),
    arrowprops=dict(
        arrowstyle="->",
        color="black"
    ),
    fontsize=10,
    zorder=10
)

ax.scatter(
    T_critical_C,
    P_critical_bar,
    color="#c00000",
    s=70,
    zorder=10
)

ax.annotate(
    (
        f"Kritischer Punkt\n"
        f"{T_critical_C:.1f} °C | {P_critical_bar:.1f} bar"
    ),
    xy=(T_critical_C, P_critical_bar),
    xytext=(38, 48),
    arrowprops=dict(
        arrowstyle="->",
        color="#c00000"
    ),
    fontsize=10,
    color="#c00000",
    zorder=10
)


# Normaler Sublimationspunkt bei ungefähr 1 bar
T_normal_sub_C = -78.46
P_normal_sub_bar = sublimation_pressure_bar(
    T_normal_sub_C + 273.15
)

ax.scatter(
    T_normal_sub_C,
    P_normal_sub_bar,
    color="#333333",
    s=40,
    zorder=10
)

ax.annotate(
    "Sublimation bei 1,013 bar\n≈ −78,5 °C",
    xy=(T_normal_sub_C, P_normal_sub_bar),
    xytext=(-72, 0.45),
    arrowprops=dict(
        arrowstyle="->",
        color="#333333"
    ),
    fontsize=9
)


# ============================================================
# 11) Prozess-/Entspannungspfad
# ============================================================

ax.plot(
    T_path,
    P_path,
    "-o",
    color="#c43c39",
    linewidth=3,
    markersize=6,
    label="Entspannungspfad",
    zorder=12
)

# Pfeile zeigen die Prozessrichtung
for i in range(0, len(T_path) - 1, 2):
    ax.annotate(
        "",
        xy=(T_path[i + 1], P_path[i + 1]),
        xytext=(T_path[i], P_path[i]),
        arrowprops=dict(
            arrowstyle="->",
            color="#8b1a1a",
            linewidth=1.5
        ),
        zorder=13
    )


# ============================================================
# 12) Phasenbereiche beschriften
# ============================================================

ax.text(
    -90,
    30,
    "fest\nTrockeneis",
    fontsize=15,
    ha="center",
    color="#35355f",
    bbox=dict(
        facecolor="white",
        alpha=0.65,
        edgecolor="none"
    )
)

ax.text(
    -20,
    1.1,
    "gasförmig",
    fontsize=15,
    ha="center",
    color="#164a73",
    bbox=dict(
        facecolor="white",
        alpha=0.65,
        edgecolor="none"
    )
)

ax.text(
    -15,
    55,
    "flüssig",
    fontsize=15,
    ha="center",
    color="#3f702d",
    bbox=dict(
        facecolor="white",
        alpha=0.65,
        edgecolor="none"
    )
)

ax.text(
    52,
    145,
    "superkritisch",
    fontsize=15,
    ha="center",
    color="#a3480b",
    bbox=dict(
        facecolor="white",
        alpha=0.65,
        edgecolor="none"
    )
)


# ============================================================
# 13) Achsen und Darstellung
# ============================================================

ax.set_xlim(Tmin, Tmax)
ax.set_ylim(Pmin, Pmax)

# Logarithmische Druckachse:
# notwendig, um 0,1 bis 250 bar sinnvoll darzustellen.
ax.set_yscale("log")

ax.set_xlabel(
    "Temperatur (°C)",
    fontsize=13
)

ax.set_ylabel(
    "Druck (bar, logarithmische Skala)",
    fontsize=13
)

ax.set_title(
    "CO$_2$-Entspannung im p-T-Phasendiagramm",
    fontsize=18
)

# Sinnvolle Druckmarken
pressure_ticks = [
    0.1,
    1.0,
    P_triple_bar,
    10.0,
    P_critical_bar,
    100.0,
    250.0
]

pressure_ticks = [
    value for value in pressure_ticks
    if Pmin <= value <= Pmax
]

ax.set_yticks(pressure_ticks)
ax.yaxis.set_major_formatter(ScalarFormatter())

ax.grid(
    True,
    which="both",
    alpha=0.25
)

ax.legend(
    loc="upper left",
    bbox_to_anchor=(1.02, 1.0),
    borderaxespad=0,
    fontsize=9,
    framealpha=0.9,
    ncol=1
)

plt.tight_layout()

# Optional als hochauflösende Grafik speichern:
# plt.savefig(
#     "CO2_Phasendiagramm_mit_Entspannung.png",
#     dpi=300,
#     bbox_inches="tight"
# )

plt.show()