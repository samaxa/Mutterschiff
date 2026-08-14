# CO2-Salzkaverne – Auslegungsrechnung

Parametrisiertes Python-Skript für den Ein- und Ausspeicherpfad einer CO2-Salzkaverne.
Alle Stoffdaten werden **live aus CoolProp** (Zustandsgleichung Span & Wagner 1996) berechnet.

## Warum ein Skript statt Excel

In Excel sind CoolProp-Werte eingefrorene Zahlen. Ändert man dort z. B. die
Oberflächentemperatur, rechnen sich Teufe, Temperatur und Δp neu – **die Dichten
bleiben aber auf den alten Werten stehen**, und das Ergebnis ist stillschweigend falsch.
Hier wird bei jeder Änderung alles konsistent neu berechnet.

## Aufbau

Vier Module, jedes in seinem Ordner zusammen mit den Dateien, die es erzeugt:

| Ordner | Modul | beantwortet |
|---|---|---|
| `1_auslegung/` | `co2_kaverne.py` | Wie sehen Gassäule, Druckfenster und Prozesspfade bei fester Teufe aus? |
| `2_zyklussimulation/` | `zyklus.py`, `zyklus_plot.py` | Wie verhält sich die Kaverne über einen kompletten Speicherzyklus? |
| `3_teufenoptimierung/` | `teufenoptimierung.py` | Welche Teufe und welche Ausspeicherrate sind sinnvoll? |
| `4_vorwaermer/` | `vorwaermer.py` | Wieviel Vorwärmleistung braucht die Drossel? (CO2 gegen Erdgas) |

`CO2_Gassaeule_Kaverne_Original.xlsx` ist die ursprüngliche Excel-Rechnung, aus der das
Projekt entstanden ist – siehe Abschnitt oben, warum sie durch Skripte ersetzt wurde.

## Benutzung

```bash
pip install CoolProp matplotlib openpyxl numpy
```

Jedes Modul ist eigenständig und wird in seinem Ordner aufgerufen:

```bash
cd 1_auslegung && python co2_kaverne.py
```

Einzige Reihenfolge-Abhängigkeit: `zyklus_plot.py` importiert `zyklus.py`, beide liegen
deshalb im selben Ordner.

Alle Annahmen stehen im Block `CFG` bzw. im Kopf der Datei. Ändern, Skript erneut
ausführen, fertig.

### Gemeinsame Geologie-Annahmen

Diese drei Werte müssen in allen Modulen übereinstimmen, sonst rechnen sie an
unterschiedlichen Kavernen:

| Größe | Wert | steht in |
|---|---|---|
| Teufe | 1200 m | `co2_kaverne.py` (`CFG["teufe"]`), `zyklus.py` (`TEUFE`) |
| Oberflächentemperatur Gebirge | 10 °C | Module 1–3 |
| geothermischer Gradient | 0,03 K/m | Module 1–3 |

Daraus folgt die Gebirgstemperatur 46 °C, die `zyklus.py` als `T_rock` berechnet statt sie
fest einzutragen. `teufenoptimierung.py` hat bewusst keine feste Teufe – dort ist sie die
Scan-Variable. `vorwaermer.py` ist eine eigenständige Vergleichsrechnung und nicht an diese
Werte gekoppelt.

Achtung: `T_anlieferung` in `co2_kaverne.py` ist die *Medium*temperatur an der Pipeline und
hat mit der Gebirgstemperatur nichts zu tun – die bleibt bei 15 °C.

## Ausgabe

**1_auslegung/**

| Datei | Inhalt |
|---|---|
| `report.txt` | Konsolenreport mit allen Kennzahlen |
| `abb1_kavernenschema.png` | Kavernenschema mit Betriebsdaten + Druckfenster/Regime |
| `abb2_teufenprofile.png` | Temperatur-, Druck- und Dichteprofil (nach Quelle Fig. 3) |
| `abb3_phasendiagramm.png` | p-T-Diagramm mit dem kompletten Prozesskreislauf |
| `abb4_arbeitsgas.png` | Inventar über Druck + Arbeitsgas je Minimaldruck |
| `CO2_Kaverne_berechnet.xlsx` | Tabellen mit frischen Werten (für Weitergabe) |

**2_zyklussimulation/**

| Datei | Inhalt |
|---|---|
| `report_zyklus.txt` | Phasentabelle und Arbeitsgas der Zyklussimulation |
| `abb5_zyklus.png` | Druck, Temperatur und Inventar über einen Zyklus, zwei Raten |
| `abb6_inventarmessung.png` | warum der Druck unterhalb p_krit kein Füllstandsmaß ist |
| `zyklus.json` | Rohdaten des simulierten Zyklus |

**3_teufenoptimierung/**

| Datei | Inhalt |
|---|---|
| `report_teufe.txt` | Tabelle und Empfehlung zur Teufe |
| `abb7_teufenoptimierung.png` | Arbeitsgas über Teufe mit Randbedingungen |
| `abb8_auslegungsfenster.png` | Zielkonflikt Arbeitsgasanteil gegen Jahresdurchsatz |

**4_vorwaermer/**

| Datei | Inhalt |
|---|---|
| `report_vorwaermer.txt` | Vorwärmtemperatur und -leistung je Drosseldruck, CO2 gegen CH4 |

## Rechenwege

- **Gassäule**: schrittweise Integration von `dp/dz = ρ(p,T)·g`, weil ρ selbst vom
  gesuchten Druck abhängt. Konstantes ρ·g·h wäre bei CO2 mehrere bar daneben.
- **Kopfdruck / Regimegrenze**: Sekantenverfahren, da der gesuchte Wert am jeweils
  anderen Ende der Säule liegt als der vorgegebene.
- **Pumpe / Verdichter**: isentrope Zustandsänderung mit Wirkungsgrad η,
  `h2 = h1 + (h2s − h1)/η`, Rückrechnung von T aus (p, h).
- **Drossel**: isenthalp (h = konst.), Joule-Thomson.
- **Kopftemperatur beim Ausspeichern**: Energiebilanz `h + g·z = konst.`
  (adiabater Grenzfall = hohe Rate). Langsamer Grenzfall: Gas folgt dem Gebirgsprofil.
- **Arbeitsgas**: Massenbilanz `m = ρ(p,T)·V`. **Nicht** über das Druckverhältnis –
  ρ ist bei CO2 nahe dem kritischen Punkt stark nichtlinear.

## Validierung gegen die Quelle

Mit den Kavernenparametern von Buzogany & Kruck (1150 m, 10 °C, 0,03 K/m) reproduziert
das Skript deren veröffentlichte Kopfdrücke exakt:

| pLCCS | Paper | berechnet |
|---|---|---|
| 200 bar | 102,2 bar | 102,2 bar |
| 167,9 bar | 73,8 bar | 73,8 bar |

Ebenso: kritische Teufe 699 m (Paper 725 m) und Zweiphasengebiet im oberen Bohrloch
ab ca. 225 m (Paper ca. 250 m).

Die 10 °C Oberflächentemperatur der Quelle sind die Standardannahme aller drei Module –
mit 15 °C läge die kritische Teufe bei 533 m und die Validierung oben würde nicht mehr
aufgehen.

## Zyklussimulation

`zyklus.py` löst die Massen- und Energiebilanz der Kaverne über einen kompletten Zyklus
(Ausspeichern → Stillstand → Einspeichern → Stillstand → Ausspeichern):

    dm/dt = ṁ
    dU/dt = ṁ·h + UA·(T_Gebirge − T_Kaverne)

Zustand jeweils aus (ρ, u) über CoolProp. Zentrales Ergebnis: **die Ausspeicherrate bestimmt
das Arbeitsgas.** Langsam (55 kg/s) → Kaverne kühlt auf 36 °C → 71 % Arbeitsgas.
Schnell (234 kg/s) → Kaverne kühlt auf 29 °C, also **unter T_krit**, der Inhalt wird
zweiphasig → nur 33 %. Die Quelle vermutet genau diesen Zusammenhang; ihre Vollsimulation
liefert 22–32 % — der schnelle Grenzfall trifft diesen Bereich.

Vereinfachungen: Kaverne ideal durchmischt, Bohrloch nicht modelliert, UA als konstante Annahme.

## Teufenoptimierung

`teufenoptimierung.py` beantwortet die Frage, die Buzogany & Kruck in Kap. 5 nur qualitativ
aufwerfen: *welche Teufe ist für CO₂ eigentlich optimal?*

Bewertet werden Arbeitsgas (in zwei Grenzfällen) sowie die Randbedingungen: Gebirgstemperatur
über T_krit (sonst Flüssigphase in der Kaverne), geomechanisches Teufenfenster, und ob der
Mindestdruck unter p_krit liegt (dann wandelt sich CO₂ in der Kaverne teilweise in Gas um,
was günstig ist).

Zulässiges Fenster: **799–1139 m.** Die Untergrenze setzt die Temperatur (darunter fällt die
Gebirgstemperatur unter T_krit + 3 K Marge, Flüssigphase in der Kaverne möglich), die
Obergrenze der Druck (darüber liegt p_min über p_krit, man fährt nur im flachen Teil der
Dichtekurve).

Ergebnis: **Das Optimum liegt auf der flachen Grenze dieses Bereichs, bei ~800 m.**
Beide Grenzfälle zeigen dieselbe Richtung – flacher ist besser. Der Effekt ist beim schnellen
Ausspeichern deutlich stärker (153 kt bei 800 m gegenüber 45 kt bei 1000 m).

**Wichtige Einschränkung:** Das Optimum ist ein *Randoptimum* – es liegt auf der jeweils
bindenden Nebenbedingung, nicht auf einem inneren Maximum. Es hängt damit direkt an der frei
gewählten Sicherheitsmarge `T_marge` (3 K). Ohne Marge verschöbe es sich auf 699 m. Das
Arbeitsgas fällt dort steil ab (~12 % je 25 m Teufe), weshalb das 95-%-Empfehlungsfenster auf
einen einzelnen Rasterpunkt zusammenfällt.

Zielkonflikt: Bei flachen Kavernen und hohen Raten wird der Kaverneninhalt selbst zweiphasig
(Dampfanteil q ≈ 0,11 bei 800 m). Das spricht zusätzlich für eine Ratenbegrenzung – die
ohnehin das Arbeitsgas erhöht.

## Grenzen

- Statische Säule; Reibungsdruckverluste bei Strömung sind nicht enthalten.
- Kavernentemperatur vereinfacht = Gebirgstemperatur; keine transiente Simulation.
- Arbeitsgaswerte sind eine **obere** Abschätzung. Die Vollsimulation der Quelle
  liefert 22–32 % Arbeitsgas, da die Kaverne beim Ausspeichern abkühlt und die
  Druckänderungsrate begrenzt ist.
- Reine Stoffdaten für CO2; Verunreinigungen verschieben die Phasengrenzen.

## Quelle

Buzogany, R. & Kruck, O. (2022): *CO2 – Storage in Salt Caverns: Thermodynamic Analysis
and Challenges.* SMRI Fall 2022 Technical Conference, Chester, UK.
Übernommen: Konzept der Druckbereiche, geothermischer Gradient, Betriebsfenster.
Berechnung und Zahlenwerte eigenständig.
