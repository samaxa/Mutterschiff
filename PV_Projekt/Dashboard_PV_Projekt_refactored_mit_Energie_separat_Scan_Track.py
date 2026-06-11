# Dashboard_PV_Projekt_refactored.py
# ------------------------------------------------------------
# Start in der Konsole / im Terminal:
# streamlit run Dashboard_PV_Projekt_refactored.py
#
# Zweck des Skripts:
# Dieses Streamlit-Dashboard liest die fortlaufend aktualisierten
# Cont-Dateien aus dem synchronisierten Sciebo-Ordner ein.
#
# Wichtig:
# Das Dashboard-Layout orientiert sich an der Ordnerstruktur des verbundenen
# Sciebo-Ordners.
#
# Die Cont-Datei enthält pro Messzeitpunkt zwei elektrische Messkanäle:
#   Kanal 1 = Volt1 / Curr1 / Power1 / ...1
#   Kanal 2 = Volt2 / Curr2 / Power2 / ...2
#
# Die Modulkennung im Header legt fest, welches reale Modul zu Kanal 1
# und Kanal 2 gehört.
#
# Beispiel:
# Modul Kennung = Modul-1_6
# -> Kanal 1 gehört zu Modul 1
# -> Kanal 2 gehört zu Modul 6
#
# Bekannte Ausrichtungen:
# - Module 1, 2, 3: Süd
# - Module 4, 5, 6: Ost/West
# ------------------------------------------------------------

from pathlib import Path
import re

from streamlit_autorefresh import st_autorefresh
import pandas as pd
import streamlit as st
import plotly.express as px


# ============================================================
# 1) Konfiguration und Konstanten
# ============================================================

# Standardpfad zum synchronisierten Sciebo-Referenzdatensatz.
# Falls der Ordner auf einem anderen Rechner anders liegt, kann er auch im Dashboard im Sidebar geändert werden, oder hier.
MESS_ROOT = Path(
    r"C:\Users\sarah\OneDrive - TH Köln\Desktop\4.Semester\PV\Messdaten_PV_Sciebo\Referenzdatensatz"
)

# Dieses Dictionary ordnet jeder Modulnummer eine Ausrichtung zu.
MODULE_ORIENTATION = {
    "1": "Süd",
    "2": "Süd",
    "3": "Süd",
    "4": "Ost/West",
    "5": "Ost/West",
    "6": "Ost/West",
}
# Grenzwert für ungültige Messwerte.
# Sehr große negative Fehlerwerte aus dem Messgerät werden als ungültig behandelt.
INVALID_VALUE_LIMIT = -1e12

# legt fest, mit welcher Zeichenkodierung die Messdateien geöffnet werden:
# Die Cont-Dateien kommen offenbar nicht immer als echtes UTF-8. Das Gradzeichen in "Temperature [°C]" ist häufig Windows-/ANSI-kodiert.
# Das Programm liest die Dateien mit der Windows-Kodierung cp1252, damit Sonderzeichen wie °C richtig erkannt werden
FILE_ENCODING = "cp1252"

# Diese Einstellung legt fest, ob leere Zahlenfelder mit 0 ersetzt werden.
# Hintergrund: In den Track-Zeilen lässt das Messgerät manche Spalten leer, Excel/manuelle Aufbereitung interpretiert diese Felder häufig als 0.
FILL_EMPTY_NUMERIC_WITH_ZERO = True

# Das ist eine Liste mit Spaltennamen aus der originalen Cont-Datei.
# Hier wird festgelegt, welche Messspalten im Export wichtig sind und in welcher Reihenfolge sie erscheinen.
RAW_EXPORT_COLUMNS = [
    "Time",
    "Mode",
    "MPP Volt1 [V]",
    "MPP Curr1 [A]",
    "MPP Power1 [W]",
    "MPP Volt2 [V]",
    "MPP Curr2 [A]",
    "MPP Power2 [W]",
    "Temperature [°C]",
    "Light Intensity [W/m2]",
    "Open Circuit Volt1 [V]",
    "Short Circuit Curr1 [A]",
    "Fill Factor1 [%]",
    "Energy1 [kWh]",
    "Open Circuit Volt2 [V]",
    "Short Circuit Curr2 [A]",
    "Fill Factor2 [%]",
    "Energy2 [kWh]",
]

# Interne Hilfsspalten, die für Filterung, Diagramme und Zuordnung nötig sind,
# Diese Spalten helfen dem Programm beim Filtern, Sortieren und Zuordnen, sollen aber für den Nutzer ausgeblendet werden.
RAW_HELPER_COLUMNS_TO_HIDE = {
    "datetime",
    "date",
    "time_of_day",
    "module_type_from_file",
    "module_pair",
    "load1",
    "load2",
    "measurement_start",
    "source_file",
    "source_path",
}

# Dieses Dictionary enthält vordefinierte Zeitbereiche für die Sidebar.
# Hier wird festgelegt, welche relativen Zeitfilter der Nutzer auswählen kann.
# Der Wert beschreibt, wie weit vom letzten Messpunkt zurückgegangen wird.
TIME_RANGE_OFFSETS = {
    "Letzte 5 Minuten": pd.Timedelta(minutes=5),
    "Letzte 15 Minuten": pd.Timedelta(minutes=15),
    "Letzte 30 Minuten": pd.Timedelta(minutes=30),
    "Letzte 60 Minuten": pd.Timedelta(hours=1),
    "Letzte 24 Stunden": pd.Timedelta(hours=24),
    "Letzte 7 Tage": pd.Timedelta(days=7),
    "Letzte 30 Tage": pd.Timedelta(days=30),
}

# Das ist die vollständige Liste der Auswahlmöglichkeiten für den Zeitbereich im Dashboard.
# Diese Liste bestimmt, welche Optionen im Dropdown-Menü für den Zeitfilter angezeigt werden.
TIME_RANGE_OPTIONS = [
    "Gesamter Zeitraum",
    *TIME_RANGE_OFFSETS.keys(),     # fügt automatisch alle Einträge aus TIME_RANGE_OFFSETS in die Liste ein.
    "Monat der letzten Messung",
    "Jahr der letzten Messung",
    "Manuell auswählen",
]



# =================================================================
# 2) Kleine Hilfsfunktionen für Zeit, Ordnernamen und Modulkennung
# =================================================================
# In diesem Abschnitt werden Funktionen gesammelt, die dabei helfen Zeitangaben,
# Ordnernamen und Modulkennungen korrekt auszulesen und umzuwandeln

def to_local_file_time(timestamp_seconds: float) -> pd.Timestamp:
    """
    Wandelt einen Dateisystem-Zeitstempel in lokale deutsche Zeit um.
    file.stat().st_mtime liefert einen Unix-Zeitstempel. Ohne Zeitzonenbehandlung
    wirkt die Anzeige sonst in Deutschland häufig um 1-2 Stunden verschoben.
    """

    return (
        pd.to_datetime(timestamp_seconds, unit="s", utc=True)
        .tz_convert("Europe/Berlin")
    )


def get_date_from_folder_name(folder_path: Path) -> pd.Timestamp:
    """
    Liest ein Datum aus einem Messlauf-Ordnernamen.
    Erwartetes Format:
        YYYY-MM-DD
    Beispiel:
        Ordnername "2026-05-22" wird als Datum 2026-05-22 erkannt.
    Falls ein Ordner nicht wie ein Datum heißt, landet er in der Sortierung unten.
    """

    try:
        return pd.to_datetime(folder_path.name, format="%Y-%m-%d")
    except ValueError:
        return pd.Timestamp.min


def get_timestamp_from_cont_name(path: Path) -> pd.Timestamp:
    """
    Liest den Start-Zeitstempel aus einem Cont-Ordner- oder Cont-Dateinamen.
    Erwartetes Muster:  ...--YYYY-MM-DD--HH-MM-SS...
    Beispiel:           Cont--2--Modul-1_6--2026-05-22--13-25-36  -> 2026-05-22 13:25:36
    """

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})--(\d{2})-(\d{2})-(\d{2})",
        path.name,
    )

    if not match:
        return pd.Timestamp.min

    return pd.to_datetime(
        f"{match.group(1)} {match.group(2)}:{match.group(3)}:{match.group(4)}",
        errors="coerce",
    )


def get_module_pair_from_name(path: Path) -> str:
    """
    Versucht, die Modulkennung direkt aus einem Ordner- oder Dateinamen zu lesen.
    Beispiel:
        Cont--2--AE435CMD-108BDS--Modul-1_6--2026-05-22--13-25-36
        -> Modul-1_6
    """

    match = re.search(r"Modul-\d+_\d+", path.name)

    if match:
        return match.group(0)

    return "Modulpaar unbekannt"


def get_modules_from_pair(module_pair: str) -> tuple[str | None, str | None]:
    """
    Extrahiert die beiden Modulnummern aus einer Modulkennung.
    Beispiel:  "Modul-1_6" -> ("1", "6")
    """

    match = re.search(r"Modul-(\d+)_(\d+)", str(module_pair))

    if not match:
        return None, None

    return match.group(1), match.group(2)



# ============================================================
# 3) Dateisuche und Metadaten
# ============================================================
# Hier sucht das Programm die richtigen Cont-Dateien, liest Zusatzinformationen
# aus dem Dateikopf und sortiert die Messordner sinnvoll

# read_file_metadata liest Modultyp, Lasten, Startdatum und Modulkennung aus dem Header einer Cont-Datei:
def read_file_metadata(file_path: Path) -> dict:
    """
    Liest die Metadaten aus dem Kopfbereich einer Cont-Datei.
    Der Header enthält u. a.:
    - Name: Modultyp
    - Load1 / Load2: elektronische Lasten
    - Date: Startdatum und Startzeit der Messung
    - Modul Kennung: z. B. Modul-1_6
    Die eigentliche Messwerttabelle beginnt danach mit der Zeile "Time Mode ...".
    """
    # Dictionary mit Standardwerten:
    # Falls was fehlt wirds mit "unbekannt" oder "None" ersetzt
    metadata = {
        "module_type_from_file": "unbekannt",
        "load1": None,
        "load2": None,
        "measurement_start": pd.NaT,
        "module_pair": "unbekannt",
    }

    # Dieses Dictionary übersetzt die Bezeichnungen aus der Datei in die internen Spaltennamen des Programms.
    metadata_key_map = {
        "Name": "module_type_from_file",
        "Load1": "load1",
        "Load2": "load2",
        "Modul Kennung": "module_pair",
    }

    # Die Datei wird zum Lesen geöffnet:
    with open(file_path, "r", encoding=FILE_ENCODING, errors="ignore") as file:
        for line in file:
            line = line.strip()

            if line.startswith("Time"):  # Sobald eine Zeile mit "Time" beginnt, startet die eigentliche Messwerttabelle.
                break

            parts = re.split(r"\t+|\s{2,}", line, maxsplit=1)

            if len(parts) < 2:
                continue

            key = parts[0].strip()      # Leerzeichen am Anfang oder Ende werden entfernt.
            value = parts[1].strip()

            if key == "Date":           # Das Startdatum der Messung wird als echter Zeitwert gespeichert
                metadata["measurement_start"] = pd.to_datetime(value, errors="coerce")
            elif key in metadata_key_map:
                metadata[metadata_key_map[key]] = value

    return metadata # Funktion gibt alle gefundenen Metadaten zurück.


def get_latest_cont_txt_file(cont_folder: Path) -> Path | None:
    """
    Sucht innerhalb eines Cont-Ordners die eigentliche Cont-Textdatei.

    In einem Cont-Ordner liegen typischerweise:
    - eine fortlaufend aktualisierte Cont-*.txt-Datei
    - viele Scan-*.txt-Dateien

    Scan-Dateien werden bewusst ignoriert.
    Falls mehrere Cont-Dateien vorhanden sind, wird die zuletzt geänderte genutzt.
    """

    cont_txt_files = [
        file_path
        for file_path in cont_folder.glob("*.txt")  # sucht Textdateien direkt in diesem Ordner
        if file_path.is_file() and file_path.name.startswith("Cont") # nur Dateien, die mit Cont- anfangen
    ]

    if not cont_txt_files: # Falls keine passende Datei gefunden wird, gibt die Funktion None zurück.
        return None

    # Falls mehrere Cont-Dateien vorhanden sind, wird die zuletzt geänderte Datei genommen.
    # st_mtime ist der Änderungszeitpunkt der Datei:
    return max(cont_txt_files, key=lambda file_path: file_path.stat().st_mtime)



def get_latest_cont_file_mtime(cont_folder: Path) -> float:
    """
    Gibt den Änderungszeitpunkt der fortlaufend aktualisierten Cont.txt.-Datei zurück.
    Das ist für die Sortierung sinnvoller als das Ordner-Änderungsdatum.
    """

    latest_file = get_latest_cont_txt_file(cont_folder) # Zuerst wird mit der vorherigen Funktion die neueste Cont-Datei gesucht.

    if latest_file is not None:                         # Wenn eine Cont-Datei gefunden wurde, wird deren Änderungszeit zurückgegeben.
        return latest_file.stat().st_mtime

    return cont_folder.stat().st_mtime



def find_cont_measurement_folders(measurement_run_folder: Path) -> list[Path]:
    """
    Sucht Cont-Messordner innerhalb eines ausgewählten Messlauf-Tages.

    Beispielstruktur:
        2026-05-22
        ├── Cont--2--Modul-1_6--2026-05-22--13-25-36
        └── Cont--2--Modul-3_4--2026-05-22--19-03-05

    Sortierung:
    Nach Änderungszeit der jeweiligen Cont-Datei, neueste zuerst.
    """

    cont_folders = [
        folder
        for folder in measurement_run_folder.iterdir()
        if folder.is_dir() and folder.name.startswith("Cont")
    ]

    return sorted(cont_folders, key=get_latest_cont_file_mtime, reverse=True) # Die gefundenen Cont-Ordner werden sortiert



def make_cont_folder_label(cont_folder: Path) -> str:
    """
    Erzeugt einen stabilen Anzeigenamen für die Cont-Ordner-Auswahl.
    Wichtig:
    Der Änderungszeitpunkt der Cont-Datei wird hier bewusst NICHT in den
    Selectbox-Text geschrieben. Sonst würde sich die Option bei jeder
    Dateiaktualisierung ändern und Streamlit könnte die Auswahl verlieren.
    """

    module_pair = get_module_pair_from_name(cont_folder)
    start_timestamp = get_timestamp_from_cont_name(cont_folder)

    start_text = (
        start_timestamp.strftime("%d.%m.%Y %H:%M:%S")
        if pd.notna(start_timestamp) and start_timestamp != pd.Timestamp.min
        else "unbekannt"
    )

    return f"{module_pair} | Start: {start_text}"


def find_cont_files(search_folder: Path) -> list[Path]:
    """
    Fallback-Suche: Sucht rekursiv nach Cont-Textdateien.
    Scan-Dateien werden ausgeschlossen, weil nur Dateinamen mit "Cont" erlaubt sind.
    """

    return sorted(
        file_path
        for file_path in search_folder.rglob("*.txt")
        if file_path.is_file() and file_path.name.startswith("Cont")
    )


# ============================================================
# 4) Daten einlesen und aufbereiten
# ============================================================

def find_table_header_line(file_path: Path) -> int:
    """
    Sucht die Zeilennummer, in der die Messwerttabelle beginnt.
    Die Tabellenkopfzeile beginnt in den Cont-Dateien mit:
        Time    Mode    MPP Volt1 [V] ...
    """

    with open(file_path, "r", encoding=FILE_ENCODING, errors="ignore") as file:
        for line_number, line in enumerate(file):
            if line.startswith("Time"):
                return line_number

    raise ValueError(f"Keine Tabellenkopfzeile mit 'Time' gefunden: {file_path}")


def clean_numeric_column(series: pd.Series) -> pd.Series:
    """
    Wandelt eine Spalte in Zahlen um und ersetzt offensichtliche Fehlerwerte.
    Leere Felder in numerischen Messspalten werden optional als 0 gesetzt.
    Das passt zur Excel-Ansicht der Cont-Dateien, in der leere Messfelder
    für diese Auswertung als 0 dargestellt werden sollen.
    """

    numeric = pd.to_numeric(series, errors="coerce")

    # Extrem negative Platzhalterwerte aus dem Messgerät sind keine realen Messwerte.
    numeric = numeric.mask(numeric < INVALID_VALUE_LIMIT)

    if FILL_EMPTY_NUMERIC_WITH_ZERO:
        numeric = numeric.fillna(0)

    return numeric


def read_cont_file_raw(file_path: Path) -> pd.DataFrame:
    """
    Liest die Cont-Datei als Rohdaten-Tabelle ein.
    Wichtig:
    Die Datei besitzt keine separate Date-Spalte in der Messwerttabelle.
    Die erste Tabellenspalte heißt "Time", enthält aber Datum und Uhrzeit zusammen,
    z. B. "2026-05-22   19:03:22".

    Im DataFrame werden zusätzlich erzeugt:
    - datetime: echter Zeitstempel
    - date: Datum als separates Feld
    - time_of_day: Uhrzeit als separates Feld

    Die originalen Cont-Spalten bleiben für den CSV-Export erhalten.
    """

    metadata = read_file_metadata(file_path)
    header_line = find_table_header_line(file_path)

    df_raw = pd.read_csv(
        file_path,
        sep="\t",
        skiprows=header_line,
        encoding=FILE_ENCODING,
        engine="python",
    )

    # Komplett leere Spalten entfernen, falls durch Tabs am Zeilenende welche entstehen.
    df_raw = df_raw.dropna(axis=1, how="all")

    # Spaltennamen bereinigen und typische Encoding-Probleme korrigieren
    df_raw.columns = df_raw.columns.str.strip()

    df_raw = df_raw.rename(
        columns={
            "Temperature [ç™ˆ]": "Temperature [°C]",
            "Temperature [Â°C]": "Temperature [°C]",
            "Temperature [Ã‚Â°C]": "Temperature [°C]",
            "Light Intensity [W/m²]": "Light Intensity [W/m2]",
        }
    )

    if "Time" not in df_raw.columns:
        raise ValueError(f"Spalte 'Time' nicht gefunden: {file_path}")

    df_raw["datetime"] = pd.to_datetime(df_raw["Time"], errors="coerce")
    df_raw = df_raw.dropna(subset=["datetime"]).copy()

    df_raw["date"] = df_raw["datetime"].dt.date.astype(str)
    df_raw["time_of_day"] = df_raw["datetime"].dt.strftime("%H:%M:%S")

    # Alle numerischen Messspalten konvertieren. Time und Mode bleiben Text.
    for column in df_raw.columns:
        if column not in ["Time", "Mode", "datetime", "date", "time_of_day"]:
            df_raw[column] = clean_numeric_column(df_raw[column])

    # Metadaten ergänzen. Diese Spalten werden intern für Filterung, Zuordnung
    # und Statusanzeige genutzt, aber im Rohdaten-Export später größtenteils ausgeblendet.
    df_raw["module_type_from_file"] = metadata["module_type_from_file"]
    df_raw["load1"] = metadata["load1"]
    df_raw["load2"] = metadata["load2"]
    df_raw["measurement_start"] = metadata["measurement_start"]
    df_raw["module_pair"] = metadata["module_pair"]
    df_raw["source_file"] = file_path.name
    df_raw["source_path"] = str(file_path)
    df_raw["last_modified"] = to_local_file_time(file_path.stat().st_mtime)

    return df_raw.sort_values("datetime")


def get_column_or_na(df: pd.DataFrame, column_name: str) -> pd.Series:
    """
    Gibt eine vorhandene Spalte zurück oder eine leere NA-Spalte gleicher Länge.
    Dadurch bricht der Code nicht ab, falls eine optionale Spalte fehlt.
    """

    if column_name in df.columns:
        return df[column_name]

    return pd.Series([pd.NA] * len(df), index=df.index)


def raw_to_module_long(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Wandelt die breite Cont-Tabelle in eine modulweise Tabelle um.
    Aus einer Zeile mit Volt1/Curr1/Power1 und Volt2/Curr2/Power2 werden zwei Zeilen:
    - eine für Modul/Kanal 1
    - eine für Modul/Kanal 2
    Diese lange Form wird intern für Modulauswahl, KPI-Kacheln und elektrische
    Diagramme genutzt. Sie wird nicht als eigene Tabelle im Dashboard angezeigt.
    """

    if df_raw.empty:
        return pd.DataFrame()

    module_pair = str(df_raw["module_pair"].iloc[0])
    module_1, module_2 = get_modules_from_pair(module_pair)

    # Nur Spalten, die für Modulauswahl, Zeitfilter, KPI-Kacheln und elektrische
    # Diagramme wirklich benötigt werden. Sensorwerte bleiben in df_raw.
    common_columns = [
        "datetime",
        "date",
        "time_of_day",
        "Mode",
        "module_pair",
        "source_file",
        "last_modified",
    ]

    base = df_raw[common_columns].copy()
    base = base.rename(columns={"Mode": "mode"})

    channel_frames = []

    for channel, module_number in [(1, module_1), (2, module_2)]:
        df_channel = base.copy()

        df_channel["channel"] = channel
        df_channel["module_number"] = module_number
        df_channel["module_label"] = (
            f"Modul {module_number}" if module_number else "Modul unbekannt"
        )
        df_channel["orientation"] = MODULE_ORIENTATION.get(module_number, "unbekannt")

        df_channel["mpp_voltage_v"] = get_column_or_na(df_raw, f"MPP Volt{channel} [V]")
        df_channel["mpp_current_a"] = get_column_or_na(df_raw, f"MPP Curr{channel} [A]")
        df_channel["mpp_power_w"] = get_column_or_na(df_raw, f"MPP Power{channel} [W]")

        channel_frames.append(df_channel)

    df_long = pd.concat(channel_frames, ignore_index=True)
    return df_long.sort_values(["datetime", "channel"])


def read_multiple_cont_files(file_paths: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Liest eine oder mehrere Cont-Dateien ein.
    Rückgabe:
    - df_raw_all: breite Rohdaten aus den Cont-Dateien, möglichst nah am Original
    - df_long_all: modulweise Tabelle für Modulauswahl, KPIs und Diagramme
    Aktuell wird im Dashboard bewusst nur ein Cont-Messordner gewählt. Die Funktion
    bleibt trotzdem auf mehrere Dateien vorbereitet, falls später ein anderer Importfall entsteht.
    """

    raw_dfs = []
    long_dfs = []

    for file_path in file_paths:
        try:
            df_raw = read_cont_file_raw(file_path)
            df_long = raw_to_module_long(df_raw)
        except Exception as exc:
            st.warning(f"Datei konnte nicht eingelesen werden: {file_path.name} ({exc})")
            continue

        if not df_raw.empty:
            raw_dfs.append(df_raw)

        if not df_long.empty:
            long_dfs.append(df_long)

    df_raw_all = (
        pd.concat(raw_dfs, ignore_index=True).sort_values("datetime")
        if raw_dfs else pd.DataFrame()
    )

    df_long_all = (
        pd.concat(long_dfs, ignore_index=True).sort_values(["datetime", "channel"])
        if long_dfs else pd.DataFrame()
    )

    return df_raw_all, df_long_all


def order_raw_columns_for_display(df_raw_table: pd.DataFrame) -> pd.DataFrame:
    """
    Sortiert die Rohdatentabelle so, dass zuerst die originalen Cont-Spalten
    stehen und die zusätzlich erzeugten Hilfsspalten danach folgen.
    Für Vorschau und CSV-Export werden die internen Hilfsspalten ausgeblendet,
    damit die Tabelle nicht unnötig breit und unübersichtlich wird.
    """

    extra_columns = ["last_modified"]

    ordered_columns = [
        col for col in RAW_EXPORT_COLUMNS + extra_columns
        if col in df_raw_table.columns
    ]

    # Falls die Cont-Datei später zusätzliche echte Messspalten bekommt, bleiben
    # diese erhalten. Nur interne Hilfsspalten werden ausgeblendet.
    remaining_measurement_columns = [
        col for col in df_raw_table.columns
        if col not in ordered_columns and col not in RAW_HELPER_COLUMNS_TO_HIDE
    ]

    return df_raw_table[ordered_columns + remaining_measurement_columns]


def make_module_mapping_table(module_pairs: list[str]) -> pd.DataFrame:
    """
    Erstellt eine Übersicht, welche Module in welchen Kanälen stecken.
    Diese Tabelle dient unten im Rohdaten-/Exportbereich als Hilfe:
    - Kanal 1 entspricht Volt1 / Curr1 / Power1
    - Kanal 2 entspricht Volt2 / Curr2 / Power2
    """

    rows = []

    for module_pair in module_pairs:
        module_1, module_2 = get_modules_from_pair(module_pair)

        for channel, module_number in [(1, module_1), (2, module_2)]:
            rows.append(
                {
                    "Modulpaar": module_pair,
                    "Kanal in Cont-Datei": channel,
                    "Messspalten": f"Volt{channel} / Curr{channel} / Power{channel}",
                    "Einzelmodul": f"Modul {module_number}" if module_number else "unbekannt",
                    "Ausrichtung": MODULE_ORIENTATION.get(module_number, "unbekannt"),
                }
            )

    return pd.DataFrame(rows)


def prepare_display_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bereitet Tabellen nur für die Anzeige im Dashboard auf.
    Numerische Messwerte sind bereits bereinigt. Falls in Metadaten trotzdem
    leere Felder vorkommen, werden sie in der Anzeige als leerer String gezeigt.
    """

    display_df = df.copy()
    return display_df.astype("object").where(pd.notna(display_df), "")


# ============================================================
# 5) Sidebar-Auswahl und Filterlogik
# ============================================================

def setup_page_and_sidebar() -> tuple[Path, bool, int]:
    """
    Initialisiert die Streamlit-Seite und die allgemeinen Sidebar-Einstellungen.
    Rückgabe:
    - root_path: Pfad zum Referenzdatensatz
    - auto_refresh: True, wenn die ausgewählte Cont-Datei automatisch neu eingelesen wird
    - refresh_seconds: Aktualisierungsintervall in Sekunden
    """

    st.set_page_config(
        page_title="PV-Messdaten Dashboard",
        layout="wide",
    )

    st.title("PV-Messdaten Dashboard")
    st.caption("Anzeige der automatisch synchronisierten PV-Cont-Messdaten")

    st.sidebar.header("Einstellungen")

    file_path_input = st.sidebar.text_input(
        "Pfad zum Referenzdatensatz",
        value=str(MESS_ROOT),
        key="file_path_input",
    )

    auto_refresh = st.sidebar.checkbox(
        "Cont-Datei automatisch neu einlesen",
        value=False,
        key="auto_refresh",
    )

    refresh_seconds = st.sidebar.number_input(
        "Cont-Datei alle X Sekunden neu prüfen",
        min_value=10,
        max_value=600,
        value=60,
        step=10,
        key="refresh_seconds",
    )

    # Ein Streamlit-Button löst ohnehin einen Rerun aus. Deshalb wird hier bewusst
    # kein zusätzliches st.rerun() aufgerufen, damit die Widget-Auswahl stabil bleibt.
    if st.sidebar.button("Ausgewählte Cont-Datei neu einlesen", key="manual_data_refresh"):
        st.session_state["manual_refresh_counter"] = (
            st.session_state.get("manual_refresh_counter", 0) + 1
        )

    return Path(file_path_input), auto_refresh, int(refresh_seconds)


def select_module_type_and_measurement_run(root_path: Path) -> tuple[str, str, Path]:
    """
    Baut die Sidebar-Auswahl für Modultyp und Messlauf auf.
    Rückgabe:
    - selected_module_type_name: Name des gewählten Modultyps
    - selected_measurement_run_name: Name des gewählten Messlauf-Ordners
    - selected_measurement_run_folder: Pfad zum gewählten Messlauf-Ordner
    """

    if not root_path.exists():
        st.error(f"Ordner nicht gefunden: {root_path}")
        st.stop()

    module_type_folders = sorted([folder for folder in root_path.iterdir() if folder.is_dir()])

    if not module_type_folders:
        st.error("Keine Modultyp-Ordner gefunden.")
        st.stop()

    module_type_names = [folder.name for folder in module_type_folders]

    selected_module_type_name = st.sidebar.selectbox(
        "Modultyp auswählen",
        ["Bitte Modultyp auswählen"] + module_type_names,
        key="selected_module_type_name",
    )

    if selected_module_type_name == "Bitte Modultyp auswählen":
        st.info("Bitte zuerst einen Modultyp auswählen, um Messdaten anzuzeigen.")
        st.stop()

    selected_module_type_folder = root_path / selected_module_type_name

    measurement_run_folders = sorted(
        [folder for folder in selected_module_type_folder.iterdir() if folder.is_dir()],
        key=get_date_from_folder_name,
        reverse=True,
    )

    measurement_run_names = [folder.name for folder in measurement_run_folders]

    selected_measurement_run_name = st.sidebar.selectbox(
        "Messlauf auswählen",
        ["Bitte Messlauf auswählen"] + measurement_run_names,
        key="selected_measurement_run_name",
    )

    if selected_measurement_run_name == "Bitte Messlauf auswählen":
        st.info("Bitte zuerst einen Messlauf auswählen, um Messdaten anzuzeigen.")
        st.stop()

    selected_measurement_run_folder = selected_module_type_folder / selected_measurement_run_name

    return (
        selected_module_type_name,
        selected_measurement_run_name,
        selected_measurement_run_folder,
    )


def select_cont_files(
    measurement_run_folder: Path,
    auto_refresh: bool,
    refresh_seconds: int,
) -> tuple[list[Path], str]:
    """
    Baut die Sidebar-Auswahl für den Cont-Messordner auf und gibt die einzulesende
    Cont-Datei zurück.
    Wichtig:
    Es wird bewusst nur ein Cont-Messordner eingelesen. Unterschiedliche Cont-Ordner
    können zeitlich versetzte Messungen enthalten und sollen nicht gemeinsam geplottet werden.
    """

    cont_measurement_folders = find_cont_measurement_folders(measurement_run_folder)

    if cont_measurement_folders:
        st.sidebar.subheader("Cont-Messordner")

        cont_folder_label_map = {
            make_cont_folder_label(folder): folder
            for folder in cont_measurement_folders
        }

        selected_cont_folder_label = st.sidebar.selectbox(
            "Cont-Messordner auswählen",
            ["Bitte Cont-Messordner auswählen"] + list(cont_folder_label_map.keys()),
            key="selected_cont_folder_label",
        )

        st.sidebar.caption(
            "Es wird bewusst nur ein Cont-Messordner eingelesen, damit keine "
            "zeitlich versetzten Messungen miteinander vermischt werden."
        )

        if selected_cont_folder_label == "Bitte Cont-Messordner auswählen":
            st.info("Bitte einen Cont-Messordner auswählen, um Messdaten einzulesen.")
            st.stop()

        # Autorefresh wird erst nach Auswahl eines konkreten Cont-Ordners aktiviert.
        # So bleibt die Auswahl stabiler als bei einem Browser-Reload.
        if auto_refresh:
            st_autorefresh(
                interval=refresh_seconds * 1000,
                key="cont_file_autorefresh",
            )

        selected_cont_folder = cont_folder_label_map[selected_cont_folder_label]
        latest_cont_file = get_latest_cont_txt_file(selected_cont_folder)
        cont_files = [latest_cont_file] if latest_cont_file is not None else []

        return cont_files, selected_cont_folder_label

    # Fallback, falls keine separaten Cont-Messordner existieren.
    # Dann wird direkt im Messlauf-Ordner nach Cont-Dateien gesucht.
    cont_files = find_cont_files(measurement_run_folder)
    return cont_files, "Direkte Cont-Dateisuche ohne separaten Cont-Ordner"



def load_selected_cont_data(cont_files: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prüft, ob Cont-Dateien vorhanden sind, und liest Rohdaten sowie modulweise Daten ein.
    """

    if not cont_files:
        st.warning("Für diese Auswahl wurden keine Cont-Dateien gefunden.")
        st.stop()

    df_raw, df_long = read_multiple_cont_files(cont_files)

    if df_long.empty or df_raw.empty:
        st.warning("Die Cont-Dateien wurden gefunden, aber es konnten keine Messdaten erkannt werden.")
        st.stop()

    return df_raw, df_long



def select_modules(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Baut die Modulauswahl in der Sidebar auf und filtert die modulweise Tabelle.
    """

    st.sidebar.subheader("Module")

    module_options_df = (
        df_long[["module_number", "module_label", "orientation"]]
        .drop_duplicates()
        .sort_values("module_number")
    )

    module_options_df["display_name"] = (
        module_options_df["module_label"]
        + " – "
        + module_options_df["orientation"]
    )

    selected_module_display_names = st.sidebar.multiselect(
        "Einzelne Module auswählen",
        module_options_df["display_name"].tolist(),
        default=[],
        key="selected_module_display_names",
    )

    if not selected_module_display_names:
        st.info("Bitte mindestens ein Modul auswählen, um Messdaten anzuzeigen.")
        st.stop()

    selected_module_numbers = module_options_df.loc[
        module_options_df["display_name"].isin(selected_module_display_names),
        "module_number",
    ].tolist()

    df_selected = df_long[df_long["module_number"].isin(selected_module_numbers)].copy()

    if df_selected.empty:
        st.warning("Für die ausgewählten Module sind keine Daten vorhanden.")
        st.stop()

    return df_selected


def filter_by_time_range(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Baut die Zeitbereich-Auswahl in der Sidebar auf und filtert die modulweise Tabelle.
    Relative Zeitbereiche beziehen sich bewusst auf den letzten vorhandenen Messpunkt
    in der ausgewählten Cont-Datei, nicht auf die aktuelle reale Uhrzeit.
    """

    st.sidebar.subheader("Zeitbereich")

    min_datetime = df_long["datetime"].min()
    max_datetime = df_long["datetime"].max()

    time_range_option = st.sidebar.selectbox(
        "Anzuzeigender Zeitraum",
        TIME_RANGE_OPTIONS,
        key="time_range_option",
    )

    if time_range_option == "Gesamter Zeitraum":
        df_filtered = df_long.copy()

    elif time_range_option in TIME_RANGE_OFFSETS:
        start_datetime = max_datetime - TIME_RANGE_OFFSETS[time_range_option]
        df_filtered = df_long[df_long["datetime"] >= start_datetime].copy()

    elif time_range_option == "Monat der letzten Messung":
        start_datetime = max_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        df_filtered = df_long[df_long["datetime"] >= start_datetime].copy()

    elif time_range_option == "Jahr der letzten Messung":
        start_datetime = max_datetime.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        df_filtered = df_long[df_long["datetime"] >= start_datetime].copy()

    else:
        df_filtered = filter_by_manual_time_range(df_long, min_datetime, max_datetime)

    if df_filtered.empty:
        st.warning("Für den ausgewählten Zeitraum sind keine Daten vorhanden.")
        st.stop()

    return df_filtered


def filter_by_manual_time_range(
    df_long: pd.DataFrame,
    min_datetime: pd.Timestamp,
    max_datetime: pd.Timestamp,
) -> pd.DataFrame:
    """
    Filtert die Messdaten über manuell eingegebenes Start-/Enddatum und Uhrzeit.
    """

    start_date = st.sidebar.date_input(
        "Startdatum",
        value=min_datetime.date(),
        min_value=min_datetime.date(),
        max_value=max_datetime.date(),
        key="manual_start_date",
    )

    end_date = st.sidebar.date_input(
        "Enddatum",
        value=max_datetime.date(),
        min_value=min_datetime.date(),
        max_value=max_datetime.date(),
        key="manual_end_date",
    )

    st.sidebar.caption(
        f"Verfügbare Zeitspanne: "
        f"{min_datetime.strftime('%d.%m.%Y %H:%M:%S')} bis "
        f"{max_datetime.strftime('%d.%m.%Y %H:%M:%S')}"
    )

    start_time_text = st.sidebar.text_input(
        "Startzeit (HH:MM oder HH:MM:SS)",
        value=min_datetime.strftime("%H:%M:%S"),
        key="manual_start_time",
    )

    end_time_text = st.sidebar.text_input(
        "Endzeit (HH:MM oder HH:MM:SS)",
        value=max_datetime.strftime("%H:%M:%S"),
        key="manual_end_time",
    )

    try:
        start_datetime = pd.to_datetime(f"{start_date} {start_time_text}")
        end_datetime = pd.to_datetime(f"{end_date} {end_time_text}")
    except ValueError:
        st.sidebar.error("Bitte die Zeit im Format HH:MM oder HH:MM:SS eingeben.")
        st.stop()

    if start_datetime < min_datetime:
        st.sidebar.error(
            f"Die Startzeit liegt vor dem ersten Messpunkt: "
            f"{min_datetime.strftime('%d.%m.%Y %H:%M:%S')}"
        )
        st.stop()

    if end_datetime > max_datetime:
        st.sidebar.error(
            f"Die Endzeit liegt nach dem letzten Messpunkt: "
            f"{max_datetime.strftime('%d.%m.%Y %H:%M:%S')}"
        )
        st.stop()

    if start_datetime > end_datetime:
        st.sidebar.error("Der Startzeitpunkt darf nicht nach dem Endzeitpunkt liegen.")
        st.stop()

    return df_long[
        (df_long["datetime"] >= start_datetime)
        & (df_long["datetime"] <= end_datetime)
    ].copy()



def filter_raw_data_like_dashboard_selection(
    df_raw: pd.DataFrame,
    df_filtered: pd.DataFrame,
) -> pd.DataFrame:
    """
    Filtert die breite Rohdatentabelle passend zum ausgewählten Zeitbereich.
    Der Modulfilter wird bewusst nicht angewendet, weil die Rohdaten weiterhin
    exakt die breite Struktur der Cont-Datei enthalten: Kanal 1 und Kanal 2 stehen
    dort in derselben Zeile.
    """

    raw_source_files = df_filtered["source_file"].dropna().unique().tolist()

    return df_raw[
        (df_raw["source_file"].isin(raw_source_files))
        & (df_raw["datetime"] >= df_filtered["datetime"].min())
        & (df_raw["datetime"] <= df_filtered["datetime"].max())
    ].copy()


# ============================================================
# 6) Anzeige-Funktionen Dashboard
# ============================================================

def render_overview_container(
    selected_module_type_name: str,
    selected_measurement_run_name: str,
    selected_cont_folder_label: str,
    cont_files: list[Path],
    df_filtered: pd.DataFrame,
) -> None:
    """
    Zeigt den oberen Dashboard-Bereich mit Auswahlstatus, Messzeitraum und KPI-Kacheln.
    """

    first_datetime = df_filtered["datetime"].min()
    latest_datetime = df_filtered["datetime"].max()

    latest_per_module = (
        df_filtered
        .sort_values("datetime")
        .groupby(["module_number", "module_label", "orientation"], as_index=False)
        .tail(1)
        .sort_values("module_number")
    )

    with st.container(border=True):
        st.subheader("Auswahl und aktueller Messstand")

        info_col1, info_col2, info_col3 = st.columns(3)

        with info_col1:
            st.markdown("**Modultyp**")
            st.write(selected_module_type_name)

        with info_col2:
            st.markdown("**Messlauf**")
            st.write(selected_measurement_run_name)

        with info_col3:
            st.markdown("**Cont-Messordner**")
            st.write(selected_cont_folder_label)

        latest_cont_mtime = max(file.stat().st_mtime for file in cont_files)
        latest_cont_mtime_local = to_local_file_time(latest_cont_mtime)

        st.caption(
            "Aktuell eingelesene Cont-Datei zuletzt geändert: "
            f"{latest_cont_mtime_local.strftime('%d.%m.%Y %H:%M:%S')}"
        )

        st.divider()

        time_col1, time_col2 = st.columns(2)

        time_col1.metric(
            "Erster Messzeitpunkt",
            first_datetime.strftime("%d.%m.%Y %H:%M:%S"),
        )

        time_col2.metric(
            "Letzter Messzeitpunkt",
            latest_datetime.strftime("%d.%m.%Y %H:%M:%S"),
        )

        st.divider()

        st.subheader("Aktuelle Messwerte je Modul")
        st.caption(
            "Die aktuellen Werte beziehen sich auf den letzten vorhandenen Messpunkt "
            "im ausgewählten Zeitraum."
        )

        for _, row in latest_per_module.iterrows():
            st.markdown(f"**{row['module_label']} – {row['orientation']}**")

            col1, col2, col3 = st.columns(3)

            col1.metric("Aktuelle Leistung", f"{row['mpp_power_w']:.1f} W")
            col2.metric("Aktuelle Spannung", f"{row['mpp_voltage_v']:.2f} V")
            col3.metric("Aktueller Strom", f"{row['mpp_current_a']:.2f} A")



def make_electrical_line_chart(
    df_filtered: pd.DataFrame,
    y_column: str,
    y_label: str,
    title: str,
):
    """
    Erstellt ein Plotly-Liniendiagramm für elektrische Messgrößen.
    Die Farbe unterscheidet die Einzelmodule, die Linienart unterscheidet Scan/Track.
    """

    return px.line(
        df_filtered,
        x="datetime",
        y=y_column,
        color="module_label",
        line_dash="mode",
        hover_data=["orientation", "module_pair", "channel"],
        title=title,
        labels={
            "datetime": "Zeit",
            y_column: y_label,
            "module_label": "Modul",
            "mode": "Messmodus",
            "orientation": "Ausrichtung",
        },
    )



def render_electrical_charts(df_filtered: pd.DataFrame) -> None:
    """
    Zeigt die elektrischen Diagramme für Leistung, Spannung und Strom.
    """

    with st.container(border=True):
        st.subheader("Elektrische Messwerte")
        st.caption(
            "Diese Diagramme werden nach den ausgewählten Einzelmodulen gefiltert. "
            "Scan und Track werden über die Linienart unterschieden."
        )

        st.plotly_chart(
            make_electrical_line_chart(
                df_filtered,
                "mpp_power_w",
                "MPP-Leistung [W]",
                "MPP-Leistung über die Zeit",
            ),
            use_container_width=True,
        )

        col_left, col_right = st.columns(2)

        with col_left:
            st.plotly_chart(
                make_electrical_line_chart(
                    df_filtered,
                    "mpp_voltage_v",
                    "MPP-Spannung [V]",
                    "MPP-Spannung über die Zeit",
                ),
                use_container_width=True,
            )

        with col_right:
            st.plotly_chart(
                make_electrical_line_chart(
                    df_filtered,
                    "mpp_current_a",
                    "MPP-Strom [A]",
                    "MPP-Strom über die Zeit",
                ),
                use_container_width=True,
            )


def add_energy_from_power(
    df_filtered: pd.DataFrame,
    max_gap_minutes: float = 10,
) -> pd.DataFrame:
    """
    Berechnet die Energie aus der MPP-Leistung und den realen Zeitabständen.

    Wichtig:
    Scan und Track werden NICHT zusammengemischt, sondern getrennt berechnet.
    Dadurch bekommt jeder Messmodus seine eigene Zeitachse:
    - Track -> nächster Track
    - Scan  -> nächster Scan

    Energie [Wh] = Leistung [W] * Zeitdifferenz [h]
    """

    if df_filtered.empty:
        return pd.DataFrame()

    df_energy = df_filtered.copy()
    df_energy = df_energy.sort_values(["module_number", "source_file", "mode", "datetime"])

    # Scan und Track werden absichtlich getrennt gruppiert.
    # Dadurch wird nicht Track -> Scan -> Track gerechnet, sondern:
    # Track -> nächster Track und Scan -> nächster Scan.
    group_columns = ["module_number", "source_file", "mode"]

    # Zeit bis zum nächsten Messpunkt desselben Moduls UND desselben Messmodus.
    next_datetime = df_energy.groupby(group_columns)["datetime"].shift(-1)

    df_energy["delta_time_s"] = (
        next_datetime - df_energy["datetime"]
    ).dt.total_seconds()

    # Der letzte Messpunkt je Modul/Modus hat keinen nächsten Messpunkt mehr.
    # Negative oder fehlende Zeitabstände sind nicht sinnvoll und werden auf 0 gesetzt.
    df_energy["delta_time_s"] = df_energy["delta_time_s"].fillna(0)
    df_energy.loc[df_energy["delta_time_s"] < 0, "delta_time_s"] = 0

    # Sehr große Lücken werden nicht integriert, weil sonst Messabbrüche oder
    # fehlende Daten die berechnete Energie künstlich erhöhen könnten.
    max_gap_seconds = max_gap_minutes * 60
    df_energy.loc[df_energy["delta_time_s"] > max_gap_seconds, "delta_time_s"] = 0

    df_energy["delta_time_h"] = df_energy["delta_time_s"] / 3600

    df_energy["energy_interval_wh"] = (
        df_energy["mpp_power_w"] * df_energy["delta_time_h"]
    )

    df_energy["energy_cumulative_kwh"] = (
        df_energy
        .groupby(group_columns)["energy_interval_wh"]
        .cumsum()
        / 1000
    )

    return df_energy


def render_energy_chart(df_filtered: pd.DataFrame) -> None:
    """
    Zeigt die aus der Leistung berechnete Energie je Modul.

    Scan und Track werden getrennt betrachtet, damit die beiden Messarten nicht
    methodisch vermischt werden. Dadurch entstehen getrennte Energiekurven für
    Scan und Track.
    """

    df_energy = add_energy_from_power(df_filtered)

    if df_energy.empty:
        return

    latest_energy = (
        df_energy
        .sort_values("datetime")
        .groupby(["module_number", "module_label", "orientation", "mode"], as_index=False)
        .tail(1)
        .sort_values(["module_number", "mode"])
    )

    with st.container(border=True):
        st.subheader("Berechnete Energie")
        st.caption(
            "Die Energie wird aus der MPP-Leistung und den realen Zeitabständen berechnet. "
            "Scan und Track werden dabei getrennt ausgewertet: Track wird nur mit Track "
            "verglichen, Scan nur mit Scan. Große Messlücken werden nicht integriert."
        )

        # KPIs je Modul und Messmodus, damit nicht versehentlich Scan und Track addiert werden.
        st.subheader("Energie je Modul und Messmodus")

        metric_rows = latest_energy.to_dict("records")
        for start_index in range(0, len(metric_rows), 4):
            metric_columns = st.columns(min(4, len(metric_rows) - start_index))

            for metric_column, row in zip(metric_columns, metric_rows[start_index:start_index + 4]):
                metric_column.metric(
                    f"{row['module_label']} – {row['mode']}",
                    f"{row['energy_cumulative_kwh']:.4f} kWh",
                )

        fig_energy = px.line(
            df_energy,
            x="datetime",
            y="energy_cumulative_kwh",
            color="module_label",
            line_dash="mode",
            hover_data=[
                "mode",
                "orientation",
                "module_pair",
                "channel",
                "mpp_power_w",
                "delta_time_s",
                "energy_interval_wh",
            ],
            title="Kumulierte Energie über die Zeit, getrennt nach Scan und Track",
            labels={
                "datetime": "Zeit",
                "energy_cumulative_kwh": "Kumulierte Energie [kWh]",
                "module_label": "Modul",
                "mode": "Messmodus",
                "orientation": "Ausrichtung",
                "mpp_power_w": "MPP-Leistung [W]",
                "delta_time_s": "Zeit bis zum nächsten Messpunkt [s]",
                "energy_interval_wh": "Energie im Intervall [Wh]",
            },
        )

        st.plotly_chart(fig_energy, use_container_width=True)

        # Nicht-kumulierte Darstellung: Energie je Zeitabschnitt.
        # Diese Kurve kann wieder hoch und runter gehen, weil sie nicht die
        # Gesamtsumme zeigt, sondern den neu erzeugten Ertrag pro Stunde.
        df_energy_hourly = (
            df_energy
            .set_index("datetime")
            .groupby(["module_label", "mode"])["energy_interval_wh"]
            .resample("1h")
            .sum()
            .reset_index()
        )

        fig_energy_hourly = px.line(
            df_energy_hourly,
            x="datetime",
            y="energy_interval_wh",
            color="module_label",
            line_dash="mode",
            markers=True,
            title="Energieertrag pro Stunde, getrennt nach Scan und Track",
            labels={
                "datetime": "Zeit",
                "energy_interval_wh": "Energie pro Stunde [Wh]",
                "module_label": "Modul",
                "mode": "Messmodus",
            },
        )

        st.plotly_chart(fig_energy_hourly, use_container_width=True)

        with st.expander("Berechnete Energie-Tabelle anzeigen"):
            energy_display_columns = [
                "datetime",
                "module_label",
                "orientation",
                "mode",
                "mpp_power_w",
                "delta_time_s",
                "energy_interval_wh",
                "energy_cumulative_kwh",
            ]

            st.dataframe(
                prepare_display_table(df_energy[energy_display_columns]),
                use_container_width=True,
                hide_index=True,
            )


def render_sensor_values(df_raw_filtered: pd.DataFrame) -> None:
    """
    Zeigt optional Temperatur und Light Intensity aus der Cont-Datei.
    Diese Sensorwerte liegen in der Cont-Datei nur einmal pro Zeitpunkt vor und sind
    nicht getrennt nach Kanal 1/Kanal 2 bzw. Einzelmodul verfügbar.
    """

    with st.container(border=True):
        with st.expander("Sensorwerte der Cont-Datei anzeigen"):
            st.caption(
                "Temperatur und Light Intensity stehen in der Cont-Datei nur einmal pro Zeitpunkt. "
                "Sie sind nicht getrennt für die Einzelmodule verfügbar und werden daher je "
                "Cont-Datei bzw. Modulpaar angezeigt."
            )

            sensor_df = df_raw_filtered.copy()

            temperature_column = "Temperature [°C]"
            light_column = "Light Intensity [W/m2]"

            if temperature_column in sensor_df.columns:
                sensor_df_temp = sensor_df[sensor_df[temperature_column] != 0].copy()

                if sensor_df_temp.empty:
                    st.info(
                        "Die Temperaturspalte wurde gefunden, enthält im ausgewählten Zeitraum aber nur 0-Werte."
                    )
                else:
                    fig_temp = px.line(
                        sensor_df_temp,
                        x="datetime",
                        y=temperature_column,
                        color="module_pair",
                        title="Temperatur über die Zeit je Cont-Datei/Modulpaar",
                        labels={
                            "datetime": "Zeit",
                            temperature_column: "Temperatur [°C]",
                            "module_pair": "Cont-Datei / Modulpaar",
                        },
                    )
                    st.plotly_chart(fig_temp, use_container_width=True)
            else:
                st.info("In dieser Cont-Datei wurde keine Temperaturspalte gefunden.")

            if light_column in sensor_df.columns:
                fig_light = px.line(
                    sensor_df,
                    x="datetime",
                    y=light_column,
                    color="module_pair",
                    title="Light Intensity über die Zeit je Cont-Datei/Modulpaar",
                    labels={
                        "datetime": "Zeit",
                        light_column: "Light Intensity [W/m²]",
                        "module_pair": "Cont-Datei / Modulpaar",
                    },
                )
                st.plotly_chart(fig_light, use_container_width=True)
            else:
                st.info("In dieser Cont-Datei wurde keine Light-Intensity-Spalte gefunden.")



def render_raw_data_export(
    df_raw_display: pd.DataFrame,
    module_mapping_table: pd.DataFrame,
) -> None:
    """
    Zeigt den Rohdaten-/Exportbereich mit Modulzuordnung, optionaler Vorschau und CSV-Download.
    """

    with st.container(border=True):
        st.subheader("Rohdaten und Export")
        st.caption(
            "Die Rohdaten bleiben möglichst nah an der Cont-Datei: pro Zeitpunkt eine Zeile, "
            "Kanal 1 und Kanal 2 stehen nebeneinander. Die Modulzuordnung erklärt, "
            "welches Modul zu Volt1/Curr1/Power1 bzw. Volt2/Curr2/Power2 gehört."
        )

        with st.expander("Modulzuordnung anzeigen"):
            st.dataframe(module_mapping_table, use_container_width=True, hide_index=True)

        with st.expander("Rohdatenvorschau anzeigen"):
            st.dataframe(prepare_display_table(df_raw_display), use_container_width=True)

        csv_raw = df_raw_display.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Rohdaten aus Cont-Datei als CSV herunterladen",
            data=csv_raw,
            file_name="pv_cont_rohdaten_export.csv",
            mime="text/csv",
        )




# ============================================================
# 7) Hauptprogramm
# ============================================================

# "Regisseur" des Programms:
# Die ganzen anderen Funktionen sind einzelne Werkzeuge.
# main() entscheidet, wann welches Werkzeug benutzt wird.
def main() -> None:
    """
    Hauptablauf des Dashboards.

    Reihenfolge:
    1. Seite und Sidebar starten
    2. Modultyp, Messlauf und Cont-Datei auswählen
    3. Cont-Datei einlesen
    4. Module und Zeitbereich filtern
    5. Dashboard-Bereiche anzeigen
    """

    # Das Dashboard wird gestartet und die Grundeinstellungen werden
    # aus der Sidebar gelesen:
    root_path, auto_refresh, refresh_seconds = setup_page_and_sidebar()

    # Modultyp und Messlauf auswählen:
    (
        selected_module_type_name,
        selected_measurement_run_name,
        selected_measurement_run_folder,
    ) = select_module_type_and_measurement_run(root_path)

    # Cont-Datei auswählen:
    cont_files, selected_cont_folder_label = select_cont_files(
        selected_measurement_run_folder,
        auto_refresh,
        refresh_seconds,
    )

    # Cont-Daten einlesen:
    df_raw, df_long = load_selected_cont_data(cont_files)

    # Die Modulzuordnung wird vorbereitet. Angezeigt wird sie unten im
    # Rohdaten-/Exportbereich, damit das Dashboard oben nicht mit Tabellen startet.
    available_pairs = sorted(df_long["module_pair"].dropna().unique())
    module_mapping_table = make_module_mapping_table(available_pairs)

    # Module auswählen:
    df_selected_modules = select_modules(df_long)
    # Zeitbereich filtern:
    df_filtered = filter_by_time_range(df_selected_modules)

    df_raw_filtered = filter_raw_data_like_dashboard_selection(df_raw, df_filtered)
    df_raw_display = order_raw_columns_for_display(df_raw_filtered)

    # Dashboard anzeigen:
    render_overview_container(
        selected_module_type_name,
        selected_measurement_run_name,
        selected_cont_folder_label,
        cont_files,
        df_filtered,
    )

    # erzeugt Diagramme für: Leistung, Spannung, Strom, Temp, Lichtintensität
    render_electrical_charts(df_filtered)
    render_energy_chart(df_filtered)
    render_sensor_values(df_raw_filtered)
    # zeigt Modulzuordnung, Rohdatenvorschau, CSV-Download
    render_raw_data_export(df_raw_display, module_mapping_table)


# Wenn diese Datei gestartet wird, dann führe die Funktion main() aus:
if __name__ == "__main__":
    main()
