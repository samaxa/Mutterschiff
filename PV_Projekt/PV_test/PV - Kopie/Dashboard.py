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


refresh_seconds = st.sidebar.number_input(
    "Aktualisierung alle X Sekunden",
    min_value=10,
    max_value=600,
    value=60,
    step=10
)

# einfache automatische Aktualisierung
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
    module_type_names
)

selected_module_type_folder = root_path / selected_module_type_name

# Messläufe innerhalb des ausgewählten Modultyps
measurement_run_folders = sorted([
    p for p in selected_module_type_folder.iterdir()
    if p.is_dir()
])

measurement_run_names = ["Alle Messläufe"] + [folder.name for folder in measurement_run_folders]

selected_measurement_run_name = st.sidebar.selectbox(
    "Messlauf auswählen",
    measurement_run_names
)

if selected_measurement_run_name == "Alle Messläufe":
    search_folder = selected_module_type_folder
else:
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
# ------------------------------------------------------------
# Kennzahlen
# ------------------------------------------------------------

latest = df.iloc[-1]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Aktuelle Leistung", f"{latest['mpp_power_w']:.1f} W")
col2.metric("Aktuelle Spannung", f"{latest['mpp_voltage_v']:.2f} V")
col3.metric("Aktueller Strom", f"{latest['mpp_current_a']:.2f} A")
col4.metric(
    "Letzter Messzeitpunkt",
    latest["datetime"].strftime("%d.%m.%Y %H:%M:%S")
)


# ------------------------------------------------------------
# Diagramm: Leistung über Zeit
# ------------------------------------------------------------

st.subheader("MPP-Leistung über die Zeit")

fig_power = px.line(
    df,
    x="datetime",
    y="mpp_power_w",
    color="mode",
    title="PV-Leistung über die Zeit",
    labels={
        "datetime": "Zeit",
        "mpp_power_w": "MPP-Leistung [W]",
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
        df,
        x="datetime",
        y="mpp_voltage_v",
        color="mode",
        labels={
            "datetime": "Zeit",
            "mpp_voltage_v": "MPP-Spannung [V]",
            "mode": "Messmodus"
        }
    )
    st.plotly_chart(fig_voltage, use_container_width=True)

with col_right:
    st.subheader("MPP-Strom")
    fig_current = px.line(
        df,
        x="datetime",
        y="mpp_current_a",
        color="mode",
        labels={
            "datetime": "Zeit",
            "mpp_current_a": "MPP-Strom [A]",
            "mode": "Messmodus"
        }
    )
    st.plotly_chart(fig_current, use_container_width=True)


# ------------------------------------------------------------
# Tabelle und Download
# ------------------------------------------------------------

st.subheader("Messdatentabelle")

st.dataframe(df, use_container_width=True)

csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Messdaten als CSV herunterladen",
    data=csv,
    file_name="pv_messdaten_export.csv",
    mime="text/csv"
)