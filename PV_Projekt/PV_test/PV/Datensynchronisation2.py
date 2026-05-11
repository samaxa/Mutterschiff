# =============================================================
# PV-Messdaten Synchronisationsskript
# =============================================================
#
# Zweck:
# Dieses Skript überwacht eine PV-Messdatei kontinuierlich.
#
# Wenn sich die Datei ändert:
# 1. wird die aktuelle Version in ein Projektlaufwerk kopiert
# 2. wird zusätzlich eine Archivkopie mit Zeitstempel gespeichert
# 3. werden alle Ereignisse ins Log geschrieben
#
# Typischer Datenfluss:
#
# Messgerät
#     ↓
# lokale Messdatei
#     ↓
# Synchronisationsskript
#     ↓
# Sciebo / Netzlaufwerk / OneDrive
#     ↓
# Streamlit Dashboard / Power BI
#
# =============================================================
# -------------------------------------------------------------
# Importe
# -------------------------------------------------------------

from pathlib import Path
import shutil
import time
from datetime import datetime
import logging


# -------------------------------------------------------------
# Logging konfigurieren
# -------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,

    format="%(asctime)s - %(levelname)s - %(message)s",

    handlers=[
        logging.FileHandler("dateiueberwachung.log"),
        logging.StreamHandler()
    ]
)


# -------------------------------------------------------------
# Pfade definieren
# -------------------------------------------------------------
#
# source_file:
# Originaldatei vom Messgerät
#
# target_current:
# aktuelle synchronisierte Datei
#
# archive_folder:
# Ordner für historische Sicherungskopien
#
# -------------------------------------------------------------

source_file = Path(
    r"C:\PV_Messdaten\messdaten.csv"
)

target_current = Path(
    r"C:\Users\USERNAME\Sciebo\PV-Projekt\messdaten_aktuell.csv"
)

archive_folder = Path(
    r"C:\Users\USERNAME\Sciebo\PV-Projekt\Archiv"
)


# -------------------------------------------------------------
# Archivordner erstellen falls nicht vorhanden
# -------------------------------------------------------------

archive_folder.mkdir(
    parents=True,
    exist_ok=True
)


# -------------------------------------------------------------
# Überprüfungsintervall
# -------------------------------------------------------------
#
# 300 Sekunden = 5 Minuten
#
# -------------------------------------------------------------

CHECK_INTERVAL = 300


# -------------------------------------------------------------
# Variable zur Speicherung der letzten Änderungszeit
# -------------------------------------------------------------

last_modified = None


# =============================================================
# Hauptschleife zur Überwachung und Synchronisation
# =============================================================

while True:

    try:

        # -----------------------------------------------------
        # Prüfen ob die Quelldatei existiert
        # -----------------------------------------------------

        if source_file.exists():

            # letzte Änderungszeit der Datei auslesen
            current_modified = source_file.stat().st_mtime


            # -------------------------------------------------
            # Prüfen ob sich die Datei geändert hat
            # -------------------------------------------------

            if current_modified != last_modified:

                logging.info("Dateiänderung erkannt")


                # ---------------------------------------------
                # aktuelle Datei synchronisieren
                # ---------------------------------------------

                shutil.copy2(
                    source_file,
                    target_current
                )

                logging.info(
                    f"Aktuelle Datei kopiert: "
                    f"'{target_current}'"
                )


                # ---------------------------------------------
                # Zeitstempel erzeugen
                # ---------------------------------------------

                timestamp = datetime.now().strftime(
                    "%Y-%m-%d_%H-%M-%S"
                )


                # ---------------------------------------------
                # Archiv-Dateiname erzeugen
                # ---------------------------------------------

                archive_file = (
                    archive_folder /
                    f"messdaten_{timestamp}.csv"
                )


                # ---------------------------------------------
                # Archivkopie erstellen
                # ---------------------------------------------

                shutil.copy2(
                    source_file,
                    archive_file
                )

                logging.info(
                    f"Archivkopie erstellt: "
                    f"'{archive_file}'"
                )


                # ---------------------------------------------
                # letzte bekannte Änderungszeit aktualisieren
                # ---------------------------------------------

                last_modified = current_modified


        # -----------------------------------------------------
        # Datei existiert nicht
        # -----------------------------------------------------

        else:

            logging.warning(
                f"Quellendatei nicht gefunden: "
                f"'{source_file}'"
            )


    # ---------------------------------------------------------
    # Fehlerbehandlung
    # ---------------------------------------------------------

    except Exception as e:

        logging.error(
            f"Fehler beim Überwachen oder Kopieren "
            f"der Datei: {e}"
        )


    # ---------------------------------------------------------
    # Warten bis zur nächsten Überprüfung
    # ---------------------------------------------------------

    time.sleep(CHECK_INTERVAL)