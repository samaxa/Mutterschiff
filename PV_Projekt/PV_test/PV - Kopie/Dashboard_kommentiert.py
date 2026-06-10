# Dashboard_kommentiert.py
# ------------------------------------------------------------
# Start in der Konsole / im Terminal:
# streamlit run Dashboard_kommentiert.py
#
# Zweck des Skripts:
# Dieses Streamlit-Dashboard liest PV-Messdateien aus einem synchronisierten
# Sciebo-Ordner ein, filtert die Daten nach Modultyp, Messlauf, Modulpaar
# und Zeitbereich und stellt MPP-Leistung, MPP-Spannung und MPP-Strom dar.
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
# Wichtig: Dieser Pfad ist nur der Default-Wert. Im Dashboard kann er in
# der Sidebar später noch manuell geändert werden.
MESS_ROOT = Path(
    r"C:\Users\sarah\OneDrive - TH Köln\Desktop\4.Semester\PV\Messdaten_PV_Sciebo\Referenzdatensatz"
)


# Manuelle Zuordnung der Modulpaare zu ihrer Ausrichtung.
# Diese Information kommt nicht zuverlässig aus der Messdatei selbst,
# daher wird sie hier im Code ergänzt.
ORIENTATION_MAPPING = {
    "Modul-1_6": "Modul 1: Süd, Modul 6: Ost/West",
    "Modul-3_4": "Modul 3: Süd, Modul 4: Ost/West",
    "Modul-2_5": "Modul 2: Süd, Modul 5: Ost/West",
}


# ============================================================
# 2) Hilfsfunktionen zum Einlesen der Messdateien
# ============================================================


def read_file_metadata(file_path: Path) -> dict:
    """
    Liest Metadaten aus dem Kopfbereich einer PV-Messdatei.

    Gesucht werden aktuell:
    - der Modultyp aus der Zeile, die mit "Name" beginnt
    - das Modulpaar aus der Zeile, die mit "Modul Kennung" beginnt

    Die Funktion liest nur den Header-Bereich der Datei. Sobald die Zeile
    "Time" erreicht wird, wird abgebrochen, weil danach die Messdaten beginnen.

    Rückgabe:
        dict mit den Schlüsseln:
        - module_type_from_file
        - module_pair
    """

    # Default-Werte, falls die gesuchten Informationen in der Datei fehlen.
    metadata = {
        "module_type_from_file": "unbekannt",
        "module_pair": "unbekannt",
    }

    # errors="ignore" verhindert, dass das Programm bei einzelnen fehlerhaften
    # Sonderzeichen in der Messdatei abstürzt.
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line = line.strip()

            # Beispielhafte Header-Zeile:
            # Name    <Modultyp>
            if line.startswith("Name"):
                parts = re.split(r"\t+", line)
                if len(parts) >= 2:
                    metadata["module_type_from_file"] = parts[1].strip()

            # Beispielhafte Header-Zeile:
            # Modul Kennung    Modul-1_6
            elif line.startswith("Modul Kennung"):
                parts = re.split(r"\t+", line)
                if len(parts) >= 2:
                    metadata["module_pair"] = parts[1].strip()

            # Ab hier beginnen die eigentlichen Messwerte.
            # Deshalb muss der Header nicht weiter durchsucht werden.
            elif line.startswith("Time"):
                break

    return metadata



def read_pv_file(file_path: Path) -> pd.DataFrame:
    """
    Liest eine einzelne PV-Cont-Datei ein und gibt die Messwerte als DataFrame zurück.

    Ausgewertet werden nur Zeilen, die mit einem Datum im Format YYYY-MM-DD beginnen.
    Erwartete Spaltenstruktur in der Messzeile:

        Date Time Mode MPP_Volt MPP_Curr MPP_Power ...

    Rückgabe:
        DataFrame mit u. a. folgenden Spalten:
        - datetime
        - date
        - time
        - mode
        - mpp_voltage_v
        - mpp_current_a
        - mpp_power_w
    """

    rows = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line = line.strip()

            # Nur echte Messzeilen auswerten.
            # Header-Zeilen, Leerzeilen und sonstige Textzeilen werden ignoriert.
            if not re.match(r"^\d{4}-\d{2}-\d{2}", line):
                continue

            # Trennt die Zeile an einem oder mehreren Leerzeichen.
            parts = re.split(r"\s+", line)

            # Mindestens diese sechs Elemente werden gebraucht:
            # parts[0] = Datum
            # parts[1] = Uhrzeit
            # parts[2] = Messmodus
            # parts[3] = MPP-Spannung
            # parts[4] = MPP-Strom
            # parts[5] = MPP-Leistung
            if len(parts) < 6:
                continue

            try:
                rows.append(
                    {
                        # Datum und Uhrzeit werden zu einem echten Zeitstempel kombiniert.
                        # Das ist wichtig für Sortierung, Filterung und Diagramme.
                        "datetime": pd.to_datetime(parts[0] + " " + parts[1]),
                        "date": parts[0],
                        "time": parts[1],
                        "mode": parts[2],
                        "mpp_voltage_v": float(parts[3]),
                        "mpp_current_a": float(parts[4]),
                        "mpp_power_w": float(parts[5]),
                    }
                )
            except ValueError:
                # Falls eine Messzeile nicht sauber in Zahlen umgewandelt werden kann,
                # wird nur diese Zeile übersprungen. Das Dashboard läuft weiter.
                continue

    df = pd.DataFrame(rows)

    # Für Zeitreihen ist eine chronologische Sortierung wichtig.
    if not df.empty:
        df = df.sort_values("datetime")

    return df



def read_multiple_pv_files(file_paths: list[Path]) -> pd.DataFrame:
    """
    Liest mehrere PV-Cont-Dateien ein und führt sie zu einem DataFrame zusammen.

    Zusätzlich zu den Messwerten werden pro Datei Metadaten ergänzt:
    - Modultyp aus der Datei
    - Modulpaar
    - Dateiname
    - vollständiger Dateipfad
    - Zeitpunkt der letzten Dateiänderung

    Rückgabe:
        Ein zusammengeführter DataFrame mit allen gültigen Messdaten.
        Falls keine Daten gelesen werden können, wird ein leerer DataFrame zurückgegeben.
    """

    all_dfs = []

    for file_path in file_paths:
        df = read_pv_file(file_path)

        # Leere oder nicht lesbare Dateien werden ignoriert.
        if df.empty:
            continue

        metadata = read_file_metadata(file_path)

        # Metadaten werden jeder Messzeile dieser Datei als neue Spalten hinzugefügt.
        df["module_type_from_file"] = metadata["module_type_from_file"]
        df["module_pair"] = metadata["module_pair"]
        df["source_file"] = file_path.name
        df["source_path"] = str(file_path)
        df["last_modified"] = pd.to_datetime(file_path.stat().st_mtime, unit="s")

        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    # Alle einzelnen Tabellen werden untereinander zusammengefügt.
    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values("datetime")

    return df_all


# ============================================================
# 3) Streamlit-Seite und Sidebar aufbauen
# ============================================================

st.set_page_config(
    page_title="PV-Messdaten Dashboard",
    layout="wide",
)

st.title("PV-Messdaten Dashboard")
st.caption("Anzeige der automatisch synchronisierten PV-Messdaten")

st.sidebar.header("Einstellungen")

# Pfad kann im Dashboard überschrieben werden, ohne den Code zu ändern.
file_path_input = st.sidebar.text_input(
    "Pfad zum Referenzdatensatz",
    value=str(MESS_ROOT),
)

# Automatische Aktualisierung: praktisch, wenn Sciebo im Hintergrund neue Daten synchronisiert.
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

# Manuelle Aktualisierung per Button.
if st.sidebar.button("Jetzt manuell aktualisieren"):
    st.rerun()

# Automatische Aktualisierung über einen HTML-Meta-Refresh.
if auto_refresh:
    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_seconds}'>",
        unsafe_allow_html=True,
    )


# ============================================================
# 4) Ordnerstruktur auswerten: Modultyp und Messlauf wählen
# ============================================================

root_path = Path(file_path_input)

# Sicherheitsprüfung: Der angegebene Hauptordner muss existieren.
if not root_path.exists():
    st.error(f"Ordner nicht gefunden: {root_path}")
    st.stop()

# Annahme zur Ordnerstruktur:
# Die direkten Unterordner im Referenzdatensatz entsprechen den Modultypen.
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

# Annahme zur Ordnerstruktur:
# Innerhalb eines Modultyps liegen einzelne Messlauf-Ordner.
# Sortierung nach Änderungsdatum: Der neueste Messlauf erscheint oben.
measurement_run_folders = sorted(
    [p for p in selected_module_type_folder.iterdir() if p.is_dir()],
    key=lambda p: p.stat().st_mtime,
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

# Gesucht werden alle Textdateien, deren Name "Cont" enthält.
# rglob sucht dabei auch in Unterordnern des Messlaufs.
cont_files = sorted(search_folder.rglob("*Cont*.txt"))

st.write(f"Ausgewählter Modultyp: {selected_module_type_name}")
st.write(f"Ausgewählter Messlauf: {selected_measurement_run_name}")
st.write(f"Gefundene Cont-Dateien: {len(cont_files)}")

if not cont_files:
    st.warning("Für diese Auswahl wurden keine Cont-Dateien gefunden.")
    st.stop()

# Alle gefundenen Cont-Dateien werden eingelesen und zu einer Tabelle zusammengeführt.
df = read_multiple_pv_files(cont_files)

if df.empty:
    st.warning("Die Dateien wurden gefunden, aber es konnten keine Messdaten erkannt werden.")
    st.stop()

# Zusätzliche Spalte mit verständlicher Beschreibung der Ausrichtung ergänzen.
df["orientation_info"] = df["module_pair"].map(ORIENTATION_MAPPING).fillna("unbekannt")


# ============================================================
# 6) Modulpaar auswählen und Daten darauf filtern
# ============================================================

module_pair_options = sorted(df["module_pair"].dropna().unique())

selected_module_pairs = st.sidebar.multiselect(
    "Modulpaar auswählen",
    module_pair_options,
    default=[],
)

st.info(
    "Hinweis: Mehrere Modulpaare können gemeinsam angezeigt werden. "
    "Die Messzeitpunkte können sich jedoch je nach Messlauf unterscheiden."
)

if not selected_module_pairs:
    st.info("Bitte ein Modulpaar auswählen, um Messdaten anzuzeigen.")
    st.stop()

st.info(f"Ausgewählte Modulpaare: {', '.join(selected_module_pairs)}")

# Ab hier bleiben nur noch Daten der ausgewählten Modulpaare übrig.
df = df[df["module_pair"].isin(selected_module_pairs)]

if df.empty:
    st.warning("Für die ausgewählten Modulpaare sind keine Daten vorhanden.")
    st.stop()


# ============================================================
# 7) Zeitbereich auswählen und Daten zeitlich filtern
# ============================================================

st.sidebar.subheader("Zeitbereich")

# Kleinster und größter vorhandener Messzeitpunkt nach der Modulpaar-Auswahl.
# Diese Werte begrenzen die sinnvolle manuelle Zeitwahl.
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

# Wichtig:
# "Letzte X Minuten/Stunden/Tage" bezieht sich hier auf den letzten Messpunkt
# in der Datei, nicht zwingend auf die aktuelle Uhrzeit des Computers.
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
    # Start am ersten Tag des Monats, in dem der letzte Messpunkt liegt.
    start_datetime = max_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    df_filtered = df[df["datetime"] >= start_datetime]

elif time_range_option == "Jahr der letzten Messung":
    # Start am 1. Januar des Jahres, in dem der letzte Messpunkt liegt.
    start_datetime = max_datetime.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    df_filtered = df[df["datetime"] >= start_datetime]

else:
    # Manuelle Auswahl: Datum per Kalender, Uhrzeit als Text.
    # Vorteil: Es sind auch genaue Zeiten wie 13:07:30 möglich,
    # nicht nur feste 15-Minuten-Schritte.
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
        # Datum und manuell eingetragene Uhrzeit werden zu einem Zeitstempel kombiniert.
        start_datetime = pd.to_datetime(f"{start_date} {start_time_text}")
        end_datetime = pd.to_datetime(f"{end_date} {end_time_text}")

    except ValueError:
        st.sidebar.error("Bitte die Zeit im Format HH:MM oder HH:MM:SS eingeben.")
        st.stop()

    # Plausibilitätsprüfungen für die manuelle Zeitwahl.
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

    # Der eigentliche Filter: Nur Messpunkte innerhalb des gewählten Zeitfensters bleiben übrig.
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

# Erster und letzter Messpunkt im aktuell gefilterten Zeitraum.
first = df_filtered.iloc[0]
latest = df_filtered.iloc[-1]

# Erste Zeile: Anfang und Ende des angezeigten Messzeitraums.
time_col1, time_col2 = st.columns(2)

time_col1.metric(
    "Erster Messzeitpunkt",
    first["datetime"].strftime("%d.%m.%Y %H:%M:%S"),
)

time_col2.metric(
    "Letzter Messzeitpunkt",
    latest["datetime"].strftime("%d.%m.%Y %H:%M:%S"),
)

# Zweite Zeile: letzte vorhandene Messwerte im gewählten Zeitraum.
# "Aktuell" bedeutet hier: letzter Messpunkt der gefilterten Daten.
col1, col2, col3 = st.columns(3)

col1.metric("Aktuelle Leistung", f"{latest['mpp_power_w']:.1f} W")
col2.metric("Aktuelle Spannung", f"{latest['mpp_voltage_v']:.2f} V")
col3.metric("Aktueller Strom", f"{latest['mpp_current_a']:.2f} A")


# ============================================================
# 9) Diagramme erstellen
# ============================================================

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
        "mode": "Messmodus",
    },
)

st.plotly_chart(fig_power, use_container_width=True)


# Spannung und Strom werden nebeneinander dargestellt.
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
            "mode": "Messmodus",
        },
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
            "mode": "Messmodus",
        },
    )
    st.plotly_chart(fig_current, use_container_width=True)


# ============================================================
# 10) Tabelle und CSV-Download
# ============================================================

st.subheader("Messdatentabelle")

# Interaktive Tabelle mit allen aktuell gefilterten Daten.
st.dataframe(df_filtered, use_container_width=True)

# Exportiert genau die Daten, die aktuell nach Modultyp, Messlauf,
# Modulpaar und Zeitbereich gefiltert sind.
csv = df_filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Messdaten als CSV herunterladen",
    data=csv,
    file_name="pv_messdaten_export.csv",
    mime="text/csv",
)
