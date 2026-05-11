# Übergabefertig kommentiert JB
import pvlib
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import LineString, Point
from typing import List
import math
import os
import matplotlib.pyplot as plt
import pandas as pd
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.bifacial.pvfactors import pvfactors_timeseries
from pvlib import pvsystem
from dataclasses import dataclass

# Global pvlib imports
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
cec_inverters = pvlib.pvsystem.retrieve_sam('CECInverter')
temp_models_sapm = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']


@dataclass(frozen=True)
class PVType:
    """
    Dataclass representing a photovoltaic (PV) system configuration.
    It bundles all relevant parameters of a PV installation, including:
    - Identification and geometric orientation (azimuth, tilt)
    - Module and inverter configuration as well as system layout
    - Optional bifacial properties (rear-side gain, albedo, ground coverage)
    - Mounting type and tracking behavior (fixed or single-axis tracking)
    The structure allows consistent definition and comparison of different PV system types.
    """
    # 1. Identification / Position
    id: int
    name: str
    azimut: float | str | None = None               # Orientation in degrees (0–360) or "variable"
    tilt: float | None = None                       # Tilt angle in degrees (0 = horizontal, 90 = vertical)

    # 2. Module and system configuration
    module: str | None = None                       # PV module model name (e.g., from database)
    inverter: str | None = None                     # Inverter model name
    temp_model: str | None = None                   # Temperature model used for cell temperature calculation
    modules_per_string: int | None = None           # Number of modules connected in series (per string)
    strings_per_inverter: int | None = None         # Number of strings connected to one inverter
    row_height: float | None = None                 # Height of the module row in meters
    row_width: float | None = None                  # Width of the module row in meters

    # 3. Bifacial properties
    # --- Simplified bifacial model ---             # Simplified bifacial gain factor.
    bifazial: float | None = None                   # This value is ONLY used if is_bifacial_detailed = False.
                                                    # Bifaciality factor (0-1)
    # --- Detailed bifacial model ---
    is_bifacial_detailed: bool = False              # Use detailed bifacial model (e.g., pvlib/pvfactors)
    bifaciality: float | None = None                # Rear-side efficiency factor (0–1)
    gcr: float | None = None                        # Ground coverage ratio (module area / ground area)
    albedo: float | None = None                     # Ground reflectivity (typically 0.2–0.3)

    # 4. Mounting / Tracking
    mount_type: str = "fixed"                       # Mount type: "fixed" or "singleaxis"
    axis_tilt: float = 0.0                          # Tilt of the rotation axis in degrees
    axis_azimuth: float = 0.0                       # Axis direction (0 = north-south, 90 = east-west)
    max_angle: float = 60.0                         # Maximum rotation angle in degrees
    backtrack: bool = True                          # Enables backtracking to reduce shading

PV_TYPEN = [
    # 1. Windschutzwand
    PVType(
        # 1. Identifikation / Position
        id=1,
        name="Windschutzwand",
        azimut="variabel",
        tilt=90,

        # 2. Modul- und Systemtechnik
        module="Canadian_Solar_CS6X_300M__2013_",
        inverter="ABB__PVI_3_0_OUTD_S_US__208V_",
        temp_model="open_rack_glass_glass",
        modules_per_string=4,
        strings_per_inverter=1,
        row_height=3.0,
        row_width=4.0,

        # 3. Bifaziale Eigenschaften
        # --- Simplified bifacial model --
        bifazial=0.2,                       # 20% annual energy yield if simplified bifacial modelling is used
        # --- Detailed bifacial model ---
        is_bifacial_detailed=False,         # False -> detailed bifacial parameters below are ignored
        bifaciality=0.75,                   # Rückseitenwirkungsgrad
        gcr=0.35,                           # Bodenbedeckungsgrad
        albedo=0.2,                         # Bodenreflexion

        # 4. Tracking / Nachführung (fixe Wand, kein Tracking nötig)
        mount_type="fixed"
    ),

    # 2. Schallschutzwand
    PVType(
        id=2,
        name="Schallschutzwand",
        azimut="variabel",
        tilt=90,

        module="Canadian_Solar_CS6X_300M__2013_",
        inverter="ABB__PVI_3_0_OUTD_S_US__208V_",
        temp_model="open_rack_glass_glass",
        modules_per_string=4,
        strings_per_inverter=1,
        row_height=3.0,
        row_width=4.0,

        bifazial=0,                             # monofacial PV system
        is_bifacial_detailed=False,
        bifaciality=0.80,
        gcr=0.35,
        albedo=0.2,

        mount_type="fixed"
    ),

    # 3. Schallschutzwand_Dach
    PVType(
        id=3,
        name="Schallschutzwand_Dach",
        azimut="variabel",
        tilt=30,

        module="Canadian_Solar_CS6X_300M__2013_",
        inverter="ABB__PVI_3_0_OUTD_S_US__208V_",
        temp_model="open_rack_glass_glass",
        modules_per_string=4,
        strings_per_inverter=1,
        row_height=3.0,
        row_width=4.0,

        bifazial=0,
        is_bifacial_detailed=False,
        bifaciality=0.80,
        gcr=0.35,
        albedo=0.2,

        mount_type="fixed"
    ),

    # 4. Böschung
    PVType(
        id=4,
        name="Böschung",
        azimut="variabel",
        tilt=30,

        module="Canadian_Solar_CS6X_300M__2013_",
        inverter="ABB__PVI_3_0_OUTD_S_US__208V_",
        temp_model="open_rack_glass_glass",
        modules_per_string=4,
        strings_per_inverter=1,
        row_height=3.0,
        row_width=4.0,

        bifazial=0,
        is_bifacial_detailed=False,
        bifaciality=0.80,
        gcr=0.35,
        albedo=0.2,

        mount_type="fixed"
    ),

    # 5. Freifläche_bzw_Agri_geneigt
    PVType(
        id=5,
        name="Freifläche_bzw_Agri_tracking",
        azimut=None,
        tilt=None,

        module="Canadian_Solar_CS6X_300M__2013_",
        inverter="ABB__PVI_3_0_OUTD_S_US__208V_",
        temp_model="open_rack_glass_glass",
        modules_per_string=2,
        strings_per_inverter=1,
        row_height=3.0,
        row_width=1.0,

        bifazial=0.1,
        is_bifacial_detailed=False,
        bifaciality=0.7,
        gcr=0.35,
        albedo=0.2,

        mount_type="singleaxis",
        axis_tilt=0,
        axis_azimuth=0,
        max_angle=60,
        backtrack=True
    ),

    # 6. Agri_vertikal
    PVType(
        id=6,
        name="Agri_vertikal",
        azimut=90,
        tilt=90,

        module="Canadian_Solar_CS6X_300M__2013_",
        inverter="ABB__PVI_3_0_OUTD_S_US__208V_",
        temp_model="open_rack_glass_glass",
        modules_per_string=1,
        strings_per_inverter=1,
        row_width=1.0,

        bifazial=0,
        is_bifacial_detailed=False,
        bifaciality=None,
        gcr=None,
        albedo=None,

        mount_type="fixed"
    ),

    # 7. Haus_Dach
    PVType(
        id=7,
        name="Haus_Dach",
        azimut=180,
        tilt=30,

        module="Canadian_Solar_CS6X_300M__2013_",
        inverter="ABB__PVI_3_0_OUTD_S_US__208V_",
        temp_model="open_rack_glass_glass",
        modules_per_string=2,
        strings_per_inverter=1,
        row_width=1.0,

        bifazial=0,
        is_bifacial_detailed=False,
        bifaciality=None,
        gcr=None,
        albedo=None,

        mount_type="fixed"
    ),
]

class AzimutCalculator:
    """
    Calculates PV orientation (azimuth) along a geometry (point or line)
    and exports the results to a CSV file.
    """
    def __init__(self, geojson_path: str, step_size: float, pv_type: PVType, output_csv_path: str):
        self.geojson_path = geojson_path                        # Path to the GeoJSON file
        self.step_size = step_size                              # Step size [m] in which the geometry will be equipped
                                                                # with individual PV Systems (Significant on Performance)
        self.pv_type = pv_type                                  # PV Type from PV Type dataclass list
        self.output_csv_path = output_csv_path                  # Path for the CSV-Export of calculated point coordinates

        self.gdf = None                                         # GeoDataFrame red from the GeoJSON path
        self.merged_line: LineString | Point | None = None      # For the case of multiple lines in the geometry, lines are merged
        self.number_of_points: List[Point] = []                 # Number of calculated Points
        self.point_azimut_list: List[tuple[Point, float]] = []  # List of calculated points with their azimuth

    # ---------------- Geometry ----------------
    def load_geometry(self) -> LineString | Point:
        """Load GeoJSON, project to UTM zone 32N, and unify geometries."""
        try:
            self.gdf = gpd.read_file(self.geojson_path)
        except Exception:
            self.gdf = gpd.read_file(self.geojson_path)  # fallback

        self.gdf = self.gdf.to_crs(epsg=25832)
        self.merged_line = unary_union(self.gdf.geometry)
        return self.merged_line

    def interpolate_points(self) -> List[Point]:
        """Interpolate points along the line according to the step size."""
        if self.merged_line.geom_type == "Point":
            self.number_of_points = [self.merged_line]
            return self.number_of_points

        total_length = self.merged_line.length
        self.number_of_points = [
            self.merged_line.interpolate(distance)
            for distance in range(0, int(total_length), self.step_size)
        ]

        # Line length is zero → add a single point
        if not self.number_of_points and total_length == 0:
            self.number_of_points = [self.merged_line.interpolate(0)]

        return self.number_of_points

    # ---------------- Points & Azimuth ----------------
    def _append_point(self, point: Point, azimut: float) -> None:
        """Append a point and azimuth to the internal list, ensure it's a Point."""
        if not isinstance(point, Point):
            point = Point(point)
        self.point_azimut_list.append((point, azimut))

    def calculate_azimut(self) -> List[Point]:
        """Calculate azimuth for all interpolated points."""
        self.load_geometry()
        self.interpolate_points()

        if len(self.number_of_points) == 1:
            p = self.number_of_points[0]
            az = 180.0 if self.pv_type.azimut == "variabel" else self.pv_type.azimut
            self._append_point(p, az)
        else:
            for i in range(len(self.number_of_points) - 1):
                p1 = self.number_of_points[i]
                p2 = self.number_of_points[i + 1]
                dx, dy = p2.x - p1.x, p2.y - p1.y
                theta_deg = math.degrees(math.atan2(dy, dx))
                az = (90 - theta_deg) % 360 if self.pv_type.azimut == "variabel" else self.pv_type.azimut
                self._append_point(p1, az)

        return [p for p, _ in self.point_azimut_list]

    # ---------------- GeoDataFrame & CSV ----------------
    def to_gdf(self) -> gpd.GeoDataFrame:
        """Create a GeoDataFrame from the points and azimuth list."""
        points = [p if isinstance(p, Point) else p[0] for p, _ in self.point_azimut_list]
        azimuts = [a for _, a in self.point_azimut_list]

        gdf = gpd.GeoDataFrame(
            {"azimut": azimuts},
            geometry=points,
            crs="EPSG:25832",
        )

        gdf = gdf.to_crs(epsg=4326)  # convert to lat/lon
        gdf["latitude"] = gdf.geometry.y
        gdf["longitude"] = gdf.geometry.x
        gdf["pv_type_id"] = self.pv_type.id
        gdf["pv_type_name"] = self.pv_type.name
        gdf["tilt"] = self.pv_type.tilt
        return gdf

    def export_to_csv(self) -> None:
        """Export calculated points and azimuths as CSV."""
        gdf = self.to_gdf()
        gdf[["latitude", "longitude", "azimut", "tilt", "pv_type_id", "pv_type_name"]].to_csv(
            self.output_csv_path, index=False
        )

    # ---------------- Full Workflow ----------------
    def run(self) -> gpd.GeoDataFrame:
        """Run full azimuth calculation and export to CSV."""
        self.calculate_azimut()
        self.export_to_csv()
        return self.to_gdf()



class AzimutVisualizer:
    """
    Visualizes PV points with their azimuth directions on a 2D plot.

    Parameters
    ----------
    calculator : AzimutCalculator
        An instance of AzimutCalculator containing PV points and azimuths.
    """

    def __init__(self, calculator):
        self.calc = calculator

    def plot(self, every_nth_arrow: int = 10):
        """
        Plot PV points and azimuth arrows.

        Parameters
        ----------
        every_nth_arrow : int, optional
            Only plot every nth arrow for clarity (default is 10).
        """
        # Extract data from the calculator
        gdf = self.calc.gdf                                             # Original geometry of PV lines/polygons
        points = [p for p, _ in self.calc.point_azimut_list]
        azimuts = [a for _, a in self.calc.point_azimut_list]           # Corresponding azimuths in degrees
        pv_typ = getattr(self.calc.pv_type, "name", "Unknown PV Type")  # PV type name

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_title(f"PV Points with Azimuth ({pv_typ})")
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Y [m]")

        # Draw direction arrows for PV points
        for i in range(0, len(points), every_nth_arrow):
            az = azimuts[i]
            if isinstance(az, (int, float)):
                # Convert azimuth to arrow direction
                dx = 5 * math.cos(math.radians(90 - az))
                dy = 5 * math.sin(math.radians(90 - az))
                ax.arrow(points[i].x, points[i].y, dx, dy,
                         head_width=2, fc="blue", ec="blue")

        # Plot the original PV line or polygon
        if gdf is not None and not gdf.empty:
            gdf.plot(ax=ax, color="gray", linewidth=2)

        # Plot PV points as red dots
        geo_gdf = gpd.GeoDataFrame(
            geometry=[Point(pt.x, pt.y) for pt in points],
            crs=gdf.crs if gdf is not None else None
        )
        geo_gdf.plot(ax=ax, color="red", markersize=5)

        # Final plot adjustments
        plt.grid(True, alpha=0.3)
        plt.axis("equal")
        plt.show()


class PV_System:
    """
    PV-System-Wrapper:
    - geojson_path: Pfad zur Linien-Geometrie (z. B. Autobahnabschnitt)
    - pvtypes: Liste von PVType-Objekten
    """

    def __init__(self, geojson_path, pvtypes, step_size, weather_df, base_output_dir):
        self.geojson_path = geojson_path                    # Path to the GeoJSON file
        self.pvtypes = pvtypes                              # Step size [m] in which the geometry will be equipped with individual PV Systems (Significant on Performance)
        self.step_size = step_size                          # PV Type from PV Type dataclass list
        self.weather_df = weather_df                        # Weather data from DWD-script
        self.base_output_dir = base_output_dir              # z. B. "./Input/punkte"

    # ------------Punkte + Azimut generieren--------------------
    def generate_pv_points(self):
        """
        Für jeden PV-Typ werden Punkte + Azimut berechnet und
        getrennt als CSV gespeichert.
        """
        results = {}

        geo_name = os.path.splitext(os.path.basename(self.geojson_path))[0]

        for pv_type in self.pvtypes:
            output_csv = os.path.join(
                self.base_output_dir,
                f"{geo_name}_punkte_{pv_type.id}_{pv_type.name}.csv".replace(" ", "_"),
            )
            calc = AzimutCalculator(
                geojson_path=self.geojson_path,
                step_size=self.step_size,
                pv_type=pv_type,
                output_csv_path=output_csv,
            )
            gdf_points = calc.run()
            results[pv_type.id] = gdf_points

        return results

    # -------------PV Simulation der Punkte-------------------------
    def _build_mount(self, pv_type: PVType, row):
        """
        Builds PV system mount in regards to pvtype configuration
        """
        if getattr(pv_type, "mount_type", "fixed") == "singleaxis":
            if pv_type.backtrack and pv_type.gcr is None:
                raise ValueError("Tracking mit backtrack=True braucht pv_type.gcr.")
            return pvsystem.SingleAxisTrackerMount(
                axis_tilt=float(pv_type.axis_tilt),
                axis_azimuth=float(pv_type.axis_azimuth),
                max_angle=float(pv_type.max_angle),
                backtrack=bool(pv_type.backtrack),
                gcr=float(pv_type.gcr) if pv_type.gcr is not None else None,
            )
        else:
            return pvsystem.FixedMount(
                surface_tilt=float(row["tilt"]),
                surface_azimuth=float(row["azimut"]),
            )

    def _simulate_monofacial_point(self, pv_type: PVType, row):
        """
        Simulates one monofacial point in regards to pvtype configuration
        """
        module_params = sandia_modules[pv_type.module]
        inverter_params = cec_inverters[pv_type.inverter]
        temp_params = temp_models_sapm[pv_type.temp_model]

        loc = Location(row["latitude"], row["longitude"], tz="Europe/Berlin")

        mount = self._build_mount(pv_type, row)

        array = pvsystem.Array(
            mount=mount,
            module_parameters=module_params,
            temperature_model_parameters=temp_params,
            albedo=pv_type.albedo,
        )

        system = pvsystem.PVSystem(
            arrays=[array],
            inverter_parameters=inverter_params,
            modules_per_string=pv_type.modules_per_string,
            strings_per_inverter=pv_type.strings_per_inverter,
        )

        mc = ModelChain(system, loc)
        mc.run_model(self.weather_df)
        return mc.results.ac

    def _simulate_bifacial_point(self, pv_type: PVType, row):
        """
        Simulates one bifacial point in regards to pvtype configuration
        """
        loc = Location(row["latitude"], row["longitude"], tz="Europe/Berlin")
        times = self.weather_df.index
        solar_position = loc.get_solarposition(times)

        # 1) Orientierung: für Wände besser FixedMount
        mount = pvsystem.FixedMount(
            surface_tilt=float(row["tilt"]),
            surface_azimuth=float(row["azimut"]),
        )
        orientation = mount.get_orientation(
            solar_zenith=solar_position["apparent_zenith"],
            solar_azimuth=solar_position["azimuth"],
        )

        # 2) pvfactors: nutze Wetterdaten (dni/dhi)
        irrad = pvfactors_timeseries(
            solar_azimuth=solar_position["azimuth"],
            solar_zenith=solar_position["apparent_zenith"],
            surface_azimuth=orientation["surface_azimuth"],
            surface_tilt=orientation["surface_tilt"],
            axis_azimuth=float(row["azimut"]),
            timestamps=times,
            dni=self.weather_df["dni"],
            dhi=self.weather_df["dhi"],
            gcr=pv_type.gcr,
            pvrow_height=pv_type.row_height,
            pvrow_width=pv_type.row_width,
            albedo=pv_type.albedo,
            n_pvrows=3,
            index_observed_pvrow=1,
        )
        irrad = pd.concat(irrad, axis=1)

        # 3) Effective Irradiance bilden
        if pv_type.bifaciality is None:
            raise ValueError(
                f"PVType '{pv_type.name}' ist als bifacial_detailed markiert, hat aber keine bifaciality definiert."
            )
        bifaciality = pv_type.bifaciality
        irrad["effective_irradiance"] = (
            irrad["total_abs_front"] + irrad["total_abs_back"] * bifaciality
        )

        # 4) System + MC
        module_params = sandia_modules[pv_type.module]
        inverter_params = cec_inverters[pv_type.inverter]
        temp_params = temp_models_sapm[pv_type.temp_model]

        array = pvsystem.Array(
            mount=mount,
            module_parameters=module_params,
            temperature_model_parameters=temp_params,
        )
        system = pvsystem.PVSystem(
            arrays=[array],
            inverter_parameters=inverter_params,
            modules_per_string=pv_type.modules_per_string,
            strings_per_inverter=pv_type.strings_per_inverter,
        )

        mc = ModelChain(system, loc, aoi_model="no_loss")

        # 5) DataFrame für run_model_from_effective_irradiance bauen
        #    pvlib erwartet hier eine Spalte 'effective_irradiance'
        data = pd.DataFrame(index=self.weather_df.index)
        data["effective_irradiance"] = irrad["effective_irradiance"].reindex(data.index)

        # Falls deine Wetterdaten diese Spalten haben, mitgeben:
        if "temp_air" in self.weather_df.columns:
            data["temp_air"] = self.weather_df["temp_air"]
        if "wind_speed" in self.weather_df.columns:
            data["wind_speed"] = self.weather_df["wind_speed"]

        # pvlib erwartet jetzt nur noch dieses DataFrame als Argument
        mc.run_model_from_effective_irradiance(data)

        return mc.results.ac

    # --------------------Energiesimulation für PV-Typ-------------------
    def simulate_pv_type_energy(self, pv_type: PVType, points_csv_path: str):
        """
        Liest die Punkte-CSV eines PV-Typs ein, simuliert alle Punkte
        (mono- oder bifazial) und gibt zurück:
        - energy_kwh: Jahresenergie [kWh/Jahr]
        - total_ac: Zeitreihe der AC-Gesamtleistung [W]
        """
        df_points = pd.read_csv(points_csv_path)

        total_type_ac_w = None

        for _, row in df_points.iterrows():
            if getattr(pv_type, "is_bifacial_detailed", False):
                ac = self._simulate_bifacial_point(pv_type,row) * pv_type.modules_per_string * pv_type.strings_per_inverter
            else:
                ac = self._simulate_monofacial_point(pv_type,row) * pv_type.modules_per_string * pv_type.strings_per_inverter

            if total_type_ac_w is None:
                total_type_ac_w = ac
            else:
                total_type_ac_w = total_type_ac_w + ac
        dt_hours = (self.weather_df.index[1] - self.weather_df.index[0]).total_seconds() / 3600.0
        energy_type_Wh = (total_type_ac_w * dt_hours).sum()

        # einfacher Mehrertragsfaktor nur für "nicht-detaillierte" Bifazialität
        if (not getattr(pv_type, "is_bifacial_detailed", False)) and getattr(pv_type, "bifazial", 0) > 0:
            energy_type_Wh *= (1 + pv_type.bifazial)

        energy_type_kWh = energy_type_Wh / 1000.0

        return energy_type_kWh, total_type_ac_w


