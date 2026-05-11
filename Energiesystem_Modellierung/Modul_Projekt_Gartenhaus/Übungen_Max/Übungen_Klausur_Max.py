import pypsa as py
import pandas as pd
import numpy as np


# ---- Beispiel-Daten laden ----
data_input = pd.read_csv("Übungen_Max/Input/data_PyPSA_04.csv")
print(data_input.head())


#Parameter
dachfläche = 20 #m²
p_nom_Netz = 15 #kW
Kaltkessel_eff = 0.85
Kaltkessel_p_nom = np.inf
Warmwasserspeicher_capacity = 8.55 #kWh
Warmwasserspeicher_loss = 0.005 #   pro Stunde
heating_rod_p_nom = 3 #kW
heating_rod_eff = 0.99
Strompreis = 0.409 #€/kWh
Gaspreis = 0.123    #€/kWh
interest_rate = 0.02 #2%

cost_pv = 1000 #€/kWp
lifetime_pv = 25 #Jahre
leistung_pv = 0.2 #kWp/m²
pv_annuity = cost_pv * ((1+interest_rate)**lifetime_pv) * interest_rate / ((1 + interest_rate)**lifetime_pv - 1)
#invest * ((1 + interest_rate)**lifespan) * interest_rate / ((1 + interest_rate)**lifespan - 1)

cost_kollektor = 600 #€/kWp
lifetime_kollektor = 20 #Jahre
leistung_kollektor = 0.805 #kWp/m²
kollektor_annuity = cost_kollektor * ((1+interest_rate)**lifetime_kollektor) * interest_rate / ((1 + interest_rate)**lifetime_kollektor - 1)


network = py.Network()
network.set_snapshots(data_input.index)
#Network aufbauen

network.add("Bus", "electricity")
network.add("Bus", "heat")

network.add("Load", "electricity_load", bus="electricity", p_set=data_input["electrical_load"])
network.add("Load", "heat_load", bus="heat", p_set=data_input["heat_load"])

network.add("Generator", "Netz", bus="electricity", p_nom=p_nom_Netz, marginal_cost=Strompreis)
network.add("Generator", "PV", bus="electricity", 
            p_nom_extendable=True,
            p_max_pu=data_input["PV"], 
            capital_cost=pv_annuity
        )

network.add("Generator", "Kollektor", bus="heat",
            p_nom_extendable=True,
            p_max_pu=data_input["solar_thermal_eff"], 
            capital_cost=kollektor_annuity
           )

network.add("Generator", "Kaltkessel", bus="heat",
            p_nom=Kaltkessel_p_nom,
            marginal_cost=Gaspreis / Kaltkessel_eff,
            )

network.add("Store", "Warmwasserspeicher", bus="heat",
            e_nom=Warmwasserspeicher_capacity,
            standing_loss=Warmwasserspeicher_loss,
            )

network.add("Link", "heating_rod", bus0="electricity", bus1="heat",
            p_nom=heating_rod_p_nom,
            efficiency=heating_rod_eff,)

network.optimize()

print("Optimale PV-Leistung [kWp]: ", network.generators.at["PV", "p_nom_opt"])
print("Optimale Kollektor-Leistung [kWp]: ", network.generators.at["Kollektor", "p_nom_opt"])
print("Gesamtkosten [€/a]: ", network.objective)
        

            
