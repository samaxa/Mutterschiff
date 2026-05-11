import pypsaheat as ph
import pandas as pd
import numpy as np

# Rohrverluste über Link darstellen?
#  PV hinzufügen
#  Batteriespeicher
#
# allgemeine Hausversorgung vs. Wärmepumpe Fußbodenheizung
# Verschiedene
# z. B.:
# 6 Wohneinheiten a 120 m²
# Gesamtwohnfläche: ca. 720 m²

# ------------------------------------------------------------
# 1) Allgemeine Einstellungen
# ------------------------------------------------------------

# Wir simulieren ein Jahr in Stundenauflösung
N_HOURS = 8760
snapshots = range(N_HOURS)

# HeatNetwork anlegen und Snapshots setzen
n = ph.HeatNetwork()
n.set_snapshots(snapshots)

# Lasten laden (Bspw. Raumwärmelast, Warmwasserlast in kWh)


df = pd.read_csv(
    "/Input_Data/Lastprofil.csv",
    sep=";",
    decimal=",",
    parse_dates=["Zeit"],
    dayfirst=True
)



df = pd.read_excel("mfh_heatprofile.xlsx") # mfh = Mehrfamilienhaus

p_space = df["Q_space_kW"]  # Wärmelast der Raumheizung (space heat)
p_dhw   = df["Q_dhw_kW"]    # Warmwasserlast (domestic hot water)

# ------------------------------------------------------------
# 2) Elektrisches System (wie im Test: Bus + Generator)
# ------------------------------------------------------------

# Strombus
n.add("Bus", "grid_el")

# Netz-Generator (Strombezug aus dem Netz)
# p_nom: max. elektrische Leistung [kW]
# marginal_cost: Strompreis [€/kWh] (Platzhalter)
n.add(
    "Generator",
    name="grid_import",
    bus="grid_el",
    p_nom=1e4,          # "groß genug", damit die Optimierung nicht an der Grenze hängt
    marginal_cost=0.30  # z.B. 0,30 €/kWh - villt noch dynamische Stromkosten?
)

# ------------------------------------------------------------
# 3) Umgebungstemperatur (T_amb) - DWD kostenlos Wetterdaten holen?
# ------------------------------------------------------------

df_weather = pd.read_excel("wetter_mfh_2022.xlsx")

T_amb = df_weather["T_amb"]    # Pandas Series, Temperatur ambient - Umgebungs Temperatur [°C]


# ------------------------------------------------------------
# 4) Wärmespeicher (HeatStore) wie in Übung 2
# ------------------------------------------------------------

# Konstant geschichteter Speicher:
# - constant="temperature"
# - T_layer: feste Temperaturschichten
# - T_return: Rücklauftemperatur
# - cyclic=True: Speicherzustand am Ende = am Anfang
n.add(
    "HeatStore",
    name="hs_mfh",              # # hs = heat store (Wärmespeicher)
    constant="temperature",
    height=2.0,                # Höhe [m] (Platzhalter)
    base=2.0,                  # Grundfläche [m²] → Volumen ~ 4 m³
    T_layer=[60, 50, 40, 30],  # Temperaturschichten [°C]
    T_return=30,               # Rücklauftemperatur [°C]
    V_initial=[0],             # initiales Volumen je Schicht = 0 m³
    cyclic=True,               # Anfangs- und Endzustand identisch (V_initial)
    T_amb=20.0,                # Umgebungstemperatur des Speichers [°C]
    U_wall=0.2                 # U-Wert der Dämmung [W/(m²*K)] (Platzhalter)
)

# ------------------------------------------------------------
# 5) Wärmepumpe (HeatPump)
# ------------------------------------------------------------

n.add(
    "HeatPump",
    name="hp_mfh",
    bus0="grid_el",        # elektrische Seite am Strombus
    heat_store="hs_mfh",   # thermische Seite am Wärmespeicher
    p_nom=20.0,            # maximale thermische Leistung [kW] (Platzhalter, später dimensionieren)
    T_source=T_amb,        # Quelltemperatur = Außentemperatur (Luft-Wasser-Wärmepumpe)
    heat_source="air"      # Luft als Quelle
)

# ------------------------------------------------------------
# 6) Elektrischer Heizstab (HeatingElement) als Backup
# ------------------------------------------------------------

n.add(
    "HeatingElement",
    name="backup_heater",
    bus0="grid_el",
    heat_store="hs_mfh",
    p_nom=20.0,    # max. elektrische Leistung [kW]
    efficiency=0.98
)

# ------------------------------------------------------------
# 7) Heizkörper vs. Fußbodenheizung über Heizkurve (flow_temperature)
# ------------------------------------------------------------

# Flag: True = Heizkörper, False = Fußbodenheizung
use_radiators = True  # kannst du einfach umschalten

if use_radiators:
    # typische Vorlauftemp. bei 0°C Außentemp. für Heizkörper
    T_at_0C = 55.0
else:
    # typische Vorlauftemp. bei 0°C Außentemp. für Fußbodenheizung
    T_at_0C = 35.0

T_gradient = 1.0  # wie stark die Vorlauftemperatur mit der Außentemp. steigt

# Heizkurve berechnen (PyPSA_heat-Funktion aus der Übung)
T_flow = ph.physics.flow_temperature(T_at_0C, T_gradient, T_amb) # erzeugt die Zeitreihe der Vorlauftemperatur, passend zur Außentemperatur:

# ------------------------------------------------------------
# 8) Wärmelasten (HeatLoad) – Raumwärme + Warmwasser
# ------------------------------------------------------------

# Raumwärme-Last mit temperaturabhängiger Anforderung
n.add(
    "HeatLoad",
    name="space_heat",
    heat_store="hs_mfh",
    p_set=p_space,   # Zeitreihe [kW] aus Excel
    T_demand=T_flow  # Zeitreihe der benötigten Vorlauftemperatur [°C]
)

# Warmwasser-Last (immer 60°C)
n.add(
    "HeatLoad",
    name="dhw",
    heat_store="hs_mfh",
    p_set=p_dhw,
    T_demand=60.0    # konstante Temperaturanforderung [°C]
)

# ------------------------------------------------------------
# 9) Optimierung
# ------------------------------------------------------------

# Erstmal "klassisch" wie in der Übung:
n.optimize(solver_name="gurobi")

# Wenn das später zu langsam wird:
# n.optimize.optimize_with_rolling_horizon(horizon=168, overlap=24)

# ------------------------------------------------------------
# 10) Speicher-Plot (wie in der Übung mit plot_stratified_heat_store)
# ------------------------------------------------------------

# Achtung: bei 8760 Stunden kann der Plot unübersichtlich werden.
# Du kannst z.B. nur jeden 24. Snapshot (einmal pro Tag) anzeigen:
sns_to_plot = list(range(0, N_HOURS, 24))

ph.plot.plot_stratified_heat_store(
    n,
    hs="hs_mfh",
    sns=sns_to_plot
)
