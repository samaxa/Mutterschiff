import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

network = pypsa.Network()

#Busse hinzufügen

network.add('Bus', name = 'waste')
network.add('Bus', name = 'food')
network.add('Bus', name = 'nutrition') # ist nur ein zusatzbus
network.add('Bus', name = 'water')
network.add('Bus', name = 'water_cycle') #Zusätzlicher Bus für das Recycelte Wasser

#Storages hinzufügen

network.add('Store', name = 'water_storage', bus = 'water_cycle', e_nom = 100, e_cyclic = True, standing_loss: 0.001)
network.add('Store', name = 'food_storage', bus = 'food',   # haben wir da nicht StorageUnit verwendet? Store berücksichtigt keine Lade-/Entladeleistung/ Verluste
           e_nom_extendable = True, e_cyclic = True)

#Links hinzufügen

network.add('Link', name = 'digestion', bus0 = 'food',bus1='waste', efficiency=3.0, p_nom_extendable = True) #Digestion ist ein Link der nur von Food zu Waste geht mit einer Recyclinrate von xy%
network.add('Link', name = 'recycling', bus0 = 'waste', bus1='nutrition', efficiency=3.0, p_nom_extendable = True) #recycling ist ein link, der nur von Waste aus zu Nutrition geht

#waste_to_storage
network.add('Link', name = 'waste_to_storage', bus0 = 'waste', bus1='water_cycle', p_nom = 20, efficiency=0.9, p_nom_extendable = True)
#water_to_storage
network.add('Link', name = 'water_to_storage', bus0 = 'water', bus1='water_cycle', p_nom = 50, efficiency=0.95, p_nom_extendable = True)
#storage_to_water
network.add('Link', name = 'storage_to_water', bus0 = 'water_cycle', bus1='water', efficiency=0.98, p_nom= True) #hier muss die größe noch gesetzt werden



