import pypsa
import pandas as pd

# Initialisiere das Netzwerk
network = pypsa.Network()

# Setze tägliche Zeitschritte für z. B. 7 Tage
days = 365
network.set_snapshots(pd.date_range("2025-01-01", periods=days, freq="D"))

# -------------------------------
# CARRIERS (Energieträger)
# -------------------------------
network.add("Carrier", name="light_energy")         # Input
network.add("Carrier", name="water_energy")         # Input (L)
network.add("Carrier", name="nutritional_energy")   # Output (kJ)
network.add("Carrier", name="protein")              # Output (g)
network.add("Carrier", name="Kohlenhydrate")        # Output (g)
network.add("Carrier", name="Ballaststoffe")        # Output (g)
network.add("Carrier", name="Fette")                # Output (g)


# -------------------------------
# BUSSE
# -------------------------------
network.add("Bus", name="light_bus", carrier="light_energy")
network.add("Bus", name="nutrition_bus", carrier="nutritional_energy")
network.add("Bus", name="protein_bus", carrier="protein")
network.add("Bus", name="kohlenhydrate_bus", carrier="kohlenhydrate")
network.add("Bus", name="Fette_bus", carrier="Fette")
network.add("Bus", name="Ballaststoffe_bus", carrier="Ballaststoffe")



# -------------------------------
# GENERATOREN (Pflanzen)
# -------------------------------
# Beispiel: Tomate
network.add("Generator",
    name="Tomate_energy",
    bus="nutrition_bus",
    carrier="nutritional_energy",
    p_nom=2.0,  # 2000 kJ/Tag - Nennleistung zweckentfremden? maximale Produktionsrate in kW (z.B. kJ/s) → Tagesenergie = p_nom⋅Δt
    p_max_pu=1.0, # Die maximale Auslastung (pro Zeitschritt) ist 100% der Nennleistung
    efficiency=1.0,
    marginal_cost=0.0  # Das Erzeugen von 1 kW (bzw. 1 kJ/s) kostet 0€.
)

network.add("Generator",
    name="Tomate_protein",
    bus="protein_bus",
    carrier="protein",
    p_nom=0.005,  # 1 g/100g → 250g = 2.5g → ≈ 0.00003 kW
    p_max_pu=1.0,
    efficiency=1.0,
    marginal_cost=0.0
)

# -------------------------------
# Multilinks Alternative - Multibus-Konversion
# -------------------------------
network.add("Link",
    name="Tomate",
    bus0="light_bus",  # Input: Licht auf Pflanze - PyPSA erlaubt standardmäßig nur 2 Busses (bus0, bus1) pro Link
    bus1="nutrition_bus",
    bus2="protein_bus",
    bus3="fiber_bus",
    p_nom=1.0,
    efficiency=1.0
)

# mehreren Link-Objekten pro Pflanze:
# Licht → Kalorien
network.add("Link",
    name="Tomate_light_to_energy",
    bus0="light_bus",
    bus1="nutrition_bus",
    efficiency=0.05
)

# Licht → Protein
network.add("Link",
    name="Tomate_light_to_protein",
    bus0="light_bus",
    bus1="protein_bus",
    efficiency=0.001
)

# Licht → Ballaststoffe
network.add("Link",
    name="Tomate_to_fiber",
    bus0="light_bus",
    bus1="fiber_bus",
    efficiency=0.002,
    p_nom=1.0
)


# -------------------------------
# DEMAND (Bedarf von 5 Personen)
# -------------------------------
daily_kcal_need = 5 * 2250  # kcal/Tag → 10460 kJ/Tag
daily_protein_need = 5 * 50  # 50g Protein/Person
# -------------------------------
# LÖSEN & ANALYSE
# ...
# -------------------------------
network.optimize()

# Ergebnisse anzeigen
print(network.generators_t.p)
print(network.loads_t.p)