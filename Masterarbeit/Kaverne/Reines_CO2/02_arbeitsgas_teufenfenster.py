# -*- coding: utf-8 -*-
"""
Kaverne Schritt 02 (reines CO₂) - Arbeitsgas, Kissengas und Teufenfenster
============================================================================
Wie viel CO₂ lässt sich umschlagen (m = ρ·V, wie DBI Q-030 Kap. 1.3), als Klammer
langsam/isotherm und schnell/isentrop; der Auslegungswert kommt aus der Kavernenbilanz (03).
Teufenfenster: warum die Referenzkaverne in 1200 m liegt (Besprechung 15.10.2026, Pkt. 2).

Die Rechnung steht einmal in Grundlagen/kaverne_schritte.py (schritt_02) und läuft für
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

ks.schritt_02(kb.REIN, ORDNER)
