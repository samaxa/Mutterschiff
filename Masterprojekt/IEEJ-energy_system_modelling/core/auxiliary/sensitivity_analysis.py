#Übergabefertig kommentiert Felix
from core.io_types import GuiInput
from Simulation import run_simulation

from itertools import product
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from pathlib import Path
import os


base_dir = Path(__file__).resolve().parents[2]
output_dir = base_dir / "data" / "outputs" / "sensi_res_dfs"
output_dir.mkdir(parents=True, exist_ok=True)


import pandas as pd
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)




# ---------------- Heatmap plot ----------------
def plot_heatmap(heatmap: pd.DataFrame, save_path: str | None = None):
    """
    Heatmap:
    - red to green colour grading
    - zero as middle point (yellow)
    - current implementation does not consider Jüchen Süd and battery scenarios
    """

    plot_df = heatmap.copy()

    # Readable labels for scenarios (excluding battery)
    plot_df.index = [f"{geh} | {ind}" for geh, ind in plot_df.index]
    plot_df.columns = [f"{el} | {h}" for el, h in plot_df.columns]

    # Shared scale in pos and neg space, zero as center
    max_abs = np.nanmax(np.abs(plot_df.to_numpy()))
    norm = TwoSlopeNorm(vmin=-max_abs, vcenter=0, vmax=max_abs)

    plt.figure(figsize=(12, 8))
    ax = sns.heatmap(
        plot_df,
        annot=False,
        fmt=".0f",
        cmap="RdYlGn",  #"RdBu_r",   # negativ blau, positiv rot
        norm=norm,
        linewidths=0.5,
        linecolor="lightgray",
        cbar_kws={"label": "Direktnutzungsrate[%]"}
    )

    ax.set_title("Sensitivitätsanalyse - Energiebilanz", pad=12)
    ax.set_xlabel("EnergyLandscape | Highway")
    ax.set_ylabel("GreenEnergyHub | Industry")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()

    # Optional plot save
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()


# ---------------------------------------------------
# Configuration of scenarios
# ---------------------------------------------------

DEFAULT_CONFIG = {}

# ---------------- Case definitions ----------------
# 0: None, 1: Small, 2: Medium, 3: Large

# List of cases for multiple simulations and sensitivity analysis
h_cases = [1,2]       #,2,3]
el_cases = [1,2]      #,2,3]
i_cases = [1,2]       #,2,3]
geh_cases = [1,2]     #,2,3]
b_cases = [1,2]       # (multiple) choices not saved as csv or displayed in heatmap


# ---------------- Solar highway ----------------
H_CONFIGS = {
    0: {},
    1: {
        "highways": ["A46"],
        "h_pv_types": [0]               #0: Wind, 1: Schall, 2: Schall Dach, 3: Böschung,
    },

    2: {
        "highways": ["A44", 'A46'],
        "h_pv_types": [1,2]
    },
    3: {
        "highways": ["A44", "A46"],
        "h_pv_types": [1,2,3]
    }
}

# ---------------- Energy landscape ----------------
EL_CONFIGS = {
    0: {},
    1: {
        "el_build_state": 50,
        "el_pv_type": 5,
        "tractor_width": 24.0,
        "tractor_length": 15.0,
        "tractor_turn_radius": 9.0
    },
    2: {
        "el_build_state": 50,
        "tractor_width": 12.0,
        "el_pv_type": 6
    },
    3: {
        "el_build_state": 100,
        "tractor_width": 12.0,
        "el_pv_type": 4
    }
}

# ---------------- Industrial area ----------------
I_CONFIGS = {
    0: {},
    1: {
        "is_heat_cooling_electric": True,
        "companies": [2, 3, 4, 5, 6]
    },

    2: {
        "companies": [1, 5, 3, 6, 7],
        "is_heat_cooling_electric": True
    },

    3: {
        "companies": [0, 1, 1, 7, 7],
        "is_heat_cooling_electric": True
    }
}

# ---------------- Green Energy Hub ----------------
GEH_CONFIGS = {
    0: {},
    1: {
        "h2_load_scenario": "2022",
        "e_load_scenario": "2022"
    },

    2: {
        "h2_load_scenario": "2050",
        "e_load_scenario": "2050"
    },

    3: {
        "h2_load_scenario": "2030",
        "e_load_scenario": "2030"
    }

}

# ---------------- Battery ----------------
B_CONFIGS = {
    0: {},
    1: {
        "bs_efficiency": 1,
        "bs_energy_kwh": 10000.0,
        "bs_c_rate": 1,
        # Leistung kann mittels c faktor angegeben werden, default = 1
    },

    2: {
        "bs_efficiency": 1,
        "bs_energy_kwh": 235000.0,
        "bs_c_rate": 1,
    }
}



# ---------------- Individual input builder ----------------
def build_test_input(h_case=1, el_case=1, i_case=1, geh_case=1, b_case=1):
    """
    Creates the individual Input objects for each simulation run.
    Based on case definitions/ scenario configurations.
    :param : All Params within configuration cases are consistent with Input types from io_types.py. Jüchen Süd is not included in current implementation.
    :return: inp object
    """
    cfg = DEFAULT_CONFIG.copy()

    cfg.update(H_CONFIGS[h_case])
    cfg.update(EL_CONFIGS[el_case])
    cfg.update(I_CONFIGS[i_case])
    cfg.update(GEH_CONFIGS[geh_case])
    cfg.update(B_CONFIGS[b_case])

    inp = GuiInput()

    inp.h_highways = cfg.get("highways", [])
    inp.h_pv_types = cfg.get("h_pv_types", [])

    inp.el_build_state = cfg.get("el_build_state", None)
    inp.el_pv_type = cfg.get("el_pv_type", None)

    inp.el_tractor_width = cfg.get("tractor_width", None)
    inp.el_tractor_length = cfg.get("tractor_length", None)
    inp.el_tractor_turn_radius = cfg.get("tractor_turn_radius", None)

    inp.i_heat_cooling_electric = cfg.get("is_heat_cooling_electric", False)
    inp.i_companies = cfg.get("companies", [])

    inp.geh_h2_load_scenario = cfg.get("h2_load_scenario", None)
    inp.geh_e_load_scenario = cfg.get("e_load_scenario", None)

    inp.bs_efficiency = cfg.get("bs_efficiency", None)
    inp.bs_energy_kwh = cfg.get("bs_energy_kwh", None)
    inp.bs_c_rate = cfg.get("bs_c_rate", None)

    return inp



# ---------------- Sensitivity analysis ----------------
def run_sensitivity_analysis():

    # Predefine columns and row indices for heatmap data frame (results matrix)
    col_index = pd.MultiIndex.from_tuples(
        [(f"EL{el}",f"H{h}") for el, h in product(el_cases, h_cases)],
        names=["EnergyLandscape","Highway"]
    )
    row_index = pd.MultiIndex.from_tuples(
        [(f"GEH{g}", f"I{i}") for g, i in product(geh_cases, i_cases)],
        names=["GreenEnergyHub", "Industry"]
    )

    heatmap_df = pd.DataFrame(index=row_index, columns=col_index, dtype=float)


    # ---------------- for-loops to move through all cases  ----------------
    # multiple battery cases are not saved separately (last iteration will overwrite the previous ones)
    for b_case in b_cases:
        for el_case in el_cases:
            for h_case in h_cases:
                for geh_case in geh_cases:
                    for i_case in i_cases:


                        print(f"\nRunning case: \nh\t\t-  {h_case} "
                              f"\nel\t\t-  {el_case} "
                              f"\ni \t\t-  {i_case} "
                              f"\ngeh \t-  {geh_case}"
                              f"\nb\t\t- {b_case} ")

                        # Building individual input for current loop
                        inp = build_test_input(
                            el_case=el_case,
                            h_case=h_case,
                            geh_case=geh_case,
                            i_case=i_case,
                            b_case=b_case
                        )

                        # Simulation call
                        out = run_simulation(inp)

                        # Writing current scenario result into results matrix (heatmap_df)
                        heatmap_df.loc[
                            (f"GEH{geh_case}", f"I{i_case}"),
                            (f"EL{el_case}", f"H{h_case}")
                        ] = out.res_df['Bilanz [kW]'].sum()/4 #

                        if not out.bs_df.empty:
                            heatmap_df.loc[
                                (f"GEH{geh_case}", f"I{i_case}"),
                                (f"EL{el_case}", f"H{h_case}")
                            ] = out.bs_df['new_balance_kw'].sum() / 4       # out.res_df['Bilanz [kW]'].sum()/4 #

                        heatmap_df.to_excel(output_dir / "bat_balance.xlsx")

                        # Save output results data frame as csv
                        if not out.res_df.empty:
                            filename = f"{output_dir}/res_df_EL{el_case}_H{h_case}_GEH{geh_case}_I{i_case}_B{b_case}.csv"
                            out.res_df.to_csv(
                                filename,
                                sep=",",
                                decimal="."
                            )

                            # Console Output
                            print('-'*50,'\nResults Data Frame:')
                            print("CSV saved:", filename)
                            print('\n',out.res_df.head())
                            print('\n', out.res_df.sum(axis=0))
                            #print('\n', out.res_df.sum().sum())
                            print('\n',out.res_df.describe())

                            # Console Output if battery
                            if not out.bs_df.empty:
                                print('-'*50,'\nBatterie Data Frame:')
                                print('\n', out.bs_df.head())
                                print('\n', out.bs_df.describe())
                                print('\nStats: \n', {k: round(v, 0) if isinstance(v, float) else v for k, v in out.bs_stats.items()})

                        else:
                            print("No results: res_df empty")


        # Plot and save heatmap
        plot_heatmap(
            heatmap_df,
            save_path = os.path.join(output_dir, f"Bat_scenario_{b_case}_energy_balance.png")
        )


# ---------------- Execute main function ----------------
if __name__ == "__main__":
    run_sensitivity_analysis()
