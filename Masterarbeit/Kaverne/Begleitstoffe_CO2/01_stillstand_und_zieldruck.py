# -*- coding: utf-8 -*-
"""
Kaverne Schritt 01 (Worst-Case-Gemisch) - Stillstand und Zieldruck im Betrieb
============================================================================
Was liegt am Bohrlochkopf an?
  - Stillstand (ruhende Säule, Gebirgstemperatur, Darstellung nach Q-028 Fig. 3): Kopfdruck
    voll / Grenzfall / leer. Grenzfall = Kopf genau an der Phasengrenze (Cricondenbar 82,2 bar).
  - Einspeisen (strömende Säule, adiabat, mit Reibung): Zieldruck der Pumpe im Betrieb für
    S1 und S2 bei 50.000 / 100.000 Nm³/h - gekoppelt an die Einspeicherung (Pumpenaustritt).
    Ersetzt den Stillstandswert als Auslegungsdruck (Besprechung K. Vosbeck 15.10.2026, Pkt. 6).

Die Rechnung steht einmal in Grundlagen/kaverne_schritte.py (schritt_01) und läuft für
reines CO₂ und Gemisch gleich; Annahmen mit Fundstellen: Grundlagen/kaverne_bausteine.py.
Erster Schritt - braucht nichts vorher.
Ausgabe in diesem Ordner: JSON (für die folgenden Schritte und die Excel-Mappe) und PNG.
"""
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402
import kaverne_schritte as ks    # noqa: E402

ks.schritt_01(kb.gemisch(), ORDNER)
