# Kaverne – Prozessschritte zwischen Einspeicherung und Ausspeicherung

Jedes Skript ist ein Prozessschritt. Die Skripte laufen in der Reihenfolge der Nummern, und jedes übergibt sein Ergebnis als JSON an die nächsten.
Annahmen und Rechenbausteine stehen nur in `kaverne_bausteine.py`. Die Stoffe (reines CO₂, Worst-Case-Gemisch) kommen unverändert aus `Einspeicherung/Begleitstoffe_CO2/Grundlagen`.

| Schritt | Skript | Frage | Ergebnis (→ wer nutzt es) |
|---|---|---|---|
| 01 | `01_kavernen_tief_flach_stillstand.py` | Was liegt im Stillstand in Kaverne und Bohrloch vor? | `kaverne_stillstand.json`: Kopfdrücke voll/leer (→ 02, Einspeicherung) |
| 02 | `02_arbeitsgas_teufe.py` | Wie viel Arbeitsgas, warum hängt das an der Teufe? | `arbeitsgas.json`, Teufenfenster |
| 03 | `03_ein_ausspeicherrate.py` | Welche Rate verträgt die Kaverne, was passiert bei 50.000/100.000 Nm³/h? | `kavernenzyklus.json` (→ 04, 06) |
| 04 | `04_bohrlochkopf_ausspeicherung.py` | Was kommt beim Ausspeichern am Kopf an? | `bohrlochkopf_ausspeicherung.json` (→ 06, Ausspeicherpfad) |
| 05 | `05_gemisch_vs_rein.py` | Was ändert das Worst-Case-Gemisch in 01–04? | `gemisch_vs_rein.json` (→ 06) |
| 06 | `06_zusammensetzung_nach_kaverne.py` | Welche Zusammensetzung hat das Ausspeichergas? | `zusammensetzung_nach_kaverne.json` (→ `ausspeichergas.py`) |

`ausspeichergas.py` ist das Stoffdatenblatt für den Ausspeicherpfad, also das Gegenstück zu `gemisch_worstcase.py`:

```python
import ausspeichergas as ag
AS = ag.gemisch_trocken()        # getrocknetes Ausspeichergas als CoolProp-AbstractState
y  = ag.wasser_im_co2(p, T)      # Wassersättigung (Spycher et al. 2003) für Abscheider/Trocknung
```

Beide Kavernen (tief: LCCS 1200 m, flach: LCCS 700 m) haben dieselbe Form und 650.000 m³ nach Q-028, damit der Vergleich nur die Teufe zeigt. Alle Annahmen mit Herkunft stehen in `Dokumentation_Kaverne.docx`. Nach einer Änderung die Kette 01–06 neu rechnen und dann `python dokumentation_erzeugen.py` ausführen – die Zahlen in der Dokumentation kommen aus den JSON-Dateien.

Die Skripte laufen mit Python310, weil dort CoolProp installiert ist. Eine komplette Kette dauert einige Minuten; Schritt 05 ist der langsamste, weil das Gemisch im Zweiphasengebiet freie Flashes braucht.
`Kaverne_Version1/` ist das Archiv der ersten Stillstandsrechnung; Schritt 01 ersetzt sie.
