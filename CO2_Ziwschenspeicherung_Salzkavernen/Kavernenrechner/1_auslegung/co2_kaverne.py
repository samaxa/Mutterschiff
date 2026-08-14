# -*- coding: utf-8 -*-
"""
CO2-Speicherung in Salzkavernen - Thermodynamische Auslegungsrechnung
=====================================================================
Berechnet Gassaeule, Teufenprofile, Arbeitsgas und Prozesspfade fuer den
Ein- und Ausspeicherpfad. Alle Stoffdaten live aus CoolProp (Span-Wagner).

Konzept/Randbedingungen nach: Buzogany, R. & Kruck, O. (2022):
  CO2 - Storage in Salt Caverns, SMRI Fall 2022 Technical Conference.
Berechnung und Zahlenwerte eigenstaendig.

Aufruf:  python co2_kaverne.py
Ausgabe: PNG-Abbildungen + Konsolenreport (+ optional Excel)
"""
from CoolProp.CoolProp import PropsSI, PhaseSI
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch

# =====================================================================
# KONFIGURATION - hier alles anpassen, der Rest rechnet sich neu
# =====================================================================
CFG = dict(
    # --- Kaverne / Geologie ---
    teufe            = 1200.0,   # m, Teufe LCCS / Kaverne
    T_oberflaeche    = 10.0,     # degC, ungestoerte GEBIRGStemperatur an der Oberflaeche
                                 # 10 degC = Annahme der Quelle (Buzogany & Kruck);
                                 # reproduziert deren kritische Teufe (699 m ggue. 725 m)
    geo_gradient     = 0.03,     # K/m, geothermischer Gradient
    volumen          = 650000.0, # m3, speicherwirksames Kavernenvolumen
    rho_salz         = 2200.0,   # kg/m3, fuer lithostatischen Druck
    p_max            = 210.0,    # bar, Maximaldruck an der LCCS
    p_min_geomech    = 70.0,     # bar, geomechanisches Minimum

    # --- Schnittstelle Pipeline (OGE) ---
    p_anlieferung    = 85.0,     # bar, dichte Phase
    T_anlieferung    = 15.0,     # degC, MEDIUMtemperatur (unabhaengig von T_oberflaeche!)
    T_spec_min       = 5.0,      # degC, Spezifikationsfenster
    T_spec_max       = 25.0,     # degC
    p_spec_min       = 80.0,     # bar
    p_spec_max       = 90.0,     # bar

    # --- Betrieb ---
    V_norm_min       = 50000.0,  # Nm3/h
    V_norm_max       = 100000.0, # Nm3/h
    eta_isentrop     = 0.80,     # - , Pumpe/Verdichter
    p_kopf_aus       = 120.0,    # bar, Bohrlochkopf beim Ausspeichern
    n_schritte       = 24,       # Tiefenschritte fuer Tabellen
    n_schritte_fein  = 600,     # fuer die Iteration (600 reicht: Abw. < 0,01 bar ggue. 2400)
)
G = 9.81
FLUID = "CO2"
TC = PropsSI("Tcrit", FLUID) - 273.15     # 31.0 degC
PC = PropsSI("pcrit", FLUID) / 1e5        # 73.8 bar
P_TRIPEL = PropsSI("ptriple", FLUID) / 1e5
T_TRIPEL = PropsSI("Ttriple", FLUID) - 273.15

# =====================================================================
# GRUNDFUNKTIONEN
# =====================================================================
def T_gebirge(z, c=CFG):
    """Geologisches Temperaturprofil [degC] in Teufe z [m]."""
    return c["T_oberflaeche"] + c["geo_gradient"] * z

def dichte(p_bar, T_c, fluid=FLUID):
    """Dichte [kg/m3] mit expliziter Phasenwahl; robust an der Siedelinie."""
    T = T_c + 273.15
    p = p_bar * 1e5
    Tk = PropsSI("Tcrit", fluid) - 273.15
    if T_c >= Tk:
        return PropsSI("D", "P", p, "T", T, fluid)
    psat = PropsSI("P", "T", T, "Q", 0, fluid)
    if abs(p - psat) / psat < 5e-4:          # praktisch auf der Siedelinie
        return PropsSI("D", "T", T, "Q", 1, fluid)
    return PropsSI("D", "P", p, "T", T, fluid)

def phase(p_bar, T_c, fluid=FLUID):
    """Phasenbezeichnung in Klartext."""
    T = T_c + 273.15; p = p_bar * 1e5
    Tk = PropsSI("Tcrit", fluid) - 273.15
    pk = PropsSI("pcrit", fluid) / 1e5
    if T_c >= Tk:
        return "überkritisch" if p_bar >= pk else "gasförmig"
    psat = PropsSI("P", "T", T, "Q", 0, fluid)
    if p > psat * 1.0005:  return "flüssig"
    if p < psat * 0.9995:  return "gasförmig"
    return "ZWEIPHASIG"

def saeule_abwaerts(p_kopf, c=CFG, n=None, fluid=FLUID):
    """Integriert dp/dz = rho*g von oben nach unten. Gibt Liste von dicts."""
    n = n or c["n_schritte"]
    dz = c["teufe"] / n
    p = p_kopf
    out = []
    for i in range(n + 1):
        z = i * dz
        T = T_gebirge(z, c)
        rho = dichte(p, T, fluid)
        out.append(dict(z=z, T=T, p=p, rho=rho, phase=phase(p, T, fluid)))
        if i < n:
            p += rho * G * dz / 1e5
    return out

def saeule_aufwaerts(p_lccs, c=CFG, n=None, fluid=FLUID):
    """Integriert von der LCCS nach oben. Gibt Liste von oben nach unten sortiert."""
    n = n or c["n_schritte"]
    dz = c["teufe"] / n
    p = p_lccs
    out = []
    for i in range(n + 1):
        z = c["teufe"] - i * dz
        T = T_gebirge(z, c)
        rho = dichte(p, T, fluid)
        out.append(dict(z=z, T=T, p=p, rho=rho, phase=phase(p, T, fluid)))
        if i < n:
            p -= rho * G * dz / 1e5
    return out[::-1]

def _sekante(f, x0, x1, tol=1e-4, maxit=30):
    """Sekantenverfahren mit Bisektions-Absicherung. f muss monoton sein."""
    f0, f1 = f(x0), f(x1)
    for _ in range(maxit):
        if abs(f1) < tol:
            return x1
        if f1 == f0:
            break
        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        x2 = min(max(x2, min(x0, x1) - 50), max(x0, x1) + 50)   # Ausreisser begrenzen
        x0, f0, x1 = x1, f1, x2
        f1 = f(x2)
    return x1

def loese_kopfdruck(p_ziel_unten, c=CFG, fluid=FLUID):
    """Welcher Kopfdruck ergibt unten p_ziel? (Sekantenverfahren)"""
    n = c["n_schritte_fein"]
    f = lambda ph: saeule_abwaerts(ph, c, n, fluid)[-1]["p"] - p_ziel_unten
    # Startschaetzung: p_ziel minus Saeule bei mittlerer Dichte
    rho0 = dichte(p_ziel_unten, T_gebirge(c["teufe"]/2, c), fluid)
    schaetz = p_ziel_unten - rho0 * G * c["teufe"] / 1e5
    schaetz = max(schaetz, 1.0)
    return _sekante(f, schaetz, schaetz * 1.05 + 1.0)

def loese_plccs_fuer_kopfdruck(p_kopf_ziel, c=CFG, fluid=FLUID):
    """Welcher pLCCS ergibt oben p_kopf_ziel? (Sekantenverfahren)"""
    n = c["n_schritte_fein"]
    f = lambda pl: saeule_aufwaerts(pl, c, n, fluid)[0]["p"] - p_kopf_ziel
    rho0 = dichte(p_kopf_ziel * 2, T_gebirge(c["teufe"]/2, c), fluid)
    schaetz = p_kopf_ziel + rho0 * G * c["teufe"] / 1e5
    return _sekante(f, schaetz, schaetz * 1.05)

def massenstrom(V_norm_h):
    """Nm3/h -> kg/s (Normzustand 0 degC, 1,013 bar)."""
    rho_n = PropsSI("D", "P", 101325, "T", 273.15, FLUID)
    return V_norm_h * rho_n / 3600.0

def druckerhoehung(p1, T1, p2, eta=None):
    """Pumpe/Verdichter: gibt (T_aus, spez. Arbeit kJ/kg, Phase)."""
    eta = eta or CFG["eta_isentrop"]
    h1 = PropsSI("H", "P", p1*1e5, "T", T1+273.15, FLUID)
    s1 = PropsSI("S", "P", p1*1e5, "T", T1+273.15, FLUID)
    h2s = PropsSI("H", "P", p2*1e5, "S", s1, FLUID)
    h2 = h1 + (h2s - h1) / eta
    T2 = PropsSI("T", "P", p2*1e5, "H", h2, FLUID) - 273.15
    return T2, (h2 - h1)/1000.0, phase(p2, T2)

def drosselung(p1, T1, p2):
    """Isenthalpe Entspannung: gibt (T_aus, Phase, Dampfanteil oder None)."""
    h = PropsSI("H", "P", p1*1e5, "T", T1+273.15, FLUID)
    T2 = PropsSI("T", "P", p2*1e5, "H", h, FLUID) - 273.15
    ph = phase(p2, T2)
    q = None
    if ph == "ZWEIPHASIG" or (T2 < TC and p2 < PC):
        try:
            qq = PropsSI("Q", "P", p2*1e5, "H", h, FLUID)
            if 0 <= qq <= 1: q = qq; ph = "ZWEIPHASIG"
        except Exception:
            pass
    return T2, ph, q

def inventar(p_bar, T_c, c=CFG):
    """Gespeicherte Masse [kt] bei Druck p und Temperatur T."""
    return dichte(p_bar, T_c) * c["volumen"] / 1e6

def arbeitsgas(p_min, p_max, T_bei_min, T_bei_max, c=CFG):
    """Arbeitsgasanteil [%] und Massen [kt]."""
    m_max = inventar(p_max, T_bei_max, c)
    m_min = inventar(p_min, T_bei_min, c)
    return (m_max - m_min) / m_max * 100.0, m_max - m_min, m_min

# =====================================================================
# ABBILDUNGEN
# =====================================================================
FARBE = dict(dicht="#1D7A5F", gas="#D2691E", grenz="#1F5FA5",
             kaverne="#7A9A3C", gebirge="#C9BFA8", warn="#B22222", grau="#5F5E5A")

def abb_kavernenschema(erg, datei="abb1_kavernenschema.png", c=CFG):
    """Schematische Kaverne mit allen berechneten Betriebsdaten."""
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.5, 8.5),
                                  gridspec_kw=dict(width_ratios=[1.55, 1]))
    tf = c["teufe"]
    # --- Gebirge ---
    ax.add_patch(Rectangle((-1.0, 0), 2.0, tf*1.28, color=FARBE["gebirge"], alpha=.35, zorder=0))
    ax.axhline(0, color="k", lw=1.4, zorder=3)
    for x in np.linspace(-0.95, 0.95, 26):
        ax.plot([x, x-0.05], [-14, -34], color="#8a8570", lw=.9, zorder=3)
    # --- Salzstock ---
    ax.add_patch(Rectangle((-0.72, tf*0.60), 1.44, tf*0.66, color="#EDE6D2",
                           ec="#B0A88C", lw=1.1, zorder=1))
    ax.text(-0.66, tf*0.65, "Salzstock", fontsize=10, color="#7a7358", style="italic", zorder=4)
    # --- Bohrung ---
    ax.add_patch(Rectangle((-0.055, 0), 0.11, tf, color="#ffffff", ec="k", lw=1.1, zorder=4))
    ax.add_patch(Rectangle((-0.038, 0), 0.076, tf, color="#cfe4f5", zorder=5))
    ax.plot([-0.055,-0.055],[0,tf], color="k", lw=2.4, zorder=6)
    ax.plot([ 0.055, 0.055],[0,tf], color="k", lw=2.4, zorder=6)
    # --- Kaverne ---
    kx, ky, kw, kh = 0.0, tf + 60, 0.30, 145
    th = np.linspace(0, 2*np.pi, 200)
    ax.add_patch(Polygon(np.column_stack([kx + kw*np.sin(th)*(1+.10*np.cos(3*th)),
                                          ky + kh*np.cos(th)*(1+.06*np.sin(2*th))]),
                         closed=True, fc=FARBE["kaverne"], alpha=.34,
                         ec=FARBE["kaverne"], lw=1.8, zorder=5))
    ax.text(kx, ky-18, "KAVERNE", ha="center", fontsize=11, fontweight="bold",
            color="#4a6b1e", zorder=7)
    ax.text(kx, ky+8, f"{c['volumen']/1000:.0f} · 10³ m³", ha="center", fontsize=9,
            color="#4a6b1e", zorder=7)
    ax.text(kx, ky+34, f"{erg['p_max']:.0f} bar · {erg['T_kaverne']:.0f} °C",
            ha="center", fontsize=9.5, fontweight="bold", color="#4a6b1e", zorder=7)
    ax.text(kx, ky+58, erg["phase_kaverne"], ha="center", fontsize=9,
            color="#4a6b1e", style="italic", zorder=7)
    # Solesumpf
    ax.add_patch(Polygon([[kx-0.20, ky+kh*0.62],[kx+0.20, ky+kh*0.62],
                          [kx+0.15, ky+kh*0.92],[kx-0.15, ky+kh*0.92]],
                         closed=True, fc="#8fa8c8", alpha=.55, zorder=6))
    ax.text(kx, ky+kh*0.80, "Solesumpf", ha="center", fontsize=7.5, color="#2f4a6b", zorder=7)
    # --- Bohrlochkopf ---
    ax.add_patch(Rectangle((-0.17, -78), 0.34, 74, fc="#dfe6ea", ec="k", lw=1.2, zorder=7))
    ax.text(0, -41, "Bohrlochkopf", ha="center", va="center", fontsize=9.5, zorder=8)

    def label(x, y, txt, farbe, ha="left"):
        ax.annotate(txt, xy=(x, y), fontsize=9.5, color=farbe, ha=ha, zorder=9,
                    bbox=dict(boxstyle="round,pad=0.34", fc="white", ec=farbe, lw=1.1, alpha=.95))
    label(0.30, -60, f"EINSPEICHERN\n{erg['p_kopf_ein']:.0f} bar · {erg['T_pumpe_aus']:.0f} °C",
          FARBE["dicht"])
    label(-0.86, -60, f"AUSSPEICHERN\n{c['p_kopf_aus']:.0f} bar · {erg['T_kopf_aus']:.0f} °C",
          FARBE["gas"])
    # Saeulenpfeil
    ax.add_patch(FancyArrowPatch((0.30, 90), (0.30, tf-40), arrowstyle="-|>",
                                 mutation_scale=17, lw=2.0, color=FARBE["dicht"], zorder=8))
    ax.text(0.35, tf*0.22, f"Gassäule\n+{erg['saeulengewinn']:.0f} bar\nρ ≈ {erg['rho_oben']:.0f}…{erg['rho_unten']:.0f} kg/m³",
            fontsize=9.5, color=FARBE["dicht"], va="center", zorder=8)
    # kritische Teufe
    if 0 < erg["z_krit"] < tf:
        ax.axhline(erg["z_krit"], color=FARBE["warn"], ls="--", lw=1.2, zorder=6)
        ax.text(-0.94, erg["z_krit"]-16, f"T = {TC:.0f} °C bei {erg['z_krit']:.0f} m  →  darüber flüssig, darunter überkritisch",
                fontsize=8.5, color=FARBE["warn"], zorder=8)
    ax.plot([-0.20, 0.20], [tf, tf], color="k", lw=2.6, zorder=8)
    ax.text(-0.22, tf-14, f"LCCS  {tf:.0f} m", fontsize=9, ha="right", zorder=8)

    ax.set_xlim(-1.0, 1.0); ax.set_ylim(tf*1.30, -110)
    ax.set_ylabel("Teufe [m]", fontsize=10)
    ax.set_xticks([]); ax.spines[["top","right","bottom"]].set_visible(False)
    ax.set_title("Kavernenspeicher – berechnete Betriebsdaten", fontsize=12.5, fontweight="bold", pad=12)

    # ---------- rechte Seite: Druckfenster + Regime ----------
    ax2.set_title("Betriebsfenster und Regime", fontsize=12.5, fontweight="bold", pad=12)
    ax2.add_patch(Rectangle((0.10, c["p_min_geomech"]), 0.34, c["p_max"]-c["p_min_geomech"],
                            fc="#dbe8c4", ec=FARBE["kaverne"], lw=1.4))
    ax2.add_patch(Rectangle((0.10, erg["p_lccs_grenz"]), 0.34, c["p_max"]-erg["p_lccs_grenz"],
                            fc=FARBE["dicht"], alpha=.30, ec=FARBE["dicht"], lw=1.4))
    ax2.text(0.27, (c["p_max"]+erg["p_lccs_grenz"])/2, "REGIME I\ndurchgehend dicht\nPumpe + 1 Drossel",
             ha="center", va="center", fontsize=9.5, color="#0d5c44", fontweight="bold")
    ax2.text(0.27, (erg["p_lccs_grenz"]+c["p_min_geomech"])/2,
             "REGIME II\nKopf unterkritisch\nPhasenwechsel im Bohrloch\n+ Vorwärmung, Messtechnik",
             ha="center", va="center", fontsize=9.5, color="#8a3b12")
    for y, txt, col, ls in [
        (erg["p_lith"], f"lithostatisch {erg['p_lith']:.0f} bar", FARBE["grau"], ":"),
        (c["p_max"], f"p_max {c['p_max']:.0f} bar (≈80 %)", FARBE["warn"], "-"),
        (erg["p_lccs_grenz"], f"Regimegrenze {erg['p_lccs_grenz']:.0f} bar → Kopf = {PC:.1f} bar", FARBE["grenz"], "--"),
        (c["p_min_geomech"], f"p_min {c['p_min_geomech']:.0f} bar (Salzkriechen)", FARBE["warn"], "-"),
        (PC, f"p_krit {PC:.1f} bar", "#888", "-.")]:
        ax2.axhline(y, xmin=.02, xmax=.46, color=col, ls=ls, lw=1.4)
        dy = -3.5 if txt.startswith("p_min") else 0
        ax2.text(0.50, y+dy, txt, fontsize=9, color=col, va="center")
    # Arbeitsgasbalken
    ax2.add_patch(Rectangle((0.02, c["p_min_geomech"]), 0.05,
                            c["p_max"]-c["p_min_geomech"], fc=FARBE["gas"], alpha=.55))
    ax2.text(0.045, (c["p_max"]+c["p_min_geomech"])/2, "nutzbarer\nDruckhub",
             rotation=90, ha="center", va="center", fontsize=8, color="#7a3a10")
    ax2.set_ylim(40, erg["p_lith"]*1.06); ax2.set_xlim(0, 1.0)
    ax2.set_ylabel("Druck an der LCCS [bar]", fontsize=10)
    ax2.set_xticks([]); ax2.spines[["top","right","bottom"]].set_visible(False)

    fig.suptitle(f"CO₂-Salzkaverne · {tf:.0f} m · Gebirge {c['T_oberflaeche']:.0f} °C + {c['geo_gradient']*100:.0f} °C/100 m"
                 f" · Stoffdaten CoolProp (Span-Wagner)", fontsize=10.5, y=0.975, color="#444")
    fig.tight_layout(rect=[0,0,1,0.955]); fig.savefig(datei, dpi=155); plt.close(fig)
    return datei

def abb_teufenprofile(faelle, datei="abb2_teufenprofile.png", c=CFG):
    """Temperatur-, Druck- und Dichteprofil (Darstellung nach Quelle Fig. 3)."""
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 6.6), sharey=True)
    z = [r["z"] for r in faelle[0][1]]
    axs[0].plot([r["T"] for r in faelle[0][1]], z, color=FARBE["grau"], lw=2)
    axs[0].set_title("Geologisches\nTemperaturprofil [°C]", fontsize=11)
    axs[0].axvline(TC, color=FARBE["warn"], ls="--", lw=1.1)
    axs[0].text(TC+0.6, c["teufe"]*0.06, f"T_krit {TC:.0f} °C", fontsize=8.5, color=FARBE["warn"])
    stile = [("-.", FARBE["dicht"]), ("--", FARBE["grenz"]), ("-", FARBE["gas"])]
    for (lbl, rows), (ls, col) in zip(faelle, stile):
        axs[1].plot([r["p"] for r in rows], z, ls=ls, color=col, lw=2, label=lbl)
        axs[2].plot([r["rho"] for r in rows], z, ls=ls, color=col, lw=2, label=lbl)
    for a, t in zip(axs[1:], ["Druck [bar]", "Dichte [kg/m³]"]):
        a.set_title(t, fontsize=11); a.legend(fontsize=8.5, loc="lower left")
    axs[1].axvline(PC, color="#888", ls=":", lw=1.2)
    axs[1].text(PC+3, c["teufe"]*0.06, f"p_krit {PC:.1f} bar", fontsize=8.5, color="#666")
    axs[0].set_ylabel("Teufe z [m]", fontsize=10)
    axs[0].set_ylim(c["teufe"]*1.12, 0)
    for a in axs: a.grid(alpha=.3)
    fig.suptitle("Teufenprofile für drei Betriebspunkte – eigene Berechnung (CoolProp), "
                 "Darstellung nach Buzogany & Kruck (2022), Fig. 3", fontsize=10.5, y=0.98)
    fig.tight_layout(rect=[0,0,1,0.94]); fig.savefig(datei, dpi=155); plt.close(fig)
    return datei

def abb_phasendiagramm(erg, datei="abb3_phasendiagramm.png", c=CFG):
    """p-T-Diagramm mit Prozesspfaden und Betriebsbereich."""
    fig, ax = plt.subplots(figsize=(11.5, 7.6))
    Ts = np.linspace(T_TRIPEL+0.4, TC-0.03, 260)
    ps = [PropsSI("P","T",t+273.15,"Q",1,FLUID)/1e5 for t in Ts]
    ax.plot(Ts, ps, "k--", lw=2, label="Sättigungslinie (flüssig ↔ gas)")
    ax.plot(TC, PC, "o", ms=11, mfc="none", mec=FARBE["warn"], mew=2.2,
            label=f"kritischer Punkt ({TC:.1f} °C / {PC:.1f} bar)")
    ax.axvline(TC, color="#bbb", ls=":", lw=1.2); ax.axhline(PC, color="#bbb", ls=":", lw=1.2)
    ax.add_patch(Rectangle((c["T_spec_min"], c["p_spec_min"]),
                           c["T_spec_max"]-c["T_spec_min"], c["p_spec_max"]-c["p_spec_min"],
                           fill=False, ec="#5f8f2a", lw=1.8, ls="--", label="Pipeline-Spezifikation"))
    ax.add_patch(Rectangle((30, c["p_min_geomech"]), 30, c["p_max"]-c["p_min_geomech"],
                           fill=False, ec="#7A6FD0", lw=1.8, ls="--", label="Betriebsbereich Kaverne"))
    p = erg["pfade"]
    ax.plot(*zip(*p["pumpe"]),   color=FARBE["dicht"], lw=3.2, label="① Pumpe (Einspeichern)")
    ax.plot(*zip(*p["ab"]),      color="#7FB8A0", lw=2.2, ls="--", label="② Bohrloch abwärts")
    ax.plot(*zip(*p["auf"]),     color="#E8A33D", lw=2.2, ls="--", label="③ Bohrloch aufwärts (Nennrate)")
    ax.plot(*zip(*p["drossel"]), color=FARBE["gas"], lw=3.2, label="④ Drossel (Ausspeichern)")
    for x, y, t in [(20,140,"flüssig / dicht"), (46,175,"überkritisch"), (12,25,"gasförmig")]:
        ax.text(x, y, t, fontsize=10, color="#777", style="italic")
    ax.set_xlabel("Temperatur [°C]", fontsize=11); ax.set_ylabel("Druck [bar]", fontsize=11)
    ax.set_xlim(-15, 70); ax.set_ylim(0, c["p_max"]*1.12)
    ax.grid(alpha=.3); ax.legend(fontsize=8.6, loc="upper left", framealpha=.94)
    ax.set_title("CO₂-Phasendiagramm mit Prozesspfaden (Regime I)", fontsize=12.5, fontweight="bold")
    fig.tight_layout(); fig.savefig(datei, dpi=155); plt.close(fig)
    return datei

def abb_arbeitsgas(erg, datei="abb4_arbeitsgas.png", c=CFG):
    """Inventar ueber Druck mit Arbeitsgas-/Kissengasanteilen."""
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.2, 6.2), gridspec_kw=dict(width_ratios=[1.35,1]))
    pp = np.linspace(c["p_min_geomech"], c["p_max"], 90)
    T_iso = 50.0
    inv_i = [inventar(p, T_iso, c) for p in pp]
    def T_abk(p): return 33.1 + (p-77.6)*(55.0-33.1)/(210.0-77.6)
    inv_r = [inventar(p, T_abk(p), c) for p in pp]
    ax.plot(pp, inv_i, "--", color=FARBE["dicht"], lw=2, label=f"isotherm {T_iso:.0f} °C (obere Abschätzung)")
    ax.plot(pp, inv_r, "-",  color=FARBE["grenz"], lw=2.4, label="mit Abkühlung (realitätsnäher)")
    ax.axvline(erg["p_lccs_grenz"], color=FARBE["warn"], ls=":", lw=1.6)
    ax.text(erg["p_lccs_grenz"]+2, max(inv_i)*0.30,
            f"Regimegrenze\n{erg['p_lccs_grenz']:.0f} bar", fontsize=9, color=FARBE["warn"])
    ax.fill_between(pp, 0, inv_r, where=(pp<=erg["p_lccs_grenz"]), color=FARBE["gas"], alpha=.10)
    ax.set_xlabel("Kavernendruck (LCCS) [bar]", fontsize=10.5)
    ax.set_ylabel("gespeicherte Masse [kt]", fontsize=10.5)
    ax.set_title("Inventar über Druck – Arbeitsgas ist die Differenz", fontsize=12, fontweight="bold")
    ax.grid(alpha=.3); ax.legend(fontsize=9); ax.set_ylim(0, max(inv_i)*1.08)

    lbl = ["A: Bohrloch dicht\n(p_min = %.0f bar)" % erg["p_lccs_grenz"],
           "B: Kaverne überkrit.\n(p_min = %.1f bar)" % PC,
           "C: geomechanisch\n(p_min = %.0f bar)" % c["p_min_geomech"]]
    ag = erg["arbeitsgas_varianten"]
    x = np.arange(3); br = .38
    ax2.bar(x-br/2, [v[0] for v in ag], br, color=FARBE["dicht"], alpha=.72, label="isotherm")
    ax2.bar(x+br/2, [v[1] for v in ag], br, color=FARBE["grenz"], alpha=.85, label="mit Abkühlung")
    for i, v in enumerate(ag):
        ax2.text(i-br/2, v[0]+1.4, f"{v[0]:.0f} %", ha="center", fontsize=9)
        ax2.text(i+br/2, v[1]+1.4, f"{v[1]:.0f} %", ha="center", fontsize=9, fontweight="bold")
    ax2.axhspan(22, 32, color="#999", alpha=.22)
    ax2.text(2.30, 27, "Vollsimulation\nder Quelle\n22–32 %", fontsize=8.4, color="#555", va="center")
    ax2.set_xticks(x); ax2.set_xticklabels(lbl, fontsize=9)
    ax2.set_ylabel("Arbeitsgasanteil [%]", fontsize=10.5); ax2.set_ylim(0, 92); ax2.set_xlim(-0.55, 2.95)
    ax2.set_title("Arbeitsgas je Minimaldruck", fontsize=12, fontweight="bold")
    ax2.grid(alpha=.3, axis="y"); ax2.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(datei, dpi=155); plt.close(fig)
    return datei

# =====================================================================
# HAUPTRECHNUNG
# =====================================================================
def rechne(c=CFG):
    erg = {}
    erg["p_max"] = c["p_max"]
    erg["T_kaverne"] = T_gebirge(c["teufe"], c)
    erg["phase_kaverne"] = phase(c["p_max"], erg["T_kaverne"])
    erg["z_krit"] = (TC - c["T_oberflaeche"]) / c["geo_gradient"]
    erg["p_lith"] = c["rho_salz"] * G * c["teufe"] / 1e5

    # Auslegung Einspeichern: Kopfdruck fuer p_max unten
    erg["p_kopf_ein"] = loese_kopfdruck(c["p_max"], c)
    saeule = saeule_abwaerts(erg["p_kopf_ein"], c)
    erg["saeule"] = saeule
    erg["saeulengewinn"] = saeule[-1]["p"] - saeule[0]["p"]
    erg["rho_oben"], erg["rho_unten"] = saeule[0]["rho"], saeule[-1]["rho"]

    # Pumpe
    T2, w, ph = druckerhoehung(c["p_anlieferung"], c["T_anlieferung"], erg["p_kopf_ein"])
    erg["T_pumpe_aus"], erg["w_pumpe"], erg["phase_pumpe"] = T2, w, ph
    erg["m_min"], erg["m_max"] = massenstrom(c["V_norm_min"]), massenstrom(c["V_norm_max"])
    erg["P_pumpe"] = (erg["m_min"]*w, erg["m_max"]*w)   # kW

    # Regimegrenze
    erg["p_lccs_grenz"] = loese_plccs_fuer_kopfdruck(PC, c)

    # Ausspeichern: adiabate Kopftemperatur
    p_unten = c["p_max"]
    h_u = PropsSI("H","P",p_unten*1e5,"T",erg["T_kaverne"]+273.15,FLUID)
    h_o = h_u - G*c["teufe"]
    erg["T_kopf_aus"] = PropsSI("T","P",c["p_kopf_aus"]*1e5,"H",h_o,FLUID) - 273.15
    Td, phd, qd = drosselung(c["p_kopf_aus"], erg["T_kopf_aus"], c["p_anlieferung"])
    erg["T_drossel_aus"], erg["phase_drossel"], erg["q_drossel"] = Td, phd, qd
    erg["spec_ok"] = c["T_spec_min"] <= Td <= c["T_spec_max"]
    if not erg["spec_ok"]:
        dh = (PropsSI("H","P",c["p_anlieferung"]*1e5,"T",Td+273.15,FLUID)
              - PropsSI("H","P",c["p_anlieferung"]*1e5,"T",c["T_spec_max"]+273.15,FLUID))
        erg["P_nachkuehler"] = (erg["m_min"]*dh/1e3, erg["m_max"]*dh/1e3)  # kW

    # Teufenprofile fuer drei Betriebspunkte
    erg["faelle"] = [(f"pLCCS = {c['p_max']:.0f} bar (hoch)",           saeule_aufwaerts(c["p_max"], c)),
                     (f"pLCCS = {erg['p_lccs_grenz']:.1f} bar (Grenzfall)", saeule_aufwaerts(erg["p_lccs_grenz"], c)),
                     (f"pLCCS = {c['p_min_geomech']:.0f} bar (niedrig)", saeule_aufwaerts(c["p_min_geomech"], c))]

    # Pfade fuers Phasendiagramm
    n = 14
    pumpe = [(c["T_anlieferung"] + (T2-c["T_anlieferung"])*i/n,
              c["p_anlieferung"] + (erg["p_kopf_ein"]-c["p_anlieferung"])*i/n) for i in range(n+1)]
    ab  = [(r["T"], r["p"]) for r in saeule]
    aufr = saeule_aufwaerts(c["p_max"], c)
    auf = []
    for r in aufr:
        hh = h_u - G*(c["teufe"]-r["z"])
        auf.append((PropsSI("T","P",r["p"]*1e5,"H",hh,FLUID)-273.15, r["p"]))
    hd = PropsSI("H","P",c["p_kopf_aus"]*1e5,"T",erg["T_kopf_aus"]+273.15,FLUID)
    dro = [(PropsSI("T","P",pv*1e5,"H",hd,FLUID)-273.15, pv)
           for pv in np.linspace(c["p_kopf_aus"], c["p_anlieferung"], 12)]
    erg["pfade"] = dict(pumpe=pumpe, ab=ab, auf=auf, drossel=dro)

    # Arbeitsgas
    def T_abk(p): return 33.1 + (p-77.6)*(55.0-33.1)/(210.0-77.6)
    erg["arbeitsgas_varianten"] = []
    for pmin in [erg["p_lccs_grenz"], PC, c["p_min_geomech"]]:
        ai = arbeitsgas(pmin, c["p_max"], 50.0, 50.0, c)[0]
        ar = arbeitsgas(pmin, c["p_max"], T_abk(pmin), T_abk(c["p_max"]), c)[0]
        erg["arbeitsgas_varianten"].append((ai, ar))
    return erg

def report(erg, c=CFG):
    L = []
    A = L.append
    A("="*78); A("  CO2-SALZKAVERNE - AUSLEGUNGSRECHNUNG"); A("="*78)
    A(f"  Teufe {c['teufe']:.0f} m | Gebirge {c['T_oberflaeche']:.0f} °C + {c['geo_gradient']*100:.0f} °C/100 m"
      f" | Volumen {c['volumen']/1000:.0f}e3 m3")
    A(f"  Stoffdaten: CoolProp / Span-Wagner | krit. Punkt {TC:.1f} °C / {PC:.1f} bar")
    A("-"*78)
    A("GEOLOGIE UND DRUCKFENSTER")
    A(f"  Kavernentemperatur (geothermisch)      {erg['T_kaverne']:8.1f} °C")
    A(f"  T unterschreitet T_krit bei Teufe      {erg['z_krit']:8.0f} m")
    A(f"  lithostatischer Gebirgsdruck           {erg['p_lith']:8.0f} bar")
    A(f"  Betriebsfenster LCCS                   {c['p_min_geomech']:8.0f} - {c['p_max']:.0f} bar")
    A(f"  Regimegrenze (Kopfdruck = p_krit)      {erg['p_lccs_grenz']:8.1f} bar")
    A("-"*78)
    A("EINSPEICHERN")
    A(f"  Anlieferung                            {c['p_anlieferung']:8.1f} bar / {c['T_anlieferung']:.0f} °C")
    A(f"  Pumpe auf Kopfdruck                    {erg['p_kopf_ein']:8.1f} bar / {erg['T_pumpe_aus']:.1f} °C  ({erg['phase_pumpe']})")
    A(f"  spezifische Arbeit                     {erg['w_pumpe']:8.2f} kJ/kg")
    A(f"  Leistung bei {c['V_norm_min']/1000:.0f}-{c['V_norm_max']/1000:.0f}e3 Nm3/h        "
      f"{erg['P_pumpe'][0]:8.0f} - {erg['P_pumpe'][1]:.0f} kW")
    A(f"  Massenstrom                            {erg['m_min']:8.1f} - {erg['m_max']:.1f} kg/s")
    A(f"  Saeulengewinn im Bohrloch              {erg['saeulengewinn']:8.1f} bar")
    A(f"  Dichte oben / unten                    {erg['rho_oben']:8.1f} / {erg['rho_unten']:.1f} kg/m3")
    A("-"*78)
    A("AUSSPEICHERN (adiabater Grenzfall = Nennrate)")
    A(f"  Kaverne                                {c['p_max']:8.1f} bar / {erg['T_kaverne']:.1f} °C")
    A(f"  am Bohrlochkopf                        {c['p_kopf_aus']:8.1f} bar / {erg['T_kopf_aus']:.1f} °C")
    A(f"  nach Drossel auf Pipelinedruck         {c['p_anlieferung']:8.1f} bar / {erg['T_drossel_aus']:.1f} °C"
      f"  ({erg['phase_drossel']})")
    if erg["spec_ok"]:
        A( "  -> innerhalb der Pipeline-Spezifikation, kein Nachkuehler noetig")
    else:
        A(f"  -> AUSSERHALB Spezifikation ({c['T_spec_min']:.0f}-{c['T_spec_max']:.0f} °C):"
          f" Nachkuehler {erg['P_nachkuehler'][0]/1000:.1f} - {erg['P_nachkuehler'][1]/1000:.1f} MW")
    A("-"*78)
    A("ARBEITSGAS (Massenbilanz m = rho(p,T) * V)")
    A("  Variante                              isotherm   mit Abkuehlung")
    for (lbl, pmin), (ai, ar) in zip(
        [("A Bohrloch durchgehend dicht", erg["p_lccs_grenz"]),
         ("B Kaverne ueberkritisch", PC),
         ("C geomechanisches Minimum", c["p_min_geomech"])], erg["arbeitsgas_varianten"]):
        A(f"  {lbl:32s} p_min {pmin:6.1f} bar  {ai:6.1f} %   {ar:6.1f} %")
    A("  Hinweis: obere Abschaetzung. Vollsimulation der Quelle: 22-32 % Arbeitsgas.")
    A("="*78)
    return "\n".join(L)


# =====================================================================
# EXCEL-EXPORT (alle Werte frisch aus CoolProp)
# =====================================================================
def export_excel(erg, datei="CO2_Kaverne_berechnet.xlsx", c=CFG):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    B = Font(name="Arial", color="0000FF"); N = Font(name="Arial", italic=True, size=9, color="595959")
    H = Font(name="Arial", bold=True, size=12); S = Font(name="Arial", bold=True, color="FFFFFF")
    F = PatternFill("solid", fgColor="1F4E79"); Y = PatternFill("solid", fgColor="FFFF00")
    tn = Side(style="thin", color="BFBFBF"); BD = Border(left=tn, right=tn, top=tn, bottom=tn)
    ct = Alignment(horizontal="center")
    wb = Workbook()

    def kopf(ws, zeile, spalten):
        for j, h in enumerate(spalten, 1):
            x = ws.cell(zeile, j, h); x.font = S; x.fill = F; x.alignment = ct; x.border = BD

    ws = wb.active; ws.title = "Annahmen & Ergebnisse"
    ws["A1"] = "CO2-Salzkaverne – erzeugt mit co2_kaverne.py"; ws["A1"].font = Font(name="Arial", bold=True, size=14)
    ws["A2"] = "Alle Stoffdaten live aus CoolProp (Span-Wagner). Zum Ändern: CFG im Skript anpassen und neu ausführen."
    ws["A2"].font = N
    ws["A4"] = "Eingaben"; ws["A4"].font = H
    r = 5
    for k, v in c.items():
        ws.cell(r, 1, k).font = Font(name="Arial")
        x = ws.cell(r, 2, v); x.font = B; x.fill = Y; x.alignment = ct; x.border = BD
        r += 1
    ws.cell(r+1, 1, "Ergebnisse").font = H
    res = [("Kavernentemperatur [°C]", erg["T_kaverne"]), ("krit. Teufe [m]", erg["z_krit"]),
           ("lithostat. Druck [bar]", erg["p_lith"]), ("Regimegrenze pLCCS [bar]", erg["p_lccs_grenz"]),
           ("Kopfdruck Einspeichern [bar]", erg["p_kopf_ein"]), ("Säulengewinn [bar]", erg["saeulengewinn"]),
           ("Pumpe T_aus [°C]", erg["T_pumpe_aus"]), ("Pumpe w [kJ/kg]", erg["w_pumpe"]),
           ("Pumpe P min/max [kW]", f"{erg['P_pumpe'][0]:.0f} – {erg['P_pumpe'][1]:.0f}"),
           ("Kopftemperatur Ausspeichern [°C]", erg["T_kopf_aus"]),
           ("nach Drossel [°C]", erg["T_drossel_aus"]),
           ("Spezifikation eingehalten", "ja" if erg["spec_ok"] else "NEIN – Nachkühler nötig")]
    for i, (k, v) in enumerate(res):
        ws.cell(r+2+i, 1, k).font = Font(name="Arial")
        x = ws.cell(r+2+i, 2, round(v, 2) if isinstance(v, float) else v); x.font = B; x.alignment = ct
    ws.column_dimensions["A"].width = 34; ws.column_dimensions["B"].width = 22

    ws2 = wb.create_sheet("Gassäule")
    ws2["A1"] = "Integration dp/dz = ρ·g von oben nach unten"; ws2["A1"].font = H
    kopf(ws2, 3, ["Teufe [m]", "T [°C]", "ρ [kg/m³]", "p [bar]", "Phase"])
    for i, row in enumerate(erg["saeule"]):
        for j, v in enumerate([round(row["z"]), round(row["T"], 1), round(row["rho"], 1),
                               round(row["p"], 2), row["phase"]], 1):
            x = ws2.cell(4+i, j, v); x.border = BD; x.alignment = ct
            x.font = B if j in (2, 3, 4) else Font(name="Arial")
    for col, w in zip("ABCDE", [11, 10, 13, 11, 15]): ws2.column_dimensions[col].width = w

    ws3 = wb.create_sheet("Teufenprofile")
    ws3["A1"] = "Drei Betriebspunkte – Darstellung nach Buzogany & Kruck (2022), Fig. 3"; ws3["A1"].font = H
    sp = ["Teufe [m]", "T [°C]"]
    for lbl, _ in erg["faelle"]: sp += [f"p – {lbl}", f"ρ – {lbl}"]
    kopf(ws3, 3, sp)
    ref = erg["faelle"][0][1]
    for i in range(len(ref)):
        vals = [round(ref[i]["z"]), round(ref[i]["T"], 1)]
        for _, rows in erg["faelle"]:
            vals += [round(rows[i]["p"], 1), round(rows[i]["rho"], 1)]
        for j, v in enumerate(vals, 1):
            x = ws3.cell(4+i, j, v); x.border = BD; x.alignment = ct
            x.font = B if j > 2 else Font(name="Arial")
    for col in "ABCDEFGH": ws3.column_dimensions[col].width = 17

    ws4 = wb.create_sheet("Arbeitsgas")
    ws4["A1"] = "Arbeitsgas über Massenbilanz m = ρ(p,T)·V"; ws4["A1"].font = H
    ws4["A2"] = "Nicht über das Druckverhältnis rechnen – ρ ist bei CO2 nahe dem kritischen Punkt stark nichtlinear."
    ws4["A2"].font = N
    kopf(ws4, 4, ["Variante", "p_min [bar]", "Arbeitsgas isotherm [%]", "Arbeitsgas mit Abkühlung [%]"])
    namen = ["A – Bohrloch durchgehend dicht", "B – Kaverne überkritisch", "C – geomechanisches Minimum"]
    pmins = [erg["p_lccs_grenz"], PC, c["p_min_geomech"]]
    for i, (nm, pm, (ai, ar)) in enumerate(zip(namen, pmins, erg["arbeitsgas_varianten"])):
        for j, v in enumerate([nm, round(pm, 1), round(ai, 1), round(ar, 1)], 1):
            x = ws4.cell(5+i, j, v); x.border = BD; x.alignment = ct
            x.font = B if j > 1 else Font(name="Arial", bold=True)
    ws4.cell(9, 1, "Obere Abschätzung. Vollsimulation der Quelle: 22–32 % Arbeitsgas.").font = N
    for col, w in zip("ABCD", [34, 14, 24, 27]): ws4.column_dimensions[col].width = w
    wb.save(datei)
    return datei

if __name__ == "__main__":
    erg = rechne(CFG)
    txt = report(erg, CFG)
    print(txt)
    open("report.txt","w",encoding="utf-8").write(txt)
    f1 = abb_kavernenschema(erg); f2 = abb_teufenprofile(erg["faelle"])
    f3 = abb_phasendiagramm(erg); f4 = abb_arbeitsgas(erg)
    xl = export_excel(erg)
    print("\nErzeugt:", f1, f2, f3, f4, xl, sep="\n  ")
