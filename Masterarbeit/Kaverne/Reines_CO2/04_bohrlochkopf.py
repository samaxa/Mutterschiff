# -*- coding: utf-8 -*-
"""
Kaverne Schritt 04 (reines CO₂) - Bohrlochkopf: Kopfdruckfenster beim Ein- und Ausspeichern
============================================================================
Der Kopfdruck ist die Regelgröße der Kaverne (Besprechung 15.10.2026, Pkt. 6):
Einspeisen max. = Auslegungsdruck der Pumpe, Ausspeisen min. = Rückverdichtung.
Förderstrang nur adiabat (Pkt. 5), Reibungseinfluss auf Druck und Temperatur ausgewiesen.

Die Rechnung steht einmal in Grundlagen/kaverne_schritte.py (schritt_04) und läuft für
reines CO₂ und Gemisch gleich; Annahmen mit Fundstellen: Grundlagen/kaverne_bausteine.py.
Braucht vorher: Schritt 01 und 03 in diesem Ordner.
Ausgabe in diesem Ordner: JSON (für die folgenden Schritte und die Excel-Mappe) und PNG.

Teile einzeln rechnen (z. B. zwei Konsolen parallel, Gemisch dauert über eine Stunde):
    python 04_bohrlochkopf.py "aus|100.000 Nm³/h" "ein|S2|100.000 Nm³/h"
Teile: ks.TEILE_04. Zwischenergebnisse liegen in _zwischen_04/ und werden wiederverwendet;
ein Lauf ohne Argumente setzt alles zusammen (Reibung, Abbildungen, bohrlochkopf.json).
"""
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402
import kaverne_schritte as ks    # noqa: E402

ks.schritt_04(kb.REIN, ORDNER, teile=sys.argv[1:] or None)
