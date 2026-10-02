# Begleitstoffe_CO2 – Einspeicherung mit Worst-Case-Gemisch

Hier wird gerechnet, was die Begleitstoffe am Einspeicherpfad ändern: Stoffdaten des Gemischs, Phasengrenze, Validierung, Einspeicherpfad S1/S2 und die Begründung für den gewählten S2-Weg.
Gemisch (mol-%): 95 % CO₂, 2,4 % N₂, 1 % Ar, 1 % CH₄, 0,5 % H₂, 0,1 % CO.

**Regel:** Die Excel-Mappe `CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx` wird von Hand gepflegt, kein Skript erzeugt sie. Skript `03` rechnet dasselbe wie die Mappe und vergleicht am Ende mit deren Werten. Eine Änderung an Annahmen kommt deshalb immer an zwei Stellen: in `einspeicherung_bausteine.py` und in der Mappe (Blatt „Übersicht“).

## Skripte

| Skript | Was es macht | Braucht | Ergebnis |
|---|---|---|---|
| `gemisch_worstcase.py` | Stoffdatenblatt des Gemischs: Zusammensetzung, Stoffwerte (CoolProp), Phasengrenze (Tau-/Blasenlinie, kritischer Punkt, Cricondenbar). Kein eigenes Ergebnis, alle anderen Skripte importieren von hier. | – | – |
| `einspeicherung_bausteine.py` | Alle Annahmen der Einspeicherung an einer Stelle (= Mappe, Blatt „Übersicht“) und die Rechenbausteine: Gassäule, Verdichter-/Pumpenstufe, Kühler, reines CO₂ und Gemisch mit gleicher Schnittstelle. Kein eigenes Ergebnis. | `gemisch_worstcase.py` | – |
| `01_phasendiagramm_rein_vs_gemisch.py` | p-T-Diagramm reines CO₂ vs. Gemisch: Wo liegt das Zweiphasengebiet, wo liegen die Betriebspunkte? | `gemisch_worstcase.py` | `abb_phasendiagramm_rein_vs_gemisch.png` |
| `02_validierung_stoffmodelle.py` | Prüft CoolProp gegen eine zweite Software (thermopack: GERG-2008, Peng-Robinson, SRK) → Unsicherheit der Phasengrenze ±3 bar. | `gemisch_worstcase.py`, `pip install thermopack` | `abb_validierung_phasengrenze.png`, `abb_validierung_rein_co2.png` |
| `03_einspeicherpfad_gemisch.py` | **Hauptrechnung** wie die Mappe: Gassäule → Kopfdruck, S1 Pumpe, S2 zwei Verdichterstufen 30 → 50 → 91 bar, Kühler auf 26 °C, Pumpe; Prüfungen (95 °C, Z > 0,65, Dichte ≥ 500 kg/m³); Vergleich mit reinem CO₂; Kontrolle gegen die Werte der Mappe. | `einspeicherung_bausteine.py` | `abb_einspeicherpfad_gemisch.png`, `abb_arbeit_rein_vs_gemisch.png`, `abb_gassaeule_rein_vs_gemisch.png` |
| `04_phasenpfade_vergleich.py` | Begründung für den S2-Weg: vergleicht fünf Wege A–E (verflüssigen, über der Cricondenbar kühlen, durchverdichten, tiefkalt verflüssigen, Pumpe im Zweiphasengebiet), Kühltemperatur und Zwischenkühlung. | `einspeicherung_bausteine.py`, `pip install scipy` | `abb_phasenpfade_gemisch.png`, `abb_kuehltemperatur_pumpeneintritt.png`, `phasenpfade_ergebnisse.json` |

Reihenfolge zum Neurechnen: `01` → `02` → `03` → `04` (jedes Skript läuft auch einzeln).

## Dokumentation und Mappe

| Datei | Inhalt | Gehört zu |
|---|---|---|
| `Dokumentation_Stoffmodelle_Validierung_v2.docx` | Stoffmodelle (Span-Wagner, Mehrfluid-Helmholtz/GERG-2008), Validierung, Unsicherheit ±3 bar | `gemisch_worstcase.py`, `01`, `02` |
| `Dokumentation_S2_Gemisch.docx` | Wege A–E, Wahl des S2-Wegs, Annahmen mit Quellen, Nachweis | `einspeicherung_bausteine.py`, `03`, `04` |
| `CO2_Einspeicherpfad_Rechenuebersicht_Gemisch.xlsx` | Rechenübersicht Gemisch (von Hand gepflegt; liegt lokal, nicht im Repo) | `03` |

## Wer nutzt die Dateien noch?

- `Kaverne/kaverne_bausteine.py` importiert `gemisch_worstcase.py` und `einspeicherung_bausteine.py`. Ein- und Ausspeicherung rechnen so mit demselben Gemisch. **Beide Dateien deshalb nicht umbenennen oder verschieben.**
- `Clean_CO2/Reines_CO2_S2_gas_Phase/03_Verdichtung_Kuehlung_Pumpe.py` verweist im Text auf `04_phasenpfade_vergleich.py`.
