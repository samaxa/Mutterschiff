#Übergabefertig kommentiert JB
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import pandas as pd

# =================================
# Input from the streamlit website
# =================================

@dataclass
class GuiInput:
    """
    All website input parameters.
    The following abbreviations are used in the variable names:
        h = highway, el = energy landscape, i = industry, geh = green energy hub, bs = battery storage
    """

    # Energy production
    # PV Highway
    h_highways: Optional[List[str]] = None              # IDs of the selected highways
    h_pv_types: Optional[List[str]] = None              # PV types that the highway will be equipped with

    # Energy landscape
    el_build_state: Optional[int] = None                # Build state [%]
    el_pv_type: Optional[int] = None                    # PV types that the energy landscape will be equipped with
    el_tractor_width: Optional[float] = None            # [m]
    el_tractor_length: Optional[float] = None           # [m]
    el_tractor_turn_radius: Optional[float] = None      # [m]

    # Energy consumption
    # Industry area
    i_heat_cooling_electric: Optional[bool] = None     # Electric Heating/Cooling active
    i_companies: Optional[List[int]] = None            # Company typ list

    # Green Energy Hub
    geh_h2_load_scenario: Optional[str] = None          # Electric load of hydrogen scenario: 2022, 2030, 2050
    geh_e_load_scenario: Optional[str] = None           # Electric load of electric charge scenario: 2022, 2030, 2050

    # Battery storage
    bs_efficiency: Optional[float] = None               # Roundtrip efficience [0–1]
    bs_energy_kwh: Optional[float] = None               # Capacity [kWh]
    bs_c_rate: Optional[float] = None                   # C-rate

    # Jüchen Süd
    js_scenario: Optional[str] = None


# =========================
# Output der Simulation
# =========================

@dataclass
class SimOutput:
    """
    All results that are shown on the website.
    The following abbreviations are used in the variable names:
        h = highway, el = energy landscape, i = industry, geh = green energy hub, bs = battery storage
    """

    # Energy amounts [kWh]
    h_sum_energy_kwh: float | None = None
    el_sum_energy_kwh: float | None = None
    geh_sum_energy_kwh: float | None = None
    i_sum_energy_kwh: float | None = None
    js_sum_energy_kwh: float | None = None

    # Max power [kW] - all values production and consumption are positive,
    h_max_power_kw: float | None = None
    el_max_power_kw: float | None = None
    geh_max_power_kw: float | None = None
    i_max_power_kw: float | None = None
    js_max_power_kw: float | None = None

    # pandas dataframes with load profiles
    res_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    bs_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Battery statistics
    bs_stats: dict = field(default_factory=dict)


    # System balance
    bal_energy_kwh: float | None = None
    bal_coverage_rate: float | None = None                          # Balanced Autarky (incl. back and forth with grid)
    bal_power_max_kw: float | None = None
    bal_power_min_kw: float | None = None

    # Internal Generation KPIs
    ee_self_consumption: float | None = None                        # Direct self consumption of generated energy in relation to total generation
    autarky: float | None = None                                    # Direct self consumption of generated energy in relation to demand

    # Error texts
    h_error_text: str | None = None
    el_error_text: str | None = None
    geh_error_text: str | None = None
    i_error_text: str | None = None
    js_error_text: str | None = None

    # Debug
    h_number_of_points: int | None = None
    el_pv_length: float | None = None
