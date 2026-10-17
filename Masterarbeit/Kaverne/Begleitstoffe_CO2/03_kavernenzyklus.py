# -*- coding: utf-8 -*-
"""
Kaverne Schritt 03 (Worst-Case-Gemisch) - Raten und Kavernenzyklus
============================================================================
Ratengrenze aus ≤ 10 bar/d (Q-030 Kap. 1.2.1) und Kavernenbilanz über einen Zyklus nach
Q-028 Kap. 4: Einspeisung mit der Enthalpie aus S1 bzw. S2, 50.000 / 100.000 Nm³/h,
Stillstand 21,67 d (Q-028) gegen kontinuierlich (Besprechung 15.10.2026, Pkt. 8).

Die Rechnung steht einmal in Grundlagen/kaverne_schritte.py (schritt_03) und läuft für
reines CO₂ und Gemisch gleich; Annahmen mit Fundstellen: Grundlagen/kaverne_bausteine.py.
Braucht vorher: Schritt 01 in diesem Ordner.
Ausgabe in diesem Ordner: JSON (für die folgenden Schritte und die Excel-Mappe) und PNG.
"""
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402
import kaverne_schritte as ks    # noqa: E402

ks.schritt_03(kb.gemisch(), ORDNER)
