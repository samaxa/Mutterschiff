# 1. Das Skript überprüft alle 5 Minuten (`CHECK_INTERVAL`),
# ob sich die Zeit des letzten Änderungszeitpunktes der Datei geändert hat.
# 2. Wenn ja, kopiert es:
#     - Die aktuelle Datei an den Zielort.
#     - Eine archivierte Kopie mit Zeitstempel in den Archivordner.
# 3. Alle Vorgänge (sowie mögliche Fehler) werden ins Log geschrieben."

# -------------------------
# Importe
# -------------------------
from pathlib import Path            # Ermöglicht die Verwendung des `Path`-Objekts für die Arbeit mit Dateipfaden
import shutil                       # Das Modul bietet Funktionen zum Kopieren und Verwalten von Dateien, z. B. `shutil.copy2()`
import time                         # Wird für Zeitfunktionen wie `time.sleep()` verwendet, um das Skript für festgelegte Zeitintervalle pausieren zu lassen
from datetime import datetime       # Ermöglicht die Verwendung von Datums- und Zeitstempeln, z. B. zur Erstellung von Zeitstempeln beim Archivieren einer Datei.
import logging                      # Logging-Modul, das Nachrichten in Konsolen oder Log-Dateien schreibt, um Ereignisse zu verfolgen.

# -------------------------
# Logging konfigurieren
# -------------------------
# Konfigurieren des Logging-Moduls für die Aussgabe von Nachrichten (Logs)
# in der Konsole und in einer Log-Datei "dateiueberwachung.log"
# statt infos per print zu bekommen
# 1. Beispiel einer generierten Log-Nachricht: "2026-05-11 15:30:12 - INFO - Aktuelle Datei kopiert: 'C:\Users\USERNAME\Sciebo\PV-Projekt\messdaten_aktuell.csv'"

logging.basicConfig(
    level=logging.INFO,                                     # Das setzt die "Log-Stufe" auf Niveau INFO. Alle wichtigen Ereignisse (z. B. Start/Erfolg einer Aktion) und Fehlermeldungen werden aufgezeichnet
    format="%(asctime)s - %(levelname)s - %(message)s",     # Andere mögliche Lvl sind DEBUG, WARNING, ERROR, CRITICAL
    handlers=[                                              # format legt fest wie die Log-Nachrichten aussehen sollen
        logging.FileHandler("dateiueberwachung.log"),       # %(asctime)s: Zeitstempel, %(levelname)s: Log-Stufe, %(message)s: Log-Nachricht
        logging.StreamHandler()                             # handlers legt fest wohin die Log-Nachrichten geschrieben werden - hier in "dateiueberwachung.log"
    ]                                                       # logging.StreamHandler() zeigt die Logs auch direkt in der Konsole an

)



# -------------------------
# Pfade definieren
# -------------------------
source_file = Path(r"C:\PV_Messdaten\messdaten.csv")                                    # hier liegt die original Datei
target_current = Path(r"C:\Users\USERNAME\Sciebo\PV-Projekt\messdaten_aktuell.csv")     # Das ist die „aktuelle Version“
archive_folder = Path(r"C:\Users\USERNAME\Sciebo\PV-Projekt\Archiv")                    # hier landen historische Kopien

# Sicherstellen, dass der Archivordner existiert
archive_folder.mkdir(parents=True, exist_ok=True)       # Befehl der Ordner erstellt sollte keiner exisitieren
                                                        # archive_folder ist ein Pfad der mit Path definiert wurde

# Zeitintervall in Sekunden (z.B. 300 = 5 Minuten)
CHECK_INTERVAL = 300                                    # Eine Variable die steuert, wie lange das Skript zwischen den Überprüfungen wartet
                                                        # 300s = 5 min
last_modified = None                                    # Eine Variable um Daten zwischenzuspeichern
                                                        # last_modified speichert das Datum und die Uhrzeit, wann eine überwachte Datei zuletzt geändert wurde
                                                        # Ist am Start auf None





# -----------------------------------------------------------------
# Hauptschleife zur Überwachung und Synchronisation der Messdatei
# -----------------------------------------------------------------

while True:                                                                     # Der Code läuft in einer endlosen Schleife (while True)

    try:
        # Überprüfen, ob die Quelle existiert
        if source_file.exists():
            current_modified = source_file.stat().st_mtime

            # Wenn sich die Datei geändert hat, kopieren
            if current_modified != last_modified:
                # Aktuelle Datei überschreiben
                shutil.copy2(source_file, target_current)
                logging.info(f"Aktuelle Datei kopiert: '{target_current}'")

                # Archivkopie mit Zeitstempel anlegen
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                archive_file = archive_folder / f"messdaten_{timestamp}.csv"
                shutil.copy2(source_file, archive_file)
                logging.info(f"Archivkopie erstellt: '{archive_file}'")

                last_modified = current_modified
        else:
            logging.warning(f"Quellendatei nicht gefunden: '{source_file}'")

    except Exception as e:
        # Fehler protokollieren
        logging.error(f"Fehler beim Überwachen oder Kopieren der Datei: {e}")

    # Warten bis zur nächsten Überprüfung
    time.sleep(CHECK_INTERVAL)
