# Übergabefertig kommentiert SM
import pandas as pd

class BatteryStorage:
    """
    Simple battery storage simulation.

    Concept:
    - Input is a load profile / power balance in kW
    - positive values -> surplus, battery can charge
    - negative values -> deficit, battery can discharge
    - output is a new balance:
        * 0   if the battery fully compensates the balance
        * >0  if surplus still remains and is exported to the grid
        * <0  if deficit still remains and grid import is required

    Extension:
    - maximum charge and discharge power via C-rate
    """

    def __init__(
        self,
        capacity_kwh: float,
        initial_soc_kwh: float = 0.0,
        charge_efficiency: float = 1.0,
        discharge_efficiency: float = 1.0,
        max_charge_c: float = 1.0,
        max_discharge_c: float = 1.0,
    ):
        self.capacity_kwh = capacity_kwh
        self.initial_soc_kwh = initial_soc_kwh
        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency

        self.max_charge_c = float(max_charge_c or 0)
        self.max_discharge_c = float(max_discharge_c or 0)


        # C-rate -> maximum power in kW
        self.max_charge_kw = self.capacity_kwh * self.max_charge_c
        self.max_discharge_kw = self.capacity_kwh * self.max_discharge_c

    def simulate(self, balance_series: pd.Series, timestep_hours: float = 1.0) -> pd.DataFrame:
        """
        Simulate the battery storage based on a power balance in kW.

        Parameters
        ----------
        balance_series : pd.Series
            Power balance in kW:
            > 0 = surplus
            < 0 = deficit
        timestep_hours : float
            Length of one timestep in hours, e.g.
            1.0 for hourly values
            0.25 for 15-minute values

        Returns
        -------
        pd.DataFrame
            DataFrame with:
            - balance_kw: original balance
            - battery_power_kw: battery charge/discharge power
                                > 0 = charging
                                < 0 = discharging
            - soc_kwh: battery state of charge
            - new_balance_kw: new balance after storage operation
                              > 0 = grid export
                              < 0 = grid import
                              = 0 = fully compensated by battery
        """

        soc = self.initial_soc_kwh

        battery_power_list = []
        soc_list = []
        new_balance_list = []

        for balance_kw in balance_series:
            # Convert power to energy for the current timestep
            balance_kwh = balance_kw * timestep_hours

            # Power limits per timestep as energy values
            max_charge_kwh_step = self.max_charge_kw * timestep_hours
            max_discharge_kwh_step = self.max_discharge_kw * timestep_hours

            # Case 1: surplus -> charge battery
            if balance_kwh > 0:
                # Charging is limited by:
                # 1. available surplus
                # 2. maximum charging power
                input_energy_for_charging = min(balance_kwh, max_charge_kwh_step)

                # Energy actually stored after charging efficiency
                energy_to_battery = input_energy_for_charging * self.charge_efficiency

                # Remaining free capacity
                free_capacity = self.capacity_kwh - soc

                # Energy that can actually be stored
                charged_kwh = min(energy_to_battery, free_capacity)

                # Update SOC
                soc += charged_kwh

                # Required input energy before efficiency losses
                input_used_for_charging = charged_kwh / self.charge_efficiency

                # Remaining surplus exported to the grid
                remaining_kwh = balance_kwh - input_used_for_charging

                # Positive battery power = charging
                battery_power_kw = input_used_for_charging / timestep_hours
                new_balance_kw = remaining_kwh / timestep_hours

            # Case 2: deficit -> discharge battery
            elif balance_kwh < 0:
                needed_kwh = abs(balance_kwh)

                # Discharge is limited by:
                # 1. required energy
                # 2. maximum discharge power
                # 3. available energy in storage
                max_deliverable_kwh = min(
                    max_discharge_kwh_step,
                    soc * self.discharge_efficiency
                )

                # Energy actually delivered by the battery
                delivered_kwh = min(needed_kwh, max_deliverable_kwh)

                # SOC reduction including efficiency losses
                energy_removed_from_soc = delivered_kwh / self.discharge_efficiency
                soc -= energy_removed_from_soc

                # Remaining deficit covered by grid import
                remaining_kwh = needed_kwh - delivered_kwh

                # Negative battery power = discharging
                battery_power_kw = -delivered_kwh / timestep_hours
                new_balance_kw = -remaining_kwh / timestep_hours

            # Case 3: exactly balanced
            else:
                battery_power_kw = 0.0
                new_balance_kw = 0.0

            battery_power_list.append(battery_power_kw)
            soc_list.append(soc)
            new_balance_list.append(new_balance_kw)

        result_df = pd.DataFrame(index=balance_series.index)
        result_df["balance_kw"] = balance_series
        result_df["battery_power_kw"] = battery_power_list
        result_df["soc_kwh"] = soc_list
        result_df["new_balance_kw"] = new_balance_list

        return result_df

    def get_stats(self, result_df: pd.DataFrame, timestep_hours: float = 1.0) -> dict:
        """
        Calculate simple key figures from the simulation result.
        """
        grid_import_kwh = abs(result_df.loc[result_df["new_balance_kw"] < 0, "new_balance_kw"].sum()) * timestep_hours
        grid_export_kwh = result_df.loc[result_df["new_balance_kw"] > 0, "new_balance_kw"].sum() * timestep_hours

        battery_charge_kwh = result_df.loc[result_df["battery_power_kw"] > 0, "battery_power_kw"].sum() * timestep_hours
        battery_discharge_kwh = abs(result_df.loc[result_df["battery_power_kw"] < 0, "battery_power_kw"].sum()) * timestep_hours

        final_soc = result_df["soc_kwh"].iloc[-1] if not result_df.empty else self.initial_soc_kwh

        return {
            "grid_import_kwh": grid_import_kwh,
            "grid_export_kwh": grid_export_kwh,
            "battery_charge_kwh": battery_charge_kwh,
            "battery_discharge_kwh": battery_discharge_kwh,
            "final_soc_kwh": final_soc,
            "final_soc_percent": (final_soc / self.capacity_kwh) * 100 if self.capacity_kwh > 0 else 0.0,
            "max_charge_kw": self.max_charge_kw,
            "max_discharge_kw": self.max_discharge_kw,
        }