#%%
# Mini-Wärmesystem;
# PyPSA_heat versucht Wärme dann zu erzeugen, wenn der Preis gerade niedrig ist - optimiert nach kosten!
import matplotlib.pyplot as plt
import pypsaheat as ph
import pandas as pd
import numpy as np
n = ph.HeatNetwork()
n.set_snapshots(range(10))

n.add("Bus", "bus1") # Stromnetz
n.add('Generator', name = 'gen1', bus = 'bus1', p_nom = 100, marginal_cost = np.random.rand(10)) #Stromquelle # Fake Strompreise €/kWh- np.random.rand(10) erzeugt 10 zufällige Zahlen zwischen 0 und 1
                                                                                                            # 100 kW Nennleistung
n.add('HeatStore', name = 'hs1', constant = 'temperature', # geschichtete Wärmespeicher
      height = 4*0.58, base = 0.5, T_amb = 20, T_layer = [60,55,50],  # 3 definierte Temperaturschichten: 60°C, 55°C, 50°C
      T_return = 40, V_initial = [0], cyclic = True)                    # Rücklaufniveau: 40°C, Anfangsvolumen = 0
                                                                        # Cyclic = True bedeutet: Der Speicher am Ende des Optimierungszeitraums muss den gleichen Zustand haben wie am Anfang.
                                                                        #  also leer sein am anfang wieder wegen: V_initial=[0]
n.add('HeatPump', name = 'hp1', bus0 = 'bus1', heat_store = 'hs1',
      T_source = pd.Series([1,1,1,1,1,1,1,1,1,1]), p_nom = 5)

n.add('HeatLoad', name = 'load1', heat_store = 'hs1', p_set = pd.Series([1,1,1,1,1,1,1,1,1,1]),
      T_demand = 60)
n.add('HeatLoad', name = 'load2', heat_store = 'hs1', p_set = pd.Series([3,3,3,3,3,3,3,3,3,3]),
      T_demand = 55)
n.optimize(solver_name='gurobi')
ph.plot.plot_stratified_heat_store(n, 'hs1', sns = n.snapshots)
plt.show()