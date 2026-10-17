# Kaverne – zwischen Einspeicherung und Ausspeicherung

Stand 15.10.2026 (nach der Besprechung mit Katrin Vosbeck). Gerechnet wird nur noch die tiefe Referenzkaverne (LCCS 1200 m, 650.000 m³) – die flache Kaverne entfällt (DBI verwirft sie selbst, Q-030 S. 17). Wie bei der Einspeicherung gibt es einen Ordner für reines CO₂ und einen für das Worst-Case-Gemisch; beide rechnen mit denselben Bausteinen.

```
Kaverne/
├── README.md
├── Grundlagen/          Annahmen + Rechenbausteine (eine Stelle für alles), Rechenschritte, Excel-Erzeugung
│   ├── kaverne_bausteine.py      Annahmen mit Fundstellen (Kopf der Datei), Stoffe, Gassäule, Förderstrang, Kavernenbilanz
│   ├── kaverne_schritte.py       die Schritte 01–04 als Funktionen (gleich für beide Stoffe)
│   └── excel_kaverne_erzeugen.py baut die beiden Excel-Mappen aus den JSON-Dateien
├── Reines_CO2/          01–04 für reines CO₂, Abbildungen, JSON, CO2_Kaverne_Rechenuebersicht.xlsx
├── Begleitstoffe_CO2/   01–04 für das Gemisch, 05 Vergleich rein/Gemisch, CO2_Kaverne_Rechenuebersicht_Gemisch.xlsx
└── Ausspeichergas/      ausspeichergas.py (Stoffdatenblatt Ausspeicherpfad), 06 Zusammensetzung (Min-/Max-Fall)
```

## Schritte

| Schritt | Skript (je Stoffordner) | Frage | Ergebnis |
|---|---|---|---|
| 01 | `01_stillstand_und_zieldruck.py` | Kopfdruck im Stillstand (voll, Grenzfall, leer) und im Betrieb (strömende Säule beim Einspeisen S1/S2, 50.000/100.000 Nm³/h) | `kaverne_stillstand.json`, `abb_K01_*.png` |
| 02 | `02_arbeitsgas_teufenfenster.py` | Inhalt, Kissengas, Arbeitsgas (isotherm/isentrop), Kontrolle gegen DBI, Teufenfenster | `arbeitsgas.json`, `abb_K02_arbeitsgas.png` |
| 03 | `03_kavernenzyklus.py` | Rate aus 10 bar/d, Kavernenbilanz über einen Zyklus für S1/S2 × 2 Raten × (Stillstand 21,67 d / kontinuierlich), Grenzrate, Nachrechnung Q-028 | `kavernenzyklus.json`, `abb_K03_*.png` |
| 04 | `04_bohrlochkopf.py` | Kopfdruckfenster beim Ein- und Ausspeichern, Pumpe oder Drossel, Phase im Strang, Reibung | `bohrlochkopf.json`, `abb_K04_*.png` |
| 05 | `Begleitstoffe_CO2/05_vergleich_rein_gemisch.py` | Welcher Stoff ist je Auslegungsgröße ungünstiger? | `vergleich_rein_gemisch.json`, `abb_K05_rein_vs_gemisch.png` |
| 06 | `Ausspeichergas/06_zusammensetzung_nach_kaverne.py` | Zusammensetzung des Ausspeichergases, Min- und Max-Fall (Q-089), Rückgabegrenzen OGE | `zusammensetzung_nach_kaverne.json`, `abb_K06_*.png` |

Reihenfolge: `Reines_CO2/01–04` → `Begleitstoffe_CO2/01–04` → `Begleitstoffe_CO2/05` → `Ausspeichergas/06` → `Grundlagen/excel_kaverne_erzeugen.py`.

## Die wichtigsten Festlegungen (Fundstellen im Kopf von `kaverne_bausteine.py`)

- **Förderstrang adiabat** (schnelle Förderung, kein Wärmeaustausch mit dem Gebirge): h + g·z = konst., Reibung Darcy f = 0,016 (Q-003 Kap. 6.2), 8 5/8"-Strang (Q-030 Tab. 1). Homogen und einphasig – ein zweiphasiger Abschnitt wird nur angezeigt (Grenze nach Q-028 S. 11).
- **Einspeisung gekoppelt an die Einspeicherung:** Kopftemperatur = Pumpenaustritt S1 bzw. S2; der Zieldruck der Pumpe kommt aus der strömenden Säule (`zieldruck_einspeisen`). Diese Funktion nutzt auch die Einspeicherung (`Einspeicherung/Begleitstoffe_CO2/Prozesskette/03_S1`, `03_S2`).
- **Stillstand 21,67 d** zwischen den Phasen aus Q-028 S. 10 (Betriebsszenario der dortigen Simulation, an der auch der Wärmeübergang UA kalibriert ist); Vergleich kontinuierlich (0 d).
- **Regelung über den Kopfdruck:** Schritt 04 weist den Kopfdruck über den ganzen Zyklus aus (höchster Wert = Pumpe, kleinster = Rückverdichtung bzw. Drossel).
- **Rein und Gemisch:** beide gerechnet; je Auslegungsgröße zählt der ungünstigere Fall (Schritt 05).

## Excel

`Grundlagen/excel_kaverne_erzeugen.py` erzeugt `Reines_CO2/CO2_Kaverne_Rechenuebersicht.xlsx` und `Begleitstoffe_CO2/CO2_Kaverne_Rechenuebersicht_Gemisch.xlsx` (Übersicht mit Annahmen, Quelle und Status, Blätter 01–06, beim Gemisch zusätzlich „Rein vs. Gemisch“, Quellen, Diagrammdaten). Anders als bei der Einspeicherung wird die Mappe also nicht von Hand gepflegt: nach einer Änderung die Skripte neu rechnen und die Mappe neu erzeugen. Blaue Annahmen auf der Übersicht dürfen zum Ausprobieren geändert werden – dann färben sich alle grauen Werte rot, bis neu gerechnet ist. Blatt 05 (Speicherbedarf) rechnet live.

## Laufzeit

Die Skripte laufen mit Python310 (dort ist CoolProp installiert). Reines CO₂ braucht für 01–04 wenige Minuten. Beim Gemisch ist Schritt 04 der langsamste (über eine Stunde), weil das Gemisch im Zweiphasengebiet freie Flashes braucht (~0,1–0,4 s je Zustand) – deshalb rechnet 04 beim Gemisch mit gröberem Raster (`n_strang = 50`, 10 Stützstellen).

Die alten Skripte aus `Kaverne/` (01_kavernen_tief_flach_stillstand.py … 06, kaverne_bausteine.py, ausspeichergas.py, JSON, alte Mappe) sind durch diese Struktur ersetzt und können ins Archiv.
