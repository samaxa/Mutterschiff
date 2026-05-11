import pandas as pd
import pyomo.environ as pyo

# Pyomo-Modell
model = pyo.ConcreteModel(name='Test Gewaechshaus')
model.T = pyo.Set(initialize=range(365))

# Funktion liefert ein Dictionary mit Pflanzendaten
def get_plant_parameters():
    return {
        'Kartoffel': {'kcal': 770,  'cost': 0.5, 'water': 100, 'growth': 90},
        'Linsen':    {'kcal': 1160, 'cost': 1.0, 'water': 80,  'growth': 100},
        'Spinat':    {'kcal': 230,  'cost': 0.8, 'water': 60,  'growth': 45}
    }

# Hole Pflanzendaten
plant_data = get_plant_parameters()

# Pyomo Sets und Parameter
model.Plants = pyo.Set(initialize=plant_data.keys())

model.kcal        = pyo.Param(model.Plants, initialize={p: plant_data[p]['kcal'] for p in model.Plants})
model.cost        = pyo.Param(model.Plants, initialize={p: plant_data[p]['cost'] for p in model.Plants})
model.water       = pyo.Param(model.Plants, initialize={p: plant_data[p]['water'] for p in model.Plants})
model.growth_days = pyo.Param(model.Plants, initialize={p: plant_data[p]['growth'] for p in model.Plants})

# Pandas DataFrame erstellen
df = pd.DataFrame(plant_data).T  # .T transponiert das Dictionary zu Zeilen = Pflanzen
print(df)


def get_energy_parameters():
    return {
        'PV': {
            'capex': 800,      # €/kWp 
            'opex': 10,        # €/kWp/a
            'efficiency': 0.18,
            'lifetime': 25
        },
        'Waermepumpe': {
            'capex': 1200,     # €/kWth
            'opex': 30,        # €/kWth/a
            'efficiency': 3.5,
            'lifetime': 20
        },
        'Batterie': {
            'capex': 500,      # €/kWh
            'opex': 15,        # €/kWh/a
            'efficiency': 0.9,
            'lifetime': 15
        }
    }

# Daten abrufen
energy_data = get_energy_parameters()

# Pyomo Set
model.Techs = pyo.Set(initialize=energy_data.keys())

# Pyomo Parameter definieren
model.capex      = pyo.Param(model.Techs, initialize={t: energy_data[t]['capex'] for t in model.Techs})
model.opex       = pyo.Param(model.Techs, initialize={t: energy_data[t]['opex'] for t in model.Techs})
model.efficiency = pyo.Param(model.Techs, initialize={t: energy_data[t]['efficiency'] for t in model.Techs})
model.lifetime   = pyo.Param(model.Techs, initialize={t: energy_data[t]['lifetime'] for t in model.Techs})

# Ausgabe als Pandas-Tabelle
df_energy = pd.DataFrame(energy_data).T
print(df_energy)



