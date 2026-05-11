
# ======================================
# Manuelle Eingabe statt Excel
# ======================================
import pandas as pd
import numpy as np
import xarray as xr
import pypsa

n = pypsa.Network()

# 1) Zeitachse (Snapshots) festlegen
# Beispiel: 6 Monats-Snapshots ab Jan 2019 (MS = Month Start)
snapshots = pd.date_range("2019-01-01", periods=12, freq="MS")

from linopy import Model
# Ins PyPSA-Netz übernehmen
n.set_snapshots(snapshots)

# 2) Kulturen festlegen
crops = ["Tomate", "Paprika", "Gurke"]

# 3) Erträge (kg/m²) je Snapshot & Kultur manuell vorgeben
# Form: (len(T) Zeilen) x (len(C) Spalten)
yield_matrix = np.array([
    [3.0, 1.5, 0.8],  # Snapshot 1
    [2.5, 1.2, 0.9],  # Snapshot 2
    [2.0, 1.1, 1.0],  # Snapshot 3
    [3.2, 1.4, 0.7],  # Snapshot 4
    [3.0, 1.6, 1.1],  # Snapshot 5
    [2.8, 1.3, 0.9],  # Snapshot 6
    [3.0, 1.5, 0.8],  # Snapshot 7
    [2.5, 1.2, 0.9],  # Snapshot 8
    [2.0, 1.1, 1.0],  # Snapshot 9
    [3.2, 1.4, 0.7],  # Snapshot 10
    [3.0, 1.6, 1.1],  # Snapshot 11
    [2.8, 1.3, 0.9],  # Snapshot 12
], dtype=float)

yield_per_area = xr.DataArray(
    yield_matrix,
    coords={"snapshot": snapshots, "crop": crops},
    dims=["snapshot", "crop"],
)

# Parameter setzen
# maximales Belegungsmaß je Kultur und Snapshot (z.B. m²,), Beispielwerte
Amax_per_crop = xr.DataArray([25, 30, 15], coords=[("crop", crops)], dims=["crop"])
Amax_total = 31.0
kcal_per_kg = xr.DataArray([180, 120, 60], coords=[("crop", crops)], dims=["crop"])
demand_kcal = xr.DataArray(np.full(len(snapshots), 200*30),
                           coords=[("snapshot", snapshots)], dims=["snapshot"])

# vor create_model():
n.add("Carrier", "agri")
n.add("Bus", "bus0", carrier="agri")
n.add("Generator", "dummy_gen", bus="bus0", p_nom=1.0, marginal_cost=1e-6)



# ======================================
# Linopy-Modell aus PyPSA erzeugen
# ======================================
m = n.optimize.create_model()
if m is None:
    m = n.model
print(type(m), hasattr(m, "add_variables"))


# 3) Variablen
# Binary: Kultur aktivieren/deaktivieren (eine pro Kultur, unabhängig von t)
build  = m.add_variables(binary=True, name="Anbau_aktiv", coords={"crop": crops})
active = m.add_variables(binary=True, name="active",
                         coords={"snapshot": snapshots, "crop": crops})
area   = m.add_variables(name="Anbau_Flaeche", lower=0, upper=Amax_per_crop,
                         coords={"snapshot": snapshots, "crop": crops})


# 4) Nebenbedingungen
m.add_constraints(area <= Amax_per_crop * active, name="cap_by_active")
m.add_constraints(active <= build, name="active_implies_build")
m.add_constraints(area.sum("crop") <= Amax_total, name="total_area_cap")
harvest = yield_per_area * area
m.add_constraints((harvest * kcal_per_kg).sum("crop") >= demand_kcal, name="diet_demand")


# ======================================
# Rotations-/Sequenzregeln pro Kultur
# ======================================
# -- TOMATE: keine zwei aufeinanderfolgenden Monate --
tom = active.sel(crop="Tomate")
# Für den letzten Monat ist der Shift 0 -> Bedingung bleibt gültig
m.add_constraints(tom + tom.shift(snapshot=-1, fill_value=0) <= 1, name="tom_no_consecutive")

# -- PAPRIKA: min-up 5 Monate, danach min-down 2 Monate --
pap = active.sel(crop="Paprika")
start_p = m.add_variables(binary=True, name="start_paprika", coords={"snapshot": snapshots})
stop_p  = m.add_variables(binary=True, name="stop_paprika",  coords={"snapshot": snapshots})

# Zustandsübergang: active[t] - active[t-1] = start[t] - stop[t]
pap_prev = pap.shift(snapshot=1, fill_value=0)
m.add_constraints(pap - pap_prev == start_p - stop_p, name="pap_state_transition")

L_up, L_down = 5, 2

# Mindestlaufzeit (min-up):
# Wenn in s gestartet wird, müssen die nächsten L_up Monate aktiv sein.
# Implementieren wir mit Schiebefenstern über die Zeitachsen.
for k in range(L_up):
    if k == 0:
        m.add_constraints(pap >= start_p, name=f"pap_minup_k{k}")
    else:
        # pap[s+k] >= start[s]  -> Indexe an Kanten passend beschneiden
        m.add_constraints(
            pap.isel(snapshot=slice(k, None)) >= start_p.isel(snapshot=slice(0, -k)),
            name=f"pap_minup_k{k}"
        )

# Mindeststillstandszeit (min-down):
# Wenn in s gestoppt wird, müssen die nächsten L_down Monate inaktiv sein.
for k in range(1, L_down + 1):
    m.add_constraints(
        pap.isel(snapshot=slice(k, None)) <= 1 - stop_p.isel(snapshot=slice(0, -k)),
    )

# -- GURKE: keine zusätzlichen Einschränkungen --


# 6) Zielfunktion (Beispiel): Flächeneinsatz oder Kosten minimieren
# Du kannst statt dessen natürlich Energie-/Wasserkosten etc. verwenden.
m.add_objective(0.0, overwrite=True, sense="min")

# 7) Lösen
n.optimize()  # oder gurobi/cbc
