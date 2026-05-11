#%%
import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
#%%


# df_electric_load erstellen (LED-Beleuchtung mit 16h an, 500 W, und 8h aus, 0W)

from datetime import datetime, timedelta
# Startdatum
start_datetime = datetime(2025, 1, 1, 0, 0)
total_hours = 365 * 24

timestamps = []
power_values = []

current_time = start_datetime

for day in range(365):
    for hour in range(16):
        timestamps.append(current_time)
        power_values.append(500)
        current_time += timedelta(hours=1)

    for hour in range(8):
        timestamps.append(current_time)
        power_values.append(0)
        current_time += timedelta(hours=1)


df_electric_load = pd.DataFrame({
    'Timestamp': timestamps,
    'Power_W': power_values
})
#%%
# Parameter
pv_costs = 1200 # €/kWp
heat_storage_loss = 0.005 #decimal

pv_p_nom = 5  # z.B. 5 kW installierte PV-Leistung, Ergänzt damit code erstmal läuft



#%%
# Netzwerk erstellen
network = pypsa.Network()
network.set_snapshots(range(8760))

#Buses
network.add('Bus', name = 'electricity')
network.add('Bus', name = 'heat')
network.add('Bus', name = 'water')

#network.add('bus', name = 'nutrition')


#Carriers
network.add("Carrier", name="electricity")
network.add("Carrier", name="heat")
network.add("Carrier", name="water")

#network.add("Carrier", name="nutrition")


#Generators
network.add('Generator', name = 'pv', bus = 'electricity',
           marginal_cost = pv_costs, p_nom = pv_p_nom)

#Links
network.add('Link', name = 'heat_pump', bus0 = 'electricity',
            bus1='heat',
            efficiency=3.0,  # COP
            p_nom_extendable = True)
network.add('Link', name = 'water_pump', bus0 = 'electricity',
            bus1='water',  p_nom_extendable = True)


#Stores
network.add('Store', name = 'battery', bus = 'electricity',   # haben wir da nicht StorageUnit verwendet? Store berücksichtigt keine Lade-/Entladeleistung/ Verluste
           e_nom_extendable = True, e_cyclic = True)
#Batterie
#network.add("StorageUnit",
#    name="battery",
#    bus="electricity",
#    p_nom=5,                  # Max. Lade-/Entladeleistung in kW
#    p_nom_extendable=True,    # Optional: soll PyPSA optimale Größe berechnen?
#    max_hours=3,              # Kapazität = p_nom * max_hours → z.B. 15 kWh
#    efficiency_store=0.9,     # Ladewirkungsgrad
#    efficiency_dispatch=0.9,  # Entladewirkungsgrad
#    cyclic_state_of_charge=True
#)

network.add('Store', name = 'heat_store', bus = 'heat',
           e_nom_extendable = True,
           standing_loss = heat_storage_loss, e_cyclic = True)
#Wärmespeicher
#network.add("StorageUnit",
#    name="heat_store",
#    bus="heat",
#    p_nom_extendable=True,         # z.B. bis 5 kW Heiz-/Ladeleistung
#    max_hours=6,                   # z.B. 6 Stunden volle Leistung speichern
#    efficiency_store=0.95,         # realistische Speicherverluste
#    efficiency_dispatch=0.95,
#   standing_loss=heat_storage_loss,  # z.B. 0.005 pro Stunde
#    cyclic_state_of_charge=True
#)


network.add('Store', name = 'water_store', bus = 'water',
           p_nom_extendable = True, e_cyclic = True)

#Loads
network.add('Load', name = 'electrical_load', bus = 'electricity', p_set = list(df_electric_load['Power_W']), p_nom = pv_p_nom)


# network.add('Load', name = 'thermal_load', bus = 'heat', p_set = heat_data)
# network.add('Load', name = 'water_load', bus = 'water', p_set = water_data)

#%%
#Global Constraint
