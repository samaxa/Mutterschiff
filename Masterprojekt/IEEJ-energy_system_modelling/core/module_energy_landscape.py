"""
Energielandschaft

Dieses Skript enthält modular aufgebaute Klassen zur:
- Einlesung einer eingebetteten GeoJSON-Fläche (WGS84)
- Auswahl des PV-Typs (horizontal/vertical)
- Abfrage der Traktorparameter (Breite, Länge, Wenderadius)
- Berechnung von Wende- und Fahrspurbreiten mit Sicherheitszuschlag von 1 m
- Berechnung der verfügbaren Nutzfläche (in m², reprojiziert in UTM)
- Generierung von PV Modulmitten als GeoJSON FeatureCollection

Technische Hinweise:
- Shapely wird für Geometrieoperationen verwendet.
- Flächen-/Längenberechnungen erfolgen in metrischem UTM (automatische Zonenwahl
  basierend auf Polygon-Zentroid) und werden für GeoJSON wieder in WGS84 zurückprojiziert.
"""

EMBEDDED_GEOJSON = '''{
	"type": "FeatureCollection",
	"features": [
		{
			"type": "Feature",
			"geometry": {
				"coordinates": [
					[
						[
							6.482341,
							51.08417
						],
						[
							6.479723,
							51.083678
						],
						[
							6.480485,
							51.082684
						],
						[
							6.478758,
							51.082283
						],
						[
							6.477481,
							51.081939
						],
						[
							6.475056,
							51.081292
						],
						[
							6.474895,
							51.081501
						],
						[
							6.474284,
							51.082508
						],
						[
							6.470116,
							51.081663
						],
						[
							6.470534,
							51.08113
						],
						[
							6.470996,
							51.08052
						],
						[
							6.471907,
							51.079465
						],
						[
							6.472031,
							51.079324
						],
						[
							6.473898,
							51.079334
						],
						[
							6.481081,
							51.070352
						],
						[
							6.483682,
							51.070877
						],
						[
							6.482266,
							51.072347
						],
						[
							6.480217,
							51.074727
						],
						[
							6.475062,
							51.081278
						],
						[
							6.476279,
							51.081612
						],
						[
							6.478769,
							51.082269
						],
						[
							6.479391,
							51.082414
						],
						[
							6.480496,
							51.08266
						],
						[
							6.485233,
							51.077318
						],
						[
							6.486654,
							51.075724
						],
						[
							6.490098,
							51.07232
						],
						[
							6.494658,
							51.07348
						],
						[
							6.493472,
							51.075023
						],
						[
							6.492298,
							51.07659
						],
						[
							6.491289,
							51.078228
						],
						[
							6.490409,
							51.079924
						],
						[
							6.489916,
							51.081043
						],
						[
							6.4891,
							51.082707
						],
						[
							6.488575,
							51.084163
						],
						[
							6.488349,
							51.085814
						],
						[
							6.487362,
							51.085585
						],
						[
							6.486161,
							51.085181
						],
						[
							6.484358,
							51.084669
						],
						[
							6.482341,
							51.08417
						]
					]
				],
			"type": "Polygon"
			},
			"properties": {
				"name": "Flaeche_Agri_PV"
			},
			"id": "E7ME4"
		}
	]
}'''

import json
from typing import Tuple, List, Dict, Any
from shapely.geometry import shape, Polygon, Point, mapping, LineString
from shapely.ops import transform
import pyproj
import math


class GeoJSONReader:
	"""Lädt eine GeoJSON-FeatureCollection (WGS84) und liefert Shapely-Objekte.

	Methoden:
	- load(): parsed Polygon in WGS84 und reprojiziert in UTM (metrische Einheit).
	"""

	def __init__(self, geojson_str: str):
		self.geojson_str = geojson_str

	def _choose_utm_crs(self, lon: float, lat: float) -> pyproj.CRS:
		zone = int((lon + 180) / 6) + 1
		if lat >= 0:
			epsg = 32600 + zone
		else:
			epsg = 32700 + zone
		return pyproj.CRS.from_epsg(epsg)

	def load(self) -> Tuple[Polygon, Polygon, pyproj.Transformer, pyproj.Transformer]:
		"""Parst das eingebettete GeoJSON und gibt zurück:
		(poly_wgs84, poly_utm, transformer_to_utm, transformer_to_wgs84)
		"""
		obj = json.loads(self.geojson_str)
		# Annahme: erste Feature enthält die Polygonfläche
		feat = obj.get("features", [])[0]
		geom = shape(feat["geometry"])  # in WGS84 (lon/lat)

		centroid = geom.representative_point()
		lon, lat = centroid.x, centroid.y
		utm_crs = self._choose_utm_crs(lon, lat)

		transformer_to_utm = pyproj.Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
		transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)

		proj_to_utm = lambda x, y: transformer_to_utm.transform(x, y)
		poly_utm = transform(proj_to_utm, geom)

		return geom, poly_utm, transformer_to_utm, transformer_to_wgs84


class PVTypeSelector:
	"""Fragt den PV-Typ ab ("horizontal", "vertical" oder "horizontal_tracking") via 1/2/3-Auswahl.

	Parameter:
	- default: Standardwert falls Enter gedrückt wird.
	- interactive: falls False, wird der Default zurückgegeben.
	"""

	VALID = ("horizontal", "vertical", "horizontal_tracking")

	@staticmethod
	def select(default: str = "horizontal", interactive: bool = True) -> str:
		if not interactive:
			return default

		options = {
			"1": "horizontal",
			"2": "vertical",
			"3": "horizontal_tracking",
		}
		default_key = next((k for k, v in options.items() if v == default), "1")
		prompt = (
			f"Bitte PV-Typ auswählen [Default: {default_key}]\n"
			"1) Horizontale PV-Anlage (aufgeständert, Ost-West)\n"
			"2) Vertikale PV-Anlage (Zaun, Nord-Süd)\n"
			"3) Horizontale PV-Anlage mit Single-Axis-Tracking (aufgeständert, Nord-Süd)\n"
			"Auswahl (1, 2 oder 3): "
		)
		choice = input(prompt).strip() or default_key
		if choice not in options:
			print("Ungültige Auswahl, verwende Default: %s" % options[default_key])
			return options[default_key]
		return options[choice]


class AusbauStatusSelector:
	"""Fragt den Ausbau-Status der Energielandschaft via 0/50/100-Auswahl ab.

	Werte:
	- 0: Kein Ausbau, keine Erzeugung
	- 50: Teil-Ausbau, 50% Erzeugung
	- 100: Voll-Ausbau, 100% Erzeugung
	"""

	VALID = (0, 50, 100)

	@staticmethod
	def select(default: int = 100, interactive: bool = True) -> int:
		if default not in AusbauStatusSelector.VALID:
			default = 100

		if not interactive:
			return default

		prompt = (
			f"Bitte Ausbau-Status auswählen [Default: {default}]\n"
			"0) 0%  - Kein Ausbau, keine Erzeugung\n"
			"50) 50% - Energielandschaft zur Hälfte ausgebaut, 50% Erzeugung\n"
			"100) 100% - Energielandschaft komplett gebaut, 100% Erzeugung\n"
			"Auswahl (0, 50 oder 100): "
		)

		raw = input(prompt).strip() or str(default)
		try:
			value = int(raw)
		except ValueError:
			print(f"Ungültige Auswahl '{raw}', verwende Default: {default}%")
			return default

		if value not in AusbauStatusSelector.VALID:
			print(f"Ungültige Auswahl '{value}', verwende Default: {default}%")
			return default

		return value


def apply_ausbau_status_to_reihen(geojson_reihen: Dict[str, Any], ausbau_status: int) -> Dict[str, Any]:
	"""Skaliert die erzeugten PV-Reihen gemäß Ausbau-Status (0/50/100)."""
	if not isinstance(geojson_reihen, dict):
		raise ValueError("geojson_reihen muss ein Dictionary sein")
	if geojson_reihen.get("type") != "FeatureCollection":
		raise ValueError("geojson_reihen.type muss 'FeatureCollection' sein")

	features = geojson_reihen.get("features", [])
	if not isinstance(features, list):
		raise ValueError("geojson_reihen['features'] muss eine Liste sein")

	if ausbau_status not in AusbauStatusSelector.VALID:
		raise ValueError("ausbau_status muss 0, 50 oder 100 sein")

	if ausbau_status == 100:
		selected_features = features
	elif ausbau_status == 0:
		selected_features = []
	else:  # 50%
		n_keep = int(round(len(features) * 0.5))
		selected_features = features[:n_keep]

	return {
		"type": "FeatureCollection",
		"features": selected_features,
	}


class TractorParameters:
	"""Container für Traktorparameter und Berechnung der Randzonen.

	Attribute:
	- width_m, length_m, turn_radius_m

	Methoden:
	- compute_wendestreifen_width(): Wende-/Rückzugsbreite inkl. 1 m Sicherheitszuschlag
	- compute_fahrspur_width(): Fahrspurbreite inkl. 1 m Sicherheitszuschlag
	"""

	def __init__(self, width_m: float, length_m: float, turn_radius_m: float):
		self.width_m = float(width_m)
		self.length_m = float(length_m)
		self.turn_radius_m = float(turn_radius_m)

	@staticmethod
	def from_input(
		interactive: bool = True,
		defaults: Tuple[float, float, float] = (12, 15, 9),
		width_m: Any = None,
		length_m: Any = None,
		turn_radius_m: Any = None,
	) -> "TractorParameters":
		# Wenn alle drei Werte übergeben wurden, verwende sie direkt.
		if width_m is not None and length_m is not None and turn_radius_m is not None:
			try:
				return TractorParameters(float(width_m), float(length_m), float(turn_radius_m))
			except ValueError:
				print("Ungültige übergebene Traktorparameter, benutze Defaultwerte.")
				return TractorParameters(*defaults)

		if not interactive:
			return TractorParameters(*defaults)
		try:
			w = input(f"Traktorbreite in Meter [{defaults[0]} m]: ") or str(defaults[0])
			l = input(f"Traktorlaenge in Meter [{defaults[1]} m]: ") or str(defaults[1])
			r = input(f"Wenderadius in Meter [{defaults[2]} m]: ") or str(defaults[2])
			return TractorParameters(float(w), float(l), float(r))
		except ValueError:
			print("Ungültige Eingabe, benutze Defaultwerte.")
			return TractorParameters(*defaults)

	def compute_wendestreifen_width(self) -> float:
		# Formel: Länge + 2 * Wenderadius + 1 m Sicherheitszuschlag
		return self.length_m + 2.0 * self.turn_radius_m + 1.0

	def compute_fahrspur_width(self) -> float:
		# Fahrspurbreite: Traktorbreite + 2 m Sicherheitszuschlag (zwei Seiten je 1 m)
		return self.width_m + 2.0


class AreaCalculator:
	"""Berechnet die nutzbare Innenfläche einer Polygonfläche unter Abzug des
	Wende-/Fahrspurmargins. Alle Berechnungen erfolgen in UTM (metrisch).

	Methoden:
	- compute_usable_area(poly_utm, margin_m) -> (usable_poly_utm, usable_area_m2)
	"""

	@staticmethod
	def compute_usable_area(poly_utm: Polygon, margin_m: float) -> Tuple[Polygon, float]:
		if margin_m <= 0:
			area = poly_utm.area
			return poly_utm, area
		inner = poly_utm.buffer(-margin_m)
		if inner.is_empty:
			return inner, 0.0
		return inner, inner.area


def compute_restflaeche(poly_utm: Polygon, breite_gruenstreifen: Any) -> Polygon:
	"""Berechnet die nutzbare Restfläche durch Entfernen eines äußeren
	Randstreifens mit Breite `breite_gruenstreifen` (in Metern) vom gegebenen
	Polygon in UTM-Koordinaten.

	Implementation:
	- Validiert `breite_gruenstreifen` (nicht-negativ, finite Zahl).
	- Verwendet `shapely.buffer` mit negativem Wert: `poly_utm.buffer(-breite)`.
	- Gibt das resultierende Polygon (kann leer sein) zurück.

	Parameter:
	- poly_utm: Shapely-Polygon in metrischem Koordinatensystem (z. B. UTM)
	- breite_gruenstreifen: Breite des abzuziehenden Streifens in Metern

	Rückgabe:
	- Shapely-Polygon der verbleibenden Innenfläche (oder ein leeres Geometry-Objekt)
	"""
	# Validierung
	if poly_utm is None:
		raise ValueError("poly_utm darf nicht None sein")
	if not hasattr(poly_utm, "buffer"):
		raise TypeError("poly_utm muss ein Shapely-Polygon sein")

	try:
		b = float(breite_gruenstreifen)
	except Exception:
		raise ValueError(f"breite_gruenstreifen muss numerisch sein, gegeben: {breite_gruenstreifen}")

	if not math.isfinite(b) or b < 0:
		raise ValueError(f"breite_gruenstreifen muss eine nicht-negative endliche Zahl sein, gegeben: {breite_gruenstreifen}")

	if b == 0:
		return poly_utm

	inner = poly_utm.buffer(-b)
	return inner


class PVGridGenerator:
	"""Generiert ein rasterförmiges Netz von Modulmitten (als Punkte) innerhalb
	der nutzbaren Fläche (UTM) und liefert ein GeoJSON FeatureCollection.

	Parameter:
	- usable_poly_utm: Shapely Polygon in UTM
	- transformer_to_wgs84: pyproj.Transformer (UTM -> EPSG:4326)

	Methode:
	- generate_points(pv_type, row_spacing_m, module_spacing_m) -> GeoJSON dict
	"""

	def __init__(self, usable_poly_utm: Polygon, transformer_to_wgs84: pyproj.Transformer):
		self.poly = usable_poly_utm
		self.transformer_to_wgs84 = transformer_to_wgs84

	@staticmethod
	def _frange(start: float, stop: float, step: float):
		vals = []
		v = start
		# guard against infinite loops
		if step <= 0:
			return vals
		while v <= stop:
			vals.append(v)
			v += step
		return vals

	def generate_points(self, pv_type: str = "horizontal", row_spacing_m: float = 12.0, module_spacing_m: float = 1.0) -> Dict[str, Any]:
		"""Erzeugt Punkte im Raster.

		Annahmen / Parameter:
		- `row_spacing_m`: Distanz zwischen zwei PV-Reihen (in Metern).
		  Empfohlen: Fahrspurbreite + Modulreihenbreite.
		- `module_spacing_m`: Abstand zwischen Modulmitten entlang einer Reihe.
		- `pv_type` beeinflusst momentan nur die Reihenorientierung.
		"""
		if self.poly.is_empty:
			return {"type": "FeatureCollection", "features": []}

		minx, miny, maxx, maxy = self.poly.bounds

		# Für horizontale Module: Reihen in x-Richtung, Abstand entlang y
		# Für vertikale Module: wir verwenden denselben Rastermechanismus, evtl. kleinerer Abstand
		if pv_type == "vertical":
			row_spacing = max(1.0, row_spacing_m / 3.0)
		else:
			row_spacing = row_spacing_m

		xs = self._frange(minx + module_spacing_m / 2.0, maxx - module_spacing_m / 2.0, module_spacing_m)
		ys = self._frange(miny + row_spacing / 2.0, maxy - row_spacing / 2.0, row_spacing)

		features = []
		for y in ys:
			for x in xs:
				pt = Point(x, y)
				if pt.within(self.poly):
					lon, lat = self.transformer_to_wgs84.transform(x, y)
					features.append({
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [lon, lat]},
						"properties": {"pv_type": pv_type}
					})

		return {"type": "FeatureCollection", "features": features}

	def generate_pv_points(polygon: Polygon, ausrichtung: str, reihenbreite: float,
						   module_spacing_m: float = 1.0,
						   transformer_to_wgs84: pyproj.Transformer = None) -> Dict[str, Any]:
		"""Generiert PV-Modulpunkte als GeoJSON FeatureCollection.
		Implementiert die angeforderte Zeilen-Segmentierung, Schnittpunkt-Generierung,
		gleichmäßige Punkt-Generierung und GeoJSON-Ausgabe. Beinhaltet Parameter-Validierung
		und optionalen Transformer für WGS84-Ausgabe.
		"""
		# Parameter-Validierung
		if not isinstance(polygon, Polygon):
			raise ValueError("Das Polygon muss ein Shapely Polygon sein.")
		if ausrichtung not in ["horizontal", "vertical"]:
			raise ValueError(f"Ungültige Ausrichtung '{ausrichtung}': erwartet 'horizontal' oder 'vertical'.")

		# Diese Methode ist veraltet; verwende stattdessen generate_pv_points() oder generate_pv_reihen()
		return {"type": "FeatureCollection", "features": []}


def generate_pv_points(polygon: Polygon, ausrichtung: str, reihenbreite: float,
                       module_spacing_m: float = 1.0,
                       transformer_to_wgs84: pyproj.Transformer = None) -> Dict[str, Any]:
	"""Generiert PV-Modulpunkte als GeoJSON FeatureCollection.

	Vorgehen:
	1. Segmentiert die Bounding-Box des Polygons in Linien (Zeilen/Spalten) abhängig von `ausrichtung`.
	2. Prüft für jede Linie den Schnitt mit dem Polygon.
	3. Für jede Schnittlinie werden äquidistante Punkte in Abstand `module_spacing_m` erzeugt.
	4. Gibt alle Punkte als GeoJSON FeatureCollection zurück.

	Parameter:
	- polygon: Shapely-Polygon (vorzugsweise in metrischen Einheiten, z. B. UTM)
	- ausrichtung: 'horizontal' oder 'vertical'
	- reihenbreite: Abstand zwischen Reihen in Metern
	- module_spacing_m: Abstand zwischen Modulen entlang einer Reihe (default 1.0 m)
	- transformer_to_wgs84: optionaler pyproj.Transformer zum Zurückprojektion der Punktkoordinaten

	Rückgabe:
	- GeoJSON-Dict mit Point-Features (Koordinaten in CRS der Transformer, falls angegeben)
	"""
	# Validierung
	if polygon is None or polygon.is_empty:
		return {"type": "FeatureCollection", "features": []}
	try:
		r = float(reihenbreite)
	except Exception:
		raise ValueError("reihenbreite muss eine positive Zahl sein")
	if r <= 0:
		raise ValueError("reihenbreite muss > 0 sein")
	try:
		spacing = float(module_spacing_m)
	except Exception:
		raise ValueError("module_spacing_m muss eine positive Zahl sein")
	if spacing <= 0:
		raise ValueError("module_spacing_m muss > 0 sein")

	a = str(ausrichtung).strip().lower()
	if a not in ("horizontal", "vertical", "horizontal_tracking"):
		raise ValueError("ausrichtung muss 'horizontal', 'vertical' oder 'horizontal_tracking' sein")

	minx, miny, maxx, maxy = polygon.bounds

	lines: List[LineString] = []
	if a == "horizontal":
		y = miny + r / 2.0
		while y <= maxy:
			# leicht überlappen, damit Schnitt robust ist
			lines.append(LineString([(minx - 1.0, y), (maxx + 1.0, y)]))
			y += r
	else:
		x = minx + r / 2.0
		while x <= maxx:
			lines.append(LineString([(x, miny - 1.0), (x, maxy + 1.0)]))
			x += r

	features: List[Dict[str, Any]] = []
	row_idx = 0
	for line in lines:
		inter = line.intersection(polygon)
		if inter.is_empty:
			row_idx += 1
			continue

		segments = []
		if inter.geom_type == 'LineString':
			segments = [inter]
		elif inter.geom_type == 'MultiLineString':
			segments = list(inter.geoms)
		else:
			row_idx += 1
			continue

		for seg in segments:
			seg_length = seg.length
			if seg_length <= 0:
				continue
			dist = spacing / 2.0
			while dist <= seg_length - 1e-9:
				pt = seg.interpolate(dist)
				x, y = pt.x, pt.y
				if transformer_to_wgs84 is not None:
					lon, lat = transformer_to_wgs84.transform(x, y)
					coords = [lon, lat]
				else:
					coords = [x, y]

				features.append({
					"type": "Feature",
					"geometry": {"type": "Point", "coordinates": coords},
					"properties": {"row": row_idx, "dist_m": round(dist, 3)}
				})
				dist += spacing

		row_idx += 1

	return {"type": "FeatureCollection", "features": features}


def generate_pv_reihen(polygon: Polygon, ausrichtung: str, row_spacing: float,
                       transformer_to_wgs84: pyproj.Transformer = None) -> Dict[str, Any]:
	"""Generiert PV-Reihen als LineString-Features (ohne Breite) in einer GeoJSON FeatureCollection.

	Die PV-Reihen werden als **geometrielose Linien** (LineStrings ohne Pufferung) dargestellt.
	Der wichtige Parameter ist der **Abstand zwischen den Linien** (row_spacing).

	Vorgehen:
	1. Bestimmt basierend auf der Ausrichtung die Segmentierungsrichtung:
	   - horizontal: Linien Ost–West, Verschiebung Nord–Süd
	   - vertical: Linien Nord–Süd, Verschiebung Ost–West
	   - horizontal_tracking: Linien Nord–Süd, Verschiebung Ost–West (wie vertical)
	2. Erzeugt aus der Bounding Box des Polygons parallele Linien im Abstand `row_spacing`.
	3. Schneidet jede Linie mit dem nutzbaren Polygon (Shapely intersection).
	4. Fügt jede resultierende nichtleere Schnittgeometrie als LineString-Feature ein (ohne Breite).
	5. Exportiert eine GeoJSON-Datei, deren Features ausschließlich LineStrings enthalten.

	Parameter:
	- polygon: Shapely-Polygon (vorzugsweise in metrischen Einheiten, z. B. UTM)
	- ausrichtung: 'horizontal', 'vertical' oder 'horizontal_tracking'
	- row_spacing: Abstand zwischen parallelen Reihen in Metern (wichtiger Parameter!)
	- transformer_to_wgs84: optionaler pyproj.Transformer zur Zurückprojektion in WGS84

	Rückgabe:
	- GeoJSON-Dict mit LineString-Features (ein Feature pro Reihe oder Reihen-Segment)

	Fehlerbehandlung:
	- ValueError bei ungültiger Ausrichtung oder negativem row_spacing
	- Leere Polygone liefern leere FeatureCollection
	"""
	# Validierung
	if polygon is None or polygon.is_empty:
		return {"type": "FeatureCollection", "features": []}

	try:
		r = float(row_spacing)
	except Exception:
		raise ValueError("row_spacing muss eine positive Zahl sein")
	if r <= 0:
		raise ValueError("row_spacing muss > 0 sein")

	a = str(ausrichtung).strip().lower()
	if a not in ("horizontal", "vertical", "horizontal_tracking"):
		raise ValueError("ausrichtung muss 'horizontal', 'vertical' oder 'horizontal_tracking' sein")

	minx, miny, maxx, maxy = polygon.bounds

	# Schritt 1 & 2: Generiere parallele Linien basierend auf Ausrichtung
	lines: List[LineString] = []
	if a == "horizontal":
		# Linien verlaufen Ost–West (Konstante Y)
		# Verschiebung Nord–Süd nach row_spacing
		y = miny + r / 2.0
		while y <= maxy:
			# Linien erstrecken sich leicht über die Bounding Box
			lines.append(LineString([(minx - 1.0, y), (maxx + 1.0, y)]))
			y += r
	elif a == "horizontal_tracking":
		# Linien verlaufen Nord–Süd (Konstante X)
		# Verschiebung Ost–West nach row_spacing
		# Abstand wie 'horizontal' berechnet, aber Ausrichtung wie 'vertical'
		x = minx + r / 2.0
		while x <= maxx:
			lines.append(LineString([(x, miny - 1.0), (x, maxy + 1.0)]))
			x += r
	else:  # vertical
		# Linien verlaufen Nord–Süd (Konstante X)
		# Verschiebung Ost–West nach row_spacing
		x = minx + r / 2.0
		while x <= maxx:
			lines.append(LineString([(x, miny - 1.0), (x, maxy + 1.0)]))
			x += r

	# Schritt 3, 4 & 5: Schneide Linien mit Polygon und generiere Features
	features: List[Dict[str, Any]] = []
	row_idx = 0

	for line in lines:
		inter = line.intersection(polygon)

		# Überspringe leere Schnitte
		if inter.is_empty:
			row_idx += 1
			continue

		# Behandle verschiedene Geometry-Typen
		segments: List[LineString] = []
		if inter.geom_type == 'LineString':
			segments = [inter]
		elif inter.geom_type == 'MultiLineString':
			segments = list(inter.geoms)
		else:
			# Ignoriere Points oder andere Geometrie-Typen
			row_idx += 1
			continue

		# Konvertiere jedes Segment in ein Feature
		for seg_idx, seg in enumerate(segments):
			if seg.length <= 0:
				continue

			# Reprojiziere Koordinaten falls Transformer vorhanden
			if transformer_to_wgs84 is not None:
				coords_wgs84 = []
				for x, y in seg.coords:
					lon, lat = transformer_to_wgs84.transform(x, y)
					coords_wgs84.append([lon, lat])
				coords = coords_wgs84
			else:
				coords = [[x, y] for x, y in seg.coords]

			features.append({
				"type": "Feature",
				"geometry": {
					"type": "LineString",
					"coordinates": coords
				},
				"properties": {
					"row": row_idx,
					"segment": seg_idx,
					"length_m": round(seg.length, 3),
					"orientation": "EW" if a == "horizontal" else "NS"
				}
			})

		row_idx += 1

	return {"type": "FeatureCollection", "features": features}

def export_geojson(points: Dict[str, Any], dateiname: str) -> None:
	"""Exportiert eine GeoJSON FeatureCollection in eine Datei (RFC 7946 konform).

	Parameter:
	- points: GeoJSON FeatureCollection Dict (z. B. Rückgabe von generate_pv_points)
	- dateiname: Pfad der Ausgabedatei (z. B. 'outputs/pv_points.geojson')

	Funktionalität:
	- Validiert, dass `points` die erforderlichen GeoJSON-Felder enthält.
	- Schreibt die Datei mit UTF-8 Encoding, 2-Leerzeichen-Indentation und sortiertem JSON.
	- RFC 7946 Konformität: Koordinaten sind [lon, lat], CRS ist implicit EPSG:4326 (WGS84).
	- Erstellt ggf. das Parent-Verzeichnis falls nicht vorhanden.

	Fehlerbehandlung:
	- ValueError bei ungültigem Input (fehlende 'type' oder 'features' Schlüssel).
	- IOError/OSError bei Dateischreib-Problemen.
	"""
	if not isinstance(points, dict):
		raise ValueError("points muss ein Dictionary sein (GeoJSON FeatureCollection)")
	if points.get("type") != "FeatureCollection":
		raise ValueError("points.type muss 'FeatureCollection' sein")
	if "features" not in points:
		raise ValueError("points muss ein 'features' Feld (Liste) enthalten")
	if not isinstance(points["features"], list):
		raise ValueError("points['features'] muss eine Liste sein")

	if not isinstance(dateiname, str) or not dateiname.strip():
		raise ValueError("dateiname muss ein nicht-leerer String sein")

	try:
		import os
		outdir = os.path.dirname(dateiname)
		if outdir and not os.path.exists(outdir):
			os.makedirs(outdir, exist_ok=True)

		with open(dateiname, 'w', encoding='utf-8') as f:
			json.dump(points, f, ensure_ascii=False, indent=2, sort_keys=True)

		#print(f"GeoJSON erfolgreich exportiert: {dateiname}")
	except IOError as e:
		raise IOError(f"Fehler beim Schreiben der Datei '{dateiname}': {e}")
	except Exception as e:
		raise RuntimeError(f"Unerwarteter Fehler beim Export: {e}")

def run_standalone(interactive: bool = True) -> Dict[str, Any]:
	"""Kurzer Ablauf (bindet alle Komponenten zusammen) und liefert ein Ergebnis-Dict:
	- Liest EMBEDDED_GEOJSON
	- Fragt PV-Typ und Traktorparameter ab (interaktiv oder Default)
	- Berechnet Wende-/Fahrspurmargen
	- Ermittelt nutzbare Innenfläche (UTM)
	- Generiert PV-Punkte und gibt GeoJSON zurück
	"""
	reader = GeoJSONReader(EMBEDDED_GEOJSON)
	geom_wgs84, geom_utm, to_utm, to_wgs84 = reader.load()

	pv_type = PVTypeSelector.select(interactive=interactive)
	tractor = TractorParameters.from_input(interactive=interactive)

	wendestreifen = tractor.compute_wendestreifen_width()
	fahrspur = tractor.compute_fahrspur_width()

	# Margin: wir nehmen als konservativen Rand die größere der beiden Breiten
	margin = max(wendestreifen, fahrspur)

	usable_poly_utm, usable_area_m2 = AreaCalculator.compute_usable_area(geom_utm, margin)

	grid_gen = PVGridGenerator(usable_poly_utm, to_wgs84)
	row_spacing = fahrspur + 2.0  # grobe Heuristik: Fahrspur + 2m frei
	geojson_points = grid_gen.generate_points(pv_type=pv_type, row_spacing_m=row_spacing, module_spacing_m=1.0)

	result = {
		"pv_type": pv_type,
		"tractor": {"width_m": tractor.width_m, "length_m": tractor.length_m, "turn_radius_m": tractor.turn_radius_m},
		"wendestreifen_m": wendestreifen,
		"fahrspur_m": fahrspur,
		"margin_used_m": margin,
		"usable_area_m2": usable_area_m2,
		"n_pv_points": len(geojson_points.get("features", [])),
		"pv_points_geojson": geojson_points,
	}

	return result


def compute_tractor_margins(traktor_breite: Any = None, traktor_laenge: Any = None, wenderadius: Any = None,
							interactive: bool = True, defaults: Tuple[float, float, float] = (2.5, 3.0, 4.0)) -> Dict[str, Any]:
	"""Fragt Traktorparameter ab oder verwendet übergebene Werte und berechnet:
	- breite_gruenstreifen = 2*wenderadius + traktor_laenge + 1
	- breite_fahrspur = traktor_breite + 2*1

	Robustheit:
	- Bei interaktiver Nutzung werden Eingaben validiert und ggf. erneut abgefragt.
	- Bei nicht-interaktivem Aufruf werden ungültige oder fehlende Werte durch Defaults ersetzt.
	- Negative oder Null-Werte werden als ungültig betrachtet und ersetzt.

	Rückgabe: Dict mit den numerischen Werten und optionalen Warnungen.
	"""

	warnings: List[str] = []

	def _to_valid_float(name: str, val: Any, default: float) -> float:
		# Versuche Umwandlung; bei Fehler Default verwenden
		if val is None:
			if interactive:
				raw = input(f"{name} in m [{default}]: ") or str(default)
			else:
				warnings.append(f"{name} nicht angegeben, verwende Default {default}")
				return float(default)
		else:
			raw = str(val)
		try:
			f = float(raw)
			if not math.isfinite(f) or f <= 0:
				raise ValueError("Nicht-positive Zahl")
			return f
		except Exception:
			warnings.append(f"Ungültiger Wert für {name}: '{raw}', benutze Default {default}")
			return float(default)

	b = _to_valid_float("traktor_breite", traktor_breite, defaults[0])
	l = _to_valid_float("traktor_laenge", traktor_laenge, defaults[1])
	r = _to_valid_float("wenderadius", wenderadius, defaults[2])

	breite_gruenstreifen = 2.0 * r + l + 1.0
	breite_fahrspur = b + 2.0 * 1.0

	res = {
		"traktor_breite_m": b,
		"traktor_laenge_m": l,
		"wenderadius_m": r,
		"breite_gruenstreifen_m": breite_gruenstreifen,
		"breite_fahrspur_m": breite_fahrspur,
	}
	if warnings:
		res["warnings"] = warnings

	return res


def get_reihenparameter(ausrichtung: Any, fahrspur_breite: float = None) -> Dict[str, Any]:
	"""Gibt Reihenparameter zurück abhängig von der Ausrichtung.

	**Reihenabstand (Zeile-zu-Zeile-Abstand in Meters):**
	- Bei "horizontal": Reihenabstand = Fahrspurbreite + 4 m (EW-Ausrichtung)
	- Bei "vertical": Reihenabstand = Fahrspurbreite + 0.5 m (NS-Ausrichtung)
	- Bei "horizontal_tracking": Reihenabstand = Fahrspurbreite + 4 m (NS-Ausrichtung)

	**Orientierung der PV-Reihen:**
	- Bei "horizontal": Reihen verlaufen Ost–West (EW), Reihenbreite = 4 m
	- Bei "vertical": Reihen verlaufen Nord–Süd (NS), Reihenbreite = 0.5 m
	- Bei "horizontal_tracking": Reihen verlaufen Nord–Süd (NS), Reihenbreite = 4 m, Single-Axis-Tracking

	Parameter:
	- ausrichtung: Erwartet 'horizontal', 'vertical' oder 'horizontal_tracking' (Groß-/Kleinschreibung ignoriert).
	- fahrspur_breite: Fahrspurbreite des Traktors in Metern (optional).
	                   Falls None, wird nur die Reihenbreite berechnet.

	Rückgabe: Dict mit Schlüsseln:
	- `orientation` ("EW" oder "NS")
	- `reihenbreite_m` (Breite der Modulreihe)
	- `row_spacing_m` (Abstand zwischen Reihen, falls fahrspur_breite übergeben)

	Fehlerbehandlung:
	- Bei ungültigem Wert wird eine `ValueError` mit erklärendem Hinweis ausgelöst.
	"""
	if ausrichtung is None:
		raise ValueError("Ausrichtung darf nicht None sein; benutze 'horizontal', 'vertical' oder 'horizontal_tracking'.")

	a = str(ausrichtung).strip().lower()
	
	if a == "horizontal":
		result = {"orientation": "EW", "reihenbreite_m": 2.5}
		if fahrspur_breite is not None:
			result["row_spacing_m"] = fahrspur_breite + 2.5
	elif a == "vertical":
		result = {"orientation": "NS", "reihenbreite_m": 0.5}
		if fahrspur_breite is not None:
			result["row_spacing_m"] = fahrspur_breite + 0.5
	elif a == "horizontal_tracking":
		result = {"orientation": "NS", "reihenbreite_m": 2}
		if fahrspur_breite is not None:
			result["row_spacing_m"] = fahrspur_breite + 2
	else:
		raise ValueError(f"Ungültige Ausrichtung '{ausrichtung}': erwartet 'horizontal', 'vertical' oder 'horizontal_tracking'.")
	
	return result


def main(
	interactive: bool = True,
	output_dir: str = "outputs",
	pv_ausrichtung: Any = None,
	ausbau_status: Any = None,
	tractor_width_m: Any = None,
	tractor_length_m: Any = None,
	tractor_turn_radius_m: Any = None,
) -> Dict[str, Any]:
	"""Hauptfunktion: Orchestriert alle Schritte für die PV-Flächenberechnung.

	Schritte:
	1. Einlesen der eingebetteten GeoJSON-Fläche.
	2. Abfrage der Benutzerinputs: Ausrichtung und Traktorparameter.
	3. Berechnung von Rand- und Fahrspurbreiten.
	4. Berechnung der nutzbaren Restfläche.
	5. Generierung der PV-Modulpunkte.
	6. Export der Punkte als GeoJSON.

	Parameter:
	- interactive: Falls True, fragt die Funktion Benutzereingaben ab. Falls False, werden Defaults verwendet.
	- output_dir: Verzeichnis für die Ausgabedateien (default: 'outputs')

	Rückgabe:
	- Dictionary mit allen Ergebnissen und Metadaten.
	"""
	#("\n" + "="*70)
	#print("PV-Flächenberechnung - Energielandschaft")
	#print("="*70 + "\n")

	# Schritt 1: Einlesen der eingebetteten GeoJSON-Fläche
	#print("[1/6] Einlesen der eingebetteten GeoJSON-Fläche...")
	try:
		reader = GeoJSONReader(EMBEDDED_GEOJSON)
		geom_wgs84, geom_utm, to_utm, to_wgs84 = reader.load()
		#print(f"  ✓ Polygon geladen (WGS84)")
		#print(f"    - Fläche (WGS84): {geom_wgs84.area:.2f} deg²")
		#print(f"    - Fläche (UTM): {geom_utm.area:.2f} m²\n")
	except Exception as e:
		print(f"  ✗ Fehler beim Laden des GeoJSON: {e}\n")
		raise

	# Schritt 2: Abfrage der Benutzerinputs
	#print("[2/6] Abfrage der Benutzerinputs...")
	try:
		if pv_ausrichtung is not None:
			ausrichtung = str(pv_ausrichtung).strip().lower()
			if ausrichtung not in PVTypeSelector.VALID:
				raise ValueError(
					f"Ungültige PV-Ausrichtung '{pv_ausrichtung}': erwartet {PVTypeSelector.VALID}."
				)
		else:
			ausrichtung = PVTypeSelector.select(interactive=interactive)
		#print(f"  ✓ PV-Ausrichtung: {ausrichtung}")

		if ausbau_status is not None:
			try:
				ausbau = int(ausbau_status)
			except (TypeError, ValueError):
				raise ValueError("Ungültiger Ausbau-Status: erwartet 0, 50 oder 100.")
			if ausbau not in AusbauStatusSelector.VALID:
				raise ValueError("Ungültiger Ausbau-Status: erwartet 0, 50 oder 100.")
		else:
			ausbau = AusbauStatusSelector.select(interactive=interactive)
		#print(f"  ✓ Ausbau-Status: {ausbau}%")

		tractor = TractorParameters.from_input(
			interactive=interactive,
			width_m=tractor_width_m,
			length_m=tractor_length_m,
			turn_radius_m=tractor_turn_radius_m,
		)
		#print(f"  ✓ Traktorparameter:")
		#print(f"    - Breite: {tractor.width_m} m")
		#print(f"    - Länge: {tractor.length_m} m")
		#print(f"    - Wenderadius: {tractor.turn_radius_m} m\n")
	except Exception as e:
		print(f"  ✗ Fehler bei Eingabeverarbeitung: {e}\n")
		raise

	# Schritt 3: Berechnung von Rand- und Fahrspurbreiten
	#print("[3/6] Berechnung von Rand- und Fahrspurbreiten...")
	try:
		wendestreifen = tractor.compute_wendestreifen_width()
		fahrspur = tractor.compute_fahrspur_width()
		#print(f"  ✓ Wendestreifen-Breite: {wendestreifen:.2f} m (Formel: 2*r + l + 1)")
		#print(f"  ✓ Fahrspur-Breite: {fahrspur:.2f} m (Formel: b + 2)\n")
	except Exception as e:
		print(f"  ✗ Fehler bei Breitenberechnung: {e}\n")
		raise

	# Schritt 4: Berechnung der nutzbaren Restfläche
	#print("[4/6] Berechnung der nutzbaren Restfläche...")
	try:
		margin = max(wendestreifen, fahrspur)
		rest_poly = compute_restflaeche(geom_utm, margin)
		usable_area = rest_poly.area if not rest_poly.is_empty else 0.0
		#print(f"  ✓ Randstreifen-Marge: {margin:.2f} m")
		#print(f"  ✓ Nutzbare Fläche: {usable_area:.2f} m²")
		if rest_poly.is_empty:
			print(f"  ⚠ Warnung: Nutzbare Fläche ist leer (Randstreifen zu groß)\n")
			return {
				"success": False,
				"error": "Nutzbare Fläche ist leer",
				"metadata": {
					"ausrichtung": ausrichtung,
					"traktor": {"width_m": tractor.width_m, "length_m": tractor.length_m, "turn_radius_m": tractor.turn_radius_m},
					"wendestreifen_m": wendestreifen,
					"fahrspur_m": fahrspur,
					"usable_area_m2": 0.0,
				}
			}
		#print()
	except Exception as e:
		print(f"  ✗ Fehler bei Flächenberechnung: {e}\n")
		raise

	# Schritt 5: Abfrage der Reihenparameter und Generierung der PV-Reihen
	#print("[5/6] Generierung der PV-Reihen (LineString-basiert)...")
	try:
		reihen_info = get_reihenparameter(ausrichtung, fahrspur_breite=fahrspur)
		row_spacing = reihen_info.get("row_spacing_m")
		orientation = reihen_info["orientation"]
		
		#print(f"  ✓ Reihenparameter für '{ausrichtung}':")
		#print(f"    - Ausrichtung: {orientation} ({'Ost-West' if orientation == 'EW' else 'Nord-Süd'})")
		#print(f"    - Reihenabstand (Zeile-zu-Zeile): {row_spacing:.2f} m")

		# Generiere PV-Reihen (LineStrings statt Punkte)
		geojson_points = generate_pv_reihen(rest_poly, ausrichtung, row_spacing, 
											transformer_to_wgs84=to_wgs84)
		geojson_points = apply_ausbau_status_to_reihen(geojson_points, ausbau)
		features_list = geojson_points.get("features", [])
		n_points = len(features_list)
		# Gesamtlänge aller erzeugten Reihen (in Metern, aus UTM berechnet)
		total_rows_length_m = sum(
			f.get("properties", {}).get("length_m", 0.0) for f in features_list
		)
		#print(f"  ✓ Generierte PV-Reihen: {n_points}")
		#print(f"  ✓ Berücksichtigter Ausbau-Status: {ausbau}%")
		#print(f"    - Gesamtlänge der Reihen: {total_rows_length_m:.2f} m")
		#print(f"    - Geometrie: LineString (durchgehende Reihen)\n")
	except Exception as e:
		print(f"  ✗ Fehler bei Reihengenerierung: {e}\n")
		raise

	# Schritt 6: Export der Reihen als GeoJSON
	#print("[6/6] Export der Reihen als GeoJSON...")
	try:
		import os
		if not os.path.exists(output_dir):
			os.makedirs(output_dir, exist_ok=True)
		
		# Generiere Dateinamen mit Traktor-Parametern und Ausrichtung
		# Format: P_02_Agri_PV_{traktor}_{orientation}.geojson
		# Beispiel: P_02_Agri_PV_Breite2.5_Laenge3.0_Wenderadius4.0_Horizontal.geojson
		traktor_params = f"Breite{tractor.width_m}_Laenge{tractor.length_m}_Wenderadius{tractor.turn_radius_m}"
		a = ausrichtung.lower()
		if a == "horizontal":
			orientation_abbrev = "Horizontal"
		elif a == "horizontal_tracking":
			orientation_abbrev = "Horizontal_Tracking"
		else:  # vertical
			orientation_abbrev = "Vertikal"
		# output_filename = f"P_02_Agri_PV_{traktor_params}_{orientation_abbrev}.geojson"
		# output_file = os.path.join(output_dir, output_filename)
		output_filename = f"P_02_Agri_PV_Reihen.geojson"
		output_file = os.path.join(output_dir, output_filename)
		
		export_geojson(geojson_points, output_file)
		#print(f"  ✓ GeoJSON exportiert: {output_file}\n")

		# Zusätzlicher Export: Mittelpunkt (Centroid) der ursprünglich eingelesenen Fläche
		# Verwende explizit das Original-Polygon (geom_utm), nicht die Restfläche
		centroid_source = geom_utm
		centroid_utm = centroid_source.centroid
		lon_c, lat_c = to_wgs84.transform(centroid_utm.x, centroid_utm.y)
		centroid_fc = {
			"type": "FeatureCollection",
			"features": [
				{
					"type": "Feature",
					"geometry": {"type": "Point", "coordinates": [lon_c, lat_c]},
					"properties": {
						"name": "Flaeche_Centroid",
						"source": "original_area"
					}
				}
			]
		}
		# centroid_filename = f"P_02_Agri_PV_{traktor_params}_{orientation_abbrev}_Centroid.geojson"
		# centroid_file = os.path.join(output_dir, centroid_filename)
		centroid_filename = f"P_02_Agri_PV_Mittelpunkt.geojson"
		centroid_file = os.path.join(output_dir, centroid_filename)
		export_geojson(centroid_fc, centroid_file)
		#print(f"  ✓ Centroid-GeoJSON exportiert: {centroid_file}\n")
	except Exception as e:
		print(f"  ✗ Fehler beim Export: {e}\n")
		raise

	# Zusammenfassung
	#print("="*70)
	#print("ZUSAMMENFASSUNG")
	#print("="*70)
	result = {
		"success": True,
		"ausrichtung": ausrichtung,
		"ausbau_status": ausbau,
		"metadata": {
			"ausrichtung": ausrichtung,
			"ausbau_status": ausbau,
			"erzeugungsfaktor": ausbau / 100.0,
			"orientation": orientation,
			"traktor": {
				"width_m": tractor.width_m,
				"length_m": tractor.length_m,
				"turn_radius_m": tractor.turn_radius_m
			},
		"wendestreifen_m": wendestreifen,
		"fahrspur_m": fahrspur,
		"margin_m": margin,
		"usable_area_m2": usable_area,
		"row_spacing_m": row_spacing,
		"n_pv_reihen": n_points,
		"total_rows_length_m": total_rows_length_m,
			"output_file": output_file,
		}
	}

	#print(f"PV-Ausrichtung: {ausrichtung}")
	#print(f"Ausbau-Status: {ausbau}% (Erzeugung: {ausbau}%)")
	#print(f"Traktor - Breite: {tractor.width_m} m, Länge: {tractor.length_m} m, Radius: {tractor.turn_radius_m} m")
	#print(f"Wendestreifen: {wendestreifen:.2f} m | Fahrspur: {fahrspur:.2f} m")
	#print(f"Nutzbare Fläche: {usable_area:.2f} m²")
	#print(f"Reihenabstand (Zeile-zu-Zeile: Traktor Fahrspur plus Breite PV-Anlage (Horizontale Ausrichtung 8 Meter, Vertikale Ausrichtung 0.5 Meter)): {row_spacing:.2f} m")
	#print(f"Orientierung: {orientation} ({'Ost-West' if orientation == 'EW' else 'Nord-Süd'})")
	#print(f"Generierte PV-Reihen: {n_points}")
	#print(f"Gesamtlänge der Reihen: {total_rows_length_m:.2f} m")
	#print(f"Output: {output_file} & {centroid_file}")
	#print("="*70 + "\n")

	return result


if __name__ == "__main__":
	try:
		result = main(interactive=True, output_dir="../data/outputs")
		if result.get("success"):
			print()#"✓ Verarbeitung erfolgreich abgeschlossen!")
		else:
			print(f"✗ Verarbeitung abgebrochen: {result.get('error')}")
	except Exception as e:
		print(f"✗ Kritischer Fehler: {e}")
		import traceback
		traceback.print_exc()


