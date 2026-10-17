# -*- coding: utf-8 -*-
"""
Kaverne Schritt 02 - Arbeitsgas, Kissengas und die Frage nach der Teufe (reines CO₂)
============================================================================
Wie viel CO₂ lässt sich zwischen p_max und p_min wirklich umschlagen - und
warum hängt das bei CO₂ so stark von der Teufe ab?

Massenbilanz wie DBI (Q-030 Kap. 1.3):  m = ρ(p, T) · V
  TGV  Gesamtinhalt bei p_max          (Total Gas Volume)
  CGV  Inhalt bei p_min = Kissengas    (Cushion Gas Volume)
  WGV  TGV - CGV = Arbeitsgas          (Working Gas Volume)
Nicht über das Druckverhältnis rechnen - ρ ist nahe dem kritischen Punkt
stark nichtlinear (Q-028 Kap. 5).

Zwei Grenzfälle für den Inhalt bei p_min:
  langsam / isotherm   Gebirge heizt nach, Kaverne bleibt auf Gebirgstemperatur
                       -> obere Schranke für das Arbeitsgas
  schnell / isentrop   keine Wärmezufuhr, Inhalt entspannt adiabat-reversibel
                       -> untere Schranke; zeigt, ob die Kaverne zweiphasig wird
Der echte Wert hängt von der Rate ab -> Schritt 03 (Kavernenbilanz).

Varianten für p_min (alle an der LCCS):
  geomechanisch   p_min der Kaverne (70 bzw. 40,8 bar)
  überkritisch    p_krit: die Kaverne bleibt überkritisch (Q-003 Kap. 4.2)
  Bohrloch dicht  Grenzfall aus 01: Kopf bleibt im Stillstand über p_krit
                  (vgl. Q-030 "Option 2 adjusted": p_min 160 bar)

Teufenfenster (analytisch, statt Teufe Meter für Meter zu scannen):
  untere Grenze   Gebirge in der Bezugsteufe ≥ T_krit + 3 K, sonst Flüssigphase in
                  der Kaverne beim Abkühlen (Q-028 Kap. 5, Q-030 Option 3)
  obere Grenze    p_min an der LCCS < p_krit, sonst bleibt der Inhalt immer
                  überkritisch und dicht - das Arbeitsgas liegt dann nur im
                  flachen Teil der Dichtekurve (Q-028 Kap. 5: "deep CO₂ caverns
                  do not lead to a further increase of the storage content")

Ausgabe: Konsole, abb_K02_arbeitsgas.png, arbeitsgas.json (-> 03, 05)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import kaverne_bausteine as kb

MED = kb.REIN
T_MARGE = 3.0      # K über T_krit in Kavernenmitte (Sicherheitsabstand, eigene Annahme wie Kavernenrechner)
stillstand = kb.lade_json("kaverne_stillstand.json", "01_kavernen_tief_flach_stillstand.py")

# ---- 0) Stoffdaten-Kontrolle gegen DBI (Q-030 Tab. 3) ---------------------------
# (Option, p [bar], T [°C], ρ DBI [kg/m³]); Option 2 entspricht der tiefen Kaverne
DBI = [("Option 2", 240, 50, 825.637), ("Option 2", 160, 50, 722.101), ("Option 2", 100, 50, 384.334),
       ("Option 2", 55, 50, 119.482), ("Option 1", 260, 84, 677.684), ("Option 1", 70, 84, 131.309),
       ("Option 3", 50, 33, 120.816), ("Option 3", 40, 33, 87.986)]
print("Kontrolle Dichte CoolProp gegen DBI (Q-030 Tab. 3):")
for opt, p, T, r in DBI:
    rc = PropsSI("D", "P", p * 1e5, "T", T + 273.15, "CO2")
    print(f"  {opt} {p:3d} bar / {T} °C: DBI {r:7.1f}, CoolProp {rc:7.1f} kg/m³ ({100 * (rc / r - 1):+.2f} %)")
print("  -> Option 2 (= tiefe Kaverne) exakt; Abweichungen bei 84 °C / 33 °C vermutlich andere"
      " T-Rundung bei DBI (nahe T_krit reagiert ρ stark auf T).")


# ---- 1) Inhalt bei p_min: isotherm und isentrop -----------------------------------
def inhalt_isentrop(kav, p_lccs_min):
    """Kaverneninhalt [t], T und Dampfanteil nach isentroper Entspannung von voll auf p_min."""
    T0 = kav.T_mitte
    pm0 = kb.p_mitte(MED, kav, kav.p_max, T0)
    s = PropsSI("S", "P", pm0 * 1e5, "T", T0 + 273.15, "CO2")
    pm = p_lccs_min + 2.0          # nicht genau auf p_krit starten - dort scheitert der PS-Flash
    for _ in range(8):     # Druck in Kavernenmitte mit der Dichte des entspannten Inhalts
        rho = PropsSI("D", "P", pm * 1e5, "S", s, "CO2")
        pm = p_lccs_min + rho * kb.G * (kav.z_mitte - kav.z_lccs) / 1e5
    T = PropsSI("T", "P", pm * 1e5, "S", s, "CO2") - 273.15
    q = PropsSI("Q", "P", pm * 1e5, "S", s, "CO2")
    return rho * kav.volumen / 1000, T, (q if 0 <= q <= 1 else None)


erg = {}
for kav in kb.KAVERNEN:
    TGV = kb.inventar(MED, kav, kav.p_max)
    varianten = [("geomechanisch", kav.p_min), ("überkritisch", kb.P_KRIT)]
    pg = stillstand[kav.kurz]["p_lccs_grenzfall"]
    if pg is not None and kav.p_min < pg < kav.p_max:
        varianten.append(("Bohrloch dicht", pg))
    zeilen = []
    for name, pmin in varianten:
        if not kav.p_min <= pmin < kav.p_max:
            continue
        CGV_iso = kb.inventar(MED, kav, pmin)
        CGV_ise, T_ise, q_ise = inhalt_isentrop(kav, pmin)
        zeilen.append(dict(variante=name, p_min=pmin, CGV_iso=CGV_iso, CGV_ise=CGV_ise, T_ise=T_ise, q_ise=q_ise,
                           WGV_iso=TGV - CGV_iso, WGV_ise=TGV - CGV_ise,
                           anteil_iso=(TGV - CGV_iso) / TGV, anteil_ise=(TGV - CGV_ise) / TGV))
    erg[kav.kurz] = dict(kav=kav, TGV=TGV, zeilen=zeilen)

# ---- 2) Teufenfenster --------------------------------------------------------------
z_mitte_min = (kb.T_KRIT + T_MARGE - kb.T_OBERFLAECHE) / kb.GRADIENT
z_lccs_max = kb.P_KRIT / kb.GRAD_PMIN

def tsd(x):
    """Tausenderpunkt: 201449 -> '201.449'."""
    return f"{x:,.0f}".replace(",", ".")


# ---- 3) Konsole ----------------------------------------------------------------------
for kurz, e in erg.items():
    kav = e["kav"]
    print(f"\n==== {kav.name}: TGV {tsd(e['TGV'])} t bei {kav.p_max:.1f} bar / {kav.T_mitte:.1f} °C ====")
    print(f"  {'p_min':<16}{'bar':>7} | {'langsam (isotherm)':^27} | {'schnell (isentrop)':^40}")
    for z in e["zeilen"]:
        zp = f", ZWEIPHASIG q = {z['q_ise']:.2f}" if z["q_ise"] is not None else ""
        print(f"  {z['variante']:<16}{z['p_min']:7.1f} | WGV {tsd(z['WGV_iso']):>8} t = {100*z['anteil_iso']:4.1f} % | "
              f"WGV {tsd(z['WGV_ise']):>8} t = {100*z['anteil_ise']:4.1f} %, T {z['T_ise']:5.1f} °C{zp}")
z_lccs_min = z_mitte_min - kb.DZ_BEZUG
print("\nTeufenfenster (Gradienten wie Kaverne V1, Gebirge 10 °C + 0,03 K/m, Geometrie wie Q-028):")
print(f"  Bezugsteufe ≥ {z_mitte_min:.0f} m, also LCCS ≥ {z_lccs_min:.0f} m "
      f"(Gebirge ≥ T_krit + {T_MARGE:.0f} K: keine Flüssigphase in der ruhenden Kaverne)")
print(f"  LCCS ≤ {z_lccs_max:.0f} m (p_min < p_krit: Arbeitsgas reicht in den steilen Teil der Dichtekurve)")
for kav in kb.KAVERNEN:
    print(f"  {kav.name}: LCCS {kav.z_lccs:.0f} m {kb.ok(z_lccs_min <= kav.z_lccs <= z_lccs_max)} "
          f"- {kav.z_lccs - z_lccs_min:.0f} m über der Temperaturgrenze, {z_lccs_max - kav.z_lccs:.0f} m unter "
          f"der Druckgrenze; Gebirge {kav.T_mitte - kb.T_KRIT:+.1f} K zu T_krit")
print("  Das Fenster gilt für die RUHENDE Kaverne. Beim Ausspeichern kühlt der Inhalt ab - wie weit,")
print("  hängt von der Rate ab (Schritt 03). Je näher die Kaverne an der Temperaturgrenze liegt,")
print("  desto kleiner ist die Rate, bei der sie noch einphasig bleibt.")

# ---- 4) Abbildung: Dichte über Druck und Arbeitsgas -----------------------------------
FARBE = {"tief": "#00304F", "flach": "#EE7203"}
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.5, 6), gridspec_kw=dict(width_ratios=[1.3, 1]))
pp = np.linspace(20, 230, 300)
for kurz, e in erg.items():
    kav = e["kav"]
    T = kav.T_mitte
    ax.plot(pp, [MED.rho(p, T) for p in pp], color=FARBE[kurz], lw=1.2, alpha=0.5)
    pw = np.linspace(kav.p_min, kav.p_max, 120)
    pm = [kb.p_mitte(MED, kav, p, T) for p in pw]
    ax.plot(pm, [MED.rho(p, T) for p in pm], color=FARBE[kurz], lw=3.5,
            label=f"{kurz}: {kb.de(T)} °C, Fenster {kb.de(kav.p_min)}-{kb.de(kav.p_max)} bar (LCCS)")
ax.axvline(kb.P_KRIT, color="#888", ls=":", lw=1.2)
ax.text(kb.P_KRIT + 2, 30, "p_krit", color="#666", fontsize=8.5)
ax.set(xlabel="Druck in Kavernenmitte [bar]", ylabel="Dichte [kg/m³]", xlim=(20, 230), ylim=(0, 950),
       title="Dichte über Druck bei Gebirgstemperatur (dick = Betriebsfenster)")
ax.text(128, 280, "Arbeitsgas = Dichteunterschied über das Fenster\n"
        "steil nur im Übergang gasförmig ↔ überkritisch (Q-028)", fontsize=8.5, color="#444")
ax.grid(alpha=0.3)
ax.legend(fontsize=8, loc="lower right")

namen, wgv_iso, wgv_ise, cgv = [], [], [], []
for kurz, e in erg.items():
    for z in e["zeilen"]:
        namen.append(f"{kurz}\n{z['variante']}\n{kb.de(z['p_min'])} bar")
        wgv_iso.append(100 * z["anteil_iso"])
        wgv_ise.append(100 * z["anteil_ise"])
x = np.arange(len(namen))
ax2.bar(x - 0.2, wgv_iso, 0.4, color="#007335", alpha=0.8, label="langsam / isotherm (obere Schranke)")
ax2.bar(x + 0.2, wgv_ise, 0.4, color="#0476D9", alpha=0.8, label="schnell / isentrop (untere Schranke)")
for xi, a, b in zip(x, wgv_iso, wgv_ise):
    ax2.text(xi - 0.2, a + 1, f"{a:.0f}", ha="center", fontsize=8)
    ax2.text(xi + 0.2, b + 1, f"{b:.0f}", ha="center", fontsize=8)
ax2.axhspan(22, 32, color="#999", alpha=0.2)
ax2.text(x[-1] + 0.45, 27, "Q-028\n22-32 %", fontsize=7.5, color="#555", va="center")
ax2.set_xticks(x)
ax2.set_xticklabels(namen, fontsize=7.5)
ax2.set(ylabel="Arbeitsgasanteil WGV/TGV [%]", ylim=(0, 118), title="Arbeitsgas je Mindestdruck")
ax2.grid(alpha=0.3, axis="y")
ax2.legend(fontsize=8, loc="upper right")
fig.suptitle("Arbeitsgas reines CO₂ - Kaverne tief und flach (V = 650.000 m³)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(kb.ORDNER / "abb_K02_arbeitsgas.png", dpi=160)
print("\ngespeichert: abb_K02_arbeitsgas.png")

kb.speichere_json("arbeitsgas.json", dict(
    teufenfenster=dict(z_bezug_min=z_mitte_min, z_lccs_min=z_lccs_min, z_lccs_max=z_lccs_max, T_marge=T_MARGE),
    **{kurz: dict(TGV=e["TGV"], varianten=e["zeilen"]) for kurz, e in erg.items()}))
