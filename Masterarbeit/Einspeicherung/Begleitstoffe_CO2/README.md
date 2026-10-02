# Begleitstoffe_CO2 – Einspeicherung mit Worst-Case-Gemisch

Hier wird gerechnet, was die Begleitstoffe am Einspeicherpfad ändern: Stoffdaten des Gemischs, Phasengrenze, Validierung, Einspeicherpfad S1/S2 und die Begründung für den gewählten S2-Weg.
Gemisch (mol-%): 95 % CO₂, 2,4 % N₂, 1 % Ar, 1 % CH₄, 0,5 % H₂, 0,1 % CO.

**Regel:** Die Excel-Mappe `Grundlagen/CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx` wird von Hand gepflegt, kein Skript erzeugt sie. Die Skripte `03_S1` und `03_S2` rechnen dasselbe wie die Mappe und vergleichen am Ende mit deren Werten. Eine Änderung an Annahmen kommt deshalb immer an zwei Stellen: in `Grundlagen/einspeicherung_bausteine.py` und in der Mappe (Blatt „Übersicht“).

## Ordner

```
Begleitstoffe_CO2/
├── README.md
├── Grundlagen/      Annahmen, Stoffdaten, Excel-Mappe, Dokumentationen
├── Stoffmodell/     01 Phasendiagramm, 02 Validierung
├── Prozesskette/    03 S1 und S2, 04 Vergleich der S2-Wege
└── Abbildungen/     alle Abbildungen und phasenpfade_ergebnisse.json
```

Die Skripte finden die Dateien in `Grundlagen/` selbst und speichern ihre Abbildungen immer in `Abbildungen/`, egal aus welchem Ordner sie gestartet werden.

## Grundlagen

| Datei | Inhalt |
|---|---|
| `gemisch_worstcase.py` | Stoffdatenblatt des Gemischs: Zusammensetzung, Stoffwerte (CoolProp), Phasengrenze (Tau-/Blasenlinie, kritischer Punkt, Cricondenbar). Alle anderen Skripte importieren von hier. |
| `einspeicherung_bausteine.py` | Alle Annahmen der Einspeicherung an einer Stelle (= Mappe, Blatt „Übersicht“) und die Rechenbausteine: Gassäule, Verdichter-/Pumpenstufe, Kühler, reines CO₂ und Gemisch mit gleicher Schnittstelle. |
| `CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx` | Rechenübersicht Gemisch (von Hand gepflegt) |
| `Dokumentation_Stoffmodelle_Validierung.docx` | Stoffmodelle (Span-Wagner, Mehrfluid-Helmholtz/GERG-2008), Validierung, Unsicherheit ±3 bar → gehört zu `01`, `02` |
| `Dokumentation_S2_Gemisch.docx` | Wege A–E, Wahl des S2-Wegs, Annahmen mit Quellen, Nachweis → gehört zu `03`, `04` |

## Skripte

| Skript | Was es macht | Braucht | Abbildungen |
|---|---|---|---|
| `Stoffmodell/01_phasendiagramm_rein_vs_gemisch.py` | p-T-Diagramm reines CO₂ vs. Gemisch mit den aktuellen Betriebspunkten | `gemisch_worstcase`, `einspeicherung_bausteine` | `abb_phasendiagramm_rein_vs_gemisch.png` |
| `Stoffmodell/02_validierung_stoffmodelle.py` | Prüft CoolProp gegen thermopack (GERG-2008, Peng-Robinson, SRK) → Unsicherheit der Phasengrenze ±3 bar | `gemisch_worstcase`, `pip install thermopack` | `abb_validierung_phasengrenze.png`, `abb_validierung_rein_co2.png` |
| `Prozesskette/03_S1_pumpe_gemisch.py` | Gassäule → Kopfdruck (voll/leer), S1 Pumpe 91 bar → Kopfdruck; Vergleich mit reinem CO₂; Kontrolle gegen die Mappe | `einspeicherung_bausteine` | `abb_gassaeule_rein_vs_gemisch.png` |
| `Prozesskette/03_S2_verdichtung_kuehlung_pumpe_gemisch.py` | S2: zwei Verdichterstufen 30 → 50 → 91 bar, Kühler auf 26 °C, Pumpe; Prüfungen (95 °C, Z > 0,65, Dichte ≥ 500 kg/m³); Vergleich mit reinem CO₂; Kontrolle gegen die Mappe | `einspeicherung_bausteine` | `abb_einspeicherpfad_gemisch.png`, `abb_arbeit_rein_vs_gemisch.png` |
| `Prozesskette/04_phasenpfade_vergleich.py` | Begründung für den S2-Weg: vergleicht fünf Wege A–E, Kühltemperatur und Zwischenkühlung | `einspeicherung_bausteine`, `pip install scipy` | `abb_phasenpfade_gemisch.png`, `abb_kuehltemperatur_pumpeneintritt.png`, `phasenpfade_ergebnisse.json` |

Reihenfolge zum Neurechnen: `01` → `02` → `03_S1` → `03_S2` → `04` (jedes Skript läuft auch einzeln).

## Wer nutzt die Dateien noch?

- `Kaverne/kaverne_bausteine.py` importiert `Grundlagen/gemisch_worstcase.py` und `Grundlagen/einspeicherung_bausteine.py`, `Kaverne/dokumentation_erzeugen.py` nutzt `Grundlagen/Dokumentation_S2_Gemisch.docx` als Formatvorlage. Ein- und Ausspeicherung rechnen so mit demselben Gemisch. **Diese Dateien deshalb nicht umbenennen oder verschieben** (sonst dort den Pfad anpassen).
- `Clean_CO2/Reines_CO2_S2_gas_Phase/03_Verdichtung_Kuehlung_Pumpe.py` verweist im Text auf `Prozesskette/04_phasenpfade_vergleich.py`.
