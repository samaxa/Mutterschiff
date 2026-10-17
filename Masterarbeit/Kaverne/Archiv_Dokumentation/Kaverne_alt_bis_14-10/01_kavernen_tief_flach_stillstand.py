# -*- coding: utf-8 -*-
"""
Kaverne Schritt 01 - tiefe und flache Kaverne im Stillstand (reines CO₂)
============================================================================
Was liegt in Kaverne und Bohrloch vor, wenn nichts strömt? Gerechnet für die
beiden Kavernen aus kaverne_bausteine.py:

  tief  (V1)  LCCS 1200 m, 210 / 70 bar   = Kaverne der Einspeicherung
  flach (V2)  LCCS  700 m, 122,5 / 40,8 bar (Q-030 Option 3: 125 / 40 bar)

Je Kaverne drei Füllstände nach Buzogany & Kruck (2022, Q-028, Fig. 3):
  voll        p_max an der LCCS
  Grenzfall   Kopfdruck = kritischer Druck: darüber bleibt das ganze Bohrloch
              über p_krit, darunter wechselt das CO₂ im Bohrloch die Phase
  leer        p_min an der LCCS

Ergebnis für die Obertageanlage:
  - Kopfdruck "voll" = Zieldruck der Einspeicherung (Pumpe/Verdichter);
    Kontrolle: tief/voll muss 107,60 bar ergeben (Einspeicherung S1/S2)
  - Kopfdruck "leer" = niedrigster Kopfdruck, mit dem die Ausspeicherung
    im Stillstand startet
  - Phasenlage in Kaverne und Bohrloch (Q-028 Kap. 3: hoher, mittlerer,
    niedriger Druckbereich)

NUR STILLSTAND: ruhendes CO₂ mit Gebirgstemperatur. Strömung, Abkühlung beim
Ausspeichern und Reibung kommen in 03 (Kaverne) und 04 (Förderstrang).
Ersetzt Kaverne_Version1/Stillstand_gassaeule_Kaverne_Version1.py (bleibt als
Archiv liegen; gleiche Rechnung, jetzt für beide Kavernen).

Ausgabe: Konsole, abb_K01_gassaeulen.png, abb_K01_betriebsfenster_pT.png,
kaverne_stillstand.json (-> 02, 04, Einspeicherung)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

import kaverne_bausteine as kb

MED = kb.REIN
RHO_GEBIRGE = 2200.0     # kg/m³, mittlere Gebirgsdichte (Q-003 Kap. 4.2) - nur zur Einordnung
Z_KRIT = (kb.T_KRIT - kb.T_OBERFLAECHE) / kb.GRADIENT     # Teufe, in der das Gebirge T_krit hat


def nassdampf(profil, tol=0.003):
    """True, wo die ruhende Säule auf der Siedelinie liegt (Dichte durch p, T nicht bestimmt)."""
    maske = []
    for z, p, T, rho in profil:
        if T >= kb.T_KRIT:
            maske.append(False)
            continue
        ps = PropsSI("P", "T", T + 273.15, "Q", 0, "CO2") / 1e5
        maske.append(abs(p - ps) / ps < tol)
    return np.array(maske)


def phasenwechsel(profil):
    """Teufen, in denen T bzw. p den kritischen Wert kreuzen (von unten nach oben)."""
    z, p, T = profil[:, 0], profil[:, 1], profil[:, 2]
    z_T = z[np.argmax(T >= kb.T_KRIT)] if np.any(T >= kb.T_KRIT) and np.any(T < kb.T_KRIT) else None
    z_p = None
    if np.any(p >= kb.P_KRIT) and np.any(p < kb.P_KRIT):
        z_p = float(np.interp(kb.P_KRIT, p, z))      # p steigt mit z monoton
    return z_T, z_p


# ---- 1) Rechnen ---------------------------------------------------------------
erg = {}
for kav in kb.KAVERNEN:
    p_lith = RHO_GEBIRGE * kb.G * kav.z_lccs / 1e5
    try:
        p_grenz = kb.p_lccs_fuer_kopf(MED, kav, kb.P_KRIT)
    except RuntimeError:
        p_grenz = np.nan
    faelle = [("voll", kav.p_max), ("leer", kav.p_min)]
    if kav.p_min < p_grenz < kav.p_max:
        faelle.insert(1, ("Grenzfall", p_grenz))
    saeulen = {}
    for name, pl in faelle:
        p_kopf, profil = kb.gassaeule(MED, kav, pl)
        z_T, z_p = phasenwechsel(profil)
        nd = nassdampf(profil)
        T_m = kav.T_mitte
        pm = kb.p_mitte(MED, kav, pl, T_m)
        saeulen[name] = dict(p_lccs=pl, p_kopf=p_kopf, profil=profil, z_T_krit=z_T, z_p_krit=z_p,
                             nassdampf=(float(profil[nd, 0].min()), float(profil[nd, 0].max())) if nd.any() else None,
                             p_mitte=pm, rho_kaverne=MED.rho(pm, T_m), phase_kaverne=MED.phase(pm, T_m),
                             phase_kopf=MED.phase(p_kopf, kb.T_OBERFLAECHE))
    erg[kav.kurz] = dict(kav=kav, p_lith=p_lith, p_grenz=p_grenz, saeulen=saeulen)

# ---- 2) Konsole -----------------------------------------------------------------
print(f"Gebirge {kb.T_OBERFLAECHE:.0f} °C + {kb.GRADIENT} K/m -> T_krit ({kb.T_KRIT:.2f} °C) in {Z_KRIT:.0f} m Teufe")
for kurz, e in erg.items():
    kav = e["kav"]
    print(f"\n==== {kav.name} ====")
    print(f"LCCS {kav.z_lccs:.0f} m ({kav.T_lccs:.1f} °C), Bezugsteufe Kaverneninhalt {kav.z_mitte:.0f} m ({kav.T_mitte:.1f} °C), "
          f"V = {kav.volumen/1e3:.0f}·10³ m³")
    print(f"p_max {kav.p_max:.1f} bar = {kav.p_max/e['p_lith']:.2f}·Gebirgsdruck ({e['p_lith']:.0f} bar bei 2200 kg/m³), "
          f"p_min {kav.p_min:.1f} bar")
    print(f"Gebirge in der Bezugsteufe {kav.T_mitte - kb.T_KRIT:+.1f} K zur kritischen Temperatur")
    for name, s in e["saeulen"].items():
        txt = f"  {name:<9} LCCS {s['p_lccs']:6.1f} bar -> Kopf {s['p_kopf']:6.2f} bar ({s['phase_kopf']}); "
        txt += f"Kaverne {s['p_mitte']:.1f} bar / {kav.T_mitte:.1f} °C: {s['phase_kaverne']}, ρ = {s['rho_kaverne']:.0f} kg/m³"
        print(txt)
        if s["z_p_krit"] is not None and s["z_p_krit"] > 5:
            print(f"            Druck unterschreitet p_krit oberhalb {s['z_p_krit']:.0f} m")
        if s["nassdampf"]:
            print(f"            Nassdampfgebiet (auf der Siedelinie) {s['nassdampf'][0]:.0f}-{s['nassdampf'][1]:.0f} m")
    if np.isnan(e["p_grenz"]) or e["p_grenz"] >= kav.p_max:
        print(f"  Grenzfall: Kopf = p_krit bräuchte {e['p_grenz']:.0f} bar an der LCCS > p_max -> "
              "Kopf im Stillstand IMMER unterkritisch, Phasenwechsel im Bohrloch in jedem Füllstand")
    else:
        print(f"  Grenzfall: Kopf = p_krit bei {e['p_grenz']:.1f} bar an der LCCS")

p_v1 = erg["tief"]["saeulen"]["voll"]["p_kopf"]
print(f"\nKontrolle gegen die Einspeicherung (Dokumentation S1/S2): Kopfdruck tief/voll 107,60 bar -> "
      f"{p_v1:.2f} bar {kb.ok(abs(p_v1 - 107.60) < 0.02)}")

# ---- 3) Abbildung 1: Gassäulen (Darstellung nach Q-028, Fig. 3) ---------------
FARBE = {"tief": "#00304F", "flach": "#EE7203"}
STIL = {"voll": "-", "Grenzfall": "--", "leer": ":"}
fig, axs = plt.subplots(1, 3, figsize=(13, 6.5), sharey=True)
z_t = np.linspace(0, kb.TIEF.z_lccs, 50)
axs[0].plot(kb.T_gebirge(z_t), z_t, color="#333333", lw=2)
axs[0].axvline(kb.T_KRIT, color="#CA220E", ls="--", lw=1.1)
axs[0].axhline(Z_KRIT, color="#CA220E", ls=":", lw=0.9)
axs[0].text(kb.T_KRIT + 1, Z_KRIT - 20, f"T_krit in {Z_KRIT:.0f} m", fontsize=8.5, color="#CA220E")
axs[0].set_title("Gebirgstemperatur [°C]")
for kurz, e in erg.items():
    kav = e["kav"]
    for a in axs:
        a.axhline(kav.z_lccs, color=FARBE[kurz], lw=0.8, alpha=0.5)
    axs[0].text(1, kav.z_lccs - 15, f"LCCS {kav.kurz} {kav.z_lccs:.0f} m", fontsize=8, color=FARBE[kurz])
    for name, s in e["saeulen"].items():
        pr = s["profil"]
        lbl = f"{kurz}, {name}: Kopf {kb.de(s['p_kopf'])} bar"
        axs[1].plot(pr[:, 1], pr[:, 0], color=FARBE[kurz], ls=STIL[name], lw=2, label=lbl)
        rho = pr[:, 3].copy()
        rho[nassdampf(pr)] = np.nan          # Dichte auf der Siedelinie nicht bestimmt -> Lücke
        axs[2].plot(rho, pr[:, 0], color=FARBE[kurz], ls=STIL[name], lw=2)
axs[1].axvline(kb.P_KRIT, color="#888", ls=":", lw=1.2)
axs[1].text(kb.P_KRIT + 2, 1150, f"p_krit {kb.de(kb.P_KRIT)} bar", fontsize=8.5, color="#666", rotation=90)
axs[1].set_title("Druck [bar]")
axs[2].set_title("Dichte [kg/m³] (Lücke = Nassdampf)")
axs[1].legend(fontsize=7.5, loc="lower left")
axs[0].set_ylabel("Teufe [m]")
axs[0].set_ylim(kb.TIEF.z_lccs * 1.03, 0)
axs[0].set_xlim(0, 60)
axs[1].set_xlim(0, 230)
axs[2].set_xlim(0, 1000)
for a in axs:
    a.grid(alpha=0.3)
fig.suptitle("Gassäulen im Stillstand - Kaverne tief (1200 m) und flach (700 m), reines CO₂\n"
             "Darstellung nach Buzogany & Kruck (2022), Fig. 3", fontsize=11)
fig.text(0.5, 0.01, "NUR STILLSTAND: ruhendes CO₂ mit Gebirgstemperatur. Strömung, Abkühlung und Reibung: Schritte 03 und 04.",
         ha="center", fontsize=8.5, color="#9C0006", weight="bold")
fig.tight_layout(rect=[0, 0.03, 1, 0.93])
fig.savefig(kb.ORDNER / "abb_K01_gassaeulen.png", dpi=160)
print("\ngespeichert: abb_K01_gassaeulen.png")

# ---- 4) Abbildung 2: Betriebsfenster im p-T-Diagramm ---------------------------
T_s = np.linspace(PropsSI("Ttriple", "CO2"), PropsSI("Tcrit", "CO2"), 200)
p_s = np.array([PropsSI("P", "T", T, "Q", 0, "CO2") for T in T_s]) / 1e5
fig, ax = plt.subplots(figsize=(10.5, 6.8))
ax.fill_between([kb.T_KRIT, 70], kb.P_KRIT, 240, color="#FCE5CD", zorder=0)
ax.fill_between(T_s - 273.15, p_s, 240, color="#D9EAD3", zorder=0)
ax.plot(T_s - 273.15, p_s, color="#1F4E79", lw=1.8, label="Sättigungslinie")
ax.plot(kb.T_KRIT, kb.P_KRIT, "o", color="#CA220E", ms=7, label="kritischer Punkt")
for kurz, e in erg.items():
    kav = e["kav"]
    for name, s in e["saeulen"].items():
        pr = s["profil"]
        ax.plot(pr[:, 2], pr[:, 1], color=FARBE[kurz], ls=STIL[name], lw=1.8,
                label=f"Säule {kurz}, {name}" if name != "Grenzfall" else None)
    ax.plot([kav.T_lccs] * 2, [kav.p_min, kav.p_max], color=FARBE[kurz], lw=6, alpha=0.8, solid_capstyle="butt",
            label=f"{kav.name}: {kb.de(kav.p_min)}-{kb.de(kav.p_max)} bar an der LCCS")
    ks = [s["p_kopf"] for s in e["saeulen"].values()]
    ax.plot([kb.T_OBERFLAECHE] * 2, [min(ks), max(ks)], color=FARBE[kurz], lw=6, alpha=0.35, solid_capstyle="butt")
    ax.text(kav.T_lccs + 1.2, kav.p_max, f"{kurz} voll", fontsize=8, color=FARBE[kurz], va="center")
    ax.text(kav.T_lccs + 1.2, kav.p_min, f"{kurz} leer", fontsize=8, color=FARBE[kurz], va="center")
ax.text(kb.T_OBERFLAECHE - 1, 5, "Bohrlochkopf\n(10 °C)", fontsize=8, ha="right", color="#555")
big = dict(fontsize=11, weight="bold", color="#7F7F7F", ha="center")
ax.text(0, 110, "flüssig", **big)
ax.text(60, 200, "überkritisch", **big)
ax.text(55, 30, "gasförmig", **big)
ax.set(xlim=(-10, 70), ylim=(0, 240), xlabel="Temperatur [°C]", ylabel="Druck [bar]",
       title="Betriebsfenster im Stillstand: Säulen von der LCCS (Balken rechts) bis zum Kopf (Balken links)")
ax.grid(alpha=0.3)
ax.legend(fontsize=7.5, loc="upper left")
fig.tight_layout()
fig.savefig(kb.ORDNER / "abb_K01_betriebsfenster_pT.png", dpi=160)
print("gespeichert: abb_K01_betriebsfenster_pT.png")

# ---- 5) Übergabe an die folgenden Schritte ---------------------------------------
kb.speichere_json("kaverne_stillstand.json", {
    kurz: dict(name=e["kav"].name, z_lccs=e["kav"].z_lccs, z_mitte=e["kav"].z_mitte,
               T_lccs=e["kav"].T_lccs, T_mitte=e["kav"].T_mitte, p_max=e["kav"].p_max, p_min=e["kav"].p_min,
               volumen=e["kav"].volumen, p_lccs_grenzfall=e["p_grenz"],
               saeulen={n: {k: v for k, v in s.items() if k != "profil"} for n, s in e["saeulen"].items()})
    for kurz, e in erg.items()})
