# Übergabe fertig Felix

import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os
import numpy as np

from core.io_types import GuiInput, SimOutput
from Simulation import Simulator, run_simulation, industry_csv_mapping
from core.functions_web_support import *
from core.functions_plot import *



# Mapping: PV type name to id
pv_name_to_id = {
    "Windschutzwand": 0,
    "Lärmschutzwand": 1,
    "Dach": 2,
    "Böschung": 3,
    "Vertikal (Zaun, Nord-Süd)": 5,
    "Horizontal (aufgeständert, Ost-West)": 6,
    "Horizontal mit Single-Axis-Tracking (aufgeständert, Nord-Süd)": 4
}


# Industry columns order
industry_order_all = [
    "Entsorgung",
    "Stahl_1",
    "Logistik und Lagerung",
    "Schrott Metallhandel",
    "Lagerung",
    "Buero",
    "Logistik Lebensmittel",
    "Stahl_2"
]



# create data objects for in- and output
Input = GuiInput()
Output = SimOutput()

# Streamlit layout
st.set_page_config(layout="centered")

# Logos as base64 for accurate placement in html wrapper
th_logo_path = os.path.join(icon_dir, "logo.png")
iee_logo_path = os.path.join(icon_dir, "IEE_Logo.png")
th_logo_b64 = image_to_base64(th_logo_path)
iee_logo_b64 = image_to_base64(iee_logo_path)
st.markdown(
    f"""
    <div style="display:flex; justify-content:center; align-items:center; gap:70px;">
        <img src="data:image/png;base64,{iee_logo_b64}" style="height:50px; border-radius:0;">
        <img src="data:image/png;base64,{th_logo_b64}" style="height:50px; border-radius:0;">
    </div>
    """,
    unsafe_allow_html=True
)


# Initial st.session.state variables definition
# Resistant to rerun of site, only changing with actual Simulation (button)
if "simulation_ran" not in st.session_state:
    st.session_state.simulation_ran = False
if "sim_output" not in st.session_state:
    st.session_state.sim_output = Output

# Title
st.write("\n")
st.title("Energiesystem Modellierung - Innovationspark Jüchen")
st.write("### Erzeugung Eingabewerte")

# ---------------- Generation Input ----------------
with st.container():

    # Tabs within Generation container
    tab1, tab2 = st.tabs(["Solarautobahn", "Energielandschaft"])

    # ---------------- Solar highway ----------------
    with tab1:
        col1_tab1, col2_tab1 = st.columns(2)
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Input multiselects
        with col1_tab1:
            Input.h_highways = st.multiselect("Autobahn auswählen", ["A44", "A46"])
            h_selected_names = st.multiselect("PV-Typ", ["Lärmschutzwand", "Windschutzwand", "Dach", "Böschung"])
            Input.h_pv_types = [pv_name_to_id[name] for name in h_selected_names]

            # dynamic info box
            st.write('\n')
            if not Input.h_highways or not Input.h_pv_types:
                st.info("Solarautobahn deaktiviert.")
            else:
                st.info("Solarautobahn aktiv.")

        # Dynamic Input visualization via folium
        with col2_tab1:
            pv_geojson_mapping_col2_tab1 = {
                "A44": "a44_beide.geojson",
                "A46": "a46_beide.geojson",
            }

            m = folium.Map(location=[51.06280, 6.49554], zoom_start=12)

            for highway in Input.h_highways:
                selected_file = pv_geojson_mapping_col2_tab1[highway]
                geojson_path = os.path.join(script_dir,"data", "inputs", "geometry", selected_file)

                with open(geojson_path, "r", encoding="utf-8") as f:
                    geojson_data = json.load(f)

                folium.GeoJson(
                    geojson_data,
                    name=f"{highway}"
                ).add_to(m)

            folium.LayerControl().add_to(m)
            st_data = st_folium(m, width=400, height=400)

    # ---------------- Energy landscape ----------------
    with tab2:
        col1_tab2, col2_tab2 = st.columns(2)

        # Input segments and selectbox
        with col1_tab2:
            Input.el_build_state = st.radio(
                "Ausbaugrad der Energielandschaft in %",
                options=[0, 50, 100],
                index=0,
                horizontal=True,
                format_func=lambda x: f"{x:.0f}%"
            )

            el_selected_names = st.selectbox(
                "PV-Typ",
                [
                    "Vertikal (Zaun, Nord-Süd)",
                    "Horizontal (aufgeständert, Ost-West)",
                    "Horizontal mit Single-Axis-Tracking (aufgeständert, Nord-Süd)"
                ]
            )
            Input.el_pv_type = pv_name_to_id[el_selected_names]

            Input.el_tractor_width = st.radio(
                "Traktorbreite",
                options=[9.0, 12.0, 15.0],
                index=1,
                horizontal=True,
                format_func=lambda x: f"{x:.0f}m"
            )

            Input.el_tractor_length = st.radio(
                "Traktorlänge",
                options=[12.0, 15.0, 18.0],
                index=1,
                horizontal=True,
                format_func=lambda x: f"{x:.0f}m"
            )

            Input.el_tractor_turn_radius = st.radio(
                "Traktor-Wenderadius",
                options=[6.0, 9.0, 12.0],
                index=1,
                horizontal=True,
                format_func=lambda x: f"{x:.0f}m"
            )

            # dynamic info box
            Input.el_build_state = 0 if Input.el_build_state is None else Input.el_build_state
            if Input.el_build_state == 0:
                st.info("Energielandschaft deaktiviert.")
            else:
                st.info("Energielandschaft aktiv.")


        # Dynamic Input visualization via folium
        with col2_tab2:
            pv_geojson_mapping_col2_tab2 = {
                "Vertikal (Zaun, Nord-Süd)": {
                    50: "Geometry_Vertikal_50_Prozent_20m.geojson",
                    100: "Geometry_Vertikal_Traktorbreite_20m.geojson",
                },
                "Horizontal (aufgeständert, Ost-West)": {
                    50: "Geometry_Horizontal_50_Prozent_20m.geojson",
                    100: "Geometry_Horizontal_Traktorbreite_20m.geojson",
                },
                "Horizontal mit Single-Axis-Tracking (aufgeständert, Nord-Süd)": {
                    50: "Geometry_Vertikal_50_Prozent_20m.geojson",
                    100: "Geometry_Vertikal_Traktorbreite_20m.geojson",
                },
            }

            if Input.el_build_state != 0 and Input.el_build_state is not None:
                selected_file = pv_geojson_mapping_col2_tab2[el_selected_names][Input.el_build_state]
                geojson_path = os.path.join(script_dir,"data", "inputs", "geometry", selected_file)

                with open(geojson_path, "r", encoding="utf-8") as f:
                    geojson_data = json.load(f)

            m = folium.Map(location=[51.07596, 6.48599], zoom_start=14)

            if Input.el_build_state != 0 and Input.el_build_state is not None:
                folium.GeoJson(
                    geojson_data,
                    name=f"{Input.el_pv_type}{Input.el_tractor_width}"
                ).add_to(m)

            folium.LayerControl().add_to(m)
            st_data = st_folium(m, width=400, height=400)


# Separation line
col1, col2, col3 = st.columns([0.05, 0.9, 0.05])
with col2:
    st.divider()


# ---------------- Consumption Input ----------------
st.write("### Verbrauch Eingabewerte")

with st.container():

    tab4, tab5, tab6 = st.tabs(["Industriegebiet", "Green Energy Hub", "Neubaugebiet Jüchen Süd"])

    # ---------------- Industrial Area ----------------
    with tab4:
        col1_tab4, col2_tab4 = st.columns(2)

        with col1_tab4:
            options = {
                0: "Entsorgung",
                1: "Stahl, 5-Tage-Woche, 3-Schicht",
                2: "Logistik und Lagerung",
                3: "Schrott- und Metallhandel",
                4: "Lagerung",
                5: "Büro",
                6: "Logistik Lebensmittel",
                7: "Stahl, 7-Tage-Woche, 2-Schicht"
            }

            st.write("Wähle bis zu 5 Unternehmen (Duplikate möglich):")

            Input.i_companies = []
            for i in range(5):
                choice = st.selectbox(
                    f"Unternehmen {i + 1}",
                    options=[None] + list(options.keys()),
                    format_func=lambda x: "Keine" if x is None else options[x],
                    key=f"selection_{i}"
                )
                if choice is not None:
                    Input.i_companies.append(choice)

        # Explanation expander
        with col2_tab4:
            Input.i_heat_cooling_electric = st.toggle("Mit Wärme/Kälte Stromverbrauch?")
            expander = st.expander("Erklärung Wärme/Kälte")
            expander.write('''
    Bei Auswahl "ohne Wärme/Kälte Stromverbrauch" werden fossiler Energiequellen für Wärme benutzt und es gibt keine Kälte

    Bei Auswahl "mit Wärme/Kälte Stromverbrauch" werden reversible Luftwärmepumpen und Geothermie-Sonden verwendet
            ''')

            # Dynamic info box
            st.write('\n')
            if not Input.i_companies:
                st.info("Industriegebiet deaktiviert.")
            else:
                st.info("Industriegebiet aktiv.")

        preview_csv_path = os.path.join(
            script_dir,
            "data",
            "inputs",
            "Projekt_04_Lastgaenge_Industriegebiet_und_nPro_Waerme_Kaelte.csv"
        )

        expander = st.expander("Erklärung Unternehmen")
        with expander:

            st.markdown('''
    1. **Entsorgung:**  
    5 1/2 Tage Woche, Kein Schichtbetrieb  
                        Jahresbedarf: 7,1 GWh, Anlehnung an Schönmackers Umweltdienste

    2. **Stahl 1:**  
    5 Tage Woche, 3-Schicht-Betrieb  
                        Jahresbedarf: 4,5 GWh, Anlehnung an TecPro

    3. **Logistik und Lagerung:**  
    5 Tage Woche, Teilweise Samstag und Sonntag Betrieb, Kein Schichtbetrieb  
                        Jahresbedarf: 1,2 GWh, Anlehnung an CTJ Janssen

    4. **Schrott- und Metallhandel:**  
    5 Tage Woche, Kein Schichtbetrieb  
                        Jahresbedarf: 1,5 GWh, Anlehnung an Willi Jenner

    5. **Lagerung:**  
    5 Tage Woche, Kein Schichtbetrieb  
                        Jahresbedarf: 0,6 GWh, Anlehnung an Kleine Logistik

    6. **Büro:**  
    5 Tage Woche, Kein Schichtbetrieb  
                        Jahresbedarf: 0,6 GWh, Anlehnung an Marvin Wickenhäuser

    7. **Logistik Lebensmittel:**  
    6 1/2 Tage Woche, Kein Schichtbetrieb  
                        Jahresbedarf: 1,2 GWh, Anlehnung an CTJ Janssen

    8. **Stahl 2:**  
    7 Tage Woche, 2-Schicht-Betrieb  
                        Jahresbedarf: 4,5 GWh, Anlehnung an TecPro
            ''')

            fig_annual_all = plot_industry_annual_energy(
                preview_csv_path,
                ordered_columns=industry_order_all,
                title="Jahresenergiebedarf aller Unternehmensprofile (inkl. Wärme & Kälte)"
            )
            st.pyplot(fig_annual_all)

        selected_columns = [industry_csv_mapping[i] for i in Input.i_companies if i in industry_csv_mapping]
        selected_columns = list(dict.fromkeys(selected_columns))

        # Plot example week of selected companies
        if selected_columns:
            st.write("#### Beispielhafte Wochenlastgänge der ausgewählten Unternehmen (inkl. Wärme & Kälte)")

            fig_preview = plot_industry_preview(
                preview_csv_path,
                selected_columns=selected_columns,
                start="2017-03-05"
            )
            st.pyplot(fig_preview)

    # ---------------- Green energy hub ----------------
    with tab5:
        green_hub_base_dir = os.path.join(
            script_dir,
            "data",
            "inputs",
            "green_energy_hub"
        )

        # Explanation expander
        expander = st.expander("Erklärung")
        with expander:
            st.write("""
    **Allgemeine Daten**
    - Elektrolyseur Wirkungsgrad 70%
    - Wasserstoffspeicher (Gas) 10 MWh Kapazität
    - keine PV- oder Windanlagen
    - Ladepunkt Berechnung ohne Wartezeiten
    - BEV Ladesäulen mit 200 kW Leistung
    - Darstellung des Strombedarfs des Elektrolyseurs und der BEV-Ladesäulen
    - Anteil der Anzahl an FCEVs für jedes Jahr: PKW 92.77% , LKW 7.07% , Busse 0.16%

    **Szenario 2022**
    - 5 BEV-Ladesäulen
    - 3 Wasserstoff-Ladesäulen
    - Elektrolyseur mit einer Leistung von ca. 8 MW um H2 Bedarf zu decken
    - Anzahl BEV-Ladevorgänge: 10.381

    **Szenario 2030**
    - 6 BEV-Ladesäulen
    - 8 Wasserstoff-Ladesäulen
    - Elektrolyseur mit einer Leistung von ca. 30 MW
    - Anzahl an FCEVs: 1.800.000
    - Anzahl BEV-Ladevorgänge: 12.154

    **Szenario 2050**
    - 6 BEV-Ladesäulen
    - 8 Wasserstoff-Ladesäulen
    - Elektrolyseur mit einer Leistung von ca. 18 MW
    - Anzahl an FCEVs: 4.560.000
    - Anzahl BEV-Ladevorgänge: 16.587

    **Einordnung der geringeren Elektrolyseurleistung im Jahr 2050**
    Die geringere Elektrolyseurleistung im Vergleich zum Szenario 2030 ist modellseitig dadurch begründet,
    dass nicht allein die Anzahl der Ladepunkte entscheidend ist, sondern vor allem die angenommene
    Wasserstoffnachfrage und deren zeitliche Spitzenlast am betrachteten Standort. Im 2050-Szenario verteilt
    sich die Nachfrage auf eine stärker ausgebaute Infrastruktur, sodass an diesem Standort trotz ausgebauter
    Tankstellenstruktur eine geringere Elektrolyseurleistung ausreicht.
            """)

            fig_green_hub_bar = plot_green_hub_annual_energy(
                green_hub_base_dir,
                years=("2022", "2030", "2050")
            )
            st.pyplot(fig_green_hub_bar)

        scenario_options = ["Keine", "2022", "2030", "2050"]

        Input.geh_h2_load_scenario = st.radio(
            "Wasserstoff-Bedarf Szenario",
            options=scenario_options,
            index=0,
            horizontal=True
        )

        Input.geh_h2_load_scenario = "Keine" if Input.geh_h2_load_scenario is None else Input.geh_h2_load_scenario

        Input.geh_e_load_scenario = st.radio(
            "Elektro-Bedarf Szenario",
            options=scenario_options,
            index=0,
            horizontal=True
        )

        Input.geh_e_load_scenario = "Keine" if Input.geh_e_load_scenario is None else Input.geh_e_load_scenario

        geh_h2_active = Input.geh_h2_load_scenario != "Keine"
        geh_e_active = Input.geh_e_load_scenario != "Keine"
        green_hub_active = geh_h2_active or geh_e_active

        # Plot example week of selected H2/electric szenario
        if green_hub_active:
            st.write("#### Beispielhafte Wochenlastprofile der ausgewählten Green-Energy-Hub-Szenarien")

            fig_green_hub_week = plot_green_hub_weekly_profiles(
                green_hub_base_dir,
                h2_year=Input.geh_h2_load_scenario,
                e_year=Input.geh_e_load_scenario,
                start="2022-03-05"
            )
            st.pyplot(fig_green_hub_week)
        else:
            st.info("Green Energy Hub ist deaktiviert.")


        # ---------------- Jüchen Süd ----------------
        with tab6:
            st.write("Wähle das Szenario für das Neubaugebiet Jüchen Süd:")

            js_options = {
                "Aus": 0,
                "1000 Bewohner": 1,
                "2000 Bewohner": 2,
                "3000 Bewohner": 3
            }

            Input.js_scenario = st.radio(
                "Szenario",
                options=list(js_options.keys()),
                index=0,
                horizontal=True
            )

            Input.js_scenario = "Aus" if Input.js_scenario is None else Input.js_scenario

            js_factor = js_options[Input.js_scenario]

            # Dynamic info box
            if js_factor == 0:
                st.info("Jüchen Süd ist deaktiviert.")
            else:
                st.info(
                    f"""
                    **Jüchen Süd aktiv:**  
                    Szenario: **{Input.js_scenario}**  
                    Skalierungsfaktor Lastgang: **x{js_factor}**
                    """
                )

                # 👉 Plot
                js_csv_path = os.path.join(
                    script_dir,
                    "data",
                    "inputs",
                    "Strombezug_Stadtentwicklung_15min.csv"
                )

                st.write("#### Beispielhafte Wochenlastprofile Jüchen Süd")

                fig_js = plot_js_weekly_profile(
                    js_csv_path,
                    scale_factor=js_factor,
                    start="2022-03-05"
                )

                st.pyplot(fig_js)


# Separation line
col1, col2, col3 = st.columns([0.05, 0.9, 0.05])
with col2:
    st.divider()


# ---------------- Battery input ----------------
st.write("### Batterie Eingabewerte")

with st.container():

    #tab7 = st.tabs(["Batterie"])
    # Batterie
    #with tab7:

    capacity_mode = st.radio(
        "Kapazität wählen über",
        options=["Standardwert", "Eigene Eingabe"],
        horizontal=True
    )

    if capacity_mode == "Standardwert":
        Input.bs_energy_kwh = st.radio(
            "Kapazität",
            options=[0, 10000, 50000, 100000, 235000],
            index=0,
            horizontal=True,
            format_func=lambda x: f"{x / 1000:.0f} MWh"
        )
    else:
        custom_mwh = st.number_input(
            "Eigene Kapazität [MWh]",
            min_value=0.0,
            value=42.0,
            step=1.0,
            max_value = 100000.0
        )
        Input.bs_energy_kwh = int(custom_mwh * 1000)

    Input.bs_energy_kwh = 0 if Input.bs_energy_kwh is None else Input.bs_energy_kwh

    st.write("\n")

    Input.bs_efficiency = st.select_slider(
        "Roundtrip Effizienz",
        options=[round(x, 3) for x in list(np.arange(0.8, 1.01, 0.01))],
        value=1.0,
        format_func=lambda x: f"{x:.0%}"
    )

    bat_active = (
            Input.bs_energy_kwh > 0
    )

    Input.bs_c_rate = st.select_slider(
        "C-Rate",
        options=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        value=1.0,
        format_func=lambda x: f"{x:.2g} C"
    )

    # Dynamic info box
    if bat_active:
        st.info(
            f"""
            **Batterie aktiv:**

            Kapazität: **{Input.bs_energy_kwh / 1000:.0f} MWh**  
            Roundtrip Effizienz: **{Input.bs_efficiency:.0%}**  
            C-Rate: **{Input.bs_c_rate:.2g} C**
            """
        )
    else:
        st.info("Batterie deaktiviert.")



st.write("")
col1, col2, col3 = st.columns([0.15, 0.7, 0.15])


# ---------------- Run simulation ----------------
with col2:
    run = st.button(
        "⚡ Simulation starten",
        type="primary",
        use_container_width=True
    )
st.write("")

# if button is pressed, actual simulation is started
if run:
    with st.spinner("Simulation läuft..."):
        Output = run_simulation(Input)          # Simulation call

    st.success("Simulation abgeschlossen.")

    # Safe simulation state and output in session state
    st.session_state.simulation_ran = True
    st.session_state.sim_output = Output
    #print('\nOutput Daten:\n', Output)     #debug
    #st.write(Output.res_df.columns)        #debug





# ---------------- Support function: KPIs and Energy flow visualization ----------------
st.write("### Ergebnisse")
with st.spinner("Visualisierung wird erstellt..."):
    fig_synergy = build_synergy_diagram(Input, st.session_state.sim_output)
    st.plotly_chart(fig_synergy, use_container_width=True)



# ---------------- Additional Results (if Sim ran) ----------------
if st.session_state.get("simulation_ran") and "sim_output" in st.session_state:

    sim_output = st.session_state.sim_output

    # Drop zero columns
    protected_cols = ["Bilanz [kW]"]
    zero_cols = [
        col for col in sim_output.res_df.columns
        if col not in protected_cols and sim_output.res_df[col].fillna(0).eq(0).all()
    ]

    sim_output.res_df = sim_output.res_df.drop(columns=zero_cols)


    # ---------------- Net balance Plot ----------------
    st.write("### Bilanzverlauf")

    # Balance from res_df (no battery) or bs_df (if battery)
    fig0 = plot_balance(sim_output)
    st.pyplot(fig0)


    # ---------------- Detailed information expander ----------------
    with st.expander("Lastgang Infos anzeigen", expanded=False):
        desc_stats = sim_output.res_df
        desc = desc_stats.describe().loc[["mean", "min", "max"]].round(0)
        desc.loc["sum [kWh]"] = desc_stats.sum()/4
        desc.loc["sum [kWh]"] = desc.loc["sum [kWh]"].round(0)
        desc = desc.loc[["sum [kWh]", "mean", "min", "max"]]
        st.dataframe(desc)

        # Plot 1: Generation
        fig = plot_generation(sim_output)
        st.pyplot(fig)

        # Plot 2: Consumption
        fig2 = plot_consumption(sim_output)
        st.pyplot(fig2)



    # ---------------- Battery details expander ----------------
    if not sim_output.bs_df.empty:

        with st.expander("Batterieergebnisse anzeigen", expanded=False):

            # Stats
            bs_desc_stats = sim_output.bs_df.drop(columns=['soc_kwh'])
            bs_desc = bs_desc_stats.describe().loc[["mean", "min", "max"]].round(0)
            bs_desc.loc["sum [kWh]"] = bs_desc_stats.sum()/4
            bs_desc.loc["sum [kWh]"] = bs_desc.loc["sum [kWh]"].round(0)
            bs_desc = bs_desc.loc[["sum [kWh]", "mean", "min", "max"]]

            bs_desc = bs_desc.rename(columns={
                "balance_kw": "Bilanz ohne Batterie [kW]",
                "new_balance_kw": "Bilanz mit Batterie [kW]",
                "battery_power_kw": "Batterieleistung [kW]",
            })
            st.dataframe(bs_desc)


            # Battery Plots
            fig3, fig4 = plot_battery_comparison(sim_output)
            # Plot 1: Balance with battery storage
            st.pyplot(fig3)
            # Plot 2: Balance withOUT battery storage
            st.pyplot(fig4)


            # Plot 3: State of charge
            fig5 = plot_soc(Input, sim_output)
            st.pyplot(fig5)
