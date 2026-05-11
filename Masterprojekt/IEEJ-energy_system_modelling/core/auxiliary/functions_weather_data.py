# Übergabefertig kommentiert SM
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

from wetterdienst.provider.dwd.observation import (
    DwdObservationRequest,
    DwdObservationResolution,
    DwdObservationPeriod,
    DwdObservationParameter,
)
from pvlib.solarposition import get_solarposition
from pvlib.irradiance import dirint, get_extra_radiation


# --------------------------------------------
# Configuration Dataclass
# --------------------------------------------
@dataclass
class DWDWeatherConfig:
    """
    Configuration for DWD weather data retrieval and preprocessing
    """
    coords: Tuple[float, float] = (51.08579, 6.47554)       # (latitude, longitude) of target location
    start: str = "2022-01-28"                               # Start of requested time period
    end: str   = "2022-12-31"                               # End of requested time period
    station_id: Optional[str] = None                        # Fixed DWD station ID; None = auto selection
    auto_select: bool = True                                # Automatically select best station
    min_quality: float = 0.95                               # Minimum valid data fraction per parameter
    tz: str = "Europe/Berlin"                               # Time zone
    save_path: Optional[str] = None                         # Optional CSV output path
    plot_date: Optional[str] = None                         # Optional single-day plot
    plot_range: Optional[Tuple[str, str]] = None            # Optional time range plot

    use_dirint: bool = True                                 # Use dirint for DNI estimation
    min_elevation_deg: float = 3.5                          # Minimum solar elevation angle
    dni_interp_limit: int = 3                               # Max number of short DNI gaps to interpolate


# --------------------------------------------
# Main Weather Fetcher
# --------------------------------------------

class DWDWeatherFetcher:
    """
    Fetches and preprocesses DWD weather data for PV simulation.
    """

    # Required parameters for valid dataset
    REQUIRED_PARAMETERS = [
        "radiation_global",
        "radiation_sky_short_wave_diffuse",
        "temperature_air_mean_200",
        "wind_speed",
    ]

    # Rename DWD parameters to internal naming
    RENAME_MAP = {
        "radiation_global": "ghi",
        "radiation_sky_short_wave_diffuse": "dhi",
        "temperature_air_mean_200": "temp_air",
        "wind_speed": "wind_speed",
        "temperature_dew_point_mean_200": "temp_dew",
        "pressure_air_site": "pressure_pa",
        "humidity": "rel_hum",
    }

    def __init__(self, cfg: DWDWeatherConfig):
        self.cfg = cfg
        # Initialize DWD request
        self._request = DwdObservationRequest(
            parameter=self._parameters(),
            resolution=DwdObservationResolution.MINUTE_10,
            period=DwdObservationPeriod.HISTORICAL,
            start_date=datetime.fromisoformat(cfg.start),
            end_date=datetime.fromisoformat(cfg.end),
        )

    @staticmethod
    def _parameters() -> List[DwdObservationParameter]:
        """Define required DWD parameters."""
        return [
            DwdObservationParameter.MINUTE_10.SOLAR.RADIATION_GLOBAL,
            DwdObservationParameter.MINUTE_10.SOLAR.RADIATION_SKY_SHORT_WAVE_DIFFUSE,
            DwdObservationParameter.MINUTE_10.TEMPERATURE_AIR.TEMPERATURE_AIR_MEAN_200,
            DwdObservationParameter.MINUTE_10.WIND.WIND_SPEED,
            DwdObservationParameter.MINUTE_10.TEMPERATURE_AIR.PRESSURE_AIR_SITE,
            DwdObservationParameter.MINUTE_10.TEMPERATURE_AIR.TEMPERATURE_DEW_POINT_MEAN_200,
            DwdObservationParameter.MINUTE_10.TEMPERATURE_AIR.HUMIDITY,
        ]

    # --------------------------------------------------------
    # Main workflow
    # --------------------------------------------------------

    def run(self) -> pd.DataFrame:
        """Load and process DWD data (10-minute resolution)."""
        station_id = self._select_station()
        df = self._fetch_dataframe(station_id)
        df = self._postprocess(df)
        self._maybe_save(df)
        self._maybe_plot(df)
        return df

    # --------------------------------------------------------
    # Station selection
    # --------------------------------------------------------
    def _select_station(self) -> str:
        if self.cfg.station_id:
            return self.cfg.station_id

        stations_info = self._request.filter_by_rank(latlon=self.cfg.coords, rank=15)
        df_top = stations_info.df.to_pandas().head(15)

        # Manual selection
        if not self.cfg.auto_select:
            print(df_top[["station_id", "name", "distance"]])
            return input("Enter station_id: ")

        # Automatic selection based on completeness
        for sid in df_top["station_id"]:
            try:
                station_data = self._request.filter_by_station_id(sid)
                df = station_data.values.all().df.to_pandas()
                if df.empty:
                    continue
                df["value"] = df["value"].replace(-999, np.nan)
                grouped = df.groupby("parameter")["value"].apply(lambda x: x.notna().mean())
                if all(p in grouped.index and grouped[p] >= self.cfg.min_quality for p in self.REQUIRED_PARAMETERS):
                    return str(sid)
            except Exception:
                continue
        raise ValueError("No suitable weather station found.")


    # --------------------------------------------------------
    # Data retrieval
    # --------------------------------------------------------
    def _fetch_dataframe(self, station_id: str) -> pd.DataFrame:
        """Fetch raw DWD data for selected station."""
        stations_info = self._request.filter_by_station_id(station_id)
        df = stations_info.values.all().df.to_pandas()
        if df.empty:
            raise ValueError(f"Station {station_id} returned no data.")
        return df

    # --------------------------------------------------------
    # Data processing
    # --------------------------------------------------------
    def _postprocess(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean, transform and extend raw DWD data."""
        df = df_raw.copy()

        # --- Pivot and rename ---
        df["value"] = df["value"].replace(-999, np.nan)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").pivot(columns="parameter", values="value")
        df.rename(columns=self.RENAME_MAP, inplace=True)

        # --- Unit conversions ---
        if "temp_air" in df.columns:
            df["temp_air"] = df["temp_air"] - 273.15
        if "temp_dew" in df.columns:
            df["temp_dew"] = df["temp_dew"] - 273.15

        # J/m² per 10 min → W/m²
        for col in ["ghi", "dhi"]:
            if col in df.columns:
                df[col] = df[col] / 600

        # --- Resampling ---
        df = df.resample("10T").interpolate("time")

        # --- Time handling ---
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)

        df = df.sort_index()

        # --- Solar position ---
        solpos = get_solarposition(df.index, latitude=self.cfg.coords[0], longitude=self.cfg.coords[1])
        df["zenith"] = solpos["zenith"]
        df["elevation"] = 90 - df["zenith"]
        cosz = np.cos(np.radians(df["zenith"]))

        # --- Masks ---
        daylight = (df["elevation"] > 0) & df["ghi"].notna() & (df["ghi"] > 0)
        valid_sun = (df["elevation"] >= self.cfg.min_elevation_deg) & (cosz > 0)

        # --- DNI calculation ---
        if self.cfg.use_dirint:
            dni_vals = dirint(
                ghi=df["ghi"].values,
                solar_zenith=df["zenith"].values,
                times=df.index,
                pressure=df["pressure_hpa"].values if "pressure_hpa" in df.columns else None,
                temp_dew=df["temp_dew"].values if "temp_dew" in df.columns else None
            )
            dni = pd.Series(dni_vals, index=df.index)
            dni.loc[~valid_sun] = 0.0
        else:
            df["dhi"] = np.minimum(df["dhi"], df["ghi"])
            dni = pd.Series(np.nan, index=df.index, dtype=float)
            idx = valid_sun
            dni.loc[idx] = (df.loc[idx, "ghi"] - df.loc[idx, "dhi"]) / cosz[idx]
            dni.loc[~valid_sun] = 0.0

        # --- Physical limits ---
        doy = df.index.dayofyear.values
        i0 = get_extra_radiation(doy)
        dni = np.minimum(dni.values, i0)
        dni = pd.Series(dni, index=df.index)

        dni = dni.clip(lower=0)
        dni.loc[~daylight] = 0.0

        # --- Interpolation ---
        dni_interp = dni.copy()
        dni_interp[~daylight] = np.nan
        dni_interp = dni_interp.interpolate(method="time", limit=self.cfg.dni_interp_limit)
        dni = dni_interp.fillna(0.0)

        df["dni"] = dni

        # --- Time filtering ---
        start_local = pd.Timestamp(self.cfg.start)
        end_local = pd.Timestamp(self.cfg.end)
        df = df.loc[start_local:end_local]

        return df


    # --------------------------------------------------------
    # Optional output
    # --------------------------------------------------------

    def _maybe_save(self, df: pd.DataFrame) -> None:
        if self.cfg.save_path:
            df.to_csv(self.cfg.save_path)
            print(f"Saved to: {self.cfg.save_path}")

    def _maybe_plot(self, df: pd.DataFrame) -> None:
        if self.cfg.plot_date:
            self.plot_day(df, self.cfg.plot_date)
        if self.cfg.plot_range:
            self.plot_range(df, *self.cfg.plot_range)

    # --------------------------------------------------------
    # Plot functions
    # --------------------------------------------------------
    @staticmethod
    def plot_day(df: pd.DataFrame, plot_date: str) -> None:
        """Plot GHI, DHI, DNI and zenith for one day."""
        day = pd.to_datetime(plot_date)
        df_day = df.loc[day.strftime("%Y-%m-%d")]
        fig, ax1 = plt.subplots()
        ax1.set_ylabel("Irradiance [W/m²]")
        df_day[["ghi", "dhi", "dni"]].plot(ax=ax1)
        ax2 = ax1.twinx()
        ax2.set_ylabel("Zenith [°]")
        df_day["zenith"].plot(ax=ax2, style="--", color="gray")
        plt.title(f"Solar radiation and position on {plot_date}")
        plt.grid()
        plt.show()

    @staticmethod
    def plot_range(df, start_plot: str, end_plot: str):
        """Plot irradiance over a time range."""
        start_ts = pd.to_datetime(start_plot)
        end_ts = pd.to_datetime(end_plot)

        df_range = df.loc[start_ts:end_ts]


        fig, ax1 = plt.subplots(figsize=(14, 6))
        cols = [c for c in ["ghi", "dhi", "dni"] if c in df_range.columns]
        df_range[cols].plot(ax=ax1)
        ax1.set_ylabel("Irradiance [W/m²]")
        plt.title(f"Solar radiation from {start_ts.date()} to {end_ts.date()}")
        plt.grid()
        plt.tight_layout()
        plt.show()


# --------------------------------------------------------
# Helper
# --------------------------------------------------------
def plot_single_series(df: pd.DataFrame, col: str, title: str = None):
    """Plot a single column of the weather dataset."""
    if col not in df.columns:
        print(f"Column '{col}' not found.")
        return
    ax = df[col].plot(figsize=(12,4))
    ax.set_title(title or col.upper())
    ax.set_ylabel("Irradiance [W/m²]")
    ax.set_xlabel("Time")
    ax.grid(True)
    plt.tight_layout()
    plt.show()



# --------------------------------------------------------
# Example usage (standalone execution)
# --------------------------------------------------------

if __name__ == "__main__":
    """
    Standalone example for:
    - fetching DWD weather data
    - quick inspection plots
    - monthly irradiation aggregation

    This block is intended for testing and preprocessing only.
    """

    # --- Configuration ---
    cfg = DWDWeatherConfig(
        start="2022-01-01 00:00",
        end="2022-12-31 23:50",
        auto_select=True,
        save_path="../../data/inputs/Wetterdaten_10min_DWD/wetter_daten_2018_10min.csv",
        plot_date="2022-07-21",
        plot_range=("2022-01-01", "2022-12-31"),
        use_dirint=True,
    )

    # --- Run data pipeline ---
    df = DWDWeatherFetcher(cfg).run()

    # --- Quick inspection plots ---
    plot_single_series(df, "dni", "Direct Normal Irradiance (DNI)")
    plot_single_series(df, "ghi", "Global Horizontal Irradiance (GHI)")
    plot_single_series(df, "dhi", "Diffuse Horizontal Irradiance (DHI)")

    # ========================================================
    # Monthly irradiation (10-min data → kWh/m²)
    # ========================================================

    # Ensure non-negative irradiance values
    df_rad = df[["ghi", "dhi", "dni"]].clip(lower=0)

    # Conversion factor: 10 min → hours → kWh
    factor = (10 / 60) / 1000  # = 1/6000

    # Aggregate monthly sums
    monthly = pd.DataFrame({
        "ghi": df_rad["ghi"].resample("MS").sum() * factor,
        "dhi": df_rad["dhi"].resample("MS").sum() * factor,
        "dni": df_rad["dni"].resample("MS").sum() * factor,
    })

    monthly.index = monthly.index.to_period("M")

    # --- Output ---
    print(monthly)

    # --- Plot ---
    monthly.plot(kind="bar", figsize=(12, 5))
    plt.ylabel("Monthly irradiation [kWh/m²]")
    plt.title("Monthly solar irradiation")
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()

