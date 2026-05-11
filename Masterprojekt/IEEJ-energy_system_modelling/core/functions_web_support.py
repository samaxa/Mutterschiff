#Übergabe fertig Felix
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import os
import base64

# ---------------- Directory Paths ----------------
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
icon_dir = os.path.join(project_dir, "data", "inputs", "icon")

# ---------------- Icons ----------------
ICON_PATHS = {
    "solar": os.path.join(icon_dir, "solar_highway.png"),
    "landscape": os.path.join(icon_dir, "energy_landscape.png"),
    "battery": os.path.join(icon_dir, "battery_storage.png"),
    "industry": os.path.join(icon_dir, "industrial_area.png"),
    "hub": os.path.join(icon_dir, "green_energy_hub.png"),
    "grid": os.path.join(icon_dir, "grid_supply.png"),
    "js": os.path.join(icon_dir, "juechen_sued.png"),
}

ICON_SCALE = {
    "solar": 0.96,
    "landscape": 0.96,
    "industry": 1.2,
    "hub": 1.2,
    "battery": 0.6,
    "grid": 0.5,
    "js": 0.8,
}

# ---------------- PNG to base64 ----------------
def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------- Format units ----------------
def format_energy(value_kwh):
    """
    Formatting energy per year values do display suitable unit.
    """
    value_kwh = float(value_kwh or 0)

    if value_kwh >= 1_000_000:
        return f"{value_kwh / 1_000_000:.2f} GWh/a"
    elif value_kwh >= 1_000:
        return f"{value_kwh / 1_000:.1f} MWh/a"
    else:
        return f"{value_kwh:.0f} kWh/a"

def format_capacity(value_kwh):
    """
    Formatting energy for capacity / SOC
    """
    value_kwh = float(value_kwh or 0)

    if value_kwh >= 1_000_000:
        return f"{value_kwh / 1_000_000:.2f} GWh"
    elif value_kwh >= 1_000:
        return f"{value_kwh / 1_000:.1f} MWh"
    else:
        return f"{value_kwh:.0f} kWh"

def format_power(value_kw):
    """
    Formatting power values do display suitable unit.
    """
    if value_kw is None:
        value_kw = 0

    if abs(value_kw) >= 1000:
        return f"{value_kw / 1000:.2f} MW"
    return f"{value_kw:.1f} kW"


# ---------------- plotly functions for visualization ----------------
def add_node_with_icon(fig, x, y, label, icon_key, box_w, box_h, label_pos="below"):
    """
    Adds icon and annotation.
    white background box is drawn separately
    """
    icon_path = ICON_PATHS.get(icon_key)
    scale = ICON_SCALE.get(icon_key, 0.80)

    if icon_path and os.path.exists(icon_path):
        fig.add_layout_image(
            dict(
                source=Image.open(icon_path).convert("RGBA"),
                xref="x",
                yref="y",
                x=x,
                y=y,
                sizex=box_w * scale,
                sizey=box_h * scale,
                xanchor="center",
                yanchor="middle",
                layer="above"
            )
        )

    if label_pos == "above":
        label_y = y + box_h / 2 + 0.04
    else:
        label_y = y - box_h / 2 - 0.04

    fig.add_annotation(
        x=x,
        y=label_y,
        text=f"<b>{label}</b>",
        showarrow=False,
        align="center",
        font=dict(size=12, color="#222222")
    )

def add_routed_arrow(fig, points, color, width=2.5, label=None, label_x=None, label_y=None):
    """
    Draws routed arrow from multiple segments, arrow heads will only be placed at the end
    'points' is a list of (x,y)-points.
    """
    if len(points) < 2:
        return

    # All segments excluding the last one without arrow head
    for i in range(len(points) - 2):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        fig.add_shape(
            type="line",
            x0=x0, y0=y0,
            x1=x1, y1=y1,
            line=dict(color=color, width=width)
        )

    # Last segment with arrow head
    x0, y0 = points[-2]
    x1, y1 = points[-1]
    fig.add_annotation(
        x=x1,
        y=y1,
        ax=x0,
        ay=y0,
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowhead=3,
        arrowsize=1.0,
        arrowwidth=width,
        arrowcolor=color,
        text=""
    )

    # Optional label
    if label:
        if label_x is None or label_y is None:
            label_x = (x0 + x1) / 2
            label_y = (y0 + y1) / 2 + 0.03

        fig.add_annotation(
            x=label_x,
            y=label_y,
            text=f"<span style='font-size:11px'>{label}</span>",
            showarrow=False,
            font=dict(size=11, color=color),
            bgcolor="rgba(255,255,255,0.85)"
        )

def scale_arrow_width(flow_value, max_flow, min_width=2.0, max_width=5.8):
    """
    Linear scaling of arrow width based on energy flow.
    max / min values as range for width.
    """
    flow_value = float(flow_value or 0)
    max_flow = float(max_flow or 1)

    if flow_value <= 0:
        return min_width

    return min_width + (flow_value / max_flow) * (max_width - min_width)


def add_legend(fig):
    """
    Legend at the bottom of energy flow visualization
    """

    legend_y1 = -0.15
    #legend_y2 = 0.035

    # Line 1:
    items_row1 = [
        ("Erneuerbare Energie", "#10B35A", 0.1, "solid"),
        ("Batterie Energiefluss", "#1DA1F2", 0.4, "solid"),
        ("Netzstrombezug", "#B9B9B9", 0.7, "solid"),
    ]

    # Line 2: dotted lines
    #items_row2 = [        ("Optionale Nutzung", "#1DA1F2", 0.1, "dot"),        ("Netzanbindung", "#A8A8A8", 0.4, "dot"),]

    for text, color, x, dash in items_row1:
        fig.add_shape(
            type="line",
            x0=x,
            y0=legend_y1,
            x1=x + 0.05,
            y1=legend_y1,
            line=dict(color=color, width=3, dash=dash)
        )
        fig.add_annotation(
            x=x + 0.06,
            y=legend_y1,
            text=text,
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(size=11, color="#333333")
        )


def add_optional_connection(fig, points, color="#1DA1F2", width=1.6, dash="dot", label=None, label_x=None, label_y=None):
    """
    Draws optional connection. Used to display dotted lines showing grid power usage.
    """
    if len(points) < 2:
        return

    for i in range(len(points) - 2):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        fig.add_shape(
            type="line",
            x0=x0, y0=y0,
            x1=x1, y1=y1,
            line=dict(color=color, width=width, dash=dash)
        )

    x0, y0 = points[-2]
    x1, y1 = points[-1]

    fig.add_shape(
        type="line",
        x0=x0, y0=y0,
        x1=x1, y1=y1,
        line=dict(color=color, width=width, dash=dash)
    )

    dx = x1 - x0
    dy = y1 - y0

    # Minimum length for arrow heads
    arrow_len = 0.025

    if abs(dx) >= abs(dy):  # horizontal
        ax = x1 - arrow_len if dx >= 0 else x1 + arrow_len
        ay = y1
    else:  # vertikal
        ax = x1
        ay = y1 - arrow_len if dy >= 0 else y1 + arrow_len

    fig.add_annotation(
        x=x1,
        y=y1,
        ax=ax,
        ay=ay,
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=False,
        arrowhead=3,
        arrowsize=1.2,
        arrowwidth=max(width, 1.8),
        arrowcolor=color,
        text=""
    )

    if label:
        fig.add_annotation(
            x=label_x if label_x is not None else (x0 + x1) / 2,
            y=label_y if label_y is not None else (y0 + y1) / 2 + 0.02,
            text=f"<span style='font-size:10px'>{label}</span>",
            showarrow=False,
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.75)"
        )



def build_synergy_diagram(inp, sim_output):
    """
    System visualization of energy flow balance:

    - Solar highway + Energy landscape feed into central system knot
    - central system knot supplies Industrial area and Green energy hub

    if annual surplus: arrow from system to grid
    if annual deficit: arrow from grid to system
    if battery enabled: back and forth arrow between system knot and battery
    """

    # =========================================================
    # 1) Import simulation values
    # =========================================================
    solar_energy = 0.0
    landscape_energy = 0.0
    industry_energy = 0.0
    green_hub_energy = 0.0
    total_generation = 0.0
    total_demand = 0.0
    coverage_percent = 0.0
    surplus = 0.0
    deficit = 0.0
    battery_charge_kwh = 0.0
    battery_discharge_kwh = 0.0
    battery_max_charge_kw = 0.0
    battery_grid_import_kwh = 0.0
    battery_grid_export_kwh = 0.0
    juechen_sued_energy = 0.0

    ee_self_consumption = 0.0
    autarky = 0.0

    max_power_from_grid = 0.0
    max_power_to_grid = 0.0


    if sim_output is not None:
        solar_energy = max(float(getattr(sim_output, "h_sum_energy_kwh", 0) or 0), 0.0)
        landscape_energy = max(float(getattr(sim_output, "el_sum_energy_kwh", 0) or 0), 0.0)
        industry_energy = max(float(getattr(sim_output, "i_sum_energy_kwh", 0) or 0), 0.0)
        green_hub_energy = max(float(getattr(sim_output, "geh_sum_energy_kwh", 0) or 0), 0.0)
        juechen_sued_energy = max(float(getattr(sim_output, "js_sum_energy_kwh", 0) or 0), 0.0)

        bs_stats = getattr(sim_output, "bs_stats", {}) or {}
        battery_charge_kwh = float(bs_stats.get("battery_charge_kwh", 0) or 0)
        battery_discharge_kwh = float(bs_stats.get("battery_discharge_kwh", 0) or 0)
        battery_max_charge_kw = float(bs_stats.get("max_charge_kw", 0) or 0)
        battery_grid_import_kwh = float(bs_stats.get("grid_import_kwh", 0) or 0)
        battery_grid_export_kwh = float(bs_stats.get("grid_export_kwh", 0) or 0)

        ee_self_consumption = max(float(getattr(sim_output, "ee_self_consumption", 0) or 0), 0.0)
        autarky  = max(float(getattr(sim_output, "autarky", 0) or 0), 0.0)


        if autarky > 1:
            autarky = 1

        total_generation = solar_energy + landscape_energy
        total_demand = industry_energy + green_hub_energy + juechen_sued_energy

        if not sim_output.bs_df.empty:
            max_power_from_grid = sim_output.bs_df['new_balance_kw'].min()
            max_power_to_grid = sim_output.bs_df['new_balance_kw'].max()
        elif not sim_output.res_df.empty:
            max_power_from_grid = sim_output.res_df['Bilanz [kW]'].min()
            max_power_to_grid = sim_output.res_df['Bilanz [kW]'].max()

        coverage = float(getattr(sim_output, "bal_coverage_rate", 0) or 0)
        coverage_percent = max(0.0, min(coverage * 100.0, 100.0))

        balance = float(getattr(sim_output, "bal_energy_kwh", 0) or 0)
        if balance >= 0:
            surplus = balance
            deficit = 0.0
        else:
            surplus = 0.0
            deficit = abs(balance)

    # =========================================================
    # 2) Balance for Visualization
    # =========================================================
    # Local coverage
    total_generation = solar_energy + landscape_energy
    total_demand = industry_energy + green_hub_energy + juechen_sued_energy

    balance = float(getattr(sim_output, "bal_energy_kwh", 0) or 0)

    if balance >= 0:
        surplus = balance
        grid_import_total = 0.0
        grid_export = balance
    else:
        surplus = 0.0
        grid_import_total = abs(balance)
        grid_export = 0.0

    grid_export = surplus

    # Quellaufteilung Solar / Landschaft für die Abgänge vom linken Bereich
    total_gen_for_split = solar_energy + landscape_energy
    if total_gen_for_split > 0:
        solar_share = solar_energy / total_gen_for_split
        landscape_share = landscape_energy / total_gen_for_split
    else:
        solar_share = 0.0
        landscape_share = 0.0

    solar_to_system = total_generation * solar_share
    landscape_to_system = total_generation * landscape_share

    # Batterie nur visuell aktiv/inaktiv
    battery_active = bool(getattr(inp, "bs_energy_kwh", 0) and getattr(inp, "bs_energy_kwh", 0) > 0)

    # =========================================================
    # 3) Texts for Hover
    # =========================================================

    # Solar highway Hover
    solar_text = "nicht aktiv"
    if inp.h_highways and inp.h_pv_types:
        solar_text = (
            f"Jahreserzeugung:<br>{format_energy(solar_energy)}"
            if solar_energy > 0 else
            "aktiv, noch ohne Ergebnis"
        )

    landscape_text = "nicht aktiv"
    if inp.el_build_state != 0:
        landscape_text = (
            f"Jahreserzeugung:<br>{format_energy(landscape_energy)}"
            if landscape_energy > 0 else
            f"Ausbaugrad: {inp.el_build_state} %<br>aktiv, noch ohne Ergebnis"
        )

    n_companies = len([c for c in inp.i_companies if c is not None]) if inp.i_companies else 0

    # Industrial area Hover
    industry_active = industry_energy > 0

    industry_text = (
        f"Status: {'aktiv' if industry_active else 'nicht aktiv'}"
        f"<br>Auswahl: {n_companies} Unternehmen"
        f"<br>Jahresbedarf: {format_energy(industry_energy)}"
    )

    # Green Energy Hub Hover
    geh_active = (
            inp.geh_h2_load_scenario not in [None, "Keine"] or
            inp.geh_e_load_scenario not in [None, "Keine"]
    )

    status = "aktiv" if geh_active else "nicht aktiv"

    hub_text = (
        f"Status: {status}"
        f"<br>H₂-Szenario: {inp.geh_h2_load_scenario}"
        f"<br>El.-Szenario: {inp.geh_e_load_scenario}"
        f"<br>Jahresbedarf: {format_energy(green_hub_energy)}"
    )

    # Jüchen-Süd Hover
    js_active = inp.js_scenario not in [None, "Aus"]

    js_text = (
        f"Status: {'aktiv' if js_active else 'nicht Aktiv'}"
        f"<br>Szenario: {inp.js_scenario}"
        f"<br>Jahresbedarf: {format_energy(juechen_sued_energy)}"
    )

    # Battery Hover
    battery_text = (
        f"Status: {'aktiv' if battery_active else 'nicht aktiv'}"
        f"<br>Kapazität: {format_capacity(float(getattr(inp, 'bs_energy_kwh', 0) or 0))}"
        f"<br>Jährliche Ladung: {format_energy(battery_charge_kwh)}"
        f"<br>Jährliche Entladung: {format_energy(battery_discharge_kwh)}"
        f"<br>Max. Leistung: {battery_max_charge_kw:.0f} kW"
    )

    # Grid Hover
    grid_text = (
        f"Import: {format_energy(grid_import_total)}"
        f"<br>Export: {format_energy(grid_export)}"
    )

    if surplus > 0:
        system_text = (
            f"Gesamterzeugung: {format_energy(total_generation)}"
            f"<br>Gesamtbedarf: {format_energy(total_demand)}"
            f"<br>Bilanz: + {format_energy(surplus)}"
            f"<br>Bilanzielle Autarkie: {coverage_percent:.1f} %"
        )
    else:
        system_text = (
            f"Gesamterzeugung: {format_energy(total_generation)}"
            f"<br>Gesamtbedarf: {format_energy(total_demand)}"
            f"<br>Bilanz: - {format_energy(deficit)}"
            f"<br>Bilanzielle Autarkie: {coverage_percent:.1f} %"
        )

    # =========================================================
    # 4) Node/Item positions
    # =========================================================
    nodes = {
        "solar": {
            "x": 0.1, "y": 0.48,
            "label": "Solarautobahn",
            "info": solar_text,
            "icon": "solar"
        },
        "landscape": {
            "x": 0.1, "y": 0.18,
            "label": "Energielandschaft",
            "info": landscape_text,
            "icon": "landscape"
        },
        "grid": {
            "x": 0.50, "y": 0.65,
            "label": "Stromnetz",
            "info": grid_text,
            "icon": "grid"
        },
        "system": {
            "x": 0.54, "y": 0.33,
            "label": "",
            "info": system_text,
            "icon": None
        },
        "battery": {
            "x": 0.50, "y": 0.03,
            "label": "Batterie Speicher",
            "info": battery_text,
            "icon": "battery"
        },
        "industry": {
            "x": 0.98, "y": 0.59,
            "label": "Industriegebiet",
            "info": industry_text,
            "icon": "industry"

        },
        "js": {
            "x": 0.98, "y": 0.33,
            "label": "Stadtteil Jüchen Süd",
            "info": js_text,
            "icon": "js"

        },
        "hub": {
            "x": 0.98, "y": 0.07,
            "label": "Green Energy Hub",
            "info": hub_text,
            "icon": "hub"
        }

    }

    # =========================================================
    # 5) Figure Setup
    # =========================================================
    fig = go.Figure()
    fig.update_xaxes(visible=False, range=[-0.02, 1.10])
    fig.update_yaxes(visible=False, range=[-0.15, 1.10])

    box_w = 0.2
    box_h = 0.15

    COLOR_RENEWABLE = "#10B35A"
    COLOR_GRID = "#B9B9B9"
    COLOR_OPTIONAL = "#11c2bc"

    flow_values = [
        solar_energy,
        landscape_energy,
        industry_energy,
        juechen_sued_energy,
        green_hub_energy,
        grid_import_total,
        grid_export
    ]

    max_flow = max(flow_values) if max(flow_values) > 0 else 1.0


    # --------------------- KPIs -------------------------
    fig.add_annotation(
        x=0.03,
        y=0.95,
        xref="paper",
        yref="paper",
        text="<b>KPIs:</b>",
        showarrow=False,
        font=dict(size=20, color="#2F3445"),
        align="left",
        xanchor="center",
        yanchor="bottom"
    )

    # KPIs first line
    kpi_y_first = 1.05
    x_min_first = 0.22
    x_max_first = 0.98
    kpis_first_line = [
        ("Erzeugung", format_energy(total_generation), '#4fe091'),
        ("Bedarf", format_energy(total_demand), '#f0af46'),#f08e46'),
        ("Bilanz", f"+ {format_energy(surplus)}" if surplus > 0 else f"- {format_energy(deficit)}", '#c5f5db' if surplus > 0 else '#fae5c2'),# "#FFF4E8"),
        ("Bilanzielle<br>Autarkie", f"{coverage_percent:.1f} %", "#EEF9EE"),
    ]

    # KPIs second line
    kpi_y_second = 0.91
    x_min_second = 0.35#0.17
    x_max_second = 0.85#0.93
    kpis_second_line = [
        #("Batterie-Ladung", format_energy(battery_charge_kwh), "#E8F7FF"),
        #("Autarkie", f"{autarky*100:.1f} %", "#e8f2ff"),
        ("Eigenenergie-<br>nutzung", f"{ee_self_consumption*100:.1f} %", "#e8e8ff"),

        #("Netzbezug nach Batterie", format_energy(battery_grid_import_kwh), "#E8F7FF"),
        #("Netzeinspeisung nach Batterie", format_energy(battery_grid_export_kwh), "#F3E8FF"),
        ("Maximaler <br>Netzbezug", format_power(max_power_from_grid), "#c7c7c7"),#dfdfdf"),
        ("Maximale <br>Einspeisung", format_power(max_power_to_grid), "#f0f0f0"), #e6e6e6"),
    ]

    # Create first line KPIs
    if len(kpis_first_line) == 1:
        kpi_xs_first = [(x_min_first + x_max_first) / 2]
    else:
        step = (x_max_first - x_min_first) / (len(kpis_first_line) - 1)
        kpi_xs_first = [x_min_first + i * step for i in range(len(kpis_first_line))] #[0.06, 0.25, 0.44, 0.63, 0.82, 1.01]

    for (title, value_text, fill), x in zip(kpis_first_line, kpi_xs_first):
        fig.add_shape(
            type="rect",
            x0=x - 0.08, x1=x + 0.08, #x0=x - 0.08, x1=x + 0.08,
            y0=kpi_y_first - 0.05, y1=kpi_y_first + 0.05, #y0=kpi_y - 0.045, y1=kpi_y + 0.045,
            line=dict(color="rgba(80,80,80,0.45)", width=1.1),
            fillcolor=fill,
            layer="below"
        )
        fig.add_annotation(
            x=x,
            y=kpi_y_first,
            text=f"<b>{title}</b><br>{value_text}",
            showarrow=False,
            font=dict(size=12, color="#2F3445"),
            align="center"
        )


    # Create second line KPIs
    if len(kpis_second_line) == 1:
        kpi_xs_second = [(x_min_second + x_max_second) / 2]
    else:
        step = (x_max_second - x_min_second) / (len(kpis_second_line) - 1)
        kpi_xs_second = [x_min_second + i * step for i in range(len(kpis_second_line))] #[0.06, 0.25, 0.44, 0.63, 0.82, 1.01]

    for (title, value_text, fill), x in zip(kpis_second_line, kpi_xs_second):
        fig.add_shape(
            type="rect",
            x0=x - 0.08, x1=x + 0.08, #x0=x - 0.08, x1=x + 0.08,
            y0=kpi_y_second - 0.05, y1=kpi_y_second + 0.05, #y0=kpi_y - 0.045, y1=kpi_y + 0.045,
            line=dict(color="rgba(80,80,80,0.45)", width=1.1),
            fillcolor=fill,
            layer="below"
        )
        fig.add_annotation(
            x=x,
            y=kpi_y_second,
            text=f"<b>{title}</b><br>{value_text}",
            showarrow=False,
            font=dict(size=12, color="#2F3445"),
            align="center"
        )

    # =========================================================
    # 6) Boxes and Nodes
    # =========================================================

    fig.add_annotation(
        x=0.095,
        y=0.7,
        xref="paper",
        yref="paper",
        text="<b>Energiebilanz:</b>",
        showarrow=False,
        font=dict(size=20, color="#2F3445"),
        align="left",
        xanchor="center",
        yanchor="bottom"
    )

    add_legend(fig)

    # Rectangular shapes with icons
    for key in ["solar", "landscape", "grid", "battery", "industry", "hub", "js"]:
        node = nodes[key]
        x = node["x"]
        y = node["y"]

        fig.add_shape(
            type="rect",
            x0=x - box_w / 2,
            x1=x + box_w / 2,
            y0=y - box_h / 2,
            y1=y + box_h / 2,
            line=dict(color="black", width=2),
            fillcolor="white",
            layer="below"
        )

        label_pos = "below" if key in ["battery"] else "above"

        add_node_with_icon(
            fig=fig,
            x=x,
            y=y,
            label=node["label"],
            icon_key=node["icon"],
            box_w=box_w,
            box_h=box_h,
            label_pos=label_pos
        )

    # Central system knot
    system = nodes["system"]
    fig.add_shape(
        type="circle",
        x0=system["x"] - 0.025, x1=system["x"] + 0.025,
        y0=system["y"] - 0.025, y1=system["y"] + 0.025,
        line=dict(color="gray", width=1.2),
        fillcolor="white"
    )

    # Hover points
    for key, node in nodes.items():
        marker_size = 26 if key == "system" else 60
        fig.add_trace(
            go.Scatter(
                x=[node["x"]],
                y=[node["y"]],
                mode="markers",
                marker=dict(size=marker_size, opacity=0),
                hovertemplate=f"<b>{node['label'] if node['label'] else 'Systemknoten'}</b><br>{node['info']}<extra></extra>",
                showlegend=False
            )
        )

    # =========================================================
    # 7) Support points for arrows
    # =========================================================
    solar_right = (nodes["solar"]["x"] + box_w / 2, nodes["solar"]["y"])
    landscape_right = (nodes["landscape"]["x"] + box_w / 2, nodes["landscape"]["y"])
    grid_bottom = (nodes["grid"]["x"], nodes["grid"]["y"] - box_h / 2)
    battery_top = (nodes["battery"]["x"], nodes["battery"]["y"] + box_h / 2)
    industry_left = (nodes["industry"]["x"] - box_w / 2, nodes["industry"]["y"])
    hub_left = (nodes["hub"]["x"] - box_w / 2, nodes["hub"]["y"])
    system_center = (nodes["system"]["x"], nodes["system"]["y"])
    js_left = (nodes["js"]["x"] - box_w / 2, nodes["js"]["y"])

    x_left_join = (system_center[0]+solar_right[0])/2 -0.07
    x_right_split = (system_center[0]+industry_left[0])/2 +0.03

    half_y_grid =  (grid_bottom[1]+system_center[1])/2
    half_y_bat =  (battery_top[1]+system_center[1])/2

    # =========================================================
    # 8) Generation -> System
    # =========================================================
    if solar_to_system > 0:
        add_routed_arrow(
            fig,
            points=[solar_right, (x_left_join, solar_right[1]), (x_left_join, system_center[1]), system_center],
            color=COLOR_RENEWABLE,
            width=scale_arrow_width(solar_to_system, max_flow)
        )

    if landscape_to_system > 0:
        add_routed_arrow(
            fig,
            points=[landscape_right, (x_left_join, landscape_right[1]), (x_left_join, system_center[1]), system_center],
            color=COLOR_RENEWABLE,
            width=scale_arrow_width(landscape_to_system, max_flow)
        )

    # =========================================================
    # 9) System -> Consumption
    # =========================================================
    if industry_energy > 0:
        add_routed_arrow(
            fig,
            points=[system_center, (x_right_split, system_center[1]), (x_right_split, industry_left[1]), industry_left],
            color=COLOR_RENEWABLE,
            width=scale_arrow_width(industry_energy, max_flow)
        )

    if green_hub_energy > 0:
        add_routed_arrow(
            fig,
            points=[system_center, (x_right_split, system_center[1]), (x_right_split, hub_left[1]), hub_left],
            color=COLOR_RENEWABLE,
            width=scale_arrow_width(green_hub_energy, max_flow)
        )

    if juechen_sued_energy > 0:
        add_routed_arrow(
            fig,
            points=[system_center, (x_right_split, system_center[1]), (x_right_split, js_left[1]), js_left],
            color=COLOR_RENEWABLE,
            width=scale_arrow_width(juechen_sued_energy, max_flow)
        )

    # =========================================================
    # 10) Battery connection (only when in use)
    # =========================================================

    battery_used = (battery_charge_kwh > 0) or (battery_discharge_kwh > 0)

    if battery_used:

        if battery_charge_kwh > 0:
            add_routed_arrow(
                fig,
                points=[system_center, (system_center[0], half_y_bat), (battery_top[0], half_y_bat), battery_top],
                color=COLOR_OPTIONAL,
                width=scale_arrow_width(battery_charge_kwh, max_flow)
            )

        if battery_discharge_kwh > 0:
            add_routed_arrow(
                fig,
                points=[battery_top, (battery_top[0], half_y_bat), (system_center[0], half_y_bat), system_center],
                color=COLOR_OPTIONAL,
                width=scale_arrow_width(battery_discharge_kwh, max_flow)
            )



    # =========================================================
    # 11) Grid logic:
    #     Surplus => System -> Grid
    #     Deficit    => Grid -> System
    # =========================================================
    if grid_export > 0:
        add_routed_arrow(
            fig,
            points=[system_center, (system_center[0], half_y_grid), (grid_bottom[0],  half_y_grid), grid_bottom],
            color=COLOR_RENEWABLE,
            width=scale_arrow_width(grid_export, max_flow),
            label="Überschuss",
            label_x=system_center[0]+0.025,
            label_y=half_y_grid+0.025
        )

    elif grid_import_total > 0:
        add_routed_arrow(
            fig,
            points=[grid_bottom, (grid_bottom[0], half_y_grid), (system_center[0], half_y_grid), system_center],
            color=COLOR_GRID,
            width=scale_arrow_width(grid_import_total, max_flow),
            label="Netzbezug",
            label_x=system_center[0]+0.02,
            label_y=half_y_grid+0.025
        )

        # Grey dotted line in case of energy deficit
        if industry_energy > 0:
            add_optional_connection(
                fig,
                points=[system_center, (x_right_split, system_center[1]), (x_right_split, industry_left[1]), industry_left],
                color=COLOR_GRID,
                width=scale_arrow_width(industry_energy, max_flow)-0.5,
                dash="dot",
            )

        if juechen_sued_energy > 0:
            add_optional_connection(
                fig,
                points=[system_center, (x_right_split, system_center[1]), (x_right_split, js_left[1]), js_left],
                color=COLOR_GRID,
                width=scale_arrow_width(juechen_sued_energy, max_flow)-0.5,
                dash="dot",
            )

        if green_hub_energy > 0:
            add_optional_connection(
                fig,
                points=[system_center, (x_right_split, system_center[1]), (x_right_split, hub_left[1]), hub_left],
                color=COLOR_GRID,
                width=scale_arrow_width(green_hub_energy, max_flow)-0.5,
                dash="dot",
            )

    # =========================================================
    # 12) Layout
    # =========================================================

    # Separation line between KPIs and energy flow visualization
    fig.add_shape(
        type="line",
        x0=0.1, x1=1.0,
        y0=0.815, y1=0.815,
        line=dict(color="gray", width=1)#, dash="dash")
    )

    # Layout: height an margin
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        height=820,
    )


    return fig

