# Übergabefertig kommentiert SM
import os
import osmnx as ox
import geopandas as gpd
from shapely.geometry import LineString, box
import math
import folium
import webbrowser

# --------------------------------------------------------
# Paths
# --------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
base_output = os.path.join(script_dir, "..", "data", "outputs", "geometry")

# --------------------------------------------------------
# Direction utilities
# --------------------------------------------------------
class DirectionUtilis:
    """
    Utility functions for orienting and filtering highway geometries
    by driving direction.
    """
    @staticmethod
    def apply_oneway_orientation(geom, oneway):
        """
        Reverse line geometry if the OSM oneway flag indicates
        opposite driving direction.
        """
        coords = list(geom.coords)
        if oneway == -1:
            coords = coords[::-1]
        return LineString(coords)

    @staticmethod
    def calculate_bearing(geom):
        """
        Calculate bearing angle of a line geometry in degrees.
        """
        x1, y1 = geom.coords[0]
        x2, y2 = geom.coords[-1]
        angle = math.degrees(math.atan2(x2 - x1, y2 - y1))
        return (angle + 360) % 360

    @staticmethod
    def is_within_direction(angle, target, tolerance=30):
        """
        Check whether a bearing angle lies within a given tolerance
        of the target direction.
        """
        delta = abs((angle - target + 180) % 360 - 180)
        return delta <= tolerance

    @staticmethod
    def richtung_to_angle(richtung):
        """
        Map cardinal direction labels to bearing angles.
        """
        mapping = {"nord": 0, "ost": 90, "süd": 180, "west": 270}
        return mapping.get(richtung, None)

# --------------------------------------------------------
# Highway extraction from OSM
# --------------------------------------------------------
class HighwayExtractor:
    """
    Extract motorway geometries from OpenStreetMap and filter them
    by reference and direction.
    """

    def __init__(self, region="Nordrhein-Westfalen, Germany", highway_refs=None):
        """
        Parameters
        ----------
        region : str
            Region from which OSM motorway data is loaded.
        highway_refs : list[str] | None
            List of motorway references, e.g. ['A 46', 'A 44'].
            If None, all motorways in the region are considered.
        """
        self.region = region
        self.highway_refs = highway_refs

        # Load motorway graph from OSM
        self.graph = ox.graph_from_place(region, network_type='drive', custom_filter='["highway"~"motorway"]')
        # Convert graph edges to GeoDataFrame
        self.edges = ox.graph_to_gdfs(self.graph, nodes=False, edges=True)

        # Optional filtering by motorway reference
        if highway_refs:
            self.edges = self.edges[self.edges['ref'].isin(highway_refs)]

    def highway_gdf_in_bb(self, list_indiv_bb):
        """
        Extract motorway segments intersecting a list of bounding boxes
        and filter them by requested direction.

        Parameters
        ----------
        list_indiv_bb : list[dict]
            List of dictionaries with:
            - "geometry": shapely bounding box
            - "richtung": target direction

        Returns
        -------
        GeoDataFrame
            Filtered motorway segments.
        """
        highway_edges_cut = []

        for bbox in list_indiv_bb:
            relevant_edges = []
            for _, edge in self.edges.iterrows():
                if edge.geometry.intersects(bbox["geometry"]):
                    cut_geom = edge.geometry.intersection(bbox["geometry"])
                    if not cut_geom.is_empty and isinstance(cut_geom, LineString):
                        relevant_edges.append((edge, cut_geom))

            richtung = bbox["richtung"]
            passt_edges = []

            # Apply directional filtering
            for edge, cut_geom in relevant_edges:
                oneway = edge.get('oneway', False)
                oneway = -1 if str(oneway) == '-1' else (1 if oneway is True else 0)
                oriented_geom = DirectionUtilis.apply_oneway_orientation(cut_geom, oneway)
                angle = DirectionUtilis.calculate_bearing(oriented_geom)
                if richtung == "beide" or (DirectionUtilis.richtung_to_angle(richtung) is not None and DirectionUtilis.is_within_direction(angle, DirectionUtilis.richtung_to_angle(richtung), tolerance=45)):
                    passt_edges.append({
                        "geometry": oriented_geom,
                        "richtung": richtung,
                        "ref": edge.get("ref", "")
                    })

            highway_edges_cut.extend(passt_edges)

        return gpd.GeoDataFrame(highway_edges_cut, crs=self.edges.crs) if highway_edges_cut else gpd.GeoDataFrame(columns=["geometry", "richtung", "ref"])


# --------------------------------------------------------
# Geometry handling: visualization and export
# --------------------------------------------------------
class GeometryHandler:
    """
    Handles visualization and export of extracted motorway geometries.
    """
    def __init__(self, gdf, base_path):
        """
        Parameters
        ----------
        gdf : GeoDataFrame
            GeoDataFrame containing filtered highway geometries.
        base_path : str
            Output directory for HTML maps and GeoJSON files.
        """
        self.gdf = gdf
        self.base_path = base_path


    def plot_geometry_on_map(self, map_filename="karte.html"):
        """
        Plot extracted geometries on an interactive folium map.
        """
        gdf_4326 = self.gdf.to_crs(epsg=4326)

        if gdf_4326.empty:
            print("GeoDataFrame is empty. No geometries to display.")
            return

        bounds = gdf_4326.total_bounds
        center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

        m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")
        folium.GeoJson(gdf_4326).add_to(m)

        os.makedirs(self.base_path, exist_ok=True)
        map_dir_filename = os.path.join(self.base_path, map_filename)
        m.save(map_dir_filename)
        webbrowser.open(map_dir_filename)


    def save_geometry(self):
        """
        Save filtered geometry as GeoJSON file.
        """
        gdf = self.gdf[self.gdf["ref"].notna()]

        if gdf.empty:
            print("No valid geometry available for export.")
            return None

        autobahn = gdf["ref"].iloc[0].replace(" ", "").lower()
        richtung = gdf["richtung"].iloc[0].lower()
        filename = f"{autobahn}_{richtung}.geojson"
        output_path = os.path.join(self.base_path, filename)

        os.makedirs(self.base_path, exist_ok=True)
        gdf.to_file(output_path, driver="GeoJSON")

        print(f"GeoDataFrame saved to: {output_path}")
        return output_path


# --------------------------------------------------------
# Predefined motorway sections
# --------------------------------------------------------
vordefinierte_abschnitte = {
    "A46": {
        "abschnitte": [
            (6.44730, 51.09131, 6.46292, 51.09533),
            (6.49446, 51.09495, 6.51060, 51.09845),
            (6.51206, 51.09495, 6.52021, 51.09786),
        ]
    },
    "A44": {
        "abschnitte": [
            (6.474917, 51.03384, 6.50147, 51.085915),
        ]
    }
}

# --------------------------------------------------------
# Main function
# --------------------------------------------------------
def run_autobahn_geometrie(base_path):
    """Interactive workflow for selecting, visualizing and saving motorway geometries."""
    print("Available predefined sections:")

    for i, name in enumerate(vordefinierte_abschnitte):
        print(f"{i + 1}. {name}")

    auswahl = int(input("Select the motorway number to analyze: ")) - 1
    key = list(vordefinierte_abschnitte.keys())[auswahl]
    info = vordefinierte_abschnitte[key]
    richtung = input("Select direction (nord/sued/ost/west/beide): ").strip().lower()

    # Build bounding boxes for selected motorway section
    bbox_liste = [{
        "geometry": box(*coords),
        "richtung": richtung
    } for coords in info["abschnitte"]]

    # Extract and process geometries
    extractor = HighwayExtractor()
    gdf = extractor.highway_gdf_in_bb(bbox_liste)
    if not gdf.empty:
        gdf = gdf.to_crs(epsg=4326)
        handler = GeometryHandler(gdf, base_path)
        handler.plot_geometry_on_map()
        handler.save_geometry()
    else:
        print("No data found.")


# --------------------------------------------------------
# Example usage
# --------------------------------------------------------
# if __name__ == "__main__":
#      run_autobahn_geometrie(
#          base_path=base_output
#      )
