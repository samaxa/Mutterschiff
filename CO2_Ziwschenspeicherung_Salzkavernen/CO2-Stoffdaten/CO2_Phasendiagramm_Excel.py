"""
Erzeugt eine Excel-Datei mit allen Daten fuer das CO2-p-T-Phasendiagramm
und einem bereits eingebauten Streudiagramm (logarithmische Druckachse).

So kann das Phasendiagramm in Excel nachgebildet / geprueft werden.

Ausfuehren mit Python 3.10:
    py -3.10 CO2_Phasendiagramm_Excel.py

Ergebnis:
    CO2_Phasendiagramm.xlsx
        Blatt "Daten"     - alle Kurvenpunkte als Spalten
        Blatt "Diagramm"  - fertiges p-T-Diagramm
"""

import numpy as np
from CoolProp.CoolProp import PropsSI
import openpyxl
from openpyxl.chart import ScatterChart, Reference, Series
from openpyxl.chart.marker import Marker
from openpyxl.chart.axis import ChartLines


# ============================================================
# 1) Referenzpunkte
# ============================================================

T_triple_K = 216.592
P_triple_bar = 5.1795
T_crit_K = PropsSI("Tcrit", "CO2")
P_crit_bar = PropsSI("Pcrit", "CO2") / 1e5


# ============================================================
# 2) Phasengrenzen (gleiche Formeln wie im Diagramm-Skript)
# ============================================================

def sublimation_pressure_bar(T_K):
    T_K = np.asarray(T_K, dtype=float)
    a1, a2, a3 = -14.740846, 2.4327015, -5.3061778
    th = 1.0 - T_K / T_triple_K
    ex = T_triple_K / T_K * (a1 * th + a2 * th**1.9 + a3 * th**2.9)
    return P_triple_bar * np.exp(ex)


def melting_pressure_bar(T_K):
    T_K = np.asarray(T_K, dtype=float)
    a1, a2 = 1955.5390, 2055.4593
    x = T_K / T_triple_K - 1.0
    return P_triple_bar * (1.0 + a1 * x + a2 * x**2)


# Sublimationslinie: -100 °C bis Tripelpunkt
T_sub_K = np.linspace(173.15, T_triple_K, 50)
T_sub_C = T_sub_K - 273.15
P_sub = sublimation_pressure_bar(T_sub_K)

# Saettigungslinie: Tripelpunkt bis kritischer Punkt
T_sat_in = np.linspace(T_triple_K + 0.01, T_crit_K - 0.01, 60)
P_sat_in = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") / 1e5 for T in T_sat_in])
T_sat_K = np.concatenate(([T_triple_K], T_sat_in, [T_crit_K]))
P_sat = np.concatenate(([P_triple_bar], P_sat_in, [P_crit_bar]))
T_sat_C = T_sat_K - 273.15

# Schmelzlinie: Tripelpunkt bis 250 bar
a1, a2 = 1955.5390, 2055.4593
tgt = 250.0 / P_triple_bar - 1.0
x_top = (-a1 + np.sqrt(a1**2 + 4.0 * a2 * tgt)) / (2.0 * a2)
T_melt_K = np.linspace(T_triple_K, T_triple_K * (1.0 + x_top), 30)
T_melt_C = T_melt_K - 273.15
P_melt = melting_pressure_bar(T_melt_K)


# ============================================================
# 3) Entspannungspfad (deine Excel-Werte) + Phase/Dampfanteil
# ============================================================

P_path = np.array([210, 200, 190, 180, 170, 160, 150, 140, 130, 120,
                   110, 100, 90, 80, 70, 60, 50, 40, 30], dtype=float)
T_path = np.array([50.0, 49.299, 48.537, 47.707, 46.801, 45.809, 44.72,
                   43.518, 42.185, 40.697, 39.021, 37.113, 34.9, 32.26,
                   28.683, 21.978, 14.284, 5.3, -5.552], dtype=float)

h0 = PropsSI("H", "T", 50 + 273.15, "P", 210e5, "CO2")   # Prozess-Enthalpie
Q_path = []
for p in P_path:
    q = PropsSI("Q", "P", p * 1e5, "H", h0, "CO2")
    Q_path.append(q if 0 <= q <= 1 else "")   # leer = einphasig


# ============================================================
# 4) Excel-Datei aufbauen
# ============================================================

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Daten"

# Spaltenpaare: jede Kurve bekommt T [°C] und p [bar]
# A/B Sublimation | C/D Saettigung | E/F Schmelze | G/H Pfad(+I Q) |
# K/L Tripel | N/O kritisch
headers = {
    1: "Sublim. T[°C]", 2: "Sublim. p[bar]",
    4: "Sätt. T[°C]", 5: "Sätt. p[bar]",
    7: "Schmelz T[°C]", 8: "Schmelz p[bar]",
    10: "Pfad T[°C]", 11: "Pfad p[bar]", 12: "Dampfanteil Q",
    14: "Tripel T[°C]", 15: "Tripel p[bar]",
    17: "krit. T[°C]", 18: "krit. p[bar]",
}
for col, txt in headers.items():
    ws.cell(row=1, column=col, value=txt).font = openpyxl.styles.Font(bold=True)


def write_pair(col_t, col_p, T, P):
    for i, (t, p) in enumerate(zip(T, P), start=2):
        ws.cell(row=i, column=col_t, value=round(float(t), 3))
        ws.cell(row=i, column=col_p, value=round(float(p), 4))


write_pair(1, 2, T_sub_C, P_sub)
write_pair(4, 5, T_sat_C, P_sat)
write_pair(7, 8, T_melt_C, P_melt)

# Pfad inkl. Dampfanteil
for i, (t, p, q) in enumerate(zip(T_path, P_path, Q_path), start=2):
    ws.cell(row=i, column=10, value=round(float(t), 3))
    ws.cell(row=i, column=11, value=round(float(p), 3))
    ws.cell(row=i, column=12, value=(round(q, 3) if q != "" else None))

# Einzelpunkte
ws.cell(row=2, column=14, value=round(T_triple_K - 273.15, 3))
ws.cell(row=2, column=15, value=round(P_triple_bar, 4))
ws.cell(row=2, column=17, value=round(T_crit_K - 273.15, 3))
ws.cell(row=2, column=18, value=round(P_crit_bar, 4))

# Spaltenbreite etwas huebscher
for col in range(1, 19):
    ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 13


# ============================================================
# 5) Streudiagramm mit logarithmischer Druckachse
# ============================================================

chart = ScatterChart()
chart.title = "CO2 p-T-Phasendiagramm (isenthalpe Entspannung)"
chart.x_axis.title = "Temperatur (°C)"
chart.y_axis.title = "Druck (bar, log.)"
chart.height = 16
chart.width = 26
chart.style = 2

# Achsen sichtbar + Gitter
chart.x_axis.delete = False
chart.y_axis.delete = False
chart.x_axis.majorGridlines = ChartLines()
chart.y_axis.majorGridlines = ChartLines()

# logarithmische Druckachse
chart.y_axis.scaling.logBase = 10
chart.y_axis.scaling.min = 0.1
chart.y_axis.scaling.max = 250
chart.x_axis.scaling.min = -100
chart.x_axis.scaling.max = 60
# Achsenkreuz unten/links erzwingen (sonst schneidet x bei 0)
chart.x_axis.crosses = "min"
chart.y_axis.crosses = "min"


def add_curve(col_t, col_p, n_rows, name, hexcolor, line=True, marker=False):
    xref = Reference(ws, min_col=col_t, min_row=2, max_row=1 + n_rows)
    yref = Reference(ws, min_col=col_p, min_row=2, max_row=1 + n_rows)
    s = Series(yref, xref, title=name)
    if marker:
        s.marker = Marker(symbol="circle", size=6)
        s.marker.graphicalProperties.solidFill = hexcolor
        s.marker.graphicalProperties.line.solidFill = hexcolor
    else:
        s.marker = Marker(symbol="none")
    if line:
        s.graphicalProperties.line.solidFill = hexcolor
        s.graphicalProperties.line.width = 28000      # ~2.2 pt (EMU)
    else:
        s.graphicalProperties.line.noFill = True
    s.smooth = False
    chart.series.append(s)


add_curve(1, 2, len(T_sub_C), "Sublimationslinie", "303030")
add_curve(4, 5, len(T_sat_C), "Sättigungslinie", "0B4F8A")
add_curve(7, 8, len(T_melt_C), "Schmelzlinie", "5D3A7E")
add_curve(10, 11, len(T_path), "Entspannungspfad", "C43C39", line=True, marker=True)
add_curve(14, 15, 1, "Tripelpunkt", "000000", line=False, marker=True)
add_curve(17, 18, 1, "kritischer Punkt", "C00000", line=False, marker=True)

ws_chart = wb.create_sheet("Diagramm")
ws_chart.add_chart(chart, "B2")

out = "CO2_Phasendiagramm.xlsx"
wb.save(out)
print(f"gespeichert: {out}")
print("  Blatt 'Daten'    -> alle Kurvenpunkte zum Nachpruefen")
print("  Blatt 'Diagramm' -> fertiges p-T-Phasendiagramm")
