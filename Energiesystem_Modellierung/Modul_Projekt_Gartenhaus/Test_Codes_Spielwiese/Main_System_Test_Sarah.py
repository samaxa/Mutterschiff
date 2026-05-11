# ======================================
# Import der Bibliotheken
# ======================================
import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
xarray as xr
from linopy import Model

# ======================================
# Nutrition System: Linus, Sarah, Recycling Alex
# ======================================
# Eingabedaten laden

# Zeitachse & Netzwerk
snapshots = pd.date_range('2019-01-01', periods=8760, freq='H') # alles in stündlichen Werten
network = pypsa.Network()
network.set_snapshots(snapshots)


# Pflanzendaten einlesen - Zyklusdauer - Wasserprofil etc.

# ======================================
#Linopy Modell
#Python-Paket für lineare und gemischt-ganzzahlige Optimierung mit n-dimensionalen, beschrifteten Daten
# ======================================

months = pd.period_range("2019-01", "2019-12", freq="M").to_timestamp() # Das setzt die Zeitachsen
crops = ["A", "B", "C"] #A=Tomate, B=Gurke, C= Paprika

T = xr.IndexVariable("t", months)
C = xr.IndexVariable("c", crops)

# Nutritionprofil - Pflanzenproduktion - Energie die die Pflanze liefert - Linus
# Tabelle die alle Pflanzen angibt und ihre Daten enthält - Kalorien, Wasserbedarf, Erntezyklus, Ernteindex, Nährstoffe die geliefert werden etc.
df_Nutritionprofile = pd.read_csv('Input/nutrition_load.csv', sep=';', decimal='.')

# Kalorienverbrauch Menschen pro Tag - stündlich
df_Nutrition_load = df_Nutritionprofile['nut_Load']

# Wasserprofil wird erstellt
# Energieverbrauch Wasserpumpe

# ======================================
#Recycling Alex
# ======================================
# Recycling - Wasser, Biomasse
df_Wasteprofile = pd.read_csv('Input/waste_load.csv', sep=';', decimal='.')
#Muss Waste auch aus einem Generator gezogen werden?
network.add('Bus', name = 'waste') #Ziel:  gesamte Biomasse - essbare Biomasse in der Excel einlesen und subtrahieren
network.add('Bus', name = 'food') #Essbare Biomasse
network.add('Bus', name = 'water') #Bus um zum Wasser zu kommen
network.add('Bus', name = 'water_cycle') #Bus für den Wasserzyklus

#Storages setzen
network.add('Store', name = 'water_storage', bus = 'water_cycle', e_nom = 100, e_cyclic = True, standing_loss: 0.001)
network.add('Store', name = 'food_storage', bus = 'food',   # haben wir da nicht StorageUnit verwendet? Store berücksichtigt keine Lade-/Entladeleistung/ Verluste
           e_nom_extendable = True, e_cyclic = True)

#Links hinzufügen

network.add('Link', name = 'digestion', bus0 = 'food',bus1='waste', efficiency=0.7, p_nom_extendable = True) #Digestion ist ein Link der nur von Food zu Waste geht mit einer Recyclinrate von 70% (Mit Vergärung)
network.add('Link', name = 'recycling', bus0 = 'waste', bus1='water_cycle', efficiency=0.9, p_nom_extendable = True) #rWasseraufbereitung hat eine Recylingrate von 95%
network.add('Link', name = 'pump', bus0 = 'water_cycle', bus1='water', p_nom_extendable = True) #Verknüpfung zum Wasserbus


# Multiliks

# Storages, Begrenzungen in den einzelnen Schritten

# Optimieren der besten Pflanzen - optimieren auf geringster Energieverbrauch

# Lastprofile erzeugen - Strom und Wasser
# - Pflanzenprofil das optimiert wurde - Energieverbrauch stündlich erstellen


# ======================================
# Energiesystem: Max
# ======================================
# Erzeugung reinladen:
# PV
df_Erzeugung = pd.read_csv('Input/ninja_pv_83.2571_-33.3694_uncorrected.csv', sep=';', decimal='.')
df_PV_Erzeugung = df_Erzeugung['electricity']

# Plot PV-Erzeugung
df_PV_Erzeugung.plot(title="PV-Erzeugungsprofil")
plt.show()

# Wind falls Pv nicht reicht
df_Erzeugung = pd.read_csv('Input/....csv', sep=';', decimal='.')
df_Wind_Erzeugung = df_Erzeugung['electricity']


# ======================================
# Parameter definieren falls nötig:
# ======================================
zinssatz = 0.02

# PV
lebensdauer_pv = 20
invest_kosten_pv = 1000
annuitaet_pv = invest_kosten_pv * ((1+zinssatz)**lebensdauer_pv) * zinssatz / ((1+zinssatz)**lebensdauer_pv - 1)

# Batterie
lebensdauer_batterie = 20
roundtrip_eff_batterie = 0.95
invest_kosten_batterie = 750
annuitaet_batterie = invest_kosten_batterie * ((1+zinssatz)**lebensdauer_batterie) * zinssatz / ((1+zinssatz)**lebensdauer_batterie - 1)

# Wärmepumpe (Platzhalter COP)
COP = 3.0

# ======================================
# Elektrisches System
# ======================================
# Nach Kosten optimieren
# Max Code erweitern
#PV:
network.add('Bus', name = 'electricity')

network.add('Generator', name = 'PV', bus = 'electricity',
            p_nom_extendable = True,
            capital_cost = annuitaet_pv,            # Investitionskosten - Annuität berechnen für die Lebensdauer? nötig?
            p_max_pu = df_PV_Erzeugung)

network.add('Load', name = 'el_Load', bus = 'electricity', p_set = df_Electrical_load)

network.add("StorageUnit", name = 'battery_store', bus = 'electricity',
            p_nom_extendable = True,                            #optimieren Lassen
            capital_cost = annuitaet_batterie,                  #fixed period costs of extending P_nom/ jährliche investkosten pro kW
            max_hours = 1,                                      #max. state of charge capacity in terms of hours at full output capacity p_nom/ std in Vollast
            efficiency_store = roundtrip_eff_batterie**0.5,     #Wirkungsgrad beim Laden- Wurzel aus Roundtrip Effizienz weil : n-store = n_dispatch = n_roundtrip**0.5
            efficiency_dispatch = roundtrip_eff_batterie**0.5)

# Wind erweiterung
# ...

# ======================================
# Thermisches System
# ======================================
# Linus Code HP erweitern
network.add('Bus', name = 'thermal')
network.add("Load", "heat_Load", bus="heat", p_set= df_Heat_load)

# Wärmepumpe (Link) - Strom zu Wärme
network.add("Link", "HP",
            bus0="electricity",   # Strom-Eingang
            bus1="heat",          # Wärme-Ausgang
            p_nom_extendable=True,
            efficiency=COP)
network.add("Store",name = "thermal_store", bus = "thermal", e_nom_extendable = True, standing_loss = 0.002)


# ======================================
# Optimierung
# ======================================
network.optimize(solver_name='gurobi')

# ======================================
# Ergebnisse ausgeben
# ======================================
for comp, name, att in [
    ("generators", "PV", "p_nom_opt"),
    ("storage_units", "battery_store", "p_nom_opt"),
    ("links", "HP", "p_nom_opt"),
    ("stores", "thermal_store", "e_nom_opt"),
    ("stores", "food_storage", "e_nom_opt")
]:
    df = getattr(network, comp)
    print(f"{name} {att} = {df.at[name, att]}")