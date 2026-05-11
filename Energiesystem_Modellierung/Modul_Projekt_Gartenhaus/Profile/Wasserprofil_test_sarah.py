import numpy as np                  # (np): Vektor-/Array‑Operationen, hier für Zeitachsen und Formeln.
import pandas as pd                 # (pd): Tabellenstrukturen (DataFrame, Series) und Datei‑Ein/Ausgabe.
import matplotlib.pyplot as plt     # (plt): Visualisierung (Linienplots).


def water_profile_parabola_cycle(T_days, b_L_per_day, snapshots,                # Funktion definiert die aus Zyklusdauer (T_days) und max. Wasserbedarf (b_L_per_day) und
                                 start_hour=0, Wmin_L_per_day=0.0):             # Zeitachse (snapshots - DatetimeIndex) ein stündliches Wasserprofil erzeugt.
    """
    Erzeugt ein parabolisches Wasserbedarfsprofil für einen Pflanzenerntezyklus.

    Parameter:
    ----------
    T_days: Zyklusdauer in Tagen
    b_L_per_day: Maximaler Wasserbedarf in L/Tag
    snapshots: Zeitachse (DatetimeIndex)
    start_hour: Startzeit in Stunden (0 = Jahresbeginn)
    Wmin_L_per_day: minimaler Wasserbedarf in L/Tag (optional)

    Rückgabe:
    ---------
    Series mit Stundenwerten in L/h
    """
    # Zyklus in Stunden - Rechnet die Zyklusdauer von Tagen in Stunden um (T_h).
    T_h = int(round(float(T_days) * 24))
    if T_h <= 0 or b_L_per_day < 0:                      # Guard‑Clause: Falls unplausible Werte (nicht‑positive Zyklusdauer oder negativer Bedarf),
        return pd.Series(0.0, index=snapshots)      # wird eine Null‑Serie zurückgegeben. So crasht die Funktion nicht.

    hours = np.arange(len(snapshots))       # hours: 0,1,2,… bis len(snapshots)-1.
    tau = (hours - int(start_hour)) % T_h   # Stundenposition im aktuellen Zyklus
    t_days = tau / 24.0

    # Parabelkern: bei t=0 und t=T -> 0, bei T/2 -> 1
    core = 1.0 - ((t_days - T_days / 2) / (T_days / 2)) ** 2
    core = np.clip(core, 0.0, None)

    # L/Tag auf L/h umrechnen
    W_day = Wmin_L_per_day + (b_L_per_day - Wmin_L_per_day) * core
    return pd.Series(W_day / 24.0, index=snapshots)


# ======================================
# Daten einlesen
# ======================================

# CSV mit Pflanzen-Wasserprofil-Daten laden
df_Plant_Water_Data = pd.read_csv(
    "../Input/Pflanzendaten_Wasserprofil.csv",
    sep=";", decimal=","
)

# ======================================
# Zeitachse (1 Jahr stündlich)
# ======================================
snapshots = pd.date_range('2019-01-01', periods=8760, freq='h')

# ======================================
# Profile erzeugen
# ======================================
profiles = {}

for _, row in df_Plant_Water_Data.iterrows():
    plant_name = str(row['plant'])
    T_days = float(row['T_days'])
    b_L_per_day = float(row['b_L_per_m2_day']) * float(row.get('area_m2', 1.0))
    Wmin_L_per_day = float(row.get('Wmin_L_per_m2_day', 0.0)) * float(row.get('area_m2', 1.0))
    start_hour = int(round(float(row.get('start_day', 0)) * 24))

    profiles[plant_name] = water_profile_parabola_cycle(
        T_days, b_L_per_day, snapshots,
        start_hour=start_hour,
        Wmin_L_per_day=Wmin_L_per_day
    )

# DataFrame mit allen Pflanzenprofilen
df_profiles = pd.DataFrame(profiles)

# Gesamtwasserbedarf pro Stunde
df_total_water = df_profiles.sum(axis=1)

# ======================================
# Beispielplot
# ======================================
df_profiles.plot(title="Wasserprofile pro Pflanze (L/h)", figsize=(12, 6))
plt.ylabel("Wasserbedarf [L/h]")
plt.show()

df_total_water.plot(title="Gesamt-Wasserbedarf (L/h)", figsize=(12, 4), color="blue")
plt.ylabel("Gesamt [L/h]")
plt.show()
