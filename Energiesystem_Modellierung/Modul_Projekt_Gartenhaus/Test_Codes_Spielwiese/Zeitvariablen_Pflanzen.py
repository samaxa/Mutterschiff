# ======================================
# Import der Bibliotheken
# ======================================
import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xarray as xr

from linopy import Model
n = pypsa.Network()
# Beispiel: eine leere Bus/Generator-Struktur, falls du 'XY' nutzt, muss der Generator existieren
n.add("Bus", "bus0")
n.add("Generator", "XY", bus="bus0", p_nom=1e6, marginal_cost=0)  # nur wenn du den Constraint brauchs
# Excel lesen
from pathlib import Path

df_yield = pd.read_csv("ertraege.test.csv") # Spalte 'snapshot' zu Datetime
df_yield["snapshot"] = pd.to_datetime(df_yield["snapshot"]) # Index setzen
df_yield = df_yield.set_index("snapshot")

#Snapshots ins Netz übernehmen
n.set_snapshots(df_yield.index)

#Liste aus Excel-Spalten nehmen
crops = list(df_yield.columns)
C = xr.IndexVariable("crop", crops)
T = xr.IndexVariable("snapshot", n.snapshots)

#Ertrag pro Flächeneinheit und Snapshot (kg/m²) – kann saisonal sein:
yield_per_area = xr.DataArray(
    df_yield.values,
    coords={
        "snapshot": n.snapshots,
        "crop": df_yield.columns
    },
    dims=["snapshot", "crop"],
)

# Parameter setzen
# maximales Belegungsmaß je Kultur und Snapshot (z.B. m²,), Beispielwerte
Amax_per_crop = xr.DataArray([25, 30, 15], coords={"crop": C}, dims=["crop"])

# Gesamtflächenlimit im Gewächshaus
Amax_total = 31.0


# Nährwert (kcal/kg) und Bedarf je Snapshot (kcal) oder egal wie man es möchte dann am Ende
kcal_per_kg = xr.DataArray([180, 120, 60], coords={"crop": C}, dims=["crop"])

# Bedarf pro Snapshot (kcal); hier Monats-Snapshots → 30 Tage a 2000 kcal als Beispiel
demand_kcal = xr.DataArray([2000*30]*len(T), coords={"snapshot": T}, dims=["snapshot"])

# ======================================
# Linopy-Modell aus PyPSA erzeugen
# ======================================
m = n.optimize.create_model()     # baut PyPSA-Variablen (z.B. 'Generator-p') ins Modell
# alternativ: n.optimize.create_model(); m = n.model

# 3) Variablen
# Binary: Kultur aktivieren/deaktivieren (eine pro Kultur, unabhängig von t)
build = m.add_variables(binary=True, name="Anbau_aktiv", coords={"crop": C})

# Ganzzahlige "Anbaufläche" pro Kultur und Snapshot (0..Amax_per_crop[c])
area = m.add_variables(
    name="Anbau_Flaeche",
    lower=0,
    upper=Amax_per_crop,
    coords={"snapshot": T, "crop": C},
)

# 4) Nebenbedingungen

# (a) Aktivierung koppelt max. Fläche:  area[c,t] ≤ build[c] * Amax_per_crop[c]
m.add_constraints(
    area <= build * Amax_per_crop,
    name="build_limits_area",
)

# (b) Gesamtflächenlimit je Snapshot:  Σ_c area[c,t] ≤ Amax_total
m.add_constraints(
    area.sum("crop") <= Amax_total,
    name="total_area_cap",
)

# (c) Ernte (kg) = Ertrag(kg/m²) * Fläche(m²) – linear, da Param * Variable
harvest = yield_per_area * area

# (d) Bedarfsdeckung je Snapshot: Σ_c harvest[c,t] * kcal/kg ≥ demand_kcal[t]
m.add_constraints(
    (harvest * kcal_per_kg).sum("crop") >= demand_kcal,
    name="diet_demand",
)
# (e) (Optional) Generator 'XY' an Tomaten-Anbau koppeln, falls vorhanden
if "XY" in n.generators.index and "Generator-p" in m.variables:
    gen_xy_p = m.variables["Generator-p"].sel(Generator="XY")  # dims: snapshot
    big_M = 1e6
    m.add_constraints(gen_xy_p <= big_M * build.sel(crop="Tomate"), name="genXY_requires_tomato")


# 6) Zielfunktion (Beispiel): Flächeneinsatz oder Kosten minimieren
# Du kannst statt dessen natürlich Energie-/Wasserkosten etc. verwenden.
objective = area.sum() * 0.0  # placeholder: keine Kosten → reine Machbarkeit
m.add_objective(objective, sense="min")

# 7) Lösen
n.optimize.solve_model(solver_name="gurobi")  # oder gurobi/cbc
