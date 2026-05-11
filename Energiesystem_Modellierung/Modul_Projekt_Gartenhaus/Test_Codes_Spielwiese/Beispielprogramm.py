from pyomo.environ import *
import numpy as np

# Modell
model = ConcreteModel()

# Zeithorizont (z. B. 24h)
T = range(24)
model.T = Set(initialize=T)

# ------------------------
# Pflanzenparameter (pro kg)
# ------------------------
plants = {
    'Kartoffel': {'kcal': 770, 'protein': 20, 'energy_kwh': 0.2, 'cost': 0.5},
    'Linsen': {'kcal': 1160, 'protein': 90, 'energy_kwh': 0.3, 'cost': 1.0},
    'Spinat': {'kcal': 230, 'protein': 29, 'energy_kwh': 0.1, 'cost': 0.8}
}

model.Plants = Set(initialize=plants.keys())

# Entscheidungsvariablen: Pflanzenmenge (kg)
model.plant_mass = Var(model.Plants, domain=NonNegativeReals)

# ------------------------
# Energiebedarf (Lastprofil in kWh)
# ------------------------
load_profile = [2.0]*6 + [3.5]*8 + [2.0]*10  # 24h Bedarf
model.load_demand = Param(model.T, initialize={t: load_profile[t] for t in T})

# PV-Erzeugung (pu-Profil)
pv_profile = {t: max(0, np.sin(t / 24 * 3.14)) for t in T}
model.pv_profile = Param(model.T, initialize=pv_profile)

# PV-Leistung (kW)
model.pv_capacity = Var(domain=NonNegativeReals)

# Wärmepumpe-Leistung (elektrisch, kW)
model.hp_capacity = Var(domain=NonNegativeReals)

# Heizlast (kWh pro Stunde, hier konstant)
heat_demand = 1.0  # konstant
COP = 3.5

# ------------------------
# Zielfunktion: Gesamtkosten minimieren
# ------------------------
def total_cost_rule(m):
    plant_costs = sum(m.plant_mass[p] * plants[p]['cost'] for p in m.Plants)
    pv_cost = m.pv_capacity * 800  # €/kW (Annahme)
    hp_cost = m.hp_capacity * 600  # €/kW
    return plant_costs + pv_cost + hp_cost

model.total_cost = Objective(rule=total_cost_rule, sense=minimize)

# ------------------------
# kcal-Bedarf
# ------------------------
required_kcal = 5 * 2500

def kcal_rule(m):
    return sum(m.plant_mass[p] * plants[p]['kcal'] for p in m.Plants) >= required_kcal

model.kcal_constraint = Constraint(rule=kcal_rule)

# ------------------------
# Energieversorgung
# ------------------------
def energy_balance_rule(m, t):
    pv_gen = m.pv_capacity * m.pv_profile[t]
    hp_el = m.hp_capacity * (heat_demand / COP)
    return pv_gen >= m.load_demand[t] + hp_el

# model.energy_balance = Constraint(model.T, rule=energy_balance_rule)

# ------------------------
# Optional: Fläche, Wasser, Protein? (später)
# ------------------------

# ------------------------
# Solver starten (Gurobi)
# ------------------------
solver = SolverFactory('gurobi')
result = solver.solve(model, tee=True)


# ------------------------
# Ergebnisse anzeigen
# ------------------------
print("\nOptimale Pflanzenmengen:")
for p in model.Plants:
    print(f"  {p}: {model.plant_mass[p]():.2f} kg")

print(f"\nPV-Kapazität: {model.pv_capacity():.2f} kW")
print(f"Wärmepumpen-Kapazität: {model.hp_capacity():.2f} kW")
print(f"Minimale Gesamtkosten: {model.total_cost():.2f} €")
