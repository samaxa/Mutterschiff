# -*- coding: utf-8 -*-
"""
Optimale Kavernenteufe für CO2-Speicherung
==========================================
Bewertet Teufen anhand von Arbeitsgas und thermodynamischen Randbedingungen.

Ausgangspunkt: Buzogany & Kruck (2022), Kap. 5 – dort wird qualitativ vermutet,
dass eine geringere Teufe günstiger wäre, die Aussage aber nicht quantifiziert.
Dieses Modul rechnet sie durch.
"""
from CoolProp.CoolProp import PropsSI
import numpy as np

CFG = dict(
    volumen        = 650000.0,  # m3
    rho_salz       = 2200.0,    # kg/m3
    T_oberflaeche  = 10.0,      # degC Gebirge (Annahme der Quelle, wie co2_kaverne.py)
    geo_gradient   = 0.03,      # K/m
    f_pmax         = 0.80,      # Anteil des lithostatischen Drucks
    f_pmin         = 0.30,
    teufe_min_geom = 700.0,     # m, geomechanische Mindestteufe (standortabhängig!)
    teufe_max_geom = 2000.0,    # m
    T_marge        = 3.0,       # K Sicherheitsabstand zur kritischen Temperatur
)
G = 9.81
TC = PropsSI("Tcrit", "CO2") - 273.15
PC = PropsSI("pcrit", "CO2") / 1e5

def rho(p_bar, T_c):
    try:
        return PropsSI("D", "P", p_bar*1e5, "T", T_c+273.15, "CO2")
    except ValueError:
        return PropsSI("D", "T", T_c+273.15, "Q", 1, "CO2")

def bewerte_teufe(z, c=CFG):
    """Alle Kennzahlen und Randbedingungen für eine Teufe."""
    p_lith = c["rho_salz"] * G * z / 1e5
    p_max  = c["f_pmax"] * p_lith
    p_min  = c["f_pmin"] * p_lith
    T_geb  = c["T_oberflaeche"] + c["geo_gradient"] * z

    # Grenzfall LANGSAM: isotherm (Gebirge heizt vollständig nach) -> obere Schranke
    inv_max_iso = rho(p_max, T_geb) * c["volumen"] / 1e6
    inv_min_iso = rho(p_min, T_geb) * c["volumen"] / 1e6

    # Grenzfall SCHNELL: isentrope Entspannung des Kaverneninhalts -> untere Schranke
    # Dichte direkt aus (p, s) bestimmen - ueber (p, T) waere sie im Zweiphasengebiet
    # nicht eindeutig und erzeugt Spruenge.
    s = PropsSI("S", "P", p_max*1e5, "T", T_geb+273.15, "CO2")
    T_ise = PropsSI("T", "P", p_min*1e5, "S", s, "CO2") - 273.15
    rho_ise = PropsSI("D", "P", p_min*1e5, "S", s, "CO2")
    q_ise = PropsSI("Q", "P", p_min*1e5, "S", s, "CO2")
    inv_min_ise = rho_ise * c["volumen"] / 1e6

    ag_iso = inv_max_iso - inv_min_iso
    ag_ise = inv_max_iso - inv_min_ise

    # Randbedingungen
    rb = {}
    rb["T_ueber_krit"]   = T_geb >= TC + c["T_marge"]      # keine Flüssigphase in der Kaverne
    rb["T_ise_ueber_krit"] = T_ise >= TC                    # auch beim schnellen Ausspeichern
    rb["geomechanik"]    = c["teufe_min_geom"] <= z <= c["teufe_max_geom"]
    rb["gasumwandlung"]  = p_min < PC                       # günstig: Kaverne wird gasförmig
    rb["zweiphasig_kaverne"] = 0.0 <= q_ise <= 1.0          # bei schnellem Ausspeichern
    zulaessig = rb["T_ueber_krit"] and rb["geomechanik"]

    return dict(z=z, p_lith=p_lith, p_max=p_max, p_min=p_min, T_geb=T_geb, T_ise=T_ise, q_ise=q_ise,
                inv_max=inv_max_iso, ag_iso=ag_iso, ag_ise=ag_ise,
                anteil_iso=ag_iso/inv_max_iso*100, anteil_ise=ag_ise/inv_max_iso*100,
                rb=rb, zulaessig=zulaessig)

def optimiere(c=CFG, z_von=400, z_bis=2000, schritt=25):
    reihe = [bewerte_teufe(z, c) for z in range(z_von, z_bis+1, schritt)]
    zul = [r for r in reihe if r["zulaessig"]]
    best_abs = max(zul, key=lambda r: r["ag_ise"]) if zul else None
    # Empfehlungsfenster: innerhalb 95 % des Optimums
    fenster = [r for r in zul if r["ag_ise"] >= 0.95*best_abs["ag_ise"]] if best_abs else []
    return reihe, best_abs, fenster

def report(c=CFG):
    reihe, best, fenster = optimiere(c)
    L=[]; A=L.append
    A("="*84)
    A("  OPTIMALE KAVERNENTEUFE FÜR CO2-SPEICHERUNG")
    A("="*84)
    A(f"  Volumen {c['volumen']/1000:.0f}e3 m3 | Gebirge {c['T_oberflaeche']:.0f} °C + {c['geo_gradient']*100:.0f} °C/100 m")
    A(f"  p_max = {c['f_pmax']*100:.0f} %, p_min = {c['f_pmin']*100:.0f} % des lithostatischen Drucks")
    A(f"  Geomechanisches Fenster: {c['teufe_min_geom']:.0f} - {c['teufe_max_geom']:.0f} m")
    A(f"  Kritischer Punkt CO2: {TC:.1f} °C / {PC:.1f} bar | Sicherheitsmarge {c['T_marge']:.0f} K")
    A("-"*84)
    A(f"{'Teufe':>7}{'p_max':>7}{'p_min':>7}{'T_Geb':>7}{'T_isentr':>9}{'AG langsam':>12}{'AG schnell':>12}  Status")
    A("-"*84)
    for r in reihe:
        if r["z"] % 100: continue
        st=[]
        if not r["rb"]["T_ueber_krit"]: st.append("Flüssigphase in Kaverne möglich")
        if not r["rb"]["geomechanik"]:  st.append("außerhalb geomech. Fenster")
        if r["rb"]["gasumwandlung"] and r["zulaessig"]: st.append("Gasumwandlung (günstig)")
        if r["rb"]["zweiphasig_kaverne"]: st.append(f"bei schneller Rate ZWEIPHASIG in der Kaverne (q={r['q_ise']:.2f})")
        mark = " <<<" if fenster and fenster[0]["z"] <= r["z"] <= fenster[-1]["z"] else ""
        A(f"{r['z']:6.0f}m{r['p_max']:6.0f}b{r['p_min']:6.0f}b{r['T_geb']:6.0f}°C{r['T_ise']:8.0f}°C"
          f"{r['ag_iso']:10.0f}kt{r['ag_ise']:10.0f}kt  {' | '.join(st)}{mark}")
    A("-"*84)
    if best:
        A(f"  OPTIMUM (konservativer Grenzfall):   {best['z']:.0f} m mit {best['ag_ise']:.0f} kt Arbeitsgas ({best['anteil_ise']:.0f} %)")
        A(f"  EMPFEHLUNGSFENSTER (95 % davon):     {fenster[0]['z']:.0f} - {fenster[-1]['z']:.0f} m")
        A(f"  Untere Grenze gesetzt durch: {'Geomechanik' if fenster[0]['z']<=c['teufe_min_geom'] else 'Temperatur'}")
    A("")
    A("  Lesart: 'AG langsam' = isotherm (Gebirge heizt nach) = obere Schranke.")
    A("          'AG schnell' = isentrop (keine Wärmezufuhr)  = untere Schranke.")
    A("          Der reale Wert liegt ratenabhängig dazwischen.")
    A("="*84)
    return "\n".join(L)


# =====================================================================
# ABBILDUNG
# =====================================================================
def abbildung(datei="abb7_teufenoptimierung.png", c=CFG):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    reihe,_,_ = optimiere(c, 400, 2000, 25)
    z   = [r["z"] for r in reihe]
    iso = [r["ag_iso"] for r in reihe]
    ise = [r["ag_ise"] for r in reihe]
    fig,(ax,ax2)=plt.subplots(2,1,figsize=(11.5,9.2),sharex=True,
                              gridspec_kw=dict(height_ratios=[1.5,1]))
    ax.fill_between(z,ise,iso,color="#1D9E75",alpha=.18,label="Bandbreite je nach Ausspeicherrate")
    ax.plot(z,iso,color="#1D9E75",lw=2.4,label="langsam / isotherm (obere Schranke)")
    ax.plot(z,ise,color="#185FA5",lw=2.4,ls="--",label="schnell / isentrop (untere Schranke)")
    z_Tkrit=(TC+c["T_marge"]-c["T_oberflaeche"])/c["geo_gradient"]
    ax.axvspan(400,max(z_Tkrit,c["teufe_min_geom"]),color="#B22222",alpha=.10)
    ax.text((400+max(z_Tkrit,c["teufe_min_geom"]))/2,max(iso)*.55,
            "ausgeschlossen:\nGeomechanik und/oder\nFlüssigphase in der Kaverne",
            ha="center",fontsize=9.5,color="#8a2020")
    zul=[r for r in reihe if r["zulaessig"]]
    if zul:
        best=max(zul,key=lambda r:r["ag_ise"])
        ax.axvline(best["z"],color="#B26B00",ls=":",lw=2)
        ax.text(best["z"]+25,max(iso)*.92,f"Optimum {best['z']:.0f} m",fontsize=10,
                color="#B26B00",fontweight="bold")
    ax.set_ylabel("Arbeitsgas [kt]",fontsize=11)
    ax.set_title("Optimale Kavernenteufe für CO₂ – Arbeitsgas über Teufe",fontsize=13,fontweight="bold")
    ax.grid(alpha=.3); ax.legend(fontsize=9.5,loc="upper right")

    ax2.plot(z,[r["T_geb"] for r in reihe],color="#5F5E5A",lw=2,label="Gebirgstemperatur")
    ax2.plot(z,[r["T_ise"] for r in reihe],color="#185FA5",lw=2,ls="--",label="T nach isentroper Entspannung")
    ax2.axhline(TC,color="#B22222",ls=":",lw=1.6)
    ax2.text(410,TC+1.5,f"T_krit {TC:.0f} °C",fontsize=9,color="#B22222")
    ax2b=ax2.twinx()
    ax2b.plot(z,[r["p_min"] for r in reihe],color="#D85A30",lw=2,label="p_min")
    ax2b.axhline(PC,color="#D85A30",ls=":",lw=1.4)
    ax2b.text(1850,PC+4,f"p_krit {PC:.1f} bar",fontsize=9,color="#D85A30")
    ax2b.set_ylabel("Mindestdruck [bar]",fontsize=10.5,color="#D85A30")
    ax2.set_xlabel("Kavernenteufe [m]",fontsize=11); ax2.set_ylabel("Temperatur [°C]",fontsize=10.5)
    ax2.grid(alpha=.3); ax2.legend(fontsize=9,loc="upper left")
    fig.tight_layout(); fig.savefig(datei,dpi=150); plt.close(fig)
    return datei

# =====================================================================
# AUSLEGUNGSFENSTER: Teufe UND Ausspeicherrate
# =====================================================================
CFG.update(
    UA            = 546e3,   # W/K, Waermeuebergang Kaverne<->Gebirge (Annahme!)
    T_einspeicher = 30.0,    # degC an der LCCS
)

def teufenfenster(c=CFG):
    """Leitet das zulaessige Teufenfenster aus drei Bedingungen analytisch her."""
    # (1) p_min < p_krit -> Betriebsfenster ueberstreicht den steilen Dichtebereich
    z_pmin  = PC*1e5 / (c["f_pmin"] * c["rho_salz"] * G)
    # (2) T_Gebirge > T_krit + Marge -> keine Fluessigphase in der Kaverne
    z_Tkrit = (TC + c["T_marge"] - c["T_oberflaeche"]) / c["geo_gradient"]
    # (3) Geomechanik
    z_geom  = c["teufe_min_geom"]
    return dict(z_min=max(z_Tkrit, z_geom), z_max=min(z_pmin, c["teufe_max_geom"]),
                z_pmin=z_pmin, z_Tkrit=z_Tkrit, z_geom=z_geom,
                grund_unten="Geomechanik" if z_geom > z_Tkrit else "Temperatur (Flüssigphase)",
                grund_oben="p_min über p_krit" if z_pmin < c["teufe_max_geom"] else "Geomechanik")

def ausspeicherung(z, m_dot, c=CFG, dt=0.05):
    """Simuliert eine Ausspeicherung von p_max auf p_min bei fester Rate.
    Gibt minimale Kavernentemperatur, Dauer und Arbeitsgasanteil zurueck."""
    p_lith = c["rho_salz"]*G*z/1e5
    p_max, p_min = c["f_pmax"]*p_lith, c["f_pmin"]*p_lith
    T_geb = c["T_oberflaeche"] + c["geo_gradient"]*z
    V = c["volumen"]
    m = PropsSI("D","P",p_max*1e5,"T",T_geb+273.15,"CO2")*V
    U = m*PropsSI("U","P",p_max*1e5,"T",T_geb+273.15,"CO2")
    m0, t, T_min = m, 0.0, T_geb
    while t < 800:
        rho_, u_ = m/V, U/m
        p = PropsSI("P","D",rho_,"U",u_,"CO2")/1e5
        T = PropsSI("T","D",rho_,"U",u_,"CO2")-273.15
        T_min = min(T_min, T)
        if p <= p_min: break
        h = u_ + p*1e5/rho_
        dts = dt*86400
        m -= m_dot*dts
        U += -m_dot*h*dts + c["UA"]*(T_geb-T)*dts
        t += dt
    return dict(T_min=T_min, dauer=t, ag_anteil=(m0-m)/m0*100,
                einphasig=T_min > TC, m_dot=m_dot,
                Nm3_h=m_dot*3600/PropsSI("D","P",101325,"T",273.15,"CO2"))

def grenzrate(z, c=CFG, lo=5.0, hi=250.0, it=11):
    """Hoechste Rate, bei der die Kaverne einphasig bleibt (Bisektion)."""
    if not ausspeicherung(z, lo, c)["einphasig"]:
        return None                      # selbst langsamste Rate reicht nicht
    for _ in range(it):
        mid = 0.5*(lo+hi)
        if ausspeicherung(z, mid, c)["einphasig"]: lo = mid
        else: hi = mid
    return lo

def auslegung(c=CFG, teufen=None):
    """Kombiniert Teufenfenster und Grenzrate zu einer Empfehlung."""
    tf = teufenfenster(c)
    if teufen is None:
        teufen = [round(x) for x in np.linspace(tf["z_min"], tf["z_max"], 5)]
    zeilen = []
    for z in teufen:
        gr = grenzrate(z, c)
        b  = bewerte_teufe(z, c)
        sim = ausspeicherung(z, gr, c) if gr else None
        if sim:
            # absolutes Arbeitsgas und Jahresdurchsatz
            ag_kt = b["inv_max"] * sim["ag_anteil"]/100
            zyklusdauer = 2*sim["dauer"] + 45      # Aus + Ein + zwei Stillstaende (grob)
            sim["ag_kt"]     = ag_kt
            sim["zyklen_a"]  = 365/zyklusdauer
            sim["durchsatz"] = ag_kt * 365/zyklusdauer     # kt pro Jahr
        zeilen.append(dict(z=z, grenzrate=gr, bew=b, sim=sim))
    gueltig = [x for x in zeilen if x["grenzrate"]]
    best_ag   = max(gueltig, key=lambda x: x["sim"]["ag_anteil"]) if gueltig else None
    best_durch= max(gueltig, key=lambda x: x["sim"]["durchsatz"])  if gueltig else None
    return tf, zeilen, (best_ag, best_durch)

def report_auslegung(c=CFG):
    tf, zeilen, (best_ag, best_durch) = auslegung(c)
    L=[]; A=L.append
    A("="*86)
    A("  AUSLEGUNGSFENSTER: TEUFE UND AUSSPEICHERRATE")
    A("="*86)
    A("  Schritt 1 – Teufenfenster (analytisch)")
    A(f"    (1) p_min < p_krit          -> z < {tf['z_pmin']:.0f} m")
    A( "        sonst liegt der kritische Druck außerhalb des Betriebsfensters")
    A( "        und man fährt nur im flachen Teil der Dichtekurve")
    A(f"    (2) T_Gebirge > T_krit + {c['T_marge']:.0f} K -> z > {tf['z_Tkrit']:.0f} m")
    A( "        sonst Flüssigphase in der Kaverne möglich")
    A(f"    (3) Geomechanik             -> z > {tf['z_geom']:.0f} m  (standortabhängig)")
    A(f"    ==> zulässige Teufe: {tf['z_min']:.0f} - {tf['z_max']:.0f} m")
    A(f"        Untergrenze durch {tf['grund_unten']}, Obergrenze durch {tf['grund_oben']}")
    A("-"*86)
    A("  Schritt 2 – Grenzrate je Teufe (Kaverne bleibt einphasig)")
    A(f"{'Teufe':>7}{'p_min':>7}{'Grenzrate':>12}{'= Nm³/h':>10}{'Dauer':>7}{'AG %':>6}{'AG kt':>8}{'Zykl./a':>9}{'Durchsatz':>11}")
    A("-"*86)
    for x in zeilen:
        b=x["bew"]; gr=x["grenzrate"]; s=x["sim"]
        if gr is None:
            A(f"{x['z']:6.0f}m{b['p_min']:6.0f}b   keine Rate hält die Kaverne einphasig")
        else:
            A(f"{x['z']:6.0f}m{b['p_min']:6.0f}b{gr:9.0f} kg/s{s['Nm3_h']:9.0f}{s['dauer']:6.0f}d"
              f"{s['ag_anteil']:5.0f}%{s['ag_kt']:7.0f}{s['zyklen_a']:9.1f}{s['durchsatz']:8.0f} kt/a")
    A("-"*86)
    A("  ZWEI OPTIMA – je nach Zielgröße")
    if best_ag:
        s=best_ag["sim"]
        A(f"    (a) maximaler Arbeitsgas-ANTEIL:  {best_ag['z']:.0f} m, bis {best_ag['grenzrate']:.0f} kg/s")
        A(f"        {s['ag_anteil']:.0f} % Arbeitsgas, aber {s['dauer']:.0f} d je Ausspeicherung -> {s['zyklen_a']:.1f} Zyklen/a")
        A( "        sinnvoll, wenn das Kissengas teuer ist (Kapitalbindung im Speicherinhalt)")
    if best_durch:
        s=best_durch["sim"]
        A(f"    (b) maximaler JAHRESDURCHSATZ:   {best_durch['z']:.0f} m, bis {best_durch['grenzrate']:.0f} kg/s")
        A(f"        {s['durchsatz']:.0f} kt/a bei {s['ag_anteil']:.0f} % Arbeitsgas und {s['zyklen_a']:.1f} Zyklen/a")
        A( "        sinnvoll, wenn der Speicher Netzschwankungen ausgleichen soll")
    A("")
    A("  Der Zielkonflikt: flacher = höherer Anteil nutzbar, aber kleinere zulässige Rate.")
    A("  Welches Optimum gilt, hängt vom Geschäftsmodell ab (Saisonspeicher vs. Netzpuffer).")
    A("")
    A("  VORBEHALTE")
    A(f"    UA = {c['UA']/1e3:.0f} kW/K ist eine Annahme und geht direkt in die Grenzrate ein.")
    A( "    Die Faustwerte 80 %/30 % für p_max/p_min sind standortabhängig zu ersetzen.")
    A( "    Kaverne ideal durchmischt, Bohrloch nicht modelliert.")
    A("="*86)
    return "\n".join(L)


def abbildung_auslegung(datei="abb8_auslegungsfenster.png", c=CFG):
    """Zielkonflikt Arbeitsgasanteil vs. Jahresdurchsatz über die Teufe."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tf = teufenfenster(c)
    teufen = [round(x) for x in np.linspace(tf["z_min"], tf["z_max"], 7)]
    _, zeilen, _ = auslegung(c, teufen)
    g = [x for x in zeilen if x["grenzrate"]]
    z   = [x["z"] for x in g]
    ant = [x["sim"]["ag_anteil"] for x in g]
    dur = [x["sim"]["durchsatz"] for x in g]
    rate= [x["grenzrate"] for x in g]
    fig,(ax,ax2)=plt.subplots(2,1,figsize=(11,8.6),sharex=True)
    ax.plot(z,ant,"o-",color="#1D9E75",lw=2.4,label="Arbeitsgas-Anteil [%]")
    ax.set_ylabel("Arbeitsgas-Anteil [%]",color="#0F6E56",fontsize=10.5)
    axb=ax.twinx()
    axb.plot(z,dur,"s--",color="#D85A30",lw=2.4,label="Jahresdurchsatz [kt/a]")
    axb.set_ylabel("Jahresdurchsatz [kt/a]",color="#993C1D",fontsize=10.5)
    ax.set_title("Zielkonflikt: Arbeitsgas-Anteil gegen Jahresdurchsatz",fontsize=13,fontweight="bold")
    ax.grid(alpha=.3)
    l1,lb1=ax.get_legend_handles_labels(); l2,lb2=axb.get_legend_handles_labels()
    ax.legend(l1+l2,lb1+lb2,fontsize=9.5,loc="center left")
    ax2.plot(z,rate,"^-",color="#185FA5",lw=2.4)
    ax2.set_ylabel("zulässige Ausspeicherrate [kg/s]",fontsize=10.5)
    ax2.set_xlabel("Kavernenteufe [m]",fontsize=11)
    ax2.set_title("Grenzrate für einphasigen Kavernenbetrieb",fontsize=11.5)
    ax2.grid(alpha=.3)
    for xx,rr in zip(z,rate):
        ax2.annotate(f"{rr:.0f}",(xx,rr),textcoords="offset points",xytext=(0,8),
                     ha="center",fontsize=9,color="#185FA5")
    fig.suptitle(f"Zulässiges Teufenfenster {tf['z_min']:.0f}–{tf['z_max']:.0f} m · "
                 f"Kaverne bleibt einphasig · UA = {c['UA']/1e3:.0f} kW/K (Annahme)",
                 fontsize=10,y=0.975,color="#555")
    fig.tight_layout(rect=[0,0,1,0.955]); fig.savefig(datei,dpi=150); plt.close(fig)
    return datei


if __name__ == "__main__":
    txt = report() + "\n\n" + report_auslegung()
    print(txt)
    # explizit utf-8: sonst haengt die Kodierung an der Locale des Rechners
    open("report_teufe.txt","w",encoding="utf-8").write(txt + "\n")
    print()
    print("Abbildungen:", abbildung(), abbildung_auslegung(), sep="\n  ")
