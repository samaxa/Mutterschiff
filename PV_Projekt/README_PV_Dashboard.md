# PV-Messdaten Dashboard

Dieses Streamlit-Dashboard liest fortlaufend aktualisierte PV-Cont-Messdateien aus einem synchronisierten Sciebo-Ordner ein. Es ordnet die beiden elektrischen Messkanäle der Cont-Datei den realen PV-Modulen zu und zeigt aktuelle Messwerte sowie interaktive Diagramme an.

## Schnellstart

```powershell
pip install -r requirements.txt
streamlit run Dashboard_PV_Projekt_refactored.py
```

Falls die Datei anders heißt, muss der Dateiname im `streamlit run`-Befehl angepasst werden.

## Benötigte Python-Pakete

Die benötigten Pakete stehen in `requirements.txt`:

```text
streamlit
pandas
plotly
streamlit-autorefresh
```

`pathlib` und `re` gehören zur Python-Standardbibliothek und müssen nicht installiert werden.

## Erwartete Ordnerstruktur

Das Dashboard orientiert sich an einer Sciebo-Ordnerstruktur etwa dieser Form:

```text
Referenzdatensatz/
├── Modultyp_A/
│   ├── 2026-05-22/
│   │   ├── Cont--...--Modul-1_6--2026-05-22--13-25-36/
│   │   │   ├── Cont--...--Modul-1_6--2026-05-22--13-25-36.txt
│   │   │   ├── Scan--...txt
│   │   │   └── Scan--...txt
│   │   └── Cont--...--Modul-3_4--2026-05-22--19-03-05/
│   └── 2026-05-18/
└── Modultyp_B/
```

Es werden bewusst nur Dateien eingelesen, deren Name mit `Cont` beginnt. Scan-Dateien werden ignoriert.

## Kanal- und Modulzuordnung

Die Cont-Datei enthält zwei elektrische Messkanäle:

- Kanal 1: `Volt1 / Curr1 / Power1`
- Kanal 2: `Volt2 / Curr2 / Power2`

Die Modulkennung im Header legt fest, welches reale Modul zu welchem Kanal gehört:

| Modulkennung | Kanal 1 | Kanal 2 |
|---|---|---|
| Modul-1_6 | Modul 1 - Süd | Modul 6 - Ost/West |
| Modul-2_5 | Modul 2 - Süd | Modul 5 - Ost/West |
| Modul-3_4 | Modul 3 - Süd | Modul 4 - Ost/West |

Die Ausrichtung ist im Code über `MODULE_ORIENTATION` definiert.

## Wichtige Codebereiche

- `MESS_ROOT`: Standardpfad zum synchronisierten Sciebo-Referenzdatensatz.
- `MODULE_ORIENTATION`: Zuordnung der Modulnummern zur Ausrichtung.
- `RAW_EXPORT_COLUMNS`: Spalten, die in Rohdatenvorschau und CSV-Export angezeigt werden.
- `read_cont_file_raw()`: liest die Cont-Datei als breite Rohdatentabelle ein.
- `raw_to_module_long()`: wandelt Kanal 1 und Kanal 2 in eine modulweise Tabelle um.
- `filter_by_time_range()`: filtert die Daten nach dem in der Sidebar ausgewählten Zeitraum.
- `render_overview_container()`: zeigt Messzeitraum und KPI-Kacheln.
- `render_electrical_charts()`: zeigt Leistung, Spannung und Strom.
- `render_sensor_values()`: zeigt optional Temperatur und Light Intensity.
- `render_raw_data_export()`: zeigt Rohdatenvorschau und CSV-Download.

## Warum gibt es Rohdaten und modulweise Daten?

Die Cont-Datei ist breit aufgebaut: Kanal 1 und Kanal 2 stehen nebeneinander in derselben Zeile. Für modulweise Diagramme und KPI-Kacheln ist das unpraktisch. Deshalb erzeugt das Dashboard intern zusätzlich eine lange Tabelle, in der jede Zeile einem konkreten Modul/Kanal entspricht.

- `df_raw`: breite Rohdaten, nah an der Cont-Datei. Wird für Rohdatenexport und Sensorwerte genutzt.
- `df_long` bzw. `df`: modulweise Tabelle. Wird für Modulauswahl, KPI-Kacheln und elektrische Diagramme genutzt.

## Automatische Aktualisierung

Die automatische Aktualisierung verwendet `streamlit-autorefresh`. Dadurch wird die ausgewählte Cont-Datei regelmäßig neu eingelesen, ohne dass der Browser hart neu geladen wird. Die Auswahl sollte erhalten bleiben.

Wichtig: Kein HTML-`meta refresh` verwenden, da dadurch die gesamte Seite neu geladen wird und Auswahlen verloren gehen können.

## Häufige Anpassungen

| Anpassung | Stelle im Code |
|---|---|
| Standardpfad ändern | `MESS_ROOT` |
| Modul-Ausrichtung ändern | `MODULE_ORIENTATION` |
| Exportspalten ändern | `RAW_EXPORT_COLUMNS` |
| Hilfsspalten aus Export ausblenden | `RAW_HELPER_COLUMNS_TO_HIDE` |
| Zeitbereichsoptionen ändern | `TIME_RANGE_OFFSETS` / `filter_by_time_range()` |
| Diagramme anpassen | `render_electrical_charts()` |
| Sensorwerte anpassen | `render_sensor_values()` |

## Troubleshooting

| Problem | Mögliche Ursache | Lösung |
|---|---|---|
| Keine Cont-Dateien gefunden | Falscher Ordner oder Dateiname beginnt nicht mit `Cont` | Ordnerstruktur und Dateinamen prüfen |
| Encoding-Fehler | Datei ist nicht UTF-8 | `FILE_ENCODING = "cp1252"` beibehalten oder Encoding prüfen |
| Auswahlen gehen bei Auto-Refresh verloren | Harter Browser-Refresh | `streamlit-autorefresh` verwenden, kein `meta refresh` |
| Temperatur zeigt 0 °C-Linien | Leere Track-Felder wurden zu 0 gesetzt | Für Temperaturplot 0-Werte ausblenden |
| Diagramm trennt Module nicht | Rohdaten statt modulweise Daten verwendet | Elektrische Diagramme mit `df_filtered` aus der modulweisen Tabelle erstellen |

## Übergabe-Checkliste

- [ ] `Dashboard_PV_Projekt_refactored.py` liegt im Projektordner.
- [ ] `requirements.txt` liegt im Projektordner.
- [ ] Sciebo-Ordner ist lokal synchronisiert.
- [ ] `MESS_ROOT` stimmt oder wird in der Sidebar angepasst.
- [ ] Test mit einem bekannten Cont-Messordner wurde durchgeführt.
- [ ] Rohdaten-CSV wurde testweise exportiert.
- [ ] KPI-Werte und letzter Messzeitpunkt wirken plausibel.
