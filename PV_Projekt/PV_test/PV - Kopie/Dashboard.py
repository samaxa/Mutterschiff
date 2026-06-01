# Dashboard.py
# zum starten streamlit run Dashboard.py in Konsole eingeben
from pathlib import Path
import re
import pandas as pd
import streamlit as st
import plotly.express as px


# ------------------------------------------------------------
# Pfad zum synchronisierten Sciebo-Referenzdatensatz - ggf. anpassen!
# ------------------------------------------------------------

MESS_ROOT = Path(
    r"C:\Users\sarah\OneDrive - TH Köln\Desktop\4.Semester\PV\Messdaten_PV_Sciebo\Referenzdatensatz"
)


def read_file_metadata(file_path: Path) -> dict:
    metadata = {
        "module_type_from_file": "unbekannt",
        "module_pair": "unbekannt",
    }

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line = line.strip()

            if line.startswith("Name"):
                parts = re.split(r"\t+", line)
                if len(parts) >= 2:
                    metadata["module_type_from_file"] = parts[1].strip()

            elif line.startswith("Modul Kennung"):
                parts = re.split(r"\t+", line)
                if len(parts) >= 2:
                    metadata["module_pair"] = parts[1].strip()

            elif line.startswith("Time"):
                break

    return metadata




# ------------------------------------------------------------
# Messdatei einlesen
# ------------------------------------------------------------

def read_pv_file(file_path: Path) -> pd.DataFrame:
    rows = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line = line.strip()

            # Nur Messzeilen auswerten, die mit Datum beginnen
            if not re.match(r"^\d{4}-\d{2}-\d{2}", line):
                continue

            parts = re.split(r"\s+", line)

            # Erwartet:
            # Date Time Mode MPP_Volt MPP_Curr MPP_Power ...
            if len(parts) < 6:
                continue

            try:
                rows.append({
                    "datetime": pd.to_datetime(parts[0] + " " + parts[1]),
                    "date": parts[0],
                    "time": parts[1],
                    "mode": parts[2],
                    "mpp_voltage_v": float(parts[3]),
                    "mpp_current_a": float(parts[4]),
                    "mpp_power_w": float(parts[5]),
                })
            except ValueError:
                continue

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values("datetime")

    return df

def read_multiple_pv_files(file_paths: list[Path]) -> pd.DataFrame:
    all_dfs = []

    for file_path in file_paths:
        df = read_pv_file(file_path)

        if df.empty:
            continue

        metadata = read_file_metadata(file_path)

        df["module_type_from_file"] = metadata["module_type_from_file"]
        df["module_pair"] = metadata["module_pair"]
        df["source_file"] = file_path.name
        df["source_path"] = str(file_path)
        df["last_modified"] = pd.to_datetime(file_path.stat().st_mtime, unit="s")

        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values("datetime")

    return df_all





# ------------------------------------------------------------
# Streamlit Layout
# ------------------------------------------------------------

st.set_page_config(
    page_title="PV-Messdaten Dashboard",
    layout="wide"
)

st.title("PV-Messdaten Dashboard")
st.caption("Anzeige der automatisch synchronisierten PV-Messdaten")

st.sidebar.header("Einstellungen")

file_path_input = st.sidebar.text_input(
    "Pfad zum Referenzdatensatz",
    value=str(MESS_ROOT)
)


auto_refresh = st.sidebar.checkbox(
    "Automatische Aktualisierung aktivieren",
    value=False
)

refresh_seconds = st.sidebar.number_input(
    "Aktualisierung alle X Sekunden",
    min_value=10,
    max_value=600,
    value=60,
    step=10
)

if st.sidebar.button("Jetzt manuell aktualisieren"):
    st.rerun()

if auto_refresh:
    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_seconds}'>",
        unsafe_allow_html=True
    )


# ------------------------------------------------------------
# Daten laden
# ------------------------------------------------------------

root_path = Path(file_path_input)

if not root_path.exists():
    st.error(f"Ordner nicht gefunden: {root_path}")
    st.stop()

# Direkte Unterordner = Modultypen
module_type_folders = sorted([p for p in root_path.iterdir() if p.is_dir()])

if not module_type_folders:
    st.error("Keine Modultyp-Ordner gefunden.")
    st.stop()

module_type_names = [folder.name for folder in module_type_folders]

selected_module_type_name = st.sidebar.selectbox(
    "Modultyp auswählen",
    ["Bitte Modultyp auswählen"] + module_type_names
)

if selected_module_type_name == "Bitte Modultyp auswählen":
    st.info("Bitte zuerst einen Modultyp auswählen, um Messdaten anzuzeigen.")
    st.stop()

selected_module_type_folder = root_path / selected_module_type_name
# Messläufe innerhalb des ausgewählten Modultyps
# Messläufe nach Änderungsdatum sortieren: neuester zuerst
measurement_run_folders = sorted(
    [p for p in selected_module_type_folder.iterdir() if p.is_dir()],
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

measurement_run_names = [folder.name for folder in measurement_run_folders]

selected_measurement_run_name = st.sidebar.selectbox(
    "Messlauf auswählen",
    ["Bitte Messlauf auswählen"] + measurement_run_names
)

if selected_measurement_run_name == "Bitte Messlauf auswählen":
    st.info("Bitte zuerst einen Messlauf auswählen, um Messdaten anzuzeigen.")
    st.stop()

search_folder = selected_module_type_folder / selected_measurement_run_name
# Cont-Dateien suchen
cont_files = sorted(search_folder.rglob("*Cont*.txt"))

st.write(f"Ausgewählter Modultyp: {selected_module_type_name}")
st.write(f"Ausgewählter Messlauf: {selected_measurement_run_name}")
st.write(f"Gefundene Cont-Dateien: {len(cont_files)}")

if not cont_files:
    st.warning("Für diese Auswahl wurden keine Cont-Dateien gefunden.")
    st.stop()

# Alle gefundenen Cont-Dateien einlesen
df = read_multiple_pv_files(cont_files)

if df.empty:
    st.warning("Die Dateien wurden gefunden, aber es konnten keine Messdaten erkannt werden.")
    st.stop()

ORIENTATION_MAPPING = {
    "Modul-1_6": "Modul 1: Süd, Modul 6: Ost/West",
    "Modul-3_4": "Modul 3: Süd, Modul 4: Ost/West",
    "Modul-2_5": "Modul 2: Süd, Modul 5: Ost/West",
}

df["orientation_info"] = df["module_pair"].map(ORIENTATION_MAPPING).fillna("unbekannt")
# ------------------------------------------------------------
# Modulpaar filtern
# ------------------------------------------------------------

module_pair_options = sorted(df["module_pair"].dropna().unique())

selected_module_pairs = st.sidebar.multiselect(
    "Modulpaar auswählen",
    module_pair_options,
    default=[]
)

st.info(
    "Hinweis: Mehrere Modulpaare können gemeinsam angezeigt werden. "
    "Die Messzeitpunkte können sich jedoch je nach Messlauf unterscheiden."
)

if not selected_module_pairs:
    st.info("Bitte ein Modulpaar auswählen, um Messdaten anzuzeigen.")
    st.stop()

st.info(
    f"Ausgewählte Modulpaare: {', '.join(selected_module_pairs)}"
)

df = df[df["module_pair"].isin(selected_module_pairs)]

if df.empty:
    st.warning("Für die ausgewählten Modulpaare sind keine Daten vorhanden.")
    st.stop()



# ------------------------------------------------------------
# Zeitbereich filtern
# ------------------------------------------------------------

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
        "Manuell auswählen"
    ]
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
        max_value=max_datetime.date()
    )

    end_date = st.sidebar.date_input(
        "Enddatum",
        value=max_datetime.date(),
        min_value=min_datetime.date(),
        max_value=max_datetime.date()
    )

    st.sidebar.caption(
        f"Verfügbare Zeitspanne: "
        f"{min_datetime.strftime('%d.%m.%Y %H:%M:%S')} bis "
        f"{max_datetime.strftime('%d.%m.%Y %H:%M:%S')}"
    )

    start_time_text = st.sidebar.text_input(
        "Startzeit (HH:MM oder HH:MM:SS)",
        value=min_datetime.strftime("%H:%M:%S")
    )

    end_time_text = st.sidebar.text_input(
        "Endzeit (HH:MM oder HH:MM:SS)",
        value=max_datetime.strftime("%H:%M:%S")
    )

    try:
        start_datetime = pd.to_datetime(
            f"{start_date} {start_time_text}"
        )

        end_datetime = pd.to_datetime(
            f"{end_date} {end_time_text}"
        )

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
        (df["datetime"] >= start_datetime) &
        (df["datetime"] <= end_datetime)
    ]

# ------------------------------------------------------------
# Kennzahlen
# ------------------------------------------------------------

if df_filtered.empty:
    st.warning("Für den ausgewählten Zeitraum sind keine Daten vorhanden.")
    st.stop()

first = df_filtered.iloc[0]
latest = df_filtered.iloc[-1]

# Erste Zeile: Messzeitraum
time_col1, time_col2 = st.columns(2)

time_col1.metric(
    "Erster Messzeitpunkt",
    first["datetime"].strftime("%d.%m.%Y %H:%M:%S")
)

time_col2.metric(
    "Letzter Messzeitpunkt",
    latest["datetime"].strftime("%d.%m.%Y %H:%M:%S")
)

# Zweite Zeile: aktuelle Messwerte
col1, col2, col3 = st.columns(3)

col1.metric("Aktuelle Leistung", f"{latest['mpp_power_w']:.1f} W")
col2.metric("Aktuelle Spannung", f"{latest['mpp_voltage_v']:.2f} V")
col3.metric("Aktueller Strom", f"{latest['mpp_current_a']:.2f} A")



# ------------------------------------------------------------
# Diagramm: Leistung über Zeit
# ------------------------------------------------------------

st.subheader("MPP-Leistung über die Zeit")

fig_power = px.line(
    df_filtered,
    x="datetime",
    y="mpp_power_w",
    color="module_pair",
    line_dash="mode",
    title="PV-Leistung über die Zeit nach Modulpaar",
    labels={
        "datetime": "Zeit",
        "mpp_power_w": "MPP-Leistung [W]",
        "module_pair": "Modulpaar",
        "mode": "Messmodus"
    }
)

st.plotly_chart(fig_power, use_container_width=True)


# ------------------------------------------------------------
# Spannung und Strom
# ------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("MPP-Spannung")
    fig_voltage = px.line(
        df_filtered,
        x="datetime",
        y="mpp_voltage_v",
        color="module_pair",
        line_dash="mode",
        labels={
            "datetime": "Zeit",
            "mpp_voltage_v": "MPP-Spannung [V]",
            "module_pair": "Modulpaar",
            "mode": "Messmodus"
        }
    )
    st.plotly_chart(fig_voltage, use_container_width=True)

with col_right:
    st.subheader("MPP-Strom")
    fig_current = px.line(
        df_filtered,
        x="datetime",
        y="mpp_current_a",
        color="module_pair",
        line_dash="mode",
        labels={
            "datetime": "Zeit",
            "mpp_current_a": "MPP-Strom [A]",
            "module_pair": "Modulpaar",
            "mode": "Messmodus"
        }
    )
    st.plotly_chart(fig_current, use_container_width=True)


# ------------------------------------------------------------
# Tabelle und Download
# ------------------------------------------------------------

st.subheader("Messdatentabelle")

st.dataframe(df_filtered, use_container_width=True)

csv = df_filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Messdaten als CSV herunterladen",
    data=csv,
    file_name="pv_messdaten_export.csv",
    mime="text/csv"
)