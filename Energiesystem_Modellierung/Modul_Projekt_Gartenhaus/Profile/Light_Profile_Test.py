import pypsa
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

            # Monatsanfang (MS)
snapshots_h = pd.date_range("2019-01-01", periods=8760, freq="h")

n = pypsa.Network()
n.set_snapshots(snapshots_h)
print(snapshots_h)


# 16h an / 8h aus als Vektor (0=aus, 1=an)
def light_profile_16on_8off(snapshots_h):
    hours_of_day = np.arange(len(snapshots_h)) % 24     # 0,1,2,...,23,0,1,2,...
    on = (hours_of_day < 16).astype(float)              # 0..15 -> 1 (an), 16..23 -> 0 (aus)
    return pd.Series(on, index=snapshots_h, name="light_on")

light_on = light_profile_16on_8off(snapshots_h)

#(optional) Sichtprüfung: nur den ersten Tag plotten
first_day = light_on.loc["2019-01-01":"2019-01-14 23:00"]
plt.plot(first_day)
plt.show()