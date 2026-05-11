

import pandas as pd
import pypsa 
import matplotlib.pyplot as plt   


df = pd.read_csv("../Input/nPro_Lastprofil.csv", index_col=0, parse_dates=True)
#print(df.columns)

df.columns = df.columns.str.strip()
total_load = df.sum(axis=1)

print(total_load.head())

total_load.to_csv("Input/gesamt_lastprofil.csv", header=["Last [kW]"])

total_load.plot(figsize=(12,5))
plt.ylabel("Last [kW]")
plt.xlabel("Zeit")
plt.title("Gesamtes Lastprofil")
plt.show()