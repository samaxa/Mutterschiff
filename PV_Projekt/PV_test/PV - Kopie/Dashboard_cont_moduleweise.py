# Dashboard_cont_moduleweise.py
# ------------------------------------------------------------
# Start in der Konsole / im Terminal:
# streamlit run Dashboard_cont_moduleweise.py
#
# Zweck des Skripts:
# Dieses Streamlit-Dashboard liest ausschließlich die fortlaufend aktualisierten
# Cont-Dateien aus dem synchronisierten Sciebo-Ordner ein.
#
# Wichtig:
# Die Scan-Dateien werden bewusst ignoriert.
# In den Cont-Dateien stehen pro Messzeitpunkt zwei Modulkanäle:
# - MPP Volt1 / Curr1 / Power1 gehört zum ersten Modul der Modulkennung
# - MPP Volt2 / Curr2 / Power2 gehört zum zweiten Modul der Modulkennung
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

# Standardpfad zum synchronisierten Sciebo-Referenzdatensatz.
# Dieser Pfad ist nur der Default-Wert und kann im Dashboard überschrieben werden.
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


# ============================================================
# 2) Hilfsfunktionen
# ============================================================


def get_date_from_folder_name(folder_path: Path) -> pd.Timestamp:
    """
    Liest ein Datum aus einem Messlauf-Ordnernamen.

    Erwartetes Format:
        YYYY-MM-DD

    Beispiel:
        Ordnername "2026-05-22" wird als Datum 2026-05-22 erkannt.

    Warum nicht nach Änderungsdatum sortieren?
    Sciebo/Windows kann Ordner später erneut anfassen oder synchronisieren.
    Dann wäre das Änderungsdatum nicht mehr identisch mit dem eigentlichen Messtag.
    Deshalb sortieren wir bewusst nach dem Datum im Ordnernamen.
    """

    try:
        return pd.to_datetime(folder_path.name, format="%Y-%m-%d")
    except ValueError:
        # Falls ein Ordner nicht wie ein Datum heißt, landet er unten in der Liste.
        return pd.Timestamp.min



def read_file_metadata(file_path: Path) -> dict:
    """
    Liest Metadaten aus dem Kopfbereich einer Cont-Datei.

    Gesucht werden aktuell:
    - Name: Modultyp, z. B. AE435CMD-108BDS
    - Modul Kennung: Modulpaar, z. B. Modul-1_6

    Die Funktion liest nur den Header. Sobald die Zeile mit "Time" beginnt,
    werden die eigentlichen Messdaten erwartet und die Suche im Header endet.
    """

    metadata = {
        "module_type_from_file": "unbekannt",
        "module_pair": "unbekannt",
    }

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line = line.strip()

            if line.startswith("Name"):
                # Beispiel: Name    AE435CMD-108BDS
                parts = re.split(r"\t+|\s{2,}", line)
                if len(parts) >= 2:
                    metadata["module_type_from_file"] = parts[1].strip()

            elif line.startswith("Modul Kennung"):
                # Beispiel: Modul Kennung    Modul-1_6
                parts = re.split(r"\t+|\s{2,}", line)
                if len(parts) >= 2:
                    metadata["module_pair"] = parts[1].strip()

            elif line.startswith("Time"):
                break

    return metadata



def get_modules_from_pair(module_pair: str) -> tuple[str | None, str | None]:
    """
    Extrahiert die beiden Modulnummern aus einer Modulkennung.

    Beispiel:
        "Modul-1_6" -> ("1", "6")

    Kanalzuordnung:
        Kanal 1 / Volt1 / Curr1 / Power1 gehört zum ersten Modul.
        Kanal 2 / Volt2 / Curr2 / Power2 gehört zum zweiten Modul.
    """

    match = re.search(r"Modul-(\d+)_(\d+)", str(module_pair))

    if not match:
        return None, None

    return match.group(1), match.group(2)



def read_cont_file(file_path: Path) -> pd.DataFrame:
    """
    Liest eine einzelne Cont-Datei ein.

    Pro Messzeitpunkt entstehen zwei Tabellenzeilen:
    - eine Zeile für Kanal 1 bzw. das erste Modul der Modulkennung
    - eine Zeile für Kanal 2 bzw. das zweite Modul der Modulkennung

    Erwartete Messspalten in der Cont-Datei:

        Date Time Mode
        MPP Volt1 [V] MPP Curr1 [A] MPP Power1 [W]
        MPP Volt2 [V] MPP Curr2 [A] MPP Power2 [W]
        Temperature [...]
        Light Intensity [W/m²]
        Open Circuit Volt1 [V] Short Circuit Curr1 [A] Fill Factor1 [%] Energy1 [kWh]
        Open Circuit Volt2 [V] Short Circuit Curr2 [A] Fill Factor2 [%] Energy2 [kWh]

    Für das Dashboard sind vor allem MPP-Spannung, MPP-Strom und MPP-Leistung wichtig.
    Die zusätzlichen Werte werden trotzdem mit eingelesen, falls sie später gebraucht werden.
    """

    metadata = read_file_metadata(file_path)
    module_pair = metadata["module_pair"]
    module_1, module_2 = get_modules_from_pair(module_pair)

    rows = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line = line.strip()

            # Nur echte Messzeilen auswerten. Messzeilen beginnen mit einem Datum.
            if not re.match(r"^\d{4}-\d{2}-\d{2}", line):
                continue

            parts = re.split(r"\s+", line)

            # Mindestanforderung:
            # Date, Time, Mode, Volt1, Curr1, Power1, Volt2, Curr2, Power2
            if len(parts) < 9:
                continue

            try:
                timestamp = pd.to_datetime(parts[0] + " " + parts[1])
                mode = parts[2]

                common_data = {
                    "datetime": timestamp,
                    "date": parts[0],
                    "time": parts[1],
                    "mode": mode,
                    "module_type_from_file": metadata["module_type_from_file"],
                    "module_pair": module_pair,
                    "source_file": file_path.name,
                    "source_path": str(file_path),
                    "last_modified": pd.to_datetime(file_path.stat().st_mtime, unit="s"),
                }

                # Einige Zusatzgrößen stehen nur einmal pro Messzeitpunkt in der Datei.
                temperature = float(parts[9]) if len(parts) > 9 else None
                light_intensity = float(parts[10]) if len(parts) > 10 else None

                # Kanal 1: gehört zum ersten Modul der Modulkennung.
                rows.append(
                    {
                        **common_data,
                        "channel": 1,
                        "module_number": module_1,
                        "module_label": f"Modul {module_1}" if module_1 else "Modul unbekannt",
                        "orientation": MODULE_ORIENTATION.get(module_1, "unbekannt"),
                        "mpp_voltage_v": float(parts[3]),
                        "mpp_current_a": float(parts[4]),
                        "mpp_power_w": float(parts[5]),
                        "temperature": temperature,
                        "light_intensity_w_m2": light_intensity,
                        "open_circuit_voltage_v": float(parts[11]) if len(parts) > 11 else None,
                        "short_circuit_current_a": float(parts[12]) if len(parts) > 12 else None,
                        "fill_factor_percent": float(parts[13]) if len(parts) > 13 else None,
                        "energy_kwh": float(parts[14]) if len(parts) > 14 else None,
                    }
                )

                # Kanal 2: gehört zum zweiten Modul der Modulkennung.
                rows.append(
                    {
                        **common_data,
                        "channel": 2,
                        "module_number": module_2,
                        "module_label": f"Modul {module_2}" if module_2 else "Modul unbekannt",
                        "orientation": MODULE_ORIENTATION.get(module_2, "unbekannt"),
                        "mpp_voltage_v": float(parts[6]),
                        "mpp_current_a": float(parts[7]),
                        "mpp_power_w": float(parts[8]),
                        "temperature": temperature,
                        "light_intensity_w_m2": light_intensity,
                        "open_circuit_voltage_v": float(parts[15]) if len(parts) > 15 else None,
                        "short_circuit_current_a": float(parts[16]) if len(parts) > 16 else None,
                        "fill_factor_percent": float(parts[17]) if len(parts) > 17 else None,
                        "energy_kwh": float(parts[18]) if len(parts) > 18 else None,
                    }
                )

            except ValueError:
                # Kaputte oder unvollständig formatierte Messzeilen werden übersprungen.
                continue

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(["datetime", "module_number", "channel"])

    return df



def read_multiple_cont_files(file_paths: list[Path]) -> pd.DataFrame:
    """
    Liest mehrere Cont-Dateien ein und führt sie zu einer gemeinsamen Tabelle zusammen.

    Scan-Dateien werden hier nicht eingelesen. Die Funktion bekommt nur Cont-Dateien,
    die vorher gezielt gesucht wurden.
    """

    all_dfs = []

    for file_path in file_paths:
        df = read_cont_file(file_path)

        if df.empty:
            continue

        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values(["datetime", "module_number", "channel"])

    return df_all



def find_cont_files(search_folder: Path) -> list[Path]:
    """
    Sucht ausschließlich Cont-Textdateien im ausgewählten Messlauf.

    Wichtig:
    Scan-Dateien werden bewusst ignoriert.

    Die Suche ist rekursiv, weil die Cont-Datei teilweise in einem Unterordner liegt,
    der ebenfalls nach dem Cont-Messlauf benannt ist.
    """

    cont_files = []

    for file_path in search_folder.rglob("*.txt"):
        if not file_path.is_file():
            continue

        # Nur Dateien verwenden, deren Dateiname mit "Cont" beginnt.
        # Dadurch werden Scan-Dateien sicher ausgeschlossen.
        if file_path.name.startswith("Cont"):
            cont_files.append(file_path)

    return sorted(cont_files)


# ============================================================
# 3) Streamlit-Seite und Sidebar aufbauen
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
# 4) Ordnerstruktur auswerten: Modultyp und Messlauf wählen
# ============================================================

root_path = Path(file_path_input)

if not root_path.exists():
    st.error(f"Ordner nicht gefunden: {root_path}")
    st.stop()

# Direkte Unterordner im Referenzdatensatz entsprechen den Modultypen.
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

# Messlauf-Ordner werden nach Datum im Ordnernamen sortiert.
# Neuester Messtag erscheint oben.
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
# 5) Cont-Dateien suchen und Messdaten einlesen
# ============================================================

search_folder = selected_module_type_folder / selected_measurement_run_name
cont_files = find_cont_files(search_folder)

st.write(f"Ausgewählter Modultyp: {selected_module_type_name}")
st.write(f"Ausgewählter Messlauf: {selected_measurement_run_name}")
st.write(f"Gefundene Cont-Dateien: {len(cont_files)}")

if not cont_files:
    st.warning("Für diese Auswahl wurden keine Cont-Dateien gefunden.")
    st.stop()

df = read_multiple_cont_files(cont_files)

if df.empty:
    st.warning("Die Cont-Dateien wurden gefunden, aber es konnten keine Messdaten erkannt werden.")
    st.stop()


# ============================================================
# 6) Module auswählen
# ============================================================

st.sidebar.subheader("Module")

available_pairs = sorted(df["module_pair"].dropna().unique())
st.info(
    "Eingelesene Modulpaare: "
    + ", ".join(available_pairs)
    + ". Kanal 1 gehört jeweils zum ersten Modul der Kennung, Kanal 2 zum zweiten Modul."
)

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
    default=module_display_options,
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
# 7) Zeitbereich auswählen und Daten zeitlich filtern
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

# "Letzte X" bezieht sich auf den letzten Messpunkt in der Datei,
# nicht unbedingt auf die aktuelle Uhrzeit des Computers.
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


# ============================================================
# 8) Kennzahlen anzeigen
# ============================================================

if df_filtered.empty:
    st.warning("Für den ausgewählten Zeitraum sind keine Daten vorhanden.")
    st.stop()

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

# Letzte Messwerte pro ausgewähltem Modul.
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
            "temperature",
            "light_intensity_w_m2",
        ]
    ],
    use_container_width=True,
)


# ============================================================
# 9) Diagramme erstellen
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


# Optional: Einstrahlung und Temperatur anzeigen, falls in den Cont-Dateien vorhanden.
with st.expander("Temperatur und Einstrahlung anzeigen"):
    sensor_df = df_filtered.drop_duplicates(subset=["datetime", "module_pair"])

    fig_temp = px.line(
        sensor_df,
        x="datetime",
        y="temperature",
        color="module_pair",
        title="Temperatur über die Zeit",
        labels={
            "datetime": "Zeit",
            "temperature": "Temperatur",
            "module_pair": "Modulpaar",
        },
    )
    st.plotly_chart(fig_temp, use_container_width=True)

    fig_light = px.line(
        sensor_df,
        x="datetime",
        y="light_intensity_w_m2",
        color="module_pair",
        title="Light Intensity über die Zeit",
        labels={
            "datetime": "Zeit",
            "light_intensity_w_m2": "Light Intensity [W/m²]",
            "module_pair": "Modulpaar",
        },
    )
    st.plotly_chart(fig_light, use_container_width=True)


# ============================================================
# 10) Tabelle und CSV-Download
# ============================================================

st.subheader("Messdatentabelle")

st.dataframe(df_filtered, use_container_width=True)

csv = df_filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Messdaten als CSV herunterladen",
    data=csv,
    file_name="pv_cont_messdaten_export.csv",
    mime="text/csv",
)
