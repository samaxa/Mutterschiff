# Gasgrundlagen – CO₂ im Vergleich zu Erdgas und Wasserstoff

Grundlagenrechnungen für Kap. 3 der Masterarbeit (Stoffliche Grundlagen): Was heißt überkritisch, gibt es dort einen Phasenübergang, wie verhält sich CO₂ beim Drosseln und beim Verdichten, und braucht es mehr oder weniger Energie als Erdgas und Wasserstoff? Dazu das Phasendiagramm mit dem Betriebsbereich der Referenzanlage.

**Herkunft:** erste Untersuchung in der alten Quellenmatrix (`1_Quellen-_und_Wissensmatrix_alt.xlsx`, Blätter „Isenthalpe_Entspannung_Gase“ und „JT-Koeffi_Gase“). Dort wurden die Zustände einzeln mit CoolProp Online und dem NIST WebBook abgefragt. Hier rechnet Python dieselben Fälle mit CoolProp direkt.

**Regel:** Die Excel-Mappe `CO2_Gasgrundlagen_Rechenuebersicht.xlsx` wird von Hand gepflegt, kein Skript erzeugt sie (wie bei der Einspeicherung). Sie zeigt jeden Rechenschritt mit Formeln, die Stoffwerte kommen aus CoolProp. Eine Änderung an den Annahmen kommt deshalb an zwei Stellen: in `gasgrundlagen_bausteine.py` und in der Mappe (Blatt „Übersicht“).

## Ordner

```
Gasgrundlagen/
├── README.md
├── gasgrundlagen_bausteine.py   Annahmen mit Begründung (Kopf der Datei), Stoffe, Rechenbausteine
├── 01 … 05                      Skripte
├── CO2_Gasgrundlagen_Rechenuebersicht.xlsx
├── Daten/                       nist_webbook_jt.csv (NIST-Werte aus der alten Mappe)
└── Abbildungen/                 alle Abbildungen und Ergebnisdateien (G01 … G05 .json)
```

## Skripte

| Skript | Was es macht | Abbildungen |
|---|---|---|
| `01_phasendiagramm_co2.py` | Sauberes p-T-Diagramm von reinem CO₂ mit pseudokritischer Linie und Betriebsbereich der Referenzanlage (30–210 bar, 5–65 °C); Dichte über Druck auf sechs Isothermen | `abb_G01_phasendiagramm_co2.png`, `abb_G01_dichte_isothermen.png` |
| `02_phasendiagramm_rein_vs_gemisch.py` | Links reines CO₂, rechts Worst-Case-Gemisch, gleiche Achsen, ohne Betriebspunkte | `abb_G02_phasendiagramm_rein_vs_gemisch.png` |
| `03_isenthalpe_entspannung.py` | Drosselung 210 bar / 50 °C → 10 bar für CO₂, CH₄, H₂; Weg von CO₂ im p-T-Diagramm | `abb_G03_drosselung_vergleich.png` |
| `04_isentrope_verdichtung.py` | Ideale Verdichtung 10 bar / 15 °C → 210 bar: Temperatur, Arbeit je kg und je Nm³; CO₂-Pumpe ab 91 bar; µ_S gegen µ_JT | `abb_G04_verdichtung_vergleich.png` |
| `05_jt_koeffizient.py` | µ_JT von CO₂ auf vier Isothermen, Vergleich der drei Gase bei 50 °C, Validierung gegen NIST (200 Punkte) | `abb_G05_jt_koeffizient.png` |

`02` braucht `Einspeicherung/Begleitstoffe_CO2/Grundlagen/gemisch_worstcase.py`. Die Ordner `Gasgrundlagen/` und `Einspeicherung/` müssen deshalb nebeneinander liegen. Alle anderen Skripte brauchen nur `gasgrundlagen_bausteine.py`.

Reihenfolge ist egal, jedes Skript läuft für sich (wenige Sekunden, Python310 mit CoolProp 8.0.0).

## Wichtigste Ergebnisse

- Kritischer Punkt 31,0 °C / 73,8 bar. Der Betriebsbereich der Referenzanlage (30–210 bar, 5–65 °C) schließt ihn ein, die Siedelinie läuft von 39,7 bar / 5 °C bis zum kritischen Punkt mitten durch.
- Überkritisch gibt es keinen Phasenwechsel, aber an der pseudokritischen Linie (91 bar: 40,5 °C) ändert sich die Dichte sehr stark: bei 91 bar von 669 kg/m³ (35 °C) auf 351 kg/m³ (45 °C).
- Drosselung 210 → 10 bar: CO₂ −90 K und ab 71 bar zweiphasig (58 % Dampf bei −40 °C), CH₄ −65 K einphasig, H₂ +8 K.
- µ_JT bei 50 °C: CO₂ im Gas ~0,9 K/bar, in dichter Phase (210 bar) nur 0,07 K/bar und damit kleiner als Erdgas (0,15 K/bar). H₂ −0,04 K/bar.
- Verdichtung bis 210 bar: CO₂ 220 kJ/kg, CH₄ 646 kJ/kg, H₂ 5.927 kJ/kg. Je Nm³ liegen alle drei nah beieinander (435 / 463 / 533 kJ/Nm³). Verdichten bis 91 bar, kühlen und pumpen: 158 kJ/kg, die Pumpe selbst nur 13 kJ/kg.
- CoolProp und NIST WebBook stimmen für µ_JT auf allen 200 Punkten im Rahmen der Rundung überein (gleiche Zustandsgleichung).

Hinweis zur alten Mappe: im Diagramm „JT-Koeffi_Gase“ wurden die 20- und 30-°C-Werte über der Druckspalte der 50-°C-Daten aufgetragen. Wegen der zusätzlichen Siedepunkte (57,3 bzw. 72,1 bar) sind die Kurven dort um eine bis zwei Druckstufen verschoben. In `05` und in der neuen Mappe hat jede Isotherme ihren eigenen Druck.
