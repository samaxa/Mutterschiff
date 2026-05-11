import pypsa
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

# =====================================================
# 1) Zeitachse (Monatsanfang) definieren:
# =====================================================
snapshots = pd.date_range("2019-01-01", periods=8760, freq="h")


# =====================================================
# 2) PyPSA-Netz & Snapshots definieren:
# =====================================================
n = pypsa.Network()
n.set_snapshots(snapshots)


# --- Dummy-Netz (nur damit create_model() läuft) ---
n.add("Carrier", "dummy")
n.add("Bus", "bus0", carrier="dummy")
n.add("Generator", "dummy_gen", bus="bus0",
      p_nom=1.0, p_min_pu=0.0, p_max_pu=0.0,
      marginal_cost=1e-6)  # <- kleine Kosten, damit PyPSA eine Objective bauen kann


# =====================================================
# 3.A) Parameter: der Pflanzen einlesen
# =====================================================

# =====================================================
# Erntefunktion für jede Pflanze:
# =====================================================
# Funktion die stündliche ertragszeitreihe baut
# Parameter:
# start_hour = ab welcher Stunde des Jahres der Zyklus beginnt (0 = 1. Jan 00:00)
# T_days = Zykluslänge in Tagen
# Y_cycle = Gesamtertrag pro m² über einen Zyklus [kg/m²]
# index = Zeitachse (8760 Stunden)
# Rückgabe: pd.Series mit Einheiten kg/(m²·h), exakt entlang des Index

def yield_spike_hourly(start_hour: int, T_days: int, Y_cycle: float,
                       index: pd.DatetimeIndex) -> pd.Series:
    """
    Ernte als EIN Spike: gesamte Menge Y_cycle fällt in genau EINER Stunde an.
    Rückgabe: stündliche Serie in kg/(m^2·h) entlang 'index'.
    """
    n = len(index)                  # Anzahl der Snapshots im Jahr - 8760
    y = np.zeros(n, dtype=float)    # anfangs überall 0 ERTRAG

    L = int(T_days) * 24            # Zykluslänge in Stunden
    if L <= 0:                              # Falls T_days ≤ 0, einfach Nullserie zurück.
        return pd.Series(y, index=index)

    # Stunde der Ernte: "letzte" Stunde des Zyklus, mit Wrap-around ins Jahresende
    harvest_hour = (int(start_hour) + L - 1) % n                #  Wir gehen vom Start genau L−1 Stunden weiter → das ist die letzte Stunde des Zyklus; % n sorgt für korrektes Überrollen am Jahresende

    # gesamte Zyklusmenge als Ein-Stunden-Flow buchen:
    y[harvest_hour] = float(Y_cycle)   # Einheit: kg/(m^2·h) in DIESER Stunde

    return pd.Series(y, index=index)

# =====================================================
# Pflanzendaten für die Funktion holen:
# =====================================================

df_crops = pd.read_excel("./Input/Finale_Pflanzendaten_Mappe.xlsx", sheet_name="crops_parameter").set_index("crops")
df_crops.index.name = "crop"


earliest_harvest_days = int(df_crops["T_days"].min())   #

# Wähle den Startvorrat: mindestens 30 Tage ODER bis zur ersten möglichen Ernte
S_INIT_DAYS = max(120, earliest_harvest_days)
print("S_INIT_DAYS =", S_INIT_DAYS)


# fehlende start_hour -> 0
if "start_hour" not in df_crops.columns:
    df_crops["start_hour"] = 0

yields = {}     # dict anlegen {crop: Series(8760)}
for crop, row in df_crops.iterrows():
    T_days = row["T_days"]
    Y_cycle = row["y_cycle_kg_m2"]
    start_hour = row["start_hour"]
    y = yield_spike_hourly(start_hour, T_days, Y_cycle, snapshots)
    yields[crop] = y

# Zu einem DataFrame zusammenführen (Spalten = crops, Index = Stunden)
yield_df = pd.DataFrame(yields)

# # 5) Mini-Checks
# print("Ernte pro Zyklus [kg/m²]:")
# print(yield_df.sum(axis=0))           # sollte je crop = Y_cycle sein
# print("Ernte-Stunden je Pflanze (Anzahl):")
# print((yield_df > 0).sum(axis=0))     # sollte je crop = 1 sein

# wieder XArray daraus machen für die späteren nebenbedingungen usw.
yield_per_area = xr.DataArray(
    yield_df.values,
    coords={"snapshot": n.snapshots, "crop": yield_df.columns},
    dims=["snapshot","crop"],
)

# =====================================================
# Weitere Parameter der Pflanzen definieren:
# =====================================================
# Energie: von kWh/(m²·Jahr) -> kWh/(m²·Stunde) (einfach gleichmäßig)

energy_per_area_h = xr.DataArray(
    (df_crops["energy_kwh_per_m2_a"] / 8760.0).astype(float).values,
    coords={"crop": df_crops.index},
    dims=["crop"]
)

# Nährwerte: pro kg Ernte (Vektoren über 'crop')
kcal_per_kg  = xr.DataArray(df_crops["kcal_per_kg" ].astype(float).values, coords={"crop": df_crops.index}, dims=["crop"])
prot_per_kg  = xr.DataArray(df_crops["prot_g_per_kg" ].astype(float).values, coords={"crop": df_crops.index}, dims=["crop"])
carb_per_kg  = xr.DataArray(df_crops["carb_g_per_kg" ].astype(float).values, coords={"crop": df_crops.index}, dims=["crop"])
sugar_per_kg = xr.DataArray(df_crops["sugar_g_per_kg"].astype(float).values, coords={"crop": df_crops.index}, dims=["crop"])
fiber_per_kg = xr.DataArray(df_crops["fiber_g_per_kg"].astype(float).values, coords={"crop": df_crops.index}, dims=["crop"])
fat_per_kg   = xr.DataArray(df_crops["fat_g_per_kg"  ].astype(float).values, coords={"crop": df_crops.index}, dims=["crop"])

# Mikro-Checks (nur zur Beruhigung)
# print("Energie [kWh/(m²·h)] je Pflanze:\n", energy_per_area_h.to_pandas().head())
# print("kcal_per_kg für 3 Pflanzen:\n", kcal_per_kg.isel(crop=slice(0,3)).to_pandas())

# Parameter täglicher Bedarf Person bezogen:
df_demand = pd.read_excel("./Input/Finale_Pflanzendaten_Mappe.xlsx", sheet_name="person_demand").set_index("person")

# Ziel - Personenanzahl wählen
P = 1
row = df_demand.loc[P]  # enthält: kcal, prot_g, carb_g, sugar_g, fiber_g, fat_g (pro TAG)

# 3) Hilfsfunktion: täglich -> stündlich (gleichmäßig über 24 h)
def daily_to_hourly(val_per_day: float, snapshots) -> xr.DataArray:
    return xr.DataArray(
        np.full(len(snapshots), float(val_per_day) / 24.0),
        coords={"snapshot": snapshots},
        dims=["snapshot"]
    )
# 4) Stündliche Demand-Zeitreihen (Einheiten bleiben kcal bzw. g – jetzt pro Stunde)
demand_kcal_h  = daily_to_hourly(row["kcal"],     n.snapshots)
demand_prot_h  = daily_to_hourly(row["prot_g"],   n.snapshots)
demand_carb_h  = daily_to_hourly(row["carb_g"],   n.snapshots)
demand_sugar_h = daily_to_hourly(row["sugar_g"],  n.snapshots)
demand_fiber_h = daily_to_hourly(row["fiber_g"],  n.snapshots)
demand_fat_h   = daily_to_hourly(row["fat_g"],    n.snapshots)

# # 5) Zwei Mikro-Checks (Plausibilität)
# print("Jahres-kcal (Soll):", row["kcal"]*365, "Ist:", float(demand_kcal_h.sum()))
# print("Jahres-Protein[g] (Soll):", row["prot_g"]*365, "Ist:", float(demand_prot_h.sum()))
#

# =====================================================
# 3.6) Parameter: Fläche definieren
# =====================================================
Amax_total = 100.0  # m²

# =====================================================
# 3.7) Parameter: Lager Werte
# =====================================================

# Crop-Liste
crops = df_crops.index.tolist()


# =====================================================
# 4) Linopy-Modell erzeugen
# =====================================================
# Optimierungsmodel mit Linopy definieren (nutzt Pypsa im Hintergrund)
m = n.optimize.create_model()

# =====================================================
# 4.1) Entscheidungsvariablen --> entscheidet die Zielfunktion
# =====================================================

area   = m.add_variables(lower=0.0,   name="area", coords=[("snapshot", n.snapshots), ("crop", crops)])

A_cycle = m.add_variables(lower=0.0, name="A_cycle", coords=[("crop", df_crops.index)])


# =====================================================
# 4.2) Anbau-Constraints
# =====================================================

# 0) Hilfsgröße: Wachstumsmaske (1 = im Fenster, 0 = sonst)
mask = xr.zeros_like(yield_per_area)
for c in df_crops.index:
    s = int(df_crops.loc[c, "start_hour"])
    L = int(df_crops.loc[c, "T_days"]) * 24
    idx = (np.arange(len(n.snapshots)) - s) % len(n.snapshots)
    mask.loc[dict(crop=c)] = (idx < L).astype(float)
#
# m.add_constraints(area * (1 - mask) == 0, name="no_area_outside_growth")

m.add_constraints(area == A_cycle * mask, name="area_eq_Acycle_in_growth")

m.add_constraints((mask * A_cycle).sum("crop") <= Amax_total, name="total_area_cap_time")

# =====================================================
# 4.3) Ernte - Nährstoffausbeute stündlich definieren:
# =====================================================

harvest_expr = yield_per_area * A_cycle

# --- Nährstoffproduktion  ---
prod_kcal_expr  = (harvest_expr * kcal_per_kg ).sum("crop")
prod_prot_expr  = (harvest_expr * prot_per_kg ).sum("crop")
prod_carb_expr  = (harvest_expr * carb_per_kg ).sum("crop")
prod_sugar_expr = (harvest_expr * sugar_per_kg).sum("crop")
prod_fiber_expr = (harvest_expr * fiber_per_kg).sum("crop")
prod_fat_expr   = (harvest_expr * fat_per_kg  ).sum("crop")


# =====================================================
# 5) Lagerdynamik für alle Nährstoffe (kcal & Makros) als Nebenbedingung erzwingt zeitliche Deckung
# =====================================================

def add_stock_hourly(m, name, prod_h, demand_h, snapshots, S_init_days=1.0):
    stock = m.add_variables(lower=0.0, name=name, coords=[("snapshot", snapshots)])
    # Tagesbedarf aus der ersten Stunde rekonstruieren (konstante Serie):
    daily0 = float(demand_h.isel(snapshot=0) * 24.0)
    S_init = S_init_days * daily0

    # t = 0
    m.add_constraints(stock.isel(snapshot=0) ==
                      prod_h.isel(snapshot=0) - demand_h.isel(snapshot=0) + S_init,
                      name=f"{name}_balance_t0")
    # t = 1..T-1
    m.add_constraints(
        stock.isel(snapshot=slice(1, None)) ==
        stock.isel(snapshot=slice(0, -1)) +
        prod_h.isel(snapshot=slice(1, None)) -
        demand_h.isel(snapshot=slice(1, None)),
        name=f"{name}_balance_dyn"
    )
    return stock

stock_kcal   = add_stock_hourly(m, "stock_kcal",    prod_kcal_expr,     demand_kcal_h,   n.snapshots, S_init_days=S_INIT_DAYS)
stock_prot   = add_stock_hourly(m, "stock_prot",    prod_prot_expr,     demand_prot_h,   n.snapshots, S_init_days=S_INIT_DAYS)
stock_carb   = add_stock_hourly(m, "stock_carb",    prod_carb_expr,     demand_carb_h,   n.snapshots, S_init_days=S_INIT_DAYS)
#stock_sugar  = add_stock_hourly(m, "stock_sugar",   prod_sugar_expr,    demand_sugar_h,  n.snapshots, S_init_days=S_INIT_DAYS)
stock_fiber  = add_stock_hourly(m, "stock_fiber",   prod_fiber_expr,    demand_fiber_h,  n.snapshots, S_init_days=S_INIT_DAYS)
#stock_fat    = add_stock_hourly(m, "stock_fat",     prod_fat_expr,      demand_fat_h,    n.snapshots, S_init_days=S_INIT_DAYS)

annual_kcal_need = float(row["kcal"]) * 365.0
kcal_per_m2_cycle = (df_crops["y_cycle_kg_m2"] * df_crops["kcal_per_kg"]).astype(float)
print("Bedarf [kcal/a]:", annual_kcal_need)
print("Beste Kultur [kcal/m² pro Zyklus]:", float(kcal_per_m2_cycle.max()))
print("Max. kcal/a mit 100 m² (1 Zyklus je Kultur):", float(kcal_per_m2_cycle.max()*100))




# =====================================================
# 6) Zielfunktion: Energieverbrauch minimieren
# =====================================================
energy_use = (energy_per_area_h * mask * A_cycle).sum(["snapshot", "crop"])
m.add_objective(energy_use, sense="min", overwrite=True)

# =====================================================
# 7) Lösen
# =====================================================
n.optimize.solve_model(solver_name="gurobi")

# === Ergebnisse & Plots (nach dem Solve) =====================================

# Lösungen holen (numerisch!)
A_cycle_sol     = m.variables["A_cycle"].solution        # (crop)
area_opt        = m.variables["area"].solution           # (snapshot, crop)
stock_kcal_sol  = m.variables["stock_kcal"].solution     # (snapshot)

# Produktion stündlich aus Lösung
harvest_h_sol   = yield_per_area * A_cycle_sol                   # (snapshot,crop) kg
prod_kcal_h_sol = (harvest_h_sol * kcal_per_kg).sum("crop")     # (snapshot) kcal

# Verfügbar in Stunde t = Lager(t-1) + Produktion(t)
avail_kcal_h = stock_kcal_sol.shift(snapshot=1, fill_value=0) + prod_kcal_h_sol

# Monats-Summen (saubere Plots)
def to_monthly_sum(da): return da.to_pandas().resample("MS").sum()
monthly_need  = to_monthly_sum(demand_kcal_h)
monthly_avail = to_monthly_sum(avail_kcal_h)

# Quick Checks / kurze Ausgabe
print("\nA_cycle (m²) > 0:")
print(A_cycle_sol.where(A_cycle_sol > 1e-6).to_pandas().dropna())

print("\nDeckt jede Stunde den Bedarf? (min(Verfügbar-Need) ≥ 0):",
      float((avail_kcal_h - demand_kcal_h).min()) >= 0)

# Plot 1: belegte Fläche (Stacked)
area_month = area_opt.to_pandas().resample("MS").mean()
ax = area_month.plot(kind="bar", stacked=True, figsize=(12,6))
ax.set_title("Belegte Fläche (Monatsmittel)"); ax.set_ylabel("m²"); ax.set_xlabel("Monat")
plt.tight_layout(); plt.show()

# Plot 2: kcal Bedarf vs. verfügbar (Monatssummen)
plt.figure(figsize=(12,4))
plt.plot(monthly_need.index,  monthly_need.values,  "k--", label="Bedarf")
plt.plot(monthly_avail.index, monthly_avail.values, "g-",  label="Verfügbar")
plt.title("kcal: Bedarf vs. verfügbar (Monatssummen)")
plt.ylabel("kcal/Monat"); plt.grid(True); plt.legend()
plt.tight_layout(); plt.show()
