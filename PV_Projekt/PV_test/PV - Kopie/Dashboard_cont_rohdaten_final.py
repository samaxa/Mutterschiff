# Dashboard_cont_rohdaten_als_haupttabelle.py
# ------------------------------------------------------------
# Start in der Konsole / im Terminal:
# streamlit run Dashboard_cont_rohdaten_als_haupttabelle.py
#
# Zweck des Skripts:
# Dieses Streamlit-Dashboard liest ausschließlich die fortlaufend aktualisierten
# Cont-Dateien aus dem synchronisierten Sciebo-Ordner ein.
#
# Wichtig:
# - Scan-Dateien werden bewusst ignoriert.
# - Die Cont-Datei enthält pro Messzeitpunkt zwei Messkanäle:
#   Kanal 1 = Volt1 / Curr1 / Power1 / ...1
#   Kanal 2 = Volt2 / Curr2 / Power2 / ...2
# - Die Modulkennung im Header legt fest, welches reale Modul zu Kanal 1
#   und Kanal 2 gehört.
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

import pandas as pd
import streamlit as st
import plotly.express as px


# ============================================================
# 1) Grundeinstellungen
# ============================================================

MESS_ROOT = Path(
    r"C:\Users\sarah\OneDrive - TH Köln\Desktop\4.Semester\PV\Messdaten_PV_Sciebo\Referenzdatensatz"
)

# Manuelle Zuordnung der einzelnen Module zu ihrer Ausrichtung.
MODULE_ORIENTATION = {
    "1": "Süd",
    "2": "Süd",
    "3": "Süd",
    "4": "Ost/West",
    "5": "Ost/West",
    "6": "Ost/West",
}

# Sehr große negative Fehlerwerte aus dem Messgerät werden als ungültig behandelt.
# Beispiel aus einer Cont-Datei: -9223372036854776.000
INVALID_VALUE_LIMIT = -1e12

# Die Cont-Dateien kommen offenbar nicht immer als echtes UTF-8.
# Das Gradzeichen in "Temperature [°C]" ist häufig Windows-/ANSI-kodiert.
# cp1252 kann diese Dateien stabil lesen.
FILE_ENCODING = "cp1252"

# Leere numerische Felder aus der Cont-Datei werden für Anzeige und Export als 0 behandelt.
# Hintergrund: In den Track-Zeilen lässt das Messgerät manche Spalten leer,
# Excel/manuelle Aufbereitung interpretiert diese Felder häufig als 0.
FILL_EMPTY_NUMERIC_WITH_ZERO = True


# ============================================================
# 2) Hilfsfunktionen für Ordner, Dateien und Metadaten
# ============================================================


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

    Erwartetes Muster:
        ...--YYYY-MM-DD--HH-MM-SS...

    Beispiel:
        Cont--2--Modul-1_6--2026-05-22--13-25-36
        -> 2026-05-22 13:25:36
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

    Beispiel:
        "Modul-1_6" -> ("1", "6")
    """

    match = re.search(r"Modul-(\d+)_(\d+)", str(module_pair))

    if not match:
        return None, None

    return match.group(1), match.group(2)


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

    metadata = {
        "module_type_from_file": "unbekannt",
        "load1": None,
        "load2": None,
        "measurement_start": pd.NaT,
        "module_pair": "unbekannt",
    }

    with open(file_path, "r", encoding=FILE_ENCODING, errors="ignore") as file:
        for line in file:
            line = line.strip()

            if line.startswith("Time"):
                break

            parts = re.split(r"\t+|\s{2,}", line, maxsplit=1)

            if len(parts) < 2:
                continue

            key = parts[0].strip()
            value = parts[1].strip()

            if key == "Name":
                metadata["module_type_from_file"] = value

            elif key == "Load1":
                metadata["load1"] = value

            elif key == "Load2":
                metadata["load2"] = value

            elif key == "Date":
                metadata["measurement_start"] = pd.to_datetime(value, errors="coerce")

            elif key == "Modul Kennung":
                metadata["module_pair"] = value

    return metadata


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
        p for p in cont_folder.glob("*.txt")
        if p.is_file() and p.name.startswith("Cont")
    ]

    if not cont_txt_files:
        return None

    return max(cont_txt_files, key=lambda p: p.stat().st_mtime)


def get_latest_cont_file_mtime(cont_folder: Path) -> float:
    """
    Gibt den Änderungszeitpunkt der fortlaufend aktualisierten Cont-Datei zurück.

    Das ist für die Sortierung sinnvoller als das Ordner-Änderungsdatum.
    """

    latest_file = get_latest_cont_txt_file(cont_folder)

    if latest_file is not None:
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
        p for p in measurement_run_folder.iterdir()
        if p.is_dir() and p.name.startswith("Cont")
    ]

    return sorted(cont_folders, key=get_latest_cont_file_mtime, reverse=True)


def make_cont_folder_label(cont_folder: Path) -> str:
    """
    Erzeugt einen verständlichen Anzeigenamen für die Cont-Ordner-Auswahl.
    """

    module_pair = get_module_pair_from_name(cont_folder)
    start_timestamp = get_timestamp_from_cont_name(cont_folder)
    latest_file = get_latest_cont_txt_file(cont_folder)

    start_text = (
        start_timestamp.strftime("%d.%m.%Y %H:%M:%S")
        if pd.notna(start_timestamp) and start_timestamp != pd.Timestamp.min
        else "unbekannt"
    )

    if latest_file is not None:
        modified_text = pd.to_datetime(
            latest_file.stat().st_mtime,
            unit="s",
        ).strftime("%d.%m.%Y %H:%M:%S")
    else:
        modified_text = "keine Cont-Datei gefunden"

    return f"{module_pair} | Start: {start_text} | Cont geändert: {modified_text}"


def find_cont_files(search_folder: Path) -> list[Path]:
    """
    Fallback-Suche: Sucht rekursiv nach Cont-Textdateien.

    Scan-Dateien werden ausgeschlossen, weil nur Dateinamen mit "Cont" erlaubt sind.
    """

    cont_files = []

    for file_path in search_folder.rglob("*.txt"):
        if file_path.is_file() and file_path.name.startswith("Cont"):
            cont_files.append(file_path)

    return sorted(cont_files)


# ============================================================
# 3) Hilfsfunktionen zum Einlesen der Cont-Dateien
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

    # Metadaten ergänzen.
    df_raw["module_type_from_file"] = metadata["module_type_from_file"]
    df_raw["load1"] = metadata["load1"]
    df_raw["load2"] = metadata["load2"]
    df_raw["measurement_start"] = metadata["measurement_start"]
    df_raw["module_pair"] = metadata["module_pair"]
    df_raw["source_file"] = file_path.name
    df_raw["source_path"] = str(file_path)
    df_raw["last_modified"] = pd.to_datetime(file_path.stat().st_mtime, unit="s")

    df_raw = df_raw.sort_values("datetime")

    return df_raw


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

    Diese lange Form ist für Plotly-Diagramme und Modulfilter deutlich praktischer.
    """

    if df_raw.empty:
        return pd.DataFrame()

    module_pair = str(df_raw["module_pair"].iloc[0])
    module_1, module_2 = get_modules_from_pair(module_pair)

    common_columns = [
        "datetime",
        "date",
        "time_of_day",
        "Mode",
        "module_type_from_file",
        "module_pair",
        "source_file",
        "source_path",
        "last_modified",
        "load1",
        "load2",
        "measurement_start",
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

        df_channel["temperature_c"] = get_column_or_na(df_raw, "Temperature [°C]")
        df_channel["light_intensity_w_m2"] = get_column_or_na(df_raw, "Light Intensity [W/m2]")

        df_channel["open_circuit_voltage_v"] = get_column_or_na(
            df_raw,
            f"Open Circuit Volt{channel} [V]",
        )
        df_channel["short_circuit_current_a"] = get_column_or_na(
            df_raw,
            f"Short Circuit Curr{channel} [A]",
        )
        df_channel["fill_factor_percent"] = get_column_or_na(
            df_raw,
            f"Fill Factor{channel} [%]",
        )
        df_channel["energy_kwh"] = get_column_or_na(df_raw, f"Energy{channel} [kWh]")

        channel_frames.append(df_channel)

    df_long = pd.concat(channel_frames, ignore_index=True)
    df_long = df_long.sort_values(["datetime", "channel"])

    return df_long


def read_multiple_cont_files(file_paths: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Liest mehrere Cont-Dateien ein.

    Rückgabe:
    - df_raw_all: breite Rohdaten aus den Cont-Dateien, möglichst nah am Original
    - df_long_all: modulweise Tabelle für Dashboard und Diagramme
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


def make_module_mapping_table(module_pairs: list[str]) -> pd.DataFrame:
    """
    Erstellt eine Übersicht, welche Module in welchen Kanälen stecken.

    Diese Tabelle dient im Dashboard als intuitive Hilfe für die Modulauswahl.
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


def order_raw_columns_for_display(df_raw_table: pd.DataFrame) -> pd.DataFrame:
    """
    Sortiert die Rohdatentabelle so, dass zuerst die originalen Cont-Spalten
    stehen und die zusätzlich erzeugten Hilfsspalten danach folgen.
    """

    original_columns = [
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

    extra_columns = [
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
        "last_modified",
    ]

    ordered_columns = [col for col in original_columns + extra_columns if col in df_raw_table.columns]
    remaining_columns = [col for col in df_raw_table.columns if col not in ordered_columns]

    return df_raw_table[ordered_columns + remaining_columns]


# ============================================================
# 4) Streamlit-Seite und Sidebar aufbauen
# ============================================================

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
)

auto_refresh = st.sidebar.checkbox(
    "Automatische Aktualisierung aktivieren",
    value=False,
)

refresh_seconds = st.sidebar.number_input(
    "Aktualisierung alle X Sekunden",
    min_value=10,
    max_value=600,
    value=60,
    step=10,
)

if st.sidebar.button("Jetzt manuell aktualisieren"):
    st.rerun()

if auto_refresh:
    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_seconds}'>",
        unsafe_allow_html=True,
    )


# ============================================================
# 5) Ordnerstruktur auswerten: Modultyp und Messlauf wählen
# ============================================================

root_path = Path(file_path_input)

if not root_path.exists():
    st.error(f"Ordner nicht gefunden: {root_path}")
    st.stop()

module_type_folders = sorted([p for p in root_path.iterdir() if p.is_dir()])

if not module_type_folders:
    st.error("Keine Modultyp-Ordner gefunden.")
    st.stop()

module_type_names = [folder.name for folder in module_type_folders]

selected_module_type_name = st.sidebar.selectbox(
    "Modultyp auswählen",
    ["Bitte Modultyp auswählen"] + module_type_names,
)

if selected_module_type_name == "Bitte Modultyp auswählen":
    st.info("Bitte zuerst einen Modultyp auswählen, um Messdaten anzuzeigen.")
    st.stop()

selected_module_type_folder = root_path / selected_module_type_name

measurement_run_folders = sorted(
    [p for p in selected_module_type_folder.iterdir() if p.is_dir()],
    key=get_date_from_folder_name,
    reverse=True,
)

measurement_run_names = [folder.name for folder in measurement_run_folders]

selected_measurement_run_name = st.sidebar.selectbox(
    "Messlauf auswählen",
    ["Bitte Messlauf auswählen"] + measurement_run_names,
)

if selected_measurement_run_name == "Bitte Messlauf auswählen":
    st.info("Bitte zuerst einen Messlauf auswählen, um Messdaten anzuzeigen.")
    st.stop()


# ============================================================
# 6) Cont-Messordner auswählen und Cont-Dateien einlesen
# ============================================================

search_folder = selected_module_type_folder / selected_measurement_run_name

cont_measurement_folders = find_cont_measurement_folders(search_folder)

st.write(f"Ausgewählter Modultyp: {selected_module_type_name}")
st.write(f"Ausgewählter Messlauf: {selected_measurement_run_name}")

if cont_measurement_folders:
    st.sidebar.subheader("Cont-Messordner")

    cont_folder_label_map = {
        make_cont_folder_label(folder): folder
        for folder in cont_measurement_folders
    }

    cont_folder_options = [
        "Bitte Cont-Messordner auswählen",
        "Alle Cont-Ordner einlesen",
    ] + list(cont_folder_label_map.keys())

    selected_cont_folder_label = st.sidebar.selectbox(
        "Cont-Messordner auswählen",
        cont_folder_options,
    )

    if selected_cont_folder_label == "Bitte Cont-Messordner auswählen":
        st.info("Bitte einen Cont-Messordner auswählen, um Messdaten einzulesen.")
        st.stop()

    if selected_cont_folder_label == "Alle Cont-Ordner einlesen":
        selected_cont_folders = cont_measurement_folders
    else:
        selected_cont_folders = [cont_folder_label_map[selected_cont_folder_label]]

    cont_files = []

    for cont_folder in selected_cont_folders:
        latest_cont_file = get_latest_cont_txt_file(cont_folder)

        if latest_cont_file is not None:
            cont_files.append(latest_cont_file)

    st.write(f"Gefundene Cont-Messordner: {len(cont_measurement_folders)}")
    st.write(f"Eingelesene Cont-Dateien: {len(cont_files)}")

else:
    cont_files = find_cont_files(search_folder)

    st.write("Keine separaten Cont-Messordner gefunden. Suche direkt nach Cont-Dateien.")
    st.write(f"Gefundene Cont-Dateien: {len(cont_files)}")

if not cont_files:
    st.warning("Für diese Auswahl wurden keine Cont-Dateien gefunden.")
    st.stop()

with st.expander("Eingelesene Cont-Dateien anzeigen"):
    cont_file_info = pd.DataFrame(
        {
            "Cont-Datei": [file.name for file in cont_files],
            "Pfad": [str(file) for file in cont_files],
            "Zuletzt geändert": [
                pd.to_datetime(file.stat().st_mtime, unit="s").strftime("%d.%m.%Y %H:%M:%S")
                for file in cont_files
            ],
        }
    )
    st.dataframe(cont_file_info, use_container_width=True)

df_raw, df = read_multiple_cont_files(cont_files)

if df.empty or df_raw.empty:
    st.warning("Die Cont-Dateien wurden gefunden, aber es konnten keine Messdaten erkannt werden.")
    st.stop()


# ============================================================
# 7) Modulzuordnung anzeigen und Module auswählen
# ============================================================

available_pairs = sorted(df["module_pair"].dropna().unique())

st.subheader("Modulzuordnung")

st.caption(
    "Die Cont-Datei enthält zwei Messkanäle. "
    "Kanal 1 gehört zum ersten Modul der Modulkennung, Kanal 2 zum zweiten Modul."
)

module_mapping_table = make_module_mapping_table(available_pairs)
st.dataframe(module_mapping_table, use_container_width=True, hide_index=True)

st.sidebar.subheader("Module")

module_options_df = (
    df[["module_number", "module_label", "orientation"]]
    .drop_duplicates()
    .sort_values("module_number")
)

module_options_df["display_name"] = (
    module_options_df["module_label"]
    + " – "
    + module_options_df["orientation"]
)

module_display_options = module_options_df["display_name"].tolist()

selected_module_display_names = st.sidebar.multiselect(
    "Einzelne Module auswählen",
    module_display_options,
    default=[],
)

if not selected_module_display_names:
    st.info("Bitte mindestens ein Modul auswählen, um Messdaten anzuzeigen.")
    st.stop()

selected_module_numbers = module_options_df.loc[
    module_options_df["display_name"].isin(selected_module_display_names),
    "module_number",
].tolist()

df = df[df["module_number"].isin(selected_module_numbers)]

if df.empty:
    st.warning("Für die ausgewählten Module sind keine Daten vorhanden.")
    st.stop()


# ============================================================
# 8) Zeitbereich auswählen und Daten zeitlich filtern
# ============================================================

st.sidebar.subheader("Zeitbereich")

min_datetime = df["datetime"].min()
max_datetime = df["datetime"].max()

time_range_option = st.sidebar.selectbox(
    "Anzuzeigender Zeitraum",
    [
        "Gesamter Zeitraum",
        "Letzte 5 Minuten",
        "Letzte 15 Minuten",
        "Letzte 30 Minuten",
        "Letzte 60 Minuten",
        "Letzte 24 Stunden",
        "Letzte 7 Tage",
        "Letzte 30 Tage",
        "Monat der letzten Messung",
        "Jahr der letzten Messung",
        "Manuell auswählen",
    ],
)

if time_range_option == "Gesamter Zeitraum":
    df_filtered = df.copy()

elif time_range_option == "Letzte 5 Minuten":
    start_datetime = max_datetime - pd.Timedelta(minutes=5)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Letzte 15 Minuten":
    start_datetime = max_datetime - pd.Timedelta(minutes=15)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Letzte 30 Minuten":
    start_datetime = max_datetime - pd.Timedelta(minutes=30)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Letzte 60 Minuten":
    start_datetime = max_datetime - pd.Timedelta(hours=1)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Letzte 24 Stunden":
    start_datetime = max_datetime - pd.Timedelta(hours=24)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Letzte 7 Tage":
    start_datetime = max_datetime - pd.Timedelta(days=7)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Letzte 30 Tage":
    start_datetime = max_datetime - pd.Timedelta(days=30)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Monat der letzten Messung":
    start_datetime = max_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Jahr der letzten Messung":
    start_datetime = max_datetime.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    df_filtered = df[df["datetime"] >= start_datetime]

else:
    start_date = st.sidebar.date_input(
        "Startdatum",
        value=min_datetime.date(),
        min_value=min_datetime.date(),
        max_value=max_datetime.date(),
    )

    end_date = st.sidebar.date_input(
        "Enddatum",
        value=max_datetime.date(),
        min_value=min_datetime.date(),
        max_value=max_datetime.date(),
    )

    st.sidebar.caption(
        f"Verfügbare Zeitspanne: "
        f"{min_datetime.strftime('%d.%m.%Y %H:%M:%S')} bis "
        f"{max_datetime.strftime('%d.%m.%Y %H:%M:%S')}"
    )

    start_time_text = st.sidebar.text_input(
        "Startzeit (HH:MM oder HH:MM:SS)",
        value=min_datetime.strftime("%H:%M:%S"),
    )

    end_time_text = st.sidebar.text_input(
        "Endzeit (HH:MM oder HH:MM:SS)",
        value=max_datetime.strftime("%H:%M:%S"),
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

    df_filtered = df[
        (df["datetime"] >= start_datetime)
        & (df["datetime"] <= end_datetime)
    ]

# Falls nach Zeitfilter keine Daten mehr vorhanden sind, muss hier gestoppt werden,
# bevor die Rohdaten passend dazu gefiltert werden.
if df_filtered.empty:
    st.warning("Für den ausgewählten Zeitraum sind keine Daten vorhanden.")
    st.stop()

# Rohdaten passend zum ausgewählten Zeitbereich filtern.
# Der Modulfilter wird hier bewusst nicht angewendet, weil die Rohdaten weiterhin
# exakt die breite Struktur der Cont-Datei enthalten: Kanal 1 und Kanal 2 stehen
# dort in derselben Zeile.
raw_source_files = df_filtered["source_file"].dropna().unique().tolist()
df_raw_filtered = df_raw[
    (df_raw["source_file"].isin(raw_source_files))
    & (df_raw["datetime"] >= df_filtered["datetime"].min())
    & (df_raw["datetime"] <= df_filtered["datetime"].max())
].copy()

df_raw_display = order_raw_columns_for_display(df_raw_filtered)


# ============================================================
# 9) Rohdaten-Tabelle zuerst anzeigen
# ============================================================

st.subheader("Rohdaten aus der Cont-Datei")

st.caption(
    "Diese Tabelle bleibt möglichst nah an der Cont-Datei: pro Zeitpunkt eine Zeile, "
    "Kanal 1 und Kanal 2 stehen nebeneinander. Zusätzlich wurden datetime, date "
    "und time_of_day ergänzt. Leere numerische Messfelder werden als 0 dargestellt."
)
st.dataframe(prepare_display_table(df_raw_display), use_container_width=True)



# ============================================================
# 10) Kennzahlen anzeigen
# ============================================================

first_datetime = df_filtered["datetime"].min()
latest_datetime = df_filtered["datetime"].max()

time_col1, time_col2 = st.columns(2)

time_col1.metric(
    "Erster Messzeitpunkt",
    first_datetime.strftime("%d.%m.%Y %H:%M:%S"),
)

time_col2.metric(
    "Letzter Messzeitpunkt",
    latest_datetime.strftime("%d.%m.%Y %H:%M:%S"),
)

latest_per_module = (
    df_filtered
    .sort_values("datetime")
    .groupby(["module_number", "module_label", "orientation"], as_index=False)
    .tail(1)
    .sort_values("module_number")
)

st.subheader("Aktuelle Messwerte je Modul")
st.dataframe(
    latest_per_module[
        [
            "datetime",
            "module_label",
            "orientation",
            "mpp_power_w",
            "mpp_voltage_v",
            "mpp_current_a",
            "temperature_c",
            "light_intensity_w_m2",
        ]
    ],
    use_container_width=True,
)


# ============================================================
# 11) Diagramme erstellen
# ============================================================

st.subheader("MPP-Leistung über die Zeit")

fig_power = px.line(
    df_filtered,
    x="datetime",
    y="mpp_power_w",
    color="module_label",
    line_dash="mode",
    hover_data=["orientation", "module_pair", "channel"],
    title="PV-Leistung über die Zeit nach Einzelmodul",
    labels={
        "datetime": "Zeit",
        "mpp_power_w": "MPP-Leistung [W]",
        "module_label": "Modul",
        "mode": "Messmodus",
        "orientation": "Ausrichtung",
    },
)

st.plotly_chart(fig_power, use_container_width=True)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("MPP-Spannung")
    fig_voltage = px.line(
        df_filtered,
        x="datetime",
        y="mpp_voltage_v",
        color="module_label",
        line_dash="mode",
        hover_data=["orientation", "module_pair", "channel"],
        labels={
            "datetime": "Zeit",
            "mpp_voltage_v": "MPP-Spannung [V]",
            "module_label": "Modul",
            "mode": "Messmodus",
            "orientation": "Ausrichtung",
        },
    )
    st.plotly_chart(fig_voltage, use_container_width=True)

with col_right:
    st.subheader("MPP-Strom")
    fig_current = px.line(
        df_filtered,
        x="datetime",
        y="mpp_current_a",
        color="module_label",
        line_dash="mode",
        hover_data=["orientation", "module_pair", "channel"],
        labels={
            "datetime": "Zeit",
            "mpp_current_a": "MPP-Strom [A]",
            "module_label": "Modul",
            "mode": "Messmodus",
            "orientation": "Ausrichtung",
        },
    )
    st.plotly_chart(fig_current, use_container_width=True)

with st.expander("Temperatur und Einstrahlung anzeigen"):
    st.caption(
        "Temperatur und Light Intensity stehen in der Cont-Datei nur einmal pro "
        "Zeitpunkt und nicht getrennt für Volt1/Volt2 bzw. Modul 1/Modul 2. "
        "Sie werden deshalb als Sensorwerte je Cont-Datei/Modulpaar angezeigt."
    )

    sensor_df = df_raw_filtered.copy()

    fig_temp = px.line(
        sensor_df,
        x="datetime",
        y="Temperature [°C]",
        color="Mode",
        line_dash="Mode",
        title="Temperatur über die Zeit je Cont-Datei/Modulpaar",
        labels={
            "datetime": "Zeit",
            "Temperature [°C]": "Temperatur [°C]",
            "Mode": "Messmodus",
        },
    )
    st.plotly_chart(fig_temp, use_container_width=True)

    fig_light = px.line(
        sensor_df,
        x="datetime",
        y="Light Intensity [W/m2]",
        color="module_pair",
        title="Light Intensity über die Zeit je Cont-Datei/Modulpaar",
        labels={
            "datetime": "Zeit",
            "Light Intensity [W/m2]": "Light Intensity [W/m²]",
            "module_pair": "Modulpaar",
        },
    )
    st.plotly_chart(fig_light, use_container_width=True)


# ============================================================
# 12) Tabellen und CSV-Downloads
# ============================================================

with st.expander("Modulweise aufbereitete Dashboard-Tabelle anzeigen"):
    st.caption(
        "Diese Tabelle ist für die Diagramme praktisch. Deshalb gibt es pro Zeitpunkt "
        "zwei Zeilen: eine für Kanal 1 und eine für Kanal 2."
    )
    st.dataframe(prepare_display_table(df_filtered), use_container_width=True)

csv_long = df_filtered.to_csv(index=False).encode("utf-8-sig")
csv_raw = df_raw_display.to_csv(index=False).encode("utf-8-sig")

download_col1, download_col2 = st.columns(2)

with download_col1:
    st.download_button(
        label="Aufbereitete Modul-Daten als CSV herunterladen",
        data=csv_long,
        file_name="pv_cont_modulweise_export.csv",
        mime="text/csv",
    )

with download_col2:
    st.download_button(
        label="Rohdaten aus Cont-Datei als CSV herunterladen",
        data=csv_raw,
        file_name="pv_cont_rohdaten_export.csv",
        mime="text/csv",
    )
