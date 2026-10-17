# Begleitstoffe_CO2 – Einspeicherung mit Worst-Case-Gemisch

Hier wird gerechnet, was die Begleitstoffe am Einspeicherpfad ändern: Stoffdaten des Gemischs, Phasengrenze, Validierung, Einspeicherpfad S1/S2 und die Begründung für den gewählten S2-Weg.
Gemisch (mol-%): 95 % CO₂, 2,4 % N₂, 1 % Ar, 1 % CH₄, 0,5 % H₂, 0,1 % CO.

**Handbuch:** `../Handbuch_Einspeicherung.docx` erklärt den gesamten Code der Einspeicherung (Clean_CO2 und Begleitstoffe_CO2): Arbeitsumgebung, Zustandsgleichungen, Rechenbausteine, Architektur, jedes Skript mit seinen Abbildungen, Validierung (Kurzfassung) und Quellen. Es ersetzt die vier früheren Dokumentationen (Einspeicherung Gemisch, S2 Gemisch, S1 dichte Phase, S2 gasförmig); diese liegen in `../Archiv_Dokumentation/`. `Grundlagen/Dokumentation_Stoffmodelle_Validierung.docx` bleibt eine eigene Dokumentation (Gleichungen, Phasendiagramme, Validierung, ± 3 bar, Abgrenzung der Spurenstoffe).

**Regel:** Die Excel-Mappe `Grundlagen/CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx` wird von Hand gepflegt, kein Skript erzeugt sie. Die Skripte `03_S1` und `03_S2` rechnen dasselbe wie die Mappe und vergleichen am Ende mit deren Werten. Eine Änderung an Annahmen kommt deshalb immer an zwei Stellen: in `Grundlagen/einspeicherung_bausteine.py` und in der Mappe (Blatt „Übersicht“). Die Mappe für reines CO₂ liegt in `../Clean_CO2/` und hat denselben Aufbau.

**Stand 15.10.2026 (Besprechung K. Vosbeck):** zwei Kühler mit verschiedenem Zweck – Zwischenkühler 40 °C (Q-017 S. 37, Q-063 Kap. 5.1), Kühler vor der Pumpe 26 °C = Kühlwasser 20 °C + 6 K (Q-120 Folie 24/32); Zwischendruck 55 bar (Z ≥ 0,7 nach Q-017 S. 44 für rein und Gemisch); Zieldruck der Pumpe nicht mehr aus der ruhenden, sondern aus der strömenden Säule beim Einspeisen (100.000 Nm³/h, Reibung, Kopftemperatur = Pumpenaustritt). Neu in den Mappen: Blätter „Annahmen & Begründung“ (jede Annahme mit Quelle und Fundstelle), „Kühlung“ und „Massenströme“.

## Ordner

```
Begleitstoffe_CO2/
├── README.md
├── Grundlagen/      Annahmen, Stoffdaten, Excel-Mappe, Doku Stoffmodelle
├── Stoffmodell/     01 Phasendiagramm, 02 Validierung
├── Prozesskette/    03 S1 und S2, 04 Vergleich der S2-Wege
└── Abbildungen/     alle Abbildungen und die Ergebnisdateien (s1_, s2_, phasenpfade_, kuehlung_, massenstrom_ergebnisse.json)
```

Die Skripte finden die Dateien in `Grundlagen/` selbst und speichern ihre Abbildungen immer in `Abbildungen/`, egal aus welchem Ordner sie gestartet werden.

## Grundlagen

| Datei | Inhalt |
|---|---|
| `gemisch_worstcase.py` | Stoffdatenblatt des Gemischs: Zusammensetzung, Stoffwerte (CoolProp), Phasengrenze (Tau-/Blasenlinie, kritischer Punkt, Cricondenbar). Alle anderen Skripte importieren von hier. |
| `einspeicherung_bausteine.py` | Alle Annahmen der Einspeicherung an einer Stelle (= Mappe, Blatt „Übersicht“), jede mit Fundstelle im Kopf der Datei, und die Rechenbausteine: Gassäule, Verdichter-/Pumpenstufe, Kühler, `kette_S2` (ganzer S2-Weg), reines CO₂ und Gemisch mit gleicher Schnittstelle. |
| `CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx` | Rechenübersicht Gemisch (von Hand gepflegt) |
| `Dokumentation_Stoffmodelle_Validierung.docx` | Stoffmodelle (Span-Wagner, Mehrfluid-Helmholtz/GERG-2008), Validierung, Unsicherheit ±3 bar, Herleitung der Zusammensetzung, Abgrenzung der Spurenstoffe → gehört zu `01`, `02`, `03` |

## Skripte

| Skript | Was es macht | Braucht | Abbildungen |
|---|---|---|---|
| `Stoffmodell/01_phasendiagramm_rein_vs_gemisch.py` | p-T-Diagramm reines CO₂ vs. Gemisch mit den aktuellen Betriebspunkten | `gemisch_worstcase`, `einspeicherung_bausteine` | `abb_phasendiagramm_rein_vs_gemisch.png`; schlicht ohne Betriebspunkte: `abb_phasendiagramm_rein_schlicht.png`, `abb_phasendiagramm_gemisch_schlicht.png` |
| `Stoffmodell/02_validierung_stoffmodelle.py` | Prüft CoolProp gegen thermopack (GERG-2008, Peng-Robinson, SRK) → Unsicherheit der Phasengrenze ±3 bar | `gemisch_worstcase`, `pip install thermopack` | `abb_validierung_phasengrenze.png`, `abb_validierung_rein_co2.png` |
| `Stoffmodell/03_abgrenzung_spurenstoffe.py` | Abgrenzung der Spurenstoffe: welche CoolProp rechnen kann (10 von 20), Vergleich 6 gegen 9 Komponenten (≤ 0,025 bar), Gegenprobe Kohlenwasserstoffe | `gemisch_worstcase` | `abb_abgrenzung_spurenstoffe.png`, `abgrenzung_spurenstoffe.json` |
| `Prozesskette/03_S1_pumpe_gemisch.py` | Zieldruck am Kopf im Stillstand (Gassäule) und im Betrieb (strömende Säule, 50.000/100.000 Nm³/h); S1 Pumpe 91 bar → Zieldruck im Betrieb; rein vs. Gemisch; Kontrolle gegen die Mappe | `einspeicherung_bausteine`, `Kaverne/Grundlagen/kaverne_bausteine` | `abb_gassaeule_rein_vs_gemisch.png`, `s1_ergebnisse.json` |
| `Prozesskette/03_S2_verdichtung_kuehlung_pumpe_gemisch.py` | S2: Verdichter 30 → 55 bar, Zwischenkühler 40 °C, Verdichter → 91 bar, Kühler 26 °C, Pumpe auf den Zieldruck im Betrieb; Prüfungen (95 °C, Z > 0,65 bzw. ≥ 0,7, Dichte ≥ 500 kg/m³); rein vs. Gemisch; Kontrolle gegen die Mappe | `einspeicherung_bausteine`, `Kaverne/Grundlagen/kaverne_bausteine` | `abb_einspeicherpfad_gemisch.png`, `abb_arbeit_rein_vs_gemisch.png`, `s2_ergebnisse.json` |
| `Prozesskette/04_phasenpfade_vergleich.py` | Begründung für den S2-Weg: vergleicht fünf Wege A–E (Zieldruck aus `s2_ergebnisse.json`) | `einspeicherung_bausteine`, `pip install scipy` | `abb_phasenpfade_gemisch.png`, `abb_kuehltemperatur_pumpeneintritt.png`, `phasenpfade_ergebnisse.json` |
| `Prozesskette/05_kuehlung_begruendung.py` | Warum 40 °C / 26 °C / 55 bar: Dichte und cp bei 91 bar (pseudokritische Linie), Wahl des Zwischendrucks, Zwischenkühler-Temperatur gegen Z, Kühlwasser 15/20/25 °C → Zieldruck | `einspeicherung_bausteine`, `kaverne_bausteine` | `abb_kuehlung_pseudokritisch.png`, `abb_zwischenkuehler.png`, `kuehlung_ergebnisse.json` |
| `Prozesskette/06_massenstrom_volumenstroeme.py` | Ein Massenstrom, viele Volumenströme: tatsächlicher Volumenstrom an jedem Zustandspunkt S1/S2 | `s1_ergebnisse.json`, `s2_ergebnisse.json` | `abb_volumenstroeme.png`, `massenstrom_ergebnisse.json` |

Reihenfolge zum Neurechnen: `01` → `02` → `03` → `04` (Stoffmodell) → `03_S1` → `03_S2` → `04` → `05` → `06` (Prozesskette). `03_S1` und `03_S2` brauchen `Kaverne/Grundlagen/kaverne_bausteine.py` (strömende Säule); `04` und `06` lesen die JSON-Dateien von `03_S1`/`03_S2`.

## Wer nutzt die Dateien noch?

- `Kaverne/Grundlagen/kaverne_bausteine.py` importiert `Grundlagen/gemisch_worstcase.py` und `Grundlagen/einspeicherung_bausteine.py`. Ein- und Ausspeicherung rechnen so mit demselben Gemisch. **Diese Dateien deshalb nicht umbenennen oder verschieben** (sonst dort den Pfad anpassen).
- Umgekehrt nutzen `03_S1`, `03_S2`, `05` und `06` den Förderstrang aus `Kaverne/Grundlagen/kaverne_bausteine.py` (`zieldruck_einspeisen`). Die beiden Ordner `Einspeicherung/` und `Kaverne/` müssen deshalb nebeneinander liegen.
- `Clean_CO2/Reines_CO2_S1_dichte_Phase/03_Pumpe_Verdichtung.py` und `Clean_CO2/Reines_CO2_S2_gas_Phase/03_Verdichtung_Kuehlung_Pumpe.py` rechnen mit denselben Bausteinen (S2 jetzt ebenfalls Pfad B: überkritisch kühlen).
- Die Handbücher (`../Handbuch_Einspeicherung.docx`) sind noch auf dem Stand vor dem 15.10.2026 – Zahlen zu Zwischendruck, Kühlung und Zieldruck dort nachziehen.
