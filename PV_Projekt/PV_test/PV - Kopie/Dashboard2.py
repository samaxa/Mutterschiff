# Dashboard.py
# zum starten streamlit run Dashboard.py in Konsole eingeben
from pathlib import Path
import re
import pandas as pd
import streamlit as st
import plotly.express as px


# ------------------------------------------------------------
# Pfad zur synchronisierten Messdatei
# ------------------------------------------------------------

MESSDATEI = Path(
    r"C:\PythonProjekte\PV_Projekt\PV_test\PV - Kopie\pv_dummy_messdaten.txt"
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
    "Pfad zur Messdatei",
    value=str(MESSDATEI)
)

auto_refresh = st.sidebar.checkbox(
    "Automatisch aktualisieren",
    value=False
)

if auto_refresh:
    refresh_seconds = st.sidebar.number_input(
        "Aktualisierung alle X Sekunden",
        min_value=10,
        max_value=600,
        value=60,
        step=10
    )

    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_seconds}'>",
        unsafe_allow_html=True
    )

if st.sidebar.button("Jetzt aktualisieren"):
    st.rerun()

time_range = st.sidebar.selectbox(
    "Zeitspanne für Diagramme",
    [
        "Alle Daten",
        "Letzte 24 Stunden",
        "Letzte 7 Tage",
        "Letzte 30 Tage",
        "Letzte 3 Monate",
        "Letzte 6 Monate",
        "Letztes Jahr",
        "Manuell auswählen"
    ]
)


# ------------------------------------------------------------
# Daten laden
# ------------------------------------------------------------

file_path = Path(file_path_input)

if not file_path.exists():
    st.error(f"Messdatei nicht gefunden: {file_path}")
    st.stop()

try:
    df = read_pv_file(file_path)

except Exception as e:
    st.warning(f"Datei konnte gerade nicht gelesen werden: {e}")
    st.stop()


if df.empty:
    st.warning("Die Datei wurde gefunden, aber es konnten keine Messdaten erkannt werden.")
    st.stop()

# ------------------------------------------------------------
# Daten für Diagramme nach Zeitspanne filtern
# ------------------------------------------------------------

df_plot = df.copy()

if time_range != "Alle Daten":
    latest_datetime = df["datetime"].max()

    if time_range == "Letzte 24 Stunden":
        start_datetime = latest_datetime - pd.Timedelta(hours=24)
        df_plot = df[df["datetime"] >= start_datetime]

    elif time_range == "Letzte 7 Tage":
        start_datetime = latest_datetime - pd.Timedelta(days=7)
        df_plot = df[df["datetime"] >= start_datetime]

    elif time_range == "Letzte 30 Tage":
        start_datetime = latest_datetime - pd.Timedelta(days=30)
        df_plot = df[df["datetime"] >= start_datetime]

    elif time_range == "Letzte 3 Monate":
        start_datetime = latest_datetime - pd.DateOffset(months=3)
        df_plot = df[df["datetime"] >= start_datetime]

    elif time_range == "Letzte 6 Monate":
        start_datetime = latest_datetime - pd.DateOffset(months=6)
        df_plot = df[df["datetime"] >= start_datetime]

    elif time_range == "Letztes Jahr":
        start_datetime = latest_datetime - pd.DateOffset(years=1)
        df_plot = df[df["datetime"] >= start_datetime]

    elif time_range == "Manuell auswählen":
        min_datetime = df["datetime"].min()
        max_datetime = df["datetime"].max()
        start_date = st.sidebar.date_input(

            "Startdatum",
            value=min_datetime.date(),
            min_value=min_datetime.date(),
            max_value=max_datetime.date()

        )

        start_time_text = st.sidebar.text_input(
            "Startzeit",
            value=min_datetime.strftime("%H:%M:%S"),
            help="Format: HH:MM oder HH:MM:SS"
        )

        end_date = st.sidebar.date_input(
            "Enddatum",
            value=max_datetime.date(),
            min_value=min_datetime.date(),
            max_value=max_datetime.date()
        )

        end_time_text = st.sidebar.text_input(
            "Endzeit",
            value=max_datetime.strftime("%H:%M:%S"),
            help="Format: HH:MM oder HH:MM:SS"
        )

        try:
            start_datetime = pd.to_datetime(f"{start_date} {start_time_text}")
            end_datetime = pd.to_datetime(f"{end_date} {end_time_text}")
        except ValueError:
            st.sidebar.error("Bitte gib die Uhrzeit im Format HH:MM oder HH:MM:SS ein.")
            st.stop()

        if start_datetime > end_datetime:
            st.sidebar.error("Der Startzeitpunkt darf nicht nach dem Endzeitpunkt liegen.")
            st.stop()

        df_plot = df[
            (df["datetime"] >= start_datetime) &
            (df["datetime"] <= end_datetime)
            ]

if df_plot.empty:
    st.warning("Für die gewählte Zeitspanne sind keine Messdaten vorhanden.")

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
    df_plot,
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
        df_plot,
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
        df_plot,
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