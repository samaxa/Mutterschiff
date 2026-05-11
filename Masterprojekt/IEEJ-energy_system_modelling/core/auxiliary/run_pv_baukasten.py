#Übergabefertig kommentiert JB
import os
import matplotlib.pyplot as plt
import pandas as pd

from core.auxiliary.functions_weather_data import DWDWeatherConfig, DWDWeatherFetcher
from core.module_pv_modulator import PV_System, PV_TYPEN

USE_EXISTING_WEATHER = True

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
base_input = os.path.join(SCRIPT_DIR, "data", "inputs")
weather_csv = os.path.join(base_input, "wetter_daten_15min.csv")


if __name__ == "__main__":
    """
    Direct run of PV Baukasten without modulation and balancing of other modules.
    Modulation of separate PV systems.
    Backend exclusive.
    """
    # ------------------------------------------------------------
    # 1) Load weatherdate (CSV or DWD)
    # ------------------------------------------------------------
    if USE_EXISTING_WEATHER:
        print("→ Verwende vorhandene Wetterdaten-CSV")
        weather_df = pd.read_csv(weather_csv, index_col=0, parse_dates=True)
        weather_df.index = pd.to_datetime(weather_df.index, utc=True).tz_convert(None)
    else:
        print("→ Hole Wetterdaten neu vom DWD")
        cfg = DWDWeatherConfig(
            coords=(51.08579, 6.47554),
            start="2022-01-01",
            end="2022-12-31",
            station_id=None,
            auto_select=False,
            min_quality=0.95,
            save_path=weather_csv,
        )
        weather_df = DWDWeatherFetcher(cfg).run()

    # ------------------------------------------------------------
    # 2) Create PV system (Geometry + PV type + step size)
    # ------------------------------------------------------------
    geojson_path = os.path.join(base_input, "geometry", "a44_beide.geojson")
    output_dir = os.path.join(SCRIPT_DIR, "data", "outputs", "highway")
    os.makedirs(output_dir, exist_ok=True)

    # Choose input variables here. Multiselect of PV types possible e.g. [PV_TYPEN[0], PV_TYPEN[3], ...]
    pv_system = PV_System(
        geojson_path=geojson_path,              # Path to the GeoJSON file
        pvtypes=[PV_TYPEN[2]],                  # PV Type from PV Type dataclass list
        step_size=50,                           # Step size [m] in which the geometry will be equipped with individual PV Systems (Significant on Performance)
        weather_df=weather_df,                  # Weather data from DWD-script
        base_output_dir=output_dir,             # Path for the CSV-Export of calculated point coordinates
    )

    # ------------------------------------------------------------
    # 3) Generate points + azimuth for all selected PV types
    # ------------------------------------------------------------
    # ------------------------------------------------------------
    # 3) Generate points + azimuth for all selected PV types
    # ------------------------------------------------------------
    results = pv_system.generate_pv_points()

    print("Berechnete PV-Typen:")
    for pv_type in pv_system.pvtypes:
        print(" -", pv_type)

    print("\n=== CSV-Test ===")
    for pv_type in pv_system.pvtypes:
        geo_name = os.path.splitext(os.path.basename(geojson_path))[0]
        csv_name = f"{geo_name}_punkte_{pv_type.id}_{pv_type.name}.csv".replace(" ", "_")
        csv_path = os.path.join(output_dir, csv_name)

        print(f"\nPV-Typ: {pv_type.name}")
        print(f"CSV erwartet unter: {csv_path}")
        print(f"Existiert: {os.path.exists(csv_path)}")

        if os.path.exists(csv_path):
            df_test = pd.read_csv(csv_path)
            print("Spalten:", df_test.columns.tolist())
            print("Zeilen:", len(df_test))
            print(df_test.head(3))
    # ------------------------------------------------------------
    # 4) Simulate yearly energy per PV type + plot time series
    # ------------------------------------------------------------
    print("\nJahresenergie je PV-Typ:")
    for pv_type in pv_system.pvtypes:
        geo_name = os.path.splitext(os.path.basename(geojson_path))[0]
        csv_name = f"{geo_name}_punkte_{pv_type.id}_{pv_type.name}.csv".replace(" ", "_")
        csv_path = os.path.join(output_dir, csv_name)

        energy_kwh_pv_type, total_ac_w = pv_system.simulate_pv_type_energy(pv_type, csv_path)
        print(f"  {pv_type.name}: {energy_kwh_pv_type:.1f} kWh")

        # Function for energy and power scaling according to step size
        scaled_energy_kwh_pv_type = 0
        if pv_system.step_size >= pv_type.row_width:
            scaling_factor = pv_system.step_size // pv_type.row_width  # Whole number division -> no half elements
            print("Scaling Faktor", f"{pv_type.name}", scaling_factor)
            scaled_energy_kwh_pv_type = energy_kwh_pv_type * scaling_factor
            print(f"Skalierte Energie {pv_type.name}: {scaled_energy_kwh_pv_type:.1f} kWh")
        else:
            print("Skalierte Gesamtenergie wurde nicht berechnet da Schrittweite kleiner als PV-Typ-Modulweite")

        # Plot AC power for year
        plt.figure(figsize=(15, 4))
        plt.plot(total_ac_w.index, total_ac_w.values, linewidth=0.6)
        plt.title(f"Jahresverlauf AC-Leistung – {pv_type.name}")
        plt.xlabel("Datum")
        plt.ylabel("AC-Leistung [W]")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

        # ------------------------------------------------------------
        # Add-on: Single day plot for a representative summer day (e.g. 21. June)
        # ------------------------------------------------------------
        summer_day_start = "2022-06-21"
        summer_day_end = "2022-06-24"
        day_ac = total_ac_w.loc[summer_day_start:summer_day_end].copy()

        # Clean-up for plotting
        day_ac = day_ac.dropna()
        day_ac = day_ac.clip(lower=0)  # set negative values zero

        plt.figure(figsize=(10, 4))
        plt.plot(day_ac.index, day_ac.values, linewidth=1.2)
        plt.title(f"Tagesverlauf AC-Leistung – {pv_type.name} ({summer_day_start}-{summer_day_end})")
        plt.xlabel("Uhrzeit")
        plt.ylabel("AC-Leistung [W]")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()


