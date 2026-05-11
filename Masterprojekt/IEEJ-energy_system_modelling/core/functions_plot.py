# Übergabefertig kommentiert SM

import matplotlib.pyplot as plt
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


"""
plot_functions.py

Visualization functions for selected subprojects of the
Innovationspark Erneuerbare Energien Jüchen.

Included:
- Industrial area load profile plots
- Green Energy Hub weekly and annual plots
- Jüchen Süd weekly load plot

-Result plots:
    -Energy Balance
    -Generation
    -Consumption
    -Balance with and without battery
    -Battery SOC

The module only visualizes prepared CSV-based time series.
No physical simulation is performed here.
"""

# --------------------------------------------------
# Industrial area
# --------------------------------------------------
def plot_industry_preview(csv_path, selected_columns=None, start="2017-03-05"):
    """
    Plot one representative week of selected industrial load profiles.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.
    selected_columns : list[str] | None
        Optional list of columns to plot.
    start : str
        Start date of the selected week.

    Returns
    -------
    matplotlib.figure.Figure
        Figure with weekly load profiles.
    """

    df = pd.read_csv(csv_path, sep=";")
    df["Time stamp"] = pd.to_datetime(df["Time stamp"])
    df.set_index("Time stamp", inplace=True)

    if selected_columns is not None and len(selected_columns) > 0:
        df = df[selected_columns]

    df_week = df.loc[start:].iloc[:7 * 24 * 4]

    fig, ax = plt.subplots(figsize=(15, 7))

    for column in df_week.columns:
        ax.plot(df_week.index, df_week[column], label=column)

    ax.set_title(f"Lastgänge Industriegebiet – Woche ab {start}")
    ax.set_xlabel("Zeit")
    ax.set_ylabel("Leistung [kW]")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()

    return fig


def plot_industry_annual_energy(csv_path, ordered_columns=None, title="Jahresenergie pro Unternehmen"):
    """
    Plot annual energy demand per company as a bar chart.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.
    ordered_columns : list[str] | None
        Optional column order for plotting.
    title : str
        Plot title.

    Returns
    -------
    matplotlib.figure.Figure
        Figure with annual energy demand.
    """

    df = pd.read_csv(csv_path, sep=";")
    df["Time stamp"] = pd.to_datetime(df["Time stamp"])
    df.set_index("Time stamp", inplace=True)

    if ordered_columns is not None:
        df = df[ordered_columns]

    # 15 min values: kW * 0.25 h = kWh, then convert to GWh
    annual_energy = df.sum() * 0.25 /1000000

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.bar(
        annual_energy.index,
        annual_energy.values,
        color=colors[:len(annual_energy)]
    )

    ax.set_title(title)
    ax.set_ylabel("Energiebedarf [GWh]")
    ax.set_xlabel("Unternehmen")
    ax.grid(axis="y")
    ax.legend(bars, annual_energy.index)

    plt.xticks(rotation=45)
    fig.tight_layout()

    return fig

# --------------------------------------------------
# Green Energy Hub
# --------------------------------------------------

def _read_green_hub_timeseries(csv_path):
    """
    Read a Green Energy Hub CSV and return one power time series.

    The function tries to detect common time and value column names
    automatically and converts the result to a numeric pandas Series.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.

    Returns
    -------
    pandas.Series
        Power time series with datetime index.
    """

    df = pd.read_csv(csv_path)

    # mögliche Zeitspalten
    time_candidates = ["time", "Time", "timestamp", "Timestamp", "time_input_year", "date", "Date"]

    # mögliche Leistungsspalten
    value_candidates = [
        "power_kW", "power_MW",
        "P (kW)", "P (MW)", "P new (MW)", "P [MW]",
        "power_mw", "power", "load", "value"
    ]

    # Detect time column
    time_col = None
    for c in time_candidates:
        if c in df.columns:
            time_col = c
            break

    if time_col is None:
        time_col = df.columns[0]

    # Detect value column
    value_col = None
    for c in value_candidates:
        if c in df.columns:
            value_col = c
            break

    if value_col is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        numeric_cols = [c for c in numeric_cols if c != time_col]
        if not numeric_cols:
            raise ValueError(f"Keine geeignete Leistungsspalte in {csv_path} gefunden.")
        value_col = numeric_cols[0]

    # Parse timestamps like "03-05 00:15" as "2022-03-05 00:15"
    time_values = df[time_col].astype(str).str.strip()
    parsed_time = pd.to_datetime(
        "2022-" + time_values,
        format="%Y-%m-%d %H:%M",
        errors="coerce"
    )

    if parsed_time.isna().all():
        raise ValueError(
            f"Zeitspalte in {csv_path} konnte nicht geparst werden. "
            f"Beispielwerte: {time_values.head().tolist()}"
        )

    df[time_col] = parsed_time
    df = df.set_index(time_col)

    series = pd.to_numeric(df[value_col], errors="coerce")
    return series


def plot_green_hub_weekly_profiles(base_dir, h2_year=None, e_year=None, start="2022-03-05"):
    """
    Plot one representative week of Green Energy Hub profiles.

    Optional:
    - BEV charging load
    - Electrolyzer load

    Parameters
    ----------
    base_dir : str
        Base directory containing scenario folders.
    h2_year : str | None
        Selected hydrogen scenario year.
    e_year : str | None
        Selected electric scenario year.
    start : str
        Start date of the selected week.

    Returns
    -------
    matplotlib.figure.Figure
        Figure with weekly profiles.
    """
    fig, ax = plt.subplots(figsize=(15, 7))
    plotted_anything = False

    # BEV load
    if e_year not in [None, "Keine"]:
        bev_path = os.path.join(base_dir, str(e_year), "BEV_load_el_15min.csv")
        bev = _read_green_hub_timeseries(bev_path)

        try:
            bev_week = bev.loc[start:].iloc[:7 * 24 * 4]
        except Exception:
            bev_week = bev.iloc[:7 * 24 * 4]

        ax.plot(bev_week.index, bev_week.values, label=f"BEV {e_year}")
        plotted_anything = True

    # Electrolyzer load
    if h2_year not in [None, "Keine"]:
        ely_path = os.path.join(base_dir, str(h2_year), "Electrolyzer_output.csv")
        ely = _read_green_hub_timeseries(ely_path)

        try:
            ely_week = ely.loc[start:].iloc[:7 * 24 * 4]
        except Exception:
            ely_week = ely.iloc[:7 * 24 * 4]

        ax.plot(ely_week.index, ely_week.values, linestyle="--", label=f"Elektrolyseur {h2_year}")
        plotted_anything = True

    # Placeholder text
    if not plotted_anything:
        ax.text(
            0.5, 0.5,
            "Keine Green-Energy-Hub-Daten ausgewählt.",
            ha="center",
            va="center",
            transform=ax.transAxes
        )

    ax.set_title("Beispielhafte Wochenprofile des Green Energy Hub")
    ax.set_xlabel("Zeit")
    ax.set_ylabel("Leistung [kW]")
    ax.grid(True)

    if plotted_anything:
        ax.legend()

    fig.tight_layout()
    return fig

def plot_green_hub_annual_energy(base_dir, years=("2022", "2030", "2050")):
    """
    Plot annual electricity demand of the Green Energy Hub.

    Compares:
    - BEV charging infrastructure
    - Electrolyzer

    Parameters
    ----------
    base_dir : str
        Base directory containing scenario folders.
    years : iterable[str]
        Scenario years to compare.

    Returns
    -------
    matplotlib.figure.Figure
        Grouped bar chart of annual energy demand.
    """
    years = [str(y) for y in years]

    bev_energy = []
    ely_energy = []

    for year in years:
        bev_path = os.path.join(base_dir, year, "BEV_load_el_15min.csv")
        ely_path = os.path.join(base_dir, year, "Electrolyzer_output.csv")

        bev = _read_green_hub_timeseries(bev_path)
        ely = _read_green_hub_timeseries(ely_path)

        # kW bei 15-min Raster -> kWh mit *0.25 -> MWh mit /1000
        bev_energy.append(bev.sum() * 0.25 / 1000)
        ely_energy.append(ely.sum() * 0.25 / 1000)

    x = range(len(years))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([i - width / 2 for i in x], bev_energy, width=width, label="BEV-Ladesäulen")
    ax.bar([i + width / 2 for i in x], ely_energy, width=width, label="Elektrolyseur")

    ax.set_title("Jährlicher Stromverbrauch des Green Energy Hub")
    ax.set_xlabel("Szenariojahr")
    ax.set_ylabel("Energie [MWh]")
    ax.set_xticks(list(x))
    ax.set_xticklabels(years)
    ax.grid(axis="y")
    ax.legend()
    fig.tight_layout()

    return fig


# --------------------------------------------------
# Jüchen Süd
# --------------------------------------------------
def plot_js_weekly_profile(csv_path, scale_factor=1, start="2022-03-05"):
    """
    Plot one representative week of the Jüchen Süd load profile.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.
    scale_factor : float
        Scaling factor applied to the load.
    start : str
        Start date of the selected week.

    Returns
    -------
    matplotlib.figure.Figure
        Figure with the scaled weekly load profile.
    """

    df = pd.read_csv(csv_path, sep=",")
    df.columns = df.columns.str.strip()

    df["timestamp"] = pd.to_datetime(
        "2022 " + df["Timestamp"].astype(str).str.strip(),
        format="%Y %d.%m. %H:%M",
        errors="coerce"
    )

    df["Strombezug (kW)"] = pd.to_numeric(
        df["Strombezug (kW)"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    ).fillna(0)

    df = df.set_index("timestamp").sort_index()

    # Skalierung
    series = df["Strombezug (kW)"] * scale_factor

    try:
        week = series.loc[start:].iloc[:7 * 24 * 4]
    except Exception:
        week = series.iloc[:7 * 24 * 4]

    fig, ax = plt.subplots(figsize=(15, 7))

    ax.plot(week.index, week.values, label=f"Jüchen Süd x{scale_factor}")

    ax.set_title("Beispielhafte Wochenprofile – Jüchen Süd")
    ax.set_xlabel("Zeit")
    ax.set_ylabel("Leistung [kW]")
    ax.grid(True)
    ax.legend()

    fig.tight_layout()
    return fig




# --------------------------------------------------
# Result Plots
# --------------------------------------------------



def plot_generation(sim_output):
    generation_cols = [col for col in sim_output.res_df.columns if "Erzeugung" in col]
    generation = sim_output.res_df[generation_cols].sum(axis=1)

    if not isinstance(generation.index, pd.DatetimeIndex):
        generation.index = pd.date_range(
            start="2021-01-01 00:00:00",
            periods=len(generation),
            freq="15min"
        )

    mean_val = generation.mean()
    max_val = generation.max()

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(
        generation.index,
        generation.values,
        label="Erzeugung"
    )
    ax.axhline(mean_val, color="red", linestyle="--", linewidth=1.5, label=f"Mittelwert: {mean_val:.1f} kW")
    ax.axhline(max_val, color="red", linestyle=":", linewidth=1.2, label=f"Maximum: {max_val:.1f} kW")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_title("Leistungsverlauf Erzeugung")
    ax.set_xlabel("Monat")
    ax.set_ylabel("Leistung [kW]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.autofmt_xdate()

    return fig

def plot_consumption(sim_output):
    demand_cols = [col for col in sim_output.res_df.columns if "Last" in col]
    demand = sim_output.res_df[demand_cols].sum(axis=1)
    if not isinstance(demand.index, pd.DatetimeIndex):
        demand.index = pd.date_range(
            start="2021-01-01 00:00:00",
            periods=len(demand),
            freq="15min"
        )
    mean_val = demand.mean()
    # min_val = demand.min()
    max_val = demand.max()

    fig1, ax1 = plt.subplots(figsize=(12, 4))
    ax1.plot(
        demand.index,
        demand.values,
        label="Verbrauch"
    )
    ax1.axhline(mean_val, color="red", linestyle="--", linewidth=1.5, label=f"Mittelwert: {mean_val:.1f} kW")
    ax1.axhline(max_val, color="red", linestyle=":", linewidth=1.2, label=f"Maximum: {max_val:.1f} kW")
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax1.set_title("Leistungsverlauf Verbrauch")
    ax1.set_xlabel("Monat")
    ax1.set_ylabel("Leistung [kW]")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper center")
    fig1.autofmt_xdate()

    return fig1

def plot_balance(sim_output):
    # Balance from res_df (no battery) or bs_df (if battery)
    if hasattr(sim_output, "bs_df") and sim_output.bs_df is not None and not sim_output.bs_df.empty:
        y = sim_output.bs_df["new_balance_kw"].copy()
        # plot_title = "Bilanz nach Batteriespeicher"
        # line_label = "Bilanz nach Batterie"
    else:
        y = sim_output.res_df["Bilanz [kW]"].copy()
        # plot_title = "Bilanzverlauf"
        # line_label = "Bilanz"

    if not isinstance(y.index, pd.DatetimeIndex):
        y.index = pd.date_range(
            start="2021-01-01 00:00:00",
            periods=len(y),
            freq="15min"
        )

    mean_val = y.mean()
    min_val = y.min()
    max_val = y.max()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(y.index, y.values, label="Bilanz")

    ax.axhline(mean_val, color="red", linestyle="--", linewidth=1.5, label=f"Mittelwert: {mean_val:.1f} kW")
    ax.axhline(min_val, color="red", linestyle=":", linewidth=1.2, label=f"Minimum: {min_val:.1f} kW")
    ax.axhline(max_val, color="red", linestyle=":", linewidth=1.2, label=f"Maximum: {max_val:.1f} kW")

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    ax.set_title("Bilanzverlauf")
    ax.set_xlabel("Monat")
    ax.set_ylabel("Leistung [kW]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")

    fig.autofmt_xdate()

    return fig


def plot_battery_comparison(sim_output):
    # Plot 1: Balance with battery storage
    balance_with_battery = sim_output.bs_df["new_balance_kw"].copy()
    if not isinstance(balance_with_battery.index, pd.DatetimeIndex):
        balance_with_battery.index = pd.date_range(
            start="2021-01-01 00:00:00",
            periods=len(balance_with_battery),
            freq="15min"
        )
    mean_val = balance_with_battery.mean()
    min_val = balance_with_battery.min()
    max_val = balance_with_battery.max()

    fig1, ax1 = plt.subplots(figsize=(12, 4))
    ax1.plot(
        balance_with_battery.index,
        balance_with_battery.values,
        label="Bilanz MIT Batterie"
    )
    ax1.axhline(mean_val, color="red", linestyle="--", linewidth=1.5, label=f"Mittelwert: {mean_val:.1f} kW")
    ax1.axhline(min_val, color="red", linestyle=":", linewidth=1.2, label=f"Minimum: {min_val:.1f} kW")
    ax1.axhline(max_val, color="red", linestyle=":", linewidth=1.2, label=f"Maximum: {max_val:.1f} kW")
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax1.set_title("Netzbilanz MIT Batteriespeicher")
    ax1.set_xlabel("Monat")
    ax1.set_ylabel("Leistung [kW]")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    fig1.autofmt_xdate()


    # Plot 2: Balance withOUT battery storage
    balance_without_battery = sim_output.bs_df["balance_kw"].copy()
    if not isinstance(balance_without_battery.index, pd.DatetimeIndex):
        balance_without_battery.index = pd.date_range(
            start="2021-01-01 00:00:00",
            periods=len(balance_without_battery),
            freq="15min"
        )
    mean_val = balance_without_battery.mean()
    min_val = balance_without_battery.min()
    max_val = balance_without_battery.max()

    fig2, ax2 = plt.subplots(figsize=(12, 4))
    ax2.plot(
        balance_without_battery.index,
        balance_without_battery.values,
        label="Bilanz OHNE Batterie"
    )
    ax2.axhline(mean_val, color="red", linestyle="--", linewidth=1.5, label=f"Mittelwert: {mean_val:.1f} kW")
    ax2.axhline(min_val, color="red", linestyle=":", linewidth=1.2, label=f"Minimum: {min_val:.1f} kW")
    ax2.axhline(max_val, color="red", linestyle=":", linewidth=1.2, label=f"Maximum: {max_val:.1f} kW")
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax2.set_title("Netzbilanz OHNE Batteriespeicher")
    ax2.set_xlabel("Monat")
    ax2.set_ylabel("Leistung [kW]")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    fig2.autofmt_xdate()


    return fig1, fig2



def plot_soc(Input, sim_output):
    bs_soc = sim_output.bs_df["soc_kwh"].copy()
    bs_soc_percent = bs_soc / Input.bs_energy_kwh * 100
    if not isinstance(bs_soc_percent.index, pd.DatetimeIndex):
        bs_soc_percent.index = pd.date_range(
            start="2021-01-01 00:00:00",
            periods=len(bs_soc_percent),
            freq="15min"
        )

    fig3, ax3 = plt.subplots(figsize=(12, 4))
    ax3.plot(
        bs_soc_percent.index,
        bs_soc_percent.values,
        label="State of charge"
    )
    ax3.xaxis.set_major_locator(mdates.MonthLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax3.set_xlabel("Monat")
    ax3.set_title(f"State of Charge der Batterie (Kapazität: {Input.bs_energy_kwh / 1000} MWh)")
    ax3.set_ylabel("SOC [%]")
    ax3.grid(True)
    ax3.legend()
    fig3.autofmt_xdate()

    return fig3
