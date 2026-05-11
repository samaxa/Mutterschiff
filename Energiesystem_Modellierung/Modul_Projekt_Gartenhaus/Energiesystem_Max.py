import pypsa
import pandas as pd


# ---- Beispiel-Daten laden ----
load_profile = pd.read_csv("Input/gesamt_lastprofil.csv", index_col=0, parse_dates=True)["Last [kW]"]
load_profile.index = pd.to_datetime("2019-" + load_profile.index, format="%Y-%d-%m %H:%M")

pv_profile = pd.read_csv("Input/ninja_pv_Köln.csv",sep=",", index_col=0, parse_dates=True, skiprows=3)["electricity"]
wind_profile = pd.read_csv("Input/ninja_wind_Köln.csv",sep=",", index_col=0, parse_dates=True, skiprows=3)["electricity"]



# ---- Netz aufsetzen ----
network = pypsa.Network()
network.set_snapshots(range(8760))
"""""
print(len(load_profile), len(network.snapshots))
print(len(pv_profile), len(network.snapshots))
print(len(wind_profile), len(network.snapshots))
"""
load_profile.index = network.snapshots
pv_profile.index = network.snapshots
wind_profile.index = network.snapshots


network.add("Carrier","solar")
network.add("Carrier","wind")  
network.add("Carrier","battery")  
network.add("Carrier","electricity")
# Bus
network.add("Bus", "Stromnetz", carrier="electricity")
network.add("Bus", "battery_bus", carrier="battery")  # Speicher-Bus

 

"""
print(network.carriers)
print(network.generators[["carrier","p_nom","p_nom_opt"]])

print(network.generators)
print(pv_profile.shape, wind_profile.shape)
print(network.snapshots.shape)
"""
# Last
network.add("Load","Verbrauch ",
            bus="Stromnetz",
            p_set=load_profile)

# PV-Generator
network.add("Generator","pv",
            bus="Stromnetz",
            p_nom=50,
            p_max_pu=pv_profile,
            capital_cost=200,     # €/kW
            marginal_cost=0,
            carrier="solar",
            p_nom_extendable=True)

# Wind-Generator
network.add("Generator","wind",
            bus="Stromnetz",
            p_nom=50,
            p_max_pu=wind_profile,
            capital_cost=800,    # €/kW
            marginal_cost=0,
            carrier="wind",
            p_nom_extendable=True)

# Speicher-Energie (MWh) → Store
network.add("Store",
            "battery",
            bus="battery_bus",
            e_cyclic=False,               # Anfang = Ende
            e_nom_extendable=True,       # Energiespeichergröße [MWh]
            capital_cost=2000,       # €/kWh → €/MWh (Beispiel: 200 €/kWh)
            marginal_cost=0,
            carrier="battery",
            efficiency_store=0.9,
            efficiency_dispatch=0.9)

# Speicher-Leistung (MW) → Links zwischen Busse
# Laden
network.add("Link",
            "charge_link",
            bus0="Stromnetz",
            bus1="battery_bus",
            p_nom_extendable=True,
            carrier="battery",  
            capital_cost=200,     # Ladeleistung optimierbar
            efficiency=0.95)             # zusätzliche Ladeverluste

# Entladen
network.add("Link",
            "discharge_link",
            bus0="battery_bus",
            bus1="Stromnetz",
            p_nom_extendable=True,  
            carrier="battery", 
            capital_cost=200,      
            efficiency=0.95)             # zusätzliche Entladeverluste)        # €/kW → €/MW


# ---- Optimierung ausführen ----

network.optimize()



# ---- Ergebnisse ----
print("Optimale PV-Leistung [MW]:", network.generators.p_nom_opt["pv"])
print("Optimale Wind-Leistung [MW]:", network.generators.p_nom_opt["wind"])
print("Speicher-Kapazität [MWh]:", network.stores.e_nom_opt["battery"])
print("Speicher-Ladeleistung [MW]:", network.links.p_nom_opt["charge_link"])
print("Speicher-Entladeleistung [MW]:", network.links.p_nom_opt["discharge_link"])
print("Gesamtkosten [€]:", network.objective)

# Zeitreihen exportieren
#network.generators_t.p.to_csv("generator_output.csv")
#network.stores_t.e.to_csv("storage_energy.csv")
