# -*- coding: utf-8 -*-
"""
Kaverne Schritt 09 (reines CO₂) - Vergleich von drei Mindestdrücken an der LCCS
============================================================================
Stand 09.11.2026. Drei Betriebsweisen, p_max jeweils 210 bar:
  160 bar  DBI-Empfehlung für Option 2 (Q-030 S. 16), dort wegen des Ausspeicherns
  100 bar  DBI-Eckparameter Option 2 "multizyklisch" (Q-030, Eckparameter)
   70 bar  geomechanische Untergrenze der Referenzkaverne (Q-028)

Je Szenario und Rate (50.000 / 100.000 Nm³/h):
  Arbeitsgas      Ausspeichern von 210 bar bis p_min (kb.kavernenzyklus, nur Abschnitt "aus",
                  wie Schritt 03), Anteil am Gesamtinhalt bei 210 bar (isotherm, Schritt 05)
  Kopf Einspeichern   Strategie Schritt 07/08: bis 155 bar gasförmig mit 40 °C am Kopf
                  (S1 vorwärmen + Ventil, S2 nur verdichten), ab 160 bar dicht
                  (S1 Ventil bzw. Pumpe, S2 Pfad B mit Ventil bzw. Pumpe)
  Kopf Ausspeichern   kb.strang_aufwaerts mit der Kaverne am Ende des Ausspeicherns, dazu die
                  Grenzen des zweiphasigen Strangs aus Schritt 04 (bohrlochkopf.json)
  Stillstand      Kopf der ruhenden Säule bei p_min (kb.kopfdruck, Gebirgstemperatur, 10 °C oben)
  Vorwärmer S1    größte Leistung beim Einspeichern (bei p_min), Kopf 40 °C
Braucht vorher: Schritte 03, 04, 05, 07. Ausgabe: mindestdruck_szenarien.json.
"""
import json
import sys
from pathlib import Path

from CoolProp.CoolProp import PropsSI

ORDNER = Path(__file__).resolve().parent
sys.path.insert(0, str(ORDNER.parent / "Grundlagen"))
import kaverne_bausteine as kb   # noqa: E402

eb = kb.eb
MED, KAV = kb.REIN, kb.TIEF
RATEN = kb.raten(MED)
de = kb.de
P_MIN = {"160 bar (DBI, Q-030 S. 16)": 160.0, "100 bar (DBI multizyklisch, Q-030)": 100.0,
         "70 bar (Q-028)": 70.0}
S = json.load(open(ORDNER / "einspeicherstrategie.json", encoding="utf-8"))
BK = json.load(open(ORDNER / "bohrlochkopf.json", encoding="utf-8"))
AG = json.load(open(ORDNER / "arbeitsgas.json", encoding="utf-8"))
TGV = AG["TGV"]
p_s = lambda T: PropsSI("P", "T", T + 273.15, "Q", 0, "CO2") / 1e5


def kopf_ein(r, sz, p_min):
    """Kopfzustände beim Einspeichern von p_min bis 210 bar (Regel aus Schritt 08)."""
    t = S["tabelle"][r]
    gas = [(x["p_kopf"], 40.0) for x in t["S2"]["neu"]
           if x["art"].startswith("gas") and p_min <= x["p_lccs"] <= 155]
    dicht = [(x["p_kopf"], x["T_kopf"]) for x in t[sz]["neu"] if x["p_lccs"] >= max(160, p_min)]
    alle = gas + dicht
    return dict(p_min=min(p for p, _ in alle), p_max=max(p for p, _ in alle),
                gasfoermig=bool(gas), dicht_ab=max(160, p_min))


def vorwaermer_S1(r, p_min):
    """Vorwärmleistung S1 [MW] beim Einspeichern bei p_min (Kopf 40 °C), 0 wenn dicht."""
    if p_min > 155:
        return 0.0
    e = kb.einspeisen_strategie(MED, KAV, max(p_min, 72.7), "S2", RATEN[r], S["tabelle"][r]["S2"]["h_auslegung"])
    k = e["kopf"]
    h_k = PropsSI("H", "P", k["p"] * 1e5, "T", k["T"] + 273.15, "CO2") / 1000
    return RATEN[r] * (h_k - MED.h(eb.p_S1, eb.T_S1)) / 1000


erg = {}
for name, pm in P_MIN.items():
    erg[name] = {}
    p_still = kb.kopfdruck(MED, KAV, pm)
    T0 = kb.T_gebirge(0.0)
    still = dict(p=p_still, T=T0, abstand_bar=p_still - p_s(T0))
    for r, md in RATEN.items():
        vl = kb.kavernenzyklus(MED, KAV, md, phasen=[("aus", pm)])
        kw = kb.zyklus_kennwerte(vl)[0]
        wgv = kw["m_start"] - kw["m_ende"]
        _, k_aus = kb.strang_aufwaerts(MED, KAV, kw["p_lccs_ende"], kw["T_ende"], md)
        sz2 = BK["ausspeisen"][r]["strang_zweiphasig"]
        zw_von, zw_bis = sz2["p_lccs_oben"], sz2["p_lccs_unten"]
        zw_aus = zw_von is not None and pm < zw_von
        erg[name][r] = dict(
            p_min=pm, WGV_t=wgv, anteil=wgv / TGV, dauer_aus_d=kw["dauer"], T_kav_ende=kw["T_ende"],
            kopf_aus_ende=dict(p=k_aus["p"], T=k_aus["T"], q=k_aus["q"]),
            strang_zweiphasig_aus=zw_aus,
            zweiphasig_von_bis=(zw_von, max(pm, zw_bis) if zw_bis is not None else pm) if zw_aus else None,
            kopf_ein={sz: kopf_ein(r, sz, pm) for sz in ("S1", "S2")},
            vorwaermer_S1_MW=vorwaermer_S1(r, pm), stillstand=still)
        e = erg[name][r]
        print(f"{name:<36} {r}: Arbeitsgas {e['WGV_t'] / 1000:6.1f} kt ({100 * e['anteil']:4.1f} %), "
              f"Ausspeichern {de(e['dauer_aus_d'])} d, Kaverne am Ende {de(e['T_kav_ende'])} °C | "
              f"Kopf aus Ende {de(k_aus['p'])} bar / {de(k_aus['T'])} °C {'2ph' if k_aus['q'] is not None else ''}, "
              f"Strang zweiphasig beim Aus: {e['zweiphasig_von_bis']} | "
              f"Kopf ein S1 {de(e['kopf_ein']['S1']['p_min'])} bis {de(e['kopf_ein']['S1']['p_max'])} bar, "
              f"S2 {de(e['kopf_ein']['S2']['p_min'])} bis {de(e['kopf_ein']['S2']['p_max'])} bar, "
              f"gasförmig: {e['kopf_ein']['S1']['gasfoermig']} | Vorwärmer S1 {de(e['vorwaermer_S1_MW'])} MW | "
              f"Stillstand Kopf {de(p_still)} bar bei {de(T0, 0)} °C ({de(still['abstand_bar'])} bar über Siededruck)")

kb.speichere_json(ORDNER, "mindestdruck_szenarien.json", dict(
    erzeugt_von="09_mindestdruck_szenarien.py", stand="09.11.2026", TGV_t=TGV, szenarien=erg))
