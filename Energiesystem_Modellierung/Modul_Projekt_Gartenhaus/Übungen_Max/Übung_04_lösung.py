import pandas as pd
import numpy as np  
import pypsa


df_data = pd.read_csv("Übungen_Max/Input/data_PyPSA_04.csv")


boiler_p_nom        = np.inf
boiler_eff          = 0.85
gas_rate            = 0.123 #€/kWh
 
electricity_rate    = 0.409 #€/kWh
grid_p_nom          = 15    #kW
 
interest_rate       = 0.02
 
pv_invest           = 1000  #€/kWp
pv_lifespan         = 25    #Jahre
pv_annuity          = pv_invest*((1+interest_rate)**pv_lifespan)*interest_rate/((1+interest_rate)**pv_lifespan-1)
pv_p_per_m2         = 0.2   #kWp/m2
 
heating_rod_eff     = 0.99  #Effizienz des Heizstabes
heating_rod_p_nom   = 3     #Leistung des Heizstabes in kW
 
col_invest          = 600   #€/kW_th (Spitzenlast bei G = 1000 W/m2 und 35° Neigung Südausrichtung)
col_lifespan        = 20    #Jahre
col_annuity         = col_invest*((1+interest_rate)**col_lifespan)*interest_rate/((1+interest_rate)**col_lifespan-1)
col_p_per_m2        = 0.805 #kWp_th/m2 (Bei 35° Dachneigung Südseite)
 
heat_store_loss     = 0.005
heat_store_e_nom    = 8.55   # kWh (entspricht einem 300 l Pufferspeicher bei einer Temperaturspreizung von 25 K)


network = pypsa.Network()
network.set_snapshots(df_data.index)
 
network.add('Bus', name = 'thermal')
network.add('Bus', name = 'electricity')
 
network.add('Load', name = 'heating_load', 
            bus = 'thermal', 
            p_set = df_data["heat_load"])
network.add('Load', name = 'electrical_load', 
            bus = 'electricity', 
            p_set = df_data["electrical_load"])
 
 
network.add('Generator', name = 'grid',
            bus = 'electricity',
            p_nom = grid_p_nom,
            marginal_cost = electricity_rate)
network.add('Generator',  name = 'boiler',
            bus = 'thermal', 
            p_nom = boiler_p_nom, 
            marginal_cost = gas_rate/boiler_eff)
network.add('Generator', name = 'PV',
            bus = 'electricity', 
            p_nom_extendable = True, 
            capital_cost = pv_annuity, 
            p_max_pu = df_data["PV"])
network.add('Generator', name = 'collector', 
            bus = 'thermal', 
            p_nom_extendable = True, 
            capital_cost = col_annuity, 
            p_max_pu = df_data["solar_thermal_eff"])
 
network.add('Link', name = 'heating_rod',
            bus0 = 'electricity', 
            bus1 = 'thermal', 
            p_nom = heating_rod_p_nom,  
            efficiency = heating_rod_eff)
 
network.add('Store',  name = 'heat_store',
            bus = 'thermal', 
            e_nom = heat_store_e_nom, 
            standing_loss = heat_store_loss)


network.optimize()

print("PV: \n",round(network.generators.p_nom_opt.PV,),"kWp \n", round(network.generators.p_nom_opt.PV / pv_p_per_m2,2),"m2")
print("Flachkollektor: \n",round(network.generators.p_nom_opt.collector,2),"max. kW_th \n",round(network.generators.p_nom_opt.collector / col_p_per_m2,2),"m2")