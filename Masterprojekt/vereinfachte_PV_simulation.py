from dataclasses import dataclass
import pandas as pd
import pvlib
from pvlib.location import Location
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain


@dataclass(frozen=True)
class PVType:
    """
    Vereinfachte PV-Typ-Struktur zur Orientierung.

    In unserem Projekt werden PV-Systeme objektorientiert beschrieben,
    damit unterschiedliche Anlagenkonzepte flexibel simuliert werden können.
    """
    name: str
    azimuth_deg: float          # 180 = Süden, 90 = Osten, 270 = Westen
    tilt_deg: float             # 0 = horizontal, 90 = vertikal
    row_spacing_m: float
    module_width_m: float
    module_height_m: float
    tracking: bool = False


PV_TYPES = [
    PVType(
        name="Vertical Agri-PV",
        azimuth_deg=180,
        tilt_deg=90,
        row_spacing_m=10.0,
        module_width_m=2.0,
        module_height_m=1.2,
        tracking=False,
    ),
    PVType(
        name="Tilted Agri-PV",
        azimuth_deg=180,
        tilt_deg=20,
        row_spacing_m=8.0,
        module_width_m=2.0,
        module_height_m=1.2,
        tracking=False,
    ),
    PVType(
        name="Single-axis tracking Agri-PV",
        azimuth_deg=180,
        tilt_deg=0,
        row_spacing_m=12.0,
        module_width_m=2.0,
        module_height_m=1.2,
        tracking=True,
    ),
]


def simulate_pv_generation(
    pv_type: PVType,
    weather_df: pd.DataFrame,
    latitude: float = 51.08579,
    longitude: float = 6.47554,
) -> pd.Series:
    """
    Vereinfachte PV-Ertragssimulation mit pvlib.

    Input:
    - pv_type: definierter PV-Anlagentyp
    - weather_df: Wetterdaten mit 15-min-Zeitindex und Spalten:
        ghi, dhi, dni, temp_air, wind_speed

    Output:
    - AC-Leistungszeitreihe in W
    """

    location = Location(
        latitude=latitude,
        longitude=longitude,
        tz="Europe/Berlin",
        altitude=80,
        name="Juechen"
    )

    # Beispielhafte Standardkomponenten aus pvlib-Datenbanken
    modules = pvlib.pvsystem.retrieve_sam("SandiaMod")
    inverters = pvlib.pvsystem.retrieve_sam("CECInverter")

    module = modules["Canadian_Solar_CS6X_300M__2013_"]
    inverter = inverters["ABB__PVI_3_0_OUTD_S_US__208V_"]

    temperature_model = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"]

    system = PVSystem(
        surface_tilt=pv_type.tilt_deg,
        surface_azimuth=pv_type.azimuth_deg,
        module_parameters=module,
        inverter_parameters=inverter,
        temperature_model_parameters=temperature_model,
        modules_per_string=4,
        strings_per_inverter=1,
    )

    model_chain = ModelChain(
        system,
        location,
        aoi_model="physical",
        spectral_model="no_loss"
    )

    model_chain.run_model(weather_df)

    ac_power_w = model_chain.results.ac.fillna(0)

    return ac_power_w


def annual_energy_kwh(ac_power_w: pd.Series, timestep_hours: float = 0.25) -> float:
    """
    Berechnet aus einer AC-Leistungszeitreihe die Jahresenergie.

    Bei 15-min-Auflösung gilt:
    Energie [Wh] = Leistung [W] * 0.25 h
    Energie [kWh] = Energie [Wh] / 1000
    """
    return (ac_power_w.sum() * timestep_hours) / 1000