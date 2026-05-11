import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df_data = pd.read_csv("Übungen_Max/Input/data_PyPSA_06.csv")

wind_data = df_data['wind_infeed']
electric_load = df_data['electric_load_kW']
heat_data = df_data['Heizlast_kW']
max_electrical_load = electric_load.max()

#marginal costs
electricity_rate =   0.4 #€/kWh
gas_rate         =  0.14 #€/kWh
 
 
#efficiencies
efficiency_electrolysis     = 0.65  #decimal
efficiency_fuel_cell        = 0.7   #decimal
fuel_cell_heat              = 0.25  #decimal
efficiency_hydrogen_heating = 0.95  #decimal
efficiency_gas_heating      = 0.95  #decimal
storage_loss                = 0.005 #decimal
 
 
#co2 emissions
co2_emissions_germany_electricity  = 0.375 #kg/kWh
co2_emissions_natural_gas          = 0.274 #kg/kWh
 
#capital costs
capital_cost_electrolysis     = 200  #€/kW  as annuity
capital_cost_fuel_cell        = 1000 #€/kW  as annuity
capital_cost_hydrogen_storage = 50   #€/kWh as annuity
capital_cost_hydrogen_heating = 10   #€/kW  as annuity
capital_cost_gas_heating      = 7    #€/kW  as annuity
capital_cost_wind             = 150  #€/kW  as annuity
capital_cost_heat_store       = 10   #€/kWh as annuity

grid_infeed = -0.06 #€/kWh infeed of wind energy
wind_p_nom_min = 4500 #kW
wind_p_nom_max = 9000 #kW
wind_p_max_pu = wind_data/wind_p_nom_min # per unit


# Netzwerk erstellen
network = pypsa.Network()
network.set_snapshots(range(8760))
 
#Buses
network.add('Bus', name = 'electricity')
network.add('Bus', name = 'wind_power')
network.add('Bus', name = 'hydrogen')
network.add('Bus', name = 'heat')
 
#Carriers
network.add('Carrier', name = 'german_electricity', 
            co2_emissions = co2_emissions_germany_electricity)
network.add('Carrier', name = 'natural_gas', 
            co2_emissions = co2_emissions_natural_gas)
 
#Generators
network.add('Generator', name = 'grid_power', bus = 'electricity',
           marginal_cost = electricity_rate, p_nom = max_electrical_load,
           carrier = 'german_electricity')
network.add('Generator', name = 'wind_tubine', bus = 'wind_power',
           p_nom_extendable = True, p_nom_min = wind_p_nom_min,
           p_max_pu = wind_p_max_pu, p_nom_max = wind_p_nom_max,
           capital_cost = capital_cost_wind, p_nom_mod = wind_p_nom_min)
network.add('Generator', name = 'grid_infeed', bus = 'wind_power',
           marginal_cost = grid_infeed, sign = -1, p_nom = wind_p_nom_max)
network.add('Generator', name = 'gas_heating', bus = 'heat',
            marginal_cost = gas_rate/efficiency_gas_heating, 
            capital_cost = capital_cost_gas_heating, p_nom_extendable = True,
           carrier = 'natural_gas', efficiency = efficiency_gas_heating)
 
 
#Links
network.add('Link', name = 'wind_self_consumption', bus0 = 'wind_power',
            bus1='electricity', p_nom = wind_p_nom_max)
network.add('Link', name = 'electrolysis', bus0 = 'wind_power',
           bus1 = 'hydrogen', p_nom_extendable = True, 
            capital_cost = capital_cost_electrolysis, 
            efficiency = efficiency_electrolysis)
network.add('Link', name = 'hydrogen_heating', 
            bus0 = 'hydrogen', bus1 ='heat',
            p_nom_extendable = True, 
            capital_cost = capital_cost_hydrogen_heating,
            efficiency = efficiency_hydrogen_heating)
network.add('Link', name = 'fuel_cell', bus0 = 'hydrogen',
           bus1= 'heat', bus2 = 'electricity',
           p_nom_extendable = True, 
            capital_cost = capital_cost_fuel_cell, 
            efficiency = fuel_cell_heat, 
            efficiency2 = efficiency_fuel_cell )
 
#Stores
network.add('Store', name = 'hydrogen_storage', bus = 'hydrogen',
           e_nom_extendable = True, 
            capital_cost = capital_cost_hydrogen_storage, e_cyclic = True)
network.add('Store', name = 'heat_store', bus = 'heat', 
           e_nom_extendable = True, capital_cost = capital_cost_heat_store,
           standing_loss = storage_loss, e_cyclic = True)
 
#Loads
network.add('Load', name = 'electrical_load', bus = 'electricity', 
            p_set = electric_load)
network.add('Load', name = 'thermal_load', bus = 'heat', 
            p_set = heat_data)
 
#Global Constraint
network.add('GlobalConstraint', name = 'co2-limit', 
           sense = '<=', carrier_attribute = 'co2_emissions',
           constant = np.inf)


network.optimize()

network.generators_t.p.plot()
plt.show()